# Findings: What `rag_core.py` Actually Simulates, and What Real Systems Do Instead

This doc captures a Q&A that came up while building the practice exercise in
this folder — specifically, which phase of a real RAG pipeline each function
stands in for, how much of this logic survives once you move from a
live-coding exercise to a production RAG / agentic AI system, whether word-
vs. sentence-level chunking maps to BERT vs. Sentence-Transformers, and which
of the three common RAG architectures (naive/standard, sentence-window,
auto-merging) this repo's files each simulate.

> Note: the original single file `rag_core.py` was later split/renamed into
> [`standard_rag_core.py`](./standard_rag_core.py),
> [`sentence_window_rag_core.py`](./sentence_window_rag_core.py), and
> [`auto_merging_rag_core.py`](./auto_merging_rag_core.py) — see Q5 below.
> Earlier sections in this doc that say `rag_core.py` are referring to what is
> now `standard_rag_core.py`.

## Q1: Which of the 3 RAG phases does `rag_core.py` simulate — ingestion, retrieval, or synthesis?

**Question asked:** *"so the rag_core logic here to simulate one of 3 process
in rag: ingestion, retrieval and synthesis? and it lies in retrieval phase
where it mimics the chunk, calculate the cosine_similarity then top_k
returned and build context preparation for phase 3 synthesis?"*

**Answer:** Close, but `chunk()` actually belongs to a different phase than
the other three.

The standard 3-phase split:

1. **Ingestion** (offline, before any query exists): split raw docs → chunk
   them → embed each chunk → store vectors in an index. Happens once, ahead
   of time.
2. **Retrieval** (per query, at request time): embed the query → score it
   against stored vectors → keep the top k.
3. **Synthesis** (a.k.a. generation): hand the retrieved content to an LLM to
   produce the answer.

Mapped onto `rag_core.py`:

| Function | Phase | Why |
|---|---|---|
| `chunk()` | **Ingestion**, not retrieval | It splits raw text before embedding — this runs once when documents are indexed, not per query. |
| `cosine_similarity()` | **Retrieval** | The pure per-pair scoring math, run at query time against the (already-chunked, already-embedded) index. |
| `top_k()` | **Retrieval** | Ranking/selection policy on top of that scoring — also query-time. |
| `build_context()` | Boundary of **retrieval → synthesis** | It's the last thing retrieval hands off, packaged into the exact input synthesis needs (a token-bounded prompt string). Some count it as the tail of retrieval, others as its own "augmentation" step — but it's not synthesis itself, since no LLM call happens anywhere in this file. |

So the file doesn't simulate *only* retrieval — it simulates parts of
**ingestion** (`chunk`) and **retrieval** (`cosine_similarity`, `top_k`,
`build_context`), and stops right at the door of synthesis without ever
calling an LLM. `chunk()` sits next to the retrieval functions in the same
file/class purely for exercise convenience — in a real pipeline it runs in a
completely separate offline indexing job, likely hours or days before any
query touches `cosine_similarity`.

**Talking point:** naming that `chunk` is ingestion-time while the other
three are query-time shows you understand the pipeline's actual execution
timeline, not just its function names.

## Q2: In a real RAG / agentic AI system, do we still need to write this logic ourselves?

**Question asked:** *"so in real rag pipeline and agentic ai system, the 1st
phase will be done offline like a batch process, the other 2 phases will be
handled by Agentic framework like Langchain/Langgraph or AWS Bedrock with our
custom logic code? we do not need to care much more about cosine_similarity
(or other similarity check model), top_k and build_context in real rag
pipeline and agentic ai system right?"*

**Answer:** Mostly right, with nuances on each piece.

**Ingestion as "batch":** usually right, but not strictly — it's often
event-driven (a doc uploaded → webhook triggers chunk+embed+upsert for just
that doc) rather than a scheduled batch job. Either way, the key point holds:
it's offline / decoupled from query time.

**"We don't need to care about `cosine_similarity` / `top_k` / `build_context`"** —
splits into three different answers:

- **`cosine_similarity` + `top_k` (the actual vector search):** Correct —
  in production you almost never hand-write this. It's delegated to the
  vector store's index (pgvector, Pinecone, Weaviate, FAISS, OpenSearch,
  Bedrock Knowledge Bases), which uses an ANN algorithm (HNSW, IVF)
  implemented in C++/Rust, not a Python loop like `rag_core.py`'s
  brute-force scan. In LangChain you just call `retriever.invoke(query)` or
  `vectorstore.similarity_search(query, k=5)`; in Bedrock Knowledge Bases you
  call one `Retrieve` / `RetrieveAndGenerate` API and it's fully managed end
  to end.
  **But** the concept still matters: which distance metric to configure the
  index with (cosine vs. dot product vs. Euclidean — chosen at
  index-creation time), what a returned score means, and why retrieval is
  returning junk when it does. That's a debugging/config skill in real
  systems, not a coding one.

- **`build_context` (packing results into the prompt under a token budget):**
  Not abstracted away nearly as much. Frameworks give you a template
  (`create_stuff_documents_chain`, a prompt template, etc.), but the actual
  "how many retrieved chunks fit, and what gets dropped" logic is often still
  something your team writes or tunes — especially in **agentic** systems,
  where the context window is also competing with conversation history, tool
  outputs, and system prompts, not just retrieved chunks. Context-budget bugs
  (silent truncation, blowing the window) are a genuinely common real-world
  RAG failure mode, so this piece stays closer to "your code" than the
  similarity math does.

- **Reranking** (not in this practice file at all): after the vector store's
  cheap ANN top-k, many real pipelines run a second, more expensive
  reranking pass (a cross-encoder model, or a managed API like Cohere
  Rerank) to reorder those candidates by true relevance. Conceptually it's
  "another `top_k`," but scored by a different, pricier model — worth
  mentioning if asked "how would you improve this in production."

**Bottom line:** the exercise's `cosine_similarity` / `top_k` functions
mimic something you'll *configure* rather than *code* in a real system — but
they get asked in live coding precisely *because* the framework hides them,
so interviewers use it to check you understand what's happening underneath
the `retriever.invoke()` call.

## Q3: Is `chunk()`'s word-level strategy specific to BERT rather than Sentence-Transformers?

**Question asked:** *"in rag_core.py, chunk() strategy is the work-level
chunking right? not the sentence-level chunking right? It aligns with BERT
model, not the sentence transformer model right?"*

**Answer:** First half correct, second half conflates two unrelated axes.

**Word-level, not sentence-level — correct.** `chunk()` splits on whitespace
(`str.split()` style) and counts words, not sentences. A sentence-level
chunker would split on sentence boundaries first (`.`/`!`/`?`, or a real
sentence splitter like spaCy/NLTK) and group whole sentences, never cutting
mid-sentence. `rag_core.py`'s chunker respects no such boundary — it's a
**fixed-size sliding-window chunker**, one of several chunking strategies
(the others being sentence-based, paragraph/recursive, and semantic
chunking).

**"Aligns with BERT, not Sentence-Transformer" — wrong axis.** Word-vs-sentence
chunking is about *how you split text before embedding*. BERT vs.
Sentence-Transformers is about *how the model turns text into a vector* — and
they use the **same tokenizer** (WordPiece subwords), so tokenization
granularity doesn't distinguish them at all. The real distinction:

- **Vanilla BERT** was trained/used mainly as a **cross-encoder**: to compare
  two texts, you feed both into the model *together*
  (`[CLS] query [SEP] passage [SEP]`) and it outputs one relevance score.
  There's no independent vector to cosine-compare — in fact, the
  Sentence-BERT paper's whole motivation was that raw BERT's
  `[CLS]`/mean-pooled embeddings give *poor* cosine-similarity results out of
  the box.
- **Sentence-Transformers (SBERT)** is BERT/RoBERTa fine-tuned with a
  siamese/triplet objective specifically so each text can be embedded
  **independently**, and two embeddings compared later via plain cosine
  similarity — cheaply, at scale, without ever running both texts through the
  model together.

`rag_core.py`'s whole design — embed each thing once, store the vector, later
compare two already-computed vectors with `cosine_similarity()` — **is the
Sentence-Transformer / bi-encoder paradigm** (also what OpenAI's/Cohere's
embedding APIs do). It does *not* align with vanilla BERT used as a
cross-encoder, since that architecture can't be decomposed into "embed
independently, then cosine-compare" at all — the two texts must be seen
together.

**Bottom line:** chunking granularity (word vs. sentence) and embedding
architecture (bi-encoder vs. cross-encoder) are two independent axes — worth
not conflating them live.

## Q4: Which of the 3 typical RAG types (naive/standard, sentence-window, auto-merging) does this repo simulate?

**Question asked:** *"I see there are 3 typical types of rag: naive/standard,
sentence-window and auto-merging rag, which one is it in this rag_core.py.
and can you explain me what they are, how it works and use cases of them?"*

**Answer:** The original single file (now `standard_rag_core.py`) implements
**naive/standard RAG** — no sentence-window, no auto-merging. Reasoning:
`chunk()` produces one flat list of fixed-size chunks, and that's the *only*
granularity in the whole pipeline — the same chunk is what gets embedded,
what gets matched by `cosine_similarity`/`top_k`, and what gets dropped
straight into `build_context()` verbatim. There's no dual granularity (small
unit for matching, larger unit for context), no metadata linking a chunk to
its neighbors, and no logic to expand or merge chunks after retrieval.

### 1. Naive / Standard RAG
**How it works:** Fixed-size (or paragraph-size) chunks, embedded once,
stored flat. At query time: embed query → cosine-similarity search → top-k
chunks → stuffed directly into the prompt as-is.
**Trade-off:** One chunk-size parameter has to serve two conflicting jobs —
small chunks embed precisely (less topic dilution, better matching) but may
lack context; large chunks give the LLM enough context but embed a blurrier
"average" of multiple ideas, hurting match precision. You can't tune
retrieval precision and context sufficiency independently.
**Use cases:** Prototyping, homogeneous short documents (FAQs, small
knowledge bases), anywhere the extra indexing complexity isn't worth it. This
is what `standard_rag_core.py` simulates, and honestly what most RAG demos
and a lot of production systems actually run.

### 2. Sentence-Window Retrieval
**How it works:** Embed at **sentence granularity** — each individual
sentence gets its own embedding, so matching is very precise (no dilution
across sentences). But each sentence is stored with metadata pointing to a
**window** of `k` neighboring sentences before/after it. When a sentence
matches, you don't hand the LLM that one bare sentence — you replace it with
its window before building context.
**Trade-off:** Decouples "unit of matching" (sentence, precise) from "unit of
context" (window, coherent) — better of both worlds than naive RAG. Costs
more preprocessing/metadata bookkeeping, and the window size is yet another
hyperparameter to tune; it only expands *locally* around a hit, so it still
can't give you "the whole relevant section."
**Use cases:** Dense factual/technical text where the *answer* lives in one
sentence but the LLM needs a sentence or two of surrounding context to not
misinterpret it (legal clauses, technical specs, medical notes).
**Simulated in:** [`sentence_window_rag_core.py`](./sentence_window_rag_core.py)

### 3. Auto-Merging Retrieval
**How it works:** Documents are chunked into a **hierarchy** — big "parent"
chunks (e.g. a section) split into smaller "child" chunks (e.g. a paragraph
or a few sentences each), and children are what get embedded and searched.
If retrieval pulls back *enough* children from the same parent (above some
threshold, e.g. "more than half of this parent's children matched"), the
system automatically merges them and returns the whole parent chunk instead
of several disjoint fragments.
**Trade-off:** Adapts context size to how broad the query is — a narrow query
gets a small precise chunk, a broad query that legitimately spans a whole
section gets auto-upgraded to that full section instead of returning several
scattered, incoherent snippets. Most complex to build and index (tree
structure, merge-threshold tuning), and indexing cost/storage is higher
(children + parents both stored).
**Use cases:** Long structured documents (manuals, books, legal codes, long
reports) where some queries want one clause and others really want "explain
this whole chapter" — and you don't want to hardcode chunk size for both.
**Simulated in:** [`auto_merging_rag_core.py`](./auto_merging_rag_core.py)

All three still bottom out on the exact same primitive — `cosine_similarity`
— and the same overall pipeline shape. The difference between them is
entirely in the **chunking/indexing strategy** (flat list vs. sentence +
window metadata vs. parent/child tree) and what happens **between retrieval
and `build_context`** (nothing, in naive; a window lookup, in sentence-window;
a merge-threshold check + parent lookup, in auto-merging) — not in the
scoring math itself. See Q5 for why this isn't *quite* the same as saying
"only indexing changes."

## Q5: Do the 3 RAG types change the overall pipeline, or only indexing and the retrieval→context-building step?

**Question asked:** *"3 these strategies does nothing to the whole rag
pipeline right? only main difference in the way how it indexes in vector db
and the time between retrieval and context building right?"*

**Answer:** Mostly right, with one addition worth being precise about.

**What's genuinely unchanged across all three:** the overall pipeline shape
(chunk → embed → store → retrieve → build context → synthesize) and the core
similarity math (`cosine_similarity`, ranking-by-score). Every strategy in
this repo calls the exact same `cosine_similarity` formula — the scoring
function itself never changes.

**What's not quite captured by "only indexing" and "only a timing
difference":** it's not just *when* something happens between retrieval and
context-building — real *logic* gets inserted there, specific to each
strategy:

- **Standard:** retrieval output → context, no transformation in between.
- **Sentence-window:** retrieval output (a matched sentence's id) → **look up
  its pre-computed window from a node store** → context. A genuine extra
  step: a fetch, keyed by the id that matched, against something that isn't
  the vector index at all.
- **Auto-merging:** retrieval output (matched child ids) → **group by parent,
  check whether enough children of that parent were retrieved to cross a
  merge threshold, and if so fetch and substitute the parent's full text** →
  context. A genuine extra decision procedure (a threshold check) plus a
  lookup, not just a relabeled moment in time.

So the more precise version: the pipeline's *shape* and its *core scoring
math* don't change — but the **indexing structure** (what's stored, and at
what granularity) and the **post-retrieval assembly logic** (what happens to
a raw retrieval hit before it's allowed into `build_context`) both do change,
and the second one is genuinely new code/logic per strategy, not merely "the
same step happening at a different time."
