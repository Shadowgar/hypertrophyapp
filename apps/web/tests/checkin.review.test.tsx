import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import CheckinPage from "@/app/checkin/page";

function resolveUrl(input: RequestInfo | URL): string {
  if (typeof input === "string") {
    return input;
  }
  if (input instanceof URL) {
    return input.toString();
  }
  return input.url;
}

beforeEach(() => {
  // @ts-ignore
  globalThis.fetch = vi.fn();
});

test("check-in page surfaces review command center and adaptive output", async () => {
  // @ts-ignore
  globalThis.fetch.mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
    const url = resolveUrl(input);

    if (url.includes("/weekly-review/status") && (init?.method === undefined || init.method === "GET")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            today_is_sunday: true,
            review_required: true,
            current_week_start: "2026-03-02",
            week_start: "2026-03-09",
            previous_week_start: "2026-03-02",
            previous_week_end: "2026-03-08",
            existing_review_submitted: false,
            previous_week_summary: {
              previous_week_start: "2026-03-02",
              previous_week_end: "2026-03-08",
              planned_sets_total: 18,
              completed_sets_total: 14,
              completion_pct: 78,
              faulty_exercise_count: 1,
              exercise_faults: [
                {
                  primary_exercise_id: "bench",
                  exercise_id: "bench",
                  name: "Bench Press",
                  planned_sets: 3,
                  completed_sets: 2,
                  completion_pct: 67,
                  target_reps_min: 8,
                  target_reps_max: 12,
                  average_performed_reps: 7,
                  target_weight: 100,
                  average_performed_weight: 97.5,
                  guidance: "below_target_reps_reduce_or_hold",
                  fault_score: 2,
                  fault_level: "high",
                  fault_reasons: ["below_target_reps"],
                },
              ],
            },
          }),
          { status: 200 },
        ),
      );
    }

    if (url.includes("/profile") && (init?.method === undefined || init.method === "GET")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            email: "athlete@example.com",
            name: "Athlete",
            age: 30,
            weight: 201,
            gender: "male",
            split_preference: "full_body",
            training_location: "gym",
            equipment_profile: ["barbell", "dumbbell"],
            weak_areas: ["chest"],
            onboarding_answers: {},
            days_available: 4,
            nutrition_phase: "maintenance",
            calories: 2800,
            protein: 220,
            fat: 70,
            carbs: 300,
            selected_program_id: "full_body_v1",
          }),
          { status: 200 },
        ),
      );
    }

    if (url.includes("/weekly-review") && init?.method === "POST") {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            status: "review_logged",
            week_start: "2026-03-09",
            previous_week_start: "2026-03-02",
            readiness_score: 78,
            global_guidance: "progressive_overload_ready",
            fault_count: 1,
            summary: {
              previous_week_start: "2026-03-02",
              previous_week_end: "2026-03-08",
              planned_sets_total: 18,
              completed_sets_total: 14,
              completion_pct: 78,
              faulty_exercise_count: 1,
              exercise_faults: [
                {
                  primary_exercise_id: "bench",
                  exercise_id: "bench",
                  name: "Bench Press",
                  planned_sets: 3,
                  completed_sets: 2,
                  completion_pct: 67,
                  target_reps_min: 8,
                  target_reps_max: 12,
                  average_performed_reps: 7,
                  target_weight: 100,
                  average_performed_weight: 97.5,
                  guidance: "below_target_reps_reduce_or_hold",
                  fault_score: 2,
                  fault_level: "high",
                  fault_reasons: ["below_target_reps"],
                },
              ],
            },
            adjustments: {
              global_set_delta: 1,
              global_weight_scale: 1.02,
              weak_point_exercises: ["bench"],
              exercise_overrides: [
                {
                  primary_exercise_id: "bench",
                  set_delta: 1,
                  weight_scale: 1.02,
                  rationale: "weak_point_bounded_extra_practice",
                },
              ],
            },
            decision_trace: { interpreter: "interpret_weekly_review_decision" },
          }),
          { status: 200 },
        ),
      );
    }

    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  render(<CheckinPage />);

  await waitFor(() => {
    expect(screen.getByText(/Review Command Center/i)).toBeInTheDocument();
  });

  expect(screen.getByText(/Sunday review required/i)).toBeInTheDocument();
  expect(screen.getByText(/Previous Week Lift Audit/i)).toBeInTheDocument();
  expect(screen.getByText(/Bench Press/i)).toBeInTheDocument();
  expect(screen.getByText(/High fault/i)).toBeInTheDocument();
  expect(screen.getByText(/Nutrition Snapshot/i)).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: /Save Weekly Review/i }));

  await waitFor(() => {
    expect(screen.getByText(/Readiness 78/i)).toBeInTheDocument();
  });

  expect(screen.getByText(/Primed to push/i)).toBeInTheDocument();
  expect(screen.getAllByText(/Progressive overload ready\./i).length).toBeGreaterThan(0);
  expect(screen.getAllByText(/Bench/i).length).toBeGreaterThan(0);
  expect(screen.getByText(/Adaptive Output/i)).toBeInTheDocument();
  expect(screen.getByText(/Load Scale/i)).toBeInTheDocument();
});