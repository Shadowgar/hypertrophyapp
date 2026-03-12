import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import CheckinPage from "@/app/checkin/page";
import TodayPage from "@/app/today/page";
import WeekPage from "@/app/week/page";

function requestUrl(input: RequestInfo | URL): string {
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

test("Week page coaching panel previews and auto-applies phase decision", async () => {
  const preview = {
    recommendation_id: "rec_week_1",
    template_id: "upper_lower",
    program_name: "Upper Lower",
    schedule: {
      from_days: 5,
      to_days: 3,
      kept_sessions: ["A", "B", "C"],
      dropped_sessions: ["D", "E"],
      added_sessions: [],
      risk_level: "medium",
      muscle_set_delta: { chest: -1 },
      tradeoffs: ["Higher density"],
    },
    progression: {
      action: "hold",
      load_scale: 1,
      set_delta: 0,
      reason: "maintain_until_stable",
      rationale: "Performance is stable but not yet strong enough to progress. Hold the current load and accumulate cleaner work.",
    },
    phase_transition: {
      next_phase: "accumulation",
      reason: "authored_sequence_complete",
      rationale: "The authored mesocycle is complete. Rotate to a fresh next step.",
      authored_sequence_complete: true,
      transition_pending: true,
      recommended_action: "rotate_program",
      post_authored_behavior: "hold_last_authored_week",
    },
    specialization: {
      focus_muscles: ["biceps"],
      focus_adjustments: { biceps: 2 },
      donor_adjustments: { quads: -1 },
      uncompensated_added_sets: 1,
    },
    media_warmups: {
      total_exercises: 10,
      video_linked_exercises: 2,
      video_coverage_pct: 20,
      sample_warmups: [],
    },
  };

  // @ts-ignore
  globalThis.fetch.mockImplementation((input, init) => {
    const url = requestUrl(input);
    if (url.endsWith("/profile")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            selected_program_id: "full_body_v1",
            days_available: 5,
          }),
          { status: 200 },
        ),
      );
    }
    if (url.endsWith("/plan/programs")) {
      return Promise.resolve(
        new Response(
          JSON.stringify([
            { id: "full_body_v1", name: "Full Body V1" },
            { id: "upper_lower", name: "Upper Lower" },
          ]),
          { status: 200 },
        ),
      );
    }
    if (url.endsWith("/plan/intelligence/coach-preview") && init?.method === "POST") {
      return Promise.resolve(new Response(JSON.stringify(preview), { status: 200 }));
    }
    if (url.endsWith("/plan/intelligence/apply-phase") && init?.method === "POST") {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            status: "applied",
            recommendation_id: "rec_week_1",
            applied_recommendation_id: "rec_week_applied_1",
            requires_confirmation: false,
            applied: true,
            next_phase: "accumulation",
            reason: "continue_accumulation",
            rationale: "Stay in accumulation. Current readiness and momentum do not justify a phase change yet.",
          }),
          { status: 200 },
        ),
      );
    }
    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  render(<WeekPage />);

  await waitFor(() => {
    expect(screen.getByRole("button", { name: /Generate coaching preview/i })).toBeInTheDocument();
  });

  fireEvent.click(screen.getByRole("button", { name: /Generate coaching preview/i }));
  await waitFor(() => {
    expect(screen.getAllByText(/Recommendation ID: rec_week_1/i).length).toBeGreaterThan(0);
  });
  expect(
    screen.getByText(/Performance is stable but not yet strong enough to progress\. Hold the current load and accumulate cleaner work\./i),
  ).toBeInTheDocument();
  expect(screen.getByText(/Program Transition/i)).toBeInTheDocument();
  expect(screen.queryByText(/Current block complete/i)).not.toBeInTheDocument();
  expect(screen.getByText(/Recommended action: rotate_program/i)).toBeInTheDocument();
  expect(screen.queryByText(/Rotate program/i)).not.toBeInTheDocument();
  expect(screen.getByText(/Post-authored behavior: hold_last_authored_week/i)).toBeInTheDocument();
  expect(screen.getByText(/hold_last_authored_week/i)).toBeInTheDocument();
  expect(screen.getByText(/The authored mesocycle is complete\. Rotate to a fresh next step\./i)).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: /Apply phase decision/i }));
  await waitFor(() => {
    expect(screen.getByText(/Phase: applied/i)).toBeInTheDocument();
  });
  expect(screen.queryByText(/continue_accumulation/i)).not.toBeInTheDocument();

  // @ts-ignore
  const fetchCalls = globalThis.fetch.mock.calls as Array<[RequestInfo | URL, RequestInit | undefined]>;
  const applyPhaseCall = fetchCalls.find(([input, init]) => {
    const url = requestUrl(input);
    return url.endsWith("/plan/intelligence/apply-phase") && init?.method === "POST";
  });
  expect(applyPhaseCall).toBeDefined();
  if (!applyPhaseCall) {
    throw new Error("Expected apply-phase request call");
  }
  const applyBody = applyPhaseCall[1]?.body;
  const parsed = typeof applyBody === "string" ? JSON.parse(applyBody) : {};
  expect(parsed).toMatchObject({ recommendation_id: "rec_week_1" });
});

test("Check-in page renders coaching panel and preview result", async () => {
  // @ts-ignore
  globalThis.fetch.mockImplementation((input, init) => {
    const url = requestUrl(input);
    if (url.endsWith("/weekly-review/status")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            today_is_sunday: false,
            review_required: false,
            week_start: "2026-03-02",
            previous_week_start: "2026-02-23",
            previous_week_end: "2026-03-01",
          }),
          { status: 200 },
        ),
      );
    }
    if (url.endsWith("/profile")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            selected_program_id: "full_body_v1",
            days_available: 5,
            weight: 84,
            calories: 2700,
            protein: 180,
            fat: 70,
            carbs: 300,
          }),
          { status: 200 },
        ),
      );
    }
    if (url.endsWith("/plan/intelligence/coach-preview") && init?.method === "POST") {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            recommendation_id: "rec_checkin_1",
            template_id: "full_body_v1",
            program_name: "Full Body V1",
            schedule: {
              from_days: 5,
              to_days: 3,
              kept_sessions: ["A", "B", "C"],
              dropped_sessions: ["D", "E"],
              added_sessions: [],
              risk_level: "medium",
              muscle_set_delta: {},
              tradeoffs: [],
            },
            progression: {
              action: "hold",
              load_scale: 1,
              set_delta: 0,
              reason: "maintain_until_stable",
            },
            phase_transition: {
              next_phase: "accumulation",
              reason: "continue_accumulation",
            },
            specialization: {
              focus_muscles: [],
              focus_adjustments: {},
              donor_adjustments: {},
              uncompensated_added_sets: 0,
            },
            media_warmups: {
              total_exercises: 10,
              video_linked_exercises: 2,
              video_coverage_pct: 20,
              sample_warmups: [],
            },
          }),
          { status: 200 },
        ),
      );
    }
    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  render(<CheckinPage />);

  await waitFor(() => {
    expect(screen.getByText(/Coaching Intelligence/i)).toBeInTheDocument();
  });

  fireEvent.click(screen.getByRole("button", { name: /Generate coaching preview/i }));

  await waitFor(() => {
    expect(screen.getAllByText(/Recommendation ID: rec_checkin_1/i).length).toBeGreaterThan(0);
  });
});

test("Today page renders coaching panel and preview result", async () => {
  // @ts-ignore
  globalThis.fetch.mockImplementation((input, init) => {
    const url = requestUrl(input);
    if (url.endsWith("/health")) {
      return Promise.resolve(new Response(JSON.stringify({ status: "ok", date: "2026-03-06" }), { status: 200 }));
    }
    if (url.endsWith("/workout/today")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            session_id: "adaptive_full_body_gold_v0_1-day5",
            title: "Arms & Weak Points",
            date: "2026-03-12",
            resume: false,
            day_role: "weak_point_arms",
            mesocycle: {
              week_index: 1,
              trigger_weeks_base: 6,
              trigger_weeks_effective: 6,
              is_deload_week: false,
              deload_reason: "none",
              authored_week_index: 1,
              authored_week_role: "adaptation",
              authored_sequence_complete: false,
              post_authored_behavior: "in_authored_sequence",
            },
            deload: {
              active: false,
              set_reduction_pct: 0,
              load_reduction_pct: 0,
              reason: "none",
            },
            exercises: [
              {
                id: "bayesian_curl",
                primary_exercise_id: "bayesian_curl",
                name: "Bayesian Curl",
                sets: 3,
                rep_range: [10, 15],
                recommended_working_weight: 17.5,
                slot_role: "weak_point",
                substitution_candidates: [],
              },
            ],
          }),
          { status: 200 },
        ),
      );
    }
    if (url.includes("/soreness")) {
      return Promise.resolve(new Response(JSON.stringify([{ id: "s1", entry_date: "2026-03-03" }]), { status: 200 }));
    }
    if (url.endsWith("/profile")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            selected_program_id: "full_body_v1",
            days_available: 5,
          }),
          { status: 200 },
        ),
      );
    }
    if (url.endsWith("/plan/intelligence/coach-preview") && init?.method === "POST") {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            recommendation_id: "rec_today_1",
            template_id: "full_body_v1",
            program_name: "Full Body V1",
            schedule: {
              from_days: 5,
              to_days: 3,
              kept_sessions: ["A", "B", "C"],
              dropped_sessions: ["D", "E"],
              added_sessions: [],
              risk_level: "medium",
              muscle_set_delta: {},
              tradeoffs: [],
            },
            progression: {
              action: "hold",
              load_scale: 1,
              set_delta: 0,
              reason: "maintain_until_stable",
            },
            phase_transition: {
              next_phase: "accumulation",
              reason: "continue_accumulation",
            },
            specialization: {
              focus_muscles: [],
              focus_adjustments: {},
              donor_adjustments: {},
              uncompensated_added_sets: 0,
            },
            media_warmups: {
              total_exercises: 10,
              video_linked_exercises: 2,
              video_coverage_pct: 20,
              sample_warmups: [],
            },
          }),
          { status: 200 },
        ),
      );
    }
    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  render(<TodayPage />);

  await waitFor(() => {
    expect(screen.getByText(/Coaching Intelligence/i)).toBeInTheDocument();
  });

  fireEvent.click(screen.getByRole("button", { name: /Load Today Workout/i }));

  await waitFor(() => {
    expect(screen.getByText(/Current context/i)).toBeInTheDocument();
  });
  expect(screen.getByText(/Today follows Arms & Weak Points/i)).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: /Generate coaching preview/i }));

  await waitFor(() => {
    expect(screen.getAllByText(/Recommendation ID: rec_today_1/i).length).toBeGreaterThan(0);
  });
});
