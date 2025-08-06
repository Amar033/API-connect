from fastapi import FastAPI, Request, HTTPException
from llmcall import response
import psycopg2
from psycopg2 import OperationalError
from pydantic import BaseModel
import logging
from dotenv import main
import os 
from getschema import get_db_connection

main.load_dotenv()
DB_CONFIG=os.getenv("DB_CONFIG")


class UserInput (BaseModel):
    user_input :str

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app=FastAPI(
    title="Database to LLM connector",
    description="API to connect normal human input to sql queries and show output",
    version="1.0.0"
)


@app.get("/db-schema")
async def dbschema():
    return {"Test"}



@app.post("/postgres")
async def postgres(user_input:str):
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
            