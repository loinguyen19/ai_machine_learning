"""Shared LLM provider factory — mirrors the pattern used across this repo's agent projects."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

SRC_DIR = Path(__file__).resolve().parent
load_dotenv(SRC_DIR.parent / ".env")

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
    print(f"Using LLM provider: {provider}")

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
    # this is for API billing    
    # if provider == "anthropic":
    #     return ChatAnthropic(
    #         api_key=_require_env("ANTHROPIC_API_KEY"),
    #         model=os.getenv("LLM_MODEL", "claude-sonnet-5"),
    #         temperature=0,
    #     )

    # this is for subscription billing
    if provider == "anthropic":
        from langchain_claude_code import ClaudeCodeChatModel
        return ClaudeCodeChatModel (
            oauth_token=_require_env("CLAUDE_CODE_OAUTH_TOKEN"),
            model=os.getenv("LLM_MODEL", "claude-sonnet-5")
        )

    return ChatGoogleGenerativeAI(
        google_api_key=_require_env("GOOGLE_API_KEY"),
        model=os.getenv("LLM_MODEL", "gemini-2.5-flash-lite"),
        temperature=0,
    )

# from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock
# import asyncio
# async def anthropic_agent(user_prompt, tools=None, system_prompt=None):
#     async for msg in query(
#             prompt=user_prompt,
#             options=ClaudeAgentOptions(
#                 allowed_tools=[],
#                 tools=tools,
#                 system_prompt=system_prompt
#             )
#         ):
#         print(f"\n\nmessage: {msg}\n\n")
#         if isinstance(msg, AssistantMessage):
#             for block in msg.content:
#                 if isinstance(block, TextBlock):
#                     print(f"\nblock.text: {block.text}\n")
#                 print(f"\nblock: {block}\n")

from pydantic import BaseModel
class CityInfo(BaseModel):
    id: str
    name: str
    location: str
    country: str


if __name__ == "__main__":
    model = create_llm()

    from langchain.agents import create_agent

    agent = create_agent(model, tools=[], response_format=CityInfo)

    # approach 1: use [("user", "question")]
    # question = "Hello, how are you?"
    # print(f"User: {question}")
    # resp = agent.invoke({"messages": [("user", question)]})
    # print(f"response_1: {resp}")
    # last = resp["messages"][-1]
    # print(f"Agent 1: {last.content}")

    # approach 2: use HumanMessage
    from langchain.messages import HumanMessage
    import json
    question = "Hello, what is the capital of Vietnam? And how much is population?"
    resp = agent.invoke({"messages": [HumanMessage(content=question)]})
    print(f"response_2: {resp}\n\n")
    last = resp["messages"][-1]
    print(f"first message: {resp["messages"][0]}")
    print(f"\nlast message: {last}\n\n")
    print(f"\nAgent 2: {last.content}\n")

    # user_prompt = "what is the capital of Vietnam? How much is population"
    # asyncio.run(anthropic_agent(user_prompt))
