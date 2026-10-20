import React from 'react';
import {act,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {beforeEach,expect,test,vi} from 'vitest';
import CustomizedPage from '@/app/customize/page';
const dates=['2026-10-19','2026-10-21','2026-10-23'];
const request={mode:'customized',bundle_id:'shorter-current',goal:'hypertrophy',population:'broadly_healthy_adult',training_context:'current',selected_dates:dates,timezone:'America/New_York',cap_minutes:60,cap_kind:'hard',equipment:['dumbbell'],skill:'intermediate',restrictions:[]};
const sessions=dates.map((date,i)=>({date,session_id:`session-${i}`,workout_occurrence_id:`occurrence-${i}`,title:`Workout ${i+1}`,exercises:[{id:'row',name:'Current row',sets:3,rep_range:[8,12],recommended_working_weight:null,customized:{target_kind:'rir',target_min:2,target_max:3,rest_seconds:{low:90,high:120},identity:{unit:'kg',basis:'per_hand'}}}]}));
const active={proposal_id:'active',revision:4,plan_version:1,snapshot_hash:'original',state:'active',blocking_reasons:[],snapshot:{request,preview:{candidate_name:'Original program',sessions:[],reasons:[],limitations:[],missing_actions:[],missing_regions:[],dose_conflicts:[]},comparison_reference:null,workload_changes:[]},active_placement:{plan_id:'plan',placement_revision:1,timezone:request.timezone,dates,sessions,frozen_dates:[dates[0]]}};
beforeEach(()=>{window.history.replaceState(null,'','/customize');localStorage.clear();vi.restoreAllMocks();});
function mockFetch(post:(path:string,body:Record<string,unknown>)=>unknown=()=>active){
 const fetcher=vi.fn(async(input:string,init?:RequestInit)=>{const path=String(input);if(path.endsWith('/customized/options'))return Response.json({equipment:['dumbbell'],restrictions:[]});if(init?.method==='POST')return Response.json(post(path,JSON.parse(String(init.body))));if(path.endsWith('/customized/active'))return Response.json({plans:[active]});return Response.json(active);});vi.stubGlobal('fetch',fetcher);return fetcher;
}
test('discovers active plan and confirms date-only preview with frozen history fixed',async()=>{
 const fetcher=mockFetch((path)=>path.endsWith('/preview')?{...active,revision:5,pending_reschedule:{digest:'bound-dates',selected_dates:[dates[0],'2026-10-22','2026-10-24'],placements:[],frozen_occurrence_ids:['occurrence-0']}}:{...active,revision:6,active_placement:{...active.active_placement,placement_revision:2,dates:[dates[0],'2026-10-22','2026-10-24'],sessions:sessions.map((s,i)=>({...s,date:[dates[0],'2026-10-22','2026-10-24'][i]}))}});
 render(<CustomizedPage/>);await screen.findByRole('heading',{name:'Current scheduled program'});expect(screen.getAllByText(/Current row/).length).toBeGreaterThan(0);
 fireEvent.click(screen.getByRole('button',{name:'Change training dates'}));expect(screen.getByLabelText('New workout date 1')).toBeDisabled();
 fireEvent.change(screen.getByLabelText('New workout date 2'),{target:{value:'2026-10-22'}});fireEvent.change(screen.getByLabelText('New workout date 3'),{target:{value:'2026-10-24'}});fireEvent.click(screen.getByRole('button',{name:'Preview date changes'}));await screen.findByLabelText('I confirm these exact date changes');
 expect(fetcher.mock.calls.filter(([,init])=>init?.method==='POST')).toHaveLength(1);expect(screen.getByRole('button',{name:'Confirm date changes'})).toBeDisabled();fireEvent.click(screen.getByLabelText('I confirm these exact date changes'));fireEvent.click(screen.getByRole('button',{name:'Confirm date changes'}));await waitFor(()=>expect(screen.queryByLabelText('I confirm these exact date changes')).not.toBeInTheDocument());
 const commands=fetcher.mock.calls.filter(([,init])=>init?.method==='POST');expect(JSON.parse(String(commands[0][1]?.body))).toMatchObject({expected_revision:4,expected_placement_revision:1,selected_dates:[dates[0],'2026-10-22','2026-10-24']});expect(JSON.parse(String(commands[1][1]?.body))).toMatchObject({expected_revision:5,expected_placement_revision:1,digest:'bound-dates',agree:true});
});
test('editing a date after preview removes confirmation and account changes clear active context',async()=>{
 mockFetch(()=>({...active,revision:5,pending_reschedule:{digest:'bound',selected_dates:dates,placements:[],frozen_occurrence_ids:[]}}));render(<CustomizedPage/>);await screen.findByRole('button',{name:'Change training dates'});fireEvent.click(screen.getByRole('button',{name:'Change training dates'}));fireEvent.click(screen.getByRole('button',{name:'Preview date changes'}));await screen.findByLabelText('I confirm these exact date changes');fireEvent.change(screen.getByLabelText('New workout date 3'),{target:{value:'2026-10-24'}});expect(screen.queryByRole('button',{name:'Confirm date changes'})).not.toBeInTheDocument();await act(async()=>window.dispatchEvent(new Event('hypertrophy:auth-token-changed')));expect(screen.queryByRole('button',{name:'Change training dates'})).not.toBeInTheDocument();expect(screen.queryByLabelText('New workout date 1')).not.toBeInTheDocument();
});
test('replacement sends explicit active-plan request and shows old full prescriptions beside proposal',async()=>{
 const fetcher=mockFetch(()=>({...active,proposal_id:'replacement',state:'review_required',revision:1,active_placement:undefined,snapshot:{...active.snapshot,replacement:{proposal_id:'active',plan_id:'plan',plan_digest:'digest',placement_revision:1,week_start:dates[0],sessions,kind:'future_week',preserved_work:[{occurrence_id:'occurrence-0',scheduled_date:dates[0],status:'started'}]},preview:{...active.snapshot.preview,candidate_name:'Replacement program'}}}));render(<CustomizedPage/>);await screen.findByRole('button',{name:'Replace active program'});fireEvent.click(screen.getByRole('button',{name:'Replace active program'}));for(let i=1;i<=3;i++)fireEvent.change(screen.getByLabelText(`Workout date ${i}`),{target:{value:`2026-10-${24+i*2}`}});fireEvent.click(screen.getByRole('button',{name:'Generate replacement preview'}));await screen.findByText('Replacement program');expect(screen.getByRole('heading',{name:'Program being replaced'})).toBeVisible();expect(screen.getByText(`${dates[0]} · started`)).toBeVisible();expect(screen.getAllByText(/Rest 90–120 seconds/).length).toBeGreaterThan(0);const command=fetcher.mock.calls.find(([path])=>String(path).endsWith('/active/replacement'));expect(command).toBeDefined();expect(JSON.parse(String(command![1]?.body))).toMatchObject({expected_revision:4,request:{selected_dates:['2026-10-26','2026-10-28','2026-10-30']}});fireEvent.click(screen.getByRole('button',{name:'Decline'}));await screen.findByRole('button',{name:'Change training dates'});
});
test('an active receipt cannot expose an old acceptance challenge',async()=>{
 const fetcher=mockFetch();fetcher.mockImplementation(async(input:string)=>String(input).endsWith('/customized/options')?Response.json({equipment:[],restrictions:[]}):String(input).endsWith('/customized/active')?Response.json({plans:[{...active,challenge:'old-consent'}]}):Response.json(active));
 render(<CustomizedPage/>);await screen.findByRole('heading',{name:'Current scheduled program'});expect(screen.queryByRole('button',{name:'Accept program'})).not.toBeInTheDocument();
});
test('late date preview after account change cannot restore old account intentions',async()=>{
 let resolvePreview!:(response:Response)=>void;
 const fetcher=mockFetch();fetcher.mockImplementation(async(input:string,init?:RequestInit)=>{
  if(init?.method==='POST')return new Promise<Response>(resolve=>{resolvePreview=resolve;});
  if(String(input).endsWith('/customized/options'))return Response.json({equipment:['dumbbell'],restrictions:[]});
  if(String(input).endsWith('/customized/active'))return Response.json({plans:[active]});return Response.json(active);
 });
 render(<CustomizedPage/>);await screen.findByRole('button',{name:'Change training dates'});fireEvent.click(screen.getByRole('button',{name:'Change training dates'}));fireEvent.click(screen.getByRole('button',{name:'Preview date changes'}));
 await act(async()=>{window.dispatchEvent(new Event('hypertrophy:auth-token-changed'));resolvePreview(Response.json({...active,pending_reschedule:{digest:'private',selected_dates:dates,placements:[]}}));});
 expect(screen.queryByRole('heading',{name:'Current scheduled program'})).not.toBeInTheDocument();expect(screen.queryByLabelText('I confirm these exact date changes')).not.toBeInTheDocument();expect(window.location.search).toBe('');
});
test('replacement consent names replacement explicitly and stays disabled before acknowledgement',async()=>{
 window.history.replaceState(null,'','/customize?proposal=replacement');
 const replacement={proposal_id:'active',plan_id:'plan',plan_digest:'digest',placement_revision:1,week_start:dates[0],sessions,kind:'same_week_unstarted',preserved_work:[]};
 const workload={name:'Replacement',weekly_sets:0,dates,timezone:'UTC',daily_sets:[0,0,0],minimum_minutes:[0,0,0],upper_minutes:[0,0,0],cap_minutes:60,cap_kind:'hard',cap_status:[]};
 const candidate={...active,proposal_id:'replacement',state:'review_required',active_placement:undefined,challenge:'new-consent',terms_hash:'terms',summary_hash:'summary',snapshot:{...active.snapshot,replacement},terms:{text:'Replace only this program',summary:{replacement,candidate:workload,reference:null,workload_changes:[],proposed_range_conflicts:[],alternative_range_conflicts:[],timing_assumptions:[],limitations:[],explanation:'Bound to exact programs',alternatives:[]}}};
 const fetcher=mockFetch();fetcher.mockImplementation(async(input:string)=>String(input).endsWith('/customized/options')?Response.json({equipment:[],restrictions:[]}):Response.json(candidate));
 render(<CustomizedPage/>);await screen.findByLabelText('I accept replacement of this active program');expect(screen.getByRole('button',{name:'Accept program'})).toBeDisabled();fireEvent.click(screen.getByLabelText('I accept replacement of this active program'));expect(screen.getByRole('button',{name:'Accept program'})).toBeEnabled();expect(screen.queryByLabelText('I accept this exact program version')).not.toBeInTheDocument();
});
test('cancelling replacement inputs restores active plan without issuing a mutation',async()=>{
 const fetcher=mockFetch();render(<CustomizedPage/>);await screen.findByRole('button',{name:'Replace active program'});fireEvent.click(screen.getByRole('button',{name:'Replace active program'}));fireEvent.click(screen.getByRole('button',{name:'Cancel replacement'}));await screen.findByRole('heading',{name:'Current scheduled program'});expect(fetcher.mock.calls.filter(([,init])=>init?.method==='POST')).toHaveLength(0);
});
test.each(['replacement','revision'])('generation binds inventory revision zero when the original request has null (%s)',async(kind)=>{
 window.history.replaceState(null,'',kind==='revision'?'/customize?proposal=active':'/customize');
 const original={...active,state:kind==='revision'?'review_required':'active',snapshot:{...active.snapshot,request:{...request,inventory_revision:null}}};
 const fetcher=vi.fn(async(input:string,init?:RequestInit)=>{
  if(String(input).endsWith('/customized/options'))return Response.json({equipment:['dumbbell'],restrictions:[],inventory:{version:'customized-location-profile-v1',revision:0,profile:null}});
  if(init?.method==='POST')return Response.json(original);
  if(String(input).endsWith('/customized/active'))return Response.json({plans:[original]});return Response.json(original);
 });vi.stubGlobal('fetch',fetcher);render(<CustomizedPage/>);
 if(kind==='replacement'){fireEvent.click(await screen.findByRole('button',{name:'Replace active program'}));fireEvent.click(screen.getByRole('button',{name:'Generate replacement preview'}));}
 else{await screen.findByText('Original program');fireEvent.click(screen.getByRole('button',{name:'Generate preview'}));}
 await waitFor(()=>expect(fetcher.mock.calls.some(([,init])=>init?.method==='POST')).toBe(true));
 const command=fetcher.mock.calls.find(([,init])=>init?.method==='POST');expect(JSON.parse(String(command![1]?.body)).request.inventory_revision).toBe(0);
});
test('started-week replacement conflict explains the next-week alternative and clears the pending request',async()=>{
 const fetcher=mockFetch();fetcher.mockImplementation(async(input:string,init?:RequestInit)=>{
  if(String(input).endsWith('/customized/options'))return Response.json({equipment:['dumbbell'],restrictions:[]});
  if(init?.method==='POST')return Response.json({detail:'started_plan_requires_future_week_replacement'},{status:409});
  if(String(input).endsWith('/customized/active'))return Response.json({plans:[active]});return Response.json(active);
 });render(<CustomizedPage/>);fireEvent.click(await screen.findByRole('button',{name:'Replace active program'}));fireEvent.click(screen.getByRole('button',{name:'Generate replacement preview'}));
 await screen.findByText('This week has recorded workout history. Keep the current program and choose next-week dates for a replacement.');
 expect(await screen.findByRole('button',{name:'Replace active program'})).toBeEnabled();expect(screen.queryByRole('button',{name:'Accept program'})).not.toBeInTheDocument();expect(screen.queryByRole('button',{name:'Generate replacement preview'})).not.toBeInTheDocument();
});
test('a fresh replacement after decline uses a fresh key while preserving active plan',async()=>{
 const candidate={...active,proposal_id:'candidate',state:'review_required',active_placement:undefined,snapshot:{...active.snapshot,replacement:{proposal_id:'active',plan_id:'plan',plan_digest:'digest',placement_revision:1,week_start:dates[0],sessions,kind:'future_week',preserved_work:[]}}};
 const fetcher=mockFetch(path=>path.endsWith('/replacement')?candidate:{...candidate,state:'declined'});render(<CustomizedPage/>);
 for(let attempt=0;attempt<2;attempt++){fireEvent.click(await screen.findByRole('button',{name:'Replace active program'}));fireEvent.click(screen.getByRole('button',{name:'Generate replacement preview'}));await screen.findByRole('button',{name:'Review acceptance'});fireEvent.click(screen.getByRole('button',{name:'Decline'}));await screen.findByRole('button',{name:'Replace active program'});}
 const commands=fetcher.mock.calls.filter(([path])=>String(path).endsWith('/replacement'));expect(commands).toHaveLength(2);expect(new Headers(commands[0][1]?.headers).get('Idempotency-Key')).not.toBe(new Headers(commands[1][1]?.headers).get('Idempotency-Key'));
});
