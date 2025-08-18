import re
from typing import List, Dict, Optional
from models import ExternalDBCredential
from getschemas import get_user_database_schemas, format_schema_for_llm, get_external_db_connection
import requests
import os
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# === Simple in-memory context store ===
# key = user_id, value = list of recent conversation turns
USER_CONTEXT: Dict[str, List[Dict[str, str]]] = {}
CONTEXT_EXPIRY_MINUTES = 10  # context expires after inactivity

from functools import lru_cache
import time

# Simple in-memory cache structure
_llm_cache = {}  # { (user_id, question.lower().strip()): (timestamp, response) }
CACHE_TTL = 3600  # seconds (1 hour)

def get_cached_response(user_id: int, question: str):
    key = (user_id, question.lower().strip())
    entry = _llm_cache.get(key)
    if entry:
        timestamp, response = entry
        if time.time() - timestamp < CACHE_TTL:
            return response
        else:
            del _llm_cache[key]  # expired
    return None

def set_cached_response(user_id: int, question: str, response):
    key = (user_id, question.lower().strip())
    _llm_cache[key] = (time.time(), response)


def _clean_expired_context():
    """Remove context for inactive users"""
    now = datetime.utcnow()
    expired_users = []
    for user_id, messages in USER_CONTEXT.items():
        if messages and 'timestamp' in messages[-1]:
            last_time = messages[-1]['timestamp']
            if (now - last_time).total_seconds() > CONTEXT_EXPIRY_MINUTES * 60:
                expired_users.append(user_id)
    for uid in expired_users:
        del USER_CONTEXT[uid]

# 
def _add_to_context(user_id: str, role: str, content: str):
    """Append message to user's context"""
    _clean_expired_context()
    if user_id not in USER_CONTEXT:
        USER_CONTEXT[user_id] = []
    USER_CONTEXT[user_id].append({
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow()
    })
    # Keep only last 10 turns
    USER_CONTEXT[user_id] = USER_CONTEXT[user_id][-10:]

def _get_context_messages(user_id: str) -> List[Dict[str, str]]:
    """Get recent conversation messages without timestamps"""
    _clean_expired_context()
    if user_id not in USER_CONTEXT:
        return []
    return [{"role": m["role"], "content": m["content"]} for m in USER_CONTEXT[user_id]]


def query_model(user_id: str, prompt: str, model="openai/gpt-oss-20b:free", url="https://openrouter.ai/api/v1/chat/completions"):
    """Query the LLM with conversation context"""
    try:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("Missing OPENROUTER_API_KEY environment variable")

        # Build message history
        # Retrieve context from the in-memory store
        history = _get_context_messages(user_id)
        history.append({"role": "user", "content": prompt})

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are an expert SQL query generator. Keep track of user context to interpret follow-up queries correctly."}
            ] + history,
            "temperature": 0,
            "max_tokens": 1024
        }

        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        answer = data["choices"][0]["message"]["content"].strip()

        # Store both user input & LLM output for context
        _add_to_context(user_id, "user", prompt)
        _add_to_context(user_id, "assistant", answer)

        return answer

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

    db_prefix_pattern = rf'\b{re.escape(target_db)}\.'
    cleaned = re.sub(db_prefix_pattern, '', cleaned, flags=re.IGNORECASE)

    cleaned = cleaned.rstrip(';').strip() + ';'
    return cleaned


def extract_database_preference(user_input: str, available_dbs: List[str]) -> Optional[str]:
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


def build_enhanced_prompt(user_id: str, user_input: str, schema_info: str, available_databases: List[str], preferred_db: Optional[str] = None) -> str:
    # Retrieve conversation context for the prompt
    context_history = _get_context_messages(user_id)
    formatted_context = "\n".join([f"{m['role']}: {m['content']}" for m in context_history])
    
    prompt = f"""You are an expert SQL query generator with access to multiple PostgreSQL databases.
The conversation may include follow-up questions referring to previous results.

CONVERSATION HISTORY:
---
{formatted_context}
---

USER QUESTION: "{user_input}"

{schema_info}

INSTRUCTIONS:
1. Use context from earlier conversation to resolve ambiguous references (e.g., "him", "that record").
2. Choose the most relevant database.
3. DO NOT prefix table names with the database name.
4. Use proper JOINs when needed.
5. Use ILIKE with % for partial matches.
6. Add LIMIT for large results.
7. Only output SQL.
8. For string comparison use LOWER() or UPPER() function to ensure case insensitivity.

DATABASES:
"""
    if preferred_db:
        prompt += f"- Focus on '{preferred_db}' database.\n"
    else:
        prompt += f"- Available: {', '.join(available_databases)}\n"

    prompt += "Generate ONLY the SQL query:"
    return prompt


def generate_sql_response(user_id: str, user_input: str, user_db_credentials: List[ExternalDBCredential], preferred_db_name: Optional[str] = None) -> Dict[str, str]:
    if not user_input.strip():
        return {"error": "User input cannot be empty", "sql": "", "database": ""}

    if not user_db_credentials:
        return {"error": "No database connections", "sql": "", "database": ""}

    try:
        cached = get_cached_response(user_id, user_input)
        if cached:
            return cached 
        user_schemas = get_user_database_schemas(user_db_credentials)
        if not user_schemas:
            return {"error": "No accessible databases", "sql": "", "database": ""}

        formatted_schema = format_schema_for_llm(user_schemas)
        available_dbs = list(user_schemas.keys())

        if not preferred_db_name:
            preferred_db_name = extract_database_preference(user_input, available_dbs)
        if not preferred_db_name:
            preferred_db_name = available_dbs[0]

        # Use the modified build_enhanced_prompt function to include conversation context
        prompt = build_enhanced_prompt(user_id, user_input, formatted_schema, available_dbs, preferred_db_name)
        raw_sql = query_model(user_id, prompt)
        clean_sql = clean_sql_query(raw_sql, preferred_db_name)
        
        # This part of the code is responsible for setting the cache
        # The key for the cache is a tuple of user_id and the question
        set_cached_response(user_id, user_input, {
            "sql": clean_sql,
            "database": preferred_db_name,
            "error": "",
            "available_databases": available_dbs
        })

        return {
            "sql": clean_sql,
            "database": preferred_db_name,
            "error": "",
            "available_databases": available_dbs
        }

    except Exception as e:
        return {"error": f"Error generating SQL: {str(e)}", "sql": "", "database": ""}


def execute_sql_query(sql_query: str, db_credential: ExternalDBCredential, limit: int = 100) -> Dict:
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
                # You might need to handle Decimal objects here if they're not handled by the database driver
                return {"data": [dict(zip(columns, row)) for row in rows], "columns": columns, "row_count": len(rows), "error": ""}
            else:
                conn.commit()
                return {"data": [], "affected_rows": cur.rowcount, "error": ""}

    except Exception as e:
        return {"error": f"Query execution error: {str(e)}", "data": []}

    finally:
        if conn:
            conn.close()