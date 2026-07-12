"""Structured output contracts for agent decisions.

The agent may reason freely, but every decision that leaves this codebase must
satisfy one of these schemas — this is the "predictable behavior" boundary
between free-text model output and something a downstream system can act on.
"""

from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field


class KYCDecision(BaseModel):
    status: Literal["approve", "reject", "escalate"]
    confidence: float = Field(ge=0.0, le=1.0)
    reasons: list[str]


class TicketTriage(BaseModel):
    category: Literal["fraud_risk", "account_access", "payment_issue", "general_inquiry"]
    priority: Literal["low", "medium", "high", "urgent"]
    route_to: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasons: list[str]
