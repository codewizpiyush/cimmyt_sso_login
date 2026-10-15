"""SSO PostgreSQL Database Manager."""
from contextlib import contextmanager
import logging
from pathlib import Path
from typing import Generator

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

from app.config import settings

logger = logging.getLogger(__name__)

_pool: pool.ThreadedConnectionPool = None


def init_pool() -> None:
    """Initialize the PostgreSQL connection pool."""
    global _pool
    if _pool is not None:
        return

    logger.info("Initializing SSO Postgres pool -> %s:%s/%s", 
                settings.db_host, settings.db_port, settings.db_name)
    _pool = pool.ThreadedConnectionPool(
        minconn=settings.db_pool_min,
        maxconn=settings.db_pool_max,
        host=settings.db_host,
        port=settings.db_port,
        dbname=settings.db_name,
        user=settings.db_user,
        password=settings.db_password,
    )


def close_pool() -> None:
    """Close all connections in the pool."""
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None


@contextmanager
def transaction() -> Generator[psycopg2.extensions.cursor, None, None]:
    """Execute within a managed database transaction."""
    global _pool
    if _pool is None:
        init_pool()

    conn = _pool.getconn()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)


def init_db() -> None:
    """Execute schema.sql to ensure all PostgreSQL tables exist."""
    schema_file = Path(__file__).parent / "schema.sql"
    with open(schema_file, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    with transaction() as cur:
        cur.execute(schema_sql)
    logger.info("SSO PostgreSQL tables verified successfully.")
