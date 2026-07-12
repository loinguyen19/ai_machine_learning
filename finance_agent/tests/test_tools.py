"""Unit tests for mock financial-workflow tools — no LLM or API key required."""

from __future__ import annotations

import json

from tools import (
    check_document_consistency,
    check_watchlist,
    lookup_customer_account,
    search_knowledge_base,
    verify_id_format,
)


def _invoke(tool, **kwargs):
    return json.loads(tool.invoke(kwargs))


def test_verify_id_format_valid_national_id():
    result = _invoke(verify_id_format, id_type="national_id", id_number="012345678901")
    assert result["id_format_valid"] is True


def test_verify_id_format_invalid_national_id():
    result = _invoke(verify_id_format, id_type="national_id", id_number="12")
    assert result["id_format_valid"] is False


def test_verify_id_format_valid_passport():
    result = _invoke(verify_id_format, id_type="passport", id_number="B1234567")
    assert result["id_format_valid"] is True


def test_check_watchlist_hit():
    result = _invoke(check_watchlist, full_name="Nguyen Van Rui")
    assert result["watchlist_hit"] is True


def test_check_watchlist_clean():
    result = _invoke(check_watchlist, full_name="Le Thi Mai")
    assert result["watchlist_hit"] is False


def test_check_document_consistency_match():
    result = _invoke(
        check_document_consistency,
        name_on_document="Le Thi Mai",
        name_on_form="Le Thi Mai",
        dob_on_document="1995-04-02",
        dob_on_form="1995-04-02",
    )
    assert result["document_mismatch"] is False


def test_check_document_consistency_name_mismatch():
    result = _invoke(
        check_document_consistency,
        name_on_document="Le Thi Mai",
        name_on_form="Le Thi Mai Nguyen",
        dob_on_document="1995-04-02",
        dob_on_form="1995-04-02",
    )
    assert result["document_mismatch"] is True


def test_lookup_customer_account_found():
    result = _invoke(lookup_customer_account, account_id="ACC-1002")
    assert result["found"] is True
    assert result["recent_chargeback"] is True


def test_lookup_customer_account_not_found():
    result = _invoke(lookup_customer_account, account_id="ACC-9999")
    assert result["found"] is False


def test_search_knowledge_base_match():
    result = _invoke(search_knowledge_base, query="I think my account was hacked")
    assert result["matched"] is True
    assert result["suggested_route"] == "fraud-team"


def test_search_knowledge_base_no_match():
    result = _invoke(search_knowledge_base, query="asdkjhaskjdh qwerty")
    assert result["matched"] is False
