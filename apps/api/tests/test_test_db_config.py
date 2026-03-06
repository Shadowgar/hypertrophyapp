import os

import test_db
from test_db import configure_test_database


def test_configure_test_database_uses_explicit_override(monkeypatch) -> None:
    explicit = "sqlite:///./explicit_override.sqlite3"
    monkeypatch.setenv("TEST_DATABASE_URL", explicit)

    url = configure_test_database("explicit_case")

    assert url == explicit
    assert os.environ["DATABASE_URL"] == explicit


def test_configure_test_database_falls_back_to_sqlite_when_postgres_unreachable(monkeypatch) -> None:
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    monkeypatch.delenv("PYTEST_ACTIVE_TEST", raising=False)
    monkeypatch.setenv("TEST_DATABASE_HOST", "127.0.0.1")
    monkeypatch.setenv("TEST_DATABASE_PORT", "65530")

    url = configure_test_database("fallback_case")

    assert url.startswith("sqlite:///")
    assert os.environ["DATABASE_URL"] == url
    assert os.environ["PYTEST_ACTIVE_TEST"] == "fallback_case"


def test_configure_test_database_prefers_database_name_when_reachable(monkeypatch) -> None:
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    monkeypatch.delenv("TEST_DATABASE_NAME", raising=False)
    monkeypatch.setenv("DATABASE_NAME", "hypertrophy")
    monkeypatch.setenv("POSTGRES_DB", "hypertrophy_test")
    monkeypatch.setenv("TEST_DATABASE_HOST", "postgres")
    monkeypatch.setenv("TEST_DATABASE_PORT", "5432")
    monkeypatch.setenv("TEST_DATABASE_USER", "hypertrophy")
    monkeypatch.setenv("TEST_DATABASE_PASSWORD", "hypertrophy")
    monkeypatch.setattr(test_db, "_postgres_is_reachable", lambda _host, _port: True)

    url = configure_test_database("reachable_case")

    assert url.endswith("/hypertrophy")
    assert os.environ["DATABASE_URL"] == url
