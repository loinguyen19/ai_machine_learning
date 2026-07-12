"""Shared LLM provider factory — mirrors the pattern used across this repo's agent projects."""

from __future__ import annotations

import os


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def create_llm():
    from langchain_anthropic import ChatAnthropic
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_openai import ChatOpenAI

    provider = os.getenv("LLM_PROVIDER", "google").strip().lower()

    if provider == "openrouter":
        return ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=_require_env("OPEN_ROUTER_AI_API_KEY"),
            model=os.getenv("LLM_MODEL", "meta-llama/llama-3.3-70b-instruct:free"),
            temperature=0,
        )

    if provider == "openai":
        return ChatOpenAI(
            api_key=_require_env("OPENAI_API_KEY"),
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            temperature=0,
        )
    
    if provider == "anthropic":
        return ChatAnthropic(
            api_key=_require_env("ANTHROPIC_API_KEY"),
            model=os.getenv("LLM_MODEL", "claude-sonnet-5"),
            temperature=0,
        )

    return ChatGoogleGenerativeAI(
        model=os.getenv("LLM_MODEL", "gemini-2.5-flash-lite"),
        temperature=0,
    )
