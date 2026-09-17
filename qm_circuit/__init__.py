"""Offline quantum-circuit-style diagrams of QUA programs (qm-qua 1.4.x)."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from .build import build_model
from .nodes import Align, Block, Branch, If, Loop, Op, Play, Program, Wait, format_model
from .style import Style
from .tracer import Tracer

if TYPE_CHECKING:
    from matplotlib.figure import Figure


class capture(Tracer):  # noqa: N801  (used like a function: ``with capture() as cap``)
    """Record the first QUA program built inside the ``with`` block, then stop that code right there.

    Use it for code that builds a program and goes on to run it: nothing after ``q.program()`` exits runs.
    Captures cannot be nested.

    Examples:
        >>> with qm_circuit.capture() as cap:
        ...     run_t1_experiment(qubit, n_avg=1000)  # stopped before any job starts
        >>> fig = cap.draw(expand=True)
    """

    def model(self, show_saves: bool = False) -> Program:
        """The captured program's model; see [`model`][qm_circuit.model]."""
        return build_model(self, show_saves)

    def draw(self, expand: bool = False, show_saves: bool = False, title: str | None = None,
             style: Style | dict | None = None, max_width: float | None = None) -> Figure:
        """Draw the captured program; the options are those of [`draw`][qm_circuit.draw]."""
        from .render import render

        return render(self.model(show_saves), expand=expand, title=title, style=style, max_width=max_width)


def model(prog_func: Callable, *args, show_saves: bool = False, **kwargs) -> Program:
    """Run ``prog_func(*args, **kwargs)`` until its ``q.program()`` exits and return the circuit model.

    Args:
        prog_func: Function that builds a QUA program; ``*args`` and ``**kwargs`` are passed to it.
        show_saves: Also include ``save`` statements.

    Examples:
        >>> m = qm_circuit.model(rabi, amplitudes=np.linspace(0, 1.5, 31), n_avg=1000)
        >>> m.lines
        ['qubit', 'resonator']
    """
    with capture() as cap:
        prog_func(*args, **kwargs)
    return cap.model(show_saves)


def draw(prog_func: Callable, *args, expand: bool = False, show_saves: bool = False, title: str | None = None,
         style: Style | dict | None = None, max_width: float | None = None, **kwargs) -> Figure:
    """Trace ``prog_func(*args, **kwargs)`` and render it.

    Args:
        prog_func: Function that builds a QUA program; ``*args`` and ``**kwargs`` are passed to it.
        expand: Show the content of helper blocks instead of one collapsed box each.
        show_saves: Also draw ``save`` statements.
        title: Figure title; defaults to the function name.
        style: A [`Style`][qm_circuit.Style], or a dict of its fields to override (colors are merged).
        max_width: Wrap top-level statements into rows at most this many inches wide.

    Returns:
        A matplotlib ``Figure``.

    Examples:
        >>> fig = qm_circuit.draw(rabi, amplitudes=np.linspace(0, 1.5, 31), n_avg=1000)
        >>> fig.savefig("rabi.svg")
        >>> qm_circuit.draw(ramsey, delays, n_avg=100, expand=True, style={"size": 10}, max_width=8)
    """
    from .render import render

    return render(model(prog_func, *args, show_saves=show_saves, **kwargs), expand=expand, title=title, style=style,
                  max_width=max_width)


__all__ = ["capture", "draw", "Style", "model", "format_model", "Program", "Play", "Wait", "Align", "Op", "Loop", "If",
           "Branch", "Block"]
