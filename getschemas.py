# Updated getschema.py
from dotenv import load_dotenv
import os
import logging
import psycopg2
from psycopg2 import OperationalError
from typing import Optional, Dict, List, Tuple
from models import ExternalDBCredential

load_dotenv()

# Local DB config for FastAPI app's database
LOCAL_DB_CONFIG = {
    'host': os.getenv('PG_HOST'),
    'port': os.getenv('PG_PORT'),
    'dbname': os.getenv('PG_DB'),
    'user': os.getenv('PG_USER'),
    'password': os.getenv('PG_PASS')
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection(config: dict = LOCAL_DB_CONFIG):
    """Create a new database connection"""
    if config is None:
        config = LOCAL_DB_CONFIG
    try:
        conn = psycopg2.connect(**config)
        logger.info("Database connection successful")
        return conn
    except OperationalError as e:
        logger.error(f"Database connection failed: {e}")
        return None

def get_detailed_schema(conn) -> Dict[str, List[Dict]]:
    """Retrieve detailed schema information organized by tables"""
    if conn is None:
        return {"error": "No connection provided"}
    
    try:
        with conn.cursor() as cur:
            # Get tables with their columns, data types, and constraints
            cur.execute("""
                SELECT 
                    t.table_name,
                    c.column_name,
                    c.data_type,
                    c.is_nullable,
                    c.column_default,
                    CASE 
                        WHEN pk.column_name IS NOT NULL THEN 'PRIMARY KEY'
                        WHEN fk.column_name IS NOT NULL THEN 'FOREIGN KEY'
                        ELSE ''
                    END as key_type,
                    fk.foreign_table_name,
                    fk.foreign_column_name
                FROM information_schema.tables t
                LEFT JOIN information_schema.columns c ON t.table_name = c.table_name
                LEFT JOIN (
                    SELECT ku.table_name, ku.column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage ku
                        ON tc.constraint_name = ku.constraint_name
                    WHERE tc.constraint_type = 'PRIMARY KEY'
                ) pk ON c.table_name = pk.table_name AND c.column_name = pk.column_name
                LEFT JOIN (
                    SELECT 
                        ku.table_name, ku.column_name,
                        ccu.table_name AS foreign_table_name,
                        ccu.column_name AS foreign_column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage ku
                        ON tc.constraint_name = ku.constraint_name
                    JOIN information_schema.constraint_column_usage ccu
                        ON tc.constraint_name = ccu.constraint_name
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                ) fk ON c.table_name = fk.table_name AND c.column_name = fk.column_name
                WHERE t.table_schema = 'public' AND t.table_type = 'BASE TABLE'
                ORDER BY t.table_name, c.ordinal_position;
            """)
            
            rows = cur.fetchall()
            schema = {}
            
            for row in rows:
                table_name = row[0]
                if table_name not in schema:
                    schema[table_name] = []
                
                column_info = {
                    'column_name': row[1],
                    'data_type': row[2],
                    'is_nullable': row[3],
                    'column_default': row[4],
                    'key_type': row[5],
                    'foreign_table': row[6],
                    'foreign_column': row[7]
                }
                schema[table_name].append(column_info)
            
            return schema
            
    except Exception as e:
        logger.error(f"Error fetching schema: {e}")
        return {"error": str(e)}
    finally:
        if conn:
            conn.close()

def get_sample_data(conn, table_name: str, limit: int = 3) -> List[Tuple]:
    """Get sample data from a table to help LLM understand data patterns"""
    if conn is None:
        return []
    
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT * FROM {table_name} LIMIT %s", (limit,))
            return cur.fetchall()
    except Exception as e:
        logger.error(f"Error fetching sample data from {table_name}: {e}")
        return []

def get_external_db_connection(db_credential: ExternalDBCredential):
    """Create connection to external database using ExternalDBCredential model"""
    external_config = {
        'host': db_credential.host,
        'port': db_credential.port,
        'dbname': db_credential.dbname,
        'user': db_credential.db_user,
        'password': db_credential.db_password
    }
    return get_db_connection(external_config)

def get_user_database_schemas(user_db_credentials: List[ExternalDBCredential]) -> Dict[str, Dict]:
    """Get schemas for all databases accessible to the authenticated user"""
    user_schemas = {}
    
    for credential in user_db_credentials:
        conn = get_external_db_connection(credential)
        if conn:
            schema = get_detailed_schema(conn)
            user_schemas[credential.name or f"DB_{credential.id}"] = {
                'schema': schema,
                'connection_info': {
                    'host': credential.host,
                    'port': credential.port,
                    'dbname': credential.dbname,
                    'name': credential.name
                }
            }
        else:
            user_schemas[credential.name or f"DB_{credential.id}"] = {
                'error': 'Connection failed'
            }
    
    return user_schemas

def format_schema_for_llm(schema_dict: Dict[str, Dict]) -> str:
    """Format schema information in a way that's optimal for LLM understanding"""
    formatted_schema = "DATABASE SCHEMAS AVAILABLE TO USER:\n\n"
    
    for db_name, db_info in schema_dict.items():
        if 'error' in db_info:
            formatted_schema += f"❌ {db_name}: {db_info['error']}\n\n"
            continue
            
        formatted_schema += f"📊 DATABASE: {db_name}\n"
        if 'connection_info' in db_info:
            conn_info = db_info['connection_info']
            formatted_schema += f"   Host: {conn_info['host']}:{conn_info['port']}\n"
            formatted_schema += f"   Database: {conn_info['dbname']}\n\n"
        
        schema = db_info.get('schema', {})
        if not schema:
            formatted_schema += "   No tables found.\n\n"
            continue
            
        formatted_schema += "   TABLES:\n"
        for table_name, columns in schema.items():
            formatted_schema += f"   📋 {table_name}:\n"
            for col in columns:
                key_info = f" ({col['key_type']})" if col['key_type'] else ""
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                formatted_schema += f"      • {col['column_name']}: {col['data_type']} {nullable}{key_info}\n"
                
                if col['foreign_table']:
                    formatted_schema += f"        ↳ References {col['foreign_table']}.{col['foreign_column']}\n"
            formatted_schema += "\n"
    
    return formatted_schema