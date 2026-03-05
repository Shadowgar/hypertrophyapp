import os


def configure_test_database(test_name: str) -> str:
    """Set DATABASE_URL for tests with Postgres-first behavior.

    Override with TEST_DATABASE_URL for local one-off cases (including SQLite).
    """
    explicit_url = os.getenv("TEST_DATABASE_URL")
    if explicit_url:
        os.environ["DATABASE_URL"] = explicit_url
        return explicit_url

    host = os.getenv("TEST_DATABASE_HOST", os.getenv("DATABASE_HOST", os.getenv("POSTGRES_HOST", "localhost")))
    port = os.getenv("TEST_DATABASE_PORT", os.getenv("DATABASE_PORT", "5432"))
    name = os.getenv("TEST_DATABASE_NAME", os.getenv("POSTGRES_DB", "hypertrophy_test"))
    user = os.getenv("TEST_DATABASE_USER", os.getenv("POSTGRES_USER", "hypertrophy"))
    password = os.getenv("TEST_DATABASE_PASSWORD", os.getenv("POSTGRES_PASSWORD", "hypertrophy"))

    url = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{name}"
    os.environ["DATABASE_URL"] = url
    os.environ.setdefault("PYTEST_ACTIVE_TEST", test_name)
    return url
