import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, test, vi } from 'vitest';
import TrainingSetupPage from '@/app/training/setup/page';
const {push}=vi.hoisted(()=>({push:vi.fn()}));
vi.mock('next/navigation',()=>({useRouter:()=>({push})}));
const token=(sub:string)=>`header.${btoa(JSON.stringify({sub}))}.signature`;
const program='pure_bodybuilding_phase_1_full_body';
const first={session_id:'native',title:'Original source workout',exercises:[{id:'a',name:'Source Press',sets:3}]};
function server(options:{legacy?:boolean;nextWeekOnly?:boolean;blocked?:boolean;lost?:boolean}={}){
 const previews:Record<string,unknown>[]=[];const enrollments:Record<string,unknown>[]=[];
 vi.stubGlobal('fetch',vi.fn(async(input,init)=>{
  const url=String(input);
  if(url.endsWith('/profile'))return Response.json({selected_program_id:program,scheduling_timezone:'America/New_York',schedule_mode:options.legacy?'calendar':'flexible',expected_sessions_per_week:null});
  if(url.endsWith('/training/next'))return Response.json({mode:'calendar',action:'none'});
  if(url.includes('/plan/scheduling-context'))return Response.json({week_start:url.includes('week_offset=1')?'2026-11-02':'2026-10-26',plan:options.legacy&&(Boolean(options.nextWeekOnly)===url.includes('week_offset=1'))?{plan_id:'legacy-a',program_template_id:program,sessions:[]}:null});
  if(url.endsWith('/training/enroll/preview')){previews.push(JSON.parse(String(init.body)));return Response.json({digest:'source-review',program_id:program,session_count:5,total_working_sets:70,first_session:first,legacy_plan_id:options.legacy?'legacy-a':null,available:!options.blocked,blockers:options.blocked?[{code:'legacy_started',message:'This saved plan already has activity.'}]:[]});}
  if(url.endsWith('/training/enroll')){enrollments.push(JSON.parse(String(init.body)));if(options.lost&&enrollments.length===1)throw Error('lost reply');return Response.json({mode:'flexible',sequence_id:'seq',action:'start'});}
  return Response.json({});
 }));return {previews,enrollments};
}
beforeEach(()=>{localStorage.setItem('hypertrophy_token',token('enroll-web'));push.mockClear();});
test('native enrollment is previewed without writes and explicitly confirmed',async()=>{
 const state=server();render(<TrainingSetupPage/>);
 fireEvent.click(await screen.findByRole('button',{name:'Preview Flexible'}));
 await screen.findByRole('heading',{name:'Review original source workouts'});
 expect(state.enrollments).toHaveLength(0);expect(state.previews[0]).toMatchObject({program_id:program,expected_sessions_per_week:null});
 expect(screen.getByText(/70 working sets/)).toBeInTheDocument();
 expect(screen.getByRole('button',{name:'Confirm Flexible enrollment'})).toBeDisabled();
 fireEvent.click(screen.getByRole('checkbox',{name:/I confirm/}));
 fireEvent.click(screen.getByRole('button',{name:'Confirm Flexible enrollment'}));
 await waitFor(()=>expect(state.enrollments).toHaveLength(1));
 expect(state.enrollments[0]).toMatchObject({preview_digest:'source-review',confirmed:true,program_id:program});
 await waitFor(()=>expect(push).toHaveBeenCalledWith('/today'));
});
test('Switch preview binds current reservation and explains retained original grouping',async()=>{
 const state=server({legacy:true});render(<TrainingSetupPage/>);
 fireEvent.click(await screen.findByRole('button',{name:'Preview Switch to Flexible'}));
 await screen.findByRole('heading',{name:'Review original source workouts'});
 expect(state.previews[0]).toMatchObject({switch_plan_id:'legacy-a'});
 expect(screen.getByText(/redistributed.*superseded history/i)).toBeInTheDocument();
});
test('a sole next-week reservation is identified and explicitly bound to Switch',async()=>{
 const state=server({legacy:true,nextWeekOnly:true});render(<TrainingSetupPage/>);
 fireEvent.click(await screen.findByRole('button',{name:'Preview Switch to Flexible'}));
 expect(screen.getByText('legacy-a')).toBeInTheDocument();
 await screen.findByRole('heading',{name:'Review original source workouts'});
 expect(state.previews[0]).toMatchObject({switch_plan_id:'legacy-a'});
 expect(state.enrollments).toHaveLength(0);
 fireEvent.click(screen.getByRole('checkbox',{name:/I confirm/}));
 fireEvent.click(screen.getByRole('button',{name:'Confirm Flexible enrollment'}));
 await waitFor(()=>expect(state.enrollments).toHaveLength(1));
 expect(state.enrollments[0]).toMatchObject({switch_plan_id:'legacy-a',preview_digest:'source-review',confirmed:true});
});
test.each([false,true])('started legacy work blocks confirmation, next-week-only=%s',async nextWeekOnly=>{
 const state=server({legacy:true,nextWeekOnly,blocked:true});render(<TrainingSetupPage/>);
 fireEvent.click(await screen.findByRole('button',{name:'Preview Switch to Flexible'}));
 await screen.findByText('This saved plan already has activity.');
 expect(screen.queryByRole('button',{name:'Confirm Flexible enrollment'})).not.toBeInTheDocument();
 expect(state.enrollments).toHaveLength(0);
});
test('lost enrollment acknowledgement retries the exact original enrollment',async()=>{
 const state=server({lost:true});render(<TrainingSetupPage/>);
 fireEvent.click(await screen.findByRole('button',{name:'Preview Flexible'}));
 await screen.findByRole('heading',{name:'Review original source workouts'});
 fireEvent.click(screen.getByRole('checkbox',{name:/I confirm/}));
 fireEvent.click(screen.getByRole('button',{name:'Confirm Flexible enrollment'}));
 fireEvent.click(await screen.findByRole('button',{name:'Retry original enrollment'}));
 await waitFor(()=>expect(state.enrollments).toHaveLength(2));
 expect(state.enrollments[1]).toEqual(state.enrollments[0]);
});

test('an account change revokes the reviewed enrollment before any write',async()=>{
 const state=server();render(<TrainingSetupPage/>);
 fireEvent.click(await screen.findByRole('button',{name:'Preview Flexible'}));
 await screen.findByRole('heading',{name:'Review original source workouts'});
 fireEvent.click(screen.getByRole('checkbox',{name:/I confirm/}));
 localStorage.setItem('hypertrophy_token',token('other-enrollment-account'));
 fireEvent.click(screen.getByRole('button',{name:'Confirm Flexible enrollment'}));
 expect(state.enrollments).toHaveLength(0);
});
