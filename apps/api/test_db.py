import os
import re
from pathlib import Path
from sqlalchemy.engine import make_url


def isolated_worker_database_url(explicit_url: str, worker_id: str, test_root: str) -> str:
    """Give each pytest worker a distinct SQLite file under an explicit test root."""
    if not re.fullmatch(r"gw\d+", worker_id):
        raise ValueError("Unexpected pytest worker ID")
    if not explicit_url or not test_root:
        raise ValueError("Parallel API tests require an explicit URL and test root")
    url = make_url(explicit_url)
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        raise ValueError("Parallel API tests require a file-backed SQLite target")
    root = Path(test_root).resolve(strict=True)
    database = Path(url.database).resolve()
    if root == Path("/") or not database.is_relative_to(root):
        raise ValueError("Parallel API database must stay under the disposable test root")
    worker_database = database.with_name(f"{database.stem}-{worker_id}{database.suffix}")
    return str(url.set(database=str(worker_database)))


def configure_test_database(test_name: str) -> str:
    """Require explicit disposable coordinates before app imports or any DDL.

    SQLite files require an existing CI_TEST_ROOT/TEST_DATABASE_ROOT. PostgreSQL
    requires separately verified, declared disposable database/user coordinates
    and a non-default loopback port. Never infer targets from runtime settings.
    """
    explicit = os.environ.get("TEST_DATABASE_URL", "")
    if not explicit:
        raise ValueError("Tests require an explicit verified disposable TEST_DATABASE_URL")
    try:
        url = make_url(explicit)
        if url.query:
            # libpq/SQLAlchemy query options can override authority coordinates
            # (host, dbname, user, service); validate the actual fixed target.
            raise ValueError("Test database URL query overrides are forbidden")
        if url.get_backend_name() == "sqlite":
            if url.database != ":memory:":
                root_value = os.environ.get("CI_TEST_ROOT") or os.environ.get("TEST_DATABASE_ROOT")
                if not root_value:
                    raise ValueError("Missing disposable test root")
                root = Path(root_value).resolve(strict=True)
                if not url.database or not Path(url.database).is_absolute():
                    raise ValueError("SQLite test path must be absolute")
                database = Path(url.database).resolve()
                if root == Path("/") or database == root or not database.is_relative_to(root):
                    raise ValueError("SQLite target is outside the disposable test root")
        elif url.get_backend_name() == "postgresql":
            if (os.environ.get("TEST_DATABASE_DISPOSABLE") != "1"
                    or url.host not in {"127.0.0.1", "::1"}
                    or not url.port or url.port == 5432
                    or not url.database or url.database in {"hypertrophy", "postgres", "template0", "template1"}
                    or url.database != os.environ.get("TEST_DATABASE_NAME")
                    or not url.username or url.username != os.environ.get("TEST_DATABASE_USER")):
                raise ValueError("PostgreSQL target is not declared disposable")
        else:
            raise ValueError("Unsupported disposable database backend")
    except Exception as exc:
        # URLs may contain passwords; never reflect parser or coordinate values.
        raise ValueError("Tests require a verified disposable database and explicit target markers") from None
    os.environ["DATABASE_URL"] = explicit
    os.environ.setdefault("PYTEST_ACTIVE_TEST", test_name)
    return explicit
