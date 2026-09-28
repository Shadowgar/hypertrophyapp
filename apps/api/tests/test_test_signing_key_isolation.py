import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize("inherited_key", [
    "synthetic-inherited-signing-key-not-for-deployment-000",
    "change_me_synthetic-inherited-placeholder-not-for-deployment-000",
])
def test_test_setup_replaces_inherited_key_before_settings_and_security_imports(tmp_path, inherited_key):
    conftest = Path(__file__).with_name("conftest.py")
    database_url = f"sqlite:///{tmp_path / 'isolated.sqlite3'}"
    environment = {
        "PATH": os.defpath,
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
        "DATABASE_URL": database_url,
        "TEST_DATABASE_URL": database_url,
        "JWT_SECRET": inherited_key,
    }
    probe = '''
import os
import runpy
import sys

assert "app.config" not in sys.modules
assert "app.security" not in sys.modules
inherited_key = os.environ["JWT_SECRET"]
runpy.run_path(sys.argv[1])
assert "app.config" not in sys.modules
assert "app.security" not in sys.modules

from app.config import settings
from app.security import create_access_token
import jwt

test_key = "isolated-api-test-signing-key-not-for-deployment-000"
assert os.environ["JWT_SECRET"] == test_key
assert settings.jwt_secret == test_key
token = create_access_token("synthetic-subject")
assert jwt.decode(token, test_key, algorithms=[settings.jwt_algorithm])["sub"] == "synthetic-subject"
try:
    jwt.decode(token, inherited_key, algorithms=[settings.jwt_algorithm])
except jwt.InvalidSignatureError:
    pass
else:
    raise AssertionError("Test token was signed using the inherited key")
'''
    result = subprocess.run(
        [sys.executable, "-c", probe, str(conftest)],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
