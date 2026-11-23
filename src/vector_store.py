from typing import List, Dict, Any
from sqlalchemy import create_engine, text
from src.config import settings
from src.llm_factory import get_local_embeddings

class LocalVectorSchemaStore:
    def __init__(self):
        self.embeddings = get_local_embeddings()
        self.engine = create_engine(settings.DATABASE_URL)
        self._init_vector_extension()
        
    def _init_vector_extension(self):
        """Ensure vector extension and schema metadata table exist."""
        with self.engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS schema_embeddings (
                    id SERIAL PRIMARY KEY,
                    table_name VARCHAR(100) UNIQUE NOT NULL,
                    schema_ddl TEXT NOT NULL,
                    business_description TEXT NOT NULL,
                    embedding vector(1024)
                );
            """))
            
    def index_table_schema(self, table_name: str, schema_ddl: str, description: str):
        """Indexes table schema DDL and business descriptions into pgvector."""
        content = f"Table: {table_name}\nDescription: {description}\nSchema:\n{schema_ddl}"
        vector = self.embeddings.embed_query(content)
        
        query = text("""
            INSERT INTO schema_embeddings (table_name, schema_ddl, business_description, embedding)
            VALUES (:table, :ddl, :desc, :vector)
            ON CONFLICT (table_name) 
            DO UPDATE SET schema_ddl = :ddl, business_description = :desc, embedding = :vector;
        """)
        
        with self.engine.begin() as conn:
            conn.execute(query, {
                "table": table_name,
                "ddl": schema_ddl,
                "desc": description,
                "vector": str(vector)
            })

    def get_dynamic_column_samples(self, table_name: str) -> str:
        """Dynamically inspects the live database for string/enum columns and extracts distinct sample values."""
        try:
            with self.engine.connect() as conn:
                cols_query = text("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = :table_name 
                      AND data_type IN ('character varying', 'text', 'character', 'USER-DEFINED');
                """)
                cols = conn.execute(cols_query, {"table_name": table_name}).fetchall()
                
                samples = []
                for col_name, data_type in cols:
                    sample_query = text(f'SELECT DISTINCT "{col_name}" FROM "{table_name}" WHERE "{col_name}" IS NOT NULL LIMIT 5;')
                    vals = [str(r[0]) for r in conn.execute(sample_query).fetchall()]
                    if vals:
                        samples.append(f"  * Column '{col_name}' sample values: {vals}")
                
                if samples:
                    return "\nDynamically Sampled Live Column Values:\n" + "\n".join(samples)
        except Exception:
            pass
        return ""

    def search_relevant_schemas(self, query: str, limit: int = 6) -> List[Dict[str, Any]]:
        """Retrieves top-k relevant database schemas dynamically enriched with live column sample values."""
        query_vector = self.embeddings.embed_query(query)
        
        sql = text("""
            SELECT table_name, schema_ddl, business_description,
                   1 - (embedding <=> :query_vector) AS similarity
            FROM schema_embeddings
            ORDER BY embedding <=> :query_vector
            LIMIT :limit;
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(sql, {"query_vector": str(query_vector), "limit": limit})
            schemas = []
            for row in result:
                dynamic_samples = self.get_dynamic_column_samples(row.table_name)
                full_ddl = f"{row.schema_ddl}\n{dynamic_samples}" if dynamic_samples else row.schema_ddl
                schemas.append({
                    "table_name": row.table_name,
                    "schema_ddl": full_ddl,
                    "business_description": row.business_description,
                    "similarity": float(row.similarity)
                })
            return schemas

