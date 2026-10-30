import React from "react";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import HomePage from "@/app/page";
import TodayPage from "@/app/today/page";
import { clearAuthToken } from "@/lib/api";
const token = (sub: string) => `header.${btoa(JSON.stringify({ sub }))}.signature`;
const preview = {plan_id:"week",workout_occurrence_id:"next",original_date:"2026-10-31",local_today:"2026-10-30",timezone:"America/New_York",program_template_id:"pure_bodybuilding_phase_1_full_body",placement_revision:4,session:{title:"Full Body B",exercises:[{id:"press",name:"Preview Press",sets:3},{id:"row",name:"Preview Row",sets:4}]},can_move:true,blocked_reason:null,preview_digest:"digest"};
function serve(options: { blocked?: string; conflict?: boolean; pendingToday?: boolean; pendingPreview?: boolean; pendingMove?: boolean; hasWorkout?: boolean; workoutIdentity?: Record<string, unknown>; nextProgramId?: string | null } = {}) {
  let moved=false; let resolvePreview!: (r:Response)=>void; let resolveMove!: (r:Response)=>void;
  const writes:Record<string,unknown>[]=[]; const reads:string[]=[];
  vi.stubGlobal("fetch",vi.fn(async(input,init)=>{
    const path=String(input);
    if(path.endsWith("/health")) return Response.json({status:"ok"});
    if(path.includes("/plan/scheduling-context?")) return Response.json({timezone:"America/New_York",local_today:"2026-10-30",week_start:"2026-10-26",selected_dates:[],plan:null});
    if(path.endsWith("/workout/today")) {
      if(options.pendingToday) return new Promise<Response>(()=>{});
      return moved || options.hasWorkout?Response.json({session_id:"template",workout_occurrence_id:"next",title:"Full Body B",date:"2026-10-30",exercises: options.hasWorkout ? preview.session.exercises : [], ...options.workoutIdentity}):Response.json({detail:"No workout scheduled today"},{status:404});
    }
    if(path.endsWith("/workout/next-planned")) {
      reads.push(new Headers(init?.headers).get("Authorization")??"");
      if(options.pendingPreview) return new Promise<Response>(resolve=>{resolvePreview=resolve;});
      return Response.json({...preview,program_template_id: options.nextProgramId === undefined ? preview.program_template_id : options.nextProgramId,can_move:!options.blocked,blocked_reason:options.blocked??null});
    }
    if(path.endsWith("/workout/next-planned/move")) {
      writes.push(JSON.parse(init.body));
      if(options.pendingMove) return new Promise<Response>(resolve=>{resolveMove=resolve;});
      if(options.conflict) return Response.json({detail:"Placement changed"},{status:409});
      moved=true; return Response.json({});
    }
    if(path.includes("/soreness")) return Response.json([{entry_date:"2026-10-30"}]);
    if(path.endsWith("/profile")) return Response.json({selected_program_id:"pure_bodybuilding_phase_1_full_body",days_available:3});
    if(path.includes("/progress")) return Response.json({exercises:[],completed_total:0,planned_total:0});
    return Response.json({});
  }));
  return {writes,reads,resolvePreview:(r:Response)=>resolvePreview(r),resolveMove:(r:Response)=>resolveMove(r)};
}
beforeEach(()=>{localStorage.setItem("hypertrophy_token",token("next-a"));});

test("Home only reads the next preview after Today is known empty",async()=>{
  const server=serve({pendingToday:true}); render(<HomePage/>);
  await screen.findByText("Checking your training"); expect(server.reads).toHaveLength(0);
  expect(screen.queryByRole("button",{name:"Do this workout today"})).not.toBeInTheDocument();
});
test("preview and Keep original date are read-only and never open execution",async()=>{
  const server=serve(); render(<HomePage/>);
  await screen.findByRole("button",{name:"Do this workout today"});
  expect(screen.getByText("Preview Press")).toBeInTheDocument(); expect(screen.getByText("Preview Row")).toBeInTheDocument();
  expect(screen.getByText(/7 (planned )?working sets/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button",{name:"Keep original date"}));
  expect(screen.getByText(/Original date kept/)).toBeInTheDocument(); expect(screen.getByText("Preview Press")).toBeInTheDocument();
  expect(screen.queryByRole("link",{name:"Open today's workout"})).not.toBeInTheDocument(); expect(server.writes).toEqual([]);
});
test("move needs explicit confirmation of exact reviewed snapshot and refreshes Home once",async()=>{
  const server=serve(); render(<HomePage/>);
  fireEvent.click(await screen.findByRole("button",{name:"Do this workout today"}));
  const dialog=screen.getByRole("dialog",{name:"Move this workout to today?"});
  expect(within(dialog).getByText(/America\/New_York/)).toBeInTheDocument(); expect(within(dialog).getByText(/7 (planned )?working sets/)).toBeInTheDocument(); expect(server.writes).toEqual([]);
  const confirm=within(dialog).getByRole("button",{name:"Confirm move to today"});
  fireEvent.click(confirm); fireEvent.click(confirm);
  await screen.findByRole("link",{name:"Open today's workout"});
  expect(server.writes).toEqual([{plan_id:"week",workout_occurrence_id:"next",expected_original_date:"2026-10-31",expected_local_today:"2026-10-30",expected_placement_revision:4,expected_preview_digest:"digest",confirmed:true}]);
});
test("blocked preview explains server reason without allowing confirmation",async()=>{
  const server=serve({blocked:"A workout in this week has already started."}); render(<HomePage/>);
  expect(await screen.findByRole("button",{name:"Do this workout today"})).toBeDisabled(); expect(screen.getByText("A workout in this week has already started.")).toBeInTheDocument(); expect(server.writes).toEqual([]);
});
test("409 closes confirmation and refetches for review without retrying mutation",async()=>{
  const server=serve({conflict:true}); render(<HomePage/>);
  fireEvent.click(await screen.findByRole("button",{name:"Do this workout today"})); fireEvent.click(screen.getByRole("button",{name:"Confirm move to today"}));
  await screen.findByText(/changed.*review.*again/i); await waitFor(()=>expect(server.reads).toHaveLength(2));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument(); expect(server.writes).toHaveLength(1);
});
test("account change discards a late preview",async()=>{
  const server=serve({pendingPreview:true}); render(<HomePage/>); await waitFor(()=>expect(server.reads).toHaveLength(1));
  act(()=>clearAuthToken()); await screen.findByRole("link",{name:"Sign in"});
  await act(async()=>server.resolvePreview(Response.json(preview))); expect(screen.queryByText("Preview Press")).not.toBeInTheDocument();
});
test("account change discards late move and completion callback",async()=>{
  const server=serve({pendingMove:true}); render(<HomePage/>);
  fireEvent.click(await screen.findByRole("button",{name:"Do this workout today"})); fireEvent.click(screen.getByRole("button",{name:"Confirm move to today"})); await waitFor(()=>expect(server.writes).toHaveLength(1));
  act(()=>clearAuthToken()); await screen.findByRole("link",{name:"Sign in"}); const count=vi.mocked(fetch).mock.calls.length;
  await act(async()=>server.resolveMove(Response.json({}))); expect(vi.mocked(fetch).mock.calls).toHaveLength(count); expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});
test("newly pending undo rejects an already open confirmation",async()=>{
  const server=serve(); render(<HomePage/>); fireEvent.click(await screen.findByRole("button",{name:"Do this workout today"}));
  localStorage.setItem("hypertrophy_undo_recovery_v1:next-a:payload",JSON.stringify({command:"pending"})); fireEvent.click(screen.getByRole("button",{name:"Confirm move to today"}));
  expect(server.writes).toEqual([]); expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});
test("Today rest day with pending undo never offers a date mutation",async()=>{
  const server=serve(); localStorage.setItem("hypertrophy_undo_recovery_v1:next-a:payload",JSON.stringify({scope:"prior",workoutId:"prior",exerciseId:"press",exerciseIdentity:"press",command:"pending"})); render(<TodayPage/>);
  await screen.findByRole("heading",{name:"No workout scheduled today"}); expect(screen.getByRole("button",{name:"Retry original undo"})).toBeInTheDocument(); expect(screen.queryByRole("button",{name:"Do this workout today"})).not.toBeInTheDocument(); expect(server.reads).toHaveLength(0);
});


test("Today previews on an acknowledged rest day and only loads moved work after confirmation",async()=>{
  const server=serve(); render(<TodayPage/>);
  fireEvent.click(await screen.findByRole("button",{name:"Do this workout today"}));
  expect(screen.queryByRole("list",{name:"Exercise list"})).not.toBeInTheDocument();
  expect(server.writes).toEqual([]);
  fireEvent.click(screen.getByRole("button",{name:"Confirm move to today"}));
  await screen.findByRole("list",{name:"Exercise list"});
  expect(server.writes).toHaveLength(1);
});

test("unknown Today failure never grants preview or move authority",async()=>{
  const server=serve(); const fetcher=vi.mocked(fetch).getMockImplementation()!;
  vi.stubGlobal("fetch",vi.fn((input,init)=>String(input).endsWith("/workout/today")?Promise.resolve(Response.json({detail:"Unrecognized absence"},{status:404})):fetcher(input,init)));
  render(<TodayPage/>);
  await screen.findByText("No workout available. Open Week to review your schedule.");
  expect(server.reads).toHaveLength(0); expect(screen.queryByRole("button",{name:"Do this workout today"})).not.toBeInTheDocument();
});


const workloadCards = ["Home", "Today", "Next preview"] as const;
const nonAuthoredIdentities = ["full_body_v1", "unknown_program", null] as const;
for (const card of workloadCards) {
  test.each(nonAuthoredIdentities)(`${card} workload never claims source-preserving scheduling for %s`, async programId => {
    serve({hasWorkout:card !== "Next preview",workoutIdentity:{program_template_id:programId},nextProgramId:programId});
    render(card === "Today" ? <TodayPage/> : <HomePage/>);
    if(card === "Next preview") await screen.findByRole("button",{name:"Do this workout today"});
    else if(card === "Home") await screen.findByRole("link",{name:"Open today's workout"});
    else await screen.findByRole("list",{name:"Exercise list"});
    expect(screen.getByText(/7 planned working sets/)).toBeInTheDocument();
    expect(screen.queryByText(/spread all source exercises/)).not.toBeInTheDocument();
    expect(screen.queryByRole("link",{name:"Review 2–5 selected visits in Week"})).not.toBeInTheDocument();
  });
  test.each(["pure_bodybuilding_phase_1_full_body","pure_bodybuilding_phase_2_full_body"])(`${card} workload preserves Authored guidance for explicit %s identity`, async programId => {
    serve({hasWorkout:card !== "Next preview",workoutIdentity:{program_template_id:programId},nextProgramId:programId});
    render(card === "Today" ? <TodayPage/> : <HomePage/>);
    expect(await screen.findByText(/spread all source exercises/)).toBeInTheDocument();
  });
}
