"""Record the Python call stack behind every QUA statement, fully offline.

qm-qua calls ``qm._loc._get_loc()`` once per statement/expression and stores the returned string in
the proto ``loc`` field. Every ``qm.*`` module imported that name directly, so we rebind it in each
module to a wrapper that records the live call stack and returns a loc tagged ``#trace=<id>``. The tag
travels inside the protobuf, so statement -> call stack mapping is exact.

Stacks start at the frame that entered ``q.program()`` (the "program frame"): wrappers around the
program function do not count as helpers. When ``q.program()`` exits, the Program is recorded and a
private exception aborts the rest of the caller (e.g. an ``*_acq`` function that would run a job).

Private qm APIs used (pinned to qm-qua 1.4.x): ``qm._loc._get_loc``, ``_ProgramScope``,
``_ForScope._create_statement`` (1.4.1 never fills ``ForStatement.loc``) and ``_ElifScope.__init__``
(elif reuses the if loc).
"""

from __future__ import annotations

import ast
import inspect
import linecache
import re
import sys
import sysconfig
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import FrameType
from typing import Any

import qm._loc as _loc_mod
from qm.qua._expressions import QuaExpression
from qm.qua._scope_management import scopes as _scopes
from qm.qua._scope_management._core_scopes import _ProgramScope

_QM_DIR = Path(_loc_mod.__file__).resolve().parent
_OWN_DIR = Path(__file__).resolve().parent
_STDLIB_DIR = Path(sysconfig.get_paths()["stdlib"]).resolve()
_TRACE_RE = re.compile(r"#trace=(\d+)\s*$")
_ORIG_GET_LOC = _loc_mod._get_loc


class _Captured(BaseException):
    """Raised when ``q.program()`` exits, to stop the caller from going on (running jobs, ...)."""


@dataclass
class Call:
    """One helper-function invocation: name, the arguments passed at the call site, stack depth."""

    func: str
    args: list[tuple[str | None, object]]  # (param name, value); name None = item of *args
    depth: int
    src: dict[str, str] = field(default_factory=dict)  # param name -> expression written at the call site


def _is_user_file(filename: str) -> bool:
    p = Path(filename).resolve()
    if _QM_DIR in p.parents or _OWN_DIR in p.parents:
        return False
    if "site-packages" in p.parts or "dist-packages" in p.parts:
        return False
    return _STDLIB_DIR not in p.parents


def _call_node(f: FrameType | None) -> ast.Call | None:
    """AST of the call expression frame ``f`` is currently executing (None if unavailable)."""
    if f is None:
        return None
    try:
        l0, l1, c0, c1 = list(f.f_code.co_positions())[f.f_lasti // 2]
        if l0 is None or l1 is None or c0 is None or c1 is None:
            return None
        raw = [ln.encode() for ln in linecache.getlines(f.f_code.co_filename)[l0 - 1 : l1]]
        seg = raw[0][c0:c1] if l0 == l1 else b"".join([raw[0][c0:], *raw[1:-1], raw[-1][:c1]])
        node = ast.parse("(\n" + seg.decode() + "\n)", mode="eval").body
    except Exception:
        return None
    return node if isinstance(node, ast.Call) else None


def _passed_args(f: FrameType) -> tuple[list[tuple[str | None, object]], dict[str, str]]:
    """Arguments of frame ``f`` that were actually given at its call site, with their bound values, and the
    source expressions written for them (by parameter name, when known)."""
    info = inspect.getargvalues(f)
    code, loc = f.f_code, info.locals
    params = [a for a in info.args if a not in ("self", "cls")]
    passed, src = set(params), {}
    fb = f.f_back
    call = _call_node(fb)
    callee = getattr(call.func, "attr", getattr(call.func, "id", None)) if call else None
    if call is not None and fb is not None and callee == code.co_name:  # otherwise (partial, alias, ...)
        positional = [a for a in info.args[: code.co_argcount] if a not in ("self", "cls")]  # positions untrusted
        starred = any(isinstance(a, ast.Starred) for a in call.args)
        passed = set(positional if starred else positional[: len(call.args)])
        if not starred:
            src = {a: ast.unparse(e) for a, e in zip(positional, call.args)}
        for kw in call.keywords:
            if kw.arg:
                passed.add(kw.arg)
                src[kw.arg] = ast.unparse(kw.value)
            else:  # **mapping: its keys were passed
                d = None
                if isinstance(kw.value, ast.Name):
                    d = fb.f_locals.get(kw.value.id, fb.f_globals.get(kw.value.id))
                passed |= set(d) if isinstance(d, Mapping) else set(params)
    args: list[tuple[str | None, object]] = [(a, loc[a]) for a in params if a in passed and a in loc]
    if info.varargs:
        args += [(None, v) for v in loc.get(info.varargs, ())]
    if info.keywords:
        args += list(loc.get(info.keywords, {}).items())
    return args, src


def proto_var_name(obj) -> str | None:
    """Proto name (``v1``, ``a2``) of a QUA variable or array object, else None."""
    if not isinstance(obj, QuaExpression):
        return None
    e = obj._expression
    if e.DESCRIPTOR.name == "ArrayVarRefExpression":
        return e.name
    if e.DESCRIPTOR.name == "AnyScalarExpression" and e.WhichOneof("expression_oneof") == "variable":
        return e.variable.name
    return None


class Tracer:
    """Patches qm while active (use as a context manager); results stay available afterwards."""

    def __init__(self) -> None:
        self.program: Any = None  # qm Program, set when q.program() exits
        self.name = "program"  # name of the function that built it
        self.traces: list[tuple[int, ...]] = []  # call ids, program frame first
        self.apis: list[str] = []  # by trace: the qm function the user code called (frame_rotation, ...)
        self.calls: list[Call] = []  # by call id
        self.names: dict[str, str] = {}  # proto variable name -> user-facing Python name
        self._frames: list[FrameType] = []  # by call id; strong refs so id(frame) is never reused
        self._ids: dict[int, int] = {}
        self._user: dict[str, bool] = {}
        self._root: FrameType | None = None
        self._restore: list = []

    def _user_frame(self, f: FrameType) -> bool:
        fn = f.f_code.co_filename
        if fn not in self._user:
            self._user[fn] = _is_user_file(fn)
        return self._user[fn]

    def get_loc(self) -> str:
        chain: list[int] = []
        api = ""
        f: FrameType | None = sys._getframe(1)
        while f is not None:
            if not chain and not self._user_frame(f):
                api = f.f_code.co_name
            if self._user_frame(f) and not f.f_code.co_name.startswith("<"):  # skip <lambda>, <genexpr>
                cid = self._ids.get(id(f))
                if cid is None:
                    cid = self._ids[id(f)] = len(self._frames)
                    self._frames.append(f)
                    args, src = _passed_args(f) if f is not self._root else ([], {})
                    self.calls.append(Call(f.f_code.co_name, args, 0, src))
                chain.append(cid)
            if f is self._root:
                break
            f = f.f_back
        chain.reverse()
        for depth, cid in enumerate(chain):
            self.calls[cid].depth = depth
        self.traces.append(tuple(chain))
        self.apis.append(api)
        return f"#trace={len(self.traces) - 1}"

    def trace_id(self, loc: str) -> int | None:
        m = _TRACE_RE.search(loc or "")
        return int(m.group(1)) if m else None

    def stack_of(self, loc: str) -> tuple[int, ...]:
        i = self.trace_id(loc)
        return () if i is None else self.traces[i]

    def _patch(self, owner, name, value) -> None:
        self._restore.append((owner, name, getattr(owner, name)))
        setattr(owner, name, value)

    def __enter__(self):
        try:
            self._install()
        except BaseException:  # e.g. an incompatible qm version: leave qm untouched
            self.__exit__(None, None, None)
            raise
        return self

    def _install(self) -> None:
        if _loc_mod._get_loc is not _ORIG_GET_LOC:
            raise RuntimeError("qm_circuit: a capture is already active (captures cannot be nested)")
        tracer = self
        for name, mod in list(sys.modules.items()):
            if (name == "qm" or name.startswith("qm.")) and getattr(mod, "_get_loc", None) is _ORIG_GET_LOC:
                self._patch(mod, "_get_loc", self.get_loc)

        orig_for_create, orig_elif_init = _scopes._ForScope._create_statement, _scopes._ElifScope.__init__
        orig_enter, orig_exit = _ProgramScope.__enter__, _ProgramScope.__exit__

        def for_create(scope):
            st = orig_for_create(scope)
            getattr(st, "for").loc = scope._loc
            return st

        def elif_init(scope, condition, if_statement, loc):
            orig_elif_init(scope, condition, if_statement, tracer.get_loc())

        def program_enter(scope):
            f = sys._getframe(1)
            while f is not None and not tracer._user_frame(f):
                f = f.f_back
            tracer._root = f
            return orig_enter(scope)

        def program_exit(scope, exc_type, exc, tb):
            result = orig_exit(scope, exc_type, exc, tb)
            if exc_type is None and tracer.program is None:
                tracer.program = scope._program
                tracer.name = tracer._root.f_code.co_name if tracer._root else "program"
                tracer._scan_names()
                raise _Captured
            return result

        self._patch(_scopes._ForScope, "_create_statement", for_create)
        self._patch(_scopes._ElifScope, "__init__", elif_init)
        self._patch(_ProgramScope, "__enter__", program_enter)
        self._patch(_ProgramScope, "__exit__", program_exit)

    def __exit__(self, exc_type, exc, tb):
        for owner, name, value in reversed(self._restore):
            setattr(owner, name, value)
        self._restore.clear()
        self._frames.clear()
        self._ids.clear()
        self._root = None
        return exc_type is _Captured

    def _scan_names(self) -> None:
        """Map proto variable names to Python names, preferring the outermost frame that holds them."""
        frames = sorted(zip(self._frames, self.calls), key=lambda fc: fc[1].depth)
        for f in [self._root, *(fr for fr, _ in frames)]:
            for k, v in (f.f_locals.items() if f is not None else ()):
                n = proto_var_name(v)
                if n and not k.startswith("_"):
                    self.names.setdefault(n, k)
