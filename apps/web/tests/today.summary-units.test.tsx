import React from "react";
import {fireEvent, render, screen, within} from "@testing-library/react";
import TodayPage from "@/app/today/page";
const state = vi.hoisted(() => ({unit: "kg" as "kg" | "lb"}));
vi.mock("@/components/appearance-provider", () => ({useAppearance: () => ({preferences: {theme_family:"classic",appearance:"dark",weight_unit:state.unit,revision:0}})}));

afterEach(() => vi.unstubAllGlobals());
test.each(["kg", "lb"] as const)("completed Authored and Customized summaries respect %s without changing canonical inputs", async unit => {
  state.unit=unit;localStorage.clear();
  const today=new Date().toISOString().slice(0,10);
  const exercise={id:"press",name:"Press",sets:1,rep_range:[8,12],completed_sets:1};
  const item={exercise_id:"press",name:"Authored press",planned_sets:1,performed_sets:1,planned_reps_min:8,planned_reps_max:12,planned_weight:10,average_performed_reps:12,average_performed_weight:10,next_working_weight:12,guidance:"Maintain"};
  vi.stubGlobal("fetch",vi.fn(async input => {
    const url=String(input);
    if(url.includes("/plan/scheduling-context?"))return Response.json({timezone:"UTC",local_today:today,week_start:today,selected_dates:[],placement_revision:0,plan:null});
    if(url.endsWith("/workout/today"))return Response.json({session_id:"template",workout_occurrence_id:"occurrence",title:"Completed",date:today,exercises:[exercise]});
    if(url.endsWith("/progress"))return Response.json({completed_total:1,planned_total:1,percent_complete:100,exercises:[{exercise_id:"press",completed_sets:1}]});
    if(url.endsWith("/summary"))return Response.json({percent_complete:100,overall_guidance:"Increase load next exposure.",exercises:[{...item,load_intelligence:{next_exposure:{action:"hold",recommended_weight:12,known_baseline_weight:10,explanation:"Qualified history"}}},{...item,exercise_id:"custom",name:"Customized press",decision_trace:{owner:"api.workout_customized-v1"}}]});
    if(url.includes("/soreness"))return Response.json([{entry_date:today}]);
    return Response.json({});
  }));
  render(<TodayPage/>);fireEvent.click(screen.getByRole("button",{name:/Load today's workout/}));
  const card=(await screen.findByText("Day Summary")).closest(".main-card")!;
  const summary=within(card as HTMLElement);
  expect(card.textContent).not.toContain("Increase load next exposure.");
  const load=unit==="kg"?"10 kg":"22 lb",next=unit==="kg"?"12 kg":"26.5 lb";
  expect(summary.getAllByText(new RegExp(`Planned:.*${load}`))).toHaveLength(2);
  expect(summary.getAllByText(new RegExp(`Performed:.*${load}`))).toHaveLength(2);
  expect(summary.getByText(`Next exposure: hold · ${next}`)).toBeInTheDocument();
  expect(summary.getByText(`Known baseline: ${load}`)).toBeInTheDocument();
  expect(summary.getByText(`Next: ${next}`)).toBeInTheDocument();
  expect(card.textContent).not.toContain(unit==="kg"?" lb":" kg");
});
