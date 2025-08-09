# Updated routes/llm.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from models import ExternalDBCredential, User
from database import get_db
from auth import get_current_user
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from llmcall import (  # Import your LLM functions
    generate_sql_response,
    execute_sql_query,
    get_user_database_schemas,
    format_schema_for_llm
)
import logging

router = APIRouter(prefix="/llm-chat", tags=["Natural Language Database Chat"])

logger = logging.getLogger(__name__)

# Request/Response Models (unchanged)
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

# Helper Functions (simplified using llmcall.py)
def get_comprehensive_database_context(credentials: List[ExternalDBCredential]) -> str:
    """Use llmcall's schema functions"""
    try:
        schemas = get_user_database_schemas(credentials)
        return format_schema_for_llm(schemas)
    except Exception as e:
        logger.error(f"Failed to get schemas: {str(e)}")
        return f"Error getting database schemas: {str(e)}"

@router.get("/summary", response_model=DatabaseSummaryResponse)
async def get_database_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get summary using llmcall.py functions"""
    credentials = db.query(ExternalDBCredential).filter(
        ExternalDBCredential.user_id == current_user.id
    ).all()
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No database connections found."
        )
    
    # Get database info using llmcall
    schemas = get_user_database_schemas(credentials)
    total_tables = sum(len(tables) for tables in schemas.values())
     
    databases_response = []
    for cred in credentials:
        db_info = {
            "name": cred.name or f"Database_{cred.id}",
            "host": cred.host,
            "database": cred.dbname,
            "status": "connected" if cred.dbname in schemas else "failed",
            "table_count": len(schemas.get(cred.dbname, []))
        }
        databases_response.append(db_info)
    
    context = get_comprehensive_database_context(credentials)
    sample_questions = [
        "How many records do we have?",
        "Show me sample customer data",
        "What are our recent orders?"
    ]
    
    return DatabaseSummaryResponse(
        databases=databases_response,
        total_tables=total_tables,
        sample_questions=sample_questions
    )

@router.post("/ask", response_model=ChatResponse)
async def ask_question(
    request: SimpleQuestionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Main endpoint using llmcall.py functions"""
    credentials = db.query(ExternalDBCredential).filter(
        ExternalDBCredential.user_id == current_user.id
    ).all()
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No database connections found."
        )
    
    try:
        # Step 1: Generate SQL using llmcall
        result = generate_sql_response(
            user_input=request.question,
            user_db_credentials=credentials
        )
        
        if result.get("error"):
            return ChatResponse(
                question=request.question,
                answer="I couldn't understand your question.",
                error=result["error"],
                suggestion="Try asking differently."
            )
        
        # Step 2: Execute the query
        target_db = next(
            (cred for cred in credentials 
             if cred.name == result["database"] or cred.dbname == result["database"]),
            credentials[0]  # fallback
        )
        
        execution_result = execute_sql_query(
            sql_query=result["sql"],
            db_credential=target_db
        )
        
        # Step 3: Format response
        if execution_result.get("error"):
            return ChatResponse(
                question=request.question,
                answer="Couldn't execute the query.",
                sql_used=result["sql"],
                error=execution_result["error"]
            )
        
        data = execution_result.get("data", [])
        answer = format_answer(
            question=request.question,
            data=data,
            row_count=len(data)
        )
        
        return ChatResponse(
            question=request.question,
            answer=answer,
            sql_used=result["sql"],
            data=data,
            suggestion=get_suggestion_based_on_results(data)
        )
        
    except Exception as e:
        logger.error(f"Error in ask_question: {str(e)}", exc_info=True)
        return ChatResponse(
            question=request.question,
            answer="An error occurred.",
            error=str(e)
        )

# Helper functions for response formatting
def format_answer(question: str, data: list, row_count: int) -> str:
    """Format a user-friendly answer"""
    if row_count == 0:
        return "No results found."
    
    if "count" in question.lower():
        return f"There are {row_count} results."
    
    if row_count == 1:
        return "Here's the result:"
    
    return f"Found {row_count} results. Showing first {min(row_count, 20)}:"

def get_suggestion_based_on_results(data: list) -> str:
    """Generate context-aware suggestions"""
    if not data:
        return "Try broadening your search criteria."
    
    first_row = data[0]
    if 'name' in first_row:
        return "Try asking about specific names or filtering by dates."
    if 'date' in first_row:
        return "You might ask about trends over time or recent records."
    
    return "Ask to see more details or filter the results further."