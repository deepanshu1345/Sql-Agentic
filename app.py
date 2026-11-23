import chainlit as cl
import json
import time
from decimal import Decimal
from datetime import date, datetime
from src.config import settings
from src.agent import build_agent_graph

# Compile LangGraph Workflow StateMachine
agent_graph = build_agent_graph()

def json_serializer(obj):
    """Custom serializer for PostgreSQL Decimal, date, and datetime objects."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    return str(obj)

@cl.on_chat_start
async def on_chat_start():
    """Initializes session state and displays welcome banner with local model details."""
    cl.user_session.set("graph", agent_graph)
    
    welcome_content = f"""
### ⚡ Local Agentic SQL Analytics Gateway

Welcome! This system executes natural language analytics queries entirely on your local machine.

- **Primary Model**: `{settings.PRIMARY_LLM_MODEL}` (Ollama / Metal GPU)
- **Fallback Coder Model**: `{settings.FALLBACK_LLM_MODEL}` (Auto Self-Correction)
- **Vector Index**: `{settings.EMBEDDING_MODEL_NAME}` + `pgvector`

*Ask any analytical question about your database or say hi to get started!*
"""
    await cl.Message(content=welcome_content).send()

@cl.on_message
async def on_message(message: cl.Message):
    """Processes user questions through LangGraph with real-time Chainlit Step Tracing."""
    graph = cl.user_session.get("graph")
    
    initial_state = {
        "user_question": message.content,
        "intent": "analytics",
        "schema_context": "",
        "generated_sql": "",
        "is_valid": False,
        "error_message": None,
        "query_results": None,
        "final_answer": "",
        "retry_count": 0,
        "used_model": settings.PRIMARY_LLM_MODEL
    }
    
    # Root message container for streaming status
    response_msg = cl.Message(content="")
    await response_msg.send()
    
    start_time = time.time()
    final_state = initial_state
    
    # Stream LangGraph Node Execution in Chainlit Steps
    async for event in graph.astream(initial_state):
        for node_name, state_update in event.items():
            final_state.update(state_update)
            
            if node_name == "intent_classifier":
                async with cl.Step(name="🎯 Intent Classifier") as step:
                    detected = state_update.get("intent", "analytics")
                    step.output = f"Detected Intent: `{detected.upper()}`"
                    
            elif node_name == "conversational":
                response_msg.content = state_update.get("final_answer", "")
                
            elif node_name == "schema_retriever":
                async with cl.Step(name="🔍 Schema Retriever (pgvector)") as step:
                    step.output = f"Retrieved Schema Context:\n```text\n{state_update.get('schema_context', 'None')}\n```"
                    
            elif node_name == "sql_generator":
                async with cl.Step(name=f"⚡ SQL Generator ({settings.PRIMARY_LLM_MODEL})") as step:
                    sql_code = state_update.get("generated_sql", "")
                    step.output = f"Generated SQL:\n```sql\n{sql_code}\n```"
                    
            elif node_name == "sql_validator":
                is_valid = state_update.get("is_valid", False)
                err = state_update.get("error_message")
                async with cl.Step(name="🛡️ SQL Validator & Guardrails") as step:
                    if is_valid:
                        step.output = "✅ SQL Syntax and Security Validation Passed."
                    else:
                        step.output = f"❌ Validation Failed: {err}"
                        
            elif node_name == "fallback_generator":
                retry_num = state_update.get("retry_count", 1)
                async with cl.Step(name=f"🛠️ Fallback Self-Correction ({settings.FALLBACK_LLM_MODEL} - Attempt {retry_num})") as step:
                    repaired_sql = state_update.get("generated_sql", "")
                    step.output = f"Repaired SQL Query:\n```sql\n{repaired_sql}\n```"
                    
            elif node_name == "sql_executor":
                async with cl.Step(name="📊 SQL Database Execution") as step:
                    results = state_update.get("query_results")
                    if results is not None:
                        formatted_json = json.dumps(results[:5], indent=2, default=json_serializer)
                        step.output = f"Returned {len(results)} rows.\n```json\n{formatted_json}\n```"
                    else:
                        step.output = f"Execution Error: {state_update.get('error_message')}"
                        
            elif node_name == "result_synthesizer":
                response_msg.content = state_update.get("final_answer", "")

    elapsed = round(time.time() - start_time, 2)
    
    # Attach SQL Query and Execution Metadata Summary (only if SQL was executed)
    final_sql = final_state.get("generated_sql", "")
    if final_sql:
        used_model = final_state.get("used_model", settings.PRIMARY_LLM_MODEL)
        retry_count = final_state.get("retry_count", 0)
        
        metadata_summary = f"\n\n---\n**Execution Summary:**\n" \
                           f"- **Model Used**: `{used_model}`\n" \
                           f"- **Self-Correction Retries**: `{retry_count}`\n" \
                           f"- **Total Latency**: `{elapsed}s`\n" \
                           f"```sql\n{final_sql}\n```"
                           
        response_msg.content += metadata_summary

    await response_msg.update()
