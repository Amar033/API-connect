from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from models import ExternalDBCredential, User
from schemas import ExternalDBCredentialCreate, ExternalDBCredential as ExternalDBCredentialSchema
from database import get_db
from auth import get_current_user
from pydantic import BaseModel
from typing import Optional,List, Dict, Any
import logging

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


router=APIRouter(prefix="/llm-chat",tags=["LLM Interaction"])

@router.post("/")
async def llm_connect(db: Session=Depends(get_db),current_user: User=Depends(get_current_user)):
    credentials = db.query(ExternalDBCredential).filter(
        ExternalDBCredential.user_id == current_user.id
    ).all()

    return [
        {
            "id": cred.id,
            "db_name": cred.dbname,
            "db_user": cred.db_user,
            "db_type": cred.db_password,
            "db_host": cred.host,
            "db_port": cred.port
        }
        for cred in credentials
    ]

