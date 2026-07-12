"""End-to-end evaluation harness — requires a working LLM provider key.

Runs the KYC and support-triage agents against the fixture cases in this folder
and checks outcomes. Two kinds of checks:

  - "hard" checks (kyc_cases.jsonl): guardrail-enforced invariants that must
    always hold, e.g. a watchlist hit must never end in "approve". These are
    expected to pass every run regardless of model variance.
  - "soft" checks (support_cases.jsonl): expected model classification,
    reported but a mismatch just means the model judged the case differently —
    not a bug in the same way a hard-check failure is.

This is a live, non-deterministic eval — unlike tests/test_guardrails.py and
tests/test_tools.py, which are pure unit tests that need no API key at all.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

EVALS_DIR = Path(__file__).resolve().parent
SRC_DIR = EVALS_DIR.parent / "src"
sys.path.insert(0, str(SRC_DIR))

from kyc_agent import review_case  # noqa: E402
from llm import create_llm  # noqa: E402
from support_agent import triage_ticket  # noqa: E402


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def run_kyc_evals(llm) -> tuple[int, int]:
    cases = _load_jsonl(EVALS_DIR / "kyc_cases.jsonl")
    print(f"cases: {cases}")
    passed = 0
    print("\n=== KYC agent evals (hard, guardrail-enforced) ===")
    for spec in cases:
        result = review_case(spec["case"], llm=llm)
        actual = result["final_decision"]["status"]
        expected = spec["expected_status"]
        ok = actual == expected
        passed += ok
        print(f"[{'PASS' if ok else 'FAIL'}] {spec['note']}")
        print(f"       expected={expected} actual={actual} latency={result['latency_seconds']}s")
    return passed, len(cases)


def run_support_evals(llm) -> tuple[int, int]:
    cases = _load_jsonl(EVALS_DIR / "support_cases.jsonl")
    passed = 0
    print("\n=== Support triage agent evals (soft, model classification) ===")
    for spec in cases:
        result = triage_ticket(spec["ticket"], llm=llm)
        actual = result["final_triage"]["category"]
        expected = spec["expected_category"]
        ok = actual == expected
        passed += ok
        print(f"[{'PASS' if ok else 'FAIL'}] {spec['note']}")
        print(
            f"       expected_category={expected} actual_category={actual} "
            f"route={result['final_triage']['route_to']} priority={result['final_triage']['priority']} "
            f"latency={result['latency_seconds']}s"
        )
    return passed, len(cases)


def main() -> None:
    llm = create_llm()
    start = time.perf_counter()

    kyc_passed, kyc_total = run_kyc_evals(llm)
    support_passed, support_total = run_support_evals(llm)

    total_passed = kyc_passed + support_passed
    total = kyc_total + support_total
    elapsed = time.perf_counter() - start

    print(f"\n=== Summary: {total_passed}/{total} passed in {elapsed:.1f}s ===")
    if kyc_passed < kyc_total:
        sys.exit(1)


if __name__ == "__main__":
    main()
