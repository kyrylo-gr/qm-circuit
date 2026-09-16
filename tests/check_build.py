"""Build every benchmark program offline (no QuantumMachinesManager). Run: python -B tests/check_build.py"""

import importlib
import sys
import traceback
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import qm  # noqa: E402

from benchmark_programs.cases import CASES  # noqa: E402

FORBIDDEN = ("labmate", "scipy", "tqdm", "ffit", "kite_exp", "IPython", "matplotlib")


def build(name: str):
    module, func, kwargs = CASES[name]
    fn = getattr(importlib.import_module(f"benchmark_programs.{module}"), func)
    return fn(**kwargs)


def main() -> int:
    failed = 0
    for name in CASES:
        try:
            prog = build(name)
            assert isinstance(prog, qm.Program), type(prog)
            qm.generate_qua_script(prog)
            print(f"OK   {name}")
        except Exception:
            failed += 1
            print(f"FAIL {name}")
            traceback.print_exc()
    leaked = sorted(m for m in sys.modules if m.split(".")[0] in FORBIDDEN)
    if leaked:
        failed += 1
        print(f"FAIL forbidden modules imported: {leaked}")
    print(f"{len(CASES) - failed + bool(leaked)}/{len(CASES)} cases OK" + (" (forbidden imports!)" if leaked else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
