import React from 'react';
import {fireEvent,render,screen} from '@testing-library/react';
import {beforeEach,expect,test,vi} from 'vitest';
import WeekPage from '@/app/week/page';

beforeEach(()=>{vi.restoreAllMocks();localStorage.clear();});
test.each([undefined,{}])('Customized Week retains unknown calibration and saved-unit loads without inventing legacy week or coverage claims (%j)',async(coverage)=>{
 const custom={target_kind:'rir',target_min:2,target_max:3,rest_seconds:{low:90,high:120},identity:{basis:'per_hand',equipment_key:'dumbbell',setup:'actual',unit:'kg'}};
 const plan={muscle_coverage:coverage,customized:{proposal_id:'active'},program_template_id:'customized_full_body_v1',split:'full_body',phase:'customized',week_start:'2026-10-19',sessions:[{session_id:'session',title:'Customized Full Body',date:'2026-10-20',exercises:[{id:'row',name:'Unknown row',sets:3,rep_range:[8,12],recommended_working_weight:null,customized:custom},{id:'press',name:'Qualified press',sets:3,rep_range:[8,12],recommended_working_weight:12.5,customized:custom}]}]};
 vi.stubGlobal('fetch',vi.fn(async(input:string)=>{
  if(String(input).endsWith('/profile'))return Response.json({selected_program_id:'customized_full_body_v1',days_available:3});
  if(String(input).endsWith('/plan/programs'))return Response.json([]);
  if(String(input).includes('/plan/scheduling-context?'))return Response.json({timezone:'America/New_York',local_today:'2026-10-20',week_start:'2026-10-19',selected_dates:['2026-10-20'],placement_revision:1,plan});
  return Response.json({});
 }));
 render(<WeekPage/>);await screen.findByText('Week Overview');
 expect(screen.queryByText(/Week 0/)).not.toBeInTheDocument();expect(screen.queryByRole('button',{name:/Mesocycle Posture/})).not.toBeInTheDocument();expect(screen.queryByText(/0 covered/)).not.toBeInTheDocument();expect(screen.queryByText(/All muscles on target/)).not.toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:/Tue, Oct 20: Customized Full Body/}));
 expect(screen.getAllByText(/Exercise-specific calibration pending/).length).toBeGreaterThan(0);
 expect(screen.getByText(/3 sets · 8[-–]12 reps · 27.6 lb/)).toBeVisible();
 expect(screen.queryByText(/0 lbs/)).not.toBeInTheDocument();expect(screen.queryByText(/27.56 lbs/)).not.toBeInTheDocument();
});
