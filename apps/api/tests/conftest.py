from pathlib import Path
import sys
import os

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from test_db import configure_test_database

# Ensure DATABASE_URL is configured before any app module import, so focused runs
# don't accidentally bind to default Postgres when it's not available locally.
configure_test_database("pytest_session_default")
# An explicit synthetic signing key; runtime has no development fallback.
os.environ["JWT_SECRET"] = "isolated-api-test-signing-key-not-for-deployment-000"
