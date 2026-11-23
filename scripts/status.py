#!/usr/bin/env python3
"""Show which stages exist and whether they pass.

    python scripts/status.py

Runs each stage's tests in a subprocess and prints one line per stage. First command in
any session.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main() -> int:
    stages = sorted(p for p in (ROOT / "stages").iterdir() if p.is_dir())
    if not stages:
        print("no stages found")
        return 1

    passed = 0
    for stage in stages:
        tests = sorted(stage.glob("test_*.py"))
        if not tests:
            print(f"  {stage.name:<22} no tests")
            continue

        result = subprocess.run(
            [sys.executable, str(tests[0])], cwd=ROOT, capture_output=True, text=True
        )
        ok = result.returncode == 0
        passed += ok
        detail = ""
        if not ok:
            tail = [line for line in result.stderr.splitlines() if line.strip()]
            detail = f"  ({tail[-1][:60]})" if tail else ""
        print(f"  {stage.name:<22} {'pass' if ok else 'fail'}{detail}")

    print(f"\n{passed} of {len(stages)} stages passing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
