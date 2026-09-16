"""Debug-only overlap check for qm_circuit figures (uses the renderer's gid tags).

``save(fig, path)`` saves the figure, then reports:
- text vs text: any intersection;
- text vs patch: text must be fully inside its own box or a container (region / if box); any other contact;
- text vs line: text crossing a line, unless an opaque box above that line fully covers the text;
- box vs box (non-containers, different nodes) and connector lines crossing another node's box;
- repeat-sign dots vs any text or non-container box.
"""

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.lines import Line2D
from matplotlib.transforms import Bbox

TOL = 0.5  # px
RESULTS: dict[str, int] = {}


def _shrink(b: Bbox, d: float = TOL) -> Bbox:
    return Bbox([[b.x0 + d, b.y0 + d], [b.x1 - d, b.y1 - d]])


def _inside(a: Bbox, b: Bbox) -> bool:
    return a.x0 >= b.x0 - TOL and a.x1 <= b.x1 + TOL and a.y0 >= b.y0 - TOL and a.y1 <= b.y1 + TOL


def _hits_line(b: Bbox, line: Line2D) -> bool:
    (x0, y0), (x1, y1) = line.get_transform().transform(line.get_xydata())[[0, -1]]
    lw = line.get_linewidth() * line.figure.dpi / 72 / 2
    seg = Bbox([[min(x0, x1) - lw, min(y0, y1) - lw], [max(x0, x1) + lw, max(y0, y1) + lw]])
    return b.overlaps(seg)


def check(fig) -> list[str]:
    ax = fig.axes[0]
    canvas = FigureCanvasAgg(fig)
    canvas.draw()
    r = canvas.get_renderer()
    texts = [(t, _shrink(t.get_window_extent(r))) for t in ax.texts if t.get_text()]
    patches = [(p, p.get_window_extent(r)) for p in ax.patches]
    containers = {id(p) for p, _ in patches if p.get_zorder() < 1}
    lines = [ln for ln in ax.lines]
    dots = []  # (gid, bbox) per scatter point
    for col in ax.collections:
        d = (col.get_sizes()[0] ** 0.5 if len(col.get_sizes()) else 0) * fig.dpi / 72 / 2
        for x, y in col.get_offset_transform().transform(col.get_offsets()):
            dots.append((col.get_gid(), Bbox([[x - d, y - d], [x + d, y + d]])))
    out = []
    name = lambda a: repr(a.get_text()) if hasattr(a, "get_text") else type(a).__name__  # noqa: E731
    for i, (t, tb) in enumerate(texts):
        for u, ub in texts[i + 1 :]:
            if tb.overlaps(ub):
                out.append(f"text {name(t)} x text {name(u)}")
        for p, pb in patches:
            if not tb.overlaps(pb):
                continue
            if (p.get_gid() == t.get_gid() or id(p) in containers) and _inside(tb, pb):
                continue
            out.append(f"text {name(t)} x patch {p.get_gid()}{' (own, sticks out)' if p.get_gid() == t.get_gid() else ''}")
        for ln in lines:
            if not _hits_line(tb, ln):
                continue
            covered = any(p.get_zorder() > ln.get_zorder() and p.get_facecolor()[3] > 0 and _inside(tb, pb)
                          for p, pb in patches)
            if not covered:
                out.append(f"text {name(t)} x line {ln.get_gid()}")
    for gid, db in dots:
        out += [f"dot {gid} x text {name(t)}" for t, tb in texts if tb.overlaps(db)]
        out += [f"dot {gid} x patch {p.get_gid()}" for p, pb in patches
                if id(p) not in containers and _shrink(pb).overlaps(db)]
    for i, (p, pb) in enumerate(patches):
        if id(p) in containers:
            continue
        for q, qb in patches[i + 1 :]:
            if id(q) not in containers and q.get_gid() != p.get_gid() and _shrink(pb).overlaps(_shrink(qb)):
                out.append(f"patch {p.get_gid()} x patch {q.get_gid()}")
        for ln in lines:
            if ln.get_gid() not in ("lane", p.get_gid()) and _hits_line(_shrink(pb), ln):
                out.append(f"patch {p.get_gid()} x line {ln.get_gid()}")
    return out


def save(fig, path) -> int:
    fig.savefig(path)
    problems = check(fig)
    RESULTS[str(path)] = len(problems)
    print(f"[overlap] {path.name if hasattr(path, 'name') else path}: {len(problems)}")
    for p in problems[:20]:
        print("    ", p)
    return len(problems)
