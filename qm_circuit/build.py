"""Turn a captured QUA program (proto + call stacks) into the circuit model.

Everything shown comes from the proto (so Python constants appear as their values) plus the tracer:
QUA variables are named as in the outermost Python frame that holds them, helper blocks are labelled
with the arguments actually passed at their call site.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping

from google.protobuf.message import Message
from qm.qua._expressions import QuaExpression
from qm.serialization.expression_serializing_visitor import ExpressionSerializingVisitor

from .nodes import Align, Block, Branch, If, Loop, Op, Play, Program, Wait, elements
from .tracer import Tracer

_NAME_RE = re.compile(r"\b[A-Za-z_]\w*\b")
_NOT_RE = re.compile(r"(\([^()]*\)|\w+)\^True\b")
_NUM_RE = re.compile(r"(?<![\w.])\d+\.\d+(?:e[-+]?\d+)?(?![\w.])")
_PLAY_PARAMS = dict(amp="amp", duration="duration", condition="condition", truncate="truncate", chirp="chirp",
                    targetInput="target")  # proto field -> play() argument
_CHIRP_UNITS = dict(HzPerNanoSec="GHz/s", mHzPerNanoSec="MHz/s", uHzPerNanoSec="kHz/s", nHzPerNanoSec="Hz/s",
                    pHzPerNanoSec="mHz/s")
_INV_2PI = 0.15915494309189535  # frame_rotation(angle) emits frame_rotation_2pi(angle * _INV_2PI)
_MAX_ITEMS = 4  # longer sequences are summarized
_HEAD = 2  # leading items kept when an unevenly spaced sequence is summarized
_MAX_STR = 24  # longer string reprs are cut


def num(x: int | float) -> str:
    """Compact number: 0.3, 16, 1.2e8; long exact integers keep all digits (51_234_567)."""
    s = f"{x:.4g}"
    if isinstance(x, int) and (abs(x) < 100_000 or float(s) != x):
        return f"{x:_}"
    mantissa, _, exp = s.partition("e")
    return f"{mantissa}e{int(exp)}" if exp else s


def _literal(s: str):
    if s in ("True", "False"):
        return s == "True"
    for typ in (int, float):
        try:
            return typ(s)
        except ValueError:
            pass
    return s


def _snake(kind: str) -> str:
    return re.sub(r"(?<!^)([A-Z])", r"_\1", kind).lower()


def _bodies(x):
    """Nested statement collections of a compound statement (loop/if/scope bodies)."""
    for f, v in x.ListFields():
        if f.name in ("init", "update") or f.message_type is None:
            continue
        for item in [v] if isinstance(v, Message) else v:
            if isinstance(item, Message) and item.DESCRIPTOR.name == "StatementsCollection":
                yield item
            elif isinstance(item, Message) and item.DESCRIPTOR.name == "ElseIf":
                yield item.body


class _Builder:
    def __init__(self, tracer: Tracer, show_saves: bool):
        self.tracer, self.show_saves = tracer, show_saves
        variables = tracer.program.qua_program.script.variables
        self.arrays = {v.name: [_literal(x.value) for x in v.value] for v in variables if len(v.value)}

    # ------------------------------------------------------------ values

    def expr(self, e) -> str:
        """Proto expression as text: literals as compact values, variables by their Python names."""
        which = e.WhichOneof("expression_oneof") if e.DESCRIPTOR.name == "AnyScalarExpression" else None
        if which == "literal":
            v = _literal(e.literal.value)
            return str(v) if isinstance(v, (str, bool)) else num(v)
        s = ExpressionSerializingVisitor(None).serialize(e)
        s = _NUM_RE.sub(lambda m: num(float(m.group())), s)
        s = _NAME_RE.sub(lambda m: self.tracer.names.get(m.group(), m.group()), s)
        s = s[1:-1] if which == "binaryOperation" else s
        return _NOT_RE.sub(r"~\1", s)  # ~x is serialized as x^True

    def fmt(self, v) -> str:
        """Short text for a Python value passed to a helper."""
        if isinstance(v, QuaExpression):
            return self.expr(v._expression)
        if type(v).__module__ == "numpy":
            v = v.tolist()
        if isinstance(v, str) and len(v) > _MAX_STR:
            return repr(v[:_MAX_STR]) + "..."
        if v is None or isinstance(v, (bool, str)):
            return repr(v)
        if isinstance(v, (int, float)):
            return num(v)
        if isinstance(v, (list, tuple)):
            return self.seq(v, "()" if isinstance(v, tuple) else "[]")
        if isinstance(v, Mapping):
            return f"{{{len(v)} items}}"
        r = repr(v)
        return r if len(r) <= _MAX_STR and "\n" not in r else getattr(v, "__name__", None) or type(v).__name__

    def seq(self, v, brackets: str = "[]", limit: int = _MAX_ITEMS) -> str:
        """Items; more than ``limit + 1`` are summarized with their count.

        Evenly spaced numbers read ``[first..last] (n)``; anything else ``[first, second, ..., last] (n)``.
        """
        if len(v) <= limit + 1:
            return brackets[0] + ", ".join(self.fmt(x) for x in v) + brackets[1]
        if all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in v):
            steps = [b - a for a, b in zip(v, v[1:])]
            if steps[0] and all(math.isclose(d, steps[0], rel_tol=1e-6) for d in steps):
                return f"[{num(v[0])}..{num(v[-1])}] ({len(v)})"
        items = [self.fmt(x) for x in v[:_HEAD]] + ["...", self.fmt(v[-1])]
        return f"{brackets[0]}{', '.join(items)}{brackets[1]} ({len(v)})"

    def param(self, k: str | None, v, src: str | None = None) -> str:
        """``k=value`` as passed to a helper; just ``value`` for a ``*args`` item or when it reads the same as ``k``.

        Objects without a readable value (a stream, ...) show the call-site expression ``src`` instead of their type.
        """
        text = self.fmt(v)
        if src and text == type(v).__name__:
            text = src
        return text if k is None or k == text else f"{k}={text}"

    def arg(self, v) -> str:
        if not isinstance(v, Message):
            return repr(v)
        name = v.DESCRIPTOR.name
        if name == "AmpMultiplier":
            vs = [self.expr(getattr(v, f"v{i}")) for i in range(4) if v.HasField(f"v{i}")]
            return vs[0] if len(vs) == 1 else f"({', '.join(vs)})"
        if name == "Chirp":
            array = self.arrays.get(v.arrayRate.name) if v.HasField("arrayRate") else None
            rate = self.seq(array) if array else self.expr(v.scalarRate if v.HasField("scalarRate") else v.arrayRate)
            unit = v.DESCRIPTOR.fields_by_name["units"].enum_type.values_by_number[v.units].name
            return f"{rate} {_CHIRP_UNITS.get(unit, unit)}"
        if name.endswith("Value"):  # google.protobuf wrappers (UInt32Value, ...)
            return str(v.value)
        if "name" in v.DESCRIPTOR.fields_by_name and name != "VarRefExpression":
            return self.tracer.names.get(v.name, v.name)
        if name.endswith("Expression"):
            return self.expr(v)
        return ", ".join(self.arg(x) for _, x in v.ListFields())  # e.g. update_correction's matrix

    # ------------------------------------------------------------ structure

    def stack(self, st) -> tuple[int, ...]:
        return self.tracer.stack_of(getattr(st, st.WhichOneof("statement_oneof")).loc)

    def api(self, st) -> str:
        i = self.tracer.trace_id(getattr(st, st.WhichOneof("statement_oneof")).loc)
        return "" if i is None else self.tracer.apis[i]

    def group(self, statements, depth: int) -> list:
        """Convert statements; contiguous ones from the same helper call (at ``depth + 1``) become a Block."""
        items: list = []  # nodes, or [call_id, statements] for pending helper blocks
        for st in statements:
            stack = self.stack(st)
            cid = stack[depth + 1] if len(stack) > depth + 1 else None
            x = getattr(st, st.WhichOneof("statement_oneof"))
            if cid is not None and not all(cid in self.stack(s) for b in _bodies(x) for s in b.statements):
                cid = None  # emitted by a context-manager helper around caller code: an open region
            if cid is None:
                items.append(self.convert(st, depth))
            elif items and isinstance(items[-1], list) and items[-1][0] == cid:
                items[-1][1].append(st)
            else:
                items.append([cid, [st]])
        out: list = []
        for it in items:
            node = self.block(it[0], it[1], depth) if isinstance(it, list) else it
            prev = out[-1] if out else None
            if isinstance(node, Align) and isinstance(prev, Align):  # consecutive aligns: one align
                new = [t for t in node.targets if t not in prev.targets]
                prev.targets = prev.targets and node.targets and prev.targets + new
            elif isinstance(node, Op) and node.name == "save" and isinstance(prev, Op) and prev.name == "save":
                prev.args += ", " + node.args
            elif isinstance(node, Wait) and isinstance(prev, Wait) and prev.targets == node.targets:  # one wait
                a, b = _literal(prev.duration.replace("_", "")), _literal(node.duration.replace("_", ""))
                both = all(isinstance(x, int) for x in (a, b))
                prev.duration = num(a + b) if both else f"{prev.duration} + {node.duration}"
            elif node is not None:
                out.append(node)
        return out

    def block(self, cid: int, statements, depth: int) -> Block | None:
        call = self.tracer.calls[cid]
        body = self.group(statements, depth + 1)
        params = [self.param(k, v, call.src.get(k)) for k, v in call.args]
        return Block(call.func, params, body) if body else None

    def convert(self, st, depth: int):
        kind = st.WhichOneof("statement_oneof")
        x = getattr(st, kind)
        if kind in ("play", "measure"):
            which = x.WhichOneof("pulseType") if kind == "play" else "pulse"
            pulse = f"ramp({self.expr(x.rampPulse.value)})" if which == "rampPulse" else getattr(x, which).name
            params = {_PLAY_PARAMS[f.name]: self.arg(v) for f, v in x.ListFields() if f.name in _PLAY_PARAMS}
            return Play(x.qe.name, pulse, params, measure=kind == "measure")
        if kind == "wait":
            return Wait([e.name for e in x.qe], self.expr(x.time))
        if kind == "align":
            return Align([e.name for e in x.qe])
        if kind == "save":
            return Op("save", [], self.arg(x.source.ListFields()[0][1])) if self.show_saves else None
        if kind == "for":
            return self.loop(x, depth)
        if kind == "forEach":
            body = self.group(x.body.statements, depth)
            names = [self.expr(it.variable) for it in x.iterator]
            arrays = [self.arrays.get(it.array.name) for it in x.iterator]
            if len(names) > 1 and all(arrays):  # parallel arrays: show the tuples actually iterated
                values = self.seq(list(zip(*arrays)), limit=_MAX_ITEMS // 2)
            else:
                values = ", ".join(self.seq(a) if a else self.expr(it.array) for a, it in zip(arrays, x.iterator))
            names_text = f"({', '.join(names)})" if len(names) > 1 else names[0]
            return Loop("for_each", f"{names_text} in {values}", body) if body else None
        if kind == "if":
            branches = [Branch(f"if {self.expr(x.condition)}", self.group(x.body.statements, depth))]
            branches += [Branch(f"elif {self.expr(e.condition)}", self.group(e.body.statements, depth))
                         for e in x.elseifs]
            if x.HasField("else"):
                branches.append(Branch("else", self.group(getattr(x, "else").statements, depth)))
            while branches and not branches[-1].body:  # nothing drawn there (e.g. switch_'s implicit else)
                branches.pop()
            return If(branches) if branches else None
        if kind == "zRotation" and self.api(st) == "frame_rotation":  # show the angle in radians, as written
            v = x.value
            if v.WhichOneof("expression_oneof") == "literal":
                angle = num(float(v.literal.value) / _INV_2PI)
            else:
                b = v.binaryOperation
                angle = self.expr(b.left) if self.expr(b.right) == num(_INV_2PI) else self.expr(v)
            return Op("frame_rotation", [x.qe.name], angle)
        bodies = list(_bodies(x))
        if bodies:  # strict_timing_ and other QUA scopes: always an open region
            body = [n for b in bodies for n in self.group(b.statements, depth)]
            return Block(_snake(kind), [], body, scope=True) if body else None
        if kind == "assign":
            return None
        qe = getattr(x, "qe", ())  # element(s); none: a marker over the region (advance_input_stream, ...)
        targets = [qe.name] if isinstance(qe, Message) else [e.name for e in qe]
        args = [self.arg(v) if isinstance(v, (Message, str)) else
                f"{_snake(f.name)}={f.enum_type.values_by_number[v].name if f.enum_type else v}"
                for f, v in x.ListFields() if f.name not in ("qe", "qes", "loc")]
        api = self.api(st)
        return Op(api if api and not api.startswith("_") else _snake(kind), targets, ", ".join(args))

    def loop(self, x, depth: int) -> Loop | None:
        body = self.group(x.body.statements, depth)
        if not body:
            return None
        if not x.init.statements and not x.update.statements:
            return Loop("while", f"while {self.expr(x.condition)}", body)
        init = x.init.statements[0].assign
        var = init.target.variable if init.HasField("target") else init.variable
        name, start = self.expr(var), self.expr(init.expression)
        cond = x.condition.binaryOperation
        upd = x.update.statements[0].assign.expression.binaryOperation if x.update.statements else None
        op = lambda b: b.DESCRIPTOR.fields_by_name["op"].enum_type.values_by_number[b.op].name  # noqa: E731
        if (upd and op(cond) == "LT" and op(upd) == "ADD" and self.expr(cond.left) == name
                and self.expr(upd.left) == name):
            step = self.expr(upd.right)
            step = "" if step == "1" else ", " + step
            return Loop("for", f"{name} in range({start}, {self.expr(cond.right)}{step})", body)
        update = self.expr(x.update.statements[0].assign.expression) if x.update.statements else ""
        return Loop("for", f"for {name} = {start}; {self.expr(x.condition)}; {name} = {update}", body)


def build_model(tracer: Tracer, show_saves: bool = False) -> Program:
    if tracer.program is None:
        raise RuntimeError("no q.program() was built")
    body = _Builder(tracer, show_saves).group(tracer.program.qua_program.script.body.statements, depth=0)
    return Program(tracer.name, elements(Block("", [], body)), body)
