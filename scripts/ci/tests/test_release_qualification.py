"""Network/DB-free release admission tests: real policy, synthetic provider facts."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location('release', ROOT / 'infra/release/release.py')
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)
SHA = 'a' * 40


class AdmissionTests(unittest.TestCase):
    def facts(self):
        return dict(sha=SHA, current=SHA, protected=True,
                    run={'head_sha':SHA, 'head_branch':'main', 'event':'push',
                         'conclusion':'success', 'path':'.github/workflows/ci.yml'},
                    jobs=[{'name':n,'conclusion':'success','steps':[{'name':'Complete API and source-fidelity qualification','conclusion':'success'}] if n=='api-tests' else []} for n in release.REQUIRED_JOBS],
                    checks=[{'name':n,'conclusion':'success'} for n in release.CODEQL_CHECKS])

    def test_qualified_current_protected_main_is_admitted(self):
        release.admit(**self.facts())

    def test_public_api_profile_cannot_replace_full_release_qualification(self):
        for steps in ([],[{'name':'PR API behavior without private source','conclusion':'success'}],
                      [{'name':'Complete API and source-fidelity qualification','conclusion':'skipped'}],
                      [{'name':'Complete API and source-fidelity qualification','conclusion':'failure'}]):
            facts=self.facts();next(job for job in facts['jobs'] if job['name']=='api-tests')['steps']=steps
            with self.subTest(steps=steps),self.assertRaisesRegex(release.Refused,'full_api_qualification_required'):release.admit(**facts)

    def test_missing_skipped_failed_cancelled_checks_never_qualify(self):
        for group in ('jobs','checks'):
            for status in ('failure','cancelled','skipped',None):
                f=self.facts();f[group][0]['conclusion']=status
                with self.subTest(group=group,status=status), self.assertRaises(release.Refused):release.admit(**f)
            f=self.facts();f[group].pop()
            with self.assertRaises(release.Refused):release.admit(**f)

    def test_pr_stale_unprotected_foreign_workflow_and_invalid_sha_are_rejected(self):
        for update in ({'current':'b'*40},{'protected':False},{'sha':'main; command'},{'sha':'A'*40}):
            f=self.facts();f.update(update)
            with self.assertRaises(release.Refused):release.admit(**f)
        for key,value in (('event','pull_request'),('head_branch','fork'),('head_sha','b'*40),('path','evil.yml'),('conclusion','failure')):
            f=self.facts();f['run'][key]=value
            with self.subTest(key=key),self.assertRaises(release.Refused):release.admit(**f)

    def test_migration_changes_stop_automatic_release(self):
        release.require_code_only(['apps/web/app/page.tsx'])
        for path in ('apps/api/alembic/versions/0027_new.py','apps/api/alembic/env.py','apps/api/app/models.py'):
            with self.subTest(path=path),self.assertRaises(release.Refused):release.require_code_only([path])

    def test_untrusted_request_cannot_choose_commands_config_or_refs(self):
        d={'sha':SHA,'creator':{'login':'github-actions[bot]','id':41898282},
           'environment':'workoutapp-production','task':'workoutapp-release',
           'payload':{'ci_run_id':123},'ref':SHA}
        self.assertEqual(release.request(d),(SHA,123))
        for update in ({'sha':'main'},{'creator':{'login':'owner','id':1}},
                       {'environment':'other'},{'payload':{'ci_run_id':'$(cmd)'}},{'ref':'refs/pull/1/merge'}):
            bad=deepcopy(d);bad.update(update)
            with self.assertRaises(release.Refused):release.request(bad)




class ExecutionTests(unittest.TestCase):
    def fake(self):
        from unittest.mock import Mock
        host=release.Host.__new__(release.Host);host.bootstrap=False;host.config={'automatic_rollback':True}
        host.verify_configuration=Mock()
        host.verify_environment=Mock()
        host.running=Mock(side_effect=[('b'*40,{'api':'old-api','web':'old-web'}),(SHA,{'api':'new-api','web':'new-web'})])
        host.build=Mock(return_value={'api':'new-api','web':'new-web'})
        host.compose=Mock(side_effect=lambda images,revision:['compose',revision])
        host.schema=Mock();host.command=Mock();host.ready=Mock()
        import tempfile
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        host.state=Path(self.temp.name)
        return host

    def test_before_and_after_build_qualification_then_immutable_pair_and_receipt(self):
        from unittest.mock import patch
        import json
        host=self.fake()
        with patch.object(release,'qualify') as qualify:host.deploy(SHA,123)
        self.assertEqual(qualify.call_count,2)
        self.assertEqual(host.command.call_args.args[0],['compose',SHA,'up','-d','--no-deps','--no-build','api','web'])
        self.assertEqual(json.loads((host.state/'last-success.json').read_text())['images'],{'api':'new-api','web':'new-web'})

    def test_schema_rejection_prevents_cutover(self):
        from unittest.mock import patch
        host=self.fake();host.schema.side_effect=release.Refused('schema_review_required')
        with patch.object(release,'qualify'),self.assertRaises(release.Refused):host.deploy(SHA,123)
        host.command.assert_not_called()
        self.assertFalse((host.state/'last-success.json').exists())

    def test_failed_health_recovers_only_old_images_without_migration(self):
        from unittest.mock import patch
        host=self.fake();host.ready.side_effect=[release.Refused('public_version_probe_failed'),None]
        with patch.object(release,'qualify'),self.assertRaises(release.Refused):host.deploy(SHA,123)
        self.assertEqual(host.compose.call_args_list[-1].args,({'api':'old-api','web':'old-web'},'b'*40))
        self.assertEqual(host.schema.call_count,2)
        self.assertEqual(host.command.call_count,2)
        self.assertTrue(all('alembic' not in str(c) for c in host.command.call_args_list))
        self.assertFalse((host.state/'last-success.json').exists())

    def test_default_failure_preserves_state_for_operator_recovery(self):
        from unittest.mock import patch
        host=self.fake();host.config={};host.ready.side_effect=release.Refused('failed')
        with patch.object(release,'qualify'),self.assertRaisesRegex(release.Refused,'operator_recovery_required'):host.deploy(SHA,123)
        self.assertEqual(host.command.call_count,1)
        self.assertFalse((host.state/'last-success.json').exists())

    def test_stale_reply_after_build_cannot_cut_over(self):
        from unittest.mock import patch
        host=self.fake()
        with patch.object(release,'qualify',side_effect=[None,release.Refused('stale')]),self.assertRaises(release.Refused):host.deploy(SHA,123)
        host.command.assert_not_called()

    def test_same_running_release_does_not_consume_github_qualification_quota(self):
        from unittest.mock import patch
        host=self.fake();host.running.return_value=(SHA,{}) ; host.running.side_effect=None
        with patch.object(release,'qualify') as q:host.deploy(SHA,123)
        q.assert_not_called();host.build.assert_not_called()

    def test_uncertain_cutover_blocks_same_and_later_requests_until_operator_recovery(self):
        from unittest.mock import patch
        import json
        host=self.fake();host.config={};host.ready.side_effect=release.Refused('failed')
        with patch.object(release,'qualify'),self.assertRaises(release.Refused):host.deploy(SHA,123)
        latch=host.state/'recovery-required.json'
        self.assertEqual(json.loads(latch.read_text())['revision'],SHA)
        for revision in (SHA,'c'*40):
            with self.subTest(revision=revision),patch.object(release,'qualify') as q,self.assertRaisesRegex(release.Refused,'operator_recovery_required'):
                host.deploy(revision,124)
            q.assert_not_called()

    def test_same_revision_still_requires_live_health_and_success_clears_inflight_latch(self):
        from unittest.mock import patch
        host=self.fake()
        with patch.object(release,'qualify'):host.deploy(SHA,123)
        self.assertFalse((host.state/'recovery-required.json').exists())
        host.running.side_effect=None;host.running.return_value=(SHA,{})
        host.ready.side_effect=release.Refused('failed')
        with patch.object(release,'qualify') as q,self.assertRaises(release.Refused):host.deploy(SHA,123)
        q.assert_not_called()

    def test_environment_drift_or_lost_customized_activation_stops_cutover(self):
        from unittest.mock import Mock
        host=release.Host.__new__(release.Host);host.prefix='synthetic'
        host.command=Mock(return_value=b'{"services":{"api":{"environment":{"CUSTOMIZED_ENABLED":"true","JWT_SECRET":"synthetic","APP_VERSION":"new","SCHEMA_MANAGEMENT_MODE":"validate"}},"web":{"environment":{"SERVER_API_BASE_URL":"http://api:8000"}}}}')
        host.inspect=Mock(side_effect=lambda kind,name:{'Config':{'Env':['CUSTOMIZED_ENABLED=true','JWT_SECRET=synthetic','APP_VERSION=old'] if name.endswith('api') else ['SERVER_API_BASE_URL=http://api:8000']}})
        host.verify_environment(['compose'])
        for key,value in (('JWT_SECRET','changed'),('CUSTOMIZED_ENABLED','false')):
            with self.subTest(key=key):
                host.inspect=Mock(side_effect=lambda kind,name:{'Config':{'Env':[f'{key}={value}'] if name.endswith('api') else ['SERVER_API_BASE_URL=http://api:8000']}})
                with self.assertRaisesRegex(release.Refused,'runtime_configuration_changed'):host.verify_environment(['compose'])

    def test_model_rename_is_not_hidden_from_schema_review(self):
        import subprocess,tempfile
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);model=root/'apps/api/app/models.py';model.parent.mkdir(parents=True)
            def git(*args):return subprocess.check_output(['git','-C',directory,*args],stderr=subprocess.DEVNULL).decode().strip()
            git('init');git('config','user.email','synthetic@example.invalid');git('config','user.name','Synthetic')
            model.write_text('field = 1\n'*100);git('add','.');git('commit','-m','synthetic baseline');base=git('rev-parse','HEAD')
            model.rename(model.with_name('model_definitions.py'));git('add','.');git('commit','-m','synthetic relocation')
            paths=git('diff','--no-renames','--name-only',base,'HEAD','--','apps/api').splitlines()
            self.assertIn('apps/api/app/models.py',paths)
            with self.assertRaisesRegex(release.Refused,'schema_review_required'):release.require_code_only(paths)


class ProviderProofTests(unittest.TestCase):
    def facts(self):
        facts=AdmissionTests().facts()
        run={**facts['run'],'repository':{'id':release.REPO_ID},'head_repository':{'id':release.REPO_ID}}
        return {'/branches/main':{'protected':True,'commit':{'sha':SHA}},
                '/actions/runs/123':run,
                '/actions/runs/123/jobs?per_page=100':{'total_count':len(facts['jobs']),'jobs':facts['jobs']},
                '/commits/'+SHA+'/check-runs?per_page=100&filter=latest':{'check_runs':[{**c,'app':{'id':15368}} for c in facts['checks']]},
                '/actions/runs?head_sha='+SHA+'&per_page=100':{'workflow_runs':[{'path':'dynamic/github-code-scanning/codeql','head_sha':SHA,'head_branch':'main','conclusion':'success','repository':{'id':release.REPO_ID}}]}}

    def test_real_admission_path_consumes_independent_provider_proofs(self):
        from unittest.mock import patch
        facts=self.facts()
        with patch.object(release,'api',side_effect=lambda path,**kw:facts[path]):release.qualify(SHA,123)

    def test_forged_codeql_name_or_missing_default_setup_cannot_qualify(self):
        from unittest.mock import patch
        for kind in ('forged-app','wrong-workflow','wrong-head','foreign-ci'):
            facts=self.facts()
            if kind=='forged-app':facts['/commits/'+SHA+'/check-runs?per_page=100&filter=latest']['check_runs'][0]['app']['id']=999
            elif kind=='wrong-workflow':facts['/actions/runs?head_sha='+SHA+'&per_page=100']['workflow_runs'][0]['path']='evil.yml'
            elif kind=='wrong-head':facts['/actions/runs?head_sha='+SHA+'&per_page=100']['workflow_runs'][0]['head_sha']='b'*40
            else:facts['/actions/runs/123']['head_repository']['id']=999
            with self.subTest(kind=kind),patch.object(release,'api',side_effect=lambda path,**kw:facts[path]),self.assertRaises(release.Refused):release.qualify(SHA,123)


if __name__=='__main__':unittest.main()
