
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models import ExternalDBCredential, User
from schemas import ExternalDBCredentialCreate, ExternalDBCredential as ExternalDBCredentialSchema
from database import get_db
from auth import get_current_user

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

@router.get("/", response_model=list[ExternalDBCredentialSchema])
def list_user_connections(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(ExternalDBCredential).filter(
        ExternalDBCredential.user_id == current_user.id
    ).all()

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