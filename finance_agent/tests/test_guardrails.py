"""Unit tests for deterministic guardrails — no LLM or API key required.

These enforce the invariant a compliance-sensitive workflow actually cares about:
the model does not get the final word on accuracy/compliance-critical outcomes.
"""

from __future__ import annotations

from src.guardrails import apply_kyc_guardrails, apply_ticket_guardrails
from schemas import KYCDecision, TicketTriage


def test_watchlist_hit_forces_escalate_even_if_model_says_approve():
    model_decision = KYCDecision(status="approve", confidence=0.95, reasons=["looks clean"])
    final = apply_kyc_guardrails(model_decision, {"watchlist_hit": True})
    assert final.status == "escalate"


def test_invalid_id_format_forces_reject():
    model_decision = KYCDecision(status="approve", confidence=0.9, reasons=["looks fine"])
    final = apply_kyc_guardrails(model_decision, {"id_format_valid": False})
    assert final.status == "reject"


def test_document_mismatch_forces_escalate():
    model_decision = KYCDecision(status="approve", confidence=0.9, reasons=[])
    final = apply_kyc_guardrails(model_decision, {"document_mismatch": True})
    assert final.status == "escalate"


def test_low_confidence_approve_gets_escalated():
    model_decision = KYCDecision(status="approve", confidence=0.3, reasons=[])
    final = apply_kyc_guardrails(model_decision, {})
    assert final.status == "escalate"


def test_clean_evidence_leaves_approve_untouched():
    model_decision = KYCDecision(status="approve", confidence=0.9, reasons=["all checks passed"])
    final = apply_kyc_guardrails(
        model_decision,
        {"watchlist_hit": False, "document_mismatch": False, "id_format_valid": True},
    )
    assert final.status == "approve"


def test_fraud_risk_always_routes_to_fraud_team():
    model_triage = TicketTriage(
        category="fraud_risk",
        priority="low",
        route_to="general-support",
        confidence=0.8,
        reasons=["customer sounded calm"],
    )
    final = apply_ticket_guardrails(model_triage, {})
    assert final.route_to == "fraud-team"
    assert final.priority == "urgent"


def test_recent_chargeback_forces_urgent_priority():
    model_triage = TicketTriage(
        category="payment_issue",
        priority="low",
        route_to="payments-support",
        confidence=0.7,
        reasons=[],
    )
    final = apply_ticket_guardrails(model_triage, {"recent_chargeback": True})
    assert final.priority == "urgent"


def test_low_confidence_ticket_routes_to_human_review():
    model_triage = TicketTriage(
        category="general_inquiry",
        priority="low",
        route_to="general-support",
        confidence=0.2,
        reasons=[],
    )
    final = apply_ticket_guardrails(model_triage, {})
    assert final.route_to == "human-review-queue"
