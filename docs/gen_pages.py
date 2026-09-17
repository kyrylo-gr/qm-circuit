"""Docs build step (mkdocs-gen-files): draw every example as SVG, fill the placeholders of the hand-written pages,
write the gallery page.

Nothing is written to disk; the files exist only in the site build.
"""

import ast
import importlib
import io
import sys
from pathlib import Path

import matplotlib
import mkdocs_gen_files
from matplotlib.figure import Figure

import qm_circuit as qc
from qm_circuit.nodes import has_collapsible_block

matplotlib.use("Agg")

DOCS = Path(__file__).resolve().parent
EXAMPLES = DOCS.parent / "examples"
sys.path.insert(0, str(EXAMPLES))
HOME = ["rabi", "active_reset", "ramsey"]
# Tune-up order; each program shows a different kind of QUA statement.
GALLERY = ["resonator_spectroscopy", "flux_map", "qubit_spectroscopy", "rabi", "rabi_chevron", "single_shot",
           "active_reset", "t1", "ramsey", "echo", "pairwise_cz"]


def save_svg(fig, name: str) -> None:
    buf = io.StringIO()
    fig.savefig(buf, format="svg")
    with mkdocs_gen_files.open(f"diagrams/{name}.svg", "w") as f:
        f.write(buf.getvalue())


def title_and_caption(mod) -> tuple[str, str]:
    title, _, caption = mod.__doc__.strip().partition("\n")
    return title, caption.strip()


def source(name: str) -> str:
    """Example source without its module docstring (the page already shows title and caption)."""
    text = (EXAMPLES / f"{name}.py").read_text()
    return "\n".join(text.splitlines()[ast.parse(text).body[0].end_lineno:]).strip()


def runnable_source(name: str, expandable: bool) -> str:
    """Example source plus the lines that draw and save it, so a reader can copy it and get the diagram shown."""
    lines = source(name).splitlines()
    last_import = max(i for i, line in enumerate(lines) if line.startswith(("import ", "from ")))
    lines.insert(last_import + 1, "import qm_circuit as qc")
    expand = "  # expand=True opens helper blocks" if expandable else ""
    lines += ["", f"fig = qc.draw({name}, **ARGS){expand}", f'fig.savefig("{name}.svg")']
    return "\n".join(lines)


def diagram_links(name: str) -> tuple[list[str], bool]:
    """Draw ``name`` collapsed (and expanded when it has a helper block); return the image links and that flag."""
    mod = importlib.import_module(name)
    fn = getattr(mod, name)
    expandable = has_collapsible_block(qc.model(fn, **mod.ARGS))
    links = []
    for view in ["collapsed", "expanded"] if expandable else ["collapsed"]:
        file = name if view == "collapsed" else f"{name}_expanded"
        save_svg(qc.draw(fn, expand=view == "expanded", **mod.ARGS), file)
        hidden = " .qc-off" if view == "expanded" else ""
        links.append(f"[![{name} diagram, {view}](diagrams/{file}.svg)](diagrams/{file}.svg)"
                     f'{{ data-view="{view}"{hidden} title="Open full size" }}')
    return links, expandable


def viewer(names: list[str], layout: str) -> str:
    """Markdown for one chip viewer holding ``names``; the JavaScript adds the chips.

    ``layout``: ``"side"`` puts source and diagram side by side (home page); ``"stacked"`` shows the diagram at
    natural size, with a Code chip that swaps it for the source (gallery). Without JavaScript only the first
    program, collapsed, shows.
    """
    parts = [f'<div class="qc-viewer qc-{layout}" markdown>']
    for i, name in enumerate(names):
        links, expandable = diagram_links(name)
        code = [f'```python title="{name}.py"', runnable_source(name, expandable), "```"]
        diagram = ['<div class="qc-diagram" markdown>', "", *links, "", "</div>"]
        if layout == "stacked":
            body = diagram + ["", '<div class="qc-code qc-off" markdown>', "", *code, "", "</div>"]
        else:
            body = code + [""] + diagram
        title = title_and_caption(importlib.import_module(name))[0]
        parts += [
            f'<div class="qc-program{" qc-off" if i else ""}" data-title="{title}"'
            f'{" data-expandable=true" if expandable else ""} markdown>',
            "", *body, "", "</div>",
        ]
    return "\n".join(parts + ["</div>"])


def fill(page: str, placeholders: dict[str, str]) -> None:
    """Rewrite the hand-written ``page`` with its ``<!-- placeholder -->`` comments replaced."""
    text = (DOCS / "user" / page).read_text()
    for key, value in placeholders.items():
        assert f"<!-- {key} -->" in text, f"{page}: missing <!-- {key} -->"
        text = text.replace(f"<!-- {key} -->", value)
    with mkdocs_gen_files.open(page, "w") as f:
        f.write(text)
    mkdocs_gen_files.set_edit_path(page, page)


rabi = importlib.import_module("rabi")
fill("index.md", {"viewer": viewer(HOME, "side")})
fill("getting-started.md", {
    "rabi source": f"```python\n{source('rabi')}\n```",
    "rabi model": f"```text\n{qc.format_model(qc.model(rabi.rabi, **rabi.ARGS))}\n```",
})

gallery = ["---", "hide:", "  - navigation", "---", "", "# Gallery", "",
           "Short, classic qubit sequences in tune-up order, each chosen to show how a kind of QUA statement "
           "is drawn: sweeps, markers, flux ops, conditionals, frame operations, helper blocks and timing "
           "scopes. Most programs read out through a `measure_readout` helper: switch to **Expanded** to open "
           "its block.", ""]
for name in GALLERY:
    title, caption = title_and_caption(importlib.import_module(name))
    gallery += [f"## {title}", "", caption, "", viewer([name], "stacked"), ""]
with mkdocs_gen_files.open("gallery.md", "w") as f:
    f.write("\n".join(gallery))
mkdocs_gen_files.set_edit_path("gallery.md", "../gen_pages.py")


customising = importlib.import_module("customising")
for name, fig in vars(customising).items():
    if isinstance(fig, Figure):
        save_svg(fig, f"customising_{name}")
