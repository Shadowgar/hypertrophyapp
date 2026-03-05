import os
import re
import socket
from pathlib import Path


def _postgres_is_reachable(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.6):
            return True
    except OSError:
        return False


def _sqlite_fallback_url(test_name: str) -> str:
    safe_name = re.sub(r"[^a-zA-Z0-9_.-]+", "_", test_name).strip("_") or "pytest"
    db_path = Path(__file__).resolve().parent / f".tmp_{safe_name}.sqlite3"
    return f"sqlite:///{db_path}"


def configure_test_database(test_name: str) -> str:
    """Set DATABASE_URL for tests with Postgres-first behavior.

    Override with TEST_DATABASE_URL for local one-off cases (including SQLite).
    """
    explicit_url = os.getenv("TEST_DATABASE_URL")
    if explicit_url:
        os.environ["DATABASE_URL"] = explicit_url
        return explicit_url

    host = os.getenv("TEST_DATABASE_HOST", os.getenv("DATABASE_HOST", os.getenv("POSTGRES_HOST", "localhost")))
    port = int(os.getenv("TEST_DATABASE_PORT", os.getenv("DATABASE_PORT", "5432")))
    name = os.getenv("TEST_DATABASE_NAME", os.getenv("POSTGRES_DB", "hypertrophy_test"))
    user = os.getenv("TEST_DATABASE_USER", os.getenv("POSTGRES_USER", "hypertrophy"))
    password = os.getenv("TEST_DATABASE_PASSWORD", os.getenv("POSTGRES_PASSWORD", "hypertrophy"))

    if _postgres_is_reachable(host, port):
        url = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{name}"
    else:
        url = _sqlite_fallback_url(test_name)

    os.environ["DATABASE_URL"] = url
    os.environ.setdefault("PYTEST_ACTIVE_TEST", test_name)
    return url
