import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import HomePage from "@/app/page";

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
  localStorage.clear();
  // @ts-ignore
  globalThis.fetch = vi.fn();
});

test("home page shows guest dashboard copy without a token", () => {
  render(<HomePage />);

  expect(screen.getByText(/Guest Preview/i)).toBeInTheDocument();
  expect(screen.getByText(/Sign in to load your training dashboard/i)).toBeInTheDocument();
  expect(screen.getByText(/How the app coaches/i)).toBeInTheDocument();
  expect(screen.getByText(/Finish onboarding to generate a personalized hypertrophy week/i)).toBeInTheDocument();
  expect(globalThis.fetch).not.toHaveBeenCalled();
});

test("home page loads authenticated dashboard metrics", async () => {
  localStorage.setItem("hypertrophy_token", "test-token");

  // @ts-ignore
  globalThis.fetch.mockImplementation((input: RequestInfo | URL) => {
    const url = resolveUrl(input);

    if (url.endsWith("/profile")) {
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

    if (url.endsWith("/workout/today")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            session_id: "full_body_v1-day1",
            title: "Full Body A",
            date: "2026-03-07",
            resume: false,
            mesocycle: {
              week_index: 4,
              trigger_weeks_base: 6,
              trigger_weeks_effective: 6,
              is_deload_week: false,
              deload_reason: "none",
            },
            deload: {
              active: false,
              set_reduction_pct: 35,
              load_reduction_pct: 10,
              reason: "none",
            },
            exercises: [
              {
                id: "bench_press",
                name: "Bench Press",
                sets: 3,
                rep_range: [8, 12],
                recommended_working_weight: 225,
              },
              {
                id: "row",
                name: "Chest Supported Row",
                sets: 3,
                rep_range: [8, 12],
                recommended_working_weight: 180,
              },
            ],
          }),
          { status: 200 },
        ),
      );
    }

    if (url.includes("/history/analytics")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            window: {
              start_date: "2026-01-10",
              end_date: "2026-03-07",
              limit_weeks: 8,
              checkin_limit: 24,
            },
            checkins: [],
            adherence: {
              average_score: 4.2,
              average_pct: 84,
              latest_score: 5,
              trend_delta: 0.4,
              high_readiness_streak: 3,
            },
            bodyweight_trend: [
              { week_start: "2026-03-01", body_weight: 201 },
            ],
            strength_trends: [
              {
                exercise_id: "bench_press",
                total_sets: 12,
                latest_weight: 250,
                pr_weight: 250,
                pr_delta: 5,
                points: [
                  { week_start: "2026-02-14", max_weight: 245, avg_est_1rm: 275 },
                  { week_start: "2026-02-21", max_weight: 250, avg_est_1rm: 280 },
                ],
              },
            ],
            pr_highlights: [
              { exercise_id: "bench_press", pr_weight: 280, previous_pr_weight: 275, pr_delta: 5 },
              { exercise_id: "row", pr_weight: 225, previous_pr_weight: 220, pr_delta: 5 },
            ],
            body_measurement_trends: [],
            volume_heatmap: { muscles: [] },
          }),
          { status: 200 },
        ),
      );
    }

    if (url.endsWith("/weekly-review/status")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            today_is_sunday: true,
            review_required: false,
            current_week_start: "2026-03-02",
            week_start: "2026-03-02",
            previous_week_start: "2026-02-23",
            previous_week_end: "2026-03-01",
            existing_review_submitted: true,
            previous_week_summary: null,
          }),
          { status: 200 },
        ),
      );
    }

    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  render(<HomePage />);

  await waitFor(() => expect(screen.getByText(/Ready To Train/i)).toBeInTheDocument());
  expect(screen.getAllByText(/Full Body A/i).length).toBeGreaterThan(0);
  expect(screen.getByText(/Week 4/i)).toBeInTheDocument();
  expect(screen.getByText(/201 lb/i)).toBeInTheDocument();
  expect(screen.getAllByText(/2 PR highlights/i).length).toBeGreaterThan(0);
  expect(screen.getAllByText(/4 training days/i).length).toBeGreaterThan(0);
  expect(screen.getByText(/Coach Brief/i)).toBeInTheDocument();
  expect(screen.getByText(/Actionable/i)).toBeInTheDocument();
  expect(screen.getByText(/Start with Bench Press: 3 x 8-12 @ 225 kg/i)).toBeInTheDocument();
  expect(screen.getByText(/Session Blueprint/i)).toBeInTheDocument();
  expect(screen.getByText(/Weak Areas/i)).toBeInTheDocument();
  expect(screen.getAllByText(/Chest/i).length).toBeGreaterThan(0);
  expect(screen.getByText(/Momentum Radar/i)).toBeInTheDocument();
  expect(screen.getAllByText(/Bench Press/i).length).toBeGreaterThan(0);
});