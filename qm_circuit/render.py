"""Matplotlib renderer: one lane per element, schematic x axis (program order, not time).

Layout is in inches (1 data unit = 1 inch), so text sizes can be measured and the figure size follows
the content; every length comes from :mod:`.style` in em. Labels drawn above a region (loop headers,
block labels, marker labels) get vertical room reserved just above the region's top lane, so they
never cross other lanes, and each node only claims horizontal room on the lanes it spans.
Every artist carries a ``gid`` naming the node it belongs to (used by overlap checks).
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np

from matplotlib.backends.backend_agg import RendererAgg
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from matplotlib.patches import FancyBboxPatch, Rectangle

from .icons import ICONS
from .model import Align, Block, If, Loop, Op, Play, Program, Wait, children, elements
from .style import Style, make_style


@lru_cache(maxsize=None)
def _measurer(dpi: int) -> RendererAgg:
    return RendererAgg(10, 10, dpi)  # same dpi as the figure: Agg glyph advances are pixel-rounded


@lru_cache(maxsize=None)
def text_w(s: str, points: float, family: str, weight: str, dpi: int) -> float:
    """Rendered text width in inches."""
    if not s:
        return 0.0
    prop = FontProperties(family=family, weight=weight, size=points)
    return _measurer(dpi).get_text_width_height_descent(s, prop, False)[0] / dpi


def wrap(parts: list[str], width: int) -> list[str]:
    """Greedy ``", "``-joined lines of at most ``width`` chars (a single long part gets its own line)."""
    lines: list[str] = []
    for i, p in enumerate(parts):
        p += "," if i < len(parts) - 1 else ""
        if lines and len(lines[-1]) + 1 + len(p) <= width:
            lines[-1] += " " + p
        else:
            lines.append(p)
    return lines


def is_open(n, expand: bool) -> bool:
    return isinstance(n, (Loop, If)) or isinstance(n, Block) and (expand or n.scope)


def elide(lines: list[str], n: int) -> list[str]:
    """At most ``n`` lines; the last kept one ends with ``...`` when some were dropped."""
    return lines if len(lines) <= n else lines[: n - 1] + [lines[n - 1].rstrip(",") + ", ..."]


def label_lines(n, width: int, max_lines: int) -> list[str]:
    """Label rows drawn at the top of an open region."""
    if isinstance(n, Loop):
        return [n.header]
    if isinstance(n, If):
        return [""]  # branch labels share one row
    if not n.params:
        return [n.func if n.scope else f"{n.func}()"]
    parts = list(n.params)
    parts[0] = f"{n.func}(" + parts[0]
    parts[-1] += ")"
    return elide(wrap(parts, width), max_lines)


def all_lanes(n) -> bool:
    """``align()`` / ``wait(t)`` without elements act on every element of the program: so does any node holding one."""
    return isinstance(n, (Align, Wait)) and not n.targets or any(all_lanes(c) for c in children(n))


def runs(indices: list[int]) -> list[list[int]]:
    """Split sorted lane indices into runs of adjacent lanes."""
    out: list[list[int]] = []
    for i in indices:
        if out and i == out[-1][-1] + 1:
            out[-1].append(i)
        else:
            out.append([i])
    return out


class _Layout:
    def __init__(self, ax, lanes: list[str], body: list, expand: bool, s: Style, top: float = 0.0):
        """Lay out ``body`` with its highest drawing at y = ``top``."""
        self.ax, self.lanes, self.expand, self.s = ax, lanes, expand, s
        self.cur = {ln: 0.0 for ln in lanes}
        self.xmax = 0.0
        self.above = {ln: 0.0 for ln in lanes}  # room reserved above / below each lane's band
        self.below = {ln: 0.0 for ln in lanes}
        self.reserve(body, lanes)
        self.y, y = {}, 0.0
        for i, ln in enumerate(lanes):
            if i:
                clear = max(s.em(s.lane_clear), self.below[lanes[i - 1]] + self.above[ln] + s.em(s.min_clear))
                y -= s.em(s.box_h) + clear
            self.y[ln] = y
        shift = top - self.top(lanes) - self.above[lanes[0]]
        self.y = {ln: y + shift for ln, y in self.y.items()}
        self.ymax, self.ymin = top, self.bottom(lanes) - self.below[lanes[-1]]

    # ------------------------------------------------------------ geometry

    def span(self, n, ctx: list[str]) -> list[str]:
        """Contiguous lanes from the first to the last touched one (``ctx`` if the node touches none)."""
        if all_lanes(n):
            return self.lanes
        idx = sorted(self.lanes.index(e) for e in elements(n))
        return self.lanes[idx[0] : idx[-1] + 1] if idx else ctx

    def top(self, lanes) -> float:
        return max(self.y[ln] for ln in lanes) + self.s.em(self.s.box_h) / 2

    def bottom(self, lanes) -> float:
        return min(self.y[ln] for ln in lanes) - self.s.em(self.s.box_h) / 2

    def stack(self, n, ctx, up: bool) -> float:
        """Height drawn beyond the band of the node's top (``up``) or bottom lane."""
        s = self.s
        if is_open(n, self.expand):
            span = self.span(n, ctx)
            end = 0 if up else -1
            inner = max((self.stack(c, span, up) for c in children(n) if self.span(c, span)[end] == span[end]),
                        default=0.0)
            rows = len(label_lines(n, s.label_chars, s.label_lines)) if up else 0
            return inner + s.em(s.edge) + rows * s.em(s.row)
        if isinstance(n, Block):
            return s.em(s.edge)
        if isinstance(n, Op) and not n.targets:
            return s.em(s.row) if up else 0.0
        return 0.0

    def reserve(self, nodes: list, ctx: list[str]) -> None:
        for n in nodes:
            span = self.span(n, ctx)
            self.above[span[0]] = max(self.above[span[0]], self.stack(n, ctx, True))
            self.below[span[-1]] = max(self.below[span[-1]], self.stack(n, ctx, False))
            if is_open(n, self.expand):
                self.reserve(children(n), span)

    def x_at(self, lanes) -> float:
        return max(self.cur[ln] for ln in lanes) + self.s.em(self.s.gap)

    def advance(self, lanes, x: float) -> None:
        for ln in lanes:
            self.cur[ln] = max(self.cur[ln], x)
        self.xmax = max(self.xmax, x)

    def between(self, touched) -> list[str]:
        """Untouched lanes inside the span of ``touched`` (crossed by connector lines)."""
        idx = [self.lanes.index(t) for t in touched]
        return [ln for ln in self.lanes[min(idx) : max(idx) + 1] if ln not in touched]

    # ------------------------------------------------------------ primitives

    def tw(self, text: str, font: float, family: str, weight: str | None = None) -> float:
        return text_w(text, self.s.pt(font), family, weight or self.s.regular, self.s.dpi)

    def text(self, x, y, text, font, family, gid, **kw):
        kw.setdefault("color", self.s.colors["text"])
        kw.setdefault("fontweight", self.s.regular)
        kw.setdefault("ha", "center")
        kw.setdefault("va", "center")
        self.ax.text(x, y, text, fontsize=self.s.pt(font), family=family, zorder=self.s.z_text, gid=gid, **kw)

    def rbox(self, x, y, w, h, gid, **kw):
        style = f"round,pad=0,rounding_size={self.s.em(self.s.rounding)}"
        self.ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=style, gid=gid, **kw))

    def vline(self, x, y0, y1, gid, lw, **kw):
        self.ax.plot([x, x], [y0, y1], solid_capstyle="butt", linewidth=self.s.pt(lw), gid=gid, **kw)

    # ------------------------------------------------------------ placement

    def place(self, nodes: list, ctx: list[str], level: int = 0) -> None:
        s, c = self.s, self.s.colors
        for n in nodes:
            span = self.span(n, ctx)
            hi, lo = self.top(span) + self.stack(n, ctx, True), self.bottom(span) - self.stack(n, ctx, False)
            gid = f"node{id(n)}"
            if isinstance(n, Play):
                self.play(n, gid)
            elif isinstance(n, Wait):
                self.small_boxes(n.targets or ctx, "wait", n.duration, c["wait"], c["wait_fill"], s.dash_wait, gid,
                                 color=c["muted"])
            elif isinstance(n, Op) and n.targets:
                self.small_boxes(n.targets, n.name, n.args, c["op_edge"], c["op_fill"], s.dash_op, gid)
            elif isinstance(n, Op):
                self.marker(n, ctx, gid)
            elif isinstance(n, Align):
                self.align(n, ctx, gid)
            elif is_open(n, self.expand):
                self.region(n, span, hi, lo, level, gid)
            elif isinstance(n, Block):
                self.block(n, ctx, gid)

    def icon_w(self, icon: str | None, lines: list, h: float) -> float:
        """Box width for an icon, a separator and text ``lines`` of ``(text, font, family, weight, color)``."""
        s = self.s
        text = max((self.tw(t, f, fam, wt) for t, f, fam, wt, _ in lines), default=0.0)
        if icon is None:
            return text + 2 * s.em(s.pad)
        return h * s.icon + 2 * s.em(s.pad) + (text + 2 * s.em(s.pad) if lines else 0.0)

    def icon_content(self, x, y, w, h, icon: str | None, lines: list, dys: tuple, ink, gid) -> None:
        """Icon on the left, a separator, then the text lines centered in the remaining width."""
        s = self.s
        x_text = x
        if icon is not None:
            size = h * s.icon
            x0, y0 = x + s.em(s.pad), y - size / 2
            for xs, ys in ICONS[icon]:
                self.ax.plot(x0 + size * np.asarray(xs), y0 + size * np.asarray(ys), color=ink, gid=gid,
                             linewidth=s.pt(s.lw_icon), solid_capstyle="round", solid_joinstyle="round",
                             zorder=s.z_text)
            x_text = x0 + size + s.em(s.pad)
            if lines:
                sep = h * s.separator / 2
                self.vline(x_text, y - sep, y + sep, gid, s.lw_separator, color=ink, alpha=0.5, zorder=s.z_text)
        cx = (x_text + x + w) / 2
        offsets = [0.0] if len(lines) == 1 else [s.em(dys[0]), -s.em(dys[1])]
        for (text, font, family, weight, color), dy in zip(lines, offsets):
            self.text(cx, y + dy, text, font, family, gid, fontweight=weight, color=color)

    def play(self, n: Play, gid) -> None:
        s, c = self.s, self.s.colors
        params = ", ".join(f"{k}={v}" for k, v in n.params.items())
        lines = [(n.pulse, s.font_pulse, s.sans, s.bold, c["pulse_text"])]
        if params:
            lines.append((params, s.font_param, s.mono, s.regular, c["param_text"]))
        icon = "measure" if n.measure else "play"
        x, y, h = self.x_at([n.element]), self.y[n.element], s.em(s.box_h)
        w = max(self.icon_w(icon, lines, h), self.icon_w(icon, [], h) + s.em(s.min_text_w) + 2 * s.em(s.pad))
        fill = c["measure" if n.measure else "pulse"]
        self.rbox(x, y - h / 2, w, h, gid, facecolor=fill, edgecolor=c["pulse_edge"], zorder=s.z_box)
        self.icon_content(x, y, w, h, icon, lines, (s.pulse_title_dy, s.pulse_param_dy), c["pulse_text"], gid)
        self.advance([n.element], x + w)

    def small_boxes(self, targets, name, args, edge, fill, dash, gid, color=None) -> None:
        """Same-width boxes at one x on each target lane (wait, update_frequency, ...).

        With an icon for ``name``: icon, then ``args`` if any. Without: ``name`` in bold above ``args``.
        """
        s = self.s
        icon = name if name in ICONS else None
        sub = (args, s.font_small_sub if icon is None else s.font_small, s.mono, s.regular, color or edge)
        lines = [sub] if args else []
        if icon is None:
            lines.insert(0, (name, s.font_small, s.sans, s.bold, edge))
        x, h = self.x_at(targets), s.em(s.small_box_h)
        w = self.icon_w(icon, lines, h)
        for t in targets:
            y = self.y[t]
            self.rbox(x, y - h / 2, w, h, gid, facecolor=fill, edgecolor=edge, linewidth=s.pt(s.lw_box),
                      linestyle=dash, zorder=s.z_box)
            self.icon_content(x, y, w, h, icon, lines, (s.small_title_dy, s.small_sub_dy), edge, gid)
        self.advance(targets, x + w)

    def marker(self, n: Op, ctx, gid) -> None:
        """Element-less instruction (pause, save): a vertical line over the region, label on top."""
        s = self.s
        label = f"{n.name} {n.args}".strip()
        w = self.tw(label, s.font_param, s.mono)
        x = self.x_at(ctx) + w / 2
        self.vline(x, self.bottom(ctx), self.top(ctx), gid, s.lw_marker, color=s.colors["op_edge"], zorder=s.z_line)
        self.text(x, self.top(ctx) + s.em(s.label_dy), label, s.font_param, s.mono, gid, va="bottom",
                  color=s.colors["op_edge"])
        self.advance(ctx, x + w / 2)

    def align(self, n: Align, ctx, gid) -> None:
        s = self.s
        touched = n.targets or ctx
        crossed = self.between(touched)
        x = self.x_at(touched + crossed)
        segs = runs(sorted(self.lanes.index(t) for t in touched))
        style = dict(color=s.colors["align"], zorder=s.z_line)
        for i, seg in enumerate(segs):
            lanes = [self.lanes[j] for j in seg]
            y0, y1 = self.bottom(lanes) - s.em(s.overhang), self.top(lanes) + s.em(s.overhang)
            self.vline(x, y0, y1, gid, s.lw_align, linestyle=s.dash_align, **style)
            if i:
                prev = [self.lanes[segs[i - 1][-1]]]
                self.vline(x, y1, self.bottom(prev) - s.em(s.overhang), gid, s.lw_align_link,
                           linestyle=s.dash_align_link, **style)
        self.advance(touched + crossed, x)

    def block(self, n: Block, ctx, gid) -> None:
        """Collapsed helper: one box per run of adjacent touched lanes, joined by a thin connector."""
        s = self.s
        touched = [ln for ln in self.lanes if ln in elements(n)] or ctx
        if all_lanes(n):  # the helper synchronises every lane: one box over its whole span
            touched = self.span(n, ctx)
        segs = [[self.lanes[j] for j in r] for r in runs([self.lanes.index(t) for t in touched])]
        main = max(segs, key=len)
        edge = s.em(s.edge)
        fit = max(1, int((self.top(main) - self.bottom(main) + 2 * edge - s.em(s.block_text_margin)) / s.em(s.line)))
        width = s.block_chars
        lines = wrap(n.params, width)
        while len(lines) > fit and width < s.block_chars_max:
            width += s.block_chars_step
            lines = wrap(n.params, width)
        lines = elide(lines, fit)
        w = max(self.tw(n.func, s.font_block, s.sans, s.bold), *(self.tw(ln, s.font_param, s.mono) for ln in lines),
                0) + 2 * s.em(s.pad)
        crossed = self.between(touched)
        x = self.x_at(touched)
        if crossed:  # the connector at the box center must clear the crossed lanes
            x = max(x, self.x_at(crossed) - w / 2)
        for i, seg in enumerate(segs):
            y0, y1 = self.bottom(seg) - edge, self.top(seg) + edge
            self.rbox(x, y0, w, y1 - y0, gid, facecolor=s.colors["block_fill"], edgecolor=s.colors["block_edge"],
                      linewidth=s.pt(s.lw_block), zorder=s.z_box)
            if i:
                self.vline(x + w / 2, y1, self.bottom(segs[i - 1]) - edge, gid, s.lw_connector,
                           color=s.colors["block_edge"], zorder=s.z_line)
            text = lines if seg is main else []
            ym = (y0 + y1) / 2 + s.em(s.line) * len(text) / 2
            self.text(x + w / 2, ym, n.func, s.font_block, s.sans, gid, fontweight=s.bold)
            for k, ln in enumerate(text):
                self.text(x + w / 2, ym - s.em(s.block_title_dy) - s.em(s.line) * k, ln, s.font_param, s.mono, gid,
                          color=s.colors["muted"])
        self.advance(touched, x + w)
        self.advance(crossed, x + w / 2)

    def repeat(self, x: float, lanes, dots, y0: float, y1: float, start: bool, gid) -> float:
        """Musical repeat sign (start: thick|thin:, end: :thin|thick); returns its width."""
        s = self.s
        e = s.em
        w = e(s.repeat_w)
        thick, thin, dot = (e(s.repeat_thick), e(s.repeat_thin), e(s.repeat_dot))
        if not start:
            thick, thin, dot = w - thick, w - thin, w - dot
        bar = dict(color=s.colors["bar"], zorder=s.z_bar)
        self.vline(x + thick, y0, y1, gid, s.lw_bar_thick, **bar)
        self.vline(x + thin, y0, y1, gid, s.lw_bar_thin, **bar)
        ys = [self.y[ln] + d for ln in lanes if ln in dots for d in (e(s.repeat_dot_dy), -e(s.repeat_dot_dy))]
        self.ax.scatter([x + dot] * len(ys), ys, s=s.pt(s.dot) ** 2, linewidths=0, gid=gid, **bar)
        return w

    def region(self, n, span, hi, lo, level: int, gid) -> None:
        """Loop (repeat signs), if (tinted box with branches) or open block (dashed box, label on top)."""
        s, c, e = self.s, self.s.colors, self.s.em
        z = s.z_region + s.z_region_step * level
        lines = label_lines(n, s.label_chars, s.label_lines)
        row_y = [hi - (i + 1) * e(s.row) + e(s.label_dy) for i in range(len(lines))]
        x0 = self.x_at(span)
        label_w = max(self.tw(ln, s.font_small, s.mono) for ln in lines)
        if isinstance(n, Loop):
            dots = span if all_lanes(n) else elements(n) or span
            w = self.repeat(x0, span, dots, lo, hi, True, gid)
            self.text(x0 + w + e(s.repeat_label), row_y[0], n.header, s.font_small, s.mono, gid, ha="left",
                      va="bottom")
            self.advance(span, x0 + w)
            self.place(n.body, span, level + 1)
            x1 = max(self.x_at(span), x0 + w + e(s.repeat_label) + label_w + e(s.label_tail))
            self.advance(span, x1 + self.repeat(x1, span, dots, lo, hi, False, gid))
        elif isinstance(n, If):
            x = x0
            for i, b in enumerate(n.branches):
                if i:
                    self.vline(x, lo, hi, gid, s.lw_box, color=c["if_edge"], linestyle=s.dash_branch,
                               zorder=z + s.z_region_step / 2)  # above this box's fill, below nested regions
                self.text(x + e(s.label_inset), row_y[0], b.label, s.font_small, s.mono, gid, ha="left", va="bottom",
                          color=c["if_text"])
                self.advance(span, x)
                self.place(b.body, span, level + 1)
                label_end = x + e(s.label_inset) + self.tw(b.label, s.font_small, s.mono) + e(s.label_tail)
                x = max(self.x_at(span), label_end)
            self.ax.add_patch(Rectangle((x0, lo), x - x0, hi - lo, facecolor=c["if_fill"], edgecolor=c["if_edge"],
                                        linewidth=s.pt(s.lw_box), zorder=z, gid=gid))
            self.advance(span, x)
        else:
            self.advance(span, x0)
            self.place(n.body, span, level + 1)
            x1 = max(self.x_at(span), x0 + e(s.label_inset) + label_w + e(s.label_tail))
            self.rbox(x0, lo, x1 - x0, hi - lo, gid, facecolor=c["region_fill"], edgecolor=c["region_edge"],
                      linewidth=s.pt(s.lw_box), linestyle=s.dash_region, zorder=z)
            for y, ln in zip(row_y, lines):
                self.text(x0 + e(s.label_inset), y, ln, s.font_small, s.mono, gid, ha="left", va="bottom",
                          color=c["block_edge"])
            self.advance(span, x1)


def rows(body: list, lanes: list[str], expand: bool, s: Style, max_width: float | None) -> list[list]:
    """Split top-level statements into rows at most ``max_width`` inches wide (a wider single item keeps its row)."""
    if max_width is None:
        return [body]
    lay = _Layout(Figure().add_axes((0, 0, 1, 1)), lanes, body, expand, s)  # dry run to measure
    out: list[list] = [[]]
    start = 0.0
    for n in body:
        before = lay.xmax
        lay.place([n], lanes)
        if out[-1] and lay.xmax - start > max_width:
            out.append([])
            start = before
        out[-1].append(n)
    return out


def render(program: Program, expand: bool = False, title: str | None = None, style: Style | dict | None = None,
           max_width: float | None = None) -> Figure:
    """Draw a :class:`Program` model. ``expand=True`` shows helper-block contents instead of one box.

    ``max_width`` (inches): wrap top-level statements into several rows of lanes (each row restarts at x=0).
    """
    s = make_style(style)
    e = s.em
    lanes = program.lanes or ["(no elements)"]
    fig = Figure(dpi=s.dpi)
    fig.patch.set_facecolor(s.colors["background"])
    ax = fig.add_axes((0, 0, 1, 1))
    ax.axis("off")
    lays, top = [], 0.0
    for body in rows(program.body, lanes, expand, s, max_width):
        lays.append(_Layout(ax, lanes, body, expand, s, top))
        lays[-1].place(body, lanes)
        top = lays[-1].ymin - e(s.row_gap)

    title = program.name if title is None else title
    name_w = max(lays[0].tw(ln, s.font_lane, s.mono, s.bold) for ln in lanes)
    xmin, xmax = -name_w - e(s.lane_name_gap) - e(s.margin_left), max(lay.xmax for lay in lays) + e(s.margin_right)
    ymax = e(s.margin_top) + (e(s.title_h) if title else 0)
    ymin = lays[-1].ymin - e(s.margin_bottom)
    fig.set_size_inches(xmax - xmin, ymax - ymin)
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    for lay in lays:
        for ln in lanes:
            y = lay.y[ln]
            ax.plot([-e(s.lane_start), xmax - e(s.lane_end)], [y, y], color=s.colors["lane"],
                    linewidth=s.pt(s.lw_lane), zorder=s.z_lane, gid="lane")
            ax.text(-e(s.lane_name_gap), y, ln, ha="right", va="center", fontsize=s.pt(s.font_lane),
                    fontweight=s.bold, family=s.mono, color=s.colors["text"], gid="lane")
    if title:
        ax.text(xmin + e(s.title_x), ymax - e(s.title_y), title, ha="left", va="top", fontsize=s.pt(s.font_title),
                fontweight=s.bold, family=s.sans, color=s.colors["text"], gid="title")
    return fig
