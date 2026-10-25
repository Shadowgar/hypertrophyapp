"""Restore launch credentials stay out of retained files and command arguments."""
import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('backup',ROOT/'infra/release/backup_preflight.py')
backup=importlib.util.module_from_spec(spec);spec.loader.exec_module(backup)


class BackupLaunchTests(unittest.TestCase):
    def test_restore_uses_child_environment_without_password_file_or_cli_value(self):
        marker='synthetic-unique-password-never-a-real-credential'
        with patch.object(backup.secrets,'token_urlsafe',return_value=marker),patch.object(backup,'run') as run,patch.object(Path,'write_text',side_effect=AssertionError('No credential file')):
            backup.start_restore_container('workoutapp-release-restore-123','sha256:synthetic')
            args=run.call_args.args[0];environment=run.call_args.kwargs['env']
            self.assertNotIn(marker,' '.join(args))
            self.assertNotIn('--env-file',args)
            self.assertEqual(environment['POSTGRES_PASSWORD'],marker)
            self.assertEqual(environment['POSTGRES_DB'],'workoutapp_release_restore')
            self.assertNotIn('POSTGRES_HOST_AUTH_METHOD',environment)
            self.assertEqual(args[args.index('--network')+1],'none')
            self.assertIn('/var/lib/postgresql/data:rw,noexec,nosuid,size=1g',args)

    def test_generated_secret_is_not_added_to_parent_environment(self):
        with patch.dict(os.environ,{'DOCKER_CONTEXT':'synthetic-verified-context'},clear=True),patch.object(backup,'run') as run:
            backup.start_restore_container('workoutapp-release-restore-123','sha256:synthetic')
            self.assertNotIn('POSTGRES_PASSWORD',os.environ)
            self.assertEqual(run.call_args.kwargs['env']['DOCKER_CONTEXT'],'synthetic-verified-context')

    def test_subprocess_gets_child_environment_and_errors_withhold_credential_output(self):
        import subprocess
        secret='synthetic-child-only-value'
        result=subprocess.CompletedProcess(['docker'],1,stdout=secret.encode(),stderr=secret.encode())
        with patch.object(backup.subprocess,'run',return_value=result) as child:
            with self.assertRaises(RuntimeError) as error:backup.run(['docker'],env={'POSTGRES_PASSWORD':secret})
            self.assertNotIn(secret,str(error.exception))
            self.assertEqual(child.call_args.kwargs['env'],{'POSTGRES_PASSWORD':secret})


if __name__=='__main__':unittest.main()
