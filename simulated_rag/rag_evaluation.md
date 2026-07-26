# RAG Evaluation: Production-Standard Metrics

Source discussion: a review of
[this article on RAG](https://viblo.asia/p/tim-hieu-ve-retrieval-augmented-generation-rag-Ny0VGRd7LPA),
cross-checked against what's actually used to evaluate RAG systems in
production, with an explanation of how each metric works, its use case, and
runnable code.

## What the source article covers

It splits into two buckets:

**Traditional IR metrics** — Precision, Recall, F1-score, Relevance Ranking,
Query Coverage, Diversity, Latency, Robustness, Error Analysis, User-Centric
Metrics, Document Comprehensiveness. Generic retrieval-system metrics, not
RAG-specific.

**Modern metrics via TruLens** — the meaningful part; this is TruLens's
well-known **"RAG Triad"**:

1. **Groundedness/Faithfulness**: `F = |V| / |S|` — fraction of statements in
   the answer that are verifiable against the retrieved context.
2. **Answer Relevance**: `AR = (1/n) Σ sim(q, qᵢ)` — generate hypothetical
   questions the answer could be responding to, compare each to the real
   query.
3. **Context Relevance**: `CR = (extracted sentences) / (total sentences in
   context)` — how much of the retrieved context is actually relevant.

The article contains no code for any of these.

## What's actually most used in production, ranked

1. **Faithfulness / Groundedness** — the most load-bearing one by far.
   Hallucination (answer not supported by retrieved context) is the #1
   production risk in RAG, especially in compliance-sensitive domains (e.g.
   the KYC-style workflows in `finance_agent/`). Almost every production RAG
   eval setup checks this first.
2. **Context Precision / Context Recall** — used to diagnose *where* a bad
   answer came from: if context recall is low, the retriever failed to find
   the right chunk (fix chunking/embedding/index); if it's high but the
   answer is still wrong, the failure is in generation, not retrieval. This
   precision/recall split is the standard first debugging step.
3. **Answer Relevancy** — catches a different failure mode: answer is fully
   grounded (high faithfulness) but doesn't actually address what was asked
   (e.g. answers a related-but-different question). Less critical than
   faithfulness but still commonly tracked.
4. **Traditional IR metrics (Recall@k, MRR, NDCG)** — used mainly *offline*,
   during development, to benchmark/tune the retriever itself (compare
   embedding models, chunk sizes, rerankers) against a labeled relevant-doc
   set. Rare to compute these live in production since they need
   ground-truth relevance labels.
5. **Latency / user feedback (thumbs up/down, click-through)** — pure ops
   monitoring, not quality-of-answer eval, but is what most teams actually
   watch in a live dashboard day to day.

The dominant **implementation** for #1–3 in industry is **RAGAS** (`ragas`
PyPI package) — it computes exactly this triad using an LLM as the judge,
and is the closest thing to a de facto standard. TruLens (what the source
article cites) is the second most common; ARES is the academic alternative
that swaps the LLM-judge for a cheaper fine-tuned classifier.

## How each works, use case, and code

### 1. Faithfulness/Groundedness — via RAGAS (the production-standard way)

**How it works:** an LLM decomposes the generated answer into atomic claims,
then checks each claim against the retrieved context, scoring
`verified_claims / total_claims` — the same formula the source article
gives.
**Use case:** gating/regression-testing a RAG pipeline before deploy — fail
the build if faithfulness drops below a threshold on your eval set.

```python
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from datasets import Dataset

data = {
    "question": ["What is the late payment fee?"],
    "answer": ["Late payments accrue a 2% monthly fee."],
    "contexts": [["Late payments accrue a 2 percent monthly fee."]],
    "ground_truth": ["A 2% monthly fee is charged on late payments."],
}
dataset = Dataset.from_dict(data)

result = evaluate(
    dataset,
    metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
)
print(result)  # {'faithfulness': 1.0, 'answer_relevancy': 0.94, 'context_precision': 1.0, 'context_recall': 1.0}
```

**What RAGAS is doing underneath**, hand-rolled to show the actual mechanism
(this is the LLM-as-judge pattern the article's formula describes):

```python
def faithfulness_score(answer: str, context: str, llm) -> float:
    statements = llm.invoke(
        f"Break this answer into a list of atomic factual claims, one per line:\n{answer}"
    ).content.strip().split("\n")

    verified = 0
    for statement in statements:
        verdict = llm.invoke(
            f"Context:\n{context}\n\nClaim: {statement}\n\n"
            "Can this claim be directly verified from the context? Answer yes or no."
        ).content.strip().lower()
        if verdict.startswith("yes"):
            verified += 1

    return verified / len(statements) if statements else 0.0
```

### 2. Answer Relevancy

**How it works:** ask the LLM to generate `n` plausible questions the
*answer* could be responding to, embed each, and average their cosine
similarity to the *original* query. Low score = answer is off-topic even if
factually grounded.
**Use case:** catching "technically true but doesn't answer what was asked"
— e.g. user asks about late fees, system answers about the payment due date
instead.

```python
def answer_relevance(query_vec, answer: str, embed_fn, llm, n: int = 3) -> float:
    generated_questions = llm.invoke(
        f"Generate {n} questions this answer could be responding to:\n{answer}"
    ).content.strip().split("\n")

    sims = [
        StandardRagSimulator.cosine_similarity(query_vec, embed_fn(q))
        for q in generated_questions
    ]
    return sum(sims) / len(sims)
```

(Reusing `cosine_similarity` from [`standard_rag_core.py`](./standard_rag_core.py)
— this is exactly the operation it was built to demonstrate.)

### 3. Context Precision / Recall

**How it works (production, RAGAS-style):** LLM-judged, not exact-match —
for each retrieved chunk, ask "was this actually useful for producing the
ground-truth answer?" (precision), and separately, "does the retrieved
context contain everything the ground-truth answer needed?" (recall).
**Use case:** the debugging split mentioned above — isolates retriever
failures from generator failures before you go tune the wrong component.

### 4. Traditional Recall@k / MRR — offline retriever benchmarking

**How it works:** exact-match against a labeled relevant-doc set — no LLM
call needed, cheap and deterministic. This is why it's used offline during
development (comparing embedding models/chunk sizes) rather than live in
production, where you rarely have ground-truth relevance labels for real
user queries.
**Use case:** "should we switch from `text-embedding-3-small` to `-large`, or
change chunk size from 256 to 512?" — run against a fixed labeled eval set
and compare.

```python
def recall_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    retrieved_top_k = set(retrieved_ids[:k])
    return len(retrieved_top_k & relevant_ids) / len(relevant_ids)

def mrr(retrieved_ids: list[str], relevant_ids: set[str]) -> float:
    for rank, doc_id in enumerate(retrieved_ids, start=1):
        if doc_id in relevant_ids:
            return 1 / rank
    return 0.0
```

## Is the RAG Triad alone sufficient?

**Question asked:** *"so the production-grade evaluation uses modern approach
triad as mentioned in the website? query -> context -> response? just need
to focus on this triad is sufficient?"*

**Answer:** Confirm the shape, but "sufficient" is too strong.

The triad is literally a triangle over three things — **query, retrieved
context, generated response** — and each metric checks one edge:

```
        Context Relevance
    query ───────────────── context
      │                        │
      │  Answer Relevance      │  Faithfulness/
      │  (query ↔ response)    │  Groundedness
      │                        │  (context ↔ response)
      └────────── response ────┘
```

It's the core quality layer and the most important starting point — but not
the whole production eval story. Five gaps it doesn't cover:

1. **It's entirely reference-free — checks *consistency*, not *correctness*.**
   Faithfulness only asks "is the answer consistent with the retrieved
   context?" If the retrieved context itself is stale or wrong, a perfectly
   "faithful" answer can still be wrong in the real world. Fixed by a
   **labeled regression eval set** (real ground-truth answers, checked
   periodically) — a separate discipline from the reference-free triad.
2. **It doesn't tune the retriever itself.** Context Relevance says "was
   what we retrieved relevant," not "did we miss a better document that
   exists in the index." That needs traditional Recall@k/MRR against
   labeled relevant-doc pairs, offline.
3. **It skips safety/compliance guardrails entirely.** PII leakage,
   toxicity, prompt-injection resistance, domain-specific business rules
   aren't semantic-similarity questions — they're usually deterministic
   checks, not LLM judgments.
4. **It's expensive to run on every request.** Each triad metric is an LLM
   call (or several, for faithfulness's claim-by-claim check) — production
   systems typically *sample* live traffic rather than scoring every
   request synchronously.
5. **For agentic RAG specifically** (tool calls, multi-step retrieval,
   iterative reasoning), the triad only evaluates the final query/context/
   response triangle — it says nothing about whether the agent called the
   right tools, in the right order, or stopped after the right number of
   steps.

So: the triad is the right starting point and the single most important
layer (faithfulness especially), but a production-grade eval stack is the
triad *plus* a labeled regression set, retriever-tuning metrics, guardrail/
safety checks, tool-call/trajectory correctness, and ops monitoring — not
the triad alone. See the next section for each of these mapped to a real
codebase.

## Production-Grade Eval Stack, Mapped to `finance_agent`

**Question asked:** *"please give me all details of the production-grade
eval stack you just mention, and maybe reference to finance_agent for more
information, and explain me what kind of action is that eval used for (used
for step of rag retrieval, or used for step of mcp tools call in total,
stuff like this, etc)"*

Each layer below targets a specific step or action in the pipeline —
retrieval step, the tool-calling loop, the generation step, the guardrail
layer, or the whole request — grounded in the actual `finance_agent/`
code rather than left abstract.

### Overview table

| Layer | Targets (what action/step) | Needs LLM judge? | Runs when | `finance_agent` reference |
|---|---|---|---|---|
| 1. Unit tests | Guardrail logic + tool logic (pure code) | No | Every commit (CI) | `tests/test_guardrails.py`, `tests/test_tools.py` |
| 2. RAG Triad | Retrieval→generation handoff specifically | Yes | Sampled live traffic / dev | Investigator's tool evidence → decision agent's output |
| 3. Ground-truth regression | Whole pipeline, end-to-end outcome | Optional | Before every deploy | `evals/run_evals.py` + `kyc_cases.jsonl`/`support_cases.jsonl` (already built) |
| 4. Retriever tuning (Recall@k/MRR) | Retrieval step only, in isolation | No | Offline dev only | `search_knowledge_base()` in `tools.py` |
| 5. Tool-call / trajectory correctness | The ReAct tool-calling loop itself | No (rule-based) | Every eval run | `INVESTIGATION_SYSTEM_PROMPT`'s 3 required tools |
| 6. Guardrail override-rate | Model-vs-policy drift, over time | No | Production monitoring | `guardrail_overrode_model` field already returned by `review_case()` |
| 7. Ops metrics | Whole request (latency/cost/errors) | No | 100% of production traffic | `latency_seconds` already returned by `review_case()` |

### 1. Unit tests — code correctness, not model quality

**Targets:** the deterministic, non-LLM parts of the pipeline —
`guardrails.py`'s rule logic and `tools.py`'s mock lookups. Not really "RAG
eval" in the ML sense, but it's the foundation everything else sits on: if
`apply_kyc_guardrails` has a bug, no amount of faithfulness scoring on the
LLM output matters.
**Already exists:** `tests/test_guardrails.py`, `tests/test_tools.py` — pure
`pytest`, no API key, no LLM call, exactly like `test_standard_rag_core.py`
in this folder.

### 2. RAG Triad — the retrieval→generation handoff

**Targets:** specifically the boundary between "what evidence did we
gather" and "what did we conclude from it" — in `kyc_agent.py`'s two-stage
design (`kyc_agent.py:78-125`), that's the handoff from the investigator's
tool evidence (`evidence` dict) to the decision agent's output
(`raw_decision`).

- **Context Relevance** → was the evidence gathered even relevant to this
  case? In the support-agent path, `search_knowledge_base()` in
  `tools.py:140` is explicitly documented as *"a stand-in for a vector
  database lookup in a production RAG pipeline"* — so this is the exact
  function Context Relevance would score if `_KNOWLEDGE_BASE`'s
  keyword-overlap search were swapped for real embeddings.
- **Faithfulness** → does `investigation_summary` (and the final
  `KYCDecision.reasons`) only state things actually present in the raw tool
  evidence, or did the model invent something ("assumed the ID was valid"
  when `verify_id_format` was never even called)?
- **Answer Relevancy** → does the final decision actually address *this*
  case's specifics, not a generic templated response?

```python
# Concrete faithfulness check for finance_agent's own pipeline
result = review_case(case, llm=llm)
score = faithfulness_score(
    answer=result["investigation_summary"],
    context=json.dumps(result["evidence"]),
    llm=llm,
)
```

### 3. Ground-truth regression — already built, worth naming explicitly

**Targets:** the whole pipeline's final output vs. a known-correct label —
this is what `evals/run_evals.py` already does, and its own docstring
(`run_evals.py:5-14`) already draws exactly the "hard vs soft check"
distinction production teams use:
- **Hard checks** (`kyc_cases.jsonl`): guardrail-enforced invariants — e.g.
  a watchlist hit must never end in `"approve"` — expected to pass every
  single run regardless of model variance, because the deterministic
  guardrail layer makes them non-negotiable.
- **Soft checks** (`support_cases.jsonl`): expected model classification — a
  mismatch is model judgment variance, not a bug, so it's reported but
  doesn't fail CI.

This is the labeled regression layer that fixes the triad's "consistency ≠
correctness" blind spot from the section above — `finance_agent` already has
it.

### 4. Retriever tuning (Recall@k/MRR) — retrieval step in isolation, offline only

**Targets:** *only* the retrieval function, never the LLM. In
`finance_agent`, that's `search_knowledge_base()` (`tools.py:139-165`) —
currently keyword-overlap scoring against `_KNOWLEDGE_BASE`. If this were
upgraded to real embeddings + a vector store, Recall@k/MRR against a labeled
`(query, correct_article_id)` set is exactly how you'd decide whether the
new retriever is actually better, with zero LLM calls needed:

```python
labeled_queries = [
    ("my card was declined at the store", {"KB-101"}),
    ("someone logged into my account", {"KB-102"}),
]
for query, relevant in labeled_queries:
    result = json.loads(search_knowledge_base.invoke({"query": query}))
    retrieved = [result["article_id"]] if result["matched"] else []
    print(recall_at_k(retrieved, relevant, k=1))
```

### 5. Tool-call / trajectory correctness — the ReAct loop itself, separate from the outcome

**Targets:** whether the agent's *process* was correct, independent of
whether the final answer happened to be right. `INVESTIGATION_SYSTEM_PROMPT`
(`kyc_agent.py:38-51`) requires all three tools be called every time — but a
case could reach the *correct* final status even if the investigator
skipped `check_watchlist` (e.g. the ID format check alone was enough to
reject it). That's a process failure the outcome-only regression eval (#3)
would never catch, since it only checks `final_decision.status`.

```python
REQUIRED_KYC_TOOLS = {"verify_id_format", "check_watchlist", "check_document_consistency"}

def tool_call_completeness(messages: list) -> float:
    called = {json.loads(m.content)["tool"] for m in messages if isinstance(m, ToolMessage)}
    return len(called & REQUIRED_KYC_TOOLS) / len(REQUIRED_KYC_TOOLS)
```

This is what "evaluate the MCP/tool-calling step in total" maps to — it's
checking the agent's *actions*, not its final text output.

### 6. Guardrail override-rate — is the model drifting from policy?

**Targets:** the gap between what the LLM decided and what the deterministic
policy layer had to correct. `review_case()` already computes and returns
this per-case (`kyc_agent.py:123`:
`"guardrail_overrode_model": raw_decision.status != final_decision.status`)
— it's not being aggregated anywhere yet, but it's a free production health
signal: if the override rate trends upward over weeks, the model (or a
prompt/provider change) is drifting away from policy, even though every
single case still ends in the *correct* final status thanks to the
guardrail catching it.

```python
def guardrail_override_rate(results: list[dict]) -> float:
    overridden = sum(1 for r in results if r["guardrail_overrode_model"])
    return overridden / len(results) if results else 0.0
```

### 7. Ops metrics — the whole request, cheap, on 100% of traffic

**Targets:** latency, cost, error rate — already partially present
(`latency_seconds`, printed by `run_evals.py:49`). This is the layer that
runs on every single production request, unlike the LLM-judged triad which
gets sampled due to cost.
