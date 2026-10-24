import json,statistics,hashlib,re
from pathlib import Path
q=Path('.qualification/closeout');out=Path('docs/evidence/today-performance-2026-10-23/closeout-2026-10-24')
rows=json.loads((q/'results.json').read_text());assert len(rows)==96
compact=[];variants={}
for label,path,api in [('base','/tmp/hypertrophy-starting-load','c656988'),('candidate','/tmp/hypertrophy-today-perf','912e7e9'),('control','/tmp/hypertrophy-cold-control','912e7e9')]:
 p=Path(path);n=p/'apps/web/.next';bundle=next(n.glob('static/chunks/app/today/page-*.js'))
 variants[label]={'web_worktree':path,'api_source':api,'build_id':(n/'BUILD_ID').read_text().strip(),'today_source_sha256':hashlib.sha256((p/'apps/web/app/today/page.tsx').read_bytes()).hexdigest(),'today_js_bytes':bundle.stat().st_size,'routes_manifest_sha256':hashlib.sha256((n/'routes-manifest.json').read_bytes()).hexdigest()}
for r in rows:
 key=f"{r['rep']}-{r['variant']}-{r['scenario']}";records=[json.loads(x) for x in Path('.qualification/api-timings-closeout-'+key+'.jsonl').read_text().splitlines()]
 api=[d for d in records if d.get('scenario')==r['scenario'] and d['path']=='/workout/today'];assert len(api)==2
 entry=api[0 if r['phase']=='cold' else 1]
 fetches=r['marks']['fetches'];health=next(x for x in fetches if x['path']=='/api/health');today=next(x for x in fetches if x['path']=='/api/workout/today');gates=[x for x in fetches if x['path'] in ['/api/plan/scheduling-context','/api/weekly-review/status']];assert len(gates)==2
 assets=[x for x in r['resources'] if '/app/today/page-' in x['path']];assert len(assets)==1
 def clean(x):return {k:round(v,3) if isinstance(v,float) else v for k,v in x.items()}
 compact.append({'rep':r['rep'],'variant':r['variant'],'scenario':r['scenario'],'phase':r['phase'],'visible_ms':round(r['visibleNode'],3),'usable_ms':round(r['usableNode'],3),'browser_visible_ms':round(r['marks']['visible'],3),'browser_usable_ms':round(r['marks']['usable'],3),'navigation':clean(r['navigation']),'today_js':clean(assets[0]),'first_today_effect_proxy_ms':round(health['start'],3),'required_gate_interval_ms':round(max(x['end'] for x in gates)-min(x['start'] for x in gates),3),'today_fetch_start_ms':round(today['start'],3),'today_fetch_ms':round(today['end']-today['start'],3),'api_today_handler_ms':round(entry['total_ms'],3),'sql_count':entry['sql_count'],'sql_ms':round(entry['sql_ms'],3),'authored_snapshot_calls':sum(v['calls'] for k,v in entry['phases'].items() if k.endswith('.load_authored_history_snapshot')),'script_task_metrics_ms':clean(r['metrics']),'longtask_count':len(r['marks']['longtasks']),'longtask_max_ms':round(max((e['duration'] for e in r['marks']['longtasks']),default=0),3),'api_fetch_paths':[re.sub(r'/workout/[^/]+/(progress|summary)',r'/workout/<occurrence>/\1',x['path']) for x in fetches if x['path'].startswith('/api/')],'non_api_fetch_count':sum(not x['path'].startswith('/api/') for x in fetches),'host_load_before':r['host']['loadavg_before'],'host_load_after':r['host']['loadavg_after'],'page_errors':r['pageErrors'],'request_failures':r['requestFailures'],'http_failures':r['httpFailures']})
old=json.loads(Path('docs/evidence/today-performance-2026-10-23/after-database.json').read_text())['tables'];after=json.loads((q/'db-after.json').read_text());assert all(after[k]==v for k,v in old.items())
olduser=json.loads(Path('.qualification/baseline-scoped-all-tables-private.json').read_text())['users'];assert olduser==after['users']
payloads={}
for r in rows:
 key=f"{r['rep']}-{r['variant']}-{r['scenario']}";body=json.loads((q/('payload-'+key+'-'+r['phase']+'.json')).read_text())
 if r['scenario'] in payloads:assert payloads[r['scenario']]==body
 else:payloads[r['scenario']]=body
proof={'original_checkpoint':'PR112 f79a438 after-database.json and existing private eight-account row checkpoint, recorded2026-10-23','ordinary_accounts':8,'all_ten_training_presentation_tables_unchanged':True,'account_rows_unchanged_private_comparison':True,'complete_today_payloads_compared':96,'all_payloads_equal_by_case_no_field_exclusions':True,'new_pre_measurement_checkpoint_available':False,'checkpoint_limitation':'Initial helper computed SELECT fingerprints but failed to save because env-i removed CLOSEOUT_SNAPSHOT; post-run helper uses an argument and compares original checkpoints. No latency sample excluded.'}
summary=[]
for case in ['customized-small-unstarted','customized-small-inprogress','authored-large-unstarted','authored-large-inprogress']:
 for phase in ['cold','warm']:
  groups={}
  for variant in variants:
   selected=[r for r in compact if r['scenario']==case and r['phase']==phase and r['variant']==variant];assert len(selected)==4
   values=[r['usable_ms'] for r in selected];groups[variant]={'n':4,'median_ms':round(statistics.median(values),3),'min_ms':min(values),'max_ms':max(values)}
  summary.append({'scenario':case,'phase':phase,'groups':groups})
data={'input_pr_head':'f79a4382e92028ec20b452dd409da0c52a48d931','application_revision':'912e7e928960069316e81f01a1df08001b0f2a53','calendar':'2026-10-23T17:00:00Z fixture calendar in browser and routing modules; actual authentication clock unchanged','variants':variants,'fixed_variant_order':[['base','candidate','control'],['control','candidate','base'],['candidate','base','control'],['control','base','candidate']],'summary':summary,'preservation':proof,'samples':compact}
(out/'measurements.json').write_text(json.dumps(data,separators=(',',':'))+'\n')
lines=['| Case | Phase | Base median [min–max] | Candidate median [min–max] | Today revert control median [min–max] |','|---|---|---:|---:|---:|']
for r in summary:
 def cell(v):g=r['groups'][v];return f"{g['median_ms']/1000:.3f} [{g['min_ms']/1000:.3f}–{g['max_ms']/1000:.3f}]"
 lines.append('| '+r['scenario']+' | '+r['phase']+' | '+' | '.join(cell(v) for v in variants)+' |')
(q/'table.md').write_text('\n'.join(lines)+'\n')
print('Validated/published96condensednavigationrecords; matching24strata4samples; originaltraining/accountcheckpointsunchanged')
