import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import HistoryPage from "@/app/history/page";

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

test("history calendar lets user inspect prior day exercises", async () => {
  const analyticsPayload = {
    window: { start_date: "2026-02-01", end_date: "2026-03-05", limit_weeks: 8, checkin_limit: 24 },
    checkins: [],
    adherence: { average_score: 0, average_pct: 0, latest_score: 0, trend_delta: 0, high_readiness_streak: 0 },
    bodyweight_trend: [],
    strength_trends: [],
    pr_highlights: [],
    body_measurement_trends: [],
    volume_heatmap: { max_volume: 0, weeks: [] },
  };

  const timelinePayload = { entries: [] };
  const calendarPayload = {
    start_date: "2026-03-01",
    end_date: "2026-03-04",
    active_days: 2,
    current_streak_days: 0,
    longest_streak_days: 1,
    days: [
      { date: "2026-03-01", weekday: 6, set_count: 0, exercise_count: 0, total_volume: 0, completed: false, program_ids: [], muscles: [], pr_count: 0, pr_exercises: [] },
      { date: "2026-03-02", weekday: 0, set_count: 2, exercise_count: 1, total_volume: 1200, completed: true, program_ids: ["pure_bodybuilding_phase_1_full_body"], muscles: ["chest"], pr_count: 1, pr_exercises: ["bench_press"] },
      { date: "2026-03-03", weekday: 1, set_count: 1, exercise_count: 1, total_volume: 700, completed: true, program_ids: ["pure_bodybuilding_phase_1_full_body"], muscles: ["hamstrings"], pr_count: 0, pr_exercises: [] },
      { date: "2026-03-04", weekday: 2, set_count: 0, exercise_count: 0, total_volume: 0, completed: false, program_ids: ["pure_bodybuilding_phase_1_full_body"], muscles: ["back"], pr_count: 0, pr_exercises: [] },
    ],
  };

  const dayDetailPayload = {
    date: "2026-03-02",
    totals: { set_count: 2, planned_set_count: 3, set_delta: -1, exercise_count: 1, total_volume: 1200 },
    workouts: [
      {
        workout_id: "workout_a",
        total_sets: 2,
        planned_sets_total: 3,
        set_delta: -1,
        total_volume: 1200,
        exercises: [
          {
            primary_exercise_id: "bench_press",
            exercise_id: "bench_press",
            planned_name: "Bench Press",
            primary_muscles: ["chest"],
            total_sets: 2,
            planned_sets: 3,
            set_delta: -1,
            total_volume: 1200,
            sets: [
              { set_index: 1, reps: 8, weight: 80, rpe: null, created_at: "2026-03-02T09:00:00" },
              { set_index: 2, reps: 7, weight: 82.5, rpe: null, created_at: "2026-03-02T09:05:00" },
            ],
          },
        ],
      },
    ],
  };

  // @ts-ignore
  globalThis.fetch.mockImplementation((input: RequestInfo | URL) => {
    const url = resolveUrl(input);
    if (url.includes("/history/analytics")) {
      return Promise.resolve(new Response(JSON.stringify(analyticsPayload), { status: 200 }));
    }
    if (url.includes("/plan/intelligence/recommendations")) {
      return Promise.resolve(new Response(JSON.stringify(timelinePayload), { status: 200 }));
    }
    if (url.includes("/history/calendar")) {
      return Promise.resolve(new Response(JSON.stringify(calendarPayload), { status: 200 }));
    }
    if (url.includes("/history/day/2026-03-02")) {
      return Promise.resolve(new Response(JSON.stringify(dayDetailPayload), { status: 200 }));
    }
    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  render(<HistoryPage />);

  await waitFor(() => {
    expect(screen.getByText(/Training Calendar/i)).toBeInTheDocument();
  });

  fireEvent.click(screen.getByTitle(/2026-03-02: 2 sets/i));

  await waitFor(() => {
    expect(screen.getByText(/Selected Day Detail/i)).toBeInTheDocument();
  });

  expect(screen.getByText(/Workout workout_a/i)).toBeInTheDocument();
  expect(screen.getAllByText(/Bench Press/i).length).toBeGreaterThan(0);
  expect(screen.getByText(/PR 1/i)).toBeInTheDocument();
  expect(screen.getAllByText(/2 sets \/ 3 planned \(-1\)/i).length).toBeGreaterThan(0);
  expect(screen.getByText(/#1 8x80 · #2 7x82.5/i)).toBeInTheDocument();
});

test("history calendar supports view toggles, filters, and previous weekday jump", async () => {
  const analyticsPayload = {
    window: { start_date: "2026-02-01", end_date: "2026-03-05", limit_weeks: 8, checkin_limit: 24 },
    checkins: [],
    adherence: { average_score: 0, average_pct: 0, latest_score: 0, trend_delta: 0, high_readiness_streak: 0 },
    bodyweight_trend: [],
    strength_trends: [],
    pr_highlights: [],
    body_measurement_trends: [],
    volume_heatmap: { max_volume: 0, weeks: [] },
  };
  const timelinePayload = { entries: [] };
  const calendarPayload = {
    start_date: "2026-02-24",
    end_date: "2026-03-03",
    active_days: 4,
    current_streak_days: 1,
    longest_streak_days: 2,
    days: [
      { date: "2026-02-24", weekday: 1, set_count: 2, exercise_count: 1, total_volume: 900, completed: true, program_ids: ["upper_lower_v1"], muscles: ["back"], pr_count: 1, pr_exercises: ["barbell_row"] },
      { date: "2026-02-25", weekday: 2, set_count: 0, exercise_count: 0, total_volume: 0, completed: false, program_ids: ["upper_lower_v1"], muscles: ["back"], pr_count: 0, pr_exercises: [] },
      { date: "2026-02-26", weekday: 3, set_count: 1, exercise_count: 1, total_volume: 600, completed: true, program_ids: ["pure_bodybuilding_phase_1_full_body"], muscles: ["chest"], pr_count: 1, pr_exercises: ["bench_press"] },
      { date: "2026-02-27", weekday: 4, set_count: 0, exercise_count: 0, total_volume: 0, completed: false, program_ids: ["pure_bodybuilding_phase_1_full_body"], muscles: ["chest"], pr_count: 0, pr_exercises: [] },
      { date: "2026-02-28", weekday: 5, set_count: 0, exercise_count: 0, total_volume: 0, completed: false, program_ids: ["pure_bodybuilding_phase_1_full_body"], muscles: ["hamstrings"], pr_count: 0, pr_exercises: [] },
      { date: "2026-03-01", weekday: 6, set_count: 1, exercise_count: 1, total_volume: 500, completed: true, program_ids: ["pure_bodybuilding_phase_1_full_body"], muscles: ["hamstrings"], pr_count: 0, pr_exercises: [] },
      { date: "2026-03-02", weekday: 0, set_count: 0, exercise_count: 0, total_volume: 0, completed: false, program_ids: ["pure_bodybuilding_phase_1_full_body"], muscles: ["hamstrings"], pr_count: 0, pr_exercises: [] },
      { date: "2026-03-03", weekday: 1, set_count: 3, exercise_count: 1, total_volume: 1300, completed: true, program_ids: ["upper_lower_v1"], muscles: ["back"], pr_count: 1, pr_exercises: ["barbell_row"] },
    ],
  };

  const dayCurrent = {
    date: "2026-03-03",
    totals: { set_count: 3, planned_set_count: 3, set_delta: 0, exercise_count: 1, total_volume: 1300 },
    workouts: [
      {
        workout_id: "workout_current",
        program_id: "upper_lower_v1",
        total_sets: 3,
        planned_sets_total: 3,
        set_delta: 0,
        total_volume: 1300,
        exercises: [
          {
            primary_exercise_id: "barbell_row",
            exercise_id: "barbell_row",
            planned_name: "Barbell Row",
            primary_muscles: ["back"],
            total_sets: 3,
            planned_sets: 3,
            set_delta: 0,
            total_volume: 1300,
            sets: [
              { set_index: 1, reps: 8, weight: 80, rpe: null, created_at: "2026-03-03T09:00:00" },
              { set_index: 2, reps: 8, weight: 82.5, rpe: null, created_at: "2026-03-03T09:05:00" },
              { set_index: 3, reps: 7, weight: 85, rpe: null, created_at: "2026-03-03T09:10:00" },
            ],
          },
        ],
      },
    ],
  };

  const dayPrevious = {
    date: "2026-02-24",
    totals: { set_count: 2, planned_set_count: 2, set_delta: 0, exercise_count: 1, total_volume: 900 },
    workouts: [
      {
        workout_id: "workout_prev",
        program_id: "upper_lower_v1",
        total_sets: 2,
        planned_sets_total: 2,
        set_delta: 0,
        total_volume: 900,
        exercises: [
          {
            primary_exercise_id: "barbell_row",
            exercise_id: "barbell_row",
            planned_name: "Barbell Row",
            primary_muscles: ["back"],
            total_sets: 2,
            planned_sets: 2,
            set_delta: 0,
            total_volume: 900,
            sets: [
              { set_index: 1, reps: 8, weight: 75, rpe: null, created_at: "2026-02-24T09:00:00" },
              { set_index: 2, reps: 8, weight: 77.5, rpe: null, created_at: "2026-02-24T09:05:00" },
            ],
          },
        ],
      },
    ],
  };

  // @ts-ignore
  globalThis.fetch.mockImplementation((input: RequestInfo | URL) => {
    const url = resolveUrl(input);
    if (url.includes("/history/analytics")) {
      return Promise.resolve(new Response(JSON.stringify(analyticsPayload), { status: 200 }));
    }
    if (url.includes("/plan/intelligence/recommendations")) {
      return Promise.resolve(new Response(JSON.stringify(timelinePayload), { status: 200 }));
    }
    if (url.includes("/history/calendar")) {
      return Promise.resolve(new Response(JSON.stringify(calendarPayload), { status: 200 }));
    }
    if (url.includes("/history/day/2026-03-03")) {
      return Promise.resolve(new Response(JSON.stringify(dayCurrent), { status: 200 }));
    }
    if (url.includes("/history/day/2026-02-24")) {
      return Promise.resolve(new Response(JSON.stringify(dayPrevious), { status: 200 }));
    }
    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  render(<HistoryPage />);

  await waitFor(() => {
    expect(screen.getByRole("button", { name: /^Month$/i })).toBeInTheDocument();
  });

  fireEvent.click(screen.getByRole("button", { name: /^Week$/i }));

  await waitFor(() => {
    expect(screen.getByLabelText(/program filter/i)).toBeInTheDocument();
  });

  const countCalendarCalls = () => {
    // @ts-ignore
    const calls = globalThis.fetch.mock.calls as Array<[RequestInfo | URL, RequestInit | undefined]>;
    return calls.filter(([input]) => resolveUrl(input).includes("/history/calendar")).length;
  };

  const initialCalendarCalls = countCalendarCalls();
  fireEvent.click(screen.getByRole("button", { name: /previous window/i }));
  await waitFor(() => {
    expect(countCalendarCalls()).toBeGreaterThan(initialCalendarCalls);
  });

  fireEvent.change(screen.getByLabelText(/completion filter/i), { target: { value: "missed" } });
  expect(screen.queryByTitle(/2026-03-03: 3 sets/i)).not.toBeInTheDocument();

  fireEvent.change(screen.getByLabelText(/completion filter/i), { target: { value: "all" } });
  fireEvent.change(screen.getByLabelText(/program filter/i), { target: { value: "upper_lower_v1" } });
  expect(screen.getByTitle(/2026-03-03: 3 sets/i)).toBeInTheDocument();
  expect(screen.queryByTitle(/2026-03-01: 1 sets/i)).not.toBeInTheDocument();

  fireEvent.change(screen.getByLabelText(/muscle filter/i), { target: { value: "back" } });
  expect(screen.getByTitle(/2026-02-24: 2 sets/i)).toBeInTheDocument();

  fireEvent.click(screen.getByTitle(/2026-03-03: 3 sets/i));

  await waitFor(() => {
    expect(screen.getByText(/Workout workout_current/i)).toBeInTheDocument();
  });

  expect(screen.getByText(/Same-Weekday Comparison/i)).toBeInTheDocument();
  expect(screen.getByText(/Sets \+1/i)).toBeInTheDocument();
  expect(screen.getByText(/Volume \+400/i)).toBeInTheDocument();
  expect(screen.getByText(/PR Days \+0/i)).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: /jump to previous same weekday/i }));

  await waitFor(() => {
    expect(screen.getByText(/Workout workout_prev/i)).toBeInTheDocument();
  });
});

test("history page summarizes progression signals and coach queue", async () => {
  const analyticsPayload = {
    window: { start_date: "2026-02-01", end_date: "2026-03-05", limit_weeks: 8, checkin_limit: 24 },
    checkins: [
      { week_start: "2026-02-17", body_weight: 82, adherence_score: 4, notes: null, created_at: "2026-02-17T08:00:00" },
      { week_start: "2026-02-24", body_weight: 83.5, adherence_score: 5, notes: null, created_at: "2026-02-24T08:00:00" },
    ],
    adherence: { average_score: 4.5, average_pct: 90, latest_score: 5, trend_delta: 1, high_readiness_streak: 2 },
    bodyweight_trend: [
      { week_start: "2026-02-17", body_weight: 82 },
      { week_start: "2026-02-24", body_weight: 83.5 },
    ],
    strength_trends: [
      {
        exercise_id: "bench_press",
        total_sets: 8,
        latest_weight: 102.5,
        pr_weight: 105,
        pr_delta: 5,
        points: [
          { week_start: "2026-02-17", max_weight: 100, avg_est_1rm: 120 },
          { week_start: "2026-02-24", max_weight: 105, avg_est_1rm: 125 },
        ],
      },
    ],
    pr_highlights: [
      { exercise_id: "bench_press", pr_weight: 105, previous_pr_weight: 100, pr_delta: 5 },
    ],
    body_measurement_trends: [],
    volume_heatmap: { max_volume: 0, weeks: [] },
  };
  const timelinePayload = {
    entries: [
      {
        recommendation_id: "rec_1",
        recommendation_type: "coach_preview",
        status: "pending",
        template_id: "pure_bodybuilding_phase_1_full_body",
        current_phase: "accumulation",
        recommended_phase: "intensification",
        progression_action: "progress",
        rationale: "Momentum is high.",
        focus_muscles: ["chest"],
        created_at: "2026-03-01T09:00:00",
        applied_at: null,
      },
    ],
  };
  const calendarPayload = {
    start_date: "2026-03-01",
    end_date: "2026-03-04",
    active_days: 0,
    current_streak_days: 0,
    longest_streak_days: 0,
    days: [],
  };

  // @ts-ignore
  globalThis.fetch.mockImplementation((input: RequestInfo | URL) => {
    const url = resolveUrl(input);
    if (url.includes("/history/analytics")) {
      return Promise.resolve(new Response(JSON.stringify(analyticsPayload), { status: 200 }));
    }
    if (url.includes("/plan/intelligence/recommendations")) {
      return Promise.resolve(new Response(JSON.stringify(timelinePayload), { status: 200 }));
    }
    if (url.includes("/history/calendar")) {
      return Promise.resolve(new Response(JSON.stringify(calendarPayload), { status: 200 }));
    }
    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  render(<HistoryPage />);

  await waitFor(() => {
    expect(screen.getByText(/Progression Brief/i)).toBeInTheDocument();
  });

  expect(screen.getByText(/Latest rationale: Momentum is high\./i)).toBeInTheDocument();
  expect(screen.getAllByText(/bench_press/i).length).toBeGreaterThan(0);
  expect(screen.getAllByText(/PR 105 kg \(\+5\)/i).length).toBeGreaterThan(0);
  expect(screen.getAllByText(/\+1.5 kg/i).length).toBeGreaterThan(0);
  expect(screen.getByText(/Coach Queue/i)).toBeInTheDocument();
  expect(screen.getAllByText(/1 pending/i).length).toBeGreaterThan(0);
  expect(screen.getByText(/Latest type: coach_preview/i)).toBeInTheDocument();
});

test("history calendar shows planned detail on missed day with zero logged sets", async () => {
  const analyticsPayload = {
    window: { start_date: "2026-02-01", end_date: "2026-03-05", limit_weeks: 8, checkin_limit: 24 },
    checkins: [],
    adherence: { average_score: 0, average_pct: 0, latest_score: 0, trend_delta: 0, high_readiness_streak: 0 },
    bodyweight_trend: [],
    strength_trends: [],
    pr_highlights: [],
    body_measurement_trends: [],
    volume_heatmap: { max_volume: 0, weeks: [] },
  };
  const timelinePayload = { entries: [] };
  const calendarPayload = {
    start_date: "2026-03-01",
    end_date: "2026-03-03",
    active_days: 0,
    current_streak_days: 0,
    longest_streak_days: 0,
    days: [
      { date: "2026-03-01", weekday: 6, set_count: 0, exercise_count: 0, total_volume: 0, completed: false, program_ids: ["pure_bodybuilding_phase_1_full_body"], muscles: ["chest"], pr_count: 0, pr_exercises: [] },
      { date: "2026-03-02", weekday: 0, set_count: 0, exercise_count: 0, total_volume: 0, completed: false, program_ids: ["pure_bodybuilding_phase_1_full_body"], muscles: ["chest"], pr_count: 0, pr_exercises: [] },
      { date: "2026-03-03", weekday: 1, set_count: 0, exercise_count: 0, total_volume: 0, completed: false, program_ids: ["pure_bodybuilding_phase_1_full_body"], muscles: ["chest"], pr_count: 0, pr_exercises: [] },
    ],
  };

  const missedDayDetail = {
    date: "2026-03-02",
    totals: { set_count: 0, planned_set_count: 2, set_delta: -2, exercise_count: 1, total_volume: 0 },
    workouts: [
      {
        workout_id: "planned_only_workout",
        program_id: "pure_bodybuilding_phase_1_full_body",
        total_sets: 0,
        planned_sets_total: 2,
        set_delta: -2,
        total_volume: 0,
        exercises: [
          {
            primary_exercise_id: "bench_press",
            exercise_id: "bench_press",
            planned_name: "Bench Press",
            primary_muscles: ["chest"],
            total_sets: 0,
            planned_sets: 2,
            set_delta: -2,
            total_volume: 0,
            sets: [],
          },
        ],
      },
    ],
  };

  // @ts-ignore
  globalThis.fetch.mockImplementation((input: RequestInfo | URL) => {
    const url = resolveUrl(input);
    if (url.includes("/history/analytics")) {
      return Promise.resolve(new Response(JSON.stringify(analyticsPayload), { status: 200 }));
    }
    if (url.includes("/plan/intelligence/recommendations")) {
      return Promise.resolve(new Response(JSON.stringify(timelinePayload), { status: 200 }));
    }
    if (url.includes("/history/calendar")) {
      return Promise.resolve(new Response(JSON.stringify(calendarPayload), { status: 200 }));
    }
    if (url.includes("/history/day/2026-03-02")) {
      return Promise.resolve(new Response(JSON.stringify(missedDayDetail), { status: 200 }));
    }
    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  render(<HistoryPage />);

  await waitFor(() => {
    expect(screen.getByText(/Training Calendar/i)).toBeInTheDocument();
  });

  fireEvent.click(screen.getByTitle(/2026-03-02: 0 sets/i));

  await waitFor(() => {
    expect(screen.getByText(/Workout planned_only_workout/i)).toBeInTheDocument();
  });

  expect(screen.getByText(/No logged sets on this day\. Planned sets: 2\./i)).toBeInTheDocument();
  expect(screen.getAllByText(/0 sets \/ 2 planned \(-2\)/i).length).toBeGreaterThan(0);
});
