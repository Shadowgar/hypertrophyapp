"""Real account lifecycle after operator reset on the explicitly restored clone.

This test never chooses a database itself. Ordinary CI skips it; the documented
PostgreSQL rehearsal supplies the verified disposable receipt and explicit URL.
"""
from datetime import datetime, timedelta, timezone
import importlib.util
import os
from pathlib import Path
import json
import subprocess

import pytest


@pytest.mark.skipif(not os.environ.get("RESET_REHEARSAL_RECEIPT"), reason="Requires verified disposable reset rehearsal")
def test_old_credentials_cannot_access_same_email_new_identity_after_reset():
    root = Path(__file__).resolve().parents[3]
    spec = importlib.util.spec_from_file_location("reset_for_auth_rehearsal", root / "scripts/reset_user_data.py")
    reset = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reset)
    receipt = reset.read_private(os.environ["RESET_REHEARSAL_RECEIPT"])
    target = receipt["target"]
    assert target["kind"] == "disposable"
    reset.verify_target(target)

    from sqlalchemy.engine import make_url
    from test_db import configure_test_database
    url = make_url(configure_test_database("test_clean_start_reset"))
    container = json.loads(subprocess.check_output(["docker", "inspect", target["container"]]))[0]
    assert url.host == "127.0.0.1" and url.database == target["database"] and url.username == target["role"]
    assert container["HostConfig"]["PortBindings"]["5432/tcp"] == [{"HostIp":"127.0.0.1", "HostPort":str(url.port)}]
    assert all(t["count"] == 0 for t in reset.capture(target)["tables"] if t["table"] in reset.DELETE)

    # Imports/startup are allowed only after the exact disposable engine target
    # and its empty state have been verified above.
    from fastapi.testclient import TestClient
    import jwt
    from app.main import app
    from app.config import settings
    from app.database import SessionLocal
    from app.models import PasswordResetToken, User
    from app.security import hash_password_reset_token

    client = TestClient(app)
    email = "clean-start-rehearsal@example.com"
    password = "Synthetic-rehearsal-credential-428!"
    created = client.post("/auth/register", json={"email":email,"password":password,"name":"Before reset"})
    assert created.status_code == 200
    old_token = created.json()["access_token"]
    old_id = jwt.decode(old_token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])["sub"]
    old_headers = {"Authorization":"Bearer " + old_token}
    assert client.get("/profile", headers=old_headers).status_code == 200
    old_legacy = jwt.encode({"sub":old_id,"exp":datetime.now(timezone.utc)+timedelta(hours=1)},
                           settings.jwt_secret, algorithm=settings.jwt_algorithm)
    reset_token = "synthetic-reset-credential-no-mail"
    with SessionLocal() as db:
        db.add(PasswordResetToken(user_id=old_id, token_hash=hash_password_reset_token(reset_token),
                                  expires_at=datetime.now(timezone.utc).replace(tzinfo=None)+timedelta(minutes=30)))
        db.commit()

    inventory = reset.capture(target)
    reset.sql(target, reset.deletion_sql(target, inventory), readonly=False)
    empty = reset.capture(target)
    assert all(t["count"] == 0 for t in empty["tables"] if t["table"] in reset.DELETE)
    assert empty["schema_sha256"] == inventory["schema_sha256"]
    assert client.get("/profile", headers=old_headers).status_code == 401

    fresh = client.post("/auth/register", json={"email":email,"password":password,"name":"Fresh account"})
    assert fresh.status_code == 200
    token = fresh.json()["access_token"]
    new_id = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])["sub"]
    assert new_id != old_id
    assert client.get("/profile", headers={"Authorization":"Bearer " + token}).json()["name"] == "Fresh account"
    assert client.get("/profile", headers=old_headers).status_code == 401
    assert client.get("/profile", headers={"Authorization":"Bearer " + old_legacy}).status_code == 401
    assert client.post("/auth/password-reset/confirm", json={"token":reset_token,"new_password":"Another-synthetic-pass-32!"}).status_code == 400
    with SessionLocal() as db:
        assert db.query(User).count() == 1
        assert db.query(PasswordResetToken).count() == 0
        assert db.query(User).filter(User.id == old_id).first() is None
    # Leave only this explicitly disposable fixture clean for later rehearsal.
    reset.sql(target, reset.deletion_sql(target, reset.capture(target)), readonly=False)
