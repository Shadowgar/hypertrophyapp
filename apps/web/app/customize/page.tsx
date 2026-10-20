"use client";

import Link from 'next/link';
import {useEffect,useRef,useState} from 'react';
import {CustomizedInventoryEditor} from '@/components/customized-inventory';
import type {InventoryDocument,InventoryVariant} from '@/lib/customized-inventory';
import {Button} from '@/components/ui/button';
import {customizedApi,type CustomizedProposal,type CustomizedRequest,type CustomizedPreview,type CustomizedConsentSummary,type CustomizedWorkload,type CustomizedExecutionSession,type CustomizedReplacement,ApiError} from '@/lib/api';

const initial:CustomizedRequest={mode:'customized',bundle_id:'shorter-current',goal:'hypertrophy',population:'broadly_healthy_adult',
  training_context:'unknown',selected_dates:['','',''],timezone:'',cap_minutes:60,cap_kind:'hard',equipment:[],skill:null,restrictions:null};

function Preview({preview}:{preview:CustomizedPreview}) {
  return <div className="space-y-3"><h2 className="text-xl font-semibold">{preview.candidate_name}</h2>
    <p>{preview.sessions.reduce((n,s)=>n+s.exercises.reduce((m,e)=>m+e.sets,0),0)} weekly working sets</p>
    {preview.sessions.map((s,i)=><section key={s.local_date} className="rounded border border-zinc-700 p-3">
      <h3>Day {i+1} · {s.local_date}</h3><p>Estimated {s.minimum_minutes.toFixed(1)}–{s.maximum_minutes.toFixed(1)} minutes · {s.cap_status==='within_estimated_cap'?'Within estimated cap':'Exceeds or may exceed your cap'}</p>
      <ul>{s.exercises.map(e=><li className="mt-2" key={e.variant_id}><strong>{e.name}</strong> · {e.sets} × {e.reps_min}–{e.reps_max} · target {e.target_min}–{e.target_max} {e.target_scale.toUpperCase()}<br/><span>Rest {e.rest_min_seconds??"unknown"}–{e.rest_max_seconds??"unknown"} seconds</span><br/><span className="text-sm text-zinc-400">Load basis: {e.load_basis.replaceAll('_',' ')}. Calibrate this exercise and actual setup; no starting weight is invented. {e.working_load!=null?`Qualified recorded baseline: ${e.working_load} ${e.load_unit}. `:''}{e.calibration_reasons?.join(', ').replaceAll('_',' ')}</span></li>)}</ul>
    </section>)}
    {preview.missing_actions.length>0&&<p>Unavailable movement coverage: {preview.missing_actions.join(', ')}</p>}
    {preview.dose_conflicts.length>0&&<p>Below provisional direct-work ranges: {preview.dose_conflicts.join(', ')}. These ranges are not proven biological minimums.</p>}
  </div>;
}

function Prescriptions({label,sessions}:{label:string;sessions:CustomizedExecutionSession[]}) {
  return <section className="space-y-3" aria-label={label}><h2 className="text-xl font-semibold">{label}</h2>
    {sessions.map((session,i)=><div className="rounded border border-zinc-700 p-3" key={session.session_id}><h3>Workout {i+1} · {session.date}</h3>
      <ul>{session.exercises.map((exercise,j)=><li className="mt-2" key={exercise.id+j}><strong>{exercise.name}</strong> · {exercise.sets} × {exercise.rep_range?.join('–')??'unknown'}
        {exercise.customized&&<> · target {exercise.customized.target_min}–{exercise.customized.target_max} {exercise.customized.target_kind.toUpperCase()}<br/>Rest {exercise.customized.rest_seconds.low}–{exercise.customized.rest_seconds.high} seconds</>}
        <br/>Working load: {exercise.recommended_working_weight==null?'Calibration required; no starting weight invented':`${exercise.recommended_working_weight} ${exercise.customized?.identity.unit??'kg'}`} · {exercise.customized?.identity.basis.replaceAll('_',' ')??'load basis unknown'}
      </li>)}</ul></div>)}
  </section>;
}
function ReplacementComparison({replacement}:{replacement:CustomizedReplacement}) {
  return <div className="space-y-3 rounded border border-amber-700 p-3"><Prescriptions label="Program being replaced" sessions={replacement.sessions}/>
    <p>{replacement.kind==='future_week'?'Future-week replacement: the current week and performed work remain in history.':'Same-week replacement: the wholly unstarted current program will be superseded only after acceptance and activation.'}</p>
    <h3>Preserved work</h3>{replacement.preserved_work.length?<ul>{replacement.preserved_work.map((work,i)=><li key={work.occurrence_id??work.workout_occurrence_id??i}>{work.scheduled_date??work.date??work.local_date??'Recorded date retained'} · {work.status??'Existing workout and its history retained'}</li>)}</ul>:<p>No started work is listed for this replacement.</p>}
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
    {summary.replacement&&<ReplacementComparison replacement={summary.replacement}/>}
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
  const [options,setOptions]=useState<{equipment:string[];restrictions:string[];inventory_issues?:string[];variants?:InventoryVariant[]}>({equipment:[],restrictions:[]});
  const [inventory,setInventory]=useState<InventoryDocument|null>(null);
  const [proposal,setProposal]=useState<CustomizedProposal|null>(null);
  const [activePlans,setActivePlans]=useState<CustomizedProposal[]>([]);
  const [replacementTarget,setReplacementTarget]=useState<CustomizedProposal|null>(null);
  const [rescheduling,setRescheduling]=useState(false);const [rescheduleDates,setRescheduleDates]=useState<string[]>([]);const [rescheduleTimezone,setRescheduleTimezone]=useState('');
  const [confirmDates,setConfirmDates]=useState(false);
  const [status,setStatus]=useState('');const [busy,setBusy]=useState(false);const [agree,setAgree]=useState(false);
  const [dirty,setDirty]=useState(false);const epoch=useRef(0);const accountEpoch=useRef(0);
  const retries=useRef(new Map<string,string>());
  useEffect(()=>{
    let mounted=true;
    const attempt=epoch.current;
    const timezone=Intl.DateTimeFormat().resolvedOptions().timeZone;
    setDraft(p=>({...p,timezone}));
    const loadOptions=(version:number)=>customizedApi.options().then(o=>{if(mounted&&version===accountEpoch.current){setOptions(o);setInventory(o.inventory??{version:'customized-location-profile-v1',revision:0,profile:null});if(o.inventory?.profile&&!new URL(window.location.href).searchParams.has('proposal'))setDraft(d=>({...d,equipment:o.inventory!.profile!.equipment,inventory_revision:o.inventory!.revision}));}}).catch(e=>{if(mounted&&version===accountEpoch.current)setStatus(e.message);});
    const optionsReady=loadOptions(accountEpoch.current);
    const id=new URL(window.location.href).searchParams.get('proposal');
    if(!id)void optionsReady.then(()=>customizedApi.active()).then(result=>{if(mounted&&attempt===epoch.current&&result.plans?.length){setActivePlans(result.plans);setProposal(result.plans[0]);setDraft(result.plans[0].snapshot.request);}}).catch(e=>{if(mounted&&attempt===epoch.current)setStatus(e.message);});
    if(id)customizedApi.read(id).then(p=>{if(mounted&&attempt===epoch.current){setProposal(p);setDraft(p.snapshot.request);}}).catch(e=>{if(mounted&&attempt===epoch.current)setStatus(e.message);});
    const reset=()=>{
      epoch.current++;accountEpoch.current++;retries.current.clear();setProposal(null);setActivePlans([]);setReplacementTarget(null);setRescheduling(false);setRescheduleDates([]);setConfirmDates(false);setDraft({...initial,timezone});setOptions({equipment:[],restrictions:[]});setInventory(null);
      setAgree(false);setDirty(false);setBusy(false);setStatus('Account changed. Sign in and generate a new preview.');
      const url=new URL(window.location.href);url.searchParams.delete('proposal');window.history.replaceState(null,'',url);
      void loadOptions(accountEpoch.current);
    };
    window.addEventListener('hypertrophy:auth-token-changed',reset);
    return()=>{mounted=false;window.removeEventListener('hypertrophy:auth-token-changed',reset);};
  },[]);
  function edit(change:Partial<CustomizedRequest>){epoch.current++;setConfirmDates(false);setBusy(false);setDraft(p=>({...p,...change}));setAgree(false);setDirty(true);}
  async function action(name:string,fn:(key:string)=>Promise<CustomizedProposal>){
    const attempt=epoch.current;setBusy(true);setStatus('');
    // A lost response reuses exactly this operation/content retry key.
    const identity=JSON.stringify([name,proposal?.proposal_id,proposal?.revision,replacementTarget?.proposal_id,replacementTarget?.revision,draft,inventory?.revision,rescheduleDates,rescheduleTimezone]);
    const key=retries.current.get(identity)??crypto.randomUUID();retries.current.set(identity,key);
    try{const p=await fn(key);if(attempt!==epoch.current)return;setProposal(p);setAgree(false);setDirty(false);setConfirmDates(false);
      if(name==='reschedule-confirm')setRescheduling(false);
      if(p.state==='active'){setReplacementTarget(null);setDraft(p.snapshot.request);setActivePlans(plans=>[...plans.filter(old=>old.proposal_id!==p.proposal_id&&!(p.snapshot.replacement?.kind==='same_week_unstarted'&&old.proposal_id===p.snapshot.replacement.proposal_id)),p]);}
      const url=new URL(window.location.href);url.searchParams.set('proposal',p.proposal_id);window.history.replaceState(null,'',url);
      setStatus(p.state==='active'?(name==='reschedule-confirm'?'Dates updated. Week and Today now use the new placement.':'Active program loaded. Your current dates route to Today.'):`Program version ${p.plan_version} · ${p.state.replaceAll('_',' ')}`);
     }catch(e){if(attempt===epoch.current){setStatus(e instanceof Error?e.message:'Request failed. Retry safely.');
      if(e instanceof ApiError&&(e.status===409||e.status===403)){setAgree(false);setConfirmDates(false);setRescheduling(false);setReplacementTarget(null);setProposal(p=>p?{...p,challenge:undefined,terms:undefined,pending_reschedule:undefined}:null);retries.current.clear();
        const refresh=proposal?.snapshot.replacement?.proposal_id??proposal?.proposal_id??replacementTarget?.proposal_id;
        if(refresh)try{const current=await customizedApi.read(refresh);if(attempt===epoch.current){setProposal(current);setDraft(current.snapshot.request);setDirty(false);}}catch{/* Keep conflict visible and require a fresh read. */}
      }
    }}
    finally{if(attempt===epoch.current)setBusy(false);}
  }
  const generationRequest={...draft,...(inventory?{inventory_revision:inventory.revision}:{})};
  const valid=draft.training_context!=='unknown'&&draft.skill!==null&&draft.restrictions!==null&&draft.equipment.length>0&&draft.timezone!==''&&draft.selected_dates.every(Boolean)&&new Set(draft.selected_dates).size===3;
  const frozen=proposal?.state==='active';
  const placement=proposal?.active_placement;
  function chooseActive(p:CustomizedProposal){epoch.current++;setProposal(p);setDraft(p.snapshot.request);setReplacementTarget(null);setRescheduling(false);setAgree(false);setConfirmDates(false);setDirty(false);setBusy(false);setStatus('');const url=new URL(window.location.href);url.searchParams.set('proposal',p.proposal_id);window.history.replaceState(null,'',url);}
  function editDates(change:{dates?:string[];timezone?:string}){epoch.current++;setBusy(false);setConfirmDates(false);if(change.dates)setRescheduleDates(change.dates);if(change.timezone!==undefined)setRescheduleTimezone(change.timezone);setProposal(p=>p?{...p,pending_reschedule:undefined}:p);}

  return <section aria-label="Customized program" className="mx-auto min-w-0 max-w-3xl space-y-5 break-words p-4 pb-24">
    <h1 className="text-2xl font-semibold">Customize My Workout</h1>
    <p>Original three-day Full Body hypertrophy training. Your choice grants programming permission only for the version you preview and accept. Existing Authored workouts and history are retained.</p>
    <p>Equipment, skill, restrictions, dates, time cap and training context control this program. Body measurements, weak-point priorities and recovery modifiers do not change this bounded design. No exercise scoring or personal-response optimization is enabled.</p>
    <p className="text-amber-200">Training rules remain provisional. Session times are estimates; equal or optimal results are not established. This option covers broadly healthy adults. Missing equipment, movement restrictions or skill may make it infeasible.</p>
    <p><Link href="/onboarding" className="underline">Sign in or finish onboarding</Link> · <Link href="/week" className="underline">Week</Link> · <Link href="/today" className="underline">Today</Link></p>
    {activePlans.length>1&&<nav aria-label="Active Customized weeks" className="flex flex-wrap gap-2">{activePlans.map(p=><Button key={p.proposal_id} disabled={busy} onClick={()=>chooseActive(p)}>{p.active_placement?.dates[0]??p.snapshot.request.selected_dates[0]} · view active program</Button>)}</nav>}
    {replacementTarget&&!proposal&&<div className="space-y-2"><p role="status">Preparing an explicit replacement. The active program remains in place until you accept and activate the replacement. For started weeks, choose dates in the next week.</p><Button variant="ghost" disabled={busy} onClick={()=>chooseActive(replacementTarget)}>Cancel replacement</Button></div>}
    {frozen&&placement&&<div className="space-y-4">
      <Prescriptions label="Current scheduled program" sessions={placement.sessions}/><p>Placement revision {placement.placement_revision} · {placement.timezone}. Started, completed and materialized workout dates stay fixed.</p>
      <div className="flex flex-wrap gap-3"><Button disabled={busy} onClick={()=>{epoch.current++;setRescheduling(true);setRescheduleDates(placement.dates);setRescheduleTimezone(placement.timezone);setConfirmDates(false);setProposal(p=>p?{...p,pending_reschedule:undefined}:p);}}>Change training dates</Button>
      <Button disabled={busy} onClick={()=>{epoch.current++;setReplacementTarget(proposal);setRescheduling(false);setConfirmDates(false);setProposal(null);setAgree(false);setDirty(false);setDraft({...proposal.snapshot.request,selected_dates:placement.dates,timezone:placement.timezone,...(inventory?{inventory_revision:inventory.revision}:{}),...(inventory?.profile?{equipment:inventory.profile.equipment}:{})});}}>Replace active program</Button></div>
      {rescheduling&&<section aria-label="Reschedule active program" className="space-y-3 rounded border border-zinc-700 p-3"><h2>Change dates, preserve the exact program</h2><p>Only unstarted workouts can move. The server rechecks spacing, timezone, neighboring weeks and recorded work before confirmation.</p>
        <label>Reschedule timezone<input aria-label="Reschedule timezone" disabled={busy} className="ui-input block w-full" value={rescheduleTimezone} onChange={e=>editDates({timezone:e.target.value})}/></label>
        <div className="grid gap-3 sm:grid-cols-3">{rescheduleDates.map((date,i)=><label key={i}>New workout date {i+1}<input aria-label={`New workout date ${i+1}`} className="ui-input block w-full min-w-0" type="date" disabled={busy||placement.frozen_dates.includes(placement.dates[i])} value={date} onChange={e=>editDates({dates:rescheduleDates.map((d,j)=>i===j?e.target.value:d)})}/>{placement.frozen_dates.includes(placement.dates[i])&&<span>Date fixed to preserve recorded work</span>}</label>)}</div>
        <Button disabled={busy||!rescheduleTimezone||rescheduleDates.some(d=>!d)||new Set(rescheduleDates).size!==rescheduleDates.length} onClick={()=>action('reschedule-preview',key=>customizedApi.previewReschedule(proposal,rescheduleDates,rescheduleTimezone,key))}>Preview date changes</Button>
        {proposal.pending_reschedule&&<div className="space-y-3"><h3>Proposed dates · {proposal.pending_reschedule.timezone??rescheduleTimezone}</h3><ul>{proposal.pending_reschedule.selected_dates.map((date,i)=><li key={i}>Workout {i+1}: {placement.dates[i]} → {date}{placement.frozen_dates.includes(placement.dates[i])?' · preserved':''}</li>)}</ul><p>Exercises, sets, repetitions, rest targets and prescribed loads are unchanged.</p>
          <label className="flex min-h-11 items-center gap-3"><input aria-label="I confirm these exact date changes" type="checkbox" checked={confirmDates} disabled={busy} onChange={e=>setConfirmDates(e.target.checked)}/>I confirm these exact date changes.</label>
          <Button disabled={busy||!confirmDates} onClick={()=>action('reschedule-confirm',key=>customizedApi.confirmReschedule(proposal,key))}>Confirm date changes</Button></div>}
        <Button variant="ghost" disabled={busy} onClick={()=>{epoch.current++;setRescheduling(false);setConfirmDates(false);setProposal(p=>p?{...p,pending_reschedule:undefined}:p);}}>Cancel date changes</Button>
      </section>}
    </div>}
    {options.inventory_issues&&<details><summary className="min-h-11 cursor-pointer py-2">Saved inventory limitations</summary><ul>{options.inventory_issues.map((issue,i)=><li key={i}>{issue}</li>)}</ul></details>}
    <CustomizedInventoryEditor document={inventory} equipment={draft.equipment} variants={options.variants??[]} onSaved={document=>{setInventory(document);setOptions(o=>({...o,inventory_issues:undefined}));const version=accountEpoch.current;void customizedApi.options().then(o=>{if(version===accountEpoch.current)setOptions(o);}).catch(()=>{});edit({equipment:document.profile?.equipment??[],inventory_revision:document.revision});setStatus('Inventory saved. Generate a new preview before accepting availability changes.');}}/>
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
      <Button disabled={!valid||busy||frozen} onClick={()=>action('generate',key=>proposal?customizedApi.revise(proposal,generationRequest,key):replacementTarget?customizedApi.replacement(replacementTarget,generationRequest,key):customizedApi.create(generationRequest,key))}>{replacementTarget||proposal?.snapshot.replacement?'Generate replacement preview':'Generate preview'}</Button>
    </fieldset>
    {status&&<p role="status">{status}</p>}
    {proposal&&<>
      <p>Program version {proposal.plan_version} · revision {proposal.revision}</p>
      {dirty&&<p>Inputs changed. Generate a new preview before accepting.</p>}
      {proposal.snapshot.replacement&&!(proposal.terms?.summary?.replacement&&!dirty)&&<ReplacementComparison replacement={proposal.snapshot.replacement}/>}
      {frozen&&<h2>Original accepted program snapshot</h2>}
      <Preview preview={proposal.snapshot.preview}/>
      {proposal.snapshot.comparison_reference&&<details><summary className="min-h-11 cursor-pointer py-3">Compare the longer program and workload differences</summary><Preview preview={proposal.snapshot.comparison_reference}/><ul>{proposal.snapshot.workload_changes.map(c=><li key={c.local_date+c.variant_id}>{c.local_date} · {c.variant_id.replaceAll('_',' ')}: {c.reference_sets} → {c.candidate_sets} working sets</li>)}</ul><p>Less work may mean less hypertrophy opportunity. No claim of equivalent results.</p></details>}
      {proposal.blocking_reasons.length>0&&<p>Resolve before acceptance: {proposal.blocking_reasons.join(', ').replaceAll('_',' ')}</p>}
      {!frozen&&proposal.state!=='accepted_candidate'&&<Button disabled={busy||dirty||proposal.blocking_reasons.length>0} onClick={()=>action('challenge',key=>customizedApi.challenge(proposal,key))}>Review acceptance</Button>}
      {!frozen&&proposal.state!=='accepted_candidate'&&proposal.challenge&&!dirty&&<div className="space-y-3 rounded border border-amber-700 p-3"><p>{proposal.terms?.text}</p>{proposal.terms?.summary&&<ConsentSummary summary={proposal.terms.summary}/>}<label className="flex items-start gap-3"><input aria-label={proposal.snapshot.replacement?"I accept replacement of this active program":"I accept this exact program version"} type="checkbox" checked={agree} disabled={busy} onChange={e=>setAgree(e.target.checked)}/>{proposal.snapshot.replacement?"I explicitly accept replacement of this active program, the exact proposed version, affected dates and preservation of recorded work.":"I accept this exact program version and the complete workload comparison."}</label><Button disabled={!agree||busy||!proposal.terms?.summary} onClick={()=>action('accept',key=>customizedApi.accept(proposal,key))}>Accept program</Button></div>}
      {proposal.state==='accepted_candidate'&&!dirty&&<Button disabled={busy} onClick={()=>action('activate',key=>customizedApi.activate(proposal,key))}>Activate selected dates</Button>}
      {!frozen&&<Button variant="ghost" disabled={busy||dirty} onClick={()=>action('decline',async key=>{const declined=await customizedApi.decline(proposal,key);return proposal.snapshot.replacement?customizedApi.read(proposal.snapshot.replacement.proposal_id):declined;})}>Decline</Button>}
      {frozen&&<p><Link className="underline" href="/today">Open Today&apos;s Workout</Link>. Your program snapshot and consent remain in history. On rest days Today shows no scheduled workout.</p>}
    </>}
  </section>;
}
