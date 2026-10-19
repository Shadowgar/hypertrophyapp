import React from 'react';
import {fireEvent,render,screen,waitFor} from '@testing-library/react';
import {beforeEach,expect,test,vi} from 'vitest';
import CustomizedPage from '@/app/customize/page';

beforeEach(()=>{window.history.replaceState(null,'','/customize');localStorage.clear();vi.restoreAllMocks();});
test('collects explicit training context, equipment and dates before generating',async()=>{
  vi.stubGlobal('fetch',vi.fn(async()=>new Response(JSON.stringify({bundles:[],equipment:['dumbbell','bench'],restrictions:['avoid_horizontal_press']}))));
  render(<CustomizedPage/>);
  await screen.findByRole('heading',{name:'Customize My Workout'});
  expect(screen.getByRole('button',{name:'Generate preview'})).toBeDisabled();
  expect(screen.getByLabelText('Training context')).toHaveValue('unknown');
  expect(screen.getByLabelText('dumbbell')).not.toBeChecked();
  expect(screen.getByLabelText('No movement restrictions')).not.toBeChecked();
  fireEvent.change(screen.getByLabelText('Training context'),{target:{value:'current'}});
  fireEvent.change(screen.getByLabelText('Exercise skill'),{target:{value:'intermediate'}});
  fireEvent.click(screen.getByLabelText('dumbbell'));
  fireEvent.click(screen.getByLabelText('No movement restrictions'));
  for(let i=1;i<=3;i++)fireEvent.change(screen.getByLabelText(`Workout date ${i}`),{target:{value:`2026-10-${18+i*2}`}});
  await waitFor(()=>expect(screen.getByRole('button',{name:'Generate preview'})).toBeEnabled());
});

test('Customized receipt editor exposes corrections without Authored prescription controls',async()=>{
  const {LoadIntelligencePanel}=await import('@/components/exercise-control');
  render(<LoadIntelligencePanel receiptOnly guidance={null} completed={1} total={2}
    loadContext={{unit:'kg',display_unit:'lb',basis:'per_hand'}} onContextChange={()=>{}}
    onPreview={async()=>{throw new Error('No Authored load preview for Customized');}}
    overrideReason="" onOverrideReason={()=>{}} onCorrect={async()=>{}}
    effectiveSets={[{id:'receipt',set_index:1,reps:8,weight:10,rpe:null,set_kind:'work',parent_set_index:null,technique:null,created_at:'2026-10-19T12:00:00'}]}/>);
  expect(screen.getByRole('button',{name:'Edit set 1'})).toBeInTheDocument();
  expect(screen.queryByRole('button',{name:'Preview load guidance'})).not.toBeInTheDocument();
});

test('late proposal hydration cannot restore the previous account after token change',async()=>{
  window.history.replaceState(null,'','/customize?proposal=old-account');
  let resolveOld!:(value:Response)=>void;
  const pending=new Promise<Response>(resolve=>{resolveOld=resolve;});
  vi.stubGlobal('fetch',vi.fn(async(input:string)=>String(input).endsWith('/customized/options')?new Response(JSON.stringify({equipment:['dumbbell'],restrictions:[]})):pending));
  render(<CustomizedPage/>);
  await screen.findByLabelText('dumbbell');
  fireEvent.change(screen.getByLabelText('Training context'),{target:{value:'current'}});
  const {act}=await import('@testing-library/react');
  await act(async()=>{
    window.dispatchEvent(new Event('hypertrophy:auth-token-changed'));
    resolveOld(new Response(JSON.stringify({proposal_id:'old-account',revision:2,plan_version:1,state:'review_required',blocking_reasons:[],
      snapshot:{request:{mode:'customized',bundle_id:'shorter-current',goal:'hypertrophy',population:'broadly_healthy_adult',training_context:'current',selected_dates:['2026-10-19','2026-10-21','2026-10-23'],timezone:'America/New_York',cap_minutes:60,cap_kind:'hard',equipment:['dumbbell'],skill:'intermediate',restrictions:[]},
      preview:{candidate_name:'Private previous-account program',sessions:[],reasons:[],limitations:[],missing_actions:[],missing_regions:[],dose_conflicts:[]},comparison_reference:null,workload_changes:[]}})));
  });
  expect(screen.queryByText('Private previous-account program')).not.toBeInTheDocument();
  expect(screen.getByLabelText('Training context')).toHaveValue('unknown');
});

test('single acknowledgement discloses the bound numeric dose and timing summary',async()=>{
  window.history.replaceState(null,'','/customize?proposal=summary');
  const proposal={proposal_id:'summary',revision:2,plan_version:1,snapshot_hash:'snapshot',state:'review_required',blocking_reasons:[],snapshot:{request:{mode:'customized',bundle_id:'shorter-current',goal:'hypertrophy',population:'broadly_healthy_adult',training_context:'current',selected_dates:['2026-10-19','2026-10-21','2026-10-23'],timezone:'UTC',cap_minutes:60,cap_kind:'hard',equipment:['dumbbell'],skill:'intermediate',restrictions:[]},preview:{candidate_name:'Bound program',sessions:[],reasons:[],limitations:[],missing_actions:[],missing_regions:[],dose_conflicts:[]},comparison_reference:null,workload_changes:[]}};
  vi.stubGlobal('fetch',vi.fn(async(input:string,init?:RequestInit)=>{
    if(String(input).endsWith('/customized/options'))return new Response(JSON.stringify({equipment:['dumbbell'],restrictions:[]}));
    if(init?.method==='POST')return new Response(JSON.stringify({...proposal,revision:3,challenge:'challenge',terms_hash:'terms',summary_hash:'summary',terms:{text:'Accept this exact program',summary:{candidate:{name:'Bound program',weekly_sets:33,daily_sets:[11,11,11],dates:['2026-10-19','2026-10-21','2026-10-23'],timezone:'UTC',minimum_minutes:[35.8,36.8,35.8],upper_minutes:[57.5,59,57.5],cap_minutes:60,cap_kind:'hard',cap_status:[]},reference:null,workload_changes:[],proposed_range_conflicts:[{region:'lateral_deltoid',primary_sets:2,proposed_minimum:4,proposed_maximum:6,interpretation:'Unapproved candidate range'}],alternative_range_conflicts:[],timing_assumptions:[{local_date:'2026-10-19',phases:{warmup_seconds:{low:480,high:720}}}],limitations:['No measured time guarantee'],explanation:'Less work may mean less opportunity.',alternatives:['Decline or revise']}}}));
    return new Response(JSON.stringify(proposal));
  }));
  render(<CustomizedPage/>);
  await screen.findByText('Bound program');
  fireEvent.click(screen.getByRole('button',{name:'Review acceptance'}));
  expect(await screen.findByText('lateral deltoid: 2 direct sets; provisional range 4–6')).toBeVisible();
  fireEvent.click(screen.getByText('Timing assumptions for this version'));
  expect(screen.getByText('warmup: 480–720 seconds')).toBeVisible();
  expect(screen.getAllByRole('checkbox',{name:'I accept this exact program version'})).toHaveLength(1);
});

test('editing context while account options load retains available equipment',async()=>{
  let resolveOptions!:(value:Response)=>void;
  vi.stubGlobal('fetch',vi.fn(()=>new Promise<Response>(resolve=>{resolveOptions=resolve;})));
  render(<CustomizedPage/>);
  fireEvent.change(screen.getByLabelText('Training context'),{target:{value:'current'}});
  const {act}=await import('@testing-library/react');
  await act(async()=>resolveOptions(new Response(JSON.stringify({equipment:['bench'],restrictions:[]}))));
  expect(await screen.findByLabelText('bench')).toBeInTheDocument();
  expect(screen.getByLabelText('Training context')).toHaveValue('current');
});

test('saving inventory invalidates an in-flight preview without leaving Generate busy',async()=>{
  const {act}=await import('@testing-library/react');
  const inventory={version:'customized-location-profile-v1',revision:1,profile:{location_id:'gym',location_name:'Actual gym',equipment:['dumbbell'],unavailable_variants:[],setups:[],assignments:{},strength_reports:[]}};
  let resolveOld!:(value:Response)=>void;
  vi.stubGlobal('fetch',vi.fn(async(input:string,init?:RequestInit)=>{
    if(String(input).endsWith('/customized/options'))return Response.json({equipment:['dumbbell'],restrictions:[],variants:[],inventory});
    if(init?.method==='PUT')return Response.json({...inventory,revision:2});
    return new Promise<Response>(resolve=>{resolveOld=resolve;});
  }));
  render(<CustomizedPage/>);
  await screen.findByLabelText('dumbbell');
  fireEvent.change(screen.getByLabelText('Training context'),{target:{value:'current'}});
  fireEvent.change(screen.getByLabelText('Exercise skill'),{target:{value:'intermediate'}});
  fireEvent.click(screen.getByLabelText('No movement restrictions'));
  for(let i=1;i<=3;i++)fireEvent.change(screen.getByLabelText(`Workout date ${i}`),{target:{value:`2026-10-${17+i*2}`}});
  fireEvent.click(screen.getByRole('button',{name:'Generate preview'}));
  expect(screen.getByRole('button',{name:'Generate preview'})).toBeDisabled();
  fireEvent.click(screen.getByText('Equipment inventory and calibration'));
  fireEvent.click(screen.getByRole('button',{name:'Save inventory'}));
  await screen.findByText('Inventory saved. Generate a new preview before accepting availability changes.');
  expect(screen.getByRole('button',{name:'Generate preview'})).toBeEnabled();
  await act(async()=>resolveOld(Response.json({proposal_id:'stale',state:'review_required'})));
  expect(window.location.search).not.toContain('stale');
  expect(screen.queryByRole('button',{name:'Review acceptance'})).not.toBeInTheDocument();
});
