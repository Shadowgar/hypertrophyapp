import React from "react";
import { beforeEach, expect, test, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import TodayPage from "@/app/today/page";
import { authoredRepLabel, authoredSetDetails, authoredSetRepRange, authoredSetTechnique } from "@/lib/authored-prescription";
import type { WorkoutExercise } from "@/lib/api";

const exercise: WorkoutExercise = {
  id: "synthetic-pushup", exercise_occurrence_id: "synthetic-slot", name: "Synthetic Push-Up",
  sets: 2, rep_range: null, recommended_working_weight: 20,
  authored_prescription: { version: "authored-prescription-v1", raw: { reps: "AMRAP" }, sets: [
    { set_index: 1, set_type: "work", rep_target: { kind: "amrap", raw: "AMRAP" },
      effort_target: { kind: "rpe", raw: "~8-9", min: 8, max: 9 }, rest: "2-3 min", intensity_technique: null },
    { set_index: 2, set_type: "work", rep_target: { kind: "amrap", raw: "AMRAP" },
      effort_target: { kind: "rpe", raw: "10", min: 10, max: 10 }, rest: "2-3 min", intensity_technique: "Example technique" },
  ] },
};

beforeEach(() => { globalThis.fetch = vi.fn(); localStorage.clear(); });

test("typed labels never invent numeric AMRAP bounds and preserve distinct set details", () => {
  expect(authoredRepLabel(exercise)).toBe("AMRAP");
  expect(authoredSetRepRange(exercise, 1)).toBeNull();
  expect(authoredSetDetails(exercise, 1)).toBe("RPE ~8-9 · Rest 2-3 min");
  expect(authoredSetDetails(exercise, 2)).toContain("RPE 10");
  expect(authoredSetDetails(exercise, 2)).toContain("Example technique");
  const positional = structuredClone(exercise);
  positional.authored_prescription!.raw.reps = "6, 10";
  positional.authored_prescription!.sets[0].rep_target = { kind: "reps", raw: "6", min: 6, max: 6 };
  positional.authored_prescription!.sets[1].rep_target = { kind: "reps", raw: "10", min: 10, max: 10 };
  expect(authoredSetRepRange(positional, 1)).toEqual([6, 6]);
  expect(authoredSetRepRange(positional, 2)).toEqual([10, 10]);
  expect(authoredRepLabel(positional, 2)).toBe("10");
});

test.each(["Mechanical Dropset (on all sets)", "Integrated Partials (All Sets)", "Mechanical Dropset (last set)"])("runner follows per-set scope for %s", async (instruction) => {
  const prescribed = structuredClone(exercise);
  prescribed.rep_range = [8, 12];
  prescribed.last_set_intensity_technique = instruction;
  const allSets = instruction.includes("all sets") || instruction.includes("All Sets");
  prescribed.authored_prescription!.sets.forEach((set, index) => {
    set.rep_target = { kind: "reps", raw: "8-12", min: 8, max: 12 };
    set.intensity_technique = allSets || index === 1 ? instruction : null;
  });
  expect(authoredSetTechnique(prescribed, 1)).toBe(allSets ? instruction : null);
  let completed = 0;
  const workout = { session_id: "synthetic", workout_occurrence_id: "synthetic-occurrence", title: "Synthetic authored",
    date: new Date().toISOString().slice(0, 10), exercises: [prescribed] };
  const mock = vi.mocked(globalThis.fetch);
  mock.mockImplementation(async (input, init) => {
    const url = String(input);
    let payload: object = {};
    if (url.includes("/workout/today")) payload = workout;
    else if (url.includes("/soreness")) payload = [{ id: "example" }];
    else if (url.includes("/progress")) payload = { completed_total: completed, planned_total: 2, percent_complete: completed * 50,
      exercises: [{ exercise_id: prescribed.id, exercise_occurrence_id: prescribed.exercise_occurrence_id, completed_sets: completed }] };
    else if (url.endsWith("/log-set")) {
      const body = JSON.parse(String(init?.body));
      if (body.set_kind !== "technique") completed += 1;
      payload = { id: "receipt", reps: body.reps, weight: body.weight, next_working_weight: 20,
        planned_reps_min: 8, planned_reps_max: 12, planned_weight: 20, rep_delta: 0, weight_delta: 0,
        guidance: "Follow source", decision_trace: {} };
    }
    return new Response(JSON.stringify(payload), { status: 200 });
  });
  render(<TodayPage />);
  fireEvent.click(screen.getByRole("button", { name: /Load today's workout/i }));
  await waitFor(() => expect(screen.getByRole("button", { name: /Synthetic Push-Up/i })).toBeInTheDocument());
  fireEvent.click(screen.getByRole("button", { name: /Synthetic Push-Up/i }));
  await waitFor(() => expect(screen.getByRole("dialog")).toBeInTheDocument());
  const complete = screen.getByRole("button", { name: /Complete (Set|technique steps first)/i });
  if (allSets) {
    expect(complete).toBeDisabled();
    fireEvent.click(screen.getByRole("checkbox", { name: /I will execute these technique cues/ }));
  } else expect(screen.queryByRole("checkbox", { name: /I will execute these technique cues/ })).not.toBeInTheDocument();
  fireEvent.change(screen.getByRole("spinbutton", { name: "Reps" }), { target: { value: "12" } });
  fireEvent.click(complete);
  await waitFor(() => expect(completed).toBe(1));
  if (allSets && instruction.startsWith("Mechanical")) {
    await waitFor(() => expect(screen.getByText(/after working set 1/)).toBeInTheDocument());
    const techniqueLog = screen.getByRole("button", { name: /Log technique/i });
    const prior = mock.mock.calls.filter(([input]) => String(input).endsWith("/log-set")).length;
    fireEvent.click(techniqueLog);
    await waitFor(() => expect(screen.getByText(/Enter actual reps and external load/)).toBeInTheDocument());
    expect(mock.mock.calls.filter(([input]) => String(input).endsWith("/log-set")).length).toBe(prior);
  }
});

test("runner renders AMRAP, requires actual reps and avoids the numeric baseline calculator", async () => {
  const workout = { session_id: "synthetic", workout_occurrence_id: "synthetic-occurrence", title: "Synthetic authored",
    date: new Date().toISOString().slice(0, 10), exercises: [exercise] };
  const fetchMock = vi.mocked(globalThis.fetch);
  fetchMock.mockImplementation(async (input) => {
    const url = String(input);
    const payload = url.includes("/workout/today") ? workout
      : url.includes("/soreness") ? [{ id: "example" }]
      : url.includes("/progress") ? { completed_total: 0, planned_total: 2, percent_complete: 0, exercises: [] }
      : {};
    return new Response(JSON.stringify(payload), { status: 200 });
  });
  render(<TodayPage />);
  fireEvent.click(screen.getByRole("button", { name: /Load today's workout/i }));
  await waitFor(() => expect(screen.getByRole("button", { name: /Synthetic Push-Up/i })).toBeInTheDocument());
  expect(screen.getByText("AMRAP reps")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /Synthetic Push-Up/i }));
  await waitFor(() => expect(screen.getByRole("dialog")).toBeInTheDocument());
  expect(screen.queryByText("Baseline Calculator")).not.toBeInTheDocument();
  expect(screen.getByText(/AMRAP reps · RPE ~8-9/)).toBeInTheDocument();
  expect(screen.getByLabelText("Reps")).toHaveValue(0);
  fireEvent.click(screen.getByRole("button", { name: "Complete Set" }));
  expect(fetchMock.mock.calls.some(([input]) => String(input).endsWith("/log-set"))).toBe(false);
});

test.each(["2", "2-3"])("runner retains %s authored warm-up sets and logs bodyweight without invented load", async (warmups) => {
  const bodyweight = structuredClone(exercise);
  bodyweight.load_semantics = "bodyweight";
  bodyweight.recommended_working_weight = 0;
  bodyweight.warmups = [];
  bodyweight.authored_prescription!.raw.warm_up_sets = warmups;
  bodyweight.warm_up_sets = warmups;
  const workout = { session_id: "synthetic", workout_occurrence_id: "synthetic-occurrence", title: "Synthetic authored",
    date: new Date().toISOString().slice(0, 10), exercises: [bodyweight] };
  const fetchMock = vi.mocked(globalThis.fetch);
  fetchMock.mockImplementation(async (input) => {
    const url = String(input);
    const payload = url.includes("/workout/today") ? workout
      : url.includes("/soreness") ? [{ id: "example" }]
      : url.includes("/progress") ? { completed_total: 0, planned_total: 2, percent_complete: 0, exercises: [] }
      : url.endsWith("/log-set") ? { id: "synthetic-receipt", reps: 12, weight: 0, next_working_weight: 0,
        planned_reps_min: null, planned_reps_max: null, planned_weight: 0, rep_delta: null, weight_delta: 0,
        guidance: "Follow the authored target", decision_trace: {} } : {};
    return new Response(JSON.stringify(payload), { status: 200 });
  });
  render(<TodayPage />);
  fireEvent.click(screen.getByRole("button", { name: /Load today's workout/i }));
  await waitFor(() => expect(screen.getByText("Bodyweight")).toBeInTheDocument());
  fireEvent.click(screen.getByRole("button", { name: /Synthetic Push-Up/i }));
  await waitFor(() => expect(screen.getByText(`${warmups} warm-up sets`)).toBeInTheDocument());
  expect(screen.queryByText("Baseline Calculator")).not.toBeInTheDocument();
  expect(screen.queryByText(/Based on your working weight/)).not.toBeInTheDocument();
  expect(screen.getByLabelText("Added load (lb), optional")).toHaveValue(0);
  fireEvent.change(screen.getByLabelText("Reps"), { target: { value: "12" } });
  fireEvent.click(screen.getByRole("button", { name: "Complete Set" }));
  await waitFor(() => expect(fetchMock.mock.calls.some(([input]) => String(input).endsWith("/log-set"))).toBe(true));
  const request = fetchMock.mock.calls.find(([input]) => String(input).endsWith("/log-set"));
  expect(JSON.parse(String(request![1]?.body))).toMatchObject({ reps: 12, weight: 0 });
});


test.each([0, 5])("day summary keeps bodyweight context for %s added kg and numeric source bounds", async (added) => {
  const bodyweight = { ...exercise, load_semantics: "bodyweight", recommended_working_weight: 0 };
  const workout = { session_id: "synthetic", workout_occurrence_id: "synthetic-occurrence", title: "Synthetic authored",
    date: new Date().toISOString().slice(0, 10), exercises: [bodyweight] };
  vi.mocked(globalThis.fetch).mockImplementation(async (input) => {
    const url = String(input);
    const payload = url.includes("/workout/today") ? workout
      : url.includes("/soreness") ? [{ id: "example" }]
      : url.includes("/progress") ? { completed_total: 2, planned_total: 2, percent_complete: 100, exercises: [] }
      : url.includes("/summary") ? { percent_complete: 100, overall_guidance: "Example", exercises: [{
        exercise_id: "synthetic-pushup", name: "Synthetic Push-Up", load_semantics: "bodyweight",
        planned_sets: 2, planned_reps_min: 8, planned_reps_max: 12, planned_weight: 0,
        performed_sets: 1, average_performed_reps: 10, average_performed_weight: added,
        next_working_weight: 0, guidance: "Example" }] } : {};
    return new Response(JSON.stringify(payload), { status: 200 });
  });
  render(<TodayPage />);
  fireEvent.click(screen.getByRole("button", { name: /Load today's workout/i }));
  await waitFor(() => expect(screen.getByText(/Planned: 2 sets · 8-12 reps · Bodyweight/)).toBeInTheDocument());
  expect(screen.getByText("Next: Bodyweight")).toBeInTheDocument();
  expect(screen.getByText(added ? /Bodyweight \+ 11 lb added/ : /Bodyweight \(no added load\)/)).toBeInTheDocument();
  expect(screen.queryByText(/0 lbs/)).not.toBeInTheDocument();
});


test("source N/A technique marker remains raw but does not become an execution cue", () => {
  const unavailable = structuredClone(exercise);
  unavailable.authored_prescription!.sets[1].intensity_technique = "N/A";
  expect(authoredSetTechnique(unavailable, 2)).toBeNull();
  expect(unavailable.authored_prescription!.sets[1].intensity_technique).toBe("N/A");
});
