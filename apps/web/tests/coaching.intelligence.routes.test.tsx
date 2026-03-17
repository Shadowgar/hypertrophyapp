import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import CheckinPage from "@/app/checkin/page";
import TodayPage from "@/app/today/page";

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
            selected_program_id: "pure_bodybuilding_phase_1_full_body",
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
            template_id: "pure_bodybuilding_phase_1_full_body",
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
    expect(screen.getByText(/Coaching Preview/i)).toBeInTheDocument();
  });

  fireEvent.click(screen.getByRole("button", { name: /Coaching Preview/i }));

  await waitFor(() => {
    expect(screen.getByRole("button", { name: /Generate coaching preview/i })).toBeInTheDocument();
  });

  fireEvent.click(screen.getByRole("button", { name: /Generate coaching preview/i }));

  await waitFor(() => {
    expect(screen.getAllByText(/Recommendation ID: rec_checkin_1/i).length).toBeGreaterThan(0);
  });
});

test("Today page shows load workout button and does not show coaching panel", async () => {
  // @ts-ignore
  globalThis.fetch.mockImplementation((input, init) => {
    const url = requestUrl(input);
    if (url.endsWith("/health")) {
      return Promise.resolve(new Response(JSON.stringify({ status: "ok", date: "2026-03-06" }), { status: 200 }));
    }
    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  render(<TodayPage />);

  await waitFor(() => {
    expect(screen.getByRole("button", { name: /Load today's workout/i })).toBeInTheDocument();
  });
  expect(screen.queryByText(/Coaching Intelligence/i)).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /Generate coaching preview/i })).not.toBeInTheDocument();
});
