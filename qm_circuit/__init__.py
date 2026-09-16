"""Offline quantum-circuit-style diagrams of QUA programs (qm-qua 1.4.x)."""

from .build import build_model
from .model import Align, Block, Branch, If, Loop, Op, Play, Program, Wait, format_model
from .style import Style
from .tracer import Tracer


class capture(Tracer):  # noqa: N801  (used like a function: ``with capture() as cap``)
    """Record the first QUA program built inside the ``with`` block, then stop that code right there.

    ``with qm_circuit.capture() as cap: some_acq(state, ...)`` never reaches the job-running part.
    """

    def model(self, show_saves: bool = False) -> Program:
        return build_model(self, show_saves)

    def draw(self, expand: bool = False, show_saves: bool = False, title: str | None = None,
             style: Style | dict | None = None, max_width: float | None = None):
        from .render import render

        return render(self.model(show_saves), expand=expand, title=title, style=style, max_width=max_width)


def model(prog_func, *args, show_saves: bool = False, **kwargs) -> Program:
    """Run ``prog_func(*args, **kwargs)`` until its ``q.program()`` exits and return the circuit model."""
    with capture() as cap:
        prog_func(*args, **kwargs)
    return cap.model(show_saves)


def draw(prog_func, *args, expand: bool = False, show_saves: bool = False, title: str | None = None,
         style: Style | dict | None = None, max_width: float | None = None, **kwargs):
    """Trace ``prog_func(*args, **kwargs)`` and render it. Returns a matplotlib Figure.

    ``style``: a :class:`Style` or a dict of its fields to override (see ``qm_circuit/style.py``).
    ``max_width``: wrap top-level statements into rows at most this many inches wide.
    """
    from .render import render

    return render(model(prog_func, *args, show_saves=show_saves, **kwargs), expand=expand, title=title, style=style,
                  max_width=max_width)


__all__ = ["capture", "draw", "Style", "model", "build_model", "format_model", "Program", "Play", "Wait", "Align", "Op",
           "Loop", "If", "Branch", "Block"]
