"""Every visual constant of the renderer, in one theme.

All lengths, font sizes and line widths are in *em*: multiples of ``size`` (the base font size, points).
One em is ``size`` points of line width or font size, and ``size / 72`` inches of geometry, so changing
``size`` scales the whole diagram consistently. ``draw(..., style=Style(size=10))`` or
``draw(..., style={"size": 10, "colors": {"pulse": "#c03"}})`` overrides fields (colors are merged).
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, replace

COLORS = dict(
    background="white", text="black", muted="#555555", line="#000000",
    pulse="white", pulse_edge="black", measure="white", pulse_text="black", param_text="#333333",
    wait="black", wait_fill="white", op_fill="white", op_edge="black",
    block_fill="white", block_edge="black", region_fill="white", region_edge="black",
    if_fill="white", if_edge="black", if_text="black", bar="black", align="#555555",
)


@dataclass(frozen=True)
class Style:
    """Every appearance value of a diagram. Lengths are in em: multiples of ``size``, the base font size.

    Examples:
        >>> qm_circuit.draw(rabi, **ARGS, style={"size": 11, "colors": {"pulse": "#0b5394"}})
        >>> big = qm_circuit.Style(size=11)
        >>> qm_circuit.draw(rabi, **ARGS, style=big)
    """

    size: float = 8.0
    """Base font size in points = 1 em; every other length is a multiple of it."""
    dpi: int = 150
    """Figure resolution in dots per inch."""
    sans: str = "DejaVu Sans"
    """Font family for names and titles (bundled with matplotlib)."""
    mono: str = "DejaVu Sans Mono"
    """Font family for values, parameters and loop headers."""
    regular: str = "normal"
    """Regular font weight."""
    bold: str = "bold"
    """Bold font weight."""
    colors: dict = field(default_factory=lambda: dict(COLORS))
    """Colour by role; a dict passed in ``style`` is merged into the defaults. Keys: ``background``, ``text``, ``muted``, ``line``, ``pulse``, ``pulse_edge``, ``measure``, ``pulse_text``, ``param_text``, ``wait``, ``wait_fill``, ``op_fill``, ``op_edge``, ``block_fill``, ``block_edge``, ``region_fill``, ``region_edge``, ``if_fill``, ``if_edge``, ``if_text``, ``bar``, ``align``."""

    # font sizes (em)
    font_title: float = 1.5
    """Title font size (em)."""
    font_line: float = 1.3125
    """Element name font size (em)."""
    font_pulse: float = 1.25
    """Pulse name font size (em)."""
    font_param: float = 0.9375
    """Pulse parameters, collapsed-block arguments and marker labels (em)."""
    font_small: float = 1.0
    """Wait and operation titles, region labels (em)."""
    font_small_sub: float = 0.875
    """Values under wait and operation titles (em)."""
    font_block: float = 1.1875
    """Collapsed-block name font size (em)."""

    # vertical geometry (em)
    box_h: float = 4.7
    """Pulse box height, which is also the band a line occupies (em)."""
    small_box_h: float = 3.3
    """Wait and operation box height (em)."""
    line_clear: float = 4.8
    """Free space between the bands of adjacent lines; grows when labels need room (em)."""
    min_clear: float = 1.1
    """Least free space between decorations of adjacent lines (em)."""
    row: float = 1.7
    """Height of one label row above a region or marker (em)."""
    line: float = 1.25
    """Line height of parameter text (em)."""
    edge: float = 0.9
    """How far blocks and regions reach beyond their lines' bands (em)."""
    overhang: float = 0.55
    """How far align barriers reach beyond the line band (em)."""
    pulse_title_dy: float = 0.72
    """Pulse name offset above the box centre when parameters are shown (em)."""
    pulse_param_dy: float = 1.08
    """Parameter text offset below the box centre (em)."""
    small_title_dy: float = 0.63
    """Wait and operation title offset above the box centre (em)."""
    small_sub_dy: float = 0.81
    """Wait and operation value offset below the box centre (em)."""
    block_title_dy: float = 1.7
    """First argument line below the collapsed-block name (em)."""
    label_dy: float = 0.45
    """Label baseline above its row bottom (em)."""
    icon: float = 0.5
    """Icon square side, as a fraction of its box height."""
    separator: float = 0.6
    """Icon / text separator length, as a fraction of the box height."""
    block_text_margin: float = 2.7
    """Vertical room of a collapsed block not usable for argument lines (em)."""

    # horizontal geometry (em)
    gap: float = 1.2
    """Horizontal gap between consecutive items on a line (em)."""
    pad: float = 1.0
    """Text padding inside boxes (em)."""
    min_text_w: float = 3.25
    """Least text width of a pulse box (em)."""
    label_inset: float = 0.72
    """Region label distance from the region's left edge (em)."""
    label_tail: float = 1.8
    """Room after a region label (em)."""
    rounding: float = 0.45
    """Box corner radius (em)."""
    repeat_thick: float = 0.225
    """Repeat sign: thick bar offset (em)."""
    repeat_thin: float = 0.9
    """Repeat sign: thin bar offset (em)."""
    repeat_dot: float = 1.53
    """Repeat sign: dots offset (em)."""
    repeat_w: float = 1.98
    """Repeat sign: total width (em)."""
    repeat_dot_dy: float = 1.0
    """Repeat sign: dot distance from the line (em)."""
    repeat_label: float = 0.36
    """Loop header distance after the repeat sign (em)."""
    line_name_gap: float = 2.25
    """Gap from the element name's right edge to the start of the diagram (em)."""
    line_start: float = 1.1
    """How far the line starts left of the diagram start (em)."""
    margin_left: float = 1.8
    """Left figure margin (em)."""
    margin_right: float = 3.15
    """Right figure margin (em)."""
    line_end: float = 1.35
    """Where lines stop before the right margin (em)."""
    margin_top: float = 1.8
    """Top figure margin (em)."""
    title_h: float = 2.7
    """Extra top room for the title (em)."""
    margin_bottom: float = 1.8
    """Bottom figure margin (em)."""
    row_gap: float = 4.5
    """Vertical gap between rows when wrapping with ``max_width`` (em)."""
    title_x: float = 1.35
    """Title position from the left edge (em)."""
    title_y: float = 1.1
    """Title baseline position from the top edge (em)."""

    # line widths (em) and dot size (em diameter)
    lw_line: float = 0.15
    """Element line width (em)."""
    lw_box: float = 0.125
    """Box outline width (em)."""
    lw_block: float = 0.1625
    """Block and region outline width (em)."""
    lw_connector: float = 0.125
    """Connector width between line groups of one item (em)."""
    lw_marker: float = 0.2
    """Marker line width (em)."""
    lw_align: float = 0.1375
    """Align barrier width (em)."""
    lw_align_link: float = 0.075
    """Width of the dotted link joining align barriers across skipped lines (em)."""
    lw_bar_thick: float = 0.4
    """Repeat sign thick bar width (em)."""
    lw_bar_thin: float = 0.125
    """Repeat sign thin bar width (em)."""
    lw_icon: float = 0.15
    """Icon stroke width (em)."""
    lw_separator: float = 0.1
    """Icon / text separator width (em)."""
    dot: float = 0.375
    """Repeat sign dot diameter (em)."""

    # dash patterns (in line widths, matplotlib convention)
    dash_wait: str = "-"
    """Wait box outline dash pattern (matplotlib linestyle)."""
    dash_op: tuple = (0, (4, 2))
    """Operation tag outline dash pattern (matplotlib linestyle)."""
    dash_align: tuple = (0, (4, 3))
    """Align barrier dash pattern (matplotlib linestyle)."""
    dash_align_link: tuple = (0, (1, 2))
    """Align link dash pattern (matplotlib linestyle)."""
    dash_region: tuple = (0, (4, 2))
    """Open region outline dash pattern (matplotlib linestyle)."""
    dash_branch: tuple = (0, (3, 2))
    """Dash pattern of the separator between branches (matplotlib linestyle)."""

    # text wrapping (characters)
    label_chars: int = 56
    """Region label wrap width (characters)."""
    label_lines: int = 6
    """Most lines of a region label."""
    block_chars: int = 36
    """Collapsed-block arguments: starting wrap width (characters)."""
    block_chars_step: int = 12
    """Collapsed-block arguments: wrap width increase while the lines do not fit (characters)."""
    block_chars_max: int = 90
    """Collapsed-block arguments: widest wrap width; beyond it arguments are elided (characters)."""
    # z order (layers)
    z_region: float = 0.5
    """Z order of regions; each nesting level adds ``z_region_step``."""
    z_region_step: float = 0.01
    """Z order added per region nesting level."""
    z_line: float = 1
    """Z order of element lines."""
    z_barrier: float = 2
    """Z order of barriers and connectors."""
    z_box: float = 3
    """Z order of boxes."""
    z_bar: float = 4
    """Z order of repeat signs."""
    z_text: float = 5
    """Z order of text."""

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
