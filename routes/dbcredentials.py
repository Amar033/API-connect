
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, logger
import psycopg2
from sqlalchemy.orm import Session
from models import ExternalDBCredential, User
from schemas import ExternalDBCredentialCreate, ExternalDBCredential as ExternalDBCredentialSchema
from database import get_db
from auth import get_current_user
from typing import Union, Optional, List
from datetime import datetime
from pydantic import BaseModel

class DatabaseWithStatus(BaseModel):
    id: str
    name: str
    db_name: str
    db_user: str
    db_host: str
    db_port: int
    connection_status: str
    table_count: int
    error: Optional[str]
    created_at: datetime

class DatabasesWithStatusResponse(BaseModel):
    user_id: str
    total_databases: int
    databases: List[DatabaseWithStatus]



router = APIRouter(prefix="/db-connections", tags=["Database Connections"])

@router.post("/", response_model=ExternalDBCredentialSchema)
def create_db_connection(
    db_data: ExternalDBCredentialCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Create the database credential object
    db_conn = ExternalDBCredential(
        user_id=current_user.id,
        name=db_data.name,
        db_owner_username=db_data.db_owner_username,
        host=db_data.host,
        port=db_data.port,
        dbname=db_data.dbname,
        db_user=db_data.db_user,
        db_password=db_data.db_password
    )
    
    db.add(db_conn)
    db.commit()
    db.refresh(db_conn)
    return db_conn

# @router.get("/", response_model=list[ExternalDBCredentialSchema])
# def list_user_connections(
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user),
# ):
#     return db.query(ExternalDBCredential).filter(
#         ExternalDBCredential.user_id == current_user.id
#     ).all()


@router.get("/")
async def list_db_connections(
    include_status: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Union[List[ExternalDBCredentialSchema], DatabasesWithStatusResponse]:
    """
    Get user's database connections. 
    Use ?include_status=true to get enhanced version with connection status and table counts.
    """
    credentials = db.query(ExternalDBCredential).filter(
        ExternalDBCredential.user_id == current_user.id
    ).all()
    
    if not include_status:
        # Original functionality - return the schema format
        return credentials
    
    # Enhanced functionality when include_status=true
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
    
    return DatabasesWithStatusResponse(
        user_id=str(current_user.id),
        total_databases=len(databases),
        databases=databases
    )

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


@router.delete("/{connection_id}")
def delete_db_connection(
    connection_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_conn = db.query(ExternalDBCredential).filter(
        ExternalDBCredential.id == connection_id,
        ExternalDBCredential.user_id == current_user.id
    ).first()
    
    if not db_conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    db.delete(db_conn)
    db.commit()
    return {"message": "Connection deleted successfully"}