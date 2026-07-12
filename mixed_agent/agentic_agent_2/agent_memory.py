import os
import json
import redis
from pinecone import Pinecone
from google import genai
from google.genai import types

# ---------------------------------------------------------
# 1. INITIALIZATION & INFRASTRUCTURE CONFIGURATION
# ---------------------------------------------------------
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "your-gemini-key")
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY", "your-pinecone-key")

# Initialize Gemini Client
ai_client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_ID = "gemini-2.5-flash"

# Connect to Hot Tier (Redis)
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# Connect to Warm Tier (Pinecone)
pc = Pinecone(api_key=PINECONE_API_KEY)
# Assumes a pre-created index named 'agent-episodic-memory' with 768 dimensions (Gemini text-embedding-004)
vdb_index = pc.Index("agent-episodic-memory")

# ---------------------------------------------------------
# 2. CORE MEMORY FUNCTIONS
# ---------------------------------------------------------
def get_working_memory(session_id: str) -> list:
    """Hot Tier: Retrieves recent conversational turns from Redis (FIFO)."""
    raw_history = redis_client.lrange(f"session:{session_id}:history", 0, -1)
    # Return as structured objects reversed back to chronological order
    return [json.loads(turn) for turn in reversed(raw_history)]

def save_working_memory(session_id: str, role: str, message: str):
    """Hot Tier: Saves the current turn to Redis and truncates at 10 turns to save context."""
    turn_data = json.dumps({"role": role, "text": message})
    redis_key = f"session:{session_id}:history"
    redis_client.lpush(redis_key, turn_data)
    redis_client.ltrim(redis_key, 0, 9) # Keeps the latest 10 items in sliding window

def get_embedding(text: str) -> list:
    """Helper: Generates 768-dimension vector embedding via Gemini."""
    response = ai_client.models.embed_content(
        model="text-embedding-004",
        contents=text
    )
    return response.embeddings[0].values

def query_episodic_memory(user_query: str, session_id: str, top_k: int = 2) -> str:
    """Warm Tier: Fetches matching past historical logs from Pinecone."""
    query_vector = get_embedding(user_query)
    search_results = vdb_index.query(
        vector=query_vector,
        top_k=top_k,
        include_metadata=True,
        filter={"session_id": {"$eq": session_id}}
    )
    
    episodes = [match["metadata"]["text"] for match in search_results["matches"] if match["score"] > 0.70]
    if not episodes:
        return "No highly relevant past experiences found."
    return "\n".join(episodes)

def async_archive_episodic_memory(session_id: str, interaction_log: str):
    """Warm Tier Background Writer: Indexes complete interactions for long-term discovery."""
    vector = get_embedding(interaction_log)
    record_id = f"ep_{session_id}_{redis_client.incr('global:episode:counter')}"
    vdb_index.upsert(vectors=[{
        "id": record_id,
        "values": vector,
        "metadata": {"session_id": session_id, "text": interaction_log}
    }])

# ---------------------------------------------------------
# 3. PROCEDURAL MEMORY (TOOLS)
# ---------------------------------------------------------
def query_production_database(product_id: str) -> str:
    """Procedural Skill: Database query lookup function."""
    db_mock = {"PROD-99": "Status: Shipped. Carrier: DHL. Tracking: DHL12345."}
    return db_mock.get(product_id, "Error: Product Identifier ID not found.")

# Define tool schemas for Gemini native Function Calling execution
db_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="query_production_database",
            description="Queries the production database for shipping and tracking data using a product ID format 'PROD-XX'.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "product_id": types.Schema(type="STRING", description="The inventory product code.")
                },
                required=["product_id"]
            )
        )
    ]
)

# ---------------------------------------------------------
# 4. RE_ACT LOOP ORCHESTRATION ENGINE
# ---------------------------------------------------------
def run_agentic_system(session_id: str, user_prompt: str):
    print(f"\n🚀 Incoming User Prompt: '{user_prompt}'")
    
    # Tier 1 & 2 Context Assembly
    working_mem = get_working_memory(session_id)
    past_episodes = query_episodic_memory(user_prompt, session_id)
    
    # Inject system constraints and context
    system_instruction = (
        "You are an autonomous operations agent. You use internal tools to solve problems.\n"
        f"Relevant Historical Episodes:\n{past_episodes}\n"
        "Analyze instructions carefully, use available tools, and respond directly to the objective."
    )
    
    # Format current running chat sequence
    contents = []
    for turn in working_mem:
        contents.append(types.Content(role=turn["role"], parts=[types.Part.from_text(text=turn["text"])]))
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_prompt)]))
    
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=[db_tool],
        temperature=0.2 # Lower temperature guarantees structured ReAct consistency
    )
    
    # Execute the Engine Call
    response = ai_client.models.generate_content(
        model=MODEL_ID,
        contents=contents,
        config=config
    )
    
    # Native ReAct Loop Resolution Block
    if response.function_calls:
        for call in response.function_calls:
            if call.name == "query_production_database":
                # Execute tool tracking step
                args = call.args
                print(f"⚙️ [Action Executed]: Calling database tool with args: {args}")
                tool_output = query_production_database(args["product_id"])
                print(f"👁️ [Observation Target]: Found database result -> {tool_output}")
                
                # Feed observation directly back to the model to finalize the answer
                contents.append(response.candidates[0].content) # Append model tool request
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part.from_function_response(
                        name="query_production_database",
                        response={"result": tool_output}
                    )]
                ))
                
                final_response = ai_client.models.generate_content(
                    model=MODEL_ID, contents=contents, config=config
                )
                agent_output = final_response.text
    else:
        agent_output = response.text

    print(f"🤖 [Final Agent Answer]: {agent_output}")
    
    # Commit State Synchronization
    save_working_memory(session_id, "user", user_prompt)
    save_working_memory(session_id, "model", agent_output)
    
    # Async memory pipeline simulation (creates an episodic record)
    full_log = f"User asked: {user_prompt} | Agent diagnosed and answered: {agent_output}"
    async_archive_episodic_memory(session_id, full_log)

# ---------------------------------------------------------
# 5. EXECUTION EXAMPLE RUN
# ---------------------------------------------------------
if __name__ == "__main__":
    # Simulate an active support ticket run
    session_id_demo = "usr_session_1002"
    run_agentic_system(session_id_demo, "Where is my package PROD-99?")
