"""Minimal, dependency-free simulation of SENTENCE-WINDOW RAG.

Contrast with standard_rag_core.py: there, one flat chunk is both the thing
that gets embedded/matched AND the thing that ends up in the LLM's context.
Sentence-window RAG deliberately splits those two jobs across two different
units of text:

  - matching happens at SENTENCE granularity (small, precise, no topic
    dilution from neighboring sentences bleeding into the embedding)
  - context is built from a WINDOW of `window_size` sentences around each
    matched sentence (larger, coherent, so the LLM isn't handed one bare
    sentence stripped of the context it needs to be interpreted correctly)

This is the same trick LlamaIndex's SentenceWindowNodeParser +
MetadataReplacementPostProcessor implement: embed small, retrieve small,
then swap in the bigger window right before the LLM ever sees it.

As in standard_rag_core.py, the embedding model itself is simulated — vectors
are passed in as plain tuples of floats rather than produced by a real
embedding API. cosine_similarity() is character-for-character identical to
the standard file's version, which is the point: the scoring math doesn't
change between RAG strategies, only the indexing structure and what happens
between retrieval and build_context does. See findings_rag_underneath.md
(Q4/Q5) for the full comparison.
"""

from __future__ import annotations

import math
import re
from typing import Sequence

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


class SentenceWindowRagSimulator:
    """Groups the four pipeline stages as methods, mirroring
    standard_rag_core.py's structure so the two are easy to compare
    side by side.
    """

    # ------------------------------------------------------------------
    # Stage 1: chunking — split into sentences, but pre-compute and store
    # a wider window alongside each one for later context assembly.
    # ------------------------------------------------------------------
    @staticmethod
    def chunk(text: str, window_size: int = 1) -> list[dict[str, str]]:
        """Split `text` into sentences; return one node per sentence.

        Each node is `{"id": ..., "sentence": ..., "window": ...}`:
          - "sentence": the single sentence — this is the small, precise
            unit that gets embedded and matched against a query.
          - "window": that sentence plus up to `window_size` sentences
            before and after it, joined back into one string — this is
            what actually reaches the LLM's context, once a sentence in
            this node is matched.

        Example: chunk("A. B. C. D.", window_size=1) sentence "B." carries
        window "A. B. C." (one neighbor each side).

        Raises:
            ValueError: if window_size < 0, or text has no sentences.
        """
        if window_size < 0:
            raise ValueError("window_size must be >= 0")

        sentences = [s for s in _SENTENCE_SPLIT_RE.split(text.strip()) if s]
        if not sentences:
            return []

        nodes: list[dict[str, str]] = []
        n = len(sentences)
        for i, sentence in enumerate(sentences):
            lo = max(0, i - window_size)
            hi = min(n, i + window_size + 1)
            window = " ".join(sentences[lo:hi])
            nodes.append({"id": f"s{i}", "sentence": sentence, "window": window})
        return nodes

    # ------------------------------------------------------------------
    # Stage 2: pairwise vector similarity — identical to standard RAG.
    # The metric never changes between strategies, only what it's applied to.
    # ------------------------------------------------------------------
    @staticmethod
    def cosine_similarity(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
        """cos(theta) = (a . b) / (||a|| * ||b||). See standard_rag_core.py
        for the full rationale — this is the same function, unchanged.
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
    # Stage 3: retrieval — rank SENTENCE embeddings against the query.
    # ------------------------------------------------------------------
    @staticmethod
    def top_k(
        query: Sequence[float],
        candidates: Sequence[dict[str, str | Sequence[float]]],
        k: int,
        return_scores: bool = False,
    ) -> list[dict] | list[tuple[dict, float]]:
        """Rank sentence-level candidates against `query`, return the top k.

        `candidates` is a sequence of `{"id": doc_id, "vector": embedding}`
        dicts — the embedding of the *sentence only*, never the window. This
        is what makes matching precise: the window's extra surrounding words
        never get to dilute the vector being searched.

        Returns the matched candidates (their "id" is what build_context
        uses to look up the stored window). Same stable-sort/tie-breaking
        and return_scores behavior as standard_rag_core.top_k.
        """
        if k <= 0:
            return []

        scored: list[tuple[float, dict]] = []
        for candidate in candidates:
            score = SentenceWindowRagSimulator.cosine_similarity(query, candidate["vector"])
            scored.append((score, candidate))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        top = scored[:k]

        if return_scores:
            return [(candidate, score) for score, candidate in top]
        return [candidate for _, candidate in top]

    # ------------------------------------------------------------------
    # Stage 4: context assembly — swap each match for its stored window,
    # THEN pack into the token budget. This is the step that doesn't exist
    # at all in naive/standard RAG.
    # ------------------------------------------------------------------
    @staticmethod
    def build_context(
        matches: Sequence[dict[str, str]],
        node_store: dict[str, dict[str, str]],
        max_tokens: int,
    ) -> str:
        """Look up each matched sentence's window, then pack windows
        (whole or not at all) into `max_tokens` — mirrors
        standard_rag_core.build_context's packing rules exactly, the only
        difference is *what* gets packed (windows, not raw chunks).

        `matches`: output of top_k(), e.g. [{"id": "s1", "vector": ...}, ...]
        `node_store`: id -> node dict, as produced by chunk() — this
        simulates the separate docstore a real sentence-window retriever
        fetches windows from (the vector index itself only ever held the
        bare sentence embeddings).

        Windows are deduplicated by id while preserving first-seen (i.e.
        best-ranked) order, since two adjacent matched sentences can share
        overlapping windows.
        """
        if max_tokens <= 0:
            raise ValueError("max_tokens must be > 0")

        seen: set[str] = set()
        windows: list[str] = []
        for match in matches:
            node_id = match["id"]
            if node_id in seen:
                continue
            seen.add(node_id)
            windows.append(node_store[node_id]["window"])

        selected: list[str] = []
        used = 0
        for window in windows:
            window_tokens = window.split()
            if not selected and len(window_tokens) > max_tokens:
                return " ".join(window_tokens[:max_tokens])
            if used + len(window_tokens) > max_tokens:
                break
            selected.append(window)
            used += len(window_tokens)
        return " ".join(selected)


if __name__ == "__main__":
    text = (
        "The invoice was issued on March 3rd. "
        "Payment is due within 30 days of issuance. "
        "Late payments accrue a 2 percent monthly fee. "
        "Disputes must be raised in writing within 14 days."
    )
    nodes = SentenceWindowRagSimulator.chunk(text, window_size=1)
    print("chunk():")
    for node in nodes:
        print(f"  {node['id']}: sentence={node['sentence']!r}")
        print(f"       window={node['window']!r}")

    # Simulated embeddings: pretend node s2 ("late payment fee") is the
    # closest match to a query about late fees.
    node_store = {node["id"]: node for node in nodes}
    candidates = [
        {"id": "s0", "vector": (0.1, 0.1, 0.0)},
        {"id": "s1", "vector": (0.2, 0.0, 0.1)},
        {"id": "s2", "vector": (0.9, 0.1, 0.0)},
        {"id": "s3", "vector": (0.0, 0.2, 0.1)},
    ]
    query = (1.0, 0.0, 0.0)
    ranked = SentenceWindowRagSimulator.top_k(query, candidates, k=1, return_scores=True)
    print(f"\ntop_k() (matches on sentence embedding only): {ranked}")

    matches = [c for c, _ in ranked]
    context = SentenceWindowRagSimulator.build_context(matches, node_store, max_tokens=50)
    print(f"\nbuild_context() (expanded to window, not just the matched sentence):\n  {context!r}")
