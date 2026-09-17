# Spec: user documentation site

## Problem Statement

`qm-circuit` has internal documents only: `CONTEXT.md`, ADRs, a spec and agent
notes. A physicist who hears about the library has no page that shows what a
diagram looks like, how to install it, or how to call it. Nor can they tell what
the library reaches into: it patches private `qm-qua` internals, and a user
deciding whether to depend on it needs to know that before a `qm-qua` upgrade
breaks their notebook.

## Solution

A MkDocs Material site built from `docs/user/`, following the structure and
styling of [dh5](https://github.com/kyrylo-gr/dh5) with current mkdocs-material
practice added. It has six pages: Home, Getting started, Gallery, Customising
diagrams, How it works, and API reference. Every diagram on the site is drawn by
`qm_circuit.draw()` during the docs build, from example programs kept as
ordinary Python files. The build therefore runs offline and cannot drift from
the code. Docstrings in the library get descriptions and examples so the API
reference is generated rather than hand-written.

## User Stories

1. As a physicist landing on the site, I want one short paragraph saying what the library does, so that I know in seconds whether it is for me.
2. As a physicist, I want to see real code next to the diagram it produces on the home page, so that I understand the idea without installing anything.
3. As a physicist, I want to switch the home-page example between Rabi, active reset and a helper-based program with chips, so that I see several kinds of experiment in one place.
4. As a physicist, I want to switch the diagram between collapsed and expanded with chips, so that I see how helper functions stay visible as blocks.
5. As a physicist, I want the switch to animate, so that I notice what changed between views.
6. As a phone reader, I want code and diagram stacked instead of side by side, so that the page stays readable.
7. As a new user, I want one install command that works today, so that I can try the library right away.
8. As a new user, I want to be told the library requires `qm-qua` 1.4.x, so that I do not install it against an incompatible version.
9. As a new user, I want one short example each for `draw`, `model` and `capture`, so that I know which entry point fits my code.
10. As a user whose program is built inside a function that runs a job, I want the Getting started page to show `capture()`, so that I know I can draw it without touching hardware.
11. As a physicist, I want a gallery of classic qubit experiments in tune-up order, each showing a different kind of QUA statement, so that I can see how programs like mine will look.
12. As a physicist, I want each gallery program shown as code with its collapsed and expanded diagrams, using the same chips as the home page, so that the site behaves consistently.
13. As a physicist, I want gallery programs to be clean, without dead code, prints or placeholder arguments, so that they read as examples and not as lab leftovers.
14. As a user, I want a page showing one program drawn with default style, a larger font, custom colours and `max_width` wrapping, so that I can see what `style=` and `max_width` do before trying them.
15. As a cautious user, I want a short technical page naming the mechanism (patching, call-stack introspection, protobuf reading), so that I know what the library reads and changes.
16. As a cautious user, I want every private `qm-qua` name the library touches listed, so that I can judge the upgrade risk.
17. As a cautious user, I want to be told that patches are restored on every exit and that capture stops my code right after the program is built, so that I trust it near lab code.
18. As a reader of How it works, I want pseudo-code rather than library source, so that I get the idea without reading the implementation.
19. As a reader of How it works, I want links to the ADRs on GitHub, so that I can find the reasoning behind each choice.
20. As a user, I want an API reference for `draw`, `model`, `capture`, `Style`, `format_model` and the model classes, so that I can look up every argument.
21. As a user, I want every `Style` setting described on the reference page and in IDE hover, so that I can find the one I need to change.
22. As a user, I want an `Examples:` section on `draw`, `model`, `capture`, `format_model` and `Style`, so that I can copy a working call.
23. As a user, I want one documented way to get a model, so that I am not left choosing between `build_model` and `capture().model()`.
24. As a reader, I want light and dark mode, with diagrams on a white card in dark mode, so that figures stay legible.
25. As a reader, I want copy buttons on code and an edit link on every page, so that I can try code and report mistakes quickly.
26. As a maintainer, I want the docs build to fail on broken links and on example programs that no longer draw, so that the site never publishes stale content.
27. As a maintainer, I want the site built and deployed by a GitHub Pages workflow on every push to `main`, and built on pull requests, so that publishing needs no manual step.

## Implementation Decisions

**Location.** `mkdocs.yml` at the repository root with `docs_dir: docs/user`.
`docs/adr`, `docs/specs` and `docs/agents` stay outside the site.

**Nav.**
- Home: `index.md`
- Getting started: `getting-started.md`
- Gallery: generated
- Customising diagrams: `customising.md`
- How it works: `how-it-works.md`
- API reference: `reference.md`

**Styling.** dh5's theme setup is copied: Material, light/dark palette with the
toggle, its `extra.css` brand colours and mkdocstrings symbol colours, and its
features (`content.code.copy`, `navigation.instant`, `navigation.sections`,
`search.suggest`, `search.highlight`). The logo is a Material icon until a real
one exists. Additions:
- `strict: true` and `edit_uri`
- Features `content.action.edit`, `navigation.top`, `toc.follow`, `search.share`
- Markdown extensions `admonition`, `pymdownx.details`, `pymdownx.superfences`, `pymdownx.highlight`, `pymdownx.inlinehilite`, `pymdownx.snippets`, `attr_list`, `md_in_html`
- mkdocstrings with Google docstrings, signature annotations shown and a separate signature

Diagrams sit on a white card in dark mode.

**Example programs.** One file per program in `examples/`, each defining a
program function plus its sample arguments. Every image, and every code block
that shows the same program, comes from these files.
Each file defines a program function named like the file and an `ARGS` dict of sample arguments. Its module docstring holds the title (first line) and the caption.
- Home: `rabi.py` and `ramsey.py` (each calling a `measure_readout(...)` helper), `active_reset.py`. The function name is the diagram title, so the helper examples are named after their experiment.
- Gallery: short, classic qubit sequences in tune-up order: `resonator_spectroscopy`, `flux_map` (`pause`), `qubit_spectroscopy` (flux bias and `ramp_to_zero`), `rabi`, `rabi_chevron` (stepped `for_`, global `align`/`wait`), `single_shot` (`if_`), `active_reset` (`while_`), `t1` (uneven sweep, an `active_reset(...)` helper with a `while_` that calls the readout helper), `ramsey` (parallel `for_each_`, frame ops) `echo` (`strict_timing_`, merged waits) and `pairwise_cz` (three qubit lines, a `cz(a, b)` helper on q1-q2, q1-q3 and q2-q3, so one block skips a line). The gallery shows how each kind of QUA statement is drawn, not full lab sequences: generic element and pulse names (`qubit`, `resonator`, `flux`, `x180`, `readout`), no lab-specific DC lines or heralding, and at most one helper function, except `t1`, whose reset helper nests the readout helper. Every program whose readout is a `measure` followed by a `wait` (or, in `t1`, a bare `measure` before an active reset) calls it through a `measure_readout(...)` helper block; `active_reset` (bare `measure`, read by `while_`) keeps the readout inline.
- Customising: `customising.py`, one program drawn four ways.

`tests/benchmark_programs/` stays untouched (ADR 0006).

**Image generation.** A `mkdocs-gen-files` script, `docs/gen_pages.py`, imports each example, calls
`qm_circuit.draw()` collapsed and expanded, and writes SVG files into the build.
It also generates the gallery page, and fills `<!-- ... -->` placeholders in `index.md` (the viewer) and `getting-started.md` (the Rabi source and its `format_model` output), so that no page repeats example code by hand. Generated pages keep an edit link: to their Markdown source, or to the script for the gallery. No images are committed. The docs build
therefore needs `qm-qua` 1.4.x installed and fails when the tracer does, which
serves as an early warning of `qm-qua` incompatibility.

**Chip viewer.** One small CSS/JS component used on the home page and in the
gallery.
- One row of chips selects the program (home only); another selects Collapsed or Expanded.
- On the home page, code and diagram sit side by side on wide screens and stack on narrow ones.
- In the gallery, the diagram is shown at natural size in a horizontally scrolling strip, and a third Code chip swaps the diagram for its source, because lab programs are too wide to read side by side.
- The source in the viewer ends with the `qc.draw` call and a `savefig`, so copying it reproduces the diagram.
- Clicking a diagram opens the full-size SVG.
- Switching animates with a CSS transition.
- For a program without helper calls, both views are the same: Expanded is disabled on the home page, where programs switch, and hidden in the gallery.
- Without JavaScript, the first program shows collapsed.

**How it works: content.** Short and in pseudo-code. It covers:
- **Trace:** `qm._loc._get_loc` is patched in every imported `qm.*` module. Each statement's `loc` gets a trace id keyed to the Python call stack (`sys._getframe`, `co_positions`, `inspect.getargvalues`, `ast` on the call site for passed arguments). The private scope classes are patched too: `_ForScope._create_statement`, because 1.4.1 leaves the `for_` loc empty; `_ElifScope.__init__`; and `_ProgramScope.__enter__`/`__exit__`.
- **Capture:** a private `BaseException` subclass is raised when the first `program()` exits, so `except Exception` in user code cannot swallow it. Patches are restored on every exit path, and nested captures are refused.
- **Build:** the protobuf statements are walked into dataclasses. `HasField` separates explicit parameters from config values. Statements sharing one helper-call frame directly below the program function become a block, and a helper that also wraps the caller's statements becomes an open region.
- **Render:** matplotlib layout with measured text widths.
- **Compatibility:** only `qm-qua` 1.4.x is supported, the tool breaks when those private names change, and the ADRs are linked on GitHub.

**API reference.** mkdocstrings directives for `draw`, `model`, `capture`,
`Style`, `format_model` and the model classes `Program`, `Play`, `Wait`,
`Align`, `Op`, `Loop`, `If`, `Branch`, `Block`.

**Library changes.**
- `build_model` leaves `__all__`; it stays importable from `qm_circuit.build`.
- `qm_circuit/model.py` becomes `qm_circuit/nodes.py`. griffe cannot document the `model()` function while a submodule has the same name. Model classes are imported from `qm_circuit`.
- The avoided term *lane* becomes *line* everywhere, as CONTEXT.md asks: `Program.lines`, the colour key `line`, the Style settings `font_line`, `line_clear`, `line_name_gap`, `line_start`, `line_end`, `lw_line` and `z_line`, and the `format_model` text. The previous `z_line`, which layers barriers, markers and connectors, becomes `z_barrier`. Drawings stay pixel-identical.
- `draw` and `model` get type annotations (`Callable`, `Figure`) for the reference page.
- `Style` field comments become attribute docstrings.
- One-line docstrings are added to the model classes and to `capture.model` and `capture.draw`.
- `Examples:` sections are added to `draw`, `model`, `capture`, `format_model` and `Style`.
- No drawing behaviour change.

**Install text.** `pip install git+https://github.com/kyrylo-gr/qm-circuit`.

**Dependencies.** A `docs` optional-dependency group in `pyproject.toml`:
`mkdocs-material`, `mkdocstrings[python]` and `mkdocs-gen-files`, with lower
bounds.

**CI.** The site is built and published by a GitHub Pages workflow,
`.github/workflows/docs.yml`, that uses the official Pages actions instead of
`mkdocs gh-deploy` and a `gh-pages` branch.
- **Build job**, on pull requests and on push to `main`: `actions/checkout`, then `actions/setup-python` with the pip cache. It installs `.[docs]`, runs `mkdocs build --strict` and uploads `site/` with `actions/upload-pages-artifact`.
- **Deploy job**, on push to `main` only: needs the build job and runs `actions/deploy-pages`. It has `pages: write` and `id-token: write` permissions and uses the `github-pages` environment.
- **Repository setting:** Settings → Pages → Source is set to "GitHub Actions", a one-time manual step.
- `site_url` is `https://kyrylo-gr.github.io/qm-circuit/`.

## Testing Decisions

- A smoke test imports each file in `examples/` and draws it collapsed and expanded, with the overlap checker, so a broken or overlapping example fails pytest before it reaches the site. Each example's docstring must give a title and caption, and each customising figure is checked the same way.
- `has_collapsible_block` (in `qm_circuit/nodes.py`) decides whether the Expanded chip is offered; it is tested on both branches.
- `mkdocs build --strict` is the check for links, snippets and reference directives.
- The chip viewer and page layout are checked by eye in `mkdocs serve`, in light and dark mode and at phone width.

## Out of Scope

- Changelog, About and Contributing pages.
- Social cards, versioned docs (`mike`) and a per-module generated reference.
- A PyPI release.
- Publishing ADRs, specs or agent docs on the site.
- Changes to `tests/benchmark_programs/` or `programs/`.

## Further Notes

- The GitHub remote is currently blocked from this environment, so the Pages workflow is written but not run from here. Before the first deploy, set the Pages source to "GitHub Actions" in the repository settings.
- Add a Changelog page and switch the install command to `pip install qm-circuit` at the first PyPI release.
