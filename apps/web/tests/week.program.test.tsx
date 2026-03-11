import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import WeekPage from "@/app/week/page";

beforeEach(() => {
  // @ts-ignore
  globalThis.fetch = vi.fn();
});

test("Week page sends template_id when override selected", async () => {
  const programs = [{ id: "full_body_v1", name: "Full Body V1" }, { id: "upper_lower", name: "Upper/Lower" }];
  const generatedPlan = {
    program_template_id: "upper_lower",
    split: "upper_lower",
    phase: "maintenance",
    week_start: "2026-03-09",
    user: { name: "Test User", days_available: 4 },
    sessions: [
      {
        session_id: "upper_lower-1",
        title: "Upper 1",
        day_role: "full_body_1",
        date: "2026-03-10",
        exercises: [
          {
            id: "bench_press",
            name: "Bench Press",
            primary_exercise_id: "bench_press",
            sets: 4,
            rep_range: [6, 8],
            recommended_working_weight: 82.5,
            primary_muscles: ["chest", "triceps"],
            slot_role: "primary_compound",
          },
        ],
      },
      {
        session_id: "upper_lower-2",
        title: "Arms & Weak Points",
        day_role: "weak_point_arms",
        date: "2026-03-12",
        exercises: [
          {
            id: "bayesian_curl",
            name: "Bayesian Curl",
            primary_exercise_id: "bayesian_curl",
            sets: 3,
            rep_range: [10, 15],
            recommended_working_weight: 17.5,
            primary_muscles: ["biceps"],
            slot_role: "weak_point",
          },
        ],
      },
    ],
    missed_day_policy: "roll-forward-priority-lifts",
    weekly_volume_by_muscle: { chest: 8, quads: 8, triceps: 4, glutes: 4 },
    muscle_coverage: {
      minimum_sets_per_muscle: 6,
      covered_muscles: ["chest", "quads"],
      under_target_muscles: ["back"],
      untracked_exercise_count: 0,
    },
    mesocycle: {
      week_index: 3,
      trigger_weeks_base: 6,
      trigger_weeks_effective: 6,
      is_deload_week: false,
      deload_reason: "scheduled",
      authored_week_index: 1,
      authored_week_role: "adaptation",
      authored_sequence_complete: false,
      post_authored_behavior: "in_authored_sequence",
    },
    deload: {
      active: false,
      set_reduction_pct: 0,
      load_reduction_pct: 0,
      reason: "scheduled",
    },
    adaptive_review: {
      global_set_delta: 1,
      global_weight_scale: 0.95,
      weak_point_exercises: ["lat_pulldown"],
    },
    applied_frequency_adaptation: {
      template_id: "upper_lower",
      target_days: 4,
      duration_weeks: 2,
      weeks_remaining_before_apply: 2,
      weeks_remaining_after_apply: 1,
      weak_areas: ["back"],
    },
    template_selection_trace: {
      selected_template_id: "upper_lower",
      reason: "explicit_template_override",
      ordered_candidate_ids: ["upper_lower", "full_body_v1"],
    },
    generation_runtime_trace: {
      outcome: {
        effective_days_available: 4,
        prior_generated_weeks: 2,
        latest_adherence_score: 4,
        severe_soreness_count: 0,
      },
    },
  };

  // @ts-ignore
  globalThis.fetch.mockImplementation((input, init) => {
    const url = typeof input === "string" ? input : input.url;
    if (url.endsWith("/plan/programs")) {
      return Promise.resolve(new Response(JSON.stringify(programs), { status: 200 }));
    }
    if (url.endsWith("/weekly-review/status")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            today_is_sunday: false,
            review_required: false,
            current_week_start: "2026-03-10",
            week_start: "2026-03-03",
            previous_week_start: "2026-02-24",
            previous_week_end: "2026-03-02",
            existing_review_submitted: true,
            previous_week_summary: null,
          }),
          { status: 200 },
        ),
      );
    }
    if (url.endsWith("/plan/generate-week") && init?.method === "POST") {
      return Promise.resolve(new Response(JSON.stringify(generatedPlan), { status: 200 }));
    }
    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  render(<WeekPage />);

  await waitFor(() => expect(screen.getByLabelText(/Program override/i)).toBeInTheDocument());

  const select = screen.getByLabelText(/Program override/i);
  fireEvent.change(select, { target: { value: "upper_lower" } });

  const btn = screen.getByRole("button", { name: /Generate Week/i });
  fireEvent.click(btn);

  await waitFor(() => expect(screen.getByText(/Week Command Deck/i)).toBeInTheDocument());

  expect(screen.getAllByText(/Upper Lower/i).length).toBeGreaterThan(0);
  expect(screen.getByText(/Coverage Radar/i)).toBeInTheDocument();
  expect(screen.getByText(/Bring up back\./i)).toBeInTheDocument();
  expect(screen.getByText(/Authored block: Week 1 · Adaptation/i)).toBeInTheDocument();
  expect(screen.getByText(/Arms & Weak Points emphasis is scheduled this week\./i)).toBeInTheDocument();
  expect(screen.getByText(/Lead slot: Bench Press · 4 sets · 6-8 reps @ 82.5 kg/i)).toBeInTheDocument();
  expect(screen.getByText(/Session intent: Arms & Weak Points/i)).toBeInTheDocument();
  expect(screen.getByText(/Current context/i)).toBeInTheDocument();
  expect(screen.getByText(/Week 1 adaptation block/i)).toBeInTheDocument();
  expect(screen.getByText(/Adaptive Review Carryover/i)).toBeInTheDocument();
  expect(screen.getByText(/Frequency Adaptation Runtime/i)).toBeInTheDocument();

  await waitFor(() => {
    // @ts-ignore
    const calls = globalThis.fetch.mock.calls.filter((entry) => {
      const url = typeof entry[0] === "string" ? entry[0] : entry[0].url;
      return url.endsWith("/plan/generate-week");
    });
    expect(calls.length).toBe(1);
    const parsed = JSON.parse(calls[0][1].body);
    expect(parsed.template_id).toBe("upper_lower");
  });
});

test("Week page blocks generation when Sunday review is required", async () => {
  // @ts-ignore
  globalThis.fetch.mockImplementation((input) => {
    const url = typeof input === "string" ? input : input.url;
    if (url.endsWith("/plan/programs")) {
      return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }));
    }
    if (url.endsWith("/weekly-review/status")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            today_is_sunday: true,
            review_required: true,
            current_week_start: "2026-03-09",
            week_start: "2026-03-09",
            previous_week_start: "2026-03-02",
            previous_week_end: "2026-03-08",
            existing_review_submitted: false,
            previous_week_summary: null,
          }),
          { status: 200 },
        ),
      );
    }
    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  render(<WeekPage />);

  fireEvent.click(screen.getByRole("button", { name: /Generate Week/i }));

  await waitFor(() => {
    expect(screen.getByText(/Sunday review required\. Open Check-In, submit weekly review, then generate the next week\./i)).toBeInTheDocument();
  });
});
