# from fastapi import FastAPI, Depends , HTTPException, status
# from sqlalchemy.orm import Session
# from models import User
# from database import Base,  engine
# from database import get_db
# from pydantic import BaseModel,EmailStr
# from uuid import uuid4
# from datetime import datetime, timedelta
# import hashlib
# from fastapi import Depends
# from auth import get_current_user
# from fastapi.security import OAuth2PasswordRequestForm
# from auth import authenticate_user, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, get_current_user,get_password_hash
# from routes.dbcredentials import router as db_router
# from schemas import UserCreate, UserLogin


# app=FastAPI()


# class UserCreate(BaseModel):
#     name: str
#     email: EmailStr
#     password: str  # plain password, we'll hash it later

# class UserLogin(BaseModel):
#     email:EmailStr
#     password: str


# @app.post("/users/")
# async def create_user(user: UserCreate, db: Session=Depends(get_db)):
#     #check user exists
#     db_user=db.query(User).filter(User.email==user.email).first()
#     if db_user:
#         raise HTTPException(status_code=400, detail="Email already registered")
#     # password_hash=hashlib.sha256(user.password.encode()).hexdigest()
#     password_hash=get_password_hash(user.password)


#     new_user=User(
#         id=uuid4(),
#         name=user.name,
#         email=user.email,
#         password_hash=password_hash,
#         created_at=datetime.now()
#     )
#     db.add(new_user)
#     db.commit()
#     db.refresh(new_user)

#     return {"id":new_user.id , "email": new_user.email}


# # @app.post("/login/")
# # async def login(user: UserLogin, db: Session =Depends(get_db)):
# #     db_user=db.query(User).filter(User.email==user.email).first()

# #     if not db_user:
# #         raise HTTPException(status_code=400, detail="Invalid email or password")
# #     password_hash=hashlib.sha256(user.password.encode()).hexdigest()

# #     if db_user.password_hash != password_hash:
# #         raise HTTPException(status_code=400, detail="Invalid email or password")
# #     return {"id": db_user.id,   "email":db_user.email}



# @app.post("/token")
# def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
#     user = authenticate_user(db, form_data.username, form_data.password)
#     if not user:
#         raise HTTPException(status_code=400, detail="Incorrect username or password")
    
#     access_token = create_access_token(
#         data={"sub": user.email},
#         expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
#     )
#     return {"access_token": access_token, "token_type": "bearer"}


# @app.get("/me")
# def read_me(current_user: User = Depends(get_current_user)):
#     return {"email": current_user.email, "id": current_user.id}



# app.include_router(db_router)




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
# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Database Connection Manager", version="1.0.0")

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

app.include_router(llm_router)

# @app.get("/")
# def root():
#     return {"message": "Database Connection Manager API"}

