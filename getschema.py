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


def gettables():
    conn=None
    conn=get_db_connection()
    cur=conn.cursor()
    cur.execute("""
        SELECT table_name column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position;
;
    """)
    response=''
    for row in cur.fetchall():
        response+=str(row)
        # print(row)
    
    cur.close()
    conn.close()
    return response

gettables()

# cur.execute("""
#         SELECT table_name, column_name, data_type
#         FROM information_schema.columns
#         WHERE table_schema = 'public'
#         ORDER BY table_name, ordinal_position;
#     """)


    
