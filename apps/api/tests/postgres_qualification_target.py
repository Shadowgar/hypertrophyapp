"""Exact opt-in targets for isolated selected-date PostgreSQL qualification.

This helper never opens a connection. Each suite must additionally verify the
live database/user and exact Alembic revision before importing the application.
"""
from collections.abc import Mapping
from typing import NamedTuple

from sqlalchemy.engine import make_url


class SelectedDateTarget(NamedTuple):
    host: str
    port: int
    database: str
    user: str
    revision: str


def selected_date_target(explicit_url: str, environment: Mapping[str, str], *, allow_0022: bool = False) -> SelectedDateTarget:
    assert explicit_url, "An explicit disposable test URL is required"
    assert environment.get('TEST_DATABASE_URL') == explicit_url and environment.get('DATABASE_URL') == explicit_url, "Test and application URLs must match"
    assert environment.get('M2B_POSTGRES_ISOLATED') == '1', "Explicit PostgreSQL isolation is required"
    target = make_url(explicit_url)
    assert target.drivername == 'postgresql+psycopg', "Only the qualified PostgreSQL driver is allowed"
    current = environment.get('M2B_CURRENT_POSTGRES_ISOLATED') == '1'
    legacy_next_week = environment.get('M2B2_POSTGRES_ISOLATED') == '1'
    assert not (current and legacy_next_week), "Choose one schema qualification target"
    if current:
        expected = SelectedDateTarget('127.0.0.1', 25461, 'm2b_current_qualification', 'm2b_current_test', '0026_initial_calibration')
    elif allow_0022 and legacy_next_week:
        expected = SelectedDateTarget('127.0.0.1', 25463, 'm2b2_qualification', 'm2b2_test', '0022_authored_load_states')
    else:
        expected = SelectedDateTarget('127.0.0.1', 25461, 'm2b_qualification', 'm2b_test', '0021_selected_workout_dates')
    assert (target.host, target.port, target.database, target.username) == expected[:4], "Disposable target identity does not match the explicit qualification mode"
    return expected
