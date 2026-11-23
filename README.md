# Local Agentic SQL Analytics Gateway

A 100% privacy-preserving, local Agentic SQL Analytics Gateway powered by LangGraph, Ollama (Llama 3.1 & Qwen Coder), pgvector, and Chainlit.

## Quickstart with UV

1. **Install dependencies**:
   ```bash
   uv sync
   ```

2. **Start pgvector**:
   ```bash
   docker-compose up -d
   ```

3. **Pull local models**:
   ```bash
   ollama pull llama3.1:8b
   ollama pull qwen2.5-coder:7b
   ```

4. **Seed database schemas**:
   ```bash
   uv run python seed_schema.py
   ```

5. **Run Chainlit UI**:
   ```bash
   uv run chainlit run app.py -w
   ```
