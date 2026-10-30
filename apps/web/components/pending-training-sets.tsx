"use client";
import {useEffect,useRef,useState} from 'react';
import {api,ApiError,getToken} from '@/lib/api';
import {accountScope} from '@/lib/appearance';
import {acknowledgeLogCommand,pendingFlexibleSets} from '@/lib/workout-identity';

type SetPayload=Parameters<typeof api.logSet>[1];

/** Exact replay remains reachable when next-day Resume hides the old runner. */
export function PendingTrainingSets({accountToken,onRecovered}:{accountToken:string;onRecovered:(message:string)=>void}) {
  const [revision,setRevision]=useState(0);
  const [notice,setNotice]=useState('');
  const [busy,setBusy]=useState(false);
  const inFlight=useRef(false);
  const mounted=useRef(true);
  useEffect(()=>{
    mounted.current=true;
    const refresh=()=>setRevision(value=>value+1);
    window.addEventListener('storage',refresh);window.addEventListener('focus',refresh);
    return()=>{mounted.current=false;window.removeEventListener('storage',refresh);window.removeEventListener('focus',refresh);};
  },[]);
  const scope=accountScope(accountToken);
  const pending=scope && getToken()===accountToken ? pendingFlexibleSets<SetPayload>(scope) : [];
  async function retry(attempt:typeof pending[number]) {
    if(inFlight.current||getToken()!==accountToken)return;
    inFlight.current=true;setBusy(true);setNotice('');
    let resolved=false;
    let resolution='';
    try {
      const receipt=await api.logSet(attempt.workoutId,attempt.payload);
      if(!mounted.current||getToken()!==accountToken)return;
      if(!receipt.id||receipt.command_id!==attempt.payload.command_id||receipt.workout_occurrence_id!==attempt.workoutId)throw new Error('Unbound receipt');
      resolved=true;resolution='Original set receipt confirmed. The retained command was sent unchanged.';
    } catch(error) {
      if(!mounted.current||getToken()!==accountToken)return;
      if(error instanceof ApiError && error.status===409 && error.code==='performance_context_not_current') {
        resolved=true;resolution='Original set was not recorded; the server rejected its expired execution context. Resume explicitly before recording new work. Past work has not been fabricated.';
      } else setNotice('Set result remains unknown. Retry the exact original set before changing training.');
    } finally {
      if(mounted.current&&getToken()===accountToken) {
        if(resolved){acknowledgeLogCommand(attempt.key);setRevision(value=>value+1);onRecovered(resolution);}
        inFlight.current=false;setBusy(false);
      }
    }
  }
  if(!pending.length&&!notice)return null;
  return <div className="space-y-2" aria-label="Pending set recovery" data-revision={revision}>
    {pending.length?<p>A previous set result is uncertain. Check its original command before Resume, Finish or changing programs.</p>:null}
    {pending.map(attempt=><div key={attempt.key} className="space-y-1">
      <p>{attempt.payload.exercise_id.replaceAll('_',' ')} · set {attempt.payload.set_index} · original request retained</p>
      <button className="ux-button ux-button-secondary" disabled={busy} onClick={()=>void retry(attempt)}>Retry original set</button>
    </div>)}
    {notice?<p role="status">{notice}</p>:null}
  </div>;
}
