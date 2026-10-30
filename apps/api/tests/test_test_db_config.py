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


def test_configure_test_database_uses_explicit_override(monkeypatch, tmp_path) -> None:
    explicit = f"sqlite:///{tmp_path / 'explicit.sqlite3'}"
    monkeypatch.setenv("TEST_DATABASE_URL", explicit)
    monkeypatch.setenv("CI_TEST_ROOT", str(tmp_path))
    assert configure_test_database("explicit_case") == explicit
    assert os.environ["DATABASE_URL"] == explicit


def test_inherited_production_settings_are_never_selected(monkeypatch):
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_NAME", "hypertrophy")
    monkeypatch.setenv("DATABASE_HOST", "postgres")
    monkeypatch.setenv("POSTGRES_DB", "hypertrophy")
    with pytest.raises(ValueError, match="explicit verified disposable"):
        configure_test_database("unsafe")


@pytest.mark.parametrize("url", [
    "postgresql://hypertrophy:private-sentinel@postgres:5432/hypertrophy",
    "postgresql://test:private-sentinel@127.0.0.1:5432/test_db",
    "sqlite:////etc/private-sentinel.sqlite3", "sqlite:///relative.sqlite3",
    "not-a-url-private-sentinel",
])
def test_unverified_or_unsafe_target_rejected_without_secret_output(monkeypatch, tmp_path, url):
    monkeypatch.setenv("TEST_DATABASE_URL", url)
    monkeypatch.setenv("CI_TEST_ROOT", str(tmp_path))
    with pytest.raises(ValueError) as rejected:
        configure_test_database("unsafe")
    assert "private-sentinel" not in str(rejected.value)


def test_postgres_requires_all_disposable_markers(monkeypatch):
    url = "postgresql+psycopg://synthetic:dummy@127.0.0.1:55439/synthetic_test"
    monkeypatch.setenv("TEST_DATABASE_URL", url)
    monkeypatch.delenv("TEST_DATABASE_DISPOSABLE", raising=False)
    with pytest.raises(ValueError):
        configure_test_database("missing_marker")
    monkeypatch.setenv("TEST_DATABASE_DISPOSABLE", "1")
    monkeypatch.setenv("TEST_DATABASE_NAME", "synthetic_test")
    monkeypatch.setenv("TEST_DATABASE_USER", "synthetic")
    assert configure_test_database("declared_target") == url
    monkeypatch.setenv("TEST_DATABASE_URL", url + "?host=other-host&port=5432&dbname=hypertrophy&user=other-user")
    with pytest.raises(ValueError):
        configure_test_database("query_override")
