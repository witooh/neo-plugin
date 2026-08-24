#!/usr/bin/env python3
"""Lock the neocheck.py exit-code contract. Stdlib only. No docker, no model.

  python3 skills/using-neo/assets/neocheck_test.py

Exit 0 = every case matched. Exit 1 = a case drifted.
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
NEOCHECK = os.path.join(HERE, "neocheck.py")
KEY = "GI-123"


def run_neocheck(repo):
    p = subprocess.run(
        [sys.executable, NEOCHECK, repo, KEY, "--timeout", "30"],
        capture_output=True,
        text=True,
    )
    return p.returncode, p.stdout + p.stderr


def write(path, body):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(body)


def spec_md(*acs):
    lines = ["# GI-123\n"]
    for ac in acs:
        lines.append(f"{ac} caller can create an account\n")
    return "".join(lines)


def e2e_ts(*acs):
    body = []
    for ac in acs:
        body.append(f'it("[GI-123 - {ac}] create account → 201", async () => {{}});\n')
    return "".join(body)


def case_no_gate(repo):
    """Empty repo: every machine gate SKIP → exit 3, not 0."""
    rc, out = run_neocheck(repo)
    if rc != 3:
        return f"no-gate: expected exit 3, got {rc}\n{out}"
    if "NO MACHINE GATE APPLIED" not in out:
        return f"no-gate: missing NO MACHINE GATE APPLIED\n{out}"
    return None


def case_e2e_without_ac_source(repo):
    """e2e suite present, no spec.md → AC FAIL → exit 1. Not SKIP-as-green."""
    os.makedirs(os.path.join(repo, "tests", "e2e", "specs"))
    rc, out = run_neocheck(repo)
    if rc != 1:
        return f"e2e-without-ac: expected exit 1, got {rc}\n{out}"
    if "FAIL" not in out or "no AC source" not in out:
        return f"e2e-without-ac: expected AC FAIL for missing spec.md\n{out}"
    return None


def case_ac_001_covered(repo):
    """spec.md AC-001 + matching e2e title → AC PASS, others SKIP → exit 0."""
    write(os.path.join(repo, "docs", "tasks", KEY, "spec.md"), spec_md("AC-001"))
    write(
        os.path.join(repo, "tests", "e2e", "specs", "create.e2e.ts"),
        e2e_ts("AC-001"),
    )
    rc, out = run_neocheck(repo)
    if rc != 0:
        return f"ac-001-covered: expected exit 0, got {rc}\n{out}"
    if "FAIL" in out.split("\n")[0:20] and "FAIL —" in out:
        return f"ac-001-covered: unexpected FAIL summary\n{out}"
    if "PASS —" not in out:
        return f"ac-001-covered: missing PASS summary\n{out}"
    return None


def case_ac_002_uncovered(repo):
    """AC-001 covered, AC-002 declared and missing a test → exit 1."""
    write(os.path.join(repo, "docs", "tasks", KEY, "spec.md"), spec_md("AC-001", "AC-002"))
    write(
        os.path.join(repo, "tests", "e2e", "specs", "create.e2e.ts"),
        e2e_ts("AC-001"),
    )
    rc, out = run_neocheck(repo)
    if rc != 1:
        return f"ac-002-uncovered: expected exit 1, got {rc}\n{out}"
    if "FAIL — AC coverage" not in out:
        return f"ac-002-uncovered: expected AC coverage fail summary\n{out}"
    return None


def main():
    if not os.path.isfile(NEOCHECK):
        sys.stderr.write(f"missing {NEOCHECK}\n")
        sys.exit(2)
    cases = (
        ("no-gate → 3", case_no_gate),
        ("e2e-without-ac → 1", case_e2e_without_ac_source),
        ("ac-001-covered → 0", case_ac_001_covered),
        ("ac-002-uncovered → 1", case_ac_002_uncovered),
    )
    failed = []
    for name, fn in cases:
        with tempfile.TemporaryDirectory() as tmp:
            err = fn(tmp)
        if err:
            failed.append(f"{name}: {err}")
            print(f"FAIL  {name}")
        else:
            print(f"PASS  {name}")
    if failed:
        sys.stderr.write("\n" + "\n".join(failed) + "\n")
        sys.exit(1)
    print(f"\n{len(cases)} cases green")


if __name__ == "__main__":
    main()
