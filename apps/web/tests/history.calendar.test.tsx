import React from "react";
import {fireEvent, render, screen} from "@testing-library/react";
import {beforeEach, expect, test, vi} from "vitest";
import HistoryPage from "@/app/history/page";

const day = (date:string, program="pure_bodybuilding_phase_1_full_body") => ({date,weekday:0,set_count:2,exercise_count:1,total_volume:1200,completed:true,program_ids:[program],muscles:["chest"],pr_count:1,pr_exercises:["bench_press"]});
const detail = {date:"2026-03-02",totals:{set_count:2,planned_set_count:3,exercise_count:1,total_volume:1200},workouts:[{
  workout_id:"workout_a",total_sets:2,planned_sets_total:3,total_volume:1200,exercises:[{exercise_id:"bench_press",planned_name:"Bench Press",planned_sets:3,total_sets:2,total_volume:1200,sets:[
    {set_index:1,reps:8,weight:80,rpe:null,created_at:"2026-03-02T09:00:00Z"},
    {set_index:2,reps:7,weight:82.5,rpe:null,created_at:"2026-03-02T09:05:00Z",supersedes_id:"old-receipt"},
  ]}]}]};
let failCalendar=false;
let failDetail=false;
const requests:URL[]=[];
beforeEach(()=>{
  failCalendar=false;failDetail=false;requests.length=0;
  vi.stubGlobal("fetch",vi.fn(async(input)=>{
    const url=new URL(String(input),"http://history.test");requests.push(url);
    if(url.pathname.endsWith("/plan/scheduling-context"))return Response.json({local_today:"2026-03-05"});
    if(url.pathname.endsWith("/history/calendar"))return failCalendar?Response.json({}, {status:503}):Response.json({start_date:url.searchParams.get("start_date"),end_date:url.searchParams.get("end_date"),days:[day("2026-03-02"),day("2026-03-03","upper_lower_v1")],active_days:2,current_streak_days:0,longest_streak_days:1});
    if(url.pathname.includes("/history/day/"))return failDetail?Response.json({}, {status:503}):Response.json(detail);
    throw new Error(`Unexpected request ${url.pathname}`);
  }));
});

test("prior day receipts preserve units, unknown effort and correction lineage without inventing completion",async()=>{
  render(<HistoryPage/>);fireEvent.click(await screen.findByRole("button",{name:"2026-03-02: Unknown"}));
  await screen.findByRole("heading",{name:"Workout workout_a"});
  expect(screen.getByText("Bench Press")).toBeInTheDocument();
  expect(screen.getByText("3 planned working sets")).toBeInTheDocument();
  expect(screen.getByText("Set 1: 8 × 176.4 lb")).toBeInTheDocument();
  expect(screen.getByText("Set 2: 7 × 181.9 lb")).toBeInTheDocument();
  expect(screen.getByText("Actual RPE unknown · corrected effective record")).toBeInTheDocument();
  expect(screen.getByText(/Correction of old-receipt/)).toBeInTheDocument();
  expect(screen.getByText(/Legacy recorded workout/)).toBeInTheDocument();
  expect(screen.queryByText(/Missed/)).not.toBeInTheDocument();
});

test("calendar week and month use real boundaries and program filters retain weekday positions",async()=>{
  render(<HistoryPage/>);await screen.findByRole("button",{name:"2026-03-02: Unknown"});
  expect(requests.at(-1)?.searchParams.get("start_date")).toBe("2026-03-02");
  fireEvent.click(screen.getByRole("button",{name:"Month"}));
  await screen.findByRole("button",{name:"2026-03-02: Unknown"});
  expect(requests.at(-1)?.searchParams.get("start_date")).toBe("2026-03-01");
  expect(requests.at(-1)?.searchParams.get("end_date")).toBe("2026-03-31");
  fireEvent.change(screen.getByLabelText("Program filter"),{target:{value:"upper_lower_v1"}});
  expect(screen.getByRole("button",{name:"2026-03-02: Unknown"})).toBeDisabled();
  expect(screen.getByRole("button",{name:"2026-03-03: Unknown"})).toBeEnabled();
  expect(screen.getByRole("button",{name:"2026-03-03: Unknown"})).toHaveStyle({gridColumn:"2"});
  expect(screen.getByRole("link",{name:"See your progress"})).toHaveAttribute("href","/analytics");
});

test("calendar read failure retries without being presented as no history",async()=>{
  failCalendar=true;render(<HistoryPage/>);
  await screen.findByText("Unable to load calendar history.");
  expect(screen.queryByText("No calendar history yet.")).not.toBeInTheDocument();
  failCalendar=false;fireEvent.click(screen.getByRole("button",{name:"Retry Calendar Load"}));
  await screen.findByRole("button",{name:"2026-03-02: Unknown"});
});

test("day read failure clears detail and retries the same selected date",async()=>{
  failDetail=true;render(<HistoryPage/>);fireEvent.click(await screen.findByRole("button",{name:"2026-03-02: Unknown"}));
  await screen.findByText("Unable to load day detail.");failDetail=false;
  fireEvent.click(screen.getByRole("button",{name:"Retry day detail"}));
  await screen.findByRole("heading",{name:"Workout workout_a"});
  expect(requests.filter(url=>url.pathname.endsWith("/history/day/2026-03-02"))).toHaveLength(2);
});
