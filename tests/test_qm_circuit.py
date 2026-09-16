"""Model-level tests for qm_circuit (offline, no QuantumMachinesManager). Run: python -B -m pytest tests/"""

import importlib.util
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import qm._loc  # noqa: E402
import qm.qua as q  # noqa: E402
from qm.qua._scope_management._core_scopes import _ProgramScope  # noqa: E402

import qm_circuit as qc  # noqa: E402
from qm_circuit.model import Block, If, Loop, Op, Play  # noqa: E402

ORIG_GET_LOC = qm._loc._get_loc
ORIG_EXIT = _ProgramScope.__exit__


def assert_unpatched():
    assert all(getattr(m, "_get_loc", ORIG_GET_LOC) is ORIG_GET_LOC for n, m in list(sys.modules.items())
               if n == "qm" or n.startswith("qm."))
    assert _ProgramScope.__exit__ is ORIG_EXIT


def readout(element, amplitude_rel, I, Q=None):
    q.measure("readout" * q.amp(amplitude_rel), element, q.demod.full("cos", I))
    q.wait(100, element)


def simple_prog(num_reps=100, drive_amp=0.3):
    with q.program() as prog:
        n = q.declare(int)
        I = q.declare(q.fixed)
        with q.for_(n, 0, n < num_reps, n + 1):
            q.play("pi", "drive")
            q.play("pi_half" * q.amp(drive_amp), "drive", duration=40)
            q.align("drive", "resonator")
            readout("resonator", 0.8, I)
    return prog


def walk(nodes):
    for n in nodes:
        yield n
        yield from walk([c for b in n.branches for c in b.body] if isinstance(n, If) else getattr(n, "body", []))


def test_import_has_no_side_effects():
    assert_unpatched()


def test_lanes_and_explicit_params_only():
    m = qc.model(simple_prog)
    assert m.lanes == ["drive", "resonator"]
    plays = [n for n in walk(m.body) if isinstance(n, Play)]
    assert [(p.element, p.pulse, p.params) for p in plays] == [
        ("drive", "pi", {}),  # everything from config: no params
        ("drive", "pi_half", {"amp": "0.3", "duration": "40"}),
        ("resonator", "readout", {"amp": "0.8"}),
    ]
    assert plays[-1].measure


def test_helper_block_label_has_passed_args_only():
    (loop,) = qc.model(simple_prog).body
    block = next(n for n in loop.body if isinstance(n, Block))
    assert block.func == "readout" and not block.scope
    assert block.params == ["element='resonator'", "amplitude_rel=0.8", "I"]  # Q not passed; I reads as its name
    assert [type(n).__name__ for n in block.body] == ["Play", "Wait"]


def test_loop_headers():
    def prog():
        with q.program() as p:
            n = q.declare(int)
            x = q.declare(q.fixed)
            with q.for_(n, 0, n < 10, n + 2):
                q.play("pi", "qubit")
            with q.for_each_(x, [0.1, 0.2]):
                q.play("pi" * q.amp(x), "qubit")
            with q.while_(n > 0):
                q.wait(4, "qubit")
        return p

    loops = [n for n in qc.model(prog).body if isinstance(n, Loop)]
    assert [(lp.kind, lp.header) for lp in loops] == [
        ("for", "n in range(0, 10, 2)"), ("for_each", "x in [0.1, 0.2]"), ("while", "while n>0")]


def test_statements_without_element_are_markers():
    def prog():
        with q.program() as p:
            s = q.declare_input_stream(int, name="s_in")
            q.advance_input_stream(s)
            q.play("pi", "qubit", target="I")
            q.update_frequency("qubit", 1000, keep_phase=True)
        return p

    body = qc.model(prog).body
    assert isinstance(body[0], Op) and body[0].name == "advance_input_stream" and body[0].targets == []
    assert body[1].params == {"target": "'I'"}
    assert (body[2].name, body[2].args) == ("update_frequency", "1_000, keep_phase=True")


def test_capture_stops_execution():
    reached = []

    def acq():
        simple_prog()
        reached.append(True)  # would run the job

    with qc.capture() as cap:
        acq()
        reached.append(True)
    assert not reached
    assert cap.program is not None and cap.name == "simple_prog"
    assert_unpatched()


def test_patches_restored_after_exception():
    def bad():
        with q.program() as p:
            q.play("pi", "qubit")
            raise ValueError("boom")
        return p

    with pytest.raises(ValueError, match="boom"):
        qc.draw(bad)
    assert_unpatched()
    assert qc.model(simple_prog).lanes == ["drive", "resonator"]  # still usable afterwards


def test_no_overlap_simple_program():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import overlap

    for expand in (False, True):
        assert overlap.check(qc.draw(simple_prog, expand=expand)) == []


def test_nested_capture_is_refused_and_restored():
    with qc.capture() as cap:
        with pytest.raises(RuntimeError, match="already active"):
            with qc.capture():
                pass
        simple_prog()
    assert cap.program is not None
    assert_unpatched()


def test_value_formatting_bool_arrays_uneven_and_streams():
    def helper(element, st):
        q.measure("readout", element, timestamp_stream=st)

    def prog():
        with q.program() as p:
            b = q.declare(bool)
            x = q.declare(q.fixed)
            y = q.declare(q.fixed)
            ts = q.declare_stream()
            with q.for_each_(b, [False, True]):
                q.play("pi", "qubit", condition=b)
            with q.for_each_(x, [0.1, 0.2, 0.2, 0.2, 0.2, 0.2]):  # uneven: no "[a..b] (n)" range summary
                q.play("pi" * q.amp(x), "qubit")
            with q.for_each_(y, [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]):  # evenly spaced: summarized
                q.play("pi" * q.amp(y), "qubit")
            helper("resonator", ts)
        return p

    body = qc.model(prog).body
    assert [n.header for n in body[:3]] == [
        "b in [False, True]", "x in [0.1, 0.2, ..., 0.2] (6)", "y in [0.1..0.6] (6)"]
    assert body[3].params == ["element='resonator'", "st=ts"]  # a stream shows its call-site name, not its type


def test_elementless_align_and_wait_span_all_lanes():
    from matplotlib.figure import Figure

    from qm_circuit.render import _Layout
    from qm_circuit.style import make_style

    def prog():
        with q.program() as p:
            n = q.declare(int)
            q.play("flux", "flux_dc")
            with q.for_(n, 0, n < 2, n + 1):
                q.play("readout", "resonator")
                q.align()
            with q.for_(n, 0, n < 2, n + 1):
                q.wait(10)
            with q.for_(n, 0, n < 2, n + 1):
                q.play("readout", "resonator")
        return p

    m = qc.model(prog)
    lay = _Layout(Figure().add_axes((0, 0, 1, 1)), m.lanes, m.body, False, make_style(None))
    assert [lay.span(n, m.lanes) for n in m.body[1:]] == [m.lanes, m.lanes, ["resonator"]]


def test_trailing_branches_without_drawn_content_are_omitted():
    def prog():
        with q.program() as p:
            c = q.declare(int)
            x = q.declare(q.fixed)
            with q.switch_(c):  # no default: qm emits an empty else
                with q.case_(1):
                    q.play("x", "qubit")
            with q.if_(c > 1):
                q.play("p", "qubit")
            with q.else_():
                q.assign(x, 0.0)  # hidden: the else draws nothing
            with q.if_(c > 2):
                q.play("p", "qubit")
            with q.elif_(c > 1):
                q.assign(x, 1.0)
            with q.else_():
                q.assign(x, 0.0)  # two trailing branches without content: both go
            with q.if_(c > 1):
                q.assign(x, 1.0)
            with q.else_():
                q.play("p", "qubit")  # an empty if before a drawn branch stays, so the else keeps its meaning
        return p

    labels = [[b.label for b in n.branches] for n in qc.model(prog).body]
    assert labels == [["if c==1"], ["if c>1"], ["if c>2"], ["if c>1", "else"]]
