import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, test, vi } from 'vitest';
import HomePage from '@/app/page';
import { emptyAnswers, setupPayload, validBasics } from '@/app/onboarding/setup-draft';

const accountToken = `header.${btoa(JSON.stringify({ sub: 'flexible-web' }))}.signature`;
const session = {session_id:'source-a',workout_occurrence_id:'occ-a',title:'Native source workout A',exercises:[{id:'press',exercise_occurrence_id:'press-a',name:'Source Press',sets:3}]};
const decision = {mode:'flexible',sequence_id:'seq-a',revision:2,occurrence_id:'occ-a',action:'start',session,local_day:'2026-10-30',digest:'reviewed-digest',coverage:{known:true,required:3,completed:0,complete:false,missing:[{exercise_occurrence_id:'press-a',set_index:1,name:'Source Press'}]}};
function serve(value: Record<string, unknown> = decision, options: { failFirst?: boolean } = {}) {
  let attempts=0;
  const writes: Array<Record<string, unknown>>=[];
  vi.stubGlobal('fetch',vi.fn(async(input,init)=>{
    const path=String(input);
    if(path.endsWith('/training/next')) return Response.json(value);
    if(path.includes('/training/seq-a/')&&init?.method==='POST') {
      writes.push(JSON.parse(String(init.body)));
      if(options.failFirst&&attempts++===0) throw new Error('acknowledgement lost');
      return Response.json({...decision,action:'active',execution_context:{id:'ctx-a',local_day:'2026-10-30',timezone:'America/New_York'}});
    }
    if(path.endsWith('/workout/today')) return Response.json({detail:'No workout scheduled today'},{status:404});
    if(path.endsWith('/profile')) return Response.json({schedule_mode:'flexible',selected_program_id:'pure_bodybuilding_phase_1_full_body',days_available:null});
    if(path.includes('/plan/scheduling-context')) return Response.json({plan:null,selected_dates:[]});
    return Response.json({});
  }));
  return writes;
}
beforeEach(()=>localStorage.setItem('hypertrophy_token',accountToken));

test('Flexible basics accept no dates or expected count and never derive a split from frequency',()=>{
  const answers={...emptyAnswers,age:'34',weightValue:'180',selectedProgramId:'pure_bodybuilding_phase_1_full_body',scheduleMode:'flexible' as const,expectedSessionsPerWeek:''};
  expect(validBasics(answers)).toBe(true);
  const payload=setupPayload({...answers,expectedSessionsPerWeek:'7'},'Synthetic',{});
  expect(payload).toMatchObject({schedule_mode:'flexible',expected_sessions_per_week:7,days_available:null,split_preference:'full_body'});
  expect(payload.onboarding_answers.days_available).toBeNull();
  expect(validBasics({...answers,expectedSessionsPerWeek:'1.5'})).toBe(false);
  expect(validBasics({...answers,selectedProgramId:null})).toBe(false);
});

test('Home prioritizes server Start and writes only after explicit source confirmation',async()=>{
  const writes=serve(); render(<HomePage/>);
  fireEvent.click(await screen.findByRole('button',{name:'Start next workout'}));
  expect(writes).toHaveLength(0);
  expect(screen.getByRole('dialog')).toHaveTextContent('Native source workout A');
  expect(screen.getByRole('dialog')).toHaveTextContent('2026');
  fireEvent.click(screen.getByRole('button',{name:'Confirm start'}));
  await waitFor(()=>expect(writes).toHaveLength(1));
  expect(writes[0]).toMatchObject({expected_revision:2,occurrence_id:'occ-a',expected_digest:'reviewed-digest',expected_local_day:'2026-10-30',confirmed:true});
  expect(screen.queryByRole('link',{name:'Choose dates'})).not.toBeInTheDocument();
});

test('an unconfirmed lifecycle command retries its exact immutable envelope',async()=>{
  const writes=serve(decision,{failFirst:true});render(<HomePage/>);
  fireEvent.click(await screen.findByRole('button',{name:'Start next workout'}));
  fireEvent.click(screen.getByRole('button',{name:'Confirm start'}));
  fireEvent.click(await screen.findByRole('button',{name:'Retry original training command'}));
  await waitFor(()=>expect(writes).toHaveLength(2));
  expect(writes[1]).toEqual(writes[0]);
  await screen.findByRole("link", {name:"Continue workout"});
  expect(screen.queryByText(/Training command not confirmed/)).not.toBeInTheDocument();
});

test('End Early explicitly lists exact missing work and never claims Finish',async()=>{
  const writes=serve({...decision,action:'active',state:'active'});render(<HomePage/>);
  fireEvent.click(await screen.findByRole('button',{name:'End early'}));
  const dialog=screen.getByRole('dialog');expect(dialog).toHaveTextContent('Source Press · set 1');
  expect(dialog).toHaveTextContent('incomplete');
  fireEvent.click(screen.getByRole('button',{name:'Confirm end early'}));
  await waitFor(()=>expect(writes).toHaveLength(1));
});

test('pending undo revokes lifecycle write permission even after opening confirmation',async()=>{
  const writes=serve();render(<HomePage/>);
  fireEvent.click(await screen.findByRole('button',{name:'Start next workout'}));
  localStorage.setItem('hypertrophy_undo_recovery_v1:flexible-web:payload','{}');
  fireEvent.click(screen.getByRole('button',{name:'Confirm start'}));
  expect(writes).toHaveLength(0);
});

test('a Flexible state read failure offers recovery without claiming a calendar rest day',async()=>{
 serve();const fetcher=vi.mocked(fetch).getMockImplementation()!;
 vi.mocked(fetch).mockImplementation((input,init)=>String(input).endsWith('/training/next')?Promise.resolve(Response.json({detail:'Unavailable'},{status:503})):fetcher(input,init));
 render(<HomePage/>);
 expect(await screen.findByRole('button',{name:'Retry training state'})).toBeInTheDocument();
 expect(screen.queryByRole('link',{name:'Choose dates'})).not.toBeInTheDocument();
});

test('source exhaustion does not claim that incomplete closures were fully completed',async()=>{
 serve({...decision,action:'none',session:null,state:'finished'});render(<HomePage/>);
 expect(await screen.findByRole('heading',{name:'End of source sequence'})).toBeInTheDocument();
 expect(screen.queryByRole('heading',{name:'Program complete'})).not.toBeInTheDocument();
});

test('a memory-retained set still blocks lifecycle writes when browser storage is full',async()=>{
 const {retainLogPayload,acknowledgeLogCommand}=await import('@/lib/workout-identity');
 const key='hypertrophy_occurrence_v2:command:hypertrophy_occurrence_v3:flexible-web:attempt:occ-a:press:work:1';
 const write=vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw new DOMException('Full','QuotaExceededError');});
 retainLogPayload(key,{command_id:'pending-set'});write.mockRestore();
 const writes=serve();render(<HomePage/>);
 fireEvent.click(await screen.findByRole('button',{name:'Start next workout'}));
 expect(screen.queryByRole('dialog')).not.toBeInTheDocument();expect(writes).toHaveLength(0);
 acknowledgeLogCommand(key);
});

test('changing accounts after source confirmation opens revokes the old command',async()=>{
 const writes=serve();render(<HomePage/>);
 fireEvent.click(await screen.findByRole('button',{name:'Start next workout'}));
 localStorage.setItem('hypertrophy_token',`header.${btoa(JSON.stringify({sub:'other-account'}))}.signature`);
 fireEvent.click(screen.getByRole('button',{name:'Confirm start'}));
 expect(writes).toHaveLength(0);
});

test('blocked training exposes a confirmed terminal retirement and factual earliest-day guidance',async()=>{
 const writes=serve({...decision,action:'blocked',blockers:[{code:'mandatory_rest',message:'Source rest is required.',earliest_day:'2026-11-02'}],resolution_options:['reconcile','retire']});render(<HomePage/>);
 fireEvent.click(await screen.findByRole('button',{name:'Retire this program'}));
 expect(writes).toHaveLength(0);expect(screen.getByRole('dialog')).toHaveTextContent('preserves all prescriptions, receipts and incomplete work');
 fireEvent.click(screen.getByRole('button',{name:'Confirm retire program'}));
 await waitFor(()=>expect(writes).toHaveLength(1));
 expect(vi.mocked(fetch).mock.calls.some(([path])=>String(path).endsWith('/training/seq-a/retire'))).toBe(true);
});

test('full effective coverage offers explicit Finish without automatically advancing',async()=>{
 const writes=serve({...decision,action:'finish',coverage:{known:true,required:3,completed:3,complete:true,missing:[]}});render(<HomePage/>);
 fireEvent.click(await screen.findByRole('button',{name:'Finish workout'}));
 expect(writes).toHaveLength(0);expect(screen.queryByRole('button',{name:'End early'})).not.toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Confirm finish'}));
 await waitFor(()=>expect(writes).toHaveLength(1));
});

test('calendar start guidance waits for the authoritative training mode when profile is also pending',async()=>{
 serve();const fetcher=vi.mocked(fetch).getMockImplementation()!;
 vi.mocked(fetch).mockImplementation((input,init)=>String(input).endsWith('/training/next')||String(input).endsWith('/profile')?new Promise<Response>(()=>{}):fetcher(input,init));
 render(<HomePage/>);
 await screen.findByText('Choose actual dates and preview your week.');
 expect(screen.queryByRole('link',{name:'Choose dates'})).not.toBeInTheDocument();
});

test('retirement is labeled separately from successful completion or source exhaustion',async()=>{
 serve({...decision,action:'none',session:null,state:'retired'});render(<HomePage/>);
 expect(await screen.findByRole('heading',{name:'Program retired'})).toBeInTheDocument();
 expect(screen.queryByRole('heading',{name:'End of source sequence'})).not.toBeInTheDocument();
});

test('a missing current occurrence still permits explicit terminal retirement',async()=>{
 const writes=serve({...decision,occurrence_id:null,session:null,action:'blocked',blockers:[{code:'missing_occurrence',message:'Current source occurrence is missing.'}],resolution_options:['retire']});render(<HomePage/>);
 fireEvent.click(await screen.findByRole('button',{name:'Retire this program'}));
 fireEvent.click(screen.getByRole('button',{name:'Confirm retire program'}));
 await waitFor(()=>expect(writes).toHaveLength(1));
 expect(writes[0].occurrence_id).toBeNull();
});

test.each(['finished','retired'])('terminal %s state offers an explicit new-program review',async state=>{
 serve({...decision,action:'none',session:null,state});render(<HomePage/>);
 expect(await screen.findByRole('link',{name:'Review new Flexible program'})).toHaveAttribute('href','/training/setup');
});
