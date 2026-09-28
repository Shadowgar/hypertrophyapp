import React from "react";
import { beforeEach, expect, test, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import TodayPage from "@/app/today/page";
import { authoredRepLabel, authoredSetDetails, authoredSetRepRange } from "@/lib/authored-prescription";
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

beforeEach(() => { globalThis.fetch = vi.fn(); });

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
