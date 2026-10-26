"""Publisher timing with real control flow, simulated clocks and no network/DB."""
from contextlib import redirect_stdout
import configparser
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import yaml

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location('publisher_under_test', ROOT/'infra/release/release.py')
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)
SHA = 'a' * 40
OLD = 'b' * 40
MONITOR_SECONDS = 100 * 60


class Clock:
    def __init__(self):
        self.now = 0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        if not 0 < seconds <= 10:
            raise AssertionError('Polling must sleep for a positive bounded interval')
        self.now += seconds


class PublisherTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.output = io.StringIO()
        self.provider = Mock(side_effect=self.metadata)
        self.qualify = Mock()
        self.host_deploy = Mock(side_effect=AssertionError('Publisher cannot deploy on the host'))
        for guard in (
            patch.dict(release.os.environ, {'GITHUB_TOKEN':'synthetic'}, clear=True),
            patch.object(release, 'api', self.provider),
            patch.object(release, 'qualify', self.qualify),
            patch.object(release.Host, 'deploy', self.host_deploy),
            patch.object(release.time, 'monotonic', self.clock.monotonic),
            patch.object(release.time, 'sleep', self.clock.sleep),
            redirect_stdout(self.output),
        ):
            guard.__enter__()
            self.addCleanup(guard.__exit__, None, None, None)

    def metadata(self, path, **kwargs):
        if path == '/actions/runs/123':
            return {'head_sha':SHA}
        if path == '/deployments':
            self.qualify.assert_called_with(SHA, 123, token='synthetic')
            self.assertEqual(kwargs['body']['ref'], SHA)
            self.assertFalse(kwargs['body']['auto_merge'])
            self.assertEqual(kwargs['body']['required_contexts'], ['CI qualification'])
            return {}
        raise AssertionError('Unexpected provider operation')

    def response(self, revision):
        return io.BytesIO(json.dumps({'version':revision}).encode())

    def deploy_after(self, seconds):
        return lambda path: self.response(SHA if self.clock.now >= seconds else OLD)

    def assert_one_request_and_no_local_deploy(self):
        self.assertEqual([c.args[0] for c in self.provider.call_args_list], ['/actions/runs/123','/deployments'])
        self.host_deploy.assert_not_called()

    def test_observed_33m41_host_success_is_not_rejected_at_30_minutes(self):
        with patch.object(release, 'public_response', side_effect=self.deploy_after(33*60+41)):
            release.publish(123)
        self.assertGreaterEqual(self.clock.now, 33*60+41)
        self.assertIn('Release confirmed: '+SHA, self.output.getvalue())
        self.assert_one_request_and_no_local_deploy()

    def test_success_after_full_host_and_timer_allowance_still_confirms(self):
        with patch.object(release, 'public_response', side_effect=self.deploy_after(95*60+15)):
            release.publish(123)
        self.assertGreaterEqual(self.clock.now, 95*60+15)
        self.assertLess(self.clock.now, MONITOR_SECONDS)
        self.assert_one_request_and_no_local_deploy()

    def test_temporary_transport_bad_json_and_missing_version_are_retryable(self):
        replies = [OSError('temporary'), release.urllib.error.HTTPError('https://example.test/api/health', 503, 'temporary', {}, None),
                   io.BytesIO(b'invalid'), io.BytesIO(b'{}'),
                   self.response(SHA), self.response(SHA)]
        with patch.object(release, 'public_response', side_effect=replies):
            release.publish(123)
        self.assertIn('Release confirmed: '+SHA, self.output.getvalue())
        self.assert_one_request_and_no_local_deploy()

    def test_mixed_versions_cannot_confirm_the_release(self):
        def probe(path):
            return self.response(SHA if path == '/api/health' or self.clock.now >= 20 else OLD)
        with patch.object(release, 'public_response', side_effect=probe):
            release.publish(123)
        self.assertGreaterEqual(self.clock.now, 20)

    def test_genuine_timeout_remains_failure_without_another_request_or_recovery(self):
        with patch.object(release, 'public_response', side_effect=self.deploy_after(float('inf'))):
            with self.assertRaisesRegex(release.Refused, '^host_release_timeout_check_private_status$'):
                release.publish(123)
        self.assertEqual(self.clock.now, MONITOR_SECONDS)
        self.assertNotIn('Release confirmed', self.output.getvalue())
        self.assert_one_request_and_no_local_deploy()

    def test_probe_latency_consumes_wall_clock_budget_instead_of_extending_poll_count(self):
        def probe(path):
            self.clock.now += 7
            return self.response(OLD)
        with patch.object(release, 'public_response', side_effect=probe):
            with self.assertRaises(release.Refused):
                release.publish(123)
        self.assertGreaterEqual(self.clock.now, MONITOR_SECONDS)
        self.assertLessEqual(self.clock.now, MONITOR_SECONDS+10)

    def test_matching_response_after_deadline_cannot_turn_timeout_into_success(self):
        def probe(path):
            self.clock.now = MONITOR_SECONDS+1
            return self.response(SHA)
        with patch.object(release, 'public_response', side_effect=probe):
            with self.assertRaisesRegex(release.Refused, 'host_release_timeout'):
                release.publish(123)
        self.assertNotIn('Release confirmed', self.output.getvalue())

    def test_slow_incomplete_qualification_is_bounded_and_never_requests_deployment(self):
        def incomplete(*args, **kwargs):
            self.clock.now += 45
            raise release.Refused('codeql_incomplete')
        self.qualify.side_effect = incomplete
        with patch.object(release, 'public_response') as public:
            with self.assertRaisesRegex(release.Refused, '^qualification_timeout$'):
                release.publish(123)
        self.assertLessEqual(self.clock.now, 10*60+5*30)
        self.assertEqual(self.provider.call_count, 1)
        public.assert_not_called()
        self.host_deploy.assert_not_called()

    def test_fatal_qualification_failure_is_not_retried_or_reclassified(self):
        self.qualify.side_effect = release.Refused('ci_origin_or_result')
        with self.assertRaisesRegex(release.Refused, '^ci_origin_or_result$'):
            release.publish(123)
        self.assertEqual(self.qualify.call_count, 1)
        self.assertEqual(self.provider.call_count, 1)

    def test_pending_qualification_must_succeed_before_the_request(self):
        self.qualify.side_effect = [release.Refused('required_checks_incomplete'),
                                   release.Refused('codeql_incomplete'), None]
        with patch.object(release, 'public_response', side_effect=self.deploy_after(0)):
            release.publish(123)
        self.assertEqual(self.qualify.call_count, 3)
        self.assert_one_request_and_no_local_deploy()


class TimeoutBudgetTests(unittest.TestCase):
    def test_workflow_includes_host_timer_qualification_network_and_shutdown_allowance(self):
        workflow = yaml.safe_load((ROOT/'.github/workflows/release.yml').read_text())
        self.assertEqual(workflow['jobs']['release']['timeout-minutes'], 120)
        self.assertEqual(release.PUBLISH_TIMEOUT_SECONDS, MONITOR_SECONDS)
        self.assertEqual(release.QUALIFICATION_TIMEOUT_SECONDS, 10*60)
        service = configparser.ConfigParser(interpolation=None)
        service.read(ROOT/'infra/release/workoutapp-release.service')
        timer = configparser.ConfigParser(interpolation=None)
        timer.read(ROOT/'infra/release/workoutapp-release.timer')
        # Read the actual unchanged host90m limit and timer5m15s settings.
        host_seconds = service.getint('Service', 'TimeoutStartSec')
        pickup_seconds = int(timer.get('Timer', 'OnUnitInactiveSec').removesuffix('min'))*60
        jitter_seconds = int(timer.get('Timer', 'RandomizedDelaySec').removesuffix('s'))
        self.assertGreaterEqual(MONITOR_SECONDS, host_seconds+pickup_seconds+jitter_seconds+20)
        # Five30s qualification calls may finish in flight; lookup/request add60s.
        self.assertGreaterEqual(120*60, MONITOR_SECONDS+600+150+60+10+300)
