from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from models import User
from database import Base, engine, get_db
from schemas import UserCreate, UserLogin  # Add missing imports
from uuid import uuid4
from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordRequestForm
from auth import (
    authenticate_user, 
    create_access_token, 
    ACCESS_TOKEN_EXPIRE_MINUTES, 
    get_current_user,
    get_password_hash
)
from routes.dbcredentials import router as db_router
from routes.llm import router as llm_router
from routes.llmchat import router as llm_chat_router
from fastapi.middleware.cors import CORSMiddleware
# from cache import create_vector_index
# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Database Connection Manager", version="1.0.0")

origins = [
    "http://localhost:3000", # The origin of your Next.js app
    "http://localhost:8000",
    "http://localhost:3001", 
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# create_vector_index()

@app.post("/users/", status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    # Check if user exists
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Email already registered"
        )
    
    # Hash password
    password_hash = get_password_hash(user.password)
    
    # Create new user
    new_user = User(
        name=user.name,
        email=user.email,
        password_hash=password_hash,
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "id": new_user.id, 
        "email": new_user.email,
        "message": "User created successfully"
    }

@app.post("/token")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/me")
def read_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "created_at": current_user.created_at
    }

# Include routers
app.include_router(db_router)


app.include_router(llm_chat_router)

