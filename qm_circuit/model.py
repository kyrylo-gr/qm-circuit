"""Renderer-independent circuit model of a QUA program (a small dataclass tree)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Play:
    element: str
    pulse: str
    params: dict[str, str] = field(default_factory=dict)  # only explicitly given params
    measure: bool = False


@dataclass
class Wait:
    targets: list[str]
    duration: str


@dataclass
class Align:
    targets: list[str]  # empty = every lane of the enclosing region


@dataclass
class Op:
    """Other instruction: element-bound (update_frequency, ...) or, with no targets, a marker (pause, save)."""

    name: str
    targets: list[str]
    args: str = ""


@dataclass
class Loop:
    kind: str  # "for" | "while" | "for_each"
    header: str
    body: list = field(default_factory=list)


@dataclass
class Branch:
    label: str  # "if x > 0", "elif ...", "else"
    body: list = field(default_factory=list)


@dataclass
class If:
    branches: list[Branch] = field(default_factory=list)


@dataclass
class Block:
    """Statements of one user helper call (collapsible), or a QUA scope such as strict_timing_ (``scope``)."""

    func: str
    params: list[str]  # "k=value" as passed at the call site
    body: list = field(default_factory=list)
    scope: bool = False


@dataclass
class Program:
    name: str
    lanes: list[str]
    body: list = field(default_factory=list)


def children(node) -> list:
    if isinstance(node, If):
        return [n for b in node.branches for n in b.body]
    return getattr(node, "body", [])


def elements(node) -> list[str]:
    """Element names (lanes) a node touches, in first-use order."""
    if isinstance(node, Play):
        return [node.element]
    if isinstance(node, (Wait, Align, Op)):
        return list(node.targets)
    out: list[str] = []
    for n in children(node):
        out += [e for e in elements(n) if e not in out]
    return out


def format_model(node, indent: int = 0) -> str:
    """Readable text dump of the model tree."""
    pad = "  " * indent
    if isinstance(node, Program):
        head = f"Program {node.name}  lanes: {', '.join(node.lanes)}"
    elif isinstance(node, Play):
        params = ", ".join(f"{k}={v}" for k, v in node.params.items())
        head = f"{'Measure' if node.measure else 'Play'} {node.element}: {node.pulse}{f' [{params}]' if params else ''}"
    elif isinstance(node, Wait):
        head = f"Wait {', '.join(node.targets) or '(all)'}: {node.duration}"
    elif isinstance(node, Align):
        head = f"Align {', '.join(node.targets) or '(all)'}"
    elif isinstance(node, Op):
        head = f"Op {node.name} {', '.join(node.targets) or '(marker)'}: {node.args}"
    elif isinstance(node, Loop):
        head = f"Loop {node.header}"
    elif isinstance(node, Block):
        head = f"{'Scope' if node.scope else 'Block'} {node.func}({', '.join(node.params)})"
    elif isinstance(node, If):
        lines = [pad + "If"]
        for b in node.branches:
            lines.append(pad + f"  {b.label}")
            lines += [format_model(n, indent + 2) for n in b.body]
        return "\n".join(lines)
    else:
        head = repr(node)
    return "\n".join([pad + head, *(format_model(n, indent + 1) for n in children(node))])
