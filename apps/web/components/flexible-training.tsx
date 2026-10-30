"use client";

import Link from 'next/link';
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { api, ApiError, getToken, type TrainingCommand, type TrainingNext, type TrainingOperation } from '@/lib/api';
import { accountScope } from '@/lib/appearance';
import { acknowledgeLogCommand, hasPendingWorkoutCommands, pendingLogPayload, retainLogPayload } from '@/lib/workout-identity';
import { WorkoutWorkload } from '@/components/workout-workload';
import { formatCalendarDate } from '@/lib/calendar-date';
import {PendingTrainingSets} from '@/components/pending-training-sets';

export function trainingRecoveryBlocked(token: string | null): boolean {
  try {
    const scope = accountScope(token) ?? 'guest';
    if (localStorage.getItem(`hypertrophy_undo_recovery_v1:${scope}:payload`) !== null) return true;
    return hasPendingWorkoutCommands(scope);
  } catch { return true; }
}

type RetainedTrainingCommand = { sequenceId: string; operation: TrainingOperation; payload: TrainingCommand };
const labels: Record<TrainingOperation, string> = { start:'start', resume:'resume', pause:'pause', finish:'finish', 'end-early':'end early', reconcile:'recheck', retire:'retire program' };

/** Server-owned sequence decisions; this view never advances from local set counts. */
export function FlexibleTraining({ accountToken, onResolved, onContinue, canChange, timeBudgetMinutes, reloadKey = 0 }: {
  accountToken: string | null; onResolved?: (next: TrainingNext | null) => void;
  onContinue?: () => void; canChange?: () => boolean; timeBudgetMinutes?: number | null; reloadKey?: number;
}) {
  const [next, setNext] = useState<TrainingNext | null>(null);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState('');
  const [readFailed, setReadFailed] = useState(false);
  const [operation, setOperation] = useState<TrainingOperation | null>(null);
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);
  const [pending, setPending] = useState<RetainedTrainingCommand | null>(null);
  const [reload, setReload] = useState(0);
  const [retired, setRetired] = useState(false);
  const callbacks = useRef({onResolved, onContinue, canChange});
  useLayoutEffect(() => { callbacks.current={onResolved,onContinue,canChange}; }, [onResolved,onContinue,canChange]);
  const generation = useRef(0);
  const invalidate = useCallback(() => { ++generation.current; }, []);
  const inFlight = useRef(false);
  const dialog = useRef<HTMLDialogElement>(null);
  const commandKey = `hypertrophy_training_v1:${accountScope(accountToken) ?? 'guest'}`;

  useEffect(()=>{
    const epoch=++generation.current; let active=true;
    const current=()=>active&&generation.current===epoch&&getToken()===accountToken;
    setReadFailed(false);setRetired(false);setNext(null);setOperation(null);setLoading(true);setBusy(false);inFlight.current=false;
    setPending(pendingLogPayload<RetainedTrainingCommand>(commandKey));
    // With no account, the existing authenticated routes own sign-in rejection;
    // there is no private sequence decision to wait for.
    if(!accountToken){setLoading(false);callbacks.current.onResolved?.(null);return;}
    void api.getNextTraining().then(value=>{
      if(!current())return;
      // Old calendar clients may have no sequence; never infer Flexible from a date plan.
      setNext(value?.mode==='flexible'?value:null);callbacks.current.onResolved?.(value?.mode==='flexible'?value:null);
    }).catch(()=>{if(current()){setReadFailed(true);setNotice('Training state could not be checked. Recheck before changing your program.');}})
      .finally(()=>{if(current())setLoading(false);});
    return()=>{active=false;invalidate();};
  },[accountToken,commandKey,reload,reloadKey,invalidate]);

  useEffect(()=>{
    function sync(){
      if(getToken()!==accountToken){++generation.current;setRetired(true);setNext(null);setOperation(null);return;}
      if(trainingRecoveryBlocked(accountToken))setOperation(null);
    }
    const changed=()=>{sync();if(getToken()===accountToken)setReload(value=>value+1);};
    window.addEventListener('hypertrophy:auth-token-changed',sync);
    window.addEventListener('storage',sync);window.addEventListener('focus',changed);
    window.addEventListener('hypertrophy:training-changed',changed);
    return()=>{window.removeEventListener('hypertrophy:auth-token-changed',sync);window.removeEventListener('storage',sync);window.removeEventListener('focus',changed);window.removeEventListener('hypertrophy:training-changed',changed);};
  },[accountToken]);

  useEffect(()=>{
    const element=dialog.current;if(!operation||!element)return;
    const previous=document.activeElement as HTMLElement|null;
    const overflow=document.body.style.overflow;document.body.style.overflow='hidden';element.showModal();
    return()=>{element.close();document.body.style.overflow=overflow;if(previous?.isConnected&&getToken()===accountToken)previous.focus();};
  },[operation,accountToken]);

  function permitted(){return Boolean(accountToken)&&getToken()===accountToken&&!trainingRecoveryBlocked(accountToken)&&(callbacks.current.canChange?.()??true);}
  function confirm(op:TrainingOperation){if(!permitted()||pending||busy)return;setReason('');setNotice('');setOperation(op);}
  async function execute(retry?:RetainedTrainingCommand){
    if(!permitted()){setOperation(null);setNotice('Resolve the pending set or undo before changing training.');return;}
    if(inFlight.current||!next)return;
    if(!retry&&(!operation||!next.sequence_id||next.revision===undefined||(!next.occurrence_id&&operation!=='retire')||!next.digest||!next.local_day))return;
    const attempted=retry??retainLogPayload<RetainedTrainingCommand>(commandKey,{sequenceId:next.sequence_id!,operation:operation!,payload:{command_id:crypto.randomUUID(),expected_revision:next.revision!,occurrence_id:next.occurrence_id??null,expected_digest:next.digest!,expected_local_day:next.local_day!,confirmed:true,...(reason.trim()?{reason:reason.trim()}: {})}});
    const epoch=generation.current;const current=()=>generation.current===epoch&&getToken()===accountToken;
    inFlight.current=true;setBusy(true);setPending(attempted);setNotice('');
    try{
      const result=await api.commandTraining(attempted.sequenceId,attempted.operation,attempted.payload);
      if(!current())return;
      acknowledgeLogCommand(commandKey);setPending(null);setOperation(null);setNext(result);callbacks.current.onResolved?.(result);
      if(['start','resume'].includes(attempted.operation))callbacks.current.onContinue?.();
      else setNotice(attempted.operation==='end-early'?'Session ended incomplete. Missing work and your prescription are retained.':attempted.operation==='finish'?result.action==='none'?'Finish recorded. End of source sequence; review History.':'Finish recorded. The next source workout is available.':attempted.operation==='retire'?'Program retired. Your history is retained.':'Training state updated.');
    }catch(error){
      if(!current())return;
      setOperation(null);
      if(error instanceof ApiError&&[409,422].includes(error.status)){
        acknowledgeLogCommand(commandKey);setPending(null);setNotice(`${error.message} Review the current state before confirming again.`);setReload(value=>value+1);
      }else setNotice('Training command not confirmed. Retry the original command before taking another action.');
    }finally{if(current()){inFlight.current=false;setBusy(false);}}
  }

  if(!accountToken||retired)return null;
  if(loading)return <p role="status">Checking Flexible training…</p>;
  if(!next)return readFailed ? <section className="ux-card space-y-3"><p role="status">{notice}</p><button className="ux-button ux-button-secondary" onClick={()=>setReload(value=>value+1)}>Retry training state</button></section> : null;
  const label=operation?labels[operation]:'';
  const actionable=next.action!=='none'&&next.action!=='blocked';
  return <section className="ux-card space-y-3" aria-label="Flexible training">
    <p className="ux-eyebrow">Flexible · original source workouts</p>
    <h2>{next.session?.title??(next.action==='none'?next.state==='retired'?'Program retired':'End of source sequence':'Training needs review')}</h2>
    <p className="ux-muted">{next.expected_sessions_per_week?`Expected ${next.expected_sessions_per_week} visits per week. `:''}Dates are optional. Unfinished work stays available across weeks.</p>
    {next.action==='none'?<Link className="ux-button ux-button-secondary" href="/training/setup">Review new Flexible program</Link>:null}
    {next.source_position !== undefined ? <p className="ux-muted">Source workout {next.source_position + 1}</p> : null}
    {next.session?<WorkoutWorkload exercises={next.session.exercises} timeBudgetMinutes={timeBudgetMinutes} mode="flexible"/>:null}
    {next.action==='none'?<p>{next.state==='retired'?'This program was retired. Prescriptions, receipts and incomplete work remain in History; retirement is not successful completion.':'Review History for full and incomplete session closures. Source exhaustion does not turn missing work into completion.'}</p>:null}
    {next.source_notice?<p className="ux-muted">{next.source_notice}</p>:null}
    {next.coverage?<p>{next.coverage.completed} / {next.coverage.required} required working sets recorded{next.coverage.known?'':'; coverage needs review'}.</p>:null}
    {next.blockers?.map(blocker=><p key={blocker.code} role="status">{blocker.message??blocker.code.replaceAll('_',' ')}{blocker.earliest_day?` Earliest eligible day: ${formatCalendarDate(blocker.earliest_day)}.`:''}</p>)}
    {notice?<p role="status">{notice}</p>:null}
    <PendingTrainingSets key={accountToken} accountToken={accountToken} onRecovered={message=>{setNotice(message);setReload(value=>value+1);}}/>
    {trainingRecoveryBlocked(accountToken)?<p role="alert">Resolve the pending set or undo before changing training.</p>:null}
    {pending?<button className="ux-button ux-button-primary" disabled={busy} onClick={()=>void execute(pending)}>Retry original training command</button>:<div className="flex flex-wrap gap-2">
      {next.action==='start'?<button className="ux-button ux-button-primary" onClick={()=>confirm('start')}>Start next workout</button>:null}
      {next.action==='resume'?<button className="ux-button ux-button-primary" onClick={()=>confirm('resume')}>Resume workout</button>:null}
      {next.action==='active'?(onContinue?<button className="ux-button ux-button-primary" onClick={()=>{if(permitted())onContinue();}}>Continue workout</button>:<Link className="ux-button ux-button-primary" href="/today">Continue workout</Link>):null}
      {next.action==='finish'?<button className="ux-button ux-button-primary" onClick={()=>confirm('finish')}>Finish workout</button>:null}
      {next.action==='active'||next.action==='finish'?<button className="ux-button ux-button-secondary" onClick={()=>confirm('pause')}>Pause workout</button>:null}
      {actionable&&next.action!=='start'&&next.coverage?.known&&!next.coverage.complete?<button className="ux-button ux-button-secondary" onClick={()=>confirm('end-early')}>End early</button>:null}
      {next.resolution_options?.some(option=>['reconcile','recheck'].includes(option))?<button className="ux-button ux-button-secondary" onClick={()=>confirm('reconcile')}>Recheck training</button>:null}
      {next.resolution_options?.includes('retire')?<button className="ux-button ux-button-secondary" onClick={()=>confirm('retire')}>Retire this program</button>:null}
    </div>}
    <button className="ux-button ux-button-ghost" disabled={busy||Boolean(pending)} onClick={()=>setReload(value=>value+1)}>Refresh training state</button>
    {operation?<dialog ref={dialog} aria-labelledby="training-confirm-title" className="ux-card fixed inset-0 m-auto max-h-[90dvh] w-[calc(100%-2rem)] max-w-lg space-y-4 overflow-y-auto backdrop:bg-black/70" onCancel={event=>{event.preventDefault();if(!busy)setOperation(null);}}>
      <h2 id="training-confirm-title">Confirm {label}</h2>
      <p>{next.session?.title} · {next.local_day?`${formatCalendarDate(next.local_day)} (${next.local_day})`:'Date unavailable'} · {next.timezone??next.execution_context?.timezone??'your program timezone'}</p>
      <p>Original source exercises and prescriptions remain unchanged.</p>
      {operation==='end-early'?<><p>This session will remain incomplete. Advance with this exact missing work:</p><ul>{next.coverage?.missing.map(item=><li key={`${item.exercise_occurrence_id}-${item.set_index}`}>{item.name} · set {item.set_index}</li>)}</ul><label className="block">Reason (optional)<input className="ux-input" maxLength={500} value={reason} onChange={event=>setReason(event.target.value)} /></label></>:null}
      {operation==='retire'?<p>This retires current program ownership and preserves all prescriptions, receipts and incomplete work. It does not count as completion or override a mandatory dependency.</p>:null}
      <div className="flex flex-wrap gap-2"><button className="ux-button ux-button-primary" disabled={busy} onClick={()=>void execute()}>Confirm {label}</button><button className="ux-button ux-button-secondary" disabled={busy} onClick={()=>setOperation(null)}>Cancel</button></div>
    </dialog>:null}
  </section>;
}
