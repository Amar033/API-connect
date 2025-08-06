from fastapi import FastAPI, Request, HTTPException
from llmcall import response
import psycopg2
from psycopg2 import OperationalError
from pydantic import BaseModel
import logging

class UserInput (BaseModel):
    user_input :str


#DB connection 
DB_CONFIG={
    "dbname":"mydb",
    "user":"myuser",
    "password":"mypass",
    "host":"localhost",
    "port":"5432"
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection():
    """Create a new database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        logger.info("Database connection successful")
        return conn
    except OperationalError as e:
        logger.error(f"Database connection failed: {e}")
def test_db_connection():
    """Test if database connection works"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
            result = cur.fetchone()
        conn.close()
        return True, "Connection successful"
    except Exception as e:
        return False, str(e)


app=FastAPI(
    title="Database to LLM connector",
    description="API to connect normal human input to sql queries and show output",
    version="1.0.0"
)

@app.get("/")
async def root():
    return {"Message" : "API running"}

@app.get("/test-db")
async def test_database():
    """Test database connectivity"""
    success, message = test_db_connection()
    if success:
        return {"status": "success", "message": message}
    else:
        raise HTTPException(status_code=500, detail=f"Database test failed: {message}")



@app.post("/llm-chat")
async def llm_chat(user_input: str):
    try:
        sql_query = response(user_input=user_input)
        return {"sql": sql_query}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM processing failed: {str(e)}")


@app.post("/postgres")
async def root(user_input:str):
    try:
        query=response(user_input=user_input)
        logger.info(f"Generated SQL: {query}")
    except Exception as e:
        raise HTTPException(status_code=505,detail="LLM failes")
    conn=None
    try:
        conn=get_db_connection()
        with conn.cursor() as cur:
            cur.execute(query)

            if cur.description:
                columns=[desc[0] for desc in cur.description]
                rows=cur.fetchall()
                return {"sql":query,"columns":columns,"rows":rows}
            else:
                conn.commit()
                return {"sql":query,"status":"Executed Succesfully"}
    except Exception as e:
        return {"sql": query,"error":str(e)}
    finally:
        if conn:
            conn.close()
            