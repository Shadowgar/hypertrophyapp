"use client";

import Link from 'next/link';
import {useEffect,useRef,useState} from 'react';
import {Button} from '@/components/ui/button';
import {customizedApi,type CustomizedProposal,type CustomizedRequest,type CustomizedPreview,type CustomizedConsentSummary,type CustomizedWorkload} from '@/lib/api';

const initial:CustomizedRequest={mode:'customized',bundle_id:'shorter-current',goal:'hypertrophy',population:'broadly_healthy_adult',
  training_context:'unknown',selected_dates:['','',''],timezone:'',cap_minutes:60,cap_kind:'hard',equipment:[],skill:null,restrictions:null};

function Preview({preview}:{preview:CustomizedPreview}) {
  return <div className="space-y-3"><h2 className="text-xl font-semibold">{preview.candidate_name}</h2>
    <p>{preview.sessions.reduce((n,s)=>n+s.exercises.reduce((m,e)=>m+e.sets,0),0)} weekly working sets</p>
    {preview.sessions.map((s,i)=><section key={s.local_date} className="rounded border border-zinc-700 p-3">
      <h3>Day {i+1} · {s.local_date}</h3><p>Estimated {s.minimum_minutes.toFixed(1)}–{s.maximum_minutes.toFixed(1)} minutes · {s.cap_status==='within_estimated_cap'?'Within estimated cap':'Exceeds or may exceed your cap'}</p>
      <ul>{s.exercises.map(e=><li className="mt-2" key={e.variant_id}><strong>{e.name}</strong> · {e.sets} × {e.reps_min}–{e.reps_max} · target {e.target_min}–{e.target_max} {e.target_scale.toUpperCase()}<br/><span className="text-sm text-zinc-400">Load basis: {e.load_basis.replaceAll('_',' ')}. Calibrate this exercise and actual setup; no starting weight is invented.</span></li>)}</ul>
    </section>)}
    {preview.missing_actions.length>0&&<p>Unavailable movement coverage: {preview.missing_actions.join(', ')}</p>}
    {preview.dose_conflicts.length>0&&<p>Below provisional direct-work ranges: {preview.dose_conflicts.join(', ')}. These ranges are not proven biological minimums.</p>}
  </div>;
}

function Workload({label,workload}:{label:string;workload:CustomizedWorkload}) {
  return <div><h3 className="font-semibold">{label}: {workload.name}</h3>
    <p>{workload.weekly_sets} weekly working sets · {workload.timezone} · {workload.cap_kind} cap {workload.cap_minutes} minutes</p>
    <ul>{workload.dates.map((d,i)=><li key={d}>{d}: {workload.daily_sets[i]} sets · estimated {workload.minimum_minutes[i]}–{workload.upper_minutes[i]} minutes</li>)}</ul>
  </div>;
}

function ConsentSummary({summary}:{summary:CustomizedConsentSummary}) {
  return <div className="space-y-3" aria-label="Complete version-bound program comparison">
    <Workload label="Selected program" workload={summary.candidate}/>
    {summary.reference&&<Workload label="Comparison program" workload={summary.reference}/>}
    {summary.workload_changes.length>0&&<details><summary className="min-h-11 cursor-pointer py-3">All exercise workload changes for this version</summary>
      <ul>{summary.workload_changes.map(c=><li key={c.local_date+c.variant_id}>{c.local_date} · {c.exercise_name}: {c.reference_sets} → {c.candidate_sets} sets ({c.removed_sets} removed)</li>)}</ul></details>}
    {([['Selected program',summary.proposed_range_conflicts],['Comparison program',summary.alternative_range_conflicts]] as const).map(([label,conflicts])=>conflicts.length>0&&<div key={label}>
      <h3>{label}: provisional direct-work range conflicts</h3>
      <p>These ranges are unapproved assumptions, not established biological minimums. Secondary work does not cancel these differences.</p>
      <ul>{conflicts.map(c=><li key={c.region}><p>{c.region.replaceAll('_',' ')}: {c.primary_sets} direct sets; provisional range {c.proposed_minimum}–{c.proposed_maximum}</p><p className="text-sm">{c.interpretation}</p></li>)}</ul>
    </div>)}
    <details><summary className="min-h-11 cursor-pointer py-3">Timing assumptions for this version</summary>
      <p>Estimates include these phases. Queues and individual pace can exceed the estimated upper duration; it is not a measured guarantee.</p>
      {summary.timing_assumptions.map(s=><div key={s.local_date}><h4>{s.local_date}</h4><ul>{Object.entries(s.phases).filter(([phase,bounds])=>phase.endsWith('_seconds')&&typeof bounds==='object').map(([phase,bounds])=>typeof bounds==='object'&&<li key={phase}>{phase.replace(/_seconds$/,'').replaceAll('_',' ')}: {bounds.low}–{bounds.high} seconds</li>)}</ul></div>)}
    </details>
    <p>{summary.explanation}</p><ul>{summary.limitations.map((l,i)=><li key={i}>{l.replaceAll('_',' ')}</li>)}</ul>
    <h3>Alternatives before activation</h3><ul>{summary.alternatives.map((a,i)=><li key={i}>{a}</li>)}</ul>
  </div>;
}

export default function CustomizedPage() {
  const [draft,setDraft]=useState(initial);
  const [options,setOptions]=useState<{equipment:string[];restrictions:string[]}>({equipment:[],restrictions:[]});
  const [proposal,setProposal]=useState<CustomizedProposal|null>(null);
  const [status,setStatus]=useState('');const [busy,setBusy]=useState(false);const [agree,setAgree]=useState(false);
  const [dirty,setDirty]=useState(false);const epoch=useRef(0);const accountEpoch=useRef(0);
  const retries=useRef(new Map<string,string>());
  useEffect(()=>{
    let mounted=true;
    const attempt=epoch.current;
    const timezone=Intl.DateTimeFormat().resolvedOptions().timeZone;
    setDraft(p=>({...p,timezone}));
    const loadOptions=(version:number)=>customizedApi.options().then(o=>{if(mounted&&version===accountEpoch.current)setOptions(o);}).catch(e=>{if(mounted&&version===accountEpoch.current)setStatus(e.message);});
    void loadOptions(accountEpoch.current);
    const id=new URL(window.location.href).searchParams.get('proposal');
    if(id)customizedApi.read(id).then(p=>{if(mounted&&attempt===epoch.current){setProposal(p);setDraft(p.snapshot.request);}}).catch(e=>{if(mounted&&attempt===epoch.current)setStatus(e.message);});
    const reset=()=>{
      epoch.current++;accountEpoch.current++;retries.current.clear();setProposal(null);setDraft({...initial,timezone});setOptions({equipment:[],restrictions:[]});
      setAgree(false);setDirty(false);setBusy(false);setStatus('Account changed. Sign in and generate a new preview.');
      const url=new URL(window.location.href);url.searchParams.delete('proposal');window.history.replaceState(null,'',url);
      void loadOptions(accountEpoch.current);
    };
    window.addEventListener('hypertrophy:auth-token-changed',reset);
    return()=>{mounted=false;window.removeEventListener('hypertrophy:auth-token-changed',reset);};
  },[]);
  function edit(change:Partial<CustomizedRequest>){epoch.current++;setDraft(p=>({...p,...change}));setAgree(false);setDirty(true);}
  async function action(name:string,fn:(key:string)=>Promise<CustomizedProposal>){
    const attempt=epoch.current;setBusy(true);setStatus('');
    // A lost response reuses exactly this operation/content retry key.
    const identity=JSON.stringify([name,proposal?.proposal_id,proposal?.revision,draft]);
    const key=retries.current.get(identity)??crypto.randomUUID();retries.current.set(identity,key);
    try{const p=await fn(key);if(attempt!==epoch.current)return;setProposal(p);setAgree(false);setDirty(false);
      const url=new URL(window.location.href);url.searchParams.set('proposal',p.proposal_id);window.history.replaceState(null,'',url);
      setStatus(p.state==='active'?'Activated. Your selected dates now route to Today.':`Program version ${p.plan_version} · ${p.state.replaceAll('_',' ')}`);
    }catch(e){if(attempt===epoch.current)setStatus(e instanceof Error?e.message:'Request failed. Retry safely.');}
    finally{if(attempt===epoch.current)setBusy(false);}
  }
  const valid=draft.training_context!=='unknown'&&draft.skill!==null&&draft.restrictions!==null&&draft.equipment.length>0&&draft.timezone!==''&&draft.selected_dates.every(Boolean)&&new Set(draft.selected_dates).size===3;
  const frozen=proposal?.state==='active';
  return <section aria-label="Customized program" className="mx-auto min-w-0 max-w-3xl space-y-5 break-words p-4 pb-24">
    <h1 className="text-2xl font-semibold">Customize My Workout</h1>
    <p>Original three-day Full Body hypertrophy training. Your choice grants programming permission only for the version you preview and accept. Existing Authored workouts and history are retained.</p>
    <p>Equipment, skill, restrictions, dates, time cap and training context control this program. Body measurements, weak-point priorities and recovery modifiers do not change this bounded design. No exercise scoring or personal-response optimization is enabled.</p>
    <p className="text-amber-200">Training rules remain provisional. Session times are estimates; equal or optimal results are not established. This option covers broadly healthy adults. Missing equipment, movement restrictions or skill may make it infeasible.</p>
    <p><Link href="/onboarding" className="underline">Sign in or finish onboarding</Link> · <Link href="/week" className="underline">Week</Link> · <Link href="/today" className="underline">Today</Link></p>
    <fieldset disabled={busy||frozen} className="space-y-4">
      <label className="block">Training context<select aria-label="Training context" className="ui-input block w-full" value={draft.training_context} onChange={e=>{const training_context=e.target.value;edit({training_context,bundle_id:training_context==='current'?'shorter-current':`longer-${training_context}`});}}>
        <option value="unknown">Choose your current context</option><option value="new">New to consistent resistance training</option><option value="returning">Returning after a break</option><option value="current">Currently training consistently</option></select></label>
      <label className="block">Exercise skill<select aria-label="Exercise skill" className="ui-input block w-full" value={draft.skill??''} onChange={e=>edit({skill:e.target.value||null})}><option value="">Confirm your exercise skill</option><option value="basic">Basic supported exercises</option><option value="intermediate">Comfortable with dumbbell hinges and presses</option><option value="advanced">Advanced</option></select></label>
      {draft.training_context==='current'&&<label className="block">Workload option<select className="ui-input block w-full" value={draft.bundle_id} onChange={e=>edit({bundle_id:e.target.value})}><option value="shorter-current">Shorter gym option · reduced direct work</option><option value="longer-current">Longer comparison · more direct work</option></select></label>}
      <label className="block">Hard session limit (minutes)<input aria-label="Hard session limit (minutes)" className="ui-input block w-full" type="number" min={15} max={240} value={draft.cap_minutes} onChange={e=>edit({cap_minutes:Number(e.target.value)})}/></label>
      <fieldset><legend>Confirm equipment you can actually use</legend><div className="grid grid-cols-2 gap-2">{options.equipment.map(e=><label key={e} className="flex min-h-11 items-center gap-2"><input aria-label={e} type="checkbox" checked={draft.equipment.includes(e)} onChange={()=>edit({equipment:draft.equipment.includes(e)?draft.equipment.filter(x=>x!==e):[...draft.equipment,e]})}/>{e.replaceAll('_',' ')}</label>)}</div></fieldset>
      <fieldset><legend>Movement restrictions</legend><label className="flex min-h-11 items-center gap-2"><input aria-label="No movement restrictions" type="checkbox" checked={draft.restrictions?.length===0} onChange={e=>edit({restrictions:e.target.checked?[]:null})}/>No movement restrictions</label>
        <div className="grid grid-cols-1 gap-1 sm:grid-cols-2">{options.restrictions.map(r=><label key={r} className="flex min-h-11 items-center gap-2"><input type="checkbox" checked={draft.restrictions?.includes(r)??false} onChange={()=>edit({restrictions:draft.restrictions?.includes(r)?draft.restrictions.filter(x=>x!==r):[...(draft.restrictions??[]),r]})}/>{r.replaceAll('_',' ')}</label>)}</div></fieldset>
      <label className="block">IANA timezone<input aria-label="IANA timezone" className="ui-input block w-full" value={draft.timezone} onChange={e=>edit({timezone:e.target.value})}/></label>
      <p>Choose three dates in the current or next local Monday–Sunday week, with at least one day between workouts. Unknown neighboring weeks do not establish safe recovery. Occupied or ambiguous weeks require resolution.</p>
      <div className="grid gap-3 sm:grid-cols-3">{draft.selected_dates.map((d,i)=><label key={i}>Workout date {i+1}<input aria-label={`Workout date ${i+1}`} className="ui-input block w-full min-w-0" type="date" value={d} onChange={e=>edit({selected_dates:draft.selected_dates.map((x,j)=>j===i?e.target.value:x)})}/></label>)}</div>
      <Button disabled={!valid||busy||frozen} onClick={()=>action('generate',key=>proposal?customizedApi.revise(proposal,draft,key):customizedApi.create(draft,key))}>Generate preview</Button>
    </fieldset>
    {status&&<p role="status">{status}</p>}
    {proposal&&<>
      <p>Program version {proposal.plan_version} · revision {proposal.revision}</p>
      {dirty&&<p>Inputs changed. Generate a new preview before accepting.</p>}
      <Preview preview={proposal.snapshot.preview}/>
      {proposal.snapshot.comparison_reference&&<details><summary className="min-h-11 cursor-pointer py-3">Compare the longer program and workload differences</summary><Preview preview={proposal.snapshot.comparison_reference}/><ul>{proposal.snapshot.workload_changes.map(c=><li key={c.local_date+c.variant_id}>{c.local_date} · {c.variant_id.replaceAll('_',' ')}: {c.reference_sets} → {c.candidate_sets} working sets</li>)}</ul><p>Less work may mean less hypertrophy opportunity. No claim of equivalent results.</p></details>}
      {proposal.blocking_reasons.length>0&&<p>Resolve before acceptance: {proposal.blocking_reasons.join(', ').replaceAll('_',' ')}</p>}
      {!frozen&&proposal.state!=='accepted_candidate'&&<Button disabled={busy||dirty||proposal.blocking_reasons.length>0} onClick={()=>action('challenge',key=>customizedApi.challenge(proposal,key))}>Review acceptance</Button>}
      {proposal.challenge&&!dirty&&<div className="space-y-3 rounded border border-amber-700 p-3"><p>{proposal.terms?.text}</p>{proposal.terms?.summary&&<ConsentSummary summary={proposal.terms.summary}/>}<label className="flex items-start gap-3"><input aria-label="I accept this exact program version" type="checkbox" checked={agree} disabled={busy} onChange={e=>setAgree(e.target.checked)}/>I accept this exact program version and the complete workload comparison.</label><Button disabled={!agree||busy||!proposal.terms?.summary} onClick={()=>action('accept',key=>customizedApi.accept(proposal,key))}>Accept program</Button></div>}
      {proposal.state==='accepted_candidate'&&!dirty&&<Button disabled={busy} onClick={()=>action('activate',key=>customizedApi.activate(proposal,key))}>Activate selected dates</Button>}
      {!frozen&&<Button variant="ghost" disabled={busy||dirty} onClick={()=>action('decline',key=>customizedApi.decline(proposal,key))}>Decline</Button>}
      {frozen&&<p><Link className="underline" href="/today">Open Today&apos;s Workout</Link>. Your program snapshot and consent remain in history. On rest days Today shows no scheduled workout.</p>}
    </>}
  </section>;
}
