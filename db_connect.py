import os
import logging
import mysql.connector
from mysql.connector import pooling

logger = logging.getLogger("NeuralDefender.DB")

# Load a .env file if python-dotenv is available (optional convenience)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DB_CONFIG = {
    "host": os.environ.get("ND_DB_HOST", ""),
    "port": int(os.environ.get("ND_DB_PORT", "4000")),
    "user": os.environ.get("ND_DB_USER", ""),
    "password": os.environ.get("ND_DB_PASSWORD", ""),
    "database": os.environ.get("ND_DB_NAME", "antivirus_db"),
    "ssl_disabled": False,
}

_pool = None


def _get_pool():
    """Lazily create a connection pool so we don't reconnect on every scan."""
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="neural_defender_pool",
            pool_size=5,
            **DB_CONFIG,
        )
    return _pool


def get_signatures():
    """
    Fetch (type, signature) rows from the signatures table.
    Returns an empty list (not None) on failure, so callers can safely
    iterate the result without extra None-checks.
    """
    if not DB_CONFIG["host"] or not DB_CONFIG["user"]:
        logger.warning(
            "Database credentials are not configured. "
            "Set ND_DB_HOST, ND_DB_USER, ND_DB_PASSWORD, ND_DB_NAME env vars."
        )
        return []

    try:
        connection = _get_pool().get_connection()
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT type, signature FROM signatures")
            data = cursor.fetchall()
            cursor.close()
            return data
        finally:
            connection.close()  # returns the connection to the pool
    except mysql.connector.Error as err:
        logger.error("Database error: %s", err)
        return []


def test_connection() -> tuple[bool, str]:
    """Quick connectivity check used by the GUI's status indicator."""
    if not DB_CONFIG["host"] or not DB_CONFIG["user"]:
        return False, "Database not configured"
    try:
        connection = _get_pool().get_connection()
        connection.close()
        return True, "Connected"
    except mysql.connector.Error as err:
        return False, str(err)
