"""Minimal, dependency-free simulation of AUTO-MERGING RAG.

Contrast with standard_rag_core.py: there, one flat chunk granularity serves
both matching and context. Auto-merging RAG instead builds a two-level
hierarchy at ingestion time:

  - PARENT chunks: bigger windows over the token stream (e.g. a "section").
  - CHILD chunks: smaller windows nested inside each parent (e.g. a
    "paragraph"). Children are what get embedded and searched — matching
    stays precise because each embedded unit is small and topically narrow.

At retrieval time, if *enough* of one parent's children were independently
retrieved (crossing `merge_threshold`), the system infers the query is
about that whole parent section and "merges" — returns the single coherent
parent chunk instead of several disjoint child fragments. Children whose
parent didn't cross the threshold are kept as-is.

This is the same idea as LlamaIndex's HierarchicalNodeParser +
AutoMergingRetriever. As in the other two files here, the embedding model
itself is simulated — vectors are passed in as plain tuples of floats.
cosine_similarity() is identical to the standard file's version; only the
indexing structure and the retrieval -> build_context step differ. See
findings_rag_underneath.md (Q4/Q5) for the full three-way comparison.
"""

from __future__ import annotations

import math
from typing import Sequence


class AutoMergingRagSimulator:
    """Groups the four pipeline stages as methods, mirroring
    standard_rag_core.py's structure so the two are easy to compare
    side by side.
    """

    # ------------------------------------------------------------------
    # Stage 1: chunking — build a 2-level parent/child hierarchy.
    # ------------------------------------------------------------------
    @staticmethod
    def chunk(
        tokens: Sequence[str], parent_size: int = 6, child_size: int = 3
    ) -> dict[str, dict[str, dict]]:
        """Split `tokens` into non-overlapping parent windows of
        `parent_size`, then split each parent's tokens into non-overlapping
        child windows of `child_size`.

        Returns a node store: `{"parents": {pid: {...}}, "children": {cid: {...}}}`
          - parents[pid] = {"id": pid, "text": ..., "children": [cid, ...]}
          - children[cid] = {"id": cid, "text": ..., "parent": pid}

        This mirrors how a real vector index only stores/embeds the small
        child nodes, while a separate docstore holds the parent/child
        hierarchy needed to merge back up later.

        Example: chunk(['a'..'f'], parent_size=6, child_size=3) produces one
        parent "a b c d e f" with two children "a b c" and "d e f".

        Raises:
            ValueError: if parent_size <= 0, child_size <= 0, or
                child_size > parent_size (a child can't be bigger than its parent).
        """
        if parent_size <= 0:
            raise ValueError("parent_size must be > 0")
        if child_size <= 0:
            raise ValueError("child_size must be > 0")
        if child_size > parent_size:
            raise ValueError("child_size must be <= parent_size")

        tokens = list(tokens)
        parents: dict[str, dict] = {}
        children: dict[str, dict] = {}

        for p_idx, p_start in enumerate(range(0, len(tokens), parent_size)):
            parent_tokens = tokens[p_start : p_start + parent_size]
            pid = f"p{p_idx}"
            child_ids: list[str] = []

            for c_idx, c_start in enumerate(range(0, len(parent_tokens), child_size)):
                child_tokens = parent_tokens[c_start : c_start + child_size]
                cid = f"{pid}-c{c_idx}"
                children[cid] = {"id": cid, "text": " ".join(child_tokens), "parent": pid}
                child_ids.append(cid)

            parents[pid] = {"id": pid, "text": " ".join(parent_tokens), "children": child_ids}

        return {"parents": parents, "children": children}

    # ------------------------------------------------------------------
    # Stage 2: pairwise vector similarity — identical to standard RAG.
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
    # Stage 3: retrieval — rank CHILD embeddings against the query.
    # ------------------------------------------------------------------
    @staticmethod
    def top_k(
        query: Sequence[float],
        candidates: Sequence[dict[str, str | Sequence[float]]],
        k: int,
        return_scores: bool = False,
    ) -> list[dict] | list[tuple[dict, float]]:
        """Rank child-level candidates against `query`, return the top k.

        `candidates` is a sequence of `{"id": child_id, "vector": embedding}`
        dicts — only children are ever embedded/searched in auto-merging
        RAG; parents exist purely in the docstore for merging, never in the
        vector index. Same stable-sort/tie-breaking and return_scores
        behavior as standard_rag_core.top_k.
        """
        if k <= 0:
            return []

        scored: list[tuple[float, dict]] = []
        for candidate in candidates:
            score = AutoMergingRagSimulator.cosine_similarity(query, candidate["vector"])
            scored.append((score, candidate))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        top = scored[:k]

        if return_scores:
            return [(candidate, score) for score, candidate in top]
        return [candidate for _, candidate in top]

    # ------------------------------------------------------------------
    # Stage 4: context assembly — merge up to parents where the retrieved
    # children cross a threshold, THEN pack into the token budget. This
    # merge-decision step doesn't exist at all in naive/standard RAG.
    # ------------------------------------------------------------------
    @staticmethod
    def build_context(
        matches: Sequence[dict[str, str]],
        node_store: dict[str, dict[str, dict]],
        max_tokens: int,
        merge_threshold: float = 0.5,
    ) -> str:
        """Group matched children by parent; for any parent where the
        fraction of its children that were retrieved is >= merge_threshold,
        replace those children with the single full parent chunk. Remaining,
        un-merged children are kept standalone. Then pack the resulting
        chunks (whole or not at all) into `max_tokens`, in best-match order
        — mirrors standard_rag_core.build_context's packing rules exactly.

        `matches`: output of top_k(), e.g. [{"id": "p0-c1", "vector": ...}, ...]
        `node_store`: the dict returned by chunk() (has "parents"/"children").

        Example: parent "p0" has 2 children; if both were retrieved,
        fraction = 2/2 = 1.0 >= default threshold 0.5 -> merged to parent
        "p0"'s full text instead of 2 separate child fragments.
        """
        if max_tokens <= 0:
            raise ValueError("max_tokens must be > 0")
        if not 0.0 <= merge_threshold <= 1.0:
            raise ValueError("merge_threshold must be between 0.0 and 1.0")

        children = node_store["children"]
        parents = node_store["parents"]

        matched_by_parent: dict[str, list[str]] = {}
        first_seen_rank: dict[str, int] = {}
        for rank, match in enumerate(matches):
            cid = match["id"]
            pid = children[cid]["parent"]
            matched_by_parent.setdefault(pid, []).append(cid)
            first_seen_rank.setdefault(pid, rank)

        resolved: list[tuple[int, str]] = []  # (best_rank, text)
        emitted_children: set[str] = set()
        for pid, matched_children in matched_by_parent.items():
            parent = parents[pid]
            fraction = len(matched_children) / len(parent["children"])
            if fraction >= merge_threshold:
                resolved.append((first_seen_rank[pid], parent["text"]))
                emitted_children.update(matched_children)

        for rank, match in enumerate(matches):
            cid = match["id"]
            if cid in emitted_children:
                continue
            resolved.append((rank, children[cid]["text"]))

        resolved.sort(key=lambda pair: pair[0])
        ordered_chunks = [text for _, text in resolved]

        selected: list[str] = []
        used = 0
        for text in ordered_chunks:
            text_tokens = text.split()
            if not selected and len(text_tokens) > max_tokens:
                return " ".join(text_tokens[:max_tokens])
            if used + len(text_tokens) > max_tokens:
                break
            selected.append(text)
            used += len(text_tokens)
        return " ".join(selected)


if __name__ == "__main__":
    tokens = "a b c d e f g h i".split()
    node_store = AutoMergingRagSimulator.chunk(tokens, parent_size=6, child_size=3)
    print("chunk():")
    print(f"  parents: {node_store['parents']}")
    print(f"  children: {node_store['children']}")

    # Simulate: both children of "p0" match well (broad query -> merges to
    # the parent), while only one child of "p1" matches (narrow -> stays a
    # standalone child chunk).
    candidates = [
        {"id": "p0-c0", "vector": (0.9, 0.1)},
        {"id": "p0-c1", "vector": (0.8, 0.2)},
        {"id": "p1-c0", "vector": (0.3, 0.9)},
    ]
    query = (1.0, 0.0)
    ranked = AutoMergingRagSimulator.top_k(query, candidates, k=3, return_scores=True)
    print(f"\ntop_k() (matches on child embeddings only): {ranked}")

    matches = [c for c, _ in ranked]
    context = AutoMergingRagSimulator.build_context(matches, node_store, max_tokens=20)
    print(f"\nbuild_context() (p0's children merged up, p1's child stays standalone):\n  {context!r}")
