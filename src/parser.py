import re
from langchain_core.output_parsers import BaseOutputParser

class CleanSQLOutputParser(BaseOutputParser[str]):
    """Strict parser for local LLMs (Llama 3.1) to extract pure SQL queries."""

    def parse(self, text: str) -> str:
        clean_text = text.strip()
        
        # 1. Remove markdown code fences if present
        markdown_match = re.search(r'```(?:sql)?\s*(.*?)\s*```', clean_text, re.DOTALL | re.IGNORECASE)
        if markdown_match:
            clean_text = markdown_match.group(1).strip()
            
        # 2. Remove common preamble text from local LLMs
        clean_text = re.sub(r'^(Here is the SQL query|The SQL query is|Query:|SELECT)', r'\1', clean_text, flags=re.IGNORECASE)
        
        # 3. If preamble still exists before SELECT/WITH, strip it
        select_match = re.search(r'\b(SELECT|WITH|INSERT|UPDATE|DELETE)\b.*', clean_text, re.DOTALL | re.IGNORECASE)
        if select_match:
            clean_text = select_match.group(0).strip()
            
        # 4. Remove trailing semicolons or markdown artifacts
        clean_text = clean_text.rstrip(';`') + ';'
        
        return clean_text
