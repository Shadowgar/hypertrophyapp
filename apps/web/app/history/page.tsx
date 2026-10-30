"use client";

import Link from "next/link";
import {useEffect, useState} from "react";
import {Button} from "@/components/ui/button";
import {useAppearance} from "@/components/appearance-provider";
import {displayLoad} from "@/lib/appearance";
import {api, getToken, getProgramDisplayName, type HistoryCalendarResponse, type HistoryDayDetailResponse, type HistoryDayStatus} from "@/lib/api";
import {calendarDate, displayDate, historyRange, historyStatusLabels, useHistoryAccount} from "@/lib/history-view";
import "./history.css";

export default function HistoryPage() {
  const account = useHistoryAccount();
  const {preferences} = useAppearance();
  const unit = preferences.weight_unit;
  const [mode,setMode] = useState<"week"|"month">("week");
  const [offset,setOffset] = useState(0);
  const [reload,setReload] = useState(0);
  const [statusFilter,setStatusFilter] = useState("all");
  const [programFilter,setProgramFilter] = useState("all");
  const [resource,setResource] = useState<{account:string|null;mode:string;offset:number;data:HistoryCalendarResponse}|null>(null);
  const [calendarState,setCalendarState] = useState("Loading calendar history…");
  const [selectedDay,setSelectedDay] = useState<string|null>(null);
  const [selectedOccurrence,setSelectedOccurrence] = useState("");
  const [detailReload,setDetailReload] = useState(0);
  const [detailResource,setDetailResource] = useState<{account:string|null;data:HistoryDayDetailResponse}|null>(null);
  const [detailState,setDetailState] = useState("");
  const calendar = resource?.account === account && resource.mode === mode && resource.offset === offset && getToken() === account ? resource.data : null;
  const detail = detailResource?.account === account && detailResource.data.date === selectedDay && getToken() === account ? detailResource.data : null;
  const days = calendar?.days ?? [];
  const programs = Array.from(new Set(days.flatMap(day=>day.program_ids)));
  const matches = (day:HistoryCalendarResponse["days"][number]) => (statusFilter === "all" || (day.status ?? "unknown") === statusFilter || day.occurrences?.some(session => session.status === statusFilter)) && (programFilter === "all" || day.program_ids.includes(programFilter));

  useEffect(()=>{setSelectedDay(null);setSelectedOccurrence("");setDetailResource(null);},[statusFilter,programFilter]);

  useEffect(()=>{
    let active=true;
    const current=()=>active && getToken()===account;
    setResource(null);setCalendarState("Loading calendar history…");setSelectedDay(null);setDetailResource(null);setSelectedOccurrence("");
    void (async()=>{
      let clockVerified=false;
      try {
        const clock=await api.getSchedulingContext("UTC");
        if(!current())return;
        const range=historyRange(clock.local_today,mode,offset);clockVerified=true;
        const payload=await api.getHistoryCalendar(range.startDate,range.endDate);
        if(!current())return;
        if(!Array.isArray(payload.days))throw new Error("Calendar unavailable");
        if(payload.start_date!==range.startDate || payload.end_date!==range.endDate)throw new Error("Calendar range mismatch");
        payload.days.forEach(day=>{calendarDate(day.date);if(day.date<range.startDate || day.date>range.endDate)throw new Error("Calendar date mismatch");});
        setResource({account,mode,offset,data:payload});setCalendarState(payload.days.length ? "" : "No calendar history yet.");
      }catch {if(current())setCalendarState(clockVerified ? "Unable to load calendar history." : "Unable to verify the current local date. Retry calendar load.");}
    })();
    return()=>{active=false;};
  },[account,mode,offset,reload]);

  useEffect(()=>{
    let active=true;
    setDetailResource(null);
    if(!selectedDay){setDetailState("");return()=>{active=false;};}
    setDetailState("Loading day detail…");
    void api.getHistoryDayDetail(selectedDay).then(payload=>{
      if(!active || getToken()!==account)return;
      if(payload.date!==selectedDay || !Array.isArray(payload.workouts))throw new Error("Day reply mismatch");
      setDetailResource({account,data:payload});setDetailState("");
      setSelectedOccurrence(previous=>payload.workouts.some(workout=>(workout.workout_occurrence_id??workout.workout_id)===previous) ? previous : payload.workouts[0]?.workout_occurrence_id ?? payload.workouts[0]?.workout_id ?? "");
    }).catch(()=>{if(active && getToken()===account)setDetailState("Unable to load day detail.");});
    return()=>{active=false;};
  },[account,selectedDay,detailReload]);

  const selected = days.find(day=>day.date===selectedDay);
  const selectedWorkout = detail?.workouts.find(workout=>(workout.workout_occurrence_id ?? workout.workout_id)===selectedOccurrence);
  const recent = [...days].reverse().filter(day=>matches(day) && ((day.occurrences?.length ?? 0)>0 || day.set_count>0));
  const choose = (day:string, occurrence="") => {setSelectedDay(day);setSelectedOccurrence(occurrence);};
  const isLoading = calendarState.startsWith("Loading");
  return <div className="history-page">
    <header className="history-heading"><p className="history-eyebrow">History</p><h1>{selectedDay ? displayDate(selectedDay) : "Your training history"}</h1>
      <p>{selectedDay ? "Your saved exercise records" : calendar ? `${displayDate(calendar.start_date,{month:"long",year:"numeric"})} · your saved record` : "Scheduled sessions and recorded work"}</p>
      {selectedDay && <Button variant="secondary" onClick={()=>{setSelectedDay(null);setSelectedOccurrence("");}}>Back to calendar</Button>}
      <Link href="/analytics" id="analytics">See your progress</Link>
    </header>
    <div className="history-layout">
      <section className="history-card" aria-label="Training Calendar">
        <div className="history-card-heading"><h2>Training calendar</h2><div className="history-switch">
          {(["week","month"] as const).map(view=><button key={view} aria-pressed={mode===view} onClick={()=>{setMode(view);setOffset(0);}}>{view==="week"?"Week":"Month"}</button>)}
        </div></div>
        <div className="history-window"><Button variant="secondary" onClick={()=>setOffset(v=>v-1)} aria-label="Previous window">←</Button>
          <p>{calendar ? `${displayDate(calendar.start_date,{month:"short",day:"numeric"})} – ${displayDate(calendar.end_date,{month:"short",day:"numeric",year:"numeric"})}` : "Your calendar"}</p>
          <Button variant="secondary" onClick={()=>setOffset(v=>Math.min(0,v+1))} disabled={offset===0} aria-label="Next window">→</Button></div>
        {calendar ? <>
          {!days.length && <p>No calendar history yet.</p>}
          <div className="history-calendar" aria-label="Calendar dates">
            {["Mon","Tue","Wed","Thu","Fri","Sat","Sun"].map(day=><span className="history-weekday" key={day}>{day}</span>)}
            {days.map(day=>{const status=day.status ?? "unknown"; const shown=matches(day); const weekday=(calendarDate(day.date).getUTCDay()+6)%7;
              return <button key={day.date} className={`history-date history-date--${status}`} style={{gridColumn:String(weekday+1)}}
                aria-label={`${day.date}: ${historyStatusLabels[status]}`} aria-pressed={selectedDay===day.date} disabled={!shown}
                title={`${day.date}: ${day.set_count} recorded sets · ${historyStatusLabels[status]}`} onClick={()=>choose(day.date)}>
                <span>{Number(day.date.slice(-2))}</span><small aria-hidden="true">{status==="complete"?"✓":["partial","ended_early","amended_incomplete"].includes(status)?"◐":status==="scheduled"?"○":status==="rest"?"—":"?"}</small>
              </button>;
            })}
          </div>
          <ul className="history-legend" aria-label="Calendar status legend">{Object.entries(historyStatusLabels).map(([key,label])=><li key={key}><span className={`history-dot history-dot--${key}`}/>{label}</li>)}</ul>
          <p className="history-note">Completion uses required working sets. Warm-ups and technique extras remain separate. Unknown means the saved evidence cannot establish completion or a rest day.</p>
        </> : <div role="status"><p>{calendarState}</p>{!isLoading && <Button onClick={()=>setReload(v=>v+1)}>Retry Calendar Load</Button>}</div>}
        <details className="history-filters"><summary>Filters: {statusFilter==="all"&&programFilter==="all"?"all sessions":"selected sessions"}</summary>
          <label>Status filter<select value={statusFilter} onChange={event=>setStatusFilter(event.target.value)}><option value="all">All sessions</option>{Object.entries(historyStatusLabels).map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label>
          <label>Program filter<select value={programFilter} onChange={event=>setProgramFilter(event.target.value)}><option value="all">All programs</option>{programs.map(program=><option key={program} value={program}>{getProgramDisplayName({id:program})}</option>)}</select></label>
        </details>
      </section>
      <section className="history-card" aria-label="Recent sessions"><h2>Recent sessions</h2>
        {recent.length ? <ul className="history-session-list">{recent.flatMap(day=>(day.occurrences?.length ? day.occurrences : [{workout_occurrence_id:"",title:"Recorded activity",status:"unknown" as HistoryDayStatus,working_sets_completed:0,working_sets_planned:null}]).filter(session => statusFilter === "all" || day.status === statusFilter || session.status === statusFilter).map((session,index)=><li key={`${day.date}-${session.workout_occurrence_id}-${index}`}>
          <button onClick={()=>choose(day.date,session.workout_occurrence_id)}><strong>{displayDate(day.date,{weekday:"short",day:"numeric"})} · {session.title}</strong>
            <span>{historyStatusLabels[session.status]}{session.working_sets_planned!=null ? ` · ${session.working_sets_completed} / ${session.working_sets_planned} working sets` : " · completion not established"}</span></button>
        </li>))}</ul> : <p>{calendar ? "No sessions match this window and filter. Dates without evidence remain unknown." : "Your sessions will appear when the calendar loads."}</p>}
        <Link href="/week">Review your schedule</Link>
      </section>
    </div>
    {selectedDay && <section className="history-card history-detail" aria-label="Selected day detail" aria-busy={detailState.startsWith("Loading")}>
      <p className="history-eyebrow">Selected day detail</p><h2>{selectedDay ? displayDate(selectedDay) : "Choose a day"}</h2>
      {selected && <p>{historyStatusLabels[selected.status ?? "unknown"]} · {selected.set_count} recorded sets</p>}
      {detailState && <p role="status">{detailState}</p>}
      {detailState.startsWith("Unable") && <Button onClick={()=>setDetailReload(v=>v+1)}>Retry day detail</Button>}
      {!selectedDay && <p>Select a calendar date or session to see the factual record.</p>}
      {detail && !detail.workouts.length && <p>No recorded or planned workouts for this date in the available record.</p>}
      {detail && detail.workouts.length>1 && <label className="history-field">Select session<select value={selectedOccurrence} onChange={e=>setSelectedOccurrence(e.target.value)}>{detail.workouts.map(workout=><option key={workout.workout_occurrence_id??workout.workout_id} value={workout.workout_occurrence_id??workout.workout_id}>{workout.title ?? `Workout ${workout.workout_id}`}</option>)}</select></label>}
      {selectedWorkout && <div className="history-receipts"><h3>{selectedWorkout.title ?? `Workout ${selectedWorkout.workout_id}`}</h3>
        {!selectedWorkout.workout_occurrence_id && <p>Legacy recorded workout · occurrence identity unresolved. Planned work is shown separately when it cannot be linked.</p>}
        {selectedWorkout.program_id && <p>{getProgramDisplayName({id:selectedWorkout.program_id})}</p>}
        <p>{selectedWorkout.total_sets} recorded sets · {displayLoad(selectedWorkout.total_volume,unit)} {unit} × reps recorded volume</p>
        {selectedWorkout.exercises.map((exercise,index)=><article key={exercise.exercise_occurrence_id??`${exercise.exercise_id}-${index}`}>
          <h4>{exercise.planned_name ?? exercise.exercise_id}</h4>
          {exercise.planned_sets!=null && <p>{exercise.planned_sets} planned working sets</p>}
          <ul>{exercise.sets.map((entry,index)=><li key={entry.id??`${entry.set_index}-${index}`}>
            <strong>{entry.set_kind==="warmup"?"Warm-up":entry.parent_set_index!=null?"Technique":"Set"} {entry.set_index}: {entry.reps} × {displayLoad(entry.weight,unit)} {unit}</strong>
            <span>{entry.actual_rir!=null ? `Actual RIR ${entry.actual_rir}` : `Actual RPE ${entry.rpe??"unknown"}`}{entry.supersedes_id?" · corrected effective record":" · effective record"}</span>
            {entry.performed_variant && <span>{entry.performed_variant.name} · original {entry.original_authored_name??exercise.planned_name??exercise.exercise_id}</span>}
            <details><summary>Record details</summary><p>Recorded {entry.created_at ? new Date(entry.created_at).toLocaleString() : "date unknown"}</p><p>Source exercise: {entry.original_authored_name??exercise.planned_name??"Not recorded"}</p><p>Occurrence: {entry.exercise_occurrence_id??"Legacy identity unresolved"}</p>{entry.supersedes_id && <p>Correction of {entry.supersedes_id}; the original audit record is retained.</p>}</details>
          </li>)}</ul>
          {!exercise.sets.length && <p>No performed sets recorded for this exercise.</p>}
        </article>)}
      </div>}
      <p className="history-note">This is the effective training record. Corrections and undo retain their original audit history.</p>
    </section>}
  </div>;
}
