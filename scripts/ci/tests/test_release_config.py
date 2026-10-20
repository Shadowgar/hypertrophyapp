"""Render the real release overlay without daemon/database access or live env."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[3]
REVISION = 'a' * 40


class ReleaseComposeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('docker'):
            raise unittest.SkipTest('Docker Compose CLI unavailable; no daemon is needed')
        probe = subprocess.run(['docker', 'compose', 'version'], capture_output=True)
        if probe.returncode:
            raise unittest.SkipTest('Docker Compose CLI unavailable; no daemon is needed')

    def render(self, revision):
        with tempfile.TemporaryDirectory(prefix='hypertrophy-release-config-') as home:
            env = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'HOME': home,
                   'POSTGRES_DB': 'synthetic_release_config', 'POSTGRES_USER': 'synthetic_release_config',
                   'POSTGRES_PASSWORD': 'synthetic-only-not-deployment',
                   'JWT_SECRET': 'synthetic-only-not-deployment-00000000000000000000'}
            if revision is not None:
                env['RELEASE_ID'] = revision
            # Explicit /dev/null prevents .env discovery. Only config is rendered;
            # no compose up/build/exec or Docker daemon operation is possible here.
            return subprocess.run(['docker', 'compose', '--env-file', '/dev/null',
                '-f', str(ROOT / 'docker-compose.yml'), '-f', str(ROOT / 'infra/compose.release.yml'),
                'config', '--format', 'json'], cwd=ROOT, env=env, capture_output=True, text=True)

    def test_missing_revision_cannot_silently_use_dev_images(self):
        result = self.render(None)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('RELEASE_ID', result.stderr)

    def test_pair_build_versions_and_labels_match_and_feature_defaults_off(self):
        result = self.render(REVISION)
        self.assertEqual(result.returncode, 0, result.stderr)
        services = json.loads(result.stdout)['services']
        for name, argument in [('api', 'APP_VERSION'), ('web', 'NEXT_PUBLIC_APP_VERSION')]:
            self.assertEqual(services[name]['image'], f'hypertrophyapp-{name}:{REVISION}')
            self.assertEqual(services[name]['build']['args'][argument], REVISION)
            self.assertEqual(services[name]['build']['labels']['org.opencontainers.image.revision'], REVISION)
        self.assertEqual(services['api']['environment']['CUSTOMIZED_ENABLED'], 'false')
        self.assertIn('alembic upgrade head', ' '.join(services['api']['command']))
        self.assertEqual(services['api']['depends_on']['postgres']['condition'], 'service_healthy')


if __name__ == '__main__':
    unittest.main()
