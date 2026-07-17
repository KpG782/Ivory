"""CLI entry point for the Ivory eval harness.

Exit code 0 iff every suite meets its gate — usable as a CI quality gate.

    backend/.venv/bin/python evals/run_evals.py
"""
from __future__ import annotations

import sys

from harness import run_all


def main() -> int:
    print("=" * 68)
    print("Ivory dental agent — offline evaluation harness")
    print("=" * 68)
    results = run_all(verbose=True)

    print("\n" + "=" * 68)
    print("SCORECARD")
    print("=" * 68)
    worst_gap = 0.0
    all_ok = True
    for res in results:
        mark = "PASS" if res.ok else "FAIL"
        print(f"  {mark}  {res.name:18s} {res.score:6.1%}  ({res.passed}/{res.total}, gate {res.gate:.0%})")
        all_ok = all_ok and res.ok
        if not res.ok:
            worst_gap = max(worst_gap, res.gate - res.score)
    overall = sum(r.passed for r in results) / max(1, sum(r.total for r in results))
    print(f"\n  Overall: {overall:.1%} across {sum(r.total for r in results)} cases")
    print(f"  Result:  {'ALL GATES PASSED ✅' if all_ok else 'GATE FAILURES ✗'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    # Allow `python evals/run_evals.py` from repo root.
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
    raise SystemExit(main())
