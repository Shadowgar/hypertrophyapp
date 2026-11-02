import React from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, test, vi } from 'vitest';
import TodayPage from '@/app/today/page';
const token=`header.${btoa(JSON.stringify({sub:'flexible-today'}))}.signature`;
const date='2026-10-30';
function fixture(options:{resume?:boolean;lost?:boolean;trainingPending?:Promise<void>;blockedAfterRefresh?:boolean;todayUnavailable?:boolean}={}){
 let started=!options.resume;let count=0;let ctx='execution-original';
 const writes:Array<Record<string,unknown>>=[];const commands:Array<Record<string,unknown>>=[];const reads:string[]=[];
 const workout=()=>({session_id:'native-a',workout_occurrence_id:'native-occ-a',title:'Source workout A',date,execution_context:{id:ctx,local_day:date,timezone:'America/New_York'},exercises:[{id:'press',exercise_occurrence_id:'slot-a',name:'Flexible Source Press',sets:3,rep_range:[8,12],recommended_working_weight:20}]});
 const next=()=>({mode:'flexible',sequence_id:'seq-a',revision:2,occurrence_id:'native-occ-a',action:started?'active':'resume',state:started?'active':'paused',session:workout(),local_day:date,digest:'evidence-digest',execution_context:started?workout().execution_context:null,coverage:{known:true,required:3,completed:count,complete:false,missing:[{exercise_occurrence_id:'slot-a',set_index:2,name:'Flexible Source Press'}]}});
 vi.stubGlobal('fetch',vi.fn(async(input,init)=>{
  const url=String(input); reads.push(url);
  if(url.endsWith('/health'))return Response.json({status:'ok'});
  if(url.endsWith('/training/next')){await options.trainingPending;return Response.json(options.blockedAfterRefresh&&reads.filter(r=>r.endsWith('/training/next')).length>1?{...next(),action:'blocked',blockers:[{code:'mandatory_rest',message:'Required rest evidence needs review'}]}:next());}
  if(url.endsWith('/training/seq-a/resume')){commands.push(JSON.parse(String(init.body)));started=true;return Response.json(next());}
  if(url.endsWith('/training/seq-a/pause')){commands.push(JSON.parse(String(init.body)));started=false;return Response.json(next());}
  if(url.includes('/plan/scheduling-context'))return Response.json({timezone:'America/New_York',local_today:date,week_start:'2026-10-26',plan:null});
  if(options.todayUnavailable&&url.endsWith('/workout/today'))return Response.json({detail:'unavailable'},{status:503});
  if(url.endsWith('/workout/today'))return started?Response.json(workout()):Response.json({detail:'No active Flexible workout'},{status:404});
  if(url.endsWith('/profile'))return Response.json({schedule_mode:'flexible',selected_program_id:'pure_bodybuilding_phase_1_full_body',weak_areas:[]});
  if(url.endsWith('/progress'))return Response.json({completed_total:count,planned_total:3,percent_complete:count/3*100,exercises:[{exercise_id:'press',exercise_occurrence_id:'slot-a',planned_sets:3,completed_sets:count}]});
  if(url.includes('/soreness?'))return Response.json([{entry_date:date}]);
  if(url.endsWith('/log-set')){writes.push(JSON.parse(String(init.body)));if(options.lost&&writes.length===1){ctx='execution-new-day';throw new TypeError('lost acknowledgement');}count=1;return Response.json({live_recommendation:{completed_sets:1,remaining_sets:2,recommended_reps_min:8,recommended_reps_max:12,recommended_weight:20}});}
  return Response.json({});
 }));return {writes,commands,reads};
}
beforeEach(()=>localStorage.setItem('hypertrophy_token',token));
test('Today waits for the server mode before attempting calendar-style autoload',async()=>{
 let resolve!:()=>void;
 const trainingPending=new Promise<void>(done=>{resolve=done;});
 const state=fixture({resume:true,trainingPending});
 await act(async()=>{render(<TodayPage/>);});
 await waitFor(()=>expect(state.reads.some(url=>url.endsWith('/training/next'))).toBe(true));
 expect(state.reads.some(url=>url.endsWith('/workout/today'))).toBe(false);
 await act(async()=>{resolve();});
 await screen.findByRole('button',{name:'Resume workout'});
 expect(state.reads.some(url=>url.endsWith('/workout/today'))).toBe(false);
});
test('Resume explicitly binds the day then opens the same source occurrence in the existing runner',async()=>{
 const state=fixture({resume:true});render(<TodayPage/>);
 fireEvent.click(await screen.findByRole('button',{name:'Resume workout'}));
 expect(state.commands).toHaveLength(0);
 fireEvent.click(screen.getByRole('button',{name:'Confirm resume'}));
 const exercise=await screen.findByRole('button',{name:/Flexible Source Press/});
 expect(state.commands[0]).toMatchObject({occurrence_id:'native-occ-a',expected_local_day:date,confirmed:true});
 fireEvent.click(exercise);
 fireEvent.change(screen.getByLabelText('Working weight (lb)'),{target:{value:'50'}});
 fireEvent.change(screen.getByLabelText('Working repetitions'),{target:{value:'8'}});
 fireEvent.click(screen.getByRole('button',{name:'Save set 1'}));
 await waitFor(()=>expect(state.writes).toHaveLength(1));
 expect(state.writes[0]).toMatchObject({execution_context_id:'execution-original',exercise_occurrence_id:'slot-a'});
});
test('an uncertain set retry preserves its original execution context after the server context changes',async()=>{
 const state=fixture({lost:true});render(<TodayPage/>);
 fireEvent.click(await screen.findByRole('button',{name:/Flexible Source Press/}));
 fireEvent.change(screen.getByLabelText('Working weight (lb)'),{target:{value:'50'}});
 fireEvent.change(screen.getByLabelText('Working repetitions'),{target:{value:'8'}});
 fireEvent.click(screen.getByRole('button',{name:'Save set 1'}));
 fireEvent.click(await screen.findByRole('button',{name:'Retry same set'}));
 await waitFor(()=>expect(state.writes).toHaveLength(2));
 expect(state.writes[1]).toEqual(state.writes[0]);
 expect(state.writes[1].execution_context_id).toBe('execution-original');
});
test('Pause retires the runner view without deleting progress and exposes Resume',async()=>{
 const state=fixture();render(<TodayPage/>);
 await screen.findByRole('button',{name:/Flexible Source Press/});
 fireEvent.click(screen.getByRole('button',{name:'Pause workout'}));
 fireEvent.click(screen.getByRole('button',{name:'Confirm pause'}));
 await screen.findByRole('button',{name:'Resume workout'});
 expect(screen.queryByRole('button',{name:/Flexible Source Press/})).not.toBeInTheDocument();
 expect(state.writes).toHaveLength(0);
});

test('training refresh stays outside active set-entry layout and mandatory blockers still retire the runner',async()=>{
 fixture({blockedAfterRefresh:true});render(<TodayPage/>);
 fireEvent.click(await screen.findByRole('button',{name:/Flexible Source Press/}));
 expect(screen.getByRole('region',{name:'Flexible training',hidden:true})).not.toBeVisible();
 await act(async()=>window.dispatchEvent(new Event('hypertrophy:training-changed')));
 await screen.findByText('Required rest evidence needs review');
 expect(screen.queryByRole('region',{name:'Working set entry'})).not.toBeInTheDocument();
 expect(screen.getByRole('region',{name:'Flexible training'})).toBeVisible();
});

test('a Flexible workout read failure explains the failure and retains the explicit Continue retry',async()=>{
 fixture({todayUnavailable:true});render(<TodayPage/>);
 await screen.findByText('Workout could not be loaded. Retry loading your workout. Your saved history is unchanged.');
 expect(screen.getByRole('button',{name:'Continue workout'})).toBeEnabled();
 expect(screen.queryByText(/No workout loaded/)).not.toBeInTheDocument();
});
