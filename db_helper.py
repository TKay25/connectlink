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


# ---------------------------------------------------------------------------
# Production write guard
# ---------------------------------------------------------------------------
# This database is the LIVE one, shared with the deployed service. A developer
# machine, a one-off script or a health probe that opens it by accident must not
# be able to change it. On 2026-10-26 exactly that happened: a local run of the
# app executed the boot-time schema bootstrap, which re-asserted the branch seed
# and reset both shops' access codes, locking the tills out.
#
# A process counts as the DEPLOYMENT when its host says so (Render exports
# RENDER / RENDER_SERVICE_ID) or when APP_ENV / FLASK_ENV is "production".
# Any other process that points at the production database gets a READ-ONLY
# session: diagnostics still work, every write fails loudly instead of quietly
# succeeding. Set ALLOW_PROD_DB_WRITE=1 to authorise writes from such a process.
PRODUCTION_DB_HOST_MARKER = os.getenv('PRODUCTION_DB_HOST_MARKER', 'render.com')


def is_deployment_process():
    """True when this process *is* the deployed service (not a laptop)."""
    if os.getenv('RENDER') or os.getenv('RENDER_SERVICE_ID'):
        return True
    return str(os.getenv('APP_ENV', '')).strip().lower() == 'production' \
        or str(os.getenv('FLASK_ENV', '')).strip().lower() == 'production'


def points_at_production_database():
    marker = (PRODUCTION_DB_HOST_MARKER or '').strip()
    return bool(marker) and marker in external_database_url


def production_writes_allowed():
    """Whether THIS process may change the live database."""
    if is_deployment_process():
        return True
    return str(os.getenv('ALLOW_PROD_DB_WRITE', '')).strip().lower() in ('1', 'true', 'yes', 'on')


def schema_writes_allowed():
    """Whether THIS process may run the boot-time schema migrations and seeds."""
    return production_writes_allowed()


def _connect():
    options = '-c timezone=Africa/Harare'
    readonly = points_at_production_database() and not production_writes_allowed()
    if readonly:
        # Reads (branch codes, project rows, diagnostics) keep working; any
        # INSERT/UPDATE/DELETE/DDL raises "cannot execute ... in a read-only
        # transaction" instead of silently changing live data.
        options += ' -c default_transaction_read_only=on'
    return psycopg2.connect(
        external_database_url,
        connect_timeout=10,
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=3,
        # Set the Zimbabwe timezone once at connect time so every request on the
        # connection sees local time without a per-request SET TIME ZONE round trip.
        options=options,
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

    if pooled and ts != 0.0:
        # Liveness-probe every reused pooled connection before handing it out.
        # Render/cloud Postgres can silently drop an idle SSL connection, which
        # otherwise surfaces later as "SSL connection has been closed unexpectedly"
        # inside request code. One cheap SELECT 1 beats a 500 error.
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
            with _pool_lock:
                _total = max(0, _total - 1)
            fresh = _connect()
            return fresh, False
    return conn, pooled


def _checkin(conn, pooled):
    """Return a connection to the pool (or close it if temporary/overflow)."""
    global _total
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
    global _total
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
