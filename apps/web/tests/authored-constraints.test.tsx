import React from "react";
import { beforeEach, expect, test, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import AuthoredConstraintCard from "@/components/AuthoredConstraintCard";
import TodayPage from "@/app/today/page";
import type { WorkoutExercise } from "@/lib/api";

const source: WorkoutExercise = { id: "source", name: "Original squat", exercise_occurrence_id: "source-occurrence",
  sets: 1, rep_range: [8,12], recommended_working_weight: 25, source_lineage: { source_slot_id: "source-slot" },
  authored_prescription: { version: "authored-prescription-v1", raw: { reps: "8-12" }, sets: [{ set_index: 1,
    set_type: "work", rep_target: { kind: "reps", raw: "8-12", min: 8, max: 12 },
    effort_target: { kind: "rpe", raw: "8" }, rest: "2 min", intensity_technique: null }] },
  authored_constraint: { status: "unresolved", revision: 0, reasons: [{kind:"restriction",details:["deep_knee_flexion"]}],
    allowed_alternatives: [{ option_id: "source-option", id: "variant", name: "Approved hinge", load_semantics: "bodyweight", permission: { source_slot_id: "source-slot" } }] },
  substitution_candidates: ["Forbidden generic swap"] };

beforeEach(() => { localStorage.clear(); globalThis.fetch = vi.fn(); });

test("choosing an allowed source alternative does not apply it before explicit confirmation", async () => {
  const apply = vi.fn(async () => {});
  render(<AuthoredConstraintCard exercise={source} onDecision={apply} />);
  expect(screen.getByText(/Original authored exercise: Original squat/)).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Source-approved alternative"), {target:{value:"source-option"}});
  expect(apply).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button",{name:"Confirm this alternative"}));
  await waitFor(() => expect(apply).toHaveBeenCalledWith({action:"confirm",option_id:"source-option"}));
});

test("decline retains the unresolved slot; missing permission stays visible", async () => {
  const apply = vi.fn(async () => {});
  render(<AuthoredConstraintCard exercise={{...source,authored_constraint:{...source.authored_constraint!,allowed_alternatives:[],status:"infeasible"}}} onDecision={apply} />);
  expect(screen.getByText(/No qualified source-approved alternative/)).toBeInTheDocument();
  expect(screen.queryByLabelText("Source-approved alternative")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button",{name:"Decline alternatives"}));
  await waitFor(() => expect(apply).toHaveBeenCalledWith({action:"decline"}));
});

test("Today blocks unresolved logging and uses server confirmation while retaining source identity", async () => {
  let current = structuredClone(source);
  const fetch = vi.mocked(globalThis.fetch);
  fetch.mockImplementation(async (input, init) => {
    const url = String(input);
    let payload: unknown = {};
    if(url.endsWith('/workout/today')) payload = { session_id:"source-workout",workout_occurrence_id:"workout-occurrence",title:"Source workout",date:new Date().toISOString().slice(0,10),exercises:[current] };
    if(url.includes('/soreness')) payload = [{id:"example"}];
    if(url.endsWith('/progress')) payload = {completed_total:0,planned_total:1,percent_complete:0,exercises:[]};
    if(url.endsWith('/authored-substitution')) {
      const body = JSON.parse(String(init?.body));
      expect(body.exercise_id).toBe('source'); expect(body.exercise_occurrence_id).toBe('source-occurrence');
      expect(body.expected_source_lineage).toEqual(source.source_lineage);
      current = {...current, performed_variant:current.authored_constraint!.allowed_alternatives[0],
        authored_constraint:{...current.authored_constraint!,status:'confirmed',revision:1},
        substitution_consent:{confirmed:true},recommended_working_weight:0};
      payload = {exercise:current,workout_occurrence_id:'workout-occurrence'};
    }
    return new Response(JSON.stringify(payload),{status:200});
  });
  render(<TodayPage />);
  fireEvent.click(screen.getByRole('button',{name:/Load today's workout/i}));
  await waitFor(() => expect(screen.getByRole('button',{name:/Original squat/i})).toBeInTheDocument());
  fireEvent.click(screen.getByRole('button',{name:/Original squat/i}));
  expect(screen.getByRole('button',{name:'Resolve authored slot first'})).toBeDisabled();
  expect(screen.queryByRole('button',{name:/Use Forbidden generic/})).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Source-approved alternative'),{target:{value:'source-option'}});
  expect(fetch.mock.calls.some(([input])=>String(input).endsWith('/authored-substitution'))).toBe(false);
  fireEvent.click(screen.getByRole('button',{name:'Confirm this alternative'}));
  await waitFor(() => expect(screen.getByText('Confirmed performed variant: Approved hinge')).toBeInTheDocument());
  expect(screen.getByText('Original authored exercise: Original squat')).toBeInTheDocument();
  expect(screen.getByLabelText('Added load (lb), optional')).toHaveValue(0);
  expect(screen.queryByText('Baseline Calculator')).not.toBeInTheDocument();
});
