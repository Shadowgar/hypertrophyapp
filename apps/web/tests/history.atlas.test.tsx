import React from "react";
import {act, cleanup, fireEvent, render, screen, waitFor} from "@testing-library/react";
import HistoryPage from "@/app/history/page";
import {setAuthToken} from "@/lib/api";

const statuses = ["complete", "rest", "partial", "scheduled", "unknown", "rest", "rest"];
const days = statuses.map((status, i) => ({date:`2026-10-${19+i}`, weekday:i, status,
  set_count:status === "partial" ? 1 : status === "complete" ? 2 : 0, completed:status === "partial" || status === "complete",
  exercise_count:1, total_volume:20, program_ids:["pure_bodybuilding_phase_1_full_body"], muscles:["chest"], pr_count:0, pr_exercises:[],
  working_sets_completed:status === "complete" ? 2 : status === "partial" ? 1 : 0, working_sets_planned:2,
  occurrences:["complete","partial","scheduled"].includes(status) ? [{workout_occurrence_id:`occ-${i}`,workout_id:`template-${i}`,title:`Workout ${i}`,status,working_sets_completed:status === "complete" ? 2 : status === "partial" ? 1 : 0,working_sets_planned:2}] : []}));
const calendar = {start_date:"2026-10-19",end_date:"2026-10-25",active_days:2,current_streak_days:0,longest_streak_days:1,days};
const detail = (date:string,name:string) => ({date,totals:{set_count:1,exercise_count:1,total_volume:80,planned_set_count:2},workouts:[{workout_id:name,workout_occurrence_id:`occ-${date === "2026-10-19" ? 0 : 2}`,title:name,total_sets:1,total_volume:80,exercises:[{exercise_id:name,planned_name:name,total_sets:1,total_volume:80,sets:[{id:name,set_index:1,reps:8,weight:10,rpe:null,created_at:`${date}T12:00:00Z`}]}]}]});
function deferred(){let resolve!:(value:Response)=>void;const promise=new Promise<Response>(r=>resolve=r);return {promise,resolve};}
function fixture(override:(url:string,init?:RequestInit)=>Response|Promise<Response>|undefined=()=>undefined){
  vi.stubGlobal("fetch",vi.fn(async(input,init)=>{const url=String(input);const custom=override(url,init);if(custom!==undefined)return custom;
    if(url.includes("/plan/scheduling-context"))return Response.json({local_today:"2026-10-21",timezone:"UTC"});
    if(url.includes("/history/calendar"))return Response.json(calendar);
    if(url.includes("/history/day/"))return Response.json(detail(url.slice(-10),"Current Press"));
    return Response.json({});}));
}
afterEach(()=>{cleanup();vi.unstubAllGlobals();});

test("calendar filters preserve weekday positions and never promote partial activity to completion",async()=>{
  fixture();render(<HistoryPage/>);
  const partial=await screen.findByRole("button",{name:/2026-10-21: Partial/});
  expect(partial).toHaveStyle({gridColumn:"3"});
  expect(screen.getByRole("button",{name:/2026-10-20: Rest/})).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Status filter"),{target:{value:"complete"}});
  expect(partial).toBeDisabled();
  expect(partial).toHaveStyle({gridColumn:"3"});
  expect(screen.getByRole("button",{name:/2026-10-19: Complete/})).toBeEnabled();
});

test("late day detail cannot replace a newer selected date",async()=>{
  const old=deferred();fixture(url=>url.endsWith("/history/day/2026-10-19")?old.promise:undefined);
  render(<HistoryPage/>);
  fireEvent.click(await screen.findByRole("button",{name:/2026-10-19: Complete/}));
  fireEvent.click(screen.getByRole("button",{name:/2026-10-21: Partial/}));
  await screen.findByRole("heading",{name:"Current Press",level:3});
  await act(async()=>old.resolve(Response.json(detail("2026-10-19","Old Press"))));
  expect(screen.queryByRole("heading",{name:"Old Press",level:3})).not.toBeInTheDocument();
  expect(screen.getByRole("heading",{name:"Current Press",level:3})).toBeInTheDocument();
});

test("account replacement retires in-flight detail and clears visible prior receipts",async()=>{
  setAuthToken("history-account-a");const old=deferred();
  fixture((url,init)=>url.includes("/history/day/") && new Headers(init?.headers).get("Authorization")==="Bearer history-account-a"?old.promise:undefined);
  render(<HistoryPage/>);fireEvent.click(await screen.findByRole("button",{name:/2026-10-19: Complete/}));
  act(()=>setAuthToken("history-account-b"));
  await waitFor(()=>expect(screen.queryByText("Loading day detail…")).not.toBeInTheDocument());
  await act(async()=>old.resolve(Response.json(detail("2026-10-19","Old Account Press"))));
  expect(screen.queryByText("Old Account Press")).not.toBeInTheDocument();
});

test("changing a filter clears selected detail outside the filtered view",async()=>{
  fixture();render(<HistoryPage/>);
  fireEvent.click(await screen.findByRole("button",{name:/2026-10-21: Partial/}));
  await screen.findByRole("heading",{name:"Current Press",level:3});
  fireEvent.change(screen.getByLabelText("Status filter"),{target:{value:"complete"}});
  expect(screen.queryByRole("heading",{name:"Current Press",level:3})).not.toBeInTheDocument();
});

test("a mismatched day response is rejected and remains retryable",async()=>{
  fixture(url=>url.includes("/history/day/")?Response.json(detail("2026-10-19","Wrong date press")):undefined);
  render(<HistoryPage/>);fireEvent.click(await screen.findByRole("button",{name:/2026-10-21: Partial/}));
  await screen.findByRole("button",{name:"Retry day detail"});
  expect(screen.queryByText("Wrong date press")).not.toBeInTheDocument();
});
