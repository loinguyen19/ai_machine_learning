"""Mock financial-workflow tools.

All data here is synthetic and in-memory — this project ships no real customer
data, PII, or connections to a real KYC/AML vendor, CRM, or core banking system.
Swap a function body for a real API call (sanctions-screening vendor, CRM,
document-OCR service, vector DB) to move a tool from demo to production; the
agent and guardrail code around it does not need to change.
"""

from __future__ import annotations

import json
import re

from langchain.tools import tool

# ---- KYC mock data ---------------------------------------------------------

_WATCHLIST = {
    "NGUYEN VAN RUI",
    "TRAN THI SANCTION",
    "PEP TEST SUBJECT",
}

_ID_PATTERNS = {
    "national_id": re.compile(r"^\d{12}$"),
    "passport": re.compile(r"^[A-Z]\d{7,8}$"),
}


@tool
def verify_id_format(id_type: str, id_number: str) -> str:
    """Check whether an ID number matches the expected format for its type.

    Args:
        id_type: "national_id" (12 digits) or "passport" (1 letter + 7-8 digits).
        id_number: the raw ID number as submitted.
    """
    pattern = _ID_PATTERNS.get(id_type.strip().lower())
    valid = bool(pattern and pattern.match(id_number.strip().upper()))
    return json.dumps({
        "tool": "verify_id_format",
        "id_type": id_type,
        "id_format_valid": valid,
    })


@tool
def check_watchlist(full_name: str) -> str:
    """Screen a full legal name against a mock sanctions/PEP watchlist.

    Args:
        full_name: the customer's full legal name as submitted on the onboarding form.
    """
    hit = full_name.strip().upper() in _WATCHLIST
    return json.dumps({
        "tool": "check_watchlist",
        "full_name": full_name,
        "watchlist_hit": hit,
    })


@tool
def check_document_consistency(
    name_on_document: str,
    name_on_form: str,
    dob_on_document: str,
    dob_on_form: str,
) -> str:
    """Compare OCR-extracted ID document fields against the onboarding form.

    Args:
        name_on_document: name as read from the submitted ID document (OCR).
        name_on_form: name as typed by the customer on the onboarding form.
        dob_on_document: date of birth as read from the ID document (OCR).
        dob_on_form: date of birth as typed on the onboarding form.
    """
    name_match = name_on_document.strip().upper() == name_on_form.strip().upper()
    dob_match = dob_on_document.strip() == dob_on_form.strip()
    return json.dumps({
        "tool": "check_document_consistency",
        "document_mismatch": not (name_match and dob_match),
        "name_match": name_match,
        "dob_match": dob_match,
    })


KYC_TOOLS = [verify_id_format, check_watchlist, check_document_consistency]

# ---- Support/CRM mock data --------------------------------------------------

_ACCOUNTS = {
    "ACC-1001": {"tier": "standard", "open_tickets": 0, "recent_chargeback": False},
    "ACC-1002": {"tier": "premium", "open_tickets": 2, "recent_chargeback": True},
    "ACC-1003": {"tier": "standard", "open_tickets": 1, "recent_chargeback": False},
}

_KNOWLEDGE_BASE = [
    {
        "id": "KB-101",
        "title": "Card declined at merchant",
        "keywords": ["declined", "card", "payment failed", "transaction failed"],
        "route_to": "payments-support",
    },
    {
        "id": "KB-102",
        "title": "Suspicious login / account takeover",
        "keywords": ["hacked", "unauthorized login", "suspicious activity", "someone accessed", "don't recognize"],
        "route_to": "fraud-team",
    },
    {
        "id": "KB-103",
        "title": "Cannot reset password",
        "keywords": ["password", "reset", "locked out", "cannot log in", "login"],
        "route_to": "account-access-support",
    },
    {
        "id": "KB-104",
        "title": "General product question",
        "keywords": ["how do i", "what is", "fee", "limit"],
        "route_to": "general-support",
    },
]


@tool
def lookup_customer_account(account_id: str) -> str:
    """Look up a customer account's tier, open ticket count, and chargeback flag.

    Args:
        account_id: the account identifier, e.g. "ACC-1001".
    """
    account = _ACCOUNTS.get(account_id.strip().upper())
    if account is None:
        return json.dumps({"tool": "lookup_customer_account", "found": False})
    return json.dumps({"tool": "lookup_customer_account", "found": True, **account})


@tool
def search_knowledge_base(query: str) -> str:
    """Retrieve the closest matching support runbook article for a customer query.

    Simple keyword-overlap retrieval over a small in-memory knowledge base — a
    stand-in for a vector database lookup in a production RAG pipeline.

    Args:
        query: the customer's support message.
    """
    q = query.lower()
    scored = []
    for article in _KNOWLEDGE_BASE:
        score = sum(1 for kw in article["keywords"] if kw in q)
        if score:
            scored.append((score, article))
    if not scored:
        return json.dumps({"tool": "search_knowledge_base", "matched": False})
    scored.sort(key=lambda pair: pair[0], reverse=True)
    best = scored[0][1]
    return json.dumps({
        "tool": "search_knowledge_base",
        "matched": True,
        "article_id": best["id"],
        "title": best["title"],
        "suggested_route": best["route_to"],
    })


SUPPORT_TOOLS = [lookup_customer_account, search_knowledge_base]
