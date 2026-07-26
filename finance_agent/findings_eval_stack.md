# Findings: A Production-Grade Eval Stack for `finance_agent`

This doc captures a Q&A about what a full production-grade evaluation stack
looks like for an agentic RAG-style system, and maps every layer of it onto
this repo's actual code — `src/kyc_agent.py`, `src/tools.py`,
`src/guardrails.py`, and `evals/run_evals.py` — rather than leaving it
abstract. For the underlying math of the "RAG Triad" (faithfulness, answer
relevancy, context relevance) and why it alone isn't sufficient, see
[`../simulated_rag_live_coding_test/rag_evaluation.md`](../simulated_rag_live_coding_test/rag_evaluation.md).

**Question asked:** *"please give me all details of the production-grade
eval stack you just mention, and maybe reference to finance_agent for more
information, and explain me what kind of action is that eval used for (used
for step of rag retrieval, or used for step of mcp tools call in total,
stuff like this, etc)"*

Each layer below targets a specific step or action in the pipeline —
retrieval step, the tool-calling loop, the generation step, the guardrail
layer, or the whole request.

## Overview table

| Layer | Targets (what action/step) | Needs LLM judge? | Runs when | `finance_agent` reference |
|---|---|---|---|---|
| 1. Unit tests | Guardrail logic + tool logic (pure code) | No | Every commit (CI) | `tests/test_guardrails.py`, `tests/test_tools.py` |
| 2. RAG Triad | Retrieval→generation handoff specifically | Yes | Sampled live traffic / dev | Investigator's tool evidence → decision agent's output |
| 3. Ground-truth regression | Whole pipeline, end-to-end outcome | Optional | Before every deploy | `evals/run_evals.py` + `evals/kyc_cases.jsonl`/`support_cases.jsonl` (already built) |
| 4. Retriever tuning (Recall@k/MRR) | Retrieval step only, in isolation | No | Offline dev only | `search_knowledge_base()` in `src/tools.py` |
| 5. Tool-call / trajectory correctness | The ReAct tool-calling loop itself | No (rule-based) | Every eval run | `INVESTIGATION_SYSTEM_PROMPT`'s 3 required tools in `src/kyc_agent.py` |
| 6. Guardrail override-rate | Model-vs-policy drift, over time | No | Production monitoring | `guardrail_overrode_model` field already returned by `review_case()` |
| 7. Ops metrics | Whole request (latency/cost/errors) | No | 100% of production traffic | `latency_seconds` already returned by `review_case()` |

## 1. Unit tests — code correctness, not model quality

**Targets:** the deterministic, non-LLM parts of the pipeline —
`src/guardrails.py`'s rule logic and `src/tools.py`'s mock lookups. Not
really "RAG eval" in the ML sense, but it's the foundation everything else
sits on: if `apply_kyc_guardrails` has a bug, no amount of faithfulness
scoring on the LLM output matters.
**Already exists:** `tests/test_guardrails.py`, `tests/test_tools.py` — pure
`pytest`, no API key, no LLM call.

## 2. RAG Triad — the retrieval→generation handoff

**Targets:** specifically the boundary between "what evidence did we
gather" and "what did we conclude from it" — in `src/kyc_agent.py`'s
two-stage design (`review_case()`, roughly lines 78-125), that's the
handoff from the investigator's tool evidence (`evidence` dict) to the
decision agent's output (`raw_decision`).

- **Context Relevance** → was the evidence gathered even relevant to this
  case? In the support-agent path, `search_knowledge_base()` in
  `src/tools.py` is explicitly documented in its own docstring as *"a
  stand-in for a vector database lookup in a production RAG pipeline"* — so
  this is the exact function Context Relevance would score if
  `_KNOWLEDGE_BASE`'s keyword-overlap search were swapped for real
  embeddings.
- **Faithfulness** → does `investigation_summary` (and the final
  `KYCDecision.reasons`) only state things actually present in the raw tool
  evidence, or did the model invent something ("assumed the ID was valid"
  when `verify_id_format` was never even called)?
- **Answer Relevancy** → does the final decision actually address *this*
  case's specifics, not a generic templated response?

### Recommended: use the `ragas` library directly

Don't hand-roll this in production — `ragas` (PyPI, latest `0.4.3` at time of
writing) is the de facto standard implementation of the RAG Triad and is
maintained/versioned/tested far beyond what's worth building in-house.

```python
# finance_agent/evals/eval_faithfulness.py — run from the evals/ dir, same
# sys.path pattern run_evals.py already uses.
import json
import sys
from pathlib import Path

EVALS_DIR = Path(__file__).resolve().parent
SRC_DIR = EVALS_DIR.parent / "src"
sys.path.insert(0, str(SRC_DIR))

from kyc_agent import review_case  # noqa: E402
from llm import create_llm  # noqa: E402

from ragas import SingleTurnSample
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import Faithfulness


def faithfulness_score(question: str, answer: str, context: str, llm) -> float:
    ragas_llm = LangchainLLMWrapper(llm)  # wraps finance_agent's existing LangChain chat model
    metric = Faithfulness(llm=ragas_llm)
    sample = SingleTurnSample(user_input=question, response=answer, retrieved_contexts=[context])
    return metric.single_turn_score(sample)  # some ragas versions require `await metric.single_turn_ascore(sample)`


if __name__ == "__main__":
    llm = create_llm()
    case = {
        "full_name": "Le Thi Mai",
        "id_type": "national_id",
        "id_number": "012345678901",
        "name_on_document": "Le Thi Mai",
        "dob_on_form": "1995-04-02",
        "dob_on_document": "1995-04-02",
    }
    result = review_case(case, llm=llm)
    score = faithfulness_score(
        question=f"Review the KYC case for {case['full_name']}",
        answer=result["investigation_summary"],
        context=json.dumps(result["evidence"]),
        llm=llm,
    )
    print(f"faithfulness: {score:.2f}")
```

Two things worth knowing before wiring this in for real:

1. **`question` doesn't map cleanly onto a KYC case.** RAGAS metrics are
   shaped for Q&A (`user_input`/`response`/`retrieved_contexts`), so this
   uses the investigation prompt (`case_text` from `review_case()`) as the
   "question" — the thing `investigation_summary` is actually responding to,
   even though it isn't a literal question.
2. **Pin a `ragas` version and check that version's docs.** The exact
   class/method names have shifted across releases (`0.1.x` used
   `from ragas.metrics import faithfulness` as a ready-made instance plus
   `evaluate(dataset, metrics=[...])`; `0.2+` moved to `Faithfulness(llm=...)`
   classes plus `SingleTurnSample`, shown above).
3. **Same caveat as the earlier `with_structured_output` bug in this repo**
   — if `LLM_PROVIDER` is set to the `langchain_claude_code` (Claude Code
   subscription) provider, `ragas`'s internal LLM calls may hit the same
   `bind_tools` crash debugged earlier, since some `ragas` metrics use
   structured-output-style prompting internally. Test against `openai` or
   `google` first to isolate whether a failure is `ragas` or that same
   provider gap.

### Under the hood: what `ragas.Faithfulness` is actually doing

Useful to know even if you never hand-roll this for real — this is the
literal mechanism `ragas`'s LLM calls implement, and it's exactly the
`F = |V| / |S|` formula from the RAG Triad:

```python
def faithfulness_score(answer: str, context: str, llm) -> float:
    """LLM-as-judge: decompose the answer into atomic claims, check each
    claim is verifiable against the raw tool evidence. Same F = |V| / |S|
    formula used by RAGAS/TruLens.
    """
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

## 3. Ground-truth regression — already built, worth naming explicitly

**Targets:** the whole pipeline's final output vs. a known-correct label —
this is what `evals/run_evals.py` already does, and its own docstring
already draws exactly the "hard vs soft check" distinction production teams
use:
- **Hard checks** (`kyc_cases.jsonl`): guardrail-enforced invariants — e.g.
  a watchlist hit must never end in `"approve"` — expected to pass every
  single run regardless of model variance, because the deterministic
  guardrail layer makes them non-negotiable.
- **Soft checks** (`support_cases.jsonl`): expected model classification — a
  mismatch is model judgment variance, not a bug, so it's reported but
  doesn't fail CI.

This is the labeled regression layer that fixes the RAG Triad's "consistency
≠ correctness" blind spot (see the RAG evaluation doc linked at the top) —
`finance_agent` already has it, running via `make run-evals` (or
`python3 evals/run_evals.py`).

## 4. Retriever tuning (Recall@k/MRR) — retrieval step in isolation, offline only

**Targets:** *only* the retrieval function, never the LLM. In
`finance_agent`, that's `search_knowledge_base()` (`src/tools.py`) —
currently keyword-overlap scoring against `_KNOWLEDGE_BASE`. If this were
upgraded to real embeddings + a vector store, Recall@k/MRR against a
labeled `(query, correct_article_id)` set is exactly how you'd decide
whether the new retriever is actually better, with zero LLM calls needed:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from tools import search_knowledge_base  # noqa: E402


def recall_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    retrieved_top_k = set(retrieved_ids[:k])
    return len(retrieved_top_k & relevant_ids) / len(relevant_ids)


labeled_queries = [
    ("my card was declined at the store", {"KB-101"}),
    ("someone logged into my account", {"KB-102"}),
    ("I can't log in, forgot my password", {"KB-103"}),
]

for query, relevant in labeled_queries:
    result = json.loads(search_knowledge_base.invoke({"query": query}))
    retrieved = [result["article_id"]] if result["matched"] else []
    print(f"{query!r}: recall@1={recall_at_k(retrieved, relevant, k=1)}")
```

## 5. Tool-call / trajectory correctness — the ReAct loop itself, separate from the outcome

**Targets:** whether the agent's *process* was correct, independent of
whether the final answer happened to be right. `INVESTIGATION_SYSTEM_PROMPT`
in `src/kyc_agent.py` requires all three tools be called every time — but a
case could reach the *correct* final status even if the investigator
skipped `check_watchlist` (e.g. the ID format check alone was enough to
reject it). That's a process failure the outcome-only regression eval (#3)
would never catch, since it only checks `final_decision.status`.

```python
from langchain_core.messages import ToolMessage

REQUIRED_KYC_TOOLS = {"verify_id_format", "check_watchlist", "check_document_consistency"}


def tool_call_completeness(messages: list) -> float:
    called = {
        json.loads(m.content)["tool"]
        for m in messages
        if isinstance(m, ToolMessage)
    }
    return len(called & REQUIRED_KYC_TOOLS) / len(REQUIRED_KYC_TOOLS)
```

This is what "evaluate the MCP/tool-calling step in total" maps to — it's
checking the agent's *actions* during the investigation stage, not its
final text output. To wire this in, `review_case()` would need to return
`messages` alongside its current fields (it currently only returns
`evidence`, derived from the tool messages, not the messages themselves).

## 6. Guardrail override-rate — is the model drifting from policy?

**Targets:** the gap between what the LLM decided and what the deterministic
policy layer had to correct. `review_case()` already computes and returns
this per-case (`"guardrail_overrode_model": raw_decision.status !=
final_decision.status"` in `src/kyc_agent.py`) — it's not being aggregated
anywhere yet, but it's a free production health signal: if the override
rate trends upward over weeks, the model (or a prompt/provider change) is
drifting away from policy, even though every single case still ends in the
*correct* final status thanks to the guardrail catching it.

```python
def guardrail_override_rate(results: list[dict]) -> float:
    overridden = sum(1 for r in results if r["guardrail_overrode_model"])
    return overridden / len(results) if results else 0.0


# e.g. inside evals/run_evals.py's run_kyc_evals(), after the loop:
# results = [review_case(spec["case"], llm=llm) for spec in cases]
# print(f"guardrail override rate: {guardrail_override_rate(results):.2%}")
```

## 7. Ops metrics — the whole request, cheap, on 100% of traffic

**Targets:** latency, cost, error rate — already partially present
(`latency_seconds`, printed by `run_evals.py`). This is the layer that runs
on every single production request, unlike the LLM-judged triad which gets
sampled due to cost.
