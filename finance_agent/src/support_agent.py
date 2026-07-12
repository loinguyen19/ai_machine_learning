"""Support-ticket triage agent.

Classifies an inbound support message, checks account context and a small
knowledge base (stand-in for a RAG vector store), and produces a structured
TicketTriage decision with a policy-guardrail pass on top — same two-stage
"agent investigates, structured call decides, guardrail enforces policy"
pattern as kyc_agent.py, applied to a CRM/support-automation workflow.
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

from guardrails import apply_ticket_guardrails
from llm import create_llm
from schemas import TicketTriage
from tools import SUPPORT_TOOLS

SRC_DIR = Path(__file__).resolve().parent
load_dotenv(SRC_DIR.parent / ".env")

TRIAGE_SYSTEM_PROMPT = """You are a support-ticket triage assistant for a finance app.

Given a customer's account id and message:
1. Look up their account with lookup_customer_account.
2. Search the knowledge base with search_knowledge_base using the customer's message.

Then write a short summary of the issue and your reasoning for how to route it.
"""

DECISION_SYSTEM_PROMPT = """Convert a triage summary and its raw evidence into a \
final structured TicketTriage decision.

Rules:
- category "fraud_risk" for anything about unauthorized access, hacking, or \
account takeover.
- priority should reflect urgency to the customer, not just category.
- route_to should be a short team name (e.g. "fraud-team", "payments-support").
- confidence should reflect how certain you are given the evidence.
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


def triage_ticket(ticket: dict, llm=None) -> dict:
    """Run the two-stage triage for one support ticket. Returns a full audit trail."""
    llm = llm or create_llm()
    agent = create_agent(llm, tools=SUPPORT_TOOLS, system_prompt=TRIAGE_SYSTEM_PROMPT)

    ticket_text = f"Account: {ticket['account_id']}\nMessage: {ticket['message']}"

    start = time.perf_counter()
    result = agent.invoke({"messages": [("user", ticket_text)]})
    messages = result.get("messages", [])
    evidence = _tool_evidence(messages)
    triage_summary = str(getattr(messages[-1], "content", "")) if messages else ""

    structured_llm = llm.with_structured_output(TicketTriage)
    raw_triage = structured_llm.invoke(
        [
            ("system", DECISION_SYSTEM_PROMPT),
            (
                "user",
                f"Triage summary:\n{triage_summary}\n\nRaw evidence:\n{json.dumps(evidence, indent=2)}",
            ),
        ]
    )
    final_triage = apply_ticket_guardrails(raw_triage, evidence)
    elapsed = time.perf_counter() - start

    return {
        "ticket": ticket,
        "evidence": evidence,
        "triage_summary": triage_summary,
        "model_triage": raw_triage.model_dump(),
        "final_triage": final_triage.model_dump(),
        "guardrail_overrode_model": raw_triage.model_dump() != final_triage.model_dump(),
        "latency_seconds": round(elapsed, 2),
    }


def _print_result(result: dict) -> None:
    final = result["final_triage"]
    print(f"\nTicket: {result['ticket']['account_id']} — \"{result['ticket']['message']}\"")
    print(f"Route: {final['route_to']}  priority={final['priority']}  category={final['category']}")
    if result["guardrail_overrode_model"]:
        print(f"  [guardrail adjusted model output: {result['model_triage']}]")
    for reason in final["reasons"]:
        print(f"  - {reason}")
    print(f"  latency: {result['latency_seconds']}s")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the support triage agent on a ticket.")
    parser.add_argument("--ticket-file", type=str, help="Path to a JSON file with one ticket")
    return parser.parse_args()


_DEMO_TICKET = {
    "account_id": "ACC-1002",
    "message": "Someone I don't recognize logged into my account and I think it's been hacked.",
}


def main() -> None:
    args = parse_args()
    if args.ticket_file:
        ticket = json.loads(Path(args.ticket_file).read_text())
    else:
        ticket = _DEMO_TICKET
        print("No --ticket-file given, running the built-in demo ticket.\n")

    result = triage_ticket(ticket)
    _print_result(result)


if __name__ == "__main__":
    main()
