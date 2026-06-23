import asyncio
import os
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI

from rag.seed_history import seed_client_memory

SRC_DIR = Path(__file__).resolve().parent
load_dotenv(SRC_DIR.parent / ".env")

HOLIDAY_SYSTEM_PROMPT = """You are a professional holiday planning assistant.

Your job: turn a short client brief into a detailed, personalized trip plan.

WORKFLOW (follow in order):
1. Call get_client_profile and search_client_memory for the client_id in the brief.
2. Call tavily_web_search (2-4 queries) for destination facts, seasonal tips, food, and attractions.
3. Build a complete plan with day-by-day agenda, budget notes, food picks, and packing tips.
4. Choose exactly 3-5 destination scenes with title, caption, location, image_search_query, and optional day_number.
5. Call render_destination_scenes with work_id and a JSON array of scene objects.
6. Call save_holiday_plan with the same work_id and full TripPlan JSON (plan_id must equal work_id).

RULES:
- Personalize using RAG memory (past trips, food prefs, budget habits, dislikes).
- Never recommend crowded group bus tours if the client dislikes them.
- Cite specific memory snippets and web sources in your final answer.
- Use the same work_id for render_destination_scenes and save_holiday_plan.
- Agenda must have at least 3 days with morning/afternoon/evening activities.
- Final response must mention:
  - final_plan/plan.pdf (latest deliverable, overwritten each run)
  - artifacts/scenes/{work_id}/ (scenes + plan.json + plan.md for this run)
  - artifacts/pdf/{work_id}/plan.pdf (archived PDF for this run)
"""

EXAMPLE_BRIEF = """Client: maria
- Interests: temples, local markets, photography
- Food: vegetarian, street food ok
- Budget: $2500 for 7 days
- Favorite places: Kyoto vibe (visited Tokyo before, loved it)
- Season: late March
"""


def create_llm():
    provider = os.getenv("LLM_PROVIDER", "openrouter").strip().lower()
    if provider == "google":
        return ChatGoogleGenerativeAI(
            model=os.getenv("LLM_MODEL", "gemini-2.5-flash"),
            temperature=0.7,
        )

    api_key = os.getenv("OPEN_ROUTER_AI_API_KEY", "").strip()
    if not api_key:
        # Fall back to Gemini when OpenRouter key is absent
        return ChatGoogleGenerativeAI(
            model=os.getenv("LLM_MODEL", "gemini-2.5-flash"),
            temperature=0.7,
        )
    return ChatOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        model=os.getenv("LLM_MODEL", "meta-llama/llama-3.3-70b-instruct:free"),
        temperature=0.7,
    )


async def ensure_memory_seeded() -> None:
    result = seed_client_memory(force=False)
    if result["status"] == "seeded":
        print(f"[startup] {result['message']}")


async def main() -> None:
    await ensure_memory_seeded()

    client = MultiServerMCPClient(
        {
            "holiday_planner": {
                "command": sys.executable,
                "args": [str(SRC_DIR / "server.py")],
                "transport": "stdio",
            }
        }
    )
    tools = await client.get_tools()

    llm = create_llm()
    agent = create_agent(llm, tools, system_prompt=HOLIDAY_SYSTEM_PROMPT)

    client_id = os.getenv("CLIENT_ID", "maria")
    work_id = os.getenv("WORK_ID") or os.getenv("PLAN_ID") or str(uuid.uuid4())
    user_brief = os.getenv("USER_BRIEF", EXAMPLE_BRIEF)

    query = (
        f"Work ID to use: {work_id}\n"
        f"Client ID: {client_id}\n\n"
        f"{user_brief}"
    )

    model_name = getattr(llm, "model_name", None) or getattr(llm, "model", "unknown")
    print(f"Running holiday planner (work_id={work_id}, client_id={client_id}, model={model_name})...\n")
    result = await agent.ainvoke({"messages": [("user", query)]})

    for message in result["messages"]:
        message.pretty_print()

    print(f"\n[done] Latest deliverable: final_plan/plan.pdf")


if __name__ == "__main__":
    asyncio.run(main())
