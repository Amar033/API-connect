# # app/schemas.py
# from pydantic import BaseModel, EmailStr
# from typing import Optional
# from uuid import UUID
# from datetime import datetime


# class UserCreate(BaseModel):
#     name: str
#     email: EmailStr
#     password: str  # plain password, we'll hash it later

# class User(BaseModel):
#     id: UUID
#     name: str
#     email: EmailStr
#     created_at: datetime

#     class Config:
#         orm_mode = True


# class ExternalDBCredentialCreate(BaseModel):
#     user_id: UUID
#     name: Optional[str]
#     db_owner_username: Optional[str]
#     host: str
#     port: int
#     dbname: str
#     db_user: str
#     db_password: str

# class ExternalDBCredential(BaseModel):
#     id: UUID
#     user_id: UUID
#     name: Optional[str]
#     db_owner_username: Optional[str]
#     host: str
#     port: int
#     dbname: str
#     db_user: str
#     db_password: str
#     created_at: datetime

#     class Config:
#         orm_mode = True

from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
from datetime import datetime

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    created_at: datetime

    class Config:
        from_attributes = True  # Updated for Pydantic v2

class ExternalDBCredentialCreate(BaseModel):
    name: Optional[str] = None
    db_owner_username: Optional[str] = None
    host: str
    port: int
    dbname: str
    db_user: str
    db_password: str

class ExternalDBCredential(BaseModel):
    id: UUID
    user_id: UUID
    name: Optional[str]
    db_owner_username: Optional[str]
    host: str
    port: int
    dbname: str
    db_user: str
    db_password: str
    created_at: datetime

    class Config:
        from_attributes = True  # Updated for Pydantic v2