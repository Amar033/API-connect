# User-friendly routes/llm.py - No database knowledge required
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from models import ExternalDBCredential, User
from database import get_db
from auth import get_current_user
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import psycopg2
import logging
import json
import urllib.request
import re

router = APIRouter(prefix="/llm-chat", tags=["Natural Language Database Chat- Better than llm"])

logger = logging.getLogger(__name__)

# Simple request models - user just asks questions
class SimpleQuestionRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    question: str
    answer: str
    sql_used: Optional[str] = None
    data: Optional[List[Dict[str, Any]]] = None
    suggestion: Optional[str] = None
    error: Optional[str] = None

class DatabaseSummaryResponse(BaseModel):
    databases: List[Dict[str, Any]]
    total_tables: int
    sample_questions: List[str]

# Helper functions
def query_ollama_model(prompt, model="llama3", url="http://localhost:11434/api/generate"):
    """Query the Ollama model"""
    data = {
        "model": model,
        "prompt": prompt,
        "stream": True,
        "options": {
            "seed": 123,
            "temperature": 0,
            "num_ctx": 8192  # Larger context for better understanding
        }
    }
    
    payload = json.dumps(data).encode("utf-8")
    request = urllib.request.Request(url, data=payload, method="POST")
    request.add_header("Content-Type", "application/json")
    
    response_data = ""
    try:
        with urllib.request.urlopen(request) as response:
            while True:
                line = response.readline().decode("utf-8")
                if not line:
                    break
                response_json = json.loads(line)
                response_data += response_json.get("response", "")
    except Exception as e:
        logger.error(f"Ollama query failed: {e}")
        return f"Error querying model: {str(e)}"
    
    return response_data

def clean_sql_query(sql_query: str) -> str:
    """Clean SQL query from LLM response"""
    if not sql_query:
        return ""
    
    cleaned = sql_query.strip()
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = re.sub(r'```sql\n?', '', cleaned)
    cleaned = re.sub(r'```\n?', '', cleaned)
    
    # Extract SQL statement
    sql_patterns = [
        r'(SELECT\s+.*?(?:;|$))',
        r'(INSERT\s+.*?(?:;|$))',
        r'(UPDATE\s+.*?(?:;|$))',
        r'(DELETE\s+.*?(?:;|$))'
    ]
    
    for pattern in sql_patterns:
        match = re.search(pattern, cleaned, re.IGNORECASE | re.DOTALL)
        if match:
            cleaned = match.group(1)
            break
    
    cleaned = cleaned.rstrip(';').strip() + ';'
    return cleaned

def get_comprehensive_database_context(credentials: List[ExternalDBCredential]) -> str:
    """Get comprehensive context about all user's databases"""
    context = "USER'S AVAILABLE DATABASES:\n\n"
    
    total_tables = 0
    all_tables_info = []
    
    for cred in credentials:
        db_name = cred.name or f"Database_{cred.id}"
        context += f"📊 DATABASE: {db_name}\n"
        context += f"   Host: {cred.host}:{cred.port}\n"
        context += f"   Database: {cred.dbname}\n\n"
        
        try:
            conn = psycopg2.connect(
                host=cred.host,
                port=cred.port,
                dbname=cred.dbname,
                user=cred.db_user,
                password=cred.db_password,
                connect_timeout=5
            )
            
            with conn.cursor() as cur:
                # Get detailed table and column information
                cur.execute("""
                    SELECT 
                        t.table_name,
                        c.column_name,
                        c.data_type,
                        c.is_nullable,
                        CASE 
                            WHEN pk.column_name IS NOT NULL THEN 'PRIMARY KEY'
                            WHEN fk.column_name IS NOT NULL THEN 'FOREIGN KEY'
                            ELSE ''
                        END as key_type
                    FROM information_schema.tables t
                    LEFT JOIN information_schema.columns c ON t.table_name = c.table_name
                    LEFT JOIN (
                        SELECT ku.table_name, ku.column_name
                        FROM information_schema.table_constraints tc
                        JOIN information_schema.key_column_usage ku ON tc.constraint_name = ku.constraint_name
                        WHERE tc.constraint_type = 'PRIMARY KEY'
                    ) pk ON c.table_name = pk.table_name AND c.column_name = pk.column_name
                    LEFT JOIN (
                        SELECT ku.table_name, ku.column_name
                        FROM information_schema.table_constraints tc
                        JOIN information_schema.key_column_usage ku ON tc.constraint_name = ku.constraint_name
                        WHERE tc.constraint_type = 'FOREIGN KEY'
                    ) fk ON c.table_name = fk.table_name AND c.column_name = fk.column_name
                    WHERE t.table_schema = 'public' AND t.table_type = 'BASE TABLE'
                    ORDER BY t.table_name, c.ordinal_position;
                """)
                
                rows = cur.fetchall()
                current_table = None
                table_count = 0
                
                for row in rows:
                    table_name, column_name, data_type, is_nullable, key_type = row
                    
                    if table_name != current_table:
                        if current_table is not None:
                            context += "\n"
                        context += f"   📋 TABLE: {table_name}\n"
                        current_table = table_name
                        table_count += 1
                        
                        # Get sample data to understand content
                        try:
                            cur.execute(f"SELECT * FROM {table_name} LIMIT 2")
                            sample_data = cur.fetchall()
                            if sample_data:
                                context += f"      Sample rows: {len(sample_data)} examples available\n"
                        except:
                            pass
                    
                    # Add column info
                    nullable = "NULL" if is_nullable == 'YES' else "NOT NULL"
                    key_info = f" [{key_type}]" if key_type else ""
                    context += f"      • {column_name}: {data_type} {nullable}{key_info}\n"
                
                total_tables += table_count
                context += f"   Total tables in {db_name}: {table_count}\n\n"
                
            conn.close()
            
        except Exception as e:
            context += f"   ❌ Connection failed: {str(e)}\n\n"
    
    context += f"\nTOTAL TABLES ACROSS ALL DATABASES: {total_tables}\n\n"
    
    return context

def generate_sample_questions(context: str) -> List[str]:
    """Generate sample questions based on database context"""
    
    # Extract table names from context
    table_matches = re.findall(r'📋 TABLE: (\w+)', context)
    
    questions = []
    
    # Generic questions that work with most databases
    if table_matches:
        # Use actual table names if found
        if any('user' in table.lower() or 'customer' in table.lower() for table in table_matches):
            questions.extend([
                "How many users/customers do we have?",
                "Show me the latest 5 users/customers",
                "Find users with names containing 'John'"
            ])
        
        if any('order' in table.lower() or 'sale' in table.lower() or 'purchase' in table.lower() for table in table_matches):
            questions.extend([
                "What are our recent orders/sales?",
                "Show me orders from this month",
                "Which customer has the most orders?"
            ])
        
        if any('product' in table.lower() or 'item' in table.lower() for table in table_matches):
            questions.extend([
                "List all products/items",
                "What are the most expensive products?",
                "Show me products with low stock"
            ])
        
        # Generic questions using actual table names
        questions.extend([
            f"Show me all data from {table_matches[0]}" if table_matches else "Show me all data",
            f"How many records are in {table_matches[0]}?" if table_matches else "How many records do we have?",
            "What tables do we have and what's in them?"
        ])
    else:
        # Fallback generic questions
        questions = [
            "What data do we have available?",
            "Show me some sample data",
            "How many records do we have?",
            "What are the main tables in the database?",
            "Give me a summary of our data"
        ]
    
    return questions[:6]  # Return up to 6 questions

@router.get("/summary", response_model=DatabaseSummaryResponse)
async def get_database_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a summary of user's databases and suggest questions they can ask"""
    
    credentials = db.query(ExternalDBCredential).filter(
        ExternalDBCredential.user_id == current_user.id
    ).all()
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No database connections found. Please add a database connection first."
        )
    
    # Get database context
    context = get_comprehensive_database_context(credentials)
    
    # Extract summary info
    databases = []
    total_tables = 0
    
    for cred in credentials:
        db_info = {
            "name": cred.name or f"Database_{cred.id}",
            "host": cred.host,
            "database": cred.dbname,
            "status": "unknown",
            "table_count": 0
        }
        
        try:
            conn = psycopg2.connect(
                host=cred.host,
                port=cred.port,
                dbname=cred.dbname,
                user=cred.db_user,
                password=cred.db_password,
                connect_timeout=5
            )
            
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                """)
                table_count = cur.fetchone()[0]
                db_info["table_count"] = table_count
                total_tables += table_count
            
            conn.close()
            db_info["status"] = "connected"
            
        except Exception as e:
            db_info["status"] = "failed"
            db_info["error"] = str(e)
        
        databases.append(db_info)
    
    # Generate sample questions
    sample_questions = generate_sample_questions(context)
    
    return DatabaseSummaryResponse(
        databases=databases,
        total_tables=total_tables,
        sample_questions=sample_questions
    )

@router.post("/ask", response_model=ChatResponse)
async def ask_question(
    request: SimpleQuestionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Ask any question about your data - no database knowledge required!"""
    
    credentials = db.query(ExternalDBCredential).filter(
        ExternalDBCredential.user_id == current_user.id
    ).all()
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No database connections found. Please add a database connection first."
        )
    
    try:
        # Get comprehensive database context
        database_context = get_comprehensive_database_context(credentials)
        
        # Create an intelligent prompt for the LLM
        prompt = f"""You are a helpful database assistant. The user has asked a question about their data, but they don't know anything about database structure, tables, or SQL.

USER'S QUESTION: "{request.question}"

{database_context}

INSTRUCTIONS:
1. Understand what the user is asking for in plain English
2. Look at the available tables and columns to find the best match
3. Generate a SQL query that answers their question
4. Use ILIKE '%term%' for partial text matching when searching
5. Use appropriate JOINs when data spans multiple tables
6. Add LIMIT to prevent overwhelming results
7. If the question is vague, make reasonable assumptions based on common business needs

IMPORTANT:
- The user doesn't know table/column names, so be smart about mapping their intent
- If they ask about "users", look for tables like users, customers, people, etc.
- If they ask about "sales", look for orders, transactions, purchases, etc.
- If they ask about "products", look for items, inventory, catalog, etc.
- Use fuzzy matching - if they search for "john", use ILIKE '%john%'

Generate ONLY the SQL query that best answers their question. No explanations."""

        # Get SQL from LLM
        raw_sql = query_ollama_model(prompt)
        generated_sql = clean_sql_query(raw_sql)
        
        if not generated_sql or "error" in generated_sql.lower():
            return ChatResponse(
                question=request.question,
                answer="I couldn't understand your question. Could you try asking in a different way?",
                error="Failed to generate appropriate SQL query",
                suggestion="Try asking about specific things like 'how many records do we have?' or 'show me some sample data'"
            )
        
        # Execute the query on the most appropriate database
        execution_result = None
        used_database = None
        
        for cred in credentials:
            try:
                conn = psycopg2.connect(
                    host=cred.host,
                    port=cred.port,
                    dbname=cred.dbname,
                    user=cred.db_user,
                    password=cred.db_password
                )
                
                with conn.cursor() as cur:
                    # Add LIMIT if it's a SELECT without LIMIT
                    if generated_sql.upper().startswith('SELECT') and 'LIMIT' not in generated_sql.upper():
                        generated_sql = generated_sql.rstrip(';') + ' LIMIT 20;'
                    
                    cur.execute(generated_sql)
                    
                    if generated_sql.upper().startswith('SELECT'):
                        columns = [desc[0] for desc in cur.description]
                        rows = cur.fetchall()
                        
                        execution_result = {
                            "data": [dict(zip(columns, row)) for row in rows],
                            "columns": columns,
                            "row_count": len(rows)
                        }
                    else:
                        conn.commit()
                        execution_result = {
                            "affected_rows": cur.rowcount,
                            "data": []
                        }
                
                conn.close()
                used_database = cred.name or f"Database_{cred.id}"
                break  # Success - use this result
                
            except Exception as e:
                logger.error(f"Query execution failed on {cred.name}: {e}")
                continue  # Try next database
        
        if execution_result is None:
            return ChatResponse(
                question=request.question,
                answer="I couldn't execute the query on any of your databases. There might be a connection issue.",
                sql_used=generated_sql,
                error="All database connections failed",
                suggestion="Please check your database connections and try again."
            )
        
        # Format the answer in a user-friendly way
        if execution_result.get("data"):
            row_count = len(execution_result["data"])
            if row_count == 0:
                answer = "No results found for your query."
            elif row_count == 1:
                answer = f"Found 1 result."
            else:
                answer = f"Found {row_count} results."
            
            # Add some context about the data
            if row_count > 0 and row_count <= 5:
                answer += " Here's what I found:"
            elif row_count > 5:
                answer += f" Here are the first {min(row_count, 20)} results:"
        else:
            affected_rows = execution_result.get("affected_rows", 0)
            answer = f"Query executed successfully. {affected_rows} rows affected."
        
        return ChatResponse(
            question=request.question,
            answer=answer,
            sql_used=generated_sql,
            data=execution_result.get("data", []),
            suggestion="You can ask follow-up questions like 'show me more details' or 'filter by specific criteria'"
        )
        
    except Exception as e:
        logger.error(f"Question processing failed: {str(e)}")
        return ChatResponse(
            question=request.question,
            answer="Sorry, I encountered an error processing your question.",
            error=str(e),
            suggestion="Try asking a simpler question or check if your databases are accessible."
        )

@router.post("/follow-up")
async def ask_follow_up(
    request: SimpleQuestionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Ask follow-up questions based on previous context"""
    # For now, this just calls the main ask endpoint
    # In the future, you could maintain conversation context
    return await ask_question(request, db, current_user)