import sqlparse
from typing import TypedDict, List, Dict, Any, Optional
from sqlalchemy import create_engine, text
from langgraph.graph import StateGraph, END
from langchain_core.prompts import PromptTemplate

from src.config import settings
from src.llm_factory import get_primary_llm, get_fallback_llm, get_synthesizer_llm
from src.vector_store import LocalVectorSchemaStore
from src.prompts import (
    SQL_GENERATOR_SYSTEM_PROMPT,
    SQL_FALLBACK_SYSTEM_PROMPT,
    SYNTHESIZER_SYSTEM_PROMPT,
    INTENT_CLASSIFIER_PROMPT,
    CONVERSATIONAL_SYSTEM_PROMPT
)
from src.parser import CleanSQLOutputParser

# 1. Define LangGraph Workflow State
class AgentState(TypedDict):
    user_question: str
    intent: str # "analytics" or "conversational"
    schema_context: str
    generated_sql: str
    is_valid: bool
    error_message: Optional[str]
    query_results: Optional[List[Dict[str, Any]]]
    final_answer: str
    retry_count: int
    used_model: str # "llama3.1:8b" or "gwen2.5-coder:7b" or "gemma2:2b"

# 2. Node Functions

def intent_classifier_node(state: AgentState) -> Dict[str, Any]:
    """Classifies user input as database analytics request vs casual conversational greeting."""
    llm = get_primary_llm()
    prompt = PromptTemplate.from_template(INTENT_CLASSIFIER_PROMPT)
    
    chain = prompt | llm
    result = chain.invoke({"user_question": state["user_question"]}).content.strip().lower()
    
    intent = "analytics" if "analytics" in result else "conversational"
    return {"intent": intent}

def conversational_node(state: AgentState) -> Dict[str, Any]:
    """Handles non-analytics inputs (greetings, general chat) without generating SQL."""
    llm = get_synthesizer_llm()
    prompt = PromptTemplate.from_template(CONVERSATIONAL_SYSTEM_PROMPT)
    
    chain = prompt | llm
    response = chain.invoke({"user_question": state["user_question"]})
    
    return {
        "final_answer": response.content,
        "generated_sql": "",
        "is_valid": True,
        "used_model": settings.SYNTHESIZER_LLM_MODEL
    }

def schema_retriever_node(state: AgentState) -> Dict[str, Any]:
    """Retrieves relevant table schemas using local pgvector embeddings."""
    try:
        vector_store = LocalVectorSchemaStore()
        schemas = vector_store.search_relevant_schemas(state["user_question"], limit=6)
        formatted_schema = "\n\n".join([
            f"--- Table: {s['table_name']} ---\nDescription: {s['business_description']}\n{s['schema_ddl']}"
            for s in schemas
        ])
    except Exception:
        formatted_schema = "Schema database unavailable or empty. Use standard ANSI SQL assumptions."
        
    return {"schema_context": formatted_schema}

def sql_generator_node(state: AgentState) -> Dict[str, Any]:
    """Generates candidate SQL using primary local LLM."""
    llm = get_primary_llm()
    parser = CleanSQLOutputParser()
    prompt = PromptTemplate.from_template(SQL_GENERATOR_SYSTEM_PROMPT)
    
    chain = prompt | llm | parser
    sql = chain.invoke({
        "schema_context": state["schema_context"],
        "user_question": state["user_question"]
    })
    
    return {
        "generated_sql": sql,
        "used_model": settings.PRIMARY_LLM_MODEL,
        "retry_count": state.get("retry_count", 0)
    }

def sql_validator_node(state: AgentState) -> Dict[str, Any]:
    """Validates SQL query syntax and guards against forbidden operations."""
    sql = state["generated_sql"]
    
    # Syntax Check with sqlparse
    parsed = sqlparse.parse(sql)
    if not parsed:
        return {"is_valid": False, "error_message": "Failed to parse SQL statement."}
    
    # Security Guardrail: Block destructive queries
    forbidden_keywords = ["DROP", "DELETE", "TRUNCATE", "ALTER", "GRANT", "REVOKE"]
    for kw in forbidden_keywords:
        if kw in sql.upper():
            return {"is_valid": False, "error_message": f"Security Violation: '{kw}' queries are restricted."}
            
    return {"is_valid": True, "error_message": None}

def fallback_generator_node(state: AgentState) -> Dict[str, Any]:
    """Fallback Node: Uses specialized coding model when primary generation fails."""
    llm = get_fallback_llm()
    parser = CleanSQLOutputParser()
    prompt = PromptTemplate.from_template(SQL_FALLBACK_SYSTEM_PROMPT)
    
    chain = prompt | llm | parser
    repaired_sql = chain.invoke({
        "schema_context": state["schema_context"],
        "failed_sql": state["generated_sql"],
        "error_message": state.get("error_message", "Unknown execution failure"),
        "user_question": state["user_question"]
    })
    
    current_retry = state.get("retry_count", 0) + 1
    return {
        "generated_sql": repaired_sql,
        "used_model": f"{settings.FALLBACK_LLM_MODEL} (Fallback Attempt {current_retry})",
        "retry_count": current_retry
    }

def sql_executor_node(state: AgentState) -> Dict[str, Any]:
    """Executes the validated SQL query against PostgreSQL database."""
    engine = create_engine(settings.DATABASE_URL)
    try:
        with engine.connect() as conn:
            result = conn.execute(text(state["generated_sql"]))
            columns = result.keys()
            rows = [dict(zip(columns, row)) for row in result.fetchall()]
            
        return {
            "query_results": rows,
            "is_valid": True,
            "error_message": None
        }
    except Exception as e:
        return {
            "is_valid": False,
            "error_message": f"PostgreSQL Execution Error: {str(e)}"
        }

def result_synthesizer_node(state: AgentState) -> Dict[str, Any]:
    """Converts structured SQL results into natural language answer."""
    llm = get_synthesizer_llm()
    prompt = PromptTemplate.from_template(SYNTHESIZER_SYSTEM_PROMPT)
    
    chain = prompt | llm
    response = chain.invoke({
        "user_question": state["user_question"],
        "sql_query": state["generated_sql"],
        "query_results": str(state.get("query_results", []))
    })
    
    return {"final_answer": response.content}

# 3. Conditional Routing Logic
def route_intent(state: AgentState) -> str:
    """Routes to schema retriever if analytics request, or directly to conversational response if chat."""
    if state.get("intent") == "analytics":
        return "schema_retriever"
    return "conversational"

def route_after_validation(state: AgentState) -> str:
    """Routes to Executor if valid, or Fallback if invalid and retries remain."""
    if state["is_valid"]:
        return "sql_executor"
    
    if state.get("retry_count", 0) < settings.MAX_SQL_RETRIES:
        return "fallback_generator"
    
    return "result_synthesizer"

def route_after_execution(state: AgentState) -> str:
    """Routes to Synthesizer if success, or Fallback if DB execution threw a runtime error."""
    if state["is_valid"]:
        return "result_synthesizer"
    
    if state.get("retry_count", 0) < settings.MAX_SQL_RETRIES:
        return "fallback_generator"
        
    return "result_synthesizer"

# 4. Construct LangGraph Workflow StateMachine
def build_agent_graph() -> StateGraph:
    workflow = StateGraph(AgentState)
    
    # Add Nodes
    workflow.add_node("intent_classifier", intent_classifier_node)
    workflow.add_node("conversational", conversational_node)
    workflow.add_node("schema_retriever", schema_retriever_node)
    workflow.add_node("sql_generator", sql_generator_node)
    workflow.add_node("sql_validator", sql_validator_node)
    workflow.add_node("fallback_generator", fallback_generator_node)
    workflow.add_node("sql_executor", sql_executor_node)
    workflow.add_node("result_synthesizer", result_synthesizer_node)
    
    # Set Entry Point
    workflow.set_entry_point("intent_classifier")
    
    # Intent Routing Conditional Edges
    workflow.add_conditional_edges(
        "intent_classifier",
        route_intent,
        {
            "schema_retriever": "schema_retriever",
            "conversational": "conversational"
        }
    )
    
    workflow.add_edge("conversational", END)
    
    # Direct Edges for Analytics Workflow
    workflow.add_edge("schema_retriever", "sql_generator")
    workflow.add_edge("sql_generator", "sql_validator")
    
    # Conditional Edges for Self-Correction & Fallback
    workflow.add_conditional_edges(
        "sql_validator",
        route_after_validation,
        {
            "sql_executor": "sql_executor",
            "fallback_generator": "fallback_generator",
            "result_synthesizer": "result_synthesizer"
        }
    )
    
    workflow.add_edge("fallback_generator", "sql_validator")
    
    workflow.add_conditional_edges(
        "sql_executor",
        route_after_execution,
        {
            "result_synthesizer": "result_synthesizer",
            "fallback_generator": "fallback_generator"
        }
    )
    
    workflow.add_edge("result_synthesizer", END)
    
    return workflow.compile()
