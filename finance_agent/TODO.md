 https://jobs.ashbyhq.com/bjakcareer/6a2a0e0b-ae4b-43d8-8716-f8f3a63e65d1?utm_source=YmpnOkRB66

⏺ Fetch(https://jobs.ashbyhq.com/bjakcareer/6a2a0e0b-ae4b-43d8-8716-f8f3a63e65d1?utm_source=YmpnOkRB66)
Received 88.3KB (200 OK)

The Ashby page is JavaScript-rendered, so the fetch tool only sees an empty shell. Let me try pulling the raw page source directly to find the embedded job data.

  Ran 1 shell command

Good, got the meta description with substantial content. Let me get the rest of the JD — it's truncated at "WHAT WE".

  Ran 2 shell commands

Good — this is a materially different (and much more specific) JD than the generic listing I pulled earlier, which appears to be for a different regional posting (heavier ML-infra stack). Here's what changes in my advice:

What's actually different

This Vietnam role is not research/ML-infra heavy (no PyTorch/JAX/vLLM/fine-tuning emphasis mentioned) — it's about shipping AI agents and automation workflows into BJAK's AI Neobank app, specifically for: onboarding, support, KYC, risk review, CRM, operations, document handling, product intelligence. Stack is explicitly "Python, TypeScript, JavaScript or similar" — full-stack app building, not model training.

The "THIS ROLE IS NOT FOR" section is the clearest signal of what they'll screen against in the technical interview:
- Not for demo-only builders → expect them to probe "did this actually run in production with real users?"
- Not for people who don't care about evals/reliability → expect a question on how you'd measure/guard against a bad output
- Not for people who overclaim AI impact → be precise and honest about what you built vs. what a team built
- Not for people who can't work with product/ops → expect a "how would you scope this with a PM" style question

Revised technical prep priorities

1. Agent/tool-calling fundamentals: how you'd design an agent that calls tools (APIs, DB lookups, doc parsers) reliably, with structured output, retries, and fallback when the model is uncertain.
2. RAG basics: retrieval + chunking + grounding, and specifically how you prevent hallucination in a finance context (citations, confidence thresholds, refuse-to-answer paths).
3. Guardrails & evals: how to test an LLM feature before and after shipping — golden test sets, LLM-as-judge, regression checks when you change a prompt, human-in-the-loop review for high-risk actions (e.g., KYC decisions, risk flags).
4. Practical coding in Python or TypeScript — since live coding is on your laptop with your normal editor (minus AI assistance), be fluent writing an API call, parsing/validating structured JSON output from an LLM, and wiring a small tool-calling loop from scratch.
5. Domain scenarios to have a POV on: automating KYC document review, fraud/risk flagging, CRM/support ticket triage, onboarding copilots — these map directly to "WHAT YOU WILL BUILD." Be ready to sketch one end-to-end: inputs → model/tool calls → guardrails → human escalation path → how you'd measure it's working.
6. Cost/latency/security/compliance tradeoffs — they list these explicitly as design constraints, so mention them unprompted when you design something (e.g., "I'd cache retrieval results," "I'd redact PII before sending to the LLM," "I'd add a confidence gate before auto-approving a KYC document").

What matters less now

Deprioritize deep transformer math, fine-tuning/training internals, and vLLM/serving-infra trivia — those fit the other regional posting's stack, not this one.

Revised practice suggestion

Build a small end-to-end demo before the interview: a tool-calling agent that takes a simulated user request (e.g., "review this KYC document" or "triage this support ticket"), calls 1–2 mock tools, returns structured output, and has a basic guardrail (e.g., low-confidence → escalate to human). Practice narrating the design tradeoffs out loud — that's closer to what a 90-minute technical + live-coding round with this JD will probe than a pure algorithms drill.

The logistics advice from before (camera/no virtual background, phone dial-in, closing extra apps since they spot-check Task Manager) still stands unchanged.