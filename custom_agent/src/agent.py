import asyncio
from dotenv import load_dotenv
import os

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from openai import OpenAI

load_dotenv()


async def main():
    client = MultiServerMCPClient({
        "advanced_explorer": {
            "command": "python",
            "args": ["server.py"],
            "transport": "stdio"
        }
    })
    tools = await client.get_tools()
    open_router_ai_api_key = os.getenv("OPEN_ROUTER_AI_API_KEY")
    # print(f"open_router_ai_api_key = {open_router_ai_api_key}")

    google_api_key = os.getenv("GOOGLE_API_KEY")
    gemini_llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",  # Highly capable free-tier model
        temperature=0.7
    )

    llm = ChatOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=open_router_ai_api_key,  # must generate an api key on OpenAI with Dev Account creation
        model_name="meta-llama/llama-3.3-70b-instruct:free",  # please check regularly for mismatched version/model name, change frequently by OpenRouter AI
        temperature=0
    )  # Low temperature for factual RAG

    # This agent uses the ReAct (Reasoning + Acting) loop
    agent = create_agent(gemini_llm, tools)

    # AGENTIC RAG EXECUTION:
    # The agent must first ingest, then search, then check the graph.
    query = (
        "First, ingest 'q3_report.pdf'. Then, find any mentions of 'Project X' in the text. "
        "Finally, query Neo4j to see which employees are linked to 'Project X'."
    )

    query_generic_knowledge = "List all classic cocktails and please give me instruction to make top 3 of them"

    result = await agent.ainvoke({"messages": [("user", query_generic_knowledge)]})
    print(f"result = {result}")
    for message in result["messages"]:
        message.pretty_print()


if __name__ == "__main__":
    asyncio.run(main())
