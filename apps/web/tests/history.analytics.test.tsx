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

test("history page renders analytics dashboard payload", async () => {
  const payload = {
    window: { start_date: "2026-02-01", end_date: "2026-03-05", limit_weeks: 8, checkin_limit: 24 },
    checkins: [
      { week_start: "2026-02-17", body_weight: 82.5, adherence_score: 4, notes: null, created_at: "2026-02-17T12:00:00" },
      { week_start: "2026-02-24", body_weight: 81.8, adherence_score: 5, notes: null, created_at: "2026-02-24T12:00:00" },
    ],
    adherence: { average_score: 4.5, average_pct: 90, latest_score: 5, trend_delta: 1, high_readiness_streak: 2 },
    bodyweight_trend: [
      { week_start: "2026-02-17", body_weight: 82.5 },
      { week_start: "2026-02-24", body_weight: 81.8 },
    ],
    strength_trends: [
      {
        exercise_id: "bench",
        total_sets: 6,
        latest_weight: 90,
        pr_weight: 90,
        pr_delta: 10,
        points: [
          { week_start: "2026-02-17", max_weight: 80, avg_est_1rm: 101.33 },
          { week_start: "2026-02-24", max_weight: 90, avg_est_1rm: 111 },
        ],
      },
    ],
    pr_highlights: [
      { exercise_id: "bench", pr_weight: 90, previous_pr_weight: 80, pr_delta: 10 },
    ],
    body_measurement_trends: [
      {
        name: "waist",
        unit: "cm",
        latest_value: 82,
        delta: -2,
        points: [
          { measured_on: "2026-02-17", value: 84 },
          { measured_on: "2026-02-24", value: 82 },
        ],
      },
    ],
    volume_heatmap: {
      max_volume: 1200,
      weeks: [
        {
          week_start: "2026-02-24",
          days: [
            { day_index: 0, sets: 0, volume: 0 },
            { day_index: 1, sets: 3, volume: 1200 },
            { day_index: 2, sets: 2, volume: 800 },
            { day_index: 3, sets: 0, volume: 0 },
            { day_index: 4, sets: 0, volume: 0 },
            { day_index: 5, sets: 0, volume: 0 },
            { day_index: 6, sets: 0, volume: 0 },
          ],
        },
      ],
    },
  };

  const timelinePayload = {
    entries: [
      {
        recommendation_id: "rec_1",
        recommendation_type: "coach_preview",
        status: "previewed",
        template_id: "full_body_v1",
        current_phase: "accumulation",
        recommended_phase: "intensification",
        progression_action: "hold",
        rationale: "maintain_until_stable",
        focus_muscles: ["biceps", "shoulders"],
        created_at: "2026-03-05T10:00:00",
        applied_at: null,
      },
    ],
  };

  // @ts-ignore
  globalThis.fetch.mockImplementation((input: RequestInfo | URL) => {
    const url = resolveUrl(input);
    if (url.includes("/history/analytics")) {
      return Promise.resolve(new Response(JSON.stringify(payload), { status: 200 }));
    }
    if (url.includes("/plan/intelligence/recommendations")) {
      return Promise.resolve(new Response(JSON.stringify(timelinePayload), { status: 200 }));
    }
    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  render(<HistoryPage />);

  await waitFor(() => expect(screen.getByText(/90% recent average/i)).toBeInTheDocument());
  expect(screen.getByText(/High-Readiness Streak/i)).toBeInTheDocument();
  expect(screen.getAllByText(/bench/i).length).toBeGreaterThan(0);
  expect(screen.getByText(/\+10 kg/i)).toBeInTheDocument();
  expect(screen.getByText(/Volume Heat Map/i)).toBeInTheDocument();
  expect(screen.getByText(/Coaching Decision Timeline/i)).toBeInTheDocument();
  expect(screen.getByText(/Rationale: maintain_until_stable/i)).toBeInTheDocument();
  expect(screen.getByText(/Focus muscles: biceps, shoulders/i)).toBeInTheDocument();

  const button = screen.getByRole("button", { name: /Load Analytics Snapshot/i });
  fireEvent.click(button);
  await waitFor(() => expect(screen.getByText(/"pr_highlights"/i)).toBeInTheDocument());
});
