"""Every visual constant of the renderer, in one theme.

All lengths, font sizes and line widths are in *em*: multiples of ``size`` (the base font size, points).
One em is ``size`` points of line width or font size, and ``size / 72`` inches of geometry, so changing
``size`` scales the whole diagram consistently. ``draw(..., style=Style(size=10))`` or
``draw(..., style={"size": 10, "colors": {"pulse": "#c03"}})`` overrides fields (colors are merged).
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, replace

COLORS = dict(
    background="white", text="#222222", muted="#666666", lane="#d0d0d0",
    pulse="#4a3fd1", pulse_edge="none", measure="#0d8a7c", pulse_text="white", param_text="#e8e8ff",
    wait="#6b6b6b", wait_fill="white", op_fill="#fbeed9", op_edge="#b4700f",
    block_fill="#eceef6", block_edge="#4b5170", region_fill="#f5f6fb", region_edge="#9aa0b8",
    if_fill="#fff7e0", if_edge="#c99a1a", if_text="#7a5a00", bar="#2b2b2b", align="#8a8a8a",
)


@dataclass(frozen=True)
class Style:
    size: float = 8.0  # base font size in points = 1 em
    dpi: int = 150
    sans: str = "DejaVu Sans"  # bundled with matplotlib
    mono: str = "DejaVu Sans Mono"
    regular: str = "normal"  # font weights
    bold: str = "bold"
    colors: dict = field(default_factory=lambda: dict(COLORS))

    # font sizes (em)
    font_title: float = 1.5
    font_lane: float = 1.3125
    font_pulse: float = 1.25
    font_param: float = 0.9375  # pulse parameters, collapsed-block arguments, marker labels
    font_small: float = 1.0  # wait / op titles, region labels
    font_small_sub: float = 0.875
    font_block: float = 1.1875

    # vertical geometry (em)
    box_h: float = 4.7  # pulse box height = the band a lane occupies
    small_box_h: float = 3.3  # wait / op boxes
    lane_clear: float = 4.8  # free space between the bands of adjacent lanes (grows when labels need room)
    min_clear: float = 1.1  # least free space between decorations of adjacent lanes
    row: float = 1.7  # one label row above a region / marker
    line: float = 1.25  # line height of parameter text
    edge: float = 0.9  # how far blocks and regions reach beyond their lanes' bands
    overhang: float = 0.55  # align lines beyond the lane band
    pulse_title_dy: float = 0.72  # pulse name above center when parameters are shown
    pulse_param_dy: float = 1.08  # parameters below center
    small_title_dy: float = 0.63
    small_sub_dy: float = 0.81
    block_title_dy: float = 1.7  # first argument line below the block name
    label_dy: float = 0.45  # label baseline above its row bottom
    icon: float = 0.5  # icon square side, as a fraction of its box height
    separator: float = 0.6  # icon / text separator length, as a fraction of the box height
    block_text_margin: float = 2.7  # vertical room of a collapsed block not usable for argument lines

    # horizontal geometry (em)
    gap: float = 1.2  # between consecutive items on a lane
    pad: float = 1.0  # text padding inside boxes
    min_text_w: float = 3.25  # least text width of a pulse box
    label_inset: float = 0.72  # region label from the region's left edge
    label_tail: float = 1.8  # room after a region label
    rounding: float = 0.45
    repeat_thick: float = 0.225  # repeat sign: thick bar, thin bar, dots offsets and total width
    repeat_thin: float = 0.9
    repeat_dot: float = 1.53
    repeat_w: float = 1.98
    repeat_dot_dy: float = 1.0
    repeat_label: float = 0.36  # loop header after the repeat sign
    lane_name_gap: float = 2.25  # lane name right edge to x=0
    lane_start: float = 1.1  # lane line starts left of x=0
    margin_left: float = 1.8
    margin_right: float = 3.15
    lane_end: float = 1.35  # lane line stops before the right margin
    margin_top: float = 1.8
    title_h: float = 2.7  # extra top room for the title
    margin_bottom: float = 1.8
    row_gap: float = 4.5  # between rows when wrapping with max_width
    title_x: float = 1.35
    title_y: float = 1.1

    # line widths (em) and dot size (em diameter)
    lw_lane: float = 0.15
    lw_box: float = 0.125
    lw_block: float = 0.1625
    lw_connector: float = 0.125
    lw_marker: float = 0.2
    lw_align: float = 0.1375
    lw_align_link: float = 0.075
    lw_bar_thick: float = 0.4
    lw_bar_thin: float = 0.125
    lw_icon: float = 0.15
    lw_separator: float = 0.1
    dot: float = 0.375

    # dash patterns (in line widths, matplotlib convention)
    dash_wait: str = "-"
    dash_op: tuple = (0, (4, 2))
    dash_align: tuple = (0, (4, 3))
    dash_align_link: tuple = (0, (1, 2))
    dash_region: tuple = (0, (4, 2))
    dash_branch: tuple = (0, (3, 2))

    # text wrapping (characters)
    label_chars: int = 56  # region labels: wrap width ...
    label_lines: int = 6  # ... and most lines
    block_chars: int = 36  # collapsed-block arguments: starting wrap width ...
    block_chars_step: int = 12  # ... widened by this while the lines do not fit ...
    block_chars_max: int = 90  # ... up to this; then arguments are elided
    # z order (layers)
    z_region: float = 0.5  # + z_region_step per nesting level
    z_region_step: float = 0.01
    z_lane: float = 1
    z_line: float = 2
    z_box: float = 3
    z_bar: float = 4
    z_text: float = 5

    def em(self, k: float) -> float:
        """``k`` em as inches (layout unit)."""
        return k * self.size / 72

    def pt(self, k: float) -> float:
        """``k`` em as points (font sizes, line widths)."""
        return k * self.size


def make_style(style: Style | dict | None) -> Style:
    if isinstance(style, Style):
        return style
    style = dict(style or {})
    unknown = set(style) - {f.name for f in fields(Style)}
    if unknown:
        raise TypeError(f"unknown style fields: {sorted(unknown)}")
    style["colors"] = {**COLORS, **style.get("colors", {})}
    return replace(Style(), **style)
