from fastapi import APIRouter,Depends, HTTPException, status
from sqlalchemy.orm import Session
from models import ExternalDBCredential, User
from schemas import ExternalDBCredentialCreate, ExternalDBCredential as ExternalDBCredentialSchema
from database import get_db
from auth import get_current_user
from pydantic import BaseModel
from typing import Optional,List, Dict, Any
import logging
import psycopg2
from llmcall import generate_sql_response, execute_sql_query

class ChatRequest(BaseModel):
    question: str
    database_id: Optional[str] = None  # Specific database ID to use
    execute_query: bool = False  # Whether to execute the generated SQL


class ChatResponse(BaseModel):
    user_question: str
    generated_sql: str
    target_database: Dict[str, Any]
    execution_results: Optional[Dict[str, Any]] = None
    available_databases: List[Dict[str, Any]]
    error: Optional[str] = None

class DatabaseTestRequest(BaseModel):
    database_id: str

logger = logging.getLogger(__name__)


router=APIRouter(prefix="/llm",tags=["LLM Interaction"])


@router.get("/databases-with-status")
async def get_databases_with_connection_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's databases with connection status (enhanced version of /db-connections/)"""
    credentials = db.query(ExternalDBCredential).filter(
        ExternalDBCredential.user_id == current_user.id
    ).all()
    
    if not credentials:
        return {
            "message": "No external database connections found",
            "databases": []
        }
    
    databases = []
    for cred in credentials:
        # Test connection status
        connection_status = await test_database_connection(cred)
        
        databases.append({
            "id": str(cred.id),
            "name": cred.name or f"Database_{cred.id}",
            "db_name": cred.dbname,
            "db_user": cred.db_user,
            "db_host": cred.host,
            "db_port": cred.port,
            "connection_status": connection_status["status"],
            "table_count": connection_status.get("table_count", 0),
            "error": connection_status.get("error"),
            "created_at": cred.created_at
        })
    
    return {
        "user_id": str(current_user.id),
        "total_databases": len(databases),
        "databases": databases
    }


async def test_database_connection(credential: ExternalDBCredential) -> Dict[str, Any]:
    """Test connection to an external database"""
    try:
        conn = psycopg2.connect(
            host=credential.host,
            port=credential.port,
            dbname=credential.dbname,
            user=credential.db_user,
            password=credential.db_password,
            connect_timeout=10
        )
        
        with conn.cursor() as cur:
            # Test basic connectivity
            cur.execute("SELECT current_database(), current_user;")
            db_info = cur.fetchone()
            
            # Get table count
            cur.execute("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            """)
            table_count = cur.fetchone()[0]
        
        conn.close()
        
        return {
            "status": "connected",
            "current_database": db_info[0],
            "current_user": db_info[1],
            "table_count": table_count
        }
        
    except Exception as e:
        logger.error(f"Connection test failed for {credential.host}:{credential.port}/{credential.dbname}: {str(e)}")
        return {
            "status": "failed",
            "error": str(e),
            "table_count": 0
        }


@router.post("/test-connection")
async def test_specific_database(
    request: DatabaseTestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Test connection to a specific database"""
    # Get the specific database credential
    credential = db.query(ExternalDBCredential).filter(
        ExternalDBCredential.id == request.database_id,
        ExternalDBCredential.user_id == current_user.id
    ).first()
    
    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Database not found or not accessible"
        )
    
    connection_result = await test_database_connection(credential)
    
    return {
        "database_id": request.database_id,
        "database_name": credential.name,
        "connection_result": connection_result
    }



@router.post("/get-schema")
async def get_database_schema(
    request: DatabaseTestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get schema information for a specific database"""
    # Get the specific database credential
    credential = db.query(ExternalDBCredential).filter(
        ExternalDBCredential.id == request.database_id,
        ExternalDBCredential.user_id == current_user.id
    ).first()
    
    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Database not found or not accessible"
        )
    
    try:
        conn = psycopg2.connect(
            host=credential.host,
            port=credential.port,
            dbname=credential.dbname,
            user=credential.db_user,
            password=credential.db_password
        )
        
        schema_info = {}
        
        with conn.cursor() as cur:
            # Get all tables and their columns
            cur.execute("""
                SELECT 
                    t.table_name,
                    c.column_name,
                    c.data_type,
                    c.is_nullable,
                    c.column_default,
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
            
            for row in rows:
                table_name = row[0]
                if table_name not in schema_info:
                    schema_info[table_name] = []
                
                schema_info[table_name].append({
                    'column_name': row[1],
                    'data_type': row[2],
                    'is_nullable': row[3],
                    'column_default': row[4],
                    'key_type': row[5]
                })
        
        conn.close()
        
        return {
            "database_id": request.database_id,
            "database_name": credential.name,
            "schema": schema_info,
            "total_tables": len(schema_info)
        }
        
    except Exception as e:
        logger.error(f"Schema retrieval failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve schema: {str(e)}"
        )


@router.post("/chat", response_model=ChatResponse)
async def chat_with_database(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Main chat endpoint - converts natural language to SQL and optionally executes"""
    
    # Get user's database credentials
    credentials = db.query(ExternalDBCredential).filter(
        ExternalDBCredential.user_id == current_user.id
    ).all()
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No database connections found. Please add a database connection first."
        )
    
    # Prepare available databases list
    available_databases = []
    for cred in credentials:
        available_databases.append({
            "id": str(cred.id),
            "name": cred.name or f"Database_{cred.id}",
            "host": cred.host,
            "dbname": cred.dbname
        })
    
    # Select target database
    target_credential = None
    if request.database_id:
        # Use specific database
        target_credential = next(
            (cred for cred in credentials if str(cred.id) == request.database_id), 
            None
        )
        if not target_credential:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Specified database not found"
            )
    else:
        # Use first available database
        target_credential = credentials[0]
    
    target_database = {
        "id": str(target_credential.id),
        "name": target_credential.name or f"Database_{target_credential.id}",
        "host": target_credential.host,
        "dbname": target_credential.dbname
    }
    
    try:
        # Generate SQL using your existing LLM system
        sql_result = generate_sql_response(
            user_input=request.question,
            user_db_credentials=credentials,
            preferred_db_name=target_database["name"]
        )
        
        if sql_result.get("error"):
            return ChatResponse(
                user_question=request.question,
                generated_sql="",
                target_database=target_database,
                available_databases=available_databases,
                error=sql_result["error"]
            )
        
        generated_sql = sql_result["sql"]
        response = ChatResponse(
            user_question=request.question,
            generated_sql=generated_sql,
            target_database=target_database,
            available_databases=available_databases
        )
        
        # Execute query if requested
        if request.execute_query and generated_sql:
            try:
                execution_result = execute_sql_query(generated_sql, target_credential)
                response.execution_results = execution_result
                
                if execution_result.get("error"):
                    response.error = f"Execution error: {execution_result['error']}"
                    
            except Exception as e:
                response.error = f"Execution failed: {str(e)}"
        
        return response
        
    except Exception as e:
        logger.error(f"Chat processing failed: {str(e)}")
        return ChatResponse(
            user_question=request.question,
            generated_sql="",
            target_database=target_database,
            available_databases=available_databases,
            error=f"Processing failed: {str(e)}"
        )


@router.post("/execute-sql")
async def execute_custom_sql(
    sql_query: str,
    database_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Execute a custom SQL query on a specific database"""
    
    # Get the specific database credential
    credential = db.query(ExternalDBCredential).filter(
        ExternalDBCredential.id == database_id,
        ExternalDBCredential.user_id == current_user.id
    ).first()
    
    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Database not found or not accessible"
        )
    
    try:
        result = execute_sql_query(sql_query, credential)
        return {
            "database_id": database_id,
            "database_name": credential.name,
            "sql_query": sql_query,
            "results": result
        }
        
    except Exception as e:
        logger.error(f"SQL execution failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query execution failed: {str(e)}"
        )
