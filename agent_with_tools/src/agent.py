"""LangChain search agent — answers client questions using Tavily web search."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from tavily import TavilyClient

SRC_DIR = Path(__file__).resolve().parent
load_dotenv(SRC_DIR.parent / ".env")

SEARCH_SYSTEM_PROMPT = """You are a helpful research assistant for clients.

Your job is to answer any question accurately using the web_search tool when needed.

WORKFLOW:
1. Decide whether the question needs current or factual web information.
2. If yes, call web_search with a focused query (you may search more than once).
3. Synthesize a clear, complete answer in plain language.
4. Cite sources when web_search was used (mention site titles or URLs from results).

RULES:
- Prefer web_search for news, prices, events, people, places, and anything time-sensitive.
- For simple general knowledge you are confident about, you may answer directly.
- If search results are thin or conflicting, say what you found and what is uncertain.
- Be concise but thorough. Use bullet points for multi-part answers when helpful.
- Never invent URLs or facts not supported by search results or your reasoning.
"""


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def create_llm():
    provider = os.getenv("LLM_PROVIDER", "google").strip().lower()

    if provider == "openrouter":
        api_key = _require_env("OPEN_ROUTER_AI_API_KEY")
        return ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            model=os.getenv("LLM_MODEL", "meta-llama/llama-3.3-70b-instruct:free"),
            temperature=0.3,
        )

    if provider == "openai":
        return ChatOpenAI(
            api_key=_require_env("OPENAI_API_KEY"),
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            temperature=0.3,
        )

    return ChatGoogleGenerativeAI(
        model=os.getenv("LLM_MODEL", "gemini-2.5-flash-lite"),
        temperature=0.3,
    )


def _format_search_results(payload: dict[str, Any]) -> str:
    lines: list[str] = []

    answer = payload.get("answer")
    if answer:
        lines.append(f"Summary: {answer}")

    results = payload.get("results") or []
    if results:
        lines.append("Sources:")
        for idx, item in enumerate(results, start=1):
            title = item.get("title") or "Untitled"
            url = item.get("url") or ""
            snippet = (item.get("content") or "").strip()
            if len(snippet) > 400:
                snippet = snippet[:400] + "..."
            lines.append(f"{idx}. {title}")
            if url:
                lines.append(f"   URL: {url}")
            if snippet:
                lines.append(f"   {snippet}")

    if not lines:
        return "No results found."

    return "\n".join(lines)


@tool
def web_search(query: str) -> str:
    """Search the web for current information about a topic, person, place, event, or fact."""

    client = TavilyClient(api_key=_require_env("TAVILY_API_KEY"))
    response = client.search(query=query, max_results=5, include_answer=True)
    return _format_search_results(response)


def create_search_agent(llm=None):
    llm = llm or create_llm()
    return create_agent(
        llm,
        tools=[web_search],
        system_prompt=SEARCH_SYSTEM_PROMPT,
    )


def run_query(agent, question: str) -> str:
    result = agent.invoke({"messages": [("user", question)]})
    messages = result.get("messages", [])
    if not messages:
        return ""

    last = messages[-1]
    content = getattr(last, "content", last)
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(p for p in parts if p).strip()
    return str(content).strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Search agent — answer client questions with Tavily web search.",
    )
    parser.add_argument(
        "question",
        nargs="?",
        help="Question to ask (omit for interactive mode or USER_QUERY env)",
    )
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Chat loop: keep asking questions until you type exit",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    llm = create_llm()
    agent = create_search_agent(llm)
    model_name = getattr(llm, "model_name", None) or getattr(llm, "model", "unknown")
    print(f"Search agent ready (model={model_name}). Type 'exit' to quit.\n")

    def handle(question: str) -> None:
        question = question.strip()
        if not question:
            return
        print(f"\nClient: {question}\n")
        answer = run_query(agent, question)
        print(f"Agent: {answer}\n")

    if args.interactive or (not args.question and not os.getenv("USER_QUERY")):
        while True:
            try:
                question = input("Client> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nBye.")
                break
            if question.lower() in {"exit", "quit", "q"}:
                print("Bye.")
                break
            handle(question)
        return

    question = args.question or os.getenv("USER_QUERY", "").strip()
    if not question:
        print("No question provided. Pass one as an argument or set USER_QUERY.", file=sys.stderr)
        sys.exit(1)

    handle(question)


if __name__ == "__main__":
    main()
