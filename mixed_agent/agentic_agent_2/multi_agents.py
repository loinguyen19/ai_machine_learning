import os
import json
import redis
from google import genai
from google.genai import types

# ---------------------------------------------------------
# 1. INFRASTRUCTURE & STATE STORAGE INITIALIZATION
# ---------------------------------------------------------
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "your-gemini-key")
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))

# Initialize the official Gemini Client
ai_client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_ID = "gemini-2.5-flash"

try:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    redis_client.ping()
except Exception:
    print("⚠️ Local Redis unavailable. Falling back to an in-memory dictionary storage.")
    class MockRedis:
        def __init__(self): self.db = {}
        def hset(self, name, key, val): self.db[f"{name}:{key}"] = val
        def hget(self, name, key): return self.db.get(f"{name}:{key}", None)
    redis_client = MockRedis()

# ---------------------------------------------------------
# 2. SHARED STATE MANAGEMENT FUNCTIONS
# ---------------------------------------------------------
def save_agent_session_state(session_id: str, state_payload: dict):
    """Saves the current multi-agent execution step to the Hot Tier store."""
    redis_client.hset(f"session:{session_id}", "state", json.dumps(state_payload))

def get_agent_session_state(session_id: str) -> dict:
    """Retrieves the system state so the next agent can resume work seamlessly."""
    raw_data = redis_client.hget(f"session:{session_id}", "state")
    if not raw_data:
        return {"current_stage": "research", "shared_context": {}, "history": []}
    return json.loads(raw_data)

# ---------------------------------------------------------
# 3. AGENT TOOL DEFINITIONS (PROCEDURAL SKILLS)
# ---------------------------------------------------------
def search_knowledge_base(query: str) -> str:
    """Mock API tool simulating real-world retrieval operations."""
    if "agentic ai" in query.lower():
        return "Agentic AI refers to autonomous loops like ReAct. Market adoption is expected to hit 70% by 2026."
    return "Generic trend: Automation frameworks show continuous compound quarterly growth."

search_tool_schema = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="search_knowledge_base",
            description="Searches internal industry databases for technical parameters and growth statistics.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "query": types.Schema(type="STRING", description="Target industry term or technological topic.")
                },
                required=["query"]
            )
        )
    ]
)

# ---------------------------------------------------------
# 4. MULTI-AGENT EXECUTION BLOCK
# ---------------------------------------------------------
def run_researcher_agent(session_id: str, prompt: str) -> dict:
    """Agent 1: Uses tools to gather technical context, then updates the shared state."""
    print("🔍 [Researcher Agent]: Commencing objective discovery...")
    state = get_agent_session_state(session_id)
    
    sys_instruction = "You are an analytical researcher. Find core facts using your search tool."
    config = types.GenerateContentConfig(
        system_instruction=sys_instruction,
        tools=[search_tool_schema],
        temperature=0.1
    )
    
    # Initial reasoning turn
    response = ai_client.models.generate_content(
        model=MODEL_ID, contents=f"Extract data regarding: {prompt}", config=config
    )
    
    # ReAct Execution Loop
    if response.function_calls:
        for call in response.function_calls:
            if call.name == "search_knowledge_base":
                args = call.args
                print(f"⚙️ [Researcher Action]: Tool Call -> {call.name} with {args}")
                observation = search_knowledge_base(args["query"])
                print(f"👁️ [Researcher Observation]: {observation}")
                
                # Close out loop with tool result injection
                follow_up_contents = [
                    types.Content(role="user", parts=[types.Part.from_text(text=prompt)]),
                    response.candidates.content,
                    types.Content(role="user", parts=[types.Part.from_function_response(
                        name="search_knowledge_base", response={"result": observation}
                    )])
                ]
                final_res = ai_client.models.generate_content(
                    model=MODEL_ID, contents=follow_up_contents, config=config
                )
                research_notes = final_res.text
    else:
        research_notes = response.text

    # Hand-off preparation
    state["current_stage"] = "writing"
    state["shared_context"]["research_data"] = research_notes
    state["history"].append("Researcher agent successfully aggregated data points.")
    save_agent_session_state(session_id, state)
    print("✅ [Researcher Agent]: Complete. Handing off state to Writer.")
    return state

def run_writer_agent(session_id: str) -> str:
    """Agent 2: Reads shared state created by Agent 1 and builds consumer-facing prose."""
    print("✍️ [Writer Agent]: Evaluating research state files...")
    state = get_agent_session_state(session_id)
    
    if "research_data" not in state["shared_context"]:
        raise ValueError("Pipeline breakdown: No historical data present in the shared state.")
        
    extracted_context = state["shared_context"]["research_data"]
    sys_instruction = "You are a professional copywriter. Transform technical raw data into bulleted summaries."
    
    prompt = f"Convert these technical findings into a concise, readable summary:\n\n{extracted_context}"
    
    response = ai_client.models.generate_content(
        model=MODEL_ID,
        contents=prompt,
        config=types.GenerateContentConfig(system_instruction=sys_instruction, temperature=0.7)
    )
    
    # Final state updates
    state["current_stage"] = "completed"
    state["history"].append("Writer agent successfully drafted the brief.")
    save_agent_session_state(session_id, state)
    return response.text

# ---------------------------------------------------------
# 5. ORCHESTRATION PIPELINE CONTROL RUN
# ---------------------------------------------------------
def pipeline_orchestrator(user_prompt: str):
    session_id = "multi_agent_session_2026"
    print(f"User Request: {user_prompt}\n" + "="*50)
    
    # Step 1: Fire Researcher Agent
    current_state = run_researcher_agent(session_id, user_prompt)
    
    # Step 2: Route dynamically based on status properties
    if current_state["current_stage"] == "writing":
        final_brief = run_writer_agent(session_id)
        print("\n🏆 [Final Output Delivered]:")
        print(final_brief)

if __name__ == "__main__":
    pipeline_orchestrator("What is the current industry status of Agentic AI?")
