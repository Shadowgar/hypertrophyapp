"""Compose-only security boundaries: synthetic inputs; no services or mail."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]

@unittest.skipUnless(shutil.which('docker'), 'Docker Compose configuration CLI required')
class GmailOverrideTests(unittest.TestCase):
    def resolve(self, credentials):
        with tempfile.TemporaryDirectory(prefix='ferravis-gmail-compose-') as directory:
            directory = Path(directory)
            (directory/'base.json').write_text(json.dumps({'services':{'api':{'image':'synthetic:no-pull', 'environment':{'SMTP_PASSWORD':'stale-synthetic-mail-value','DATABASE_PASSWORD':'unchanged-synthetic-db-value','SCHEMA_MANAGEMENT_MODE':'validate'}}}}))
            (directory/'empty.env').write_text('')
            return subprocess.run(['docker','compose','--project-directory',str(directory),'--env-file',str(directory/'empty.env'),'-f',str(directory/'base.json'),'-f',str(ROOT/'infra/mail/compose.gmail.yml'),'config','--format','json'],env={'PATH':os.environ['PATH'],**credentials},stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15)

    def test_missing_new_password_cannot_fall_back_to_stale_smtp_value(self):
        result=self.resolve({'FERRAVIS_GMAIL_USERNAME':'synthetic@example.com'})
        self.assertNotEqual(result.returncode,0)

    def test_missing_sender_is_rejected(self):
        result=self.resolve({'FERRAVIS_GMAIL_APP_PASSWORD':'synthetic-mail-credential'})
        self.assertNotEqual(result.returncode,0)

    def test_override_uses_verified_tls_and_preserves_database_configuration(self):
        result=self.resolve({'FERRAVIS_GMAIL_USERNAME':'synthetic@example.com','FERRAVIS_GMAIL_APP_PASSWORD':'synthetic-mail-credential'})
        self.assertEqual(result.returncode,0)
        env=json.loads(result.stdout)['services']['api']['environment']
        self.assertEqual(env['SMTP_HOST'],'smtp.gmail.com')
        self.assertEqual(env['SMTP_PORT'],'587')
        self.assertEqual(env['SMTP_USE_TLS'],'true')
        self.assertEqual(env['SMTP_USERNAME'],env['SMTP_FROM_EMAIL'])
        self.assertEqual(env['SMTP_PASSWORD'],'synthetic-mail-credential')
        self.assertEqual(env['DATABASE_PASSWORD'],'unchanged-synthetic-db-value')
        self.assertEqual(env['SCHEMA_MANAGEMENT_MODE'],'validate')
