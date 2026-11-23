import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Application Config
    APP_NAME: str = "Local Agentic SQL Gateway"
    ENV: str = "development"
    DEBUG: bool = True
    
    # Ollama Configuration (Local Serving)
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    PRIMARY_LLM_MODEL: str = os.getenv("PRIMARY_LLM_MODEL", "qwen2.5-coder:3b")
    FALLBACK_LLM_MODEL: str = os.getenv("FALLBACK_LLM_MODEL", "gemma2:2b")
    SYNTHESIZER_LLM_MODEL: str = os.getenv("SYNTHESIZER_LLM_MODEL", "gemma2:2b")

    # Hugging Face Embeddings Configuration
    EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-m3")
    EMBEDDING_DEVICE: str = os.getenv("EMBEDDING_DEVICE", "mps") # 'mps' for Apple Silicon Metal, 'cuda' or 'cpu'
    
    # PostgreSQL & pgvector Connection
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5433"))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "analytics_db")
    
    # Agent Workflow Settings
    MAX_SQL_RETRIES: int = 3
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    @property
    def ASYNC_DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

settings = Settings()
