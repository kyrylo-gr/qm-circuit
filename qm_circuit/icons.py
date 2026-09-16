"""Instruction icons as polylines in a unit square (x, y in 0..1, y up), keyed by the QUA function name.

An instruction without an entry here is drawn as text only (its name, then its arguments).
"""

from __future__ import annotations

import numpy as np

_t = np.linspace(0, 1, 60)
_a = np.linspace(0, 2 * np.pi, 60)


def _arc(a0: float, a1: float, r: float = 0.4, cx: float = 0.5, cy: float = 0.5, head: bool = False):
    """Circular arc (degrees, counter-clockwise), optionally with an arrow head at its end."""
    a = np.radians(np.linspace(a0, a1, 40))
    out = [(cx + r * np.cos(a), cy + r * np.sin(a))]
    if head:
        end, tangent = a[-1], a[-1] + np.pi / 2
        x, y = cx + r * np.cos(end), cy + r * np.sin(end)
        for side in (-0.55, 0.55):
            back = tangent + np.pi + side
            out.append(([x, x + 0.22 * np.cos(back)], [y, y + 0.22 * np.sin(back)]))
    return out


_RESET = _arc(60, 380, head=True)

ICONS: dict[str, list] = {
    # Gaussian-envelope carrier
    "play": [(_t, 0.5 + 0.45 * np.exp(-((_t - 0.5) / 0.2) ** 2) * np.sin(2 * np.pi * 4.5 * _t))],
    # meter: arc and needle
    "measure": [*_arc(20, 160, r=0.48, cy=0.18), ([0.5, 0.82], [0.18, 0.72])],
    # hourglass
    "wait": [([0.18, 0.82, 0.18, 0.82, 0.18], [0.95, 0.95, 0.05, 0.05, 0.95])],
    # constant sine with an up/down arrow: frequency change
    "update_frequency": [(_t * 0.7, 0.5 + 0.3 * np.sin(2 * np.pi * 2 * _t)),
                         ([0.9, 0.9], [0.1, 0.9]), ([0.8, 0.9, 1.0], [0.75, 0.9, 0.75]),
                         ([0.8, 0.9, 1.0], [0.25, 0.1, 0.25])],
    # level ramped down to the baseline
    "ramp_to_zero": [([0.0, 0.3, 0.9], [0.85, 0.85, 0.1]), ([0.0, 1.0], [0.1, 0.1])],
    # DC step
    "set_dc_offset": [([0.0, 0.4, 0.4, 1.0], [0.2, 0.2, 0.8, 0.8])],
    # rotation arrow with a radius: an angle
    "frame_rotation": [*_arc(0, 270, head=True), ([0.5, 0.9], [0.5, 0.5])],
    "reset_frame": _RESET,
    "reset_phase": _RESET,
    "reset_if_phase": _RESET,
    "reset_global_phase": _RESET,
    # 2x2 matrix
    "update_correction": [([0.25, 0.1, 0.1, 0.25], [0.95, 0.95, 0.05, 0.05]),
                          ([0.75, 0.9, 0.9, 0.75], [0.95, 0.95, 0.05, 0.05]),
                          ([0.3, 0.42], [0.7, 0.7]), ([0.58, 0.7], [0.7, 0.7]),
                          ([0.3, 0.42], [0.3, 0.3]), ([0.58, 0.7], [0.3, 0.3])],
}
ICONS["frame_rotation_2pi"] = ICONS["fast_frame_rotation"] = ICONS["frame_rotation"]
