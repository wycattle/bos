'''pipeline/neon/neon_connect.py '''
"""
Neon (Postgres) connection helpers.

- get_engine(): builds a SQLAlchemy engine from DATABASE_URL and attaches
  table-read tracing to it.
- read_sql_table_traced(): drop-in for pd.read_sql_table that logs the read.

DATABASE_URL comes from the environment. In a Modal container that is the
'neon-credentials' secret. Locally it comes from the shell, or from .env if
the shell doesn't set it (load_dotenv uses override=False).
"""
import hashlib
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

_url_fingerprint_printed = False  # TEMPORARY: print the fingerprint once per process


def _print_url_fingerprint(url: str) -> None:
    """TEMPORARY auth diagnostic. Prints a non-secret fingerprint of DATABASE_URL
    (length, short sha256, head/tail, host) so the Modal container's value can be
    compared with the local .env value. The password itself is never printed.
    Remove once the auth problem is solved."""
    global _url_fingerprint_printed
    if _url_fingerprint_printed:
        return
    _url_fingerprint_printed = True
    host = url.split("@")[-1].split("/")[0]
    print("DBURL len:", len(url),
          "sha:", hashlib.sha256(url.encode()).hexdigest()[:8],
          "head:", repr(url[:22]),
          "tail:", repr(url[-10:]),
          "host:", host)


# @event.listens_for is a built-in SQLAlchemy decorator used to hook custom logic into the database's lifecycle. 
#Instead of waiting for an application event (like a user logging in), 
# this decorator intercepts low-level database actions right as they are passing through SQLAlchemy.

def _attach_table_tracing(engine):
    """Attach a before_cursor_execute listener that records every table read
    (parsed from the SQL text) with container.record_table_read. Returns the engine."""
    @event.listens_for(engine, "before_cursor_execute")   #"before_cursor_execute" (The Hook): This is a specific core SQLAlchemy event. 
    #It fires immediately before a raw SQL query string is sent to the database driver (like psycopg2 or sqlite3)
    #The function you define right under @event.listens_for will run automatically every time a database query is executed
    def _log_tables(conn, cursor, statement, params, context, executemany):
        for match in _TABLE_RE.finditer(statement):
            container.record_table_read(match.group(1))
    return engine


def get_engine(branch: str = "production"):
    """Return a traced SQLAlchemy engine for the given branch.

    Only "production" exists; it reads DATABASE_URL from the environment.
    Raises KeyError if DATABASE_URL is unset, ValueError for an unknown branch.
    """
    url = os.environ["DATABASE_URL"]
    _print_url_fingerprint(url)  # TEMPORARY, see above

    urls = {
        "production": url,
    }
    if branch not in urls:
        raise ValueError(f"Unknown branch {branch!r}; expected one of {sorted(urls)}")

    engine = create_engine(urls[branch])
    return _attach_table_tracing(engine)


def read_sql_table_traced(table_name, conn, **kwargs):
    """Drop-in replacement for pd.read_sql_table that also logs the read.
    read_sql_table bypasses before_cursor_execute's SQL text (it uses
    reflection), so it needs its own explicit log call."""
    container.record_table_read(table_name)
    return pd.read_sql_table(table_name, conn, **kwargs)