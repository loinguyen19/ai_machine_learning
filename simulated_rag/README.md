# Simulated RAG — Live Coding Practice

A from-scratch, dependency-free simulation of the core mechanics behind
Retrieval-Augmented Generation (RAG). No LLM calls, no embedding API, no
vector DB — just the plain math and logic those systems wrap, so you can
rehearse writing it live under interview conditions.

## Objective

A real RAG pipeline looks like:

```
raw docs -> chunk -> embed each chunk -> store vectors
                                            |
query -> embed query -> rank stored vectors by similarity -> take top k
                                            |
                          pack top-k chunks into a token-bounded context
                                            |
                                    hand context to an LLM
```

This exercise simulates every step **except the embedding model itself**.
Embeddings are passed in directly as plain tuples of numbers (e.g. `(1, 0, 0)`)
instead of being produced by a real model — so you can focus on and practice
the part that's actually asked about in a live-coding round: chunking logic,
similarity math, top-k ranking, and context assembly under a token budget.

## Three RAG strategies, three files

This folder actually implements three variants of the pipeline above, one
per file, so the differences between them can be rehearsed side by side
instead of only read about:

| File | Strategy | What's different |
|---|---|---|
| [`standard_rag_core.py`](./standard_rag_core.py) | Naive / standard RAG | One flat chunk granularity for both matching and context — no post-retrieval transformation. |
| [`sentence_window_rag_core.py`](./sentence_window_rag_core.py) | Sentence-window RAG | Matches at sentence granularity; expands to a stored neighbor window before `build_context`. |
| [`auto_merging_rag_core.py`](./auto_merging_rag_core.py) | Auto-merging RAG | Matches at child-chunk granularity; merges up to the parent chunk when enough of a parent's children are retrieved. |

The rest of this README documents `standard_rag_core.py` in detail, since it's
the baseline the other two are variations on. For the full walkthrough of
what changes (and, just as importantly, what *doesn't* — the pipeline shape
and `cosine_similarity` math are identical across all three) see
[`findings_rag_underneath.md`](./findings_rag_underneath.md).

## The four functions (`standard_rag_core.py`, class `StandardRagSimulator`)

All four are `staticmethod`s on one class — stateless on purpose, so each
stage is independently testable and composable.

### 1. `chunk(tokens, max_tokens=3, overlap=1) -> list[str]`

Sliding-window chunking over a list of tokens.

```python
StandardRagSimulator.chunk(['a', 'b', 'c', 'd', 'e'], max_tokens=3, overlap=1)
# -> ['a b c', 'c d e']
```

- `max_tokens` = chunk size (window width).
- `overlap` = how many tokens the end of one chunk shares with the start of
  the next. The window advances by `step = max_tokens - overlap` each time.
- **Why overlap exists in real RAG:** if you chunk with zero overlap, a
  sentence or idea that straddles exactly a chunk boundary gets split and
  loses context in *both* halves. A small overlap (commonly 10-20% of chunk
  size in production, exaggerated here to 1/3 for a readable example) means
  boundary content still appears whole in at least one chunk.
- Edge cases handled: empty input -> `[]`; input shorter than `max_tokens` ->
  a single chunk; `overlap >= max_tokens` raises `ValueError` (the window
  would never advance -> infinite loop).

> Note: here a "token" is just a whitespace-separated word (`str.split()`
> style), not a real subword tokenizer (e.g. tiktoken/BPE) — good enough to
> reason about the *algorithm*, which is the point of the exercise.

### 2. `cosine_similarity(vec_a, vec_b) -> float`

The pure pairwise similarity metric — nothing else:

```
cos(theta) = (a . b) / (||a|| * ||b||)
```

```python
StandardRagSimulator.cosine_similarity((1, 0, 0), (2, 0, 0))  # -> 1.0   same direction, different magnitude
StandardRagSimulator.cosine_similarity((1, 0),    (0, 1))      # -> 0.0   orthogonal / unrelated
StandardRagSimulator.cosine_similarity((1, 0),    (1, 1))      # -> 0.7071...  ~45 degrees apart
```

- Cosine similarity measures **direction, not magnitude** — that's exactly
  why it's the standard metric for embeddings: two chunks about the same
  topic should score highly even if one is longer/"louder" in vector space.
- Returns `0.0` for a zero vector instead of raising `ZeroDivisionError` —
  "similarity to a null embedding" is undefined, but crashing an entire
  retrieval batch over one bad vector is worse than returning a neutral score.
- Raises `ValueError` on a dimension mismatch — in a real system this means
  two chunks were embedded with different models, which should never happen
  silently.

> **Correction vs. a common intuition:** `(1, 0)` vs `(1, 1)` is **not**
> 0.97 — it's `1/sqrt(2) ≈ 0.707`. Worth double-checking this kind of mental
> math out loud in an interview rather than guessing.

### 3. `top_k(query, candidates, k, return_scores=False) -> list[...]`

Ranks a batch of candidate vectors against a query vector using
`cosine_similarity`, and returns only the best `k`.

```python
candidates = [
    {"d1": (1.0, 0.0, 0.0)},
    {"d2": (0.0, 1.0, 0.0)},
    {"d3": (0.7, 0.7, 0.0)},
]
StandardRagSimulator.top_k((1.0, 0.0, 0.0), candidates, k=2)
# -> [{'d1': (1.0, 0.0, 0.0)}, {'d3': (0.7, 0.7, 0.0)}]
```

- Each candidate is a single-key `{doc_id: vector}` dict — mirroring how a
  real vector store hands back `(doc_id, vector)` pairs.
- `return_scores=True` also returns each result's similarity score, e.g.
  `[({'d1': ...}, 1.0), ({'d3': ...}, 0.707)]` — real retrieval code almost
  always wants this, e.g. to apply a "drop anything below 0.75" confidence
  gate before a chunk is ever allowed into the LLM's context.
- Sort is stable and descending by score; ties keep their input order.

**Design note — why this is a separate function from `cosine_similarity`:**
in the original rough spec these two responsibilities were tangled into one
function. Keeping the pure metric (`cosine_similarity`: compare exactly two
vectors) separate from the ranking/selection policy (`top_k`: score *many*
candidates against one query and keep the best `k`) is the actual RAG
practice — it also makes both pieces independently unit-testable, and lets
you swap in a different metric (dot product, Euclidean) without touching the
ranking logic.

### 4. `build_context(chunks, max_tokens) -> str`

Packs already-ranked chunks (best first, e.g. straight from `top_k`) into one
string without exceeding a token budget.

```python
StandardRagSimulator.build_context(["aa bb", "cc dd"], max_tokens=4)
# -> "aa bb cc dd"

StandardRagSimulator.build_context(["aa bb", "cc dd", "ee ff gg"], max_tokens=4)
# -> "aa bb cc dd"   (adding "ee ff gg" would push total past 4, so it's dropped)
```

- Chunks are included **whole or not at all** — never cut mid-chunk, so the
  LLM never receives half a sentence.
- Edge case: if the very first chunk alone exceeds `max_tokens`, it's
  truncated to the first `max_tokens` tokens rather than returning an empty
  context (some grounding beats none).
- **Why this is a separate stage from `chunk()`:** the chunk size used for
  *retrieval granularity* (how finely you split for embedding/ranking) and
  the *final context token budget* (how much fits in the LLM's prompt) are
  two independent numbers in a real system — you might chunk at 200 tokens
  each but only have room for 3 of them in the final prompt.

## Running it

```bash
cd simulated_rag_live_coding_test
python3 standard_rag_core.py            # quick demo run, prints all four functions in action
python3 -m pytest -v           # run the test suite (19 tests, no network/deps beyond pytest)
```

## Live-coding talking points

Things worth being able to say out loud, since that's the actual skill being
tested — not just producing correct output:

- **Complexity:** `chunk` is O(n). `cosine_similarity` is O(d) in vector
  dimension. `top_k` is O(n log n) for the sort — call out that for large n
  you'd use a heap (`heapq.nlargest`) to get O(n log k) instead, or in
  practice an ANN index (FAISS, pgvector, HNSW) instead of brute-force
  scoring every candidate.
- **Why cosine similarity and not raw dot product:** dot product is
  magnitude-sensitive — a longer/"more confident" embedding could win purely
  on scale, not relevance. Cosine normalizes that out.
- **What's faked here vs. production:** real chunking uses a model-specific
  tokenizer (token count ≠ word count); real embeddings come from an API
  call; real retrieval uses an approximate-nearest-neighbor index, not a
  linear scan; real context assembly also has to budget for the system
  prompt and the user's own message, not just retrieved chunks.
- **Failure modes to mention unprompted:** empty candidate list, `k=0`,
  mismatched embedding dimensions (usually means two different embedding
  models got mixed), a chunk larger than the entire context budget.
