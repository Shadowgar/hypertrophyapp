import React from 'react';
import { render, screen } from '@testing-library/react';
import { expect, test, vi } from 'vitest';
import HistoryPage from '@/app/history/page';
test('history labels End Early and amended coverage without presenting full completion',async()=>{
 vi.stubGlobal('fetch',vi.fn(async(input)=>{
  const url=new URL(String(input),'http://history.test');
  if(url.pathname.endsWith('/plan/scheduling-context'))return Response.json({local_today:'2026-10-30'});
  if(url.pathname.endsWith('/history/calendar'))return Response.json({start_date:url.searchParams.get('start_date'),end_date:url.searchParams.get('end_date'),days:[{date:'2026-10-28',status:'ended_early',set_count:2,program_ids:[],occurrences:[{workout_occurrence_id:'a',title:'Source A',status:'ended_early',working_sets_completed:2,working_sets_planned:3}]},{date:'2026-10-29',status:'amended_incomplete',set_count:1,program_ids:[],occurrences:[{workout_occurrence_id:'b',title:'Source B',status:'amended_incomplete',working_sets_completed:1,working_sets_planned:3}]}]});
  return Response.json({});
 }));render(<HistoryPage/>);
 expect(await screen.findByRole('button',{name:'2026-10-28: Ended early · incomplete'})).toBeInTheDocument();
 expect(screen.getByRole('button',{name:'2026-10-29: Amended · incomplete'})).toBeInTheDocument();
});
