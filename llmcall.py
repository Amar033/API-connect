import re
from typing import List, Dict, Optional
from models import ExternalDBCredential
from getschemas import get_user_database_schemas, format_schema_for_llm, get_external_db_connection, get_sample_data
import requests
import json
import os


def query_model(
    prompt,
    model="openai/gpt-oss-20b",  # OpenRouter model name
    url="https://openrouter.ai/api/v1/chat/completions"
):
    """Query the OpenRouter GPT-OSS-20B model"""
    try:
        api_key = os.getenv("OPENROUTER_API_KEY")  # Store API key in env
        if not api_key:
            raise ValueError("Missing OPENROUTER_API_KEY environment variable")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

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


def clean_sql_query(sql_query: str) -> str:
    """Clean and validate SQL query from LLM response"""
    if not sql_query:
        return ""
    
    # Remove extra whitespace, newlines, and tabs
    cleaned = sql_query.strip()
    
    # Replace multiple whitespaces and newlines with single spaces
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # Remove any markdown code block markers
    cleaned = re.sub(r'```sql\n?', '', cleaned)
    cleaned = re.sub(r'```\n?', '', cleaned)
    
    # Remove any explanatory text that might come before or after the SQL
    # Look for SELECT, INSERT, UPDATE, DELETE statements
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
    
    # Remove trailing semicolon if present (we'll add it back)
    cleaned = cleaned.rstrip(';').strip()
    
    # Ensure single semicolon at the end
    cleaned = cleaned + ';'
    
    return cleaned

def extract_database_preference(user_input: str, available_dbs: List[str]) -> Optional[str]:
    """Try to extract which database the user might be referring to"""
    user_input_lower = user_input.lower()
    
    for db_name in available_dbs:
        if db_name.lower() in user_input_lower:
            return db_name
    
    # Look for keywords that might indicate database preference
    if any(word in user_input_lower for word in ['customer', 'client', 'user']):
        # Prefer databases that might contain customer data
        customer_dbs = [db for db in available_dbs if any(
            keyword in db.lower() for keyword in ['customer', 'client', 'user', 'crm']
        )]
        if customer_dbs:
            return customer_dbs[0]
    
    return None

def build_enhanced_prompt(
    user_input: str, 
    schema_info: str, 
    available_databases: List[str],
    preferred_db: Optional[str] = None
) -> str:
    """Build an enhanced prompt for the LLM with better context"""
    
    prompt = f"""You are an expert SQL query generator with access to multiple databases.

USER QUESTION: "{user_input}"

{schema_info}

INSTRUCTIONS:
1. Generate a SQL query that answers the user's question accurately
2. Use proper JOIN operations when querying multiple tables
3. Use LIKE operations with wildcards (%) for text searches when exact matches might not exist
4. Include relevant WHERE conditions to filter results appropriately
5. Use LIMIT when appropriate to avoid overwhelming results
6. If the user's question is ambiguous, make reasonable assumptions based on available tables

SEARCH STRATEGY:
- For name/text searches, use ILIKE '%search_term%' (case-insensitive partial matching)
- For exact matches, use = operator
- For date ranges, use BETWEEN or >= / <= operators
- For multiple conditions, use AND/OR appropriately

DATABASE SELECTION:
"""
    
    if preferred_db:
        prompt += f"- Focus primarily on the '{preferred_db}' database\n"
    else:
        prompt += f"- Available databases: {', '.join(available_databases)}\n"
        prompt += "- Choose the most appropriate database based on the user's question\n"
    
    prompt += """
OUTPUT REQUIREMENTS:
- Return ONLY the SQL query, no explanations or comments
- Ensure the query is syntactically correct
- Use standard PostgreSQL syntax
- Include appropriate table prefixes when using JOINs

EXAMPLE PATTERNS:
- For "find customers named John": SELECT * FROM customers WHERE name ILIKE '%john%';
- For "sales in 2023": SELECT * FROM sales WHERE date_created >= '2023-01-01' AND date_created < '2024-01-01';
- For "top 10 products": SELECT * FROM products ORDER BY some_metric DESC LIMIT 10;

Generate the SQL query now:"""

    return prompt

def generate_sql_response(
    user_input: str, 
    user_db_credentials: List[ExternalDBCredential],
    preferred_db_name: Optional[str] = None
) -> Dict[str, str]:
    """
    Generate SQL response based on user input and their available databases
    
    Args:
        user_input: The user's natural language query
        user_db_credentials: List of user's database connections
        preferred_db_name: Optional preferred database name
    
    Returns:
        Dict with 'sql', 'database', 'error' keys
    """
    if not user_input or not user_input.strip():
        return {"error": "User input cannot be empty", "sql": "", "database": ""}
    
    if not user_db_credentials:
        return {"error": "No database connections available", "sql": "", "database": ""}
    
    try:
        # Get schemas for all user databases
        user_schemas = get_user_database_schemas(user_db_credentials)
        
        if not user_schemas:
            return {"error": "No accessible databases found", "sql": "", "database": ""}
        
        # Format schema for LLM
        formatted_schema = format_schema_for_llm(user_schemas)
        
        # Get list of available database names
        available_dbs = list(user_schemas.keys())
        
        # Try to determine preferred database
        if not preferred_db_name:
            preferred_db_name = extract_database_preference(user_input, available_dbs)
        
        # Build enhanced prompt
        prompt = build_enhanced_prompt(
            user_input, 
            formatted_schema, 
            available_dbs,
            preferred_db_name
        )
        
        # Query the model
        raw_sql = query_model(prompt=prompt)
        clean_sql = clean_sql_query(raw_sql)
        
        # Determine which database to use
        target_database = preferred_db_name or available_dbs[0]
        
        return {
            "sql": clean_sql,
            "database": target_database,
            "error": "",
            "available_databases": available_dbs
        }
        
    except Exception as e:
        return {"error": f"Error generating SQL: {str(e)}", "sql": "", "database": ""}

def execute_sql_query(
    sql_query: str,
    db_credential: ExternalDBCredential,
    limit: int = 100
) -> Dict:
    """Execute SQL query on the specified database"""
    try:
        conn = get_external_db_connection(db_credential)
        if not conn:
            return {"error": "Failed to connect to database", "data": []}
        
        with conn.cursor() as cur:
            # Add LIMIT if not already present in SELECT queries
            if sql_query.strip().upper().startswith('SELECT') and 'LIMIT' not in sql_query.upper():
                sql_query = sql_query.rstrip(';') + f' LIMIT {limit};'
            
            cur.execute(sql_query)
            
            # For SELECT queries, fetch results
            if sql_query.strip().upper().startswith('SELECT'):
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
                
                return {
                    "data": [dict(zip(columns, row)) for row in rows],
                    "columns": columns,
                    "row_count": len(rows),
                    "error": ""
                }
            else:
                # For non-SELECT queries, return affected rows
                conn.commit()
                return {
                    "data": [],
                    "affected_rows": cur.rowcount,
                    "error": ""
                }
                
    except Exception as e:
        return {"error": f"Query execution error: {str(e)}", "data": []}
    finally:
        if conn:
            conn.close()