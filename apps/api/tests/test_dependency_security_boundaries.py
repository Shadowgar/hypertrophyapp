"""Compatibility checks for patched authentication and request parsing dependencies."""

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.config import settings
from app.main import app
from app.security import create_access_token


def _claims(**overrides):
    return {
        "sub": "synthetic-user",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        **overrides,
    }


def _malformed_tokens():
    secret = settings.jwt_secret
    # This depth exceeds the JSON decoder's own nesting limit on the test runtime.
    nested_payload = b'{"sub":"synthetic-user","exp":9999999999,"nested":' + b"[" * 50_000 + b"0" + b"]" * 50_000 + b"}"
    return {
        "wrong signature": jwt.encode(_claims(), "different-synthetic-test-signing-key-000", algorithm="HS256"),
        "wrong algorithm": jwt.encode(_claims(), secret, algorithm="HS384"),
        "expired": jwt.encode(_claims(exp=datetime.now(timezone.utc) - timedelta(minutes=1)), secret, algorithm="HS256"),
        "malformed": "not-a-jwt",
        "oversized": "x" * 20_000,
        "detached payload": jwt.api_jws.PyJWS().encode(
            b'{"sub":"synthetic-user"}', secret, algorithm="HS256", headers={"b64": False}, is_payload_detached=True
        ),
        "deeply nested payload": jwt.api_jws.PyJWS().encode(nested_payload, secret, algorithm="HS256"),
    }


@pytest.mark.parametrize("case", [
    "wrong signature", "wrong algorithm", "expired", "malformed", "oversized",
    "detached payload", "deeply nested payload",
])
def test_invalid_bearer_tokens_fail_closed(case):
    response = TestClient(app).get(
        "/profile", headers={"Authorization": f"Bearer {_malformed_tokens()[case]}"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token"


def test_valid_token_still_decodes_with_configured_algorithm():
    token = create_access_token("synthetic-user")
    assert jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])["sub"] == "synthetic-user"


def test_malformed_host_cannot_change_auth_route_path():
    request = Request({
        "type": "http", "scheme": "http", "server": ("testserver", 80),
        "path": "/auth/login", "root_path": "", "query_string": b"",
        "headers": [(b"host", b"attacker.invalid/?/not-auth")],
    })
    assert request.url.path == "/auth/login"
