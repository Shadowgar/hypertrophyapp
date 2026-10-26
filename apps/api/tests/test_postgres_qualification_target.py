"""Negative target boundaries run without opening any database connection."""
import pytest
from postgres_qualification_target import selected_date_target


def environment(database='m2b_current_qualification', role='m2b_current_test', port=25461, **extra):
    url=f'postgresql+psycopg://{role}@127.0.0.1:{port}/{database}'
    return url, {'TEST_DATABASE_URL':url,'DATABASE_URL':url,'M2B_POSTGRES_ISOLATED':'1',**extra}


def test_explicit_current_target_requires_current_revision_for_both_suites():
    url, env=environment(M2B_CURRENT_POSTGRES_ISOLATED='1')
    for allow_0022 in (False,True):
        expected=selected_date_target(url,env,allow_0022=allow_0022)
        assert (expected.database,expected.user,expected.revision)==('m2b_current_qualification','m2b_current_test','0026_initial_calibration')


def test_historical_targets_and_history_only_revision_boundary_are_preserved():
    url,env=environment('m2b_qualification','m2b_test')
    assert selected_date_target(url,env).revision=='0021_selected_workout_dates'
    url,env=environment('m2b2_qualification','m2b2_test',25463,M2B2_POSTGRES_ISOLATED='1')
    assert selected_date_target(url,env,allow_0022=True).revision=='0022_authored_load_states'
    with pytest.raises(AssertionError):selected_date_target(url,env)


@pytest.mark.parametrize('change',[
    {'host':'localhost'},{'port':5432},{'database':'hypertrophy'},{'role':'m2b_test'},
    {'driver':'postgresql+psycopg2'},{'sqlite':True},{'isolation':None},{'current':None},{'other_url':True},{'conflicting':True},
])
def test_current_opt_in_never_relaxes_identity_driver_or_environment_guards(change):
    url,env=environment(M2B_CURRENT_POSTGRES_ISOLATED='1')
    if 'host' in change:url=url.replace('127.0.0.1',change['host'])
    if 'port' in change:url=url.replace(':25461/',f":{change['port']}/")
    if 'database' in change:url=url.replace('/m2b_current_qualification','/'+change['database'])
    if 'role' in change:url=url.replace('m2b_current_test@',change['role']+'@')
    if 'driver' in change:url=url.replace('postgresql+psycopg:',change['driver']+':')
    if 'sqlite' in change:url='sqlite:////tmp/not-a-postgres-qualification.db'
    env.update(TEST_DATABASE_URL=url,DATABASE_URL=url)
    if 'isolation' in change:env.pop('M2B_POSTGRES_ISOLATED')
    if 'current' in change:env.pop('M2B_CURRENT_POSTGRES_ISOLATED')
    if 'other_url' in change:env['DATABASE_URL']='postgresql+psycopg://m2b_test@127.0.0.1:25461/m2b_qualification'
    if 'conflicting' in change:env['M2B2_POSTGRES_ISOLATED']='1'
    with pytest.raises(AssertionError):selected_date_target(url,env,allow_0022=True)
