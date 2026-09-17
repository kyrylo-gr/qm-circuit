"""Docs examples: each draws, collapsed and expanded, without overlaps. Run: python -B -m pytest tests/test_examples.py"""

import ast
import importlib
import sys
from pathlib import Path

import pytest
from matplotlib.figure import Figure

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
sys.path[:0] = [str(ROOT), str(Path(__file__).resolve().parent), str(EXAMPLES)]
sys.dont_write_bytecode = True

import overlap  # noqa: E402
import qm_circuit as qc  # noqa: E402
from qm_circuit.nodes import has_collapsible_block  # noqa: E402

PROGRAMS = sorted(p.stem for p in EXAMPLES.glob("*.py") if p.stem != "customising")
CUSTOMISING = [name for name, v in vars(importlib.import_module("customising")).items() if isinstance(v, Figure)]


def model_of(name):
    mod = importlib.import_module(name)
    return qc.model(getattr(mod, name), **mod.ARGS)


@pytest.mark.parametrize("name", PROGRAMS)
@pytest.mark.parametrize("expand", [False, True])
def test_example_draws_without_overlap(name, expand):
    mod = importlib.import_module(name)
    assert overlap.check(qc.draw(getattr(mod, name), expand=expand, **mod.ARGS)) == []


@pytest.mark.parametrize("name", PROGRAMS)
def test_example_docstring_gives_title_and_caption(name):
    title, _, caption = (importlib.import_module(name).__doc__ or "").strip().partition("\n")
    assert title and caption.strip(), "the docs page shows the first docstring line as title, the rest as caption"


def test_expanded_chip_is_offered_only_for_programs_with_a_helper_block():
    assert has_collapsible_block(model_of("ramsey"))  # measure_readout(...) helper
    assert has_collapsible_block(model_of("rabi"))  # measure_readout(...) helper
    assert not has_collapsible_block(model_of("active_reset"))


def test_every_example_is_on_the_site_and_gallery_has_no_duplicates():
    tree = ast.parse((ROOT / "docs" / "gen_pages.py").read_text())
    lists = {t.id: ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
             for t in node.targets if isinstance(t, ast.Name) and t.id in ("HOME", "GALLERY")}
    assert len(set(lists["GALLERY"])) == len(lists["GALLERY"])
    assert set(lists["HOME"]) | set(lists["GALLERY"]) == set(PROGRAMS)


@pytest.mark.parametrize("name", CUSTOMISING)
def test_customising_figure_has_no_overlap(name):
    assert overlap.check(getattr(importlib.import_module("customising"), name)) == []


def test_customising_page_gets_its_four_figures():
    assert CUSTOMISING == ["default", "larger_font", "custom_colours", "wrapped"]
