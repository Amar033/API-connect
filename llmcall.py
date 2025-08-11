import re
from typing import List, Dict, Optional
from models import ExternalDBCredential
from getschemas import get_user_database_schemas, format_schema_for_llm, get_external_db_connection
import requests
import os


def query_model(prompt, model="openai/gpt-oss-20b", url="https://openrouter.ai/api/v1/chat/completions"):
    """Query the OpenRouter GPT-OSS-20B model"""
    try:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("Missing OPENROUTER_API_KEY environment variable")

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are an expert SQL query generator."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0,
            "max_tokens": 1024
        }

        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        return data["choices"][0]["message"]["content"].strip()

    except Exception as e:
        return f"Error querying OpenRouter: {str(e)}"


def clean_sql_query(sql_query: str, target_db: str) -> str:
    """Clean and validate SQL query from LLM response, remove db prefixes"""
    if not sql_query:
        return ""

    cleaned = sql_query.strip()
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = re.sub(r'```sql\n?', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'```\n?', '', cleaned, flags=re.IGNORECASE)

    # Extract actual SQL (first matching main SQL pattern)
    sql_patterns = [
        r'(SELECT\s+.*?;)',
        r'(INSERT\s+.*?;)',
        r'(UPDATE\s+.*?;)',
        r'(DELETE\s+.*?;)',
        r'(WITH\s+.*?;)',
        r'(CREATE\s+.*?;)',
        r'(DROP\s+.*?;)',
        r'(ALTER\s+.*?;)'
    ]
    for pattern in sql_patterns:
        match = re.search(pattern, cleaned, re.IGNORECASE | re.DOTALL)
        if match:
            cleaned = match.group(1)
            break

    # Remove DB prefix if it matches target_db
    db_prefix_pattern = rf'\b{re.escape(target_db)}\.'  # e.g. railway.
    cleaned = re.sub(db_prefix_pattern, '', cleaned, flags=re.IGNORECASE)

    cleaned = cleaned.rstrip(';').strip() + ';'
    return cleaned


def extract_database_preference(user_input: str, available_dbs: List[str]) -> Optional[str]:
    """Guess which DB to use based on input"""
    user_input_lower = user_input.lower()
    for db_name in available_dbs:
        if db_name.lower() in user_input_lower:
            return db_name
    if any(word in user_input_lower for word in ['customer', 'client', 'user']):
        matches = [db for db in available_dbs if any(
            kw in db.lower() for kw in ['customer', 'client', 'user', 'crm']
        )]
        if matches:
            return matches[0]
    return None


def build_enhanced_prompt(user_input: str, schema_info: str, available_databases: List[str], preferred_db: Optional[str] = None) -> str:
    """Builds a context-rich prompt for LLM"""
    prompt = f"""You are an expert SQL query generator with access to multiple PostgreSQL databases.

USER QUESTION: "{user_input}"

{schema_info}

INSTRUCTIONS:
1. Choose the most relevant database.
2. DO NOT prefix table names with the database name (e.g., use "teacher" not "railway.teacher").
3. Use proper JOINs for multiple tables but not in all queries.
4. Use ILIKE with % for partial matches.
5. Add LIMIT for large results.
6. Only output SQL, no explanations.

DATABASES:
"""
    if preferred_db:
        prompt += f"- Focus on '{preferred_db}' database.\n"
    else:
        prompt += f"- Available: {', '.join(available_databases)}\n"

    prompt += "Generate ONLY the SQL query:"
    return prompt


def generate_sql_response(user_input: str, user_db_credentials: List[ExternalDBCredential], preferred_db_name: Optional[str] = None) -> Dict[str, str]:
    """Generate SQL query for user"""
    if not user_input.strip():
        return {"error": "User input cannot be empty", "sql": "", "database": ""}

    if not user_db_credentials:
        return {"error": "No database connections", "sql": "", "database": ""}

    try:
        user_schemas = get_user_database_schemas(user_db_credentials)
        if not user_schemas:
            return {"error": "No accessible databases", "sql": "", "database": ""}

        formatted_schema = format_schema_for_llm(user_schemas)
        available_dbs = list(user_schemas.keys())

        if not preferred_db_name:
            preferred_db_name = extract_database_preference(user_input, available_dbs)
        if not preferred_db_name:
            preferred_db_name = available_dbs[0]  # default

        prompt = build_enhanced_prompt(user_input, formatted_schema, available_dbs, preferred_db_name)
        raw_sql = query_model(prompt)
        clean_sql = clean_sql_query(raw_sql, preferred_db_name)

        return {
            "sql": clean_sql,
            "database": preferred_db_name,
            "error": "",
            "available_databases": available_dbs
        }

    except Exception as e:
        return {"error": f"Error generating SQL: {str(e)}", "sql": "", "database": ""}


def execute_sql_query(sql_query: str, db_credential: ExternalDBCredential, limit: int = 100) -> Dict:
    """Run SQL query"""
    conn = None
    try:
        conn = get_external_db_connection(db_credential)
        if not conn:
            return {"error": "Failed to connect to database", "data": []}

        with conn.cursor() as cur:
            if sql_query.strip().upper().startswith('SELECT') and 'LIMIT' not in sql_query.upper():
                sql_query = sql_query.rstrip(';') + f' LIMIT {limit};'
            cur.execute(sql_query)

            if sql_query.strip().upper().startswith('SELECT'):
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
                return {"data": [dict(zip(columns, row)) for row in rows], "columns": columns, "row_count": len(rows), "error": ""}
            else:
                conn.commit()
                return {"data": [], "affected_rows": cur.rowcount, "error": ""}

    except Exception as e:
        return {"error": f"Query execution error: {str(e)}", "data": []}

    finally:
        if conn:
            conn.close()
