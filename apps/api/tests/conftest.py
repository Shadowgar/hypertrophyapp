from pathlib import Path
import sys
import os

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from test_db import configure_test_database, isolated_worker_database_url

worker_id = os.environ.get("PYTEST_XDIST_WORKER")
if worker_id:
    test_root = os.environ.get("CI_TEST_ROOT", "")
    worker_url = isolated_worker_database_url(os.environ.get("TEST_DATABASE_URL", ""), worker_id, test_root)
    os.environ["TEST_DATABASE_URL"] = worker_url
    os.environ["DATABASE_URL"] = worker_url
    os.environ["LOG_FILE_PATH"] = str(Path(test_root) / f"api-{worker_id}.log")

# Ensure DATABASE_URL is configured before any app module import, so focused runs
# don't accidentally bind to default Postgres when it's not available locally.
configure_test_database("pytest_session_default")
# An explicit synthetic signing key; runtime has no development fallback.
os.environ["JWT_SECRET"] = "isolated-api-test-signing-key-not-for-deployment-000"
