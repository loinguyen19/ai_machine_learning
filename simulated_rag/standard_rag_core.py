"""Minimal, dependency-free simulation of NAIVE / STANDARD RAG.

Real RAG = chunk documents -> embed chunks -> store vectors -> at query time,
embed the query -> rank stored vectors by similarity -> take the top k ->
assemble a token-bounded context -> hand that context to an LLM.

This file simulates every step except the embedding model itself: vectors are
passed in as plain tuples of floats instead of being produced by a real
embedding API, so the ranking/selection/assembly logic can be rehearsed and
tested without any network call or ML dependency.

This is the "naive/standard" RAG strategy specifically: one flat chunk
granularity serves both matching (embedding + cosine similarity) and context
(what gets handed to the LLM) — there is no dual granularity and no
post-retrieval transformation. Contrast with:
  - sentence_window_rag_core.py: matches at sentence granularity, but expands
    to a stored neighbor window before building context.
  - auto_merging_rag_core.py: matches at child-chunk granularity, but merges
    up to the parent chunk when enough children of one parent are retrieved.

See findings_rag_underneath.md (Q4/Q5) for the full comparison.
"""

from __future__ import annotations

import math
from typing import Sequence


class StandardRagSimulator:
    """Groups the four pipeline stages as methods, mirroring how this is
    typically framed as a small class in a live-coding exercise.

    None of the methods hold instance state — they're stateless on purpose,
    so each stage stays independently testable.
    """

    # ------------------------------------------------------------------
    # Stage 1: chunking
    # ------------------------------------------------------------------
    @staticmethod
    def chunk(tokens: Sequence[str], max_tokens: int = 3, overlap: int = 1) -> list[str]:
        """Sliding-window chunking over a sequence of tokens.

        Each chunk is up to `max_tokens` tokens joined with a single space.
        Consecutive chunks share `overlap` trailing/leading tokens, which is
        the standard RAG trick to avoid cutting a sentence/idea exactly at a
        chunk boundary and losing it from every chunk's context.

        Example: chunk(['a','b','c','d','e'], max_tokens=3, overlap=1)
                 -> ['a b c', 'c d e']

        Raises:
            ValueError: if max_tokens <= 0, overlap < 0, or overlap >= max_tokens
                (an overlap that large or larger would never advance the window).
        """
        if max_tokens <= 0:
            raise ValueError("max_tokens must be > 0")
        if overlap < 0:
            raise ValueError("overlap must be >= 0")
        if overlap >= max_tokens:
            raise ValueError("overlap must be < max_tokens, or the window never advances")

        tokens = list(tokens)
        if not tokens:
            return []

        step = max_tokens - overlap
        chunks: list[str] = []
        i = 0
        n = len(tokens)
        while i < n:
            window = tokens[i : i + max_tokens]
            chunks.append(" ".join(window))
            if i + max_tokens >= n:
                break
            i += step
        return chunks

    # ------------------------------------------------------------------
    # Stage 2: pairwise vector similarity (the actual math)
    # ------------------------------------------------------------------
    @staticmethod
    def cosine_similarity(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
        """Cosine similarity between two equal-length vectors.

        cos(theta) = (a . b) / (||a|| * ||b||)

        This measures *direction*, not magnitude: (1, 0, 0) vs (2, 0, 0) -> 1.0
        (same direction, different length -> identical similarity), while
        (1, 0) vs (0, 1) -> 0.0 (orthogonal, i.e. "unrelated").

        Returns 0.0 for a zero vector instead of raising ZeroDivisionError,
        since "similarity to a null embedding" is undefined but a hard crash
        would take down a whole retrieval batch over one bad vector.
        """
        if len(vec_a) != len(vec_b):
            raise ValueError(f"vector dimension mismatch: {len(vec_a)} vs {len(vec_b)}")

        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    # ------------------------------------------------------------------
    # Stage 3: retrieval — rank candidates against a query, keep the top k
    # ------------------------------------------------------------------
    @staticmethod
    def top_k(
        query: Sequence[float],
        candidates: Sequence[dict[str, Sequence[float]]],
        k: int,
        return_scores: bool = False,
    ) -> list[dict[str, Sequence[float]]] | list[tuple[dict[str, Sequence[float]], float]]:
        """Rank each candidate against `query` by cosine similarity, return the top k.

        `candidates` is a sequence of single-key dicts, e.g.
            [{'d1': (1, 0, 0)}, {'d2': (0, 1, 0)}, {'d3': (0.7, 0.7, 0)}]
        (one document id -> one embedding vector each). This mirrors how a
        real vector store hands back `(doc_id, vector)` pairs.

        Ties and ordering: sorted purely by score, descending; Python's sort
        is stable so candidates with equal scores keep their input order.

        Set `return_scores=True` to also get each item's similarity score back
        — real retrieval code almost always wants this too, e.g. to apply a
        "drop anything below 0.75" confidence gate before it ever reaches the
        LLM.
        """
        if k <= 0:
            return []

        scored: list[tuple[float, dict[str, Sequence[float]]]] = []
        for candidate in candidates:
            if len(candidate) != 1:
                raise ValueError("each candidate must be a single {doc_id: vector} dict")
            _, vector = next(iter(candidate.items()))
            score = StandardRagSimulator.cosine_similarity(query, vector)
            scored.append((score, candidate))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        top = scored[:k]

        if return_scores:
            return [(candidate, score) for score, candidate in top]
        return [candidate for _, candidate in top]

    # ------------------------------------------------------------------
    # Stage 4: context assembly — pack retrieved chunks into a token budget
    # ------------------------------------------------------------------
    @staticmethod
    def build_context(chunks: Sequence[str], max_tokens: int) -> str:
        """Concatenate `chunks` (already ranked, best first) into one string
        without exceeding `max_tokens` whitespace-separated tokens.

        Whole chunks are packed in order — a chunk is either included in
        full or not at all, never cut mid-chunk, so the LLM never receives a
        half-sentence. That's why this is a separate stage from chunk(): the
        chunk size used for retrieval granularity and the final context
        token budget are two independent numbers in real RAG systems.

        Example: build_context(["aa bb", "cc dd"], max_tokens=4)
                 -> "aa bb cc dd"

        Edge case: if the very first chunk alone exceeds `max_tokens`, it is
        truncated to the first `max_tokens` tokens rather than returning an
        empty context — an LLM call with *some* grounding beats one with none.
        """
        if max_tokens <= 0:
            raise ValueError("max_tokens must be > 0")

        selected: list[str] = []
        used = 0
        for chunk in chunks:
            chunk_tokens = chunk.split()
            if not selected and len(chunk_tokens) > max_tokens:
                return " ".join(chunk_tokens[:max_tokens])
            if used + len(chunk_tokens) > max_tokens:
                break
            selected.append(chunk)
            used += len(chunk_tokens)
        return " ".join(selected)


if __name__ == "__main__":
    tokens = ["a", "b", "c", "d", "e"]
    chunks = StandardRagSimulator.chunk(tokens, max_tokens=4, overlap=3)
    print(f"chunk(): {chunks}")

    query = (1.0, 0.0, 0.0)
    candidates = [
        {"d1": (1.0, 0.0, 0.0)},
        {"d2": (0.0, 1.0, 0.0)},
        {"d3": (0.7, 0.7, 0.0)},
    ]
    ranked = StandardRagSimulator.top_k(query, candidates, k=2, return_scores=True)
    print(f"top_k(): {ranked}")

    context = StandardRagSimulator.build_context(["aa bb", "cc dd", "ee ff gg"], max_tokens=4)
    print(f"build_context(): {context!r}")
