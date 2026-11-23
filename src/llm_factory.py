from langchain_ollama import ChatOllama
from langchain_huggingface import HuggingFaceEmbeddings
from src.config import settings

def get_primary_llm() -> ChatOllama:
    """Returns the primary fast local LLM (e.g. Llama 3.1 8B)."""
    return ChatOllama(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.PRIMARY_LLM_MODEL,
        temperature=0.0,
        num_ctx=8192,
    )

def get_fallback_llm() -> ChatOllama:
    """Returns the specialized coding LLM used for self-correction (e.g. Qwen2.5-Coder or CodeLlama)."""
    return ChatOllama(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.FALLBACK_LLM_MODEL,
        temperature=0.0,
        num_ctx=8192,
    )

def get_synthesizer_llm() -> ChatOllama:
    """Returns the LLM for natural language response generation."""
    return ChatOllama(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.SYNTHESIZER_LLM_MODEL,
        temperature=0.2,
    )

def get_local_embeddings() -> HuggingFaceEmbeddings:
    """Returns HuggingFace embedding instance optimized for local Apple Silicon Metal / GPU execution."""
    return HuggingFaceEmbeddings(
        model_name=settings.EMBEDDING_MODEL_NAME,
        model_kwargs={"device": settings.EMBEDDING_DEVICE},
        encode_kwargs={"normalize_embeddings": True},
    )
