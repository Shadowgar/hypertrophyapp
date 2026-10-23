import {runnerScreen as screen} from "./helpers/runner-driver";
import React from 'react';
import {fireEvent,render,screen as nativeScreen,waitFor} from '@testing-library/react';
import TodayPage from '@/app/today/page';

test('Customized keeps original names and updated correction reasons without legacy swap policy',async()=>{
  const initial={recommended_weight:11,action:'increase',reason_codes:['bounded_attainable_increase'],attainable_loads:[10,11],calibration:{strength_information:[]}};
  const corrected={...initial,recommended_weight:null,action:'monitor',reason_codes:['actual_effort_unknown_or_invalid']};
  const receipt={id:'r1',set_index:1,reps:12,weight:10,rpe:null,actual_rir:5,technique_quality:'acceptable',pain:false,set_kind:'work',parent_set_index:null,created_at:'2026-10-19T12:00:00'};
  const exercise={id:'original',exercise_occurrence_id:'slot',name:'Original pilot press',sets:1,completed_sets:1,rep_range:[8,12],slot_role:'weak_point',substitution_candidates:['Legacy fallback'],load_semantics:'per_hand',
    customized:{identity:{basis:'per_hand',equipment_key:'actual-pair'},target_kind:'rir',target_min:1,target_max:3,rest_seconds:{low:120,high:180}},customized_load_decision:initial,customized_receipts:[receipt]};
  const writes:Record<string,unknown>[]=[];
  vi.stubGlobal('fetch',vi.fn(async(input,init)=>{
    const url=String(input);
    if(url.includes('/plan/scheduling-context?'))return Response.json({timezone:'UTC',local_today:new Date().toISOString().slice(0,10),week_start:'2026-10-19',selected_dates:[],placement_revision:0,plan:null});
    if(url.endsWith('/workout/today'))return Response.json({session_id:'template',workout_occurrence_id:'occurrence',title:'Original pilot',date:new Date().toISOString().slice(0,10),exercises:[exercise]});
    if(url.includes('/soreness'))return Response.json([{entry_date:new Date().toISOString().slice(0,10)}]);
    if(url.endsWith('/correct')){writes.push(JSON.parse(String(init?.body)));return Response.json({status:'ok',customized_receipts:[{...receipt,id:'r2',actual_rir:null}],live_recommendation:{completed_sets:1,remaining_sets:0,recommended_weight:null,decision_trace:{load_decision:corrected}}});}
    return Response.json({});
  }));
  render(<TodayPage/>);
  fireEvent.click(screen.getByRole('button',{name:/Load today's workout/}));
  fireEvent.click(await screen.findByRole('button',{name:/Original pilot press/}));
  expect(await screen.findByText('Suggested 24.3 lb')).toBeInTheDocument();
  expect(screen.queryByRole('button',{name:'Swap'})).not.toBeInTheDocument();
  expect(screen.queryByText(/Primary weak-point slot/)).not.toBeInTheDocument();
  expect(screen.queryByText('Legacy fallback')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:/Recorded sets ·/}));
  expect(screen.getAllByText('Set 1: 12 reps @ 22 lb · Actual RIR 5').length).toBeGreaterThan(0);
  fireEvent.click(screen.getByRole('button',{name:'Edit set 1'}));
  fireEvent.change(screen.getByRole('spinbutton',{name:'Corrected actual RIR'}),{target:{value:''}});
  fireEvent.change(screen.getByRole('textbox',{name:'Correction reason'}),{target:{value:'Effort unknown'}});
  fireEvent.click(screen.getByRole('button',{name:'Save correction'}));
  await waitFor(()=>expect(writes[0]).toMatchObject({actual_rir:null,weight:10}));
  fireEvent.click(screen.getByRole('button',{name:'Close Recorded sets'}));
  fireEvent.click(screen.getByRole('button',{name:'Guide & setup'}));
  expect(await screen.findByText('actual effort unknown or invalid.')).toBeInTheDocument();
  expect(screen.queryByText('Suggested 24.3 lb')).not.toBeInTheDocument();
  vi.unstubAllGlobals();
});

test.each(['edited', 'uncertain'])('same-occurrence Reload refreshes Customized advice and receipts while retaining the %s actual draft', async draftState => {
  const adviceA = {recommended_weight:11,action:'increase',reason_codes:['bounded_attainable_increase'],attainable_loads:[10,11],calibration:{strength_information:[]}};
  const adviceB = {...adviceA,recommended_weight:null,action:'monitor',reason_codes:['actual_effort_unknown_or_invalid']};
  const initialReceipt = {id:'r1',set_index:1,reps:12,weight:10,rpe:null,actual_rir:5,technique_quality:'acceptable',pain:false,set_kind:'work',parent_set_index:null,created_at:'2026-10-19T12:00:00'};
  const replacementReceipt = {...initialReceipt,id:'r2',actual_rir:null};
  let refreshed = false;
  const writes: Record<string, unknown>[] = [];
  vi.stubGlobal('fetch', vi.fn(async(input,init) => {
    const url = String(input);
    if(url.includes('/plan/scheduling-context?')) return Response.json({timezone:'UTC',local_today:'2026-10-23',week_start:'2026-10-19',selected_dates:['2026-10-23'],placement_revision:1,plan:null});
    if(url.endsWith('/workout/today')) {
      const advice = refreshed ? adviceB : adviceA;
      return Response.json({session_id:'template',workout_occurrence_id:'occurrence',title:'Original pilot',date:'2026-10-23',exercises:[{
        id:'original',exercise_occurrence_id:'slot',name:'Original pilot press',sets:3,completed_sets:1,rep_range:[8,12],load_semantics:'per_hand',
        customized:{identity:{basis:'per_hand',equipment_key:'actual-pair'},target_kind:'rir',target_min:1,target_max:3,rest_seconds:{low:120,high:180}},
        customized_load_decision:advice,customized_receipts:[refreshed ? replacementReceipt : initialReceipt],
        live_recommendation:{completed_sets:1,remaining_sets:2,recommended_weight:advice.recommended_weight,decision_trace:{load_decision:advice}},
      }]});
    }
    if(url.endsWith('/progress')) return Response.json({completed_total:1,planned_total:3,percent_complete:33,exercises:[{exercise_id:'original',exercise_occurrence_id:'slot',completed_sets:1}]});
    if(url.includes('/soreness')) return Response.json([{entry_date:'2026-10-23'}]);
    if(url.endsWith('/log-set')) { writes.push(JSON.parse(String(init?.body))); throw Error('reply lost'); }
    return Response.json({});
  }));
  render(<TodayPage/>);
  fireEvent.click(screen.getByRole('button',{name:/Load today's workout/}));
  fireEvent.click(await screen.findByRole('button',{name:/Original pilot press/}));
  expect(await screen.findByText('Suggested 24.3 lb')).toBeInTheDocument();
  fireEvent.change(screen.getByRole('spinbutton',{name:'Weight (lb)'}),{target:{value:'60'}});
  fireEvent.change(screen.getByRole('spinbutton',{name:'Reps'}),{target:{value:'9'}});
  if(draftState === 'uncertain') {
    fireEvent.click(screen.getByRole('button',{name:'Complete Set'}));
    await nativeScreen.findByText('Save not confirmed. Retry the same set.');
  }
  fireEvent.click(screen.getByRole('button',{name:'Back to list'}));
  const reload = screen.getByRole('button',{name:'Reload'});
  await waitFor(() => expect(reload).toBeEnabled());
  refreshed = true;
  fireEvent.click(reload);
  await waitFor(() => expect(reload).toBeEnabled());
  fireEvent.click(screen.getByRole('button',{name:/Original pilot press/}));
  fireEvent.click(nativeScreen.getByRole('button',{name:'Guide & setup'}));
  expect(await screen.findByText('actual effort unknown or invalid.')).toBeInTheDocument();
  expect(screen.queryByText('Suggested 24.3 lb')).not.toBeInTheDocument();
  fireEvent.click(nativeScreen.getByRole('button',{name:'Close Guide & setup'}));
  expect(screen.getByRole('spinbutton',{name:'Weight (lb)'})).toHaveValue(60);
  expect(screen.getByRole('spinbutton',{name:'Reps'})).toHaveValue(9);
  fireEvent.click(nativeScreen.getByRole('button',{name:/Recorded sets ·/}));
  expect(screen.getAllByText(/Set 1: 12 reps @ 22 lb/).length).toBeGreaterThan(0);
  expect(screen.queryByText(/Actual RIR 5/)).not.toBeInTheDocument();
  fireEvent.click(nativeScreen.getByRole('button',{name:'Close Recorded sets'}));
  if(draftState === 'uncertain') {
    fireEvent.click(nativeScreen.getByRole('button',{name:'Retry same set'}));
    await waitFor(() => expect(writes).toHaveLength(2));
    expect(writes[1]).toEqual(writes[0]);
  }
  vi.unstubAllGlobals();
});
