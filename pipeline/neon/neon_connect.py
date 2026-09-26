'''pipeline/neon/neon_connect.py '''
import os
import re
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, event
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)

from container import container

_TABLE_RE = re.compile(r'\bFROM\s+"?(\w+)"?', re.IGNORECASE)
#his regex is designed to extract a table name following a FROM clause in a SQL string. 
# Because your decorator intercepts before_cursor_execute, it receives a statement argument—which contains the raw SQL query text


# @event.listens_for is a built-in SQLAlchemy decorator used to hook custom logic into the database's lifecycle. 
#Instead of waiting for an application event (like a user logging in), 
# this decorator intercepts low-level database actions right as they are passing through SQLAlchemy.

def _attach_table_tracing(engine):
    @event.listens_for(engine, "before_cursor_execute")   #"before_cursor_execute" (The Hook): This is a specific core SQLAlchemy event. 
    #It fires immediately before a raw SQL query string is sent to the database driver (like psycopg2 or sqlite3)
    #The function you define right under @event.listens_for will run automatically every time a database query is executed
    def _log_tables(conn, cursor, statement, params, context, executemany):
        for match in _TABLE_RE.finditer(statement):
            container.record_table_read(match.group(1))
    return engine


def get_engine(branch: str = "production"):
    urls = {
        "production":  os.environ["DATABASE_URL"],
        "dev-testing": os.environ["DEV_DATABASE_URL"],
    }
    engine = create_engine(urls[branch])
    return _attach_table_tracing(engine)


def read_sql_table_traced(table_name, conn, **kwargs):
    """Drop-in replacement for pd.read_sql_table that also logs the read.
    read_sql_table bypasses before_cursor_execute's SQL text (it uses
    reflection), so it needs its own explicit log call."""
    container.record_table_read(table_name)
    return pd.read_sql_table(table_name, conn, **kwargs)