"use client";
import Link from "next/link";
import {useEffect,useState} from "react";
import {Button} from "@/components/ui/button";
import {useAppearance} from "@/components/appearance-provider";
import {api,getToken,type HistoryAnalyticsResponse,type CoachingRecommendationTimelineEntry} from "@/lib/api";
import {displayLoad} from "@/lib/appearance";
import {displayDate,useHistoryAccount} from "@/lib/history-view";
import "../history/history.css";

export default function AnalyticsPage(){
  const account=useHistoryAccount();
  const {preferences}=useAppearance();
  const unit=preferences.weight_unit;
  const [weeks,setWeeks]=useState(8);
  const [reload,setReload]=useState(0);
  const [timelineReload,setTimelineReload]=useState(0);
  const [resource,setResource]=useState<{account:string|null;weeks:number;data:HistoryAnalyticsResponse}|null>(null);
  const [readState,setReadState]=useState<"loading"|"ready"|"error">("loading");
  const [seriesId,setSeriesId]=useState("");
  const [tableOpen,setTableOpen]=useState(false);
  const [timeline,setTimeline]=useState<{account:string|null;entries:CoachingRecommendationTimelineEntry[]}|null>(null);
  const [timelineState,setTimelineState]=useState("Loading recommendation history…");
  const data=resource?.account===account && resource.weeks===weeks && getToken()===account ? resource.data : null;
  const entries=timeline?.account===account && getToken()===account ? timeline.entries : [];
  useEffect(()=>{
    let active=true;const current=()=>active&&getToken()===account;
    setResource(null);setReadState("loading");
    void api.getHistoryAnalytics(weeks,24).then(payload=>{
      if(!current())return;
      if(!payload.window || !Array.isArray(payload.strength_trends))throw new Error("Analytics unavailable");
      setResource({account,weeks,data:payload});setReadState("ready");
      setSeriesId(previous=>payload.load_series?.some(series=>series.series_id===previous)?previous:payload.load_series?.[0]?.series_id??"");
    }).catch(()=>{if(current())setReadState("error");});
    return()=>{active=false;};
  },[account,weeks,reload]);
  useEffect(()=>{
    let active=true;setTimeline(null);setTimelineState("Loading recommendation history…");
    void api.getCoachingRecommendationTimeline(24).then(reply=>{
      if(!active || getToken()!==account)return;
      setTimeline({account,entries:reply.entries??[]});setTimelineState(reply.entries?.length?"":"No coaching recommendations yet.");
    }).catch(()=>{if(active&&getToken()===account)setTimelineState("Unable to load recommendation history.");});
    return()=>{active=false;};
  },[account,timelineReload]);
  const series=data?.load_series?.find(item=>item.series_id===seriesId);
  const points=series?.points??[];
  const values=points.map(point=>displayLoad(point.max_weight,unit));
  const maximum=Math.max(...values,1);
  const x=(index:number)=>48+index/Math.max(1,points.length-1)*552;
  const y=(value:number)=>176-(value/maximum)*140;
  const selectedLabel=series ? `${series.exercise_name} · ${series.equipment_key}` : "Choose a recorded exercise and setup";
  return <div className="history-page">
    <header className="history-heading"><p className="history-eyebrow">Analytics</p><h1>See your progress</h1><p>{selectedLabel}</p><Link href="/history">Open your training record</Link></header>
    <section className="history-card" aria-label="Analytics filters"><div className="history-layout">
      <label className="history-field">Exercise and recorded setup<select value={seriesId} onChange={e=>setSeriesId(e.target.value)} disabled={!data?.load_series?.length}>
        {!data?.load_series?.length&&<option value="">No supported setup series</option>}{data?.load_series?.map(item=><option key={item.series_id} value={item.series_id}>{item.exercise_name} · {item.equipment_key} · {item.basis.replaceAll("_"," ")}</option>)}
      </select></label>
      <label className="history-field">Date range<select value={weeks} onChange={e=>setWeeks(Number(e.target.value))}>{[4,8,12,26].map(count=><option value={count} key={count}>Last {count} weeks</option>)}</select></label>
    </div>{data&&<p>{data.window.start_date} – {data.window.end_date} · values in {unit}</p>}</section>
    {readState==="loading"&&<section className="history-card" role="status"><h2>Loading your recorded progress…</h2><p>Checking the selected range.</p></section>}
    {readState==="error"&&<section className="history-card" role="alert"><h2>Analytics could not be loaded</h2><p>Your recorded history is unchanged. Try the read again.</p><Button onClick={()=>setReload(v=>v+1)}>Retry analytics</Button></section>}
    {data && <>
      <div className="analytics-layout">
        <div className="analytics-support">
          <section className="history-card">
            <h2>Working weight · {unit}</h2>
            {points.length>=2 ? <svg className="analytics-chart" viewBox="0 0 640 220" role="img" aria-label={`Weekly highest working load for ${selectedLabel}, ${unit}; identical values in the data table`}>
              <title>Weekly highest recorded working load</title>
              {[0,.5,1].map(fraction=><g key={fraction}><line className="analytics-axis" x1="48" x2="600" y1={y(maximum*fraction)} y2={y(maximum*fraction)}/><text x="4" y={y(maximum*fraction)+4}>{Number((maximum*fraction).toFixed(1))}</text></g>)}
              <polyline className="analytics-line" points={values.map((value,index)=>`${x(index)},${y(value)}`).join(" ")}/>
              {points.map((point,index)=><circle key={point.week_start} cx={x(index)} cy={y(values[index])} r="5"><title>{point.week_start}: {values[index]} {unit}</title></circle>)}
              <text x="48" y="210">{points[0].week_start}</text><text x="600" y="210" textAnchor="end">{points.at(-1)?.week_start}</text>
            </svg> : <div className="history-empty"><h2>More training will tell the story</h2><p>{points.length===1 ? "One recorded week is a factual observation; it does not establish a trend." : "No repeated working-load series with a recorded setup is available in this range."}</p><Link href="/history">View the factual record</Link></div>}
            <p className="history-note">Saved performance, not a growth or readiness score.</p>
            <Button variant="secondary" onClick={()=>setTableOpen(value=>!value)} aria-expanded={tableOpen}>{tableOpen?"Hide data table":"Show data table"}</Button>
            {tableOpen&&<div className="history-table-wrap"><table><caption>The values behind the chart · weekly highest working load · {unit}</caption><thead><tr><th scope="col">Week starting</th><th scope="col">Recorded load</th></tr></thead><tbody>{points.map(point=><tr key={point.week_start}><th scope="row">{point.week_start}</th><td>{displayLoad(point.max_weight,unit)} {unit}</td></tr>)}</tbody></table>{!points.length&&<p>No sampled values in this range.</p>}</div>}
          </section>
          <section className="history-card"><h2>What this view includes</h2><p>Effective working sets grouped by the same recorded exercise, load basis, equipment and available variant identity. Warm-ups, technique extras and voided records are excluded.</p><p>Targets, effort and technique can differ. A higher load alone does not establish better performance or justify a prescription change.</p>
            {(data.load_series_unknown_sets??0)>0&&<p>{data.load_series_unknown_sets} working sets have insufficient setup information for this comparison. They remain in History.</p>}
            {!data.load_series&&<p>This response does not include qualified setup grouping. Legacy aggregates remain available below with their limitations.</p>}
          </section>
        </div>
        <aside className="analytics-support">
          <section className="history-card"><h2>Working weight · {unit}</h2>{points.length ? <ul className="history-session-list">{points.map(point=><li key={point.week_start}><div style={{padding:"12px 0"}}><strong>{displayDate(point.week_start,{day:"numeric",month:"long"})}</strong><p>{displayLoad(point.max_weight,unit)} {unit} · weekly highest recorded load</p></div></li>)}</ul> : <p>No comparable setup values to list.</p>}</section>
          <section className="history-card"><h2>Same recorded setup</h2><p>{selectedLabel}</p>{series&&<p>{series.basis.replaceAll("_"," ")} · displayed in your saved {unit} preference.</p>}</section>
        </aside>
      </div>
      <section className="history-card"><details><summary>Check-ins and body measurements</summary>
        {data.checkins?.length ? <p>{data.adherence.average_pct}% recent average self-reported adherence · {data.checkins.length} check-ins. Adherence is not readiness.</p> : <p>No weekly check-ins yet. Missing observations stay unknown.</p>}
        <div className="history-table-wrap"><table><caption>Recorded bodyweight · {unit}</caption><thead><tr><th>Week</th><th>Bodyweight</th></tr></thead><tbody>{data.bodyweight_trend?.map((point,index)=><tr key={point.week_start??index}><th>{point.week_start??"Date unknown"}</th><td>{displayLoad(point.body_weight,unit)} {unit}</td></tr>)}</tbody></table></div>
        {data.body_measurement_trends?.map(item=><div key={`${item.name}-${item.unit}`}><h3>{item.name}</h3><p>{item.latest_value} {item.unit} · change {item.delta>0?"+":""}{item.delta} {item.unit}</p></div>)}
      </details></section>
      <section className="history-card"><details><summary>Earlier aggregate views and recorded activity</summary><p>These earlier exercise-level aggregates do not establish matching setup, effort or complete exposures. Use the setup-separated series above for a like-setup load view.</p>
        {data.strength_trends?.map(item=><div key={item.exercise_id}><h3>{item.exercise_id.replaceAll("_"," ")}</h3><p>Recorded maximum {displayLoad(item.pr_weight,unit)} {unit}</p></div>)}
        <div className="history-table-wrap"><table><caption>Recorded volume · {unit} × reps; all retained set kinds</caption><thead><tr><th>Week</th><th>Weekday</th><th>Records</th><th>Volume</th></tr></thead><tbody>{data.volume_heatmap?.weeks.flatMap(week=>week.days.map(day=><tr key={`${week.week_start}-${day.day_index}`}><th>{week.week_start}</th><td>{["Mon","Tue","Wed","Thu","Fri","Sat","Sun"][day.day_index]}</td><td>{day.sets}</td><td>{displayLoad(day.volume,unit)} {unit} × reps</td></tr>))}</tbody></table></div>
      </details></section>
    </>}
    <section className="history-card"><details><summary>Coaching decision history</summary>{entries.length ? <ul className="history-session-list">{entries.map(entry=><li key={entry.recommendation_id}><strong>{entry.recommendation_type.replaceAll("_"," ")} · {entry.status}</strong><p>{entry.rationale}</p><p>{new Date(entry.created_at).toLocaleString()}</p></li>)}</ul> : <p>{timelineState}</p>}{timelineState.startsWith("Unable")&&<Button onClick={()=>setTimelineReload(value=>value+1)}>Retry recommendation history</Button>}</details></section>
  </div>;
}
