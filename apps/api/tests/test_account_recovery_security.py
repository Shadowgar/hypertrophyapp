import asyncio
import json
import logging
import ssl

import pytest
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.config import Settings, settings
from app import emailer, main, security
from app.observability import logger
from app.schemas import PasswordResetRequestResponse


@pytest.mark.parametrize("key", ["", "change_me", "change_me_in_production", "CHANGE_ME" * 8, "short-test-key"])
def test_unsafe_signing_configuration_rejected_without_reflection(monkeypatch, key):
    config = Settings(_env_file=None, jwt_secret=key)
    with pytest.raises(RuntimeError, match="explicit non-placeholder") as error:
        config.validate_signing_configuration()
    if key:
        assert key not in str(error.value)
    monkeypatch.setattr(settings, "jwt_secret", key)
    for operation in (lambda: security.create_access_token("synthetic"), lambda: security.hash_password_reset_token("synthetic-reset-input")):
        with pytest.raises(RuntimeError, match="explicit non-placeholder"):
            operation()


@pytest.mark.parametrize("context", ["development", "test", "production"])
def test_explicit_safe_signing_configuration_works_in_every_context(monkeypatch, context):
    monkeypatch.setenv("ENVIRONMENT", context)
    config = Settings(_env_file=None, jwt_secret="explicit-synthetic-signing-key-000000000000")
    config.validate_signing_configuration()


def test_startup_rejects_unsafe_key_before_database_access(monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret", "change_me_in_production")
    calls = []
    monkeypatch.setattr(main.Base.metadata, "create_all", lambda **kwargs: calls.append(kwargs))
    with pytest.raises(RuntimeError, match="explicit non-placeholder"):
        with TestClient(main.app):
            pass
    assert calls == []


def _mail_config(**overrides):
    return Settings(_env_file=None, smtp_host="smtp.example.com", smtp_username="sender@example.com", smtp_password="synthetic-mail-credential", smtp_from_email="sender@example.com", **overrides)


@pytest.mark.parametrize("tls_failure", [False, True])
def test_verified_starttls_precedes_login_and_send(monkeypatch, tls_failure):
    calls = []
    class SMTP:
        def __init__(self, host, port, *, timeout):
            assert timeout == 10
            calls.append("connect")
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def starttls(self, *, context):
            assert isinstance(context, ssl.SSLContext)
            assert context.check_hostname
            assert context.verify_mode == ssl.CERT_REQUIRED
            calls.append("tls")
            if tls_failure:
                raise ssl.SSLCertVerificationError("synthetic-secret-provider-error")
        def login(self, *args):
            calls.append("login")
        def send_message(self, message):
            calls.append("send")
    monkeypatch.setattr(emailer.smtplib, "SMTP", SMTP)
    result = emailer.send_password_reset_email(to_email="recipient@example.com", reset_token="synthetic-reset-credential", config=_mail_config())
    assert result.sent is not tls_failure
    assert calls == (["connect", "tls"] if tls_failure else ["connect", "tls", "login", "send"])
    assert "synthetic-secret-provider-error" not in str(result)


@pytest.mark.parametrize("overrides", [
    {"smtp_use_tls": False}, {"password_reset_base_url": "http://example.com/reset"},
    {"password_reset_base_url": "https://[invalid"}, {"password_reset_base_url": "https://user:pass@example.com/reset"},
    {"smtp_timeout_seconds": float("inf")}, {"smtp_timeout_seconds": 0},
])
def test_unsafe_delivery_configuration_never_opens_transport(monkeypatch, overrides):
    def forbidden_transport(*args, **kwargs):
        pytest.fail("Unsafe delivery opened SMTP")
    monkeypatch.setattr(emailer.smtplib, "SMTP", forbidden_transport)
    result = emailer.send_password_reset_email(to_email="recipient@example.com", reset_token="synthetic-reset-credential", config=_mail_config(**overrides))
    assert result.sent is False


def test_response_schema_cannot_carry_a_credential():
    with pytest.raises(ValueError):
        PasswordResetRequestResponse(status="accepted", reset_token="synthetic-reset-credential")


@pytest.mark.parametrize("route,payload", [
    ("/auth/register", {"email": "invalid", "password": {"arbitrary": "private-sentinel"}, "name": "Synthetic"}),
    ("/auth/password-reset/confirm", {"token": ["private-sentinel"], "new_password": {"arbitrary": "private-sentinel"}}),
    ("/auth/login", {"email": {"arbitrary": "private-sentinel"}, "password": ["private-sentinel"]}),
])
def test_auth_validation_response_and_logs_never_reflect_input(monkeypatch, caplog, route, payload):
    monkeypatch.setattr(logger, "propagate", True)
    caplog.set_level(logging.WARNING, logger=logger.name)
    response = TestClient(main.app).post(route, json=payload)
    assert response.status_code == 422
    assert "private-sentinel" not in response.text
    assert "private-sentinel" not in caplog.text
    assert all(set(error) == {"loc", "type", "msg"} for error in response.json()["detail"])
    assert any("request_validation_failed" in record.message for record in caplog.records)


def test_nested_validation_metadata_cannot_bypass_redaction(monkeypatch, caplog):
    monkeypatch.setattr(logger, "propagate", True)
    caplog.set_level(logging.WARNING, logger=logger.name)
    marker = "private-sentinel"
    error = RequestValidationError([{"loc": ("body", marker, 0), "type": marker, "msg": marker, "ctx": {"reason": marker}, "input": {"nested": [marker]}}])
    request = Request({"type": "http", "path": "/auth/password-reset/confirm", "method": "POST", "headers": []})
    response = asyncio.run(main.handle_request_validation_error(request, error))
    assert marker not in response.body.decode()
    assert marker not in caplog.text
    assert json.loads(response.body)["detail"][0]["loc"] == ["body", "[field]", 0]


def test_auth_operation_error_never_reflects_exception_or_traceback(monkeypatch, caplog):
    monkeypatch.setattr(logger, "propagate", True)
    caplog.set_level(logging.WARNING, logger=logger.name)
    def fail(*args):
        raise RuntimeError("private-sentinel")
    monkeypatch.setattr(main.auth, "hash_password", fail)
    response = TestClient(main.app).post("/auth/register", json={"email": "error@example.com", "password": "Synthetic-password-1", "name": "Synthetic"})
    assert response.status_code == 500
    assert "private-sentinel" not in response.text
    assert "private-sentinel" not in caplog.text
    assert all(record.exc_info is None for record in caplog.records if record.name == logger.name)
