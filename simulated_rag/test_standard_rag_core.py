"""Tests for the naive/standard RAG simulation — no LLM, no network, pure math/logic."""

from __future__ import annotations

import math

import pytest

from standard_rag_core import StandardRagSimulator


# ----------------------------------------------------------------------
# chunk()
# ----------------------------------------------------------------------


def test_chunk_sliding_window_with_overlap():
    tokens = ["a", "b", "c", "d", "e"]
    assert StandardRagSimulator.chunk(tokens, max_tokens=3, overlap=1) == ["a b c", "c d e"]


def test_chunk_no_overlap():
    tokens = ["a", "b", "c", "d"]
    assert StandardRagSimulator.chunk(tokens, max_tokens=2, overlap=0) == ["a b", "c d"]


def test_chunk_shorter_than_max_tokens_returns_single_chunk():
    assert StandardRagSimulator.chunk(["a", "b"], max_tokens=5, overlap=1) == ["a b"]


def test_chunk_empty_input_returns_empty_list():
    assert StandardRagSimulator.chunk([], max_tokens=3, overlap=1) == []


def test_chunk_rejects_overlap_gte_max_tokens():
    with pytest.raises(ValueError):
        StandardRagSimulator.chunk(["a", "b", "c"], max_tokens=2, overlap=2)


def test_chunk_rejects_non_positive_max_tokens():
    with pytest.raises(ValueError):
        StandardRagSimulator.chunk(["a", "b"], max_tokens=0, overlap=0)


# ----------------------------------------------------------------------
# cosine_similarity()
# ----------------------------------------------------------------------


def test_cosine_similarity_same_direction_different_magnitude_is_one():
    assert StandardRagSimulator.cosine_similarity((1, 0, 0), (2, 0, 0)) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal_is_zero():
    assert StandardRagSimulator.cosine_similarity((1, 0), (0, 1)) == pytest.approx(0.0)


def test_cosine_similarity_45_degrees():
    # (1, 0) vs (1, 1): dot=1, ||a||=1, ||b||=sqrt(2) -> 1/sqrt(2) ~= 0.7071
    score = StandardRagSimulator.cosine_similarity((1, 0), (1, 1))
    assert score == pytest.approx(1 / math.sqrt(2))


def test_cosine_similarity_zero_vector_returns_zero_not_crash():
    assert StandardRagSimulator.cosine_similarity((0, 0, 0), (1, 2, 3)) == 0.0


def test_cosine_similarity_dimension_mismatch_raises():
    with pytest.raises(ValueError):
        StandardRagSimulator.cosine_similarity((1, 0), (1, 0, 0))


# ----------------------------------------------------------------------
# top_k()
# ----------------------------------------------------------------------


def _candidates():
    return [
        {"d1": (1.0, 0.0, 0.0)},
        {"d2": (0.0, 1.0, 0.0)},
        {"d3": (0.7, 0.7, 0.0)},
    ]


def test_top_k_ranks_best_first_and_drops_worst():
    result = StandardRagSimulator.top_k((1.0, 0.0, 0.0), _candidates(), k=2)
    assert result == [{"d1": (1.0, 0.0, 0.0)}, {"d3": (0.7, 0.7, 0.0)}]


def test_top_k_with_scores():
    result = StandardRagSimulator.top_k((1.0, 0.0, 0.0), _candidates(), k=3, return_scores=True)
    doc_ids = [next(iter(d)) for d, _ in result]
    scores = [score for _, score in result]
    assert doc_ids == ["d1", "d3", "d2"]
    assert scores == sorted(scores, reverse=True)
    assert scores[0] == pytest.approx(1.0)
    assert scores[-1] == pytest.approx(0.0)


def test_top_k_zero_returns_empty():
    assert StandardRagSimulator.top_k((1.0, 0.0, 0.0), _candidates(), k=0) == []


def test_top_k_rejects_multi_key_candidate():
    with pytest.raises(ValueError):
        StandardRagSimulator.top_k((1.0, 0.0), [{"d1": (1.0, 0.0), "d2": (0.0, 1.0)}], k=1)


# ----------------------------------------------------------------------
# build_context()
# ----------------------------------------------------------------------


def test_build_context_packs_whole_chunks_within_budget():
    assert StandardRagSimulator.build_context(["aa bb", "cc dd"], max_tokens=4) == "aa bb cc dd"


def test_build_context_stops_before_exceeding_budget():
    result = StandardRagSimulator.build_context(["aa bb", "cc dd", "ee ff gg"], max_tokens=4)
    assert result == "aa bb cc dd"


def test_build_context_never_cuts_a_chunk_in_half():
    # "cc dd ee" (3 tokens) would push total to 5 > max_tokens=4, so it's dropped whole.
    result = StandardRagSimulator.build_context(["aa bb", "cc dd ee"], max_tokens=4)
    assert result == "aa bb"


def test_build_context_truncates_an_oversized_first_chunk_instead_of_returning_empty():
    result = StandardRagSimulator.build_context(["a b c d e"], max_tokens=3)
    assert result == "a b c"
