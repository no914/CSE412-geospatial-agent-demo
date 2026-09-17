import os

import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("DB_NAME", "geospatial_demo"),
    "user": os.getenv("DB_USER", "agent_ro"),
    "password": os.getenv("DB_PASSWORD", ""),
}

STATEMENT_TIMEOUT_MS = 5000


def get_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    with conn.cursor() as cur:
        cur.execute("SET statement_timeout = %s", (STATEMENT_TIMEOUT_MS,))
    return conn


def run_query(sql, params=None, max_rows=100):
    """Run one query and return (column_names, rows)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchmany(max_rows)
            return columns, rows
    finally:
        conn.close()
