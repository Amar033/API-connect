from sqlalchemy import Column,String, Text,Integer,TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from database import Base

class User(Base):
    __tablename__="users"


    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())


class ExternalDBCredential(Base):
    __tablename__ = "external_db_credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(100))
    db_owner_username = Column(String(100))
    host = Column(Text, nullable=False)
    port = Column(Integer, nullable=False)
    dbname = Column(Text, nullable=False)
    db_user = Column(Text, nullable=False)
    db_password = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())