"""Render every benchmark program (collapsed + expanded) and run the overlap check.

Run: python -B tests/render_benchmarks.py [case ...]
Figures go to tests/figures/<case>.png and <case>_expanded.png.
"""

import importlib
import sys
import traceback
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]

import matplotlib.pyplot as plt  # noqa: E402

import overlap  # noqa: E402
import qm_circuit as qc  # noqa: E402
from benchmark_programs.cases import CASES  # noqa: E402

OUT = HERE / "figures"


def main(names: list[str]) -> int:
    OUT.mkdir(exist_ok=True)
    failed = 0
    for name in names or CASES:
        module, func, kwargs = CASES[name]
        fn = getattr(importlib.import_module(f"benchmark_programs.{module}"), func)
        for expand in (False, True):
            path = OUT / f"{name}{'_expanded' if expand else ''}.png"
            try:
                fig = qc.draw(fn, expand=expand, **kwargs)
                n = overlap.save(fig, path)
                plt.close(fig)
                status = "OK  " if n == 0 else "OVER"
                failed += n > 0
                print(f"{status} {path.name}: {n} overlaps")
            except Exception:
                failed += 1
                print(f"FAIL {path.name}")
                traceback.print_exc()
    print(f"{failed} failing figures")
    return int(failed > 0)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
