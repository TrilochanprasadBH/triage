#!/usr/bin/env python3
"""Show which stages exist, whether the stubs fail, and whether the reference passes.

    python3 scripts/status.py

Two columns per stage, because this project ships a learner workspace and an answer:

  src        the shipped stub. It must fail, otherwise the stage is already done for you.
  reference  the answer. It must pass, otherwise the stage is broken.

The first version of this script ran only `src`, so a complete checkout reported "0 of 7
stages passing" — the correct answer to a question nobody was asking. `scout` fixed it first;
this is the same script, so the three projects behave the same way.

Exit code is zero only when every stage's reference passes, every stub fails, and the shared
modules are byte-identical in `src/` and `reference/`.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

# Modules that are scaffolding rather than stage work. They must be identical in both trees,
# because a test that passes under one IMPL and fails under the other is a bug in the repo, not
# in your answer. The seven modules that differ are the seven stages.
SHARED = (
    "__init__.py",
    "actions.py",
    "audit.py",
    "baselines.py",
    "baselines_actions.py",
    "baselines_audit.py",
    "baselines_draft.py",
    "baselines_policy.py",
    "baselines_scoring.py",
    "checks.py",
    "evalmetrics.py",
    "policy.py",
    "stats.py",
    "tickets.py",
    "versions.py",
)


def run(test: pathlib.Path, impl: str) -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, str(test)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={"IMPL": impl, "PATH": "/usr/bin:/bin:/usr/local/bin"},
    )
    ok = result.returncode == 0
    detail = ""
    if not ok:
        tail = [line for line in result.stderr.splitlines() if line.strip()]
        detail = tail[-1][:58] if tail else ""
    return ok, detail


def check_shared() -> list[str]:
    problems = []
    for name in SHARED:
        left = ROOT / "src" / "triage" / name
        right = ROOT / "reference" / "triage" / name
        if not left.exists() or not right.exists():
            problems.append(f"{name} is missing from one tree")
        elif left.read_bytes() != right.read_bytes():
            problems.append(f"{name} differs between src/ and reference/")
    return problems


def main() -> int:
    stages = sorted(p for p in (ROOT / "stages").iterdir() if p.is_dir())
    if not stages:
        print("no stages found")
        return 1

    healthy = 0
    for stage in stages:
        tests = sorted(stage.glob("test_*.py"))
        if not tests:
            print(f"  {stage.name:<20} no tests")
            continue
        stub_ok, _ = run(tests[0], "src")
        reference_ok, reference_detail = run(tests[0], "reference")
        healthy += (not stub_ok) and reference_ok
        print(
            f"  {stage.name:<20} src {'PASS' if stub_ok else 'fail':<5}"
            f" reference {'PASS' if reference_ok else 'fail':<5}"
            f"{'' if reference_ok else reference_detail}"
        )

    print(f"\n  {healthy} of {len(stages)} stages healthy")

    problems = check_shared()
    if problems:
        print("  shared modules drifted:")
        for problem in problems:
            print(f"    {problem}")
    else:
        print(f"  shared modules identical in src/ and reference/ ({len(SHARED)} files)")

    return 0 if healthy == len(stages) and not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
