import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
import yaml

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('release_changes',ROOT/'scripts/ci/changes.py')
changes=importlib.util.module_from_spec(spec);spec.loader.exec_module(changes)


class ReleaseWorkflowTests(unittest.TestCase):
    def test_privileged_workflow_never_executes_pr_or_fork_code(self):
        workflow=yaml.safe_load((ROOT/'.github/workflows/release.yml').read_text())
        triggers=workflow.get('on',workflow.get(True))
        self.assertEqual(set(triggers),{'workflow_run'})
        self.assertEqual(triggers['workflow_run']['branches'],['main'])
        job=workflow['jobs']['release'];guard=job['if']
        for clause in ("head_branch == 'main'","head_repository.full_name == github.repository","event == 'push'","event == 'workflow_dispatch'","conclusion == 'success'"):self.assertIn(clause,guard)
        checkout=job['steps'][0]
        self.assertEqual(checkout['with']['ref'],'${{ github.event.workflow_run.head_sha }}')
        self.assertFalse(checkout['with']['persist-credentials'])
        self.assertEqual({k for k,v in workflow['permissions'].items() if v=='write'},{'deployments'})
        self.assertNotIn('pull_request_target',str(workflow))

    def test_main_push_selects_every_release_check_even_for_docs_only(self):
        for event,ref,full in (('push','refs/heads/main',True),('pull_request','refs/pull/1/merge',False)):
            with tempfile.TemporaryDirectory() as temp:
                path=Path(temp)/'event.json';path.write_text('{}')
                env={'GITHUB_EVENT_NAME':event,'GITHUB_REF':ref,'GITHUB_EVENT_PATH':str(path)}
                output=io.StringIO()
                with patch.dict(os.environ,env,clear=True),patch.object(sys,'argv',['changes.py']),patch.object(changes,'changed_paths',return_value=('a'*40,'a'*40,['README.md'])),redirect_stdout(output):changes.main()
                result=json.loads(output.getvalue())
                self.assertEqual(all(result[c] for c in changes.CATEGORIES),full)

    def test_manual_full_qualification_keeps_parent_baseline_and_full_test_selection(self):
        with patch.object(changes,'git',return_value=('b'*40).encode()):
            base,diff,paths=changes.changed_paths('workflow_dispatch',{})
        self.assertEqual((base,diff),('b'*40,'b'*40))
        self.assertIsNone(paths)

    def test_initial_commit_has_no_invented_baseline(self):
        import subprocess
        with patch.object(changes,'git',side_effect=subprocess.CalledProcessError(1,['git'])):
            self.assertEqual(changes.changed_paths('workflow_dispatch',{}),(None,None,None))
