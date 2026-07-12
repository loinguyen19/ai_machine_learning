"""KYC document-review agent.

Two-stage design:
  1. A ReAct tool-calling agent gathers evidence (ID format check, watchlist
     screen, document consistency check) and writes a free-text investigation
     summary.
  2. A structured-output call turns that summary plus the raw tool evidence
     into a schema-validated KYCDecision.
  3. Deterministic guardrails (guardrails.py) can override the LLM's decision
     when tool evidence contradicts it — the model never gets the final word
     on a watchlist hit or a failed document check.

Keeping "the model decides" and "the system enforces policy" as separate,
auditable steps is the difference between a demo and something you could
actually ship into a compliance-sensitive workflow.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.messages import ToolMessage

from guardrails import apply_kyc_guardrails
from llm import create_llm
from schemas import KYCDecision
from tools import KYC_TOOLS

SRC_DIR = Path(__file__).resolve().parent
load_dotenv(SRC_DIR.parent / ".env")

INVESTIGATION_SYSTEM_PROMPT = """You are a KYC (Know Your Customer) review assistant \
for a fintech onboarding flow.

Given a new customer's submitted onboarding details, investigate using the \
available tools before concluding anything:
1. Check the ID number format with verify_id_format.
2. Screen the full legal name with check_watchlist.
3. Compare the ID document fields against the form with check_document_consistency.

After calling the tools you need, write a short investigation summary in plain \
English: what you checked, what you found, and what you would recommend \
(approve / reject / escalate to a human reviewer) and why. Do not skip tool calls \
to save time — every case must be checked against all three tools.
"""

DECISION_SYSTEM_PROMPT = """You convert a KYC investigation summary and its raw \
tool evidence into a final structured decision.

Rules:
- "approve" only if there is no watchlist hit, no document mismatch, and the ID \
format is valid.
- "reject" if the ID format is invalid.
- "escalate" if anything is ambiguous, borderline, or the evidence conflicts.
- confidence should reflect how certain you are given the evidence, not how \
certain you sound.
"""


def _tool_evidence(messages: list[Any]) -> dict:
    evidence: dict[str, Any] = {}
    for message in messages:
        if isinstance(message, ToolMessage):
            try:
                payload = json.loads(message.content)
            except (TypeError, ValueError):
                continue
            evidence.update(payload)
    return evidence


def review_case(case: dict, llm=None) -> dict:
    """Run the two-stage KYC review for one onboarding case. Returns a full audit trail."""
    llm = llm or create_llm()
    investigator = create_agent(llm, tools=KYC_TOOLS, system_prompt=INVESTIGATION_SYSTEM_PROMPT)

    case_text = (
        f"Full name: {case['full_name']}\n"
        f"ID type: {case['id_type']}\n"
        f"ID number: {case['id_number']}\n"
        f"Name on document (OCR): {case['name_on_document']}\n"
        f"DOB on form: {case['dob_on_form']}\n"
        f"DOB on document (OCR): {case['dob_on_document']}\n"
    )

    start = time.perf_counter()
    result = investigator.invoke({"messages": [("user", case_text)]})
    messages = result.get("messages", [])
    evidence = _tool_evidence(messages)
    investigation_summary = str(getattr(messages[-1], "content", "")) if messages else ""

    structured_llm = llm.with_structured_output(KYCDecision)
    raw_decision = structured_llm.invoke(
        [
            ("system", DECISION_SYSTEM_PROMPT),
            (
                "user",
                f"Investigation summary:\n{investigation_summary}\n\n"
                f"Raw tool evidence:\n{json.dumps(evidence, indent=2)}",
            ),
        ]
    )
    final_decision = apply_kyc_guardrails(raw_decision, evidence)
    elapsed = time.perf_counter() - start

    return {
        "case": case,
        "evidence": evidence,
        "investigation_summary": investigation_summary,
        "model_decision": raw_decision.model_dump(),
        "final_decision": final_decision.model_dump(),
        "guardrail_overrode_model": raw_decision.status != final_decision.status,
        "latency_seconds": round(elapsed, 2),
    }


def _print_result(result: dict) -> None:
    final = result["final_decision"]
    print(f"\nCase: {result['case']['full_name']} ({result['case']['id_type']})")
    print(f"Final status: {final['status'].upper()}  (confidence={final['confidence']:.2f})")
    if result["guardrail_overrode_model"]:
        print(f"  [guardrail overrode model decision: model said '{result['model_decision']['status']}']")
    for reason in final["reasons"]:
        print(f"  - {reason}")
    print(f"  latency: {result['latency_seconds']}s")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the KYC review agent on a case.")
    parser.add_argument("--case-file", type=str, help="Path to a JSON file with one onboarding case")
    return parser.parse_args()


_DEMO_CASE = {
    "full_name": "Le Thi Mai",
    "id_type": "national_id",
    "id_number": "012345678901",
    "name_on_document": "Le Thi Mai",
    "dob_on_form": "1995-04-02",
    "dob_on_document": "1995-04-02",
}


def main() -> None:
    args = parse_args()
    if args.case_file:
        case = json.loads(Path(args.case_file).read_text())
    else:
        case = _DEMO_CASE
        print("No --case-file given, running the built-in demo case.\n")

    result = review_case(case)
    _print_result(result)


if __name__ == "__main__":
    main()
