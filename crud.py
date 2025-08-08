from sqlalchemy.orm import Session 
import models, schemas
import uuid
from datetime import datetime
from passlib.context import CryptContext

pwd_context=CryptContext(schemes=["bcrypt"],deprecated="auto")

def get_password_hash(password: str)-> str:
    return pwd_context.hash(password)

def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        id=uuid.uuid4(),
        name=user.name,
        email=user.email,
        hashed_password=hashed_password,
        created_at=datetime.utcnow()
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user_by_email(db:Session, email:str)->models.User | None:
    return db.query(models.User).filter(models.User.email==email).first()

def get_user(db:Session, user_id : uuid.UUID)-> models.User | None:
    return db.query(models.User).filter(models.User.id==user_id).first()

def create_external_db_credential(
    db: Session, cred: schemas.ExternalDBCredentialCreate
) -> models.ExternalDBCredential:
    db_cred = models.ExternalDBCredential(
        id=uuid.uuid4(),
        user_id=cred.user_id,
        name=cred.name,
        db_owner_username=cred.db_owner_username,
        host=cred.host,
        port=cred.port,
        dbname=cred.dbname,
        db_user=cred.db_user,
        db_password=cred.db_password,
        created_at=datetime.now()
    )
    db.add(db_cred)
    db.commit()
    db.refresh(db_cred)
    return db_cred

def get_credentials_by_user (db:Session, user_id=uuid.UUID):
    return db.query(models.ExternalDBCredential).filter(models.ExternalDBCredential.user_id==user_id).all()