"""Deterministic guardrails applied after the LLM proposes a decision.

The model's own status and confidence score are never trusted outright for
high-risk outcomes — hard facts returned by tools always win. Compliance-critical
systems need a policy layer the LLM cannot argue its way around.
"""

from __future__ import annotations

from schemas import KYCDecision, TicketTriage

KYC_CONFIDENCE_FLOOR = 0.6
TICKET_CONFIDENCE_FLOOR = 0.5


def apply_kyc_guardrails(decision: KYCDecision, evidence: dict) -> KYCDecision:
    status = decision.status
    reasons = list(decision.reasons)

    if evidence.get("watchlist_hit"):
        status = "escalate"
        reasons.append("guardrail: watchlist hit forces manual escalation")

    if evidence.get("document_mismatch"):
        status = "escalate"
        reasons.append("guardrail: document/form mismatch forces manual escalation")

    if evidence.get("id_format_valid") is False:
        status = "reject"
        reasons.append("guardrail: ID number fails format check")

    if status == "approve" and decision.confidence < KYC_CONFIDENCE_FLOOR:
        status = "escalate"
        reasons.append(
            f"guardrail: confidence {decision.confidence:.2f} below floor {KYC_CONFIDENCE_FLOOR}"
        )

    return KYCDecision(status=status, confidence=decision.confidence, reasons=reasons)


def apply_ticket_guardrails(triage: TicketTriage, evidence: dict) -> TicketTriage:
    priority = triage.priority
    route_to = triage.route_to
    reasons = list(triage.reasons)

    if evidence.get("recent_chargeback") and triage.category == "payment_issue":
        priority = "urgent"
        reasons.append("guardrail: recent chargeback on account forces urgent priority")

    if triage.category == "fraud_risk":
        route_to = "fraud-team"
        priority = "urgent"
        reasons.append("guardrail: fraud_risk category always routes to fraud-team at urgent priority")

    if triage.confidence < TICKET_CONFIDENCE_FLOOR:
        route_to = "human-review-queue"
        reasons.append(
            f"guardrail: confidence {triage.confidence:.2f} below floor {TICKET_CONFIDENCE_FLOOR}, "
            "routing to human review"
        )

    return TicketTriage(
        category=triage.category,
        priority=priority,
        route_to=route_to,
        confidence=triage.confidence,
        reasons=reasons,
    )
