from dotenv import main
import os 
import logging
import psycopg2 
from psycopg2 import OperationalError


main.load_dotenv()

DB_CONFIG = {
    'host': os.getenv('PG_HOST'),
    'port': os.getenv('PG_PORT'),
    'dbname': os.getenv('PG_DB'),
    'user': os.getenv('PG_USER'),
    'password': os.getenv('PG_PASS')
}


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection(config:dict =DB_CONFIG):
    """Create a new database connection"""
    try:
        conn = psycopg2.connect(**config)
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

def get_schema(conn):
    "Retrieve schema"
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name, column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public'
                ORDER BY table_name, ordinal_position;
            """)
            rows=cur.fetchall()
        return "\n".join(str(row) for row in rows)
    except Exception as e:
        logger.error(f"Error fetching Schema:{e}")
        return f"Error:{e}"
    finally:
        conn.close()


def get_local_db_schema():
    """Get schema of the local database"""
    conn = get_db_connection()
    if not conn:
        return "Local DB connection failed."
    return get_schema(conn)


def get_external_db_schema_by_company(company_name: str):
    """
    Fetch schema of external DB using company_name stored in local table `externaldbcredentials`
    """
    local_conn = get_db_connection()
    if not local_conn:
        return "Failed to connect to local DB."

    try:
        with local_conn.cursor() as cur:
            cur.execute("""
                SELECT host, port, dbname, db_user, db_password 
                FROM externaldbcredentials 
                WHERE company_name = %s;
            """, (company_name,))
            row = cur.fetchone()
            if not row:
                return f"No credentials found for company: {company_name}"

            # Extract external DB config
            host, port, dbname, user, password = row
            external_config = {
                'host': host,
                'port': port,
                'dbname': dbname,
                'user': user,
                'password': password
            }

            external_conn = get_db_connection(external_config)
            if not external_conn:
                return f"Failed to connect to external DB for {company_name}"

            return get_schema(external_conn)

    except Exception as e:
        logger.error(f"Error querying externaldbcredentials: {e}")
        return f"Error: {e}"
    finally:
        local_conn.close()

def gettables(company_name: str = None):
    if company_name:
        return get_external_db_schema_by_company(company_name)
    else:
        return get_local_db_schema()


# cur.execute("""
#         SELECT table_name, column_name, data_type
#         FROM information_schema.columns
#         WHERE table_schema = 'public'
#         ORDER BY table_name, ordinal_position;
#     """)


    
