from fastapi import FastAPI, Request, HTTPException
from llmcall import response
import psycopg2
from psycopg2 import OperationalError
from pydantic import BaseModel
import logging
from dotenv import main
import os 
from getschema import get_db_connection
from pydantic import BaseModel
from typing import Optional
from psycopg2.extras import RealDictCursor



class ExternalDBCredentialsInput(BaseModel):
    company_name: str
    db_owner_username: Optional[str] = None
    host: str
    port: Optional[int] = 5432
    dbname: str
    db_user: str
    db_password: str

class UserQuery(BaseModel):
    company_name: str
    user_input: str

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


@app.post("/store-credentials")
async def store_credentials(data: ExternalDBCredentialsInput):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO ExternalDBCredentials (
                company_name,
                db_owner_username,
                host,
                port,
                dbname,
                db_user,
                db_password
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            data.company_name,
            data.db_owner_username,
            data.host,
            data.port,
            data.dbname,
            data.db_user,
            data.db_password
        ))
        conn.commit()
        return {"message": "Credentials stored successfully"}

    except Exception as e:
        if conn:
            conn.rollback()
        return {"error": str(e)}

    finally:
        if conn:
            conn.close()


@app.post("/postgres")
async def postgres(query_input:UserQuery):
    conn=None #local connection
    ext_conn=None
    query=None
    try :
        conn=get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM externaldbcredentials WHERE company_name = %s",
                (query_input.company_name,)
            )
            credentials = cur.fetchone()
            if not credentials:
                raise HTTPException(status_code=404, detail="Company not found")
        try:
            query=response(
                user_input=query_input.user_input,
                company_name=query_input.company_name
            )
            logger.info(f"Sql: {query}")
        except Exception as e:
            raise HTTPException(status_code=500,detail="LLM failed to generate SQL")
        

        external_conn = psycopg2.connect(
            host=credentials["host"],
            port=credentials["port"],
            dbname=credentials["dbname"],
            user=credentials["db_user"],
            password=credentials["db_password"]
        )
        with external_conn.cursor() as cur:
            cur.execute(query)
            if cur.description:
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
                return {
                    "sql": query,
                    "columns": columns,
                    "rows": rows
                }
            else:
                external_conn.commit()
                return {
                    "sql": query,
                    "status": "Executed Successfully"
                }

    except Exception as e:
        return {
            "sql": query,
            "error": str(e)
        }

    finally:
        if conn:
            conn.close()
        if ext_conn:
            ext_conn.close()
        




# @app.post("/postgres")
# async def postgres(user_input:str):
#     try:
#         query=response(user_input=user_input)
#         logger.info(f"Generated SQL: {query}")
#     except Exception as e:
#         raise HTTPException(status_code=505,detail="LLM failes")
#     conn=None
#     try:
#         conn=get_db_connection()
#         with conn.cursor() as cur:
#             cur.execute(query)

#             if cur.description:
#                 columns=[desc[0] for desc in cur.description]
#                 rows=cur.fetchall()
#                 return {"sql":query,"columns":columns,"rows":rows}
#             else:
#                 conn.commit()
#                 return {"sql":query,"status":"Executed Succesfully"}
#     except Exception as e:
#         return {"sql": query,"error":str(e)}
#     finally:
#         if conn:
#             conn.close()
            