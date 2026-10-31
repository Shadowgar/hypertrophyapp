"use client";

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useRef, useState } from 'react';
import { api, ApiError, getProgramDisplayName, getToken, type TrainingEnrollmentInput, type TrainingEnrollmentPreview } from '@/lib/api';
import { accountScope } from '@/lib/appearance';
import { acknowledgeLogCommand, pendingLogPayload, retainLogPayload } from '@/lib/workout-identity';
import { trainingRecoveryBlocked } from '@/components/flexible-training';
import { WorkoutWorkload } from '@/components/workout-workload';

type EnrollmentCommand = TrainingEnrollmentInput & {preview_digest:string;command_id:string;confirmed:true};
const authoredPrograms=['pure_bodybuilding_phase_1_full_body','pure_bodybuilding_phase_2_full_body'];

export default function TrainingSetupPage() {
  const router=useRouter();
  const [token,setToken]=useState<string|null|undefined>(undefined);
  const [loading,setLoading]=useState(true);
  const [loaded,setLoaded]=useState(false);
  const [program,setProgram]=useState('');
  const [timezone,setTimezone]=useState('UTC');
  const [expectation,setExpectation]=useState('');
  const [legacyPlan,setLegacyPlan]=useState<string|null>(null);
  const [hasLegacyPlan,setHasLegacyPlan]=useState(false);
  const [enrolled,setEnrolled]=useState(false);
  const [preview,setPreview]=useState<TrainingEnrollmentPreview|null>(null);
  const [previewInput,setPreviewInput]=useState<TrainingEnrollmentInput|null>(null);
  const [confirmed,setConfirmed]=useState(false);
  const [pending,setPending]=useState<EnrollmentCommand|null>(null);
  const [busy,setBusy]=useState(false);
  const [notice,setNotice]=useState('');
  const [reload,setReload]=useState(0);
  const epoch=useRef(0);
  const invalidateEpoch=useCallback(()=>{++epoch.current;},[]);
  const inFlight=useRef(false);
  const commandKey=`hypertrophy_training_enroll_v1:${accountScope(token??null)??'guest'}`;
  useEffect(()=>{
    const sync=()=>setToken(getToken());sync();
    window.addEventListener('hypertrophy:auth-token-changed',sync);window.addEventListener('storage',sync);window.addEventListener('focus',sync);
    return()=>{window.removeEventListener('hypertrophy:auth-token-changed',sync);window.removeEventListener('storage',sync);window.removeEventListener('focus',sync);};
  },[]);
  useEffect(()=>{
    const generation=++epoch.current;let active=true;
    const current=()=>active&&generation===epoch.current&&getToken()===token;
    setPreview(null);setPreviewInput(null);setConfirmed(false);setLoading(true);setLoaded(false);setNotice('');setBusy(false);inFlight.current=false;
    setPending(pendingLogPayload<EnrollmentCommand>(commandKey));
    if(!token){setLoading(false);return;}
    const fallback=Intl.DateTimeFormat().resolvedOptions().timeZone||'UTC';
    void Promise.all([api.getProfile(),api.getSchedulingContext(fallback),api.getSchedulingContext(fallback,1),api.getNextTraining()]).then(([profile,calendar,upcoming,next])=>{
      if(!current())return;
      setProgram(authoredPrograms.includes(profile.selected_program_id??'')?profile.selected_program_id!:'');
      setTimezone(profile.scheduling_timezone||calendar.timezone||fallback);
      setExpectation(profile.expected_sessions_per_week?.toString()??'');
      // Discovery is limited to the two supported calendar windows. The
      // server's guarded preview still owns eligibility across ALL outstanding
      // work, including ambiguous reservations outside these visible windows.
      const reservation=calendar.plan??upcoming.plan;
      setHasLegacyPlan(Boolean(reservation));
      setLegacyPlan(reservation?.plan_id??null);
      setEnrolled(Boolean(next.mode==='flexible'&&next.sequence_id&&next.state!=='retired'&&next.state!=='finished'));
      setLoaded(true);
    }).catch(()=>{if(current())setNotice('Could not verify your saved program and reservations. Retry before changing your training.');})
      .finally(()=>{if(current())setLoading(false);});
    return()=>{active=false;invalidateEpoch();};
  },[token,commandKey,reload,invalidateEpoch]);

  function permitted(){return Boolean(token)&&getToken()===token&&!trainingRecoveryBlocked(token??null);}
  function invalidate(){setPreview(null);setPreviewInput(null);setConfirmed(false);}
  async function review(){
    if(inFlight.current||!permitted()||pending||!loaded)return;
    if(!authoredPrograms.includes(program)){setNotice('Select an explicit Authored phase before previewing.');return;}
    if(expectation!==''&&(!Number.isInteger(Number(expectation))||Number(expectation)<1||Number(expectation)>7)){setNotice('Expected frequency must be a whole number from 1 to 7, or left blank.');return;}
    try {new Intl.DateTimeFormat('en-US',{timeZone:timezone}).format();} catch {setNotice('Enter a valid IANA timezone.');return;}
    if(hasLegacyPlan&&!legacyPlan){setNotice('The saved reservation identity is unavailable. Review Week before switching; no work was changed.');return;}
    const input:TrainingEnrollmentInput={program_id:program,timezone,expected_sessions_per_week:expectation===''?null:Number(expectation),switch_plan_id:legacyPlan};
    const generation=epoch.current;inFlight.current=true;setBusy(true);invalidate();setNotice('');
    try{const value=await api.previewTrainingEnrollment(input);if(generation!==epoch.current||getToken()!==token)return;setPreview(value);setPreviewInput(input);setLegacyPlan(value.legacy_plan_id??null);setHasLegacyPlan(Boolean(value.legacy_plan_id));}
    catch(error){if(generation===epoch.current&&getToken()===token)setNotice(error instanceof Error?error.message:'The preview could not be checked. No enrollment was created.');}
    finally{if(generation===epoch.current&&getToken()===token){inFlight.current=false;setBusy(false);}}
  }
  async function enroll(retry?:EnrollmentCommand){
    if(inFlight.current||!permitted()||(!retry&&(!confirmed||!preview?.available||!previewInput)))return;
    const payload=retry??retainLogPayload<EnrollmentCommand>(commandKey,{...previewInput!,preview_digest:preview!.digest,command_id:crypto.randomUUID(),confirmed:true});
    const generation=epoch.current;inFlight.current=true;setBusy(true);setPending(payload);
    try{await api.enrollTraining(payload);if(generation!==epoch.current||getToken()!==token)return;acknowledgeLogCommand(commandKey);setPending(null);router.push('/today');}
    catch(error){
      if(generation!==epoch.current||getToken()!==token)return;
      if(error instanceof ApiError&&[409,422].includes(error.status)){acknowledgeLogCommand(commandKey);setPending(null);invalidate();setNotice(`${error.message} Review a new preview before confirming.`);}
      else setNotice('Enrollment not confirmed. Retry the original enrollment before changing your choices.');
    }finally{if(generation===epoch.current&&getToken()===token){inFlight.current=false;setBusy(false);}}
  }

  if(token===undefined||loading)return <p role="status">Checking your training setup…</p>;
  if(!token)return <section className="ux-card space-y-3"><h1>Flexible training</h1><p>Sign in to review your own saved training.</p><Link href="/login?next=%2Ftraining%2Fsetup">Sign in</Link></section>;
  return <div className="mx-auto max-w-3xl space-y-5">
    <h1>{hasLegacyPlan?'Switch to Flexible':'Set up Flexible training'}</h1>
    <p className="ux-muted">Follow original source workouts at your pace. Dates are optional; expected frequency never compresses their exercises, sets or instructions.</p>
    {notice?<p role="status" className="ux-card">{notice}</p>:null}
    {trainingRecoveryBlocked(token)?<p role="alert">Resolve your pending set or undo in Today before changing training.</p>:null}
    {pending?<button className="ux-button ux-button-primary" disabled={busy||trainingRecoveryBlocked(token)} onClick={()=>void enroll(pending)}>Retry original enrollment</button>:null}
    {!loaded?<button className="ux-button ux-button-secondary" onClick={()=>setReload(value=>value+1)}>Retry training setup</button>:enrolled?<section className="ux-card"><p>You already have a current Flexible program. Continue it in Today.</p><Link href="/today">Open Today</Link></section>:<>
      <form className="ux-card space-y-4" onSubmit={event=>{event.preventDefault();void review();}}>
        <label className="block">Authored program<select className="ux-input" required value={program} disabled={busy||Boolean(pending)} onChange={event=>{setProgram(event.target.value);invalidate();}}><option value="">Choose an explicit phase</option>{authoredPrograms.map(id=><option key={id} value={id}>{getProgramDisplayName({id})}</option>)}</select></label>
        <label className="block">Program timezone<input className="ux-input" required value={timezone} disabled={busy||Boolean(pending)} onChange={event=>{setTimezone(event.target.value);invalidate();}} /></label>
        <label className="block">Expected sessions per week (optional)<select className="ux-input" value={expectation} disabled={busy||Boolean(pending)} onChange={event=>{setExpectation(event.target.value);invalidate();}}><option value="">No expectation set</option>{[1,2,3,4,5,6,7].map(count=><option key={count} value={count}>{count}</option>)}</select></label>
        <p className="ux-muted">This is an expectation, not a weekly quota or a promise about workout duration.</p>
        {hasLegacyPlan?<p>Switching is available only for an entirely unstarted, conflict-free Authored reservation. Any activity or consent snapshot blocks conversion; nothing is silently abandoned.</p>:null}
        {legacyPlan?<p>Calendar reservation to review: <code>{legacyPlan}</code>. The preview checks eligibility before you can confirm the switch.</p>:null}
        <button className="ux-button ux-button-primary" disabled={busy||Boolean(pending)||trainingRecoveryBlocked(token)} type="submit">{busy?'Checking preview…':hasLegacyPlan?'Preview Switch to Flexible':'Preview Flexible'}</button>
      </form>
      {preview?<section className="ux-card space-y-4" aria-label="Flexible enrollment preview">
        <h2>Review original source workouts</h2>
        {preview.source_notice?<p>{preview.source_notice}</p>:null}
        <p>{preview.session_count} original source workouts · {preview.total_working_sets} working sets. Each source block may span more than seven days.</p>
        {preview.legacy_plan_id?<p>Your redistributed calendar allocation will be retained as superseded history. New Flexible occurrences use the original native grouping; this does not reinterpret the old saved prescription.</p>:null}
        {preview.first_session?<><h3>First: {preview.first_session.title ?? preview.first_session.name ?? 'Original source workout'}</h3><WorkoutWorkload exercises={preview.first_session.exercises} mode="flexible" /><ul>{preview.first_session.exercises.map((exercise,index)=><li key={`${exercise.id}-${index}`}>{exercise.name} · {exercise.sets} working sets</li>)}</ul></>:null}
        {preview.blockers?.map(blocker=><p role="alert" key={blocker.code}>{blocker.message??blocker.code.replaceAll('_',' ')}</p>)}
        {preview.available?<><label className="flex gap-2"><input type="checkbox" checked={confirmed} disabled={busy||Boolean(pending)} onChange={event=>setConfirmed(event.target.checked)} />I confirm this program, timezone and original source grouping. Existing history is preserved.</label><button className="ux-button ux-button-primary" disabled={!confirmed||busy||Boolean(pending)||trainingRecoveryBlocked(token)} onClick={()=>void enroll()}>Confirm Flexible enrollment</button><p className="ux-muted">Enrollment does not start performance. Start the next workout explicitly in Today.</p></>:null}
      </section>:null}
    </>}
    <Link className="ux-button ux-button-secondary" href="/">Back to Home</Link>
  </div>;
}
