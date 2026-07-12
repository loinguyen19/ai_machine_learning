import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic

async def main():
    async with MultiServerMCPClient({
        "advanced_explorer": {
            "command": "python",
            "args": ["server.py"],
            "transport": "stdio"
        }
    }) as client:
        
        tools = await client.get_tools()
        llm = ChatOpenAI(model="gpt-4o", temperature=0) # Low temperature for factual RAG
        
        # This agent uses the ReAct (Reasoning + Acting) loop
        agent = create_agent(llm, tools, agent_type="react")
        
        # AGENTIC RAG EXECUTION: 
        # The agent must first ingest, then search, then check the graph.
        query = (
            "First, ingest 'q3_report.pdf'. Then, find any mentions of 'Project X' in the text. "
            "Finally, query Neo4j to see which employees are linked to 'Project X'."
        )
        
        result = await agent.ainvoke({"messages": [("user", query)]})
        
        for message in result["messages"]:
            message.pretty_print()

if __name__ == "__main__":
    asyncio.run(main())
