import os
import pytest

import test_db
from test_db import configure_test_database, isolated_worker_database_url


def test_parallel_worker_database_stays_unique_and_disposable(tmp_path) -> None:
    base = f"sqlite:///{tmp_path / 'api.sqlite3'}"
    first = isolated_worker_database_url(base, "gw0", str(tmp_path))
    second = isolated_worker_database_url(base, "gw1", str(tmp_path))
    assert first != second
    assert first.endswith("/api-gw0.sqlite3")
    assert second.endswith("/api-gw1.sqlite3")


@pytest.mark.parametrize("url,worker", [
    ("postgresql://localhost/test", "gw0"),
    ("sqlite:////tmp/outside.sqlite3", "gw0"),
    ("sqlite:////tmp/outside.sqlite3", "unexpected"),
])
def test_parallel_worker_database_rejects_unsafe_targets(tmp_path, url, worker) -> None:
    with pytest.raises(ValueError):
        isolated_worker_database_url(url, worker, str(tmp_path))


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
