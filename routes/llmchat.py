# from fastapi import APIRouter, Depends, HTTPException, status
# from sqlalchemy.orm import Session
# from models import ExternalDBCredential, User
# from database import get_db
# from auth import get_current_user
# from pydantic import BaseModel
# from typing import Optional, List, Dict, Any
# from llmcall import ( 
#     generate_sql_response,
#     execute_sql_query,
#     get_user_database_schemas,
#     format_schema_for_llm
# )
# import logging
# import hashlib
# from cache import get_cache, set_cache #exact cache search
# from cache import find_semantic_cache, store_semantic_cache
# import time
# from fastapi.responses import StreamingResponse
# import json


# def timed_step(step_name, func, *args, **kwargs):
#     start = time.time()
#     result = func(*args, **kwargs)
#     elapsed = time.time() - start
#     logger.info(f"⏱ {step_name} took {elapsed:.2f}s")
#     return result





# router = APIRouter(prefix="/llm-chat", tags=["Natural Language Database Chat"])

# logger = logging.getLogger(__name__)

# # Request/Response Models (unchanged)
# class SimpleQuestionRequest(BaseModel):
#     question: str

# class ChatResponse(BaseModel):
#     question: str
#     answer: str
#     sql_used: Optional[str] = None
#     data: Optional[List[Dict[str, Any]]] = None
#     suggestion: Optional[str] = None
#     error: Optional[str] = None

# class DatabaseSummaryResponse(BaseModel):
#     databases: List[Dict[str, Any]]
#     total_tables: int
#     sample_questions: List[str]



# '''Woks for internal memory cache, not useful if there are many sessions'''
# # CACHE_TTL = 300  # 5 minutes
# # cache_store = {}  # { cache_key: (expiry_timestamp, data) }

# # def make_cache_key(user_id: int, question: str) -> str:
# #     normalized_q = question.strip().lower()
# #     return f"user:{user_id}:q:{normalized_q}"

# # def get_cache(key: str):
# #     entry = cache_store.get(key)
# #     if not entry:
# #         return None
# #     expiry, value = entry
# #     if time.time() > expiry:
# #         cache_store.pop(key, None)
# #         return None
# #     return value

# # def set_cache(key: str, value: dict, ttl: int = CACHE_TTL):
# #     cache_store[key] = (time.time() + ttl, value)






# def get_comprehensive_database_context(credentials: List[ExternalDBCredential]) -> str:
#     """Use llmcall's schema functions"""
#     try:
#         schemas = get_user_database_schemas(credentials)
#         return format_schema_for_llm(schemas)
#     except Exception as e:
#         logger.error(f"Failed to get schemas: {str(e)}")
#         return f"Error getting database schemas: {str(e)}"

# @router.get("/summary", response_model=DatabaseSummaryResponse)
# async def get_database_summary(
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     """Get summary using llmcall.py functions"""
#     credentials = db.query(ExternalDBCredential).filter(
#         ExternalDBCredential.user_id == current_user.id
#     ).all()
    
#     if not credentials:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="No database connections found."
#         )
    
#     # Get database info using llmcall
#     schemas = get_user_database_schemas(credentials)
#     total_tables = sum(len(tables) for tables in schemas.values())
     
#     databases_response = []
#     for cred in credentials:
#         db_info = {
#             "name": cred.name or f"Database_{cred.id}",
#             "host": cred.host,
#             "database": cred.dbname,
#             "status": "connected" if cred.dbname in schemas else "failed",
#             "table_count": len(schemas.get(cred.dbname, []))
#         }
#         databases_response.append(db_info)
    
#     context = get_comprehensive_database_context(credentials)
#     sample_questions = [
#         "How many records do we have?",
#         "Show me sample customer data",
#         "What are our recent orders?"
#     ]
    
#     return DatabaseSummaryResponse(
#         databases=databases_response,
#         total_tables=total_tables,
#         sample_questions=sample_questions
#     )
# @router.post("/ask-stream", response_class=StreamingResponse)
# async def ask_question_stream(
#     request: SimpleQuestionRequest,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     def stream():
#         try:
#             # Step 0: Fetch DB credentials
#             yield json.dumps({"status": "info", "message": "Fetching DB credentials..."}) + "\n"
#             credentials = db.query(ExternalDBCredential).filter(
#                 ExternalDBCredential.user_id == current_user.id
#             ).all()
#             if not credentials:
#                 yield json.dumps({"status": "error", "message": "No database connections found."}) + "\n"
#                 return

#             # Step 1: Check semantic cache
#             yield json.dumps({"status": "info", "message": "Checking semantic cache..."}) + "\n"
#             cached_response = find_semantic_cache(current_user.id, request.question)
#             if cached_response:
#                 yield json.dumps({"status": "cache_hit", "data": cached_response}) + "\n"
#                 return
#             yield json.dumps({"status": "info", "message": "Cache miss. Generating SQL..."}) + "\n"

#             # Step 2: Generate SQL
#             result = generate_sql_response(current_user.id, request.question, credentials)
#             if result.get("error"):
#                 yield json.dumps({"status": "error", "message": result["error"]}) + "\n"
#                 return

#             # Step 3: Execute SQL
#             yield json.dumps({"status": "info", "message": f"Executing query: {result['sql']}"}) + "\n"
#             target_db = next(
#                 (cred for cred in credentials 
#                  if cred.name == result["database"] or cred.dbname == result["database"]),
#                 credentials[0]
#             )
#             execution_result = execute_sql_query(result["sql"], target_db)
#             if execution_result.get("error"):
#                 yield json.dumps({"status": "error", "message": execution_result["error"]}) + "\n"
#                 return

#             # Step 4: Format answer
#             data = execution_result.get("data", [])
#             answer = format_answer(request.question, data, len(data))
#             suggestion = get_suggestion_based_on_results(data)

#             response_payload = ChatResponse(
#                 question=request.question,
#                 answer=answer,
#                 sql_used=result["sql"],
#                 data=data,
#                 suggestion=suggestion
#             )

#             # Step 5: Store in cache
#             store_semantic_cache(current_user.id, request.question, response_payload.model_dump(), 600)

#             # Final send
#             yield json.dumps({"status": "done", "data": response_payload.model_dump()}) + "\n"

#         except Exception as e:
#             yield json.dumps({"status": "error", "message": str(e)}) + "\n"

#     return StreamingResponse(stream(), media_type="text/event-stream")


# @router.post("/ask", response_model=ChatResponse)
# async def ask_question(
#     request: SimpleQuestionRequest,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     credentials = timed_step(
#         "Fetch DB credentials",
#         lambda: db.query(ExternalDBCredential).filter(
#             ExternalDBCredential.user_id == current_user.id
#         ).all()
#     )
    
#     if not credentials:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="No database connections found."
#         )

#     # Check semantic cache
#     cached_response = timed_step(
#         "Semantic cache lookup",
#         find_semantic_cache,
#         current_user.id,
#         request.question
#     )
#     if cached_response:
#         logger.info("✅ Cache hit")
#         return ChatResponse(**cached_response)
#     logger.info("❌ Cache miss")

#     try:
#         # Step 1: LLM generates SQL
#         result = timed_step(
#             "Generate SQL from LLM",
#             generate_sql_response,
#             current_user.id,
#             request.question,
#             credentials
#         )
        
#         if result.get("error"):
#             return ChatResponse(
#                 question=request.question,
#                 answer="I couldn't understand your question.",
#                 error=result["error"],
#                 suggestion="Try asking differently."
#             )

#         # Step 2: Choose target DB
#         target_db = next(
#             (cred for cred in credentials 
#              if cred.name == result["database"] or cred.dbname == result["database"]),
#             credentials[0]
#         )

#         # Step 3: Execute SQL
#         execution_result = timed_step(
#             "Execute SQL query",
#             execute_sql_query,
#             result["sql"],
#             target_db
#         )
        
#         if execution_result.get("error"):
#             return ChatResponse(
#                 question=request.question,
#                 answer="Couldn't execute the query.",
#                 sql_used=result["sql"],
#                 error=execution_result["error"]
#             )

#         # Step 4: Format answer
#         data = execution_result.get("data", [])
#         answer = timed_step(
#             "Format answer",
#             format_answer,
#             request.question,
#             data,
#             len(data)
#         )
#         suggestion = get_suggestion_based_on_results(data)

#         response_payload = ChatResponse(
#             question=request.question,
#             answer=answer,
#             sql_used=result["sql"],
#             data=data,
#             suggestion=suggestion
#         )

#         # Step 5: Store in semantic cache
#         timed_step(
#             "Store in semantic cache",
#             store_semantic_cache,
#             current_user.id,
#             request.question,
#             response_payload.model_dump(),
#             600
#         )

#         return response_payload

#     except Exception as e:
#         logger.error(f"Error in ask_question: {str(e)}", exc_info=True)
#         return ChatResponse(
#             question=request.question,
#             answer="An error occurred.",
#             error=str(e)
#         )


# # Helper functions for response formatting
# def format_answer(question: str, data: list, row_count: int) -> str:
#     """Format a user-friendly answer"""
#     if row_count == 0:
#         return "No results found."
    
#     if "count" in question.lower():
#         return f"There are {row_count} results."
    
#     if row_count == 1:
#         return "Here's the result:"
    
#     return f"Found {row_count} results. Showing first {min(row_count, 20)}:"

# def get_suggestion_based_on_results(data: list) -> str:
#     """Generate context-aware suggestions"""
#     if not data:
#         return "Try broadening your search criteria."
    
#     first_row = data[0]
#     if 'name' in first_row:
#         return "Try asking about specific names or filtering by dates."
#     if 'date' in first_row:
#         return "You might ask about trends over time or recent records."
    
#     return "Ask to see more details or filter the results further."



from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from models import ExternalDBCredential, User
from database import get_db
from auth import get_current_user
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from llmcall import ( 
    generate_sql_response,
    execute_sql_query,
    get_user_database_schemas,
    format_schema_for_llm
)
import logging
import hashlib
from cache import find_semantic_cache, store_semantic_cache
import time
from fastapi.responses import StreamingResponse
import json
import asyncio
import uuid
from datetime import datetime, timedelta
from enum import Enum
from cache import EnhancedJSONEncoder

# Task status enumeration
class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


# In-memory task store (in production, use Redis or database)
task_store: Dict[str, Dict] = {}
TASK_TIMEOUT = 300  # 5 minutes


def timed_step(step_name, func, *args, **kwargs):
    start = time.time()
    result = func(*args, **kwargs)
    elapsed = time.time() - start
    logger.info(f"⏱ {step_name} took {elapsed:.2f}s")
    return result


router = APIRouter(prefix="/llm-chat", tags=["Natural Language Database Chat"])
logger = logging.getLogger(__name__)


# Enhanced Request/Response Models
class SimpleQuestionRequest(BaseModel):
    question: str
    timeout_seconds: Optional[int] = 300  # 5 minutes default

class TaskInitResponse(BaseModel):
    task_id: str
    status: TaskStatus
    message: str
    estimated_time: Optional[int] = None

class TaskStatusResponse(BaseModel):
    task_id: str
    status: TaskStatus
    progress: Optional[str] = None
    result: Optional[Dict] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    estimated_completion: Optional[datetime] = None

class ChatResponse(BaseModel):
    question: str
    answer: str
    sql_used: Optional[str] = None
    data: Optional[List[Dict[str, Any]]] = None
    suggestion: Optional[str] = None
    error: Optional[str] = None
    processing_time: Optional[float] = None

class DatabaseSummaryResponse(BaseModel):
    databases: List[Dict[str, Any]]
    total_tables: int
    sample_questions: List[str]


# Task management functions
def create_task(user_id: int, question: str, timeout_seconds: int = 300) -> str:
    """Create a new background task"""
    task_id = str(uuid.uuid4())
    now = datetime.now()
    
    task_store[task_id] = {
        "task_id": task_id,
        "user_id": user_id,
        "question": question,
        "status": TaskStatus.PENDING,
        "progress": "Task created",
        "result": None,
        "error": None,
        "created_at": now,
        "updated_at": now,
        "timeout_seconds": timeout_seconds,
        "estimated_completion": now + timedelta(seconds=min(timeout_seconds, 60))
    }
    
    return task_id


def update_task_status(task_id: str, status: TaskStatus, progress: str = None, 
                      result: Dict = None, error: str = None):
    """Update task status and metadata"""
    if task_id not in task_store:
        return
    
    task = task_store[task_id]
    task["status"] = status
    task["updated_at"] = datetime.utcnow()
    
    if progress:
        task["progress"] = progress
    if result:
        task["result"] = result
    if error:
        task["error"] = error


def cleanup_old_tasks():
    """Clean up tasks older than 1 hour"""
    cutoff = datetime.utcnow() - timedelta(hours=1)
    to_remove = [
        task_id for task_id, task in task_store.items()
        if task["created_at"] < cutoff
    ]
    for task_id in to_remove:
        del task_store[task_id]
    
    if to_remove:
        logger.info(f"Cleaned up {len(to_remove)} old tasks")


async def process_question_background(task_id: str, question: str, user_id: int, 
                                    credentials: List[ExternalDBCredential]):
    """Background task to process the question"""
    start_time = time.time()
    
    try:
        update_task_status(task_id, TaskStatus.PROCESSING, "Checking semantic cache...")
        
        # Step 1: Check semantic cache
        cached_response = await asyncio.to_thread(
            find_semantic_cache, user_id, question
        )
        
        if cached_response:
            logger.info("✅ Cache hit for background task")
            update_task_status(
                task_id, 
                TaskStatus.COMPLETED, 
                "Retrieved from cache",
                result=cached_response
            )
            return

        update_task_status(task_id, TaskStatus.PROCESSING, "Generating SQL query...")
        
        # Step 2: Generate SQL with timeout
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(generate_sql_response, user_id, question, credentials),
                timeout=120  # 2 minute timeout for SQL generation
            )
        except asyncio.TimeoutError:
            update_task_status(
                task_id, 
                TaskStatus.TIMEOUT, 
                error="SQL generation timed out"
            )
            return
        
        if result.get("error"):
            update_task_status(
                task_id, 
                TaskStatus.FAILED, 
                error=result["error"]
            )
            return

        update_task_status(task_id, TaskStatus.PROCESSING, f"Executing query: {result['sql'][:100]}...")

        # Step 3: Choose target DB and execute
        target_db = next(
            (cred for cred in credentials 
             if cred.name == result["database"] or cred.dbname == result["database"]),
            credentials[0]
        )

        try:
            execution_result = await asyncio.wait_for(
                asyncio.to_thread(execute_sql_query, result["sql"], target_db),
                timeout=180  # 3 minute timeout for query execution
            )
        except asyncio.TimeoutError:
            update_task_status(
                task_id, 
                TaskStatus.TIMEOUT, 
                error="Query execution timed out"
            )
            return
        
        if execution_result.get("error"):
            update_task_status(
                task_id, 
                TaskStatus.FAILED, 
                error=execution_result["error"]
            )
            return

        update_task_status(task_id, TaskStatus.PROCESSING, "Formatting response...")

        # Step 4: Format answer
        data = execution_result.get("data", [])
        answer = format_answer(question, data, len(data))
        suggestion = get_suggestion_based_on_results(data)
        processing_time = time.time() - start_time

        response_payload = {
            "question": question,
            "answer": answer,
            "sql_used": result["sql"],
            "data": data,
            "suggestion": suggestion,
            "processing_time": processing_time
        }

        # Step 5: Store in cache (fire and forget)
        asyncio.create_task(
            asyncio.to_thread(
                store_semantic_cache, user_id, question, response_payload, 600
            )
        )

        update_task_status(
            task_id, 
            TaskStatus.COMPLETED, 
            "Query completed successfully",
            result=response_payload
        )

    except Exception as e:
        logger.error(f"Background task {task_id} failed: {str(e)}", exc_info=True)
        update_task_status(
            task_id, 
            TaskStatus.FAILED, 
            error=str(e)
        )


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


@router.post("/ask-async", response_model=TaskInitResponse)
async def ask_question_async(
    request: SimpleQuestionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Initiate async processing of a question"""
    # Clean up old tasks
    cleanup_old_tasks()
    
    credentials = db.query(ExternalDBCredential).filter(
        ExternalDBCredential.user_id == current_user.id
    ).all()
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No database connections found."
        )

    # Create task
    task_id = create_task(current_user.id, request.question, request.timeout_seconds)
    
    # Start background processing
    background_tasks.add_task(
        process_question_background, 
        task_id, 
        request.question, 
        current_user.id, 
        credentials
    )
    
    return TaskInitResponse(
        task_id=task_id,
        status=TaskStatus.PENDING,
        message="Question submitted for processing",
        estimated_time=60
    )


@router.get("/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get the status of a background task"""
    if task_id not in task_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    task = task_store[task_id]
    
    # Verify ownership
    if task["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Check for timeout
    if (task["status"] in [TaskStatus.PENDING, TaskStatus.PROCESSING] and 
        datetime.utcnow() - task["created_at"] > timedelta(seconds=task["timeout_seconds"])):
        update_task_status(task_id, TaskStatus.TIMEOUT, error="Task timed out")
        task = task_store[task_id]  # Refresh task data
    
    return TaskStatusResponse(**task)


@router.get("/tasks", response_model=List[TaskStatusResponse])
async def get_user_tasks(
    current_user: User = Depends(get_current_user),
    limit: int = 10
):
    """Get recent tasks for the current user"""
    user_tasks = [
        task for task in task_store.values()
        if task["user_id"] == current_user.id
    ]
    
    # Sort by created_at descending and limit
    user_tasks.sort(key=lambda x: x["created_at"], reverse=True)
    return [TaskStatusResponse(**task) for task in user_tasks[:limit]]


@router.delete("/task/{task_id}")
async def cancel_task(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """Cancel or delete a task"""
    if task_id not in task_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    task = task_store[task_id]
    
    # Verify ownership
    if task["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    del task_store[task_id]
    return {"message": "Task deleted successfully"}


# Keep your original streaming endpoint for real-time use cases
@router.post("/ask-stream", response_class=StreamingResponse)
async def ask_question_stream(
    request: SimpleQuestionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Stream processing results in real-time (for faster queries)"""
    def stream():
        try:
            # Step 0: Fetch DB credentials
            yield json.dumps({"status": "info", "message": "Fetching DB credentials..."}) + "\n"
            credentials = db.query(ExternalDBCredential).filter(
                ExternalDBCredential.user_id == current_user.id
            ).all()
            if not credentials:
                yield json.dumps({"status": "error", "message": "No database connections found."}) + "\n"
                return

            # Step 1: Check semantic cache
            yield json.dumps({"status": "info", "message": "Checking semantic cache..."}) + "\n"
            cached_response = find_semantic_cache(current_user.id, request.question)
            if cached_response:
                yield json.dumps({"status": "cache_hit", "data": cached_response}) + "\n"
                return
            yield json.dumps({"status": "info", "message": "Cache miss. Generating SQL..."}) + "\n"

            # Step 2: Generate SQL
            result = generate_sql_response(current_user.id, request.question, credentials)
            if result.get("error"):
                yield json.dumps({"status": "error", "message": result["error"]}) + "\n"
                return

            # Step 3: Execute SQL
            yield json.dumps({"status": "info", "message": f"Executing query: {result['sql']}"}) + "\n"
            target_db = next(
                (cred for cred in credentials 
                 if cred.name == result["database"] or cred.dbname == result["database"]),
                credentials[0]
            )
            execution_result = execute_sql_query(result["sql"], target_db)
            if execution_result.get("error"):
                yield json.dumps({"status": "error", "message": execution_result["error"]}) + "\n"
                return

            # Step 4: Format answer
            data = execution_result.get("data", [])
            answer = format_answer(request.question, data, len(data))
            suggestion = get_suggestion_based_on_results(data)

            response_payload = ChatResponse(
                question=request.question,
                answer=answer,
                sql_used=result["sql"],
                data=data,
                suggestion=suggestion
            )

            # Step 5: Store in cache
            store_semantic_cache(current_user.id, request.question, response_payload.model_dump(), 600)
            
            # Final send
            # yield json.dumps({"status": "done", "data": response_payload.model_dump()}) + "\n"
            yield json.dumps({"status": "done", "data": response_payload.model_dump()}, cls=EnhancedJSONEncoder) + "\n"

        except Exception as e:
            yield json.dumps({"status": "error", "message": str(e)}) + "\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


# Keep your original synchronous endpoint for simple use cases
@router.post("/ask", response_model=ChatResponse)
async def ask_question(
    request: SimpleQuestionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Synchronous question processing (with timeout risk)"""
    credentials = timed_step(
        "Fetch DB credentials",
        lambda: db.query(ExternalDBCredential).filter(
            ExternalDBCredential.user_id == current_user.id
        ).all()
    )
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No database connections found."
        )

    # Check semantic cache
    cached_response = timed_step(
        "Semantic cache lookup",
        find_semantic_cache,
        current_user.id,
        request.question
    )
    if cached_response:
        logger.info("✅ Cache hit")
        return ChatResponse(**cached_response)
    logger.info("❌ Cache miss")

    try:
        # Step 1: LLM generates SQL
        result = timed_step(
            "Generate SQL from LLM",
            generate_sql_response,
            current_user.id,
            request.question,
            credentials
        )
        
        if result.get("error"):
            return ChatResponse(
                question=request.question,
                answer="I couldn't understand your question.",
                error=result["error"],
                suggestion="Try asking differently."
            )

        # Step 2: Choose target DB
        target_db = next(
            (cred for cred in credentials 
             if cred.name == result["database"] or cred.dbname == result["database"]),
            credentials[0]
        )

        # Step 3: Execute SQL
        execution_result = timed_step(
            "Execute SQL query",
            execute_sql_query,
            result["sql"],
            target_db
        )
        
        if execution_result.get("error"):
            return ChatResponse(
                question=request.question,
                answer="Couldn't execute the query.",
                sql_used=result["sql"],
                error=execution_result["error"]
            )

        # Step 4: Format answer
        data = execution_result.get("data", [])
        answer = timed_step(
            "Format answer",
            format_answer,
            request.question,
            data,
            len(data)
        )
        suggestion = get_suggestion_based_on_results(data)

        response_payload = ChatResponse(
            question=request.question,
            answer=answer,
            sql_used=result["sql"],
            data=data,
            suggestion=suggestion
        )

        # Step 5: Store in semantic cache
        timed_step(
            "Store in semantic cache",
            store_semantic_cache,
            current_user.id,
            request.question,
            response_payload.model_dump(),
            600
        )

        return response_payload

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