"""
Database Helper Module for EDSDEVV
Provides context manager for safe database connection handling
"""

from contextlib import contextmanager
import threading
import time
import psycopg2
import os

# Get database URL from environment or fallback to default
external_database_url = os.getenv(
    'DATABASE_URL',
    "postgresql://connectlinkdata_user:RsYLVxq6lzCBXV7m3e2drdiNMebYBFIC@dpg-d4m0bqggjchc73avg3eg-a.oregon-postgres.render.com/connectlinkdata"
)

# ---------------------------------------------------------------------------
# Connection pooling
# ---------------------------------------------------------------------------
# Opening a fresh connection to the remote (Render) Postgres costs ~3s per
# request (TLS handshake + cross-continent round trip). Pages like the HR
# dashboard fire many requests on load, each opening its own connection,
# which is the main cause of slow page loads. This small pool reuses up to
# DB_POOL_MAX warm connections across requests and never blocks (it falls
# back to a direct connection when the pool is busy), so N requests cost
# ~1 connect, not N.
# ---------------------------------------------------------------------------

DB_POOL_MAX = int(os.getenv('DB_POOL_MAX', '3'))
# Connections idle longer than this are liveness-probed before reuse
POOL_IDLE_PROBE_SECONDS = 15

_pool_lock = threading.Lock()
_idle = []          # warm, idle psycopg2 connections ready for reuse as (conn, last_used_ts)
_total = 0          # number of pool-managed connections currently created


def _connect():
    return psycopg2.connect(
        external_database_url,
        connect_timeout=10,
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=3,
        # Set the Zimbabwe timezone once at connect time so every request on the
        # connection sees local time without a per-request SET TIME ZONE round trip.
        options='-c timezone=Africa/Harare',
    )


def _checkout():
    """Return (connection, pooled) preferring a warm pooled connection.

    pooled=True means the connection is pool-managed and must be returned via
    _checkin; pooled=False means it is a temporary direct connection that must
    be closed. Never blocks: if the pool is full, a temporary connection is
    created so callers cannot deadlock. A pooled connection is only liveness-
    probed if it has been idle longer than POOL_IDLE_PROBE_SECONDS, so bursts
    of back-to-back requests skip the probe round trip.
    """
    global _total
    conn = None
    pooled = False
    ts = 0.0
    with _pool_lock:
        if _idle:
            conn, ts = _idle.pop()
            pooled = True
        elif _total < DB_POOL_MAX:
            try:
                conn = _connect()
                _total += 1
                pooled = True
            except Exception:
                conn = None
    if conn is None:
        conn = _connect()
        pooled = False
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
            return conn, pooled
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            return _connect(), False

    if not pooled or (time.time() - ts) > POOL_IDLE_PROBE_SECONDS:
        # Probe (or replace) a possibly-stale connection
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
            return conn, pooled
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            if pooled:
                with _pool_lock:
                    _total = max(0, _total - 1)
            fresh = _connect()
            return fresh, False
    return conn, pooled


def _checkin(conn, pooled):
    """Return a connection to the pool (or close it if temporary/overflow)."""
    if conn is None:
        return
    if not pooled:
        try:
            conn.close()
        except Exception:
            pass
        return
    with _pool_lock:
        if len(_idle) < DB_POOL_MAX:
            _idle.append((conn, time.time()))
            return
    # pool already full -> close and free a slot
    try:
        conn.close()
    except Exception:
        pass
    with _pool_lock:
        _total = max(0, _total - 1)


def _discard(conn, pooled):
    """Close a broken/poisoned connection and free its pool slot."""
    if conn is None:
        return
    try:
        conn.close()
    except Exception:
        pass
    if pooled:
        with _pool_lock:
            _total = max(0, _total - 1)


@contextmanager
def get_db():
    """
    Context manager for database connections.

    Uses a small connection pool to avoid the ~3s per-request connect cost.
    Yields a cursor and a connection; rolls back on error and always returns
    the connection to the pool (or closes it if broken).

    Usage:
        with get_db() as (cursor, connection):
            cursor.execute("SELECT * FROM table WHERE id = %s", (123,))
            result = cursor.fetchone()
            connection.commit()
    """
    connection = None
    cursor = None
    pooled = False
    broken = False
    try:
        # Timezone is applied once via connection options (-c timezone=Africa/Harare)
        connection, pooled = _checkout()
        cursor = connection.cursor()
        yield cursor, connection
    except Exception as e:
        broken = isinstance(e, (psycopg2.OperationalError, psycopg2.InterfaceError))
        if connection:
            try:
                connection.rollback()
            except Exception:
                broken = True
        raise e
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass  # Ignore errors during cursor close
        if connection:
            if not broken:
                try:
                    connection.rollback()
                except Exception:
                    broken = True
            if broken:
                _discard(connection, pooled)
            else:
                _checkin(connection, pooled)


@contextmanager
def get_db_cursor_only():
    """
    Simplified context manager that yields only cursor.

    Uses the shared connection pool (see get_db).

    Usage:
        with get_db_cursor_only() as cursor:
            cursor.execute("SELECT * FROM table")
            results = cursor.fetchall()

    Note: Remember to manually commit if doing writes!
    """
    connection = None
    cursor = None
    pooled = False
    broken = False
    try:
        # Timezone is applied once via connection options (-c timezone=Africa/Harare)
        connection, pooled = _checkout()
        cursor = connection.cursor()
        yield cursor
    except Exception as e:
        broken = isinstance(e, (psycopg2.OperationalError, psycopg2.InterfaceError))
        if connection:
            try:
                connection.rollback()
            except Exception:
                broken = True
        raise e
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        if connection:
            if not broken:
                try:
                    connection.rollback()
                except Exception:
                    broken = True
            if broken:
                _discard(connection, pooled)
            else:
                _checkin(connection, pooled)


def execute_query(query, params=None, fetch_one=False, fetch_all=False, commit=False):
    """
    Helper function for single queries (non-context-based).
    
    Args:
        query: SQL query string
        params: Tuple of parameters for the query
        fetch_one: If True, returns one result
        fetch_all: If True, returns all results
        commit: If True, commits the transaction
    
    Returns:
        Query result or None depending on fetch flags
    
    Example:
        result = execute_query("SELECT * FROM users WHERE id = %s", (1,), fetch_one=True)
    """
    with get_db() as (cursor, connection):
        cursor.execute(query, params or ())
        
        if fetch_one:
            result = cursor.fetchone()
        elif fetch_all:
            result = cursor.fetchall()
        else:
            result = None
        
        if commit:
            connection.commit()
        
        return result
