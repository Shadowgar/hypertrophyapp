import React from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import HistoryPage from "@/app/history/page";

const emptyAnalytics = {
  window: { start_date: "2026-09-01", end_date: "2026-10-05", limit_weeks: 8, checkin_limit: 24 },
  checkins: [], adherence: { average_score: 0, average_pct: 0, latest_score: 0, trend_delta: 0, high_readiness_streak: 0 },
  bodyweight_trend: [], strength_trends: [], pr_highlights: [], body_measurement_trends: [], volume_heatmap: { max_volume: 0, weeks: [] },
};

function historyResponses(localToday: string, timezone: string, clockFails: () => boolean = () => false) {
  const calendarRequests: URL[] = [];
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const url = new URL(String(input), "http://history.test");
    if (url.pathname.endsWith("/plan/scheduling-context")) {
      if (clockFails()) return Response.json({ detail: "Scheduling clock unavailable" }, { status: 503 });
      // An unconfigured account retains the legacy UTC day. Configured accounts
      // return their persisted zone even when the caller supplies the UTC suggestion.
      if (timezone === "UTC") expect(url.searchParams.get("timezone")).toBe("UTC");
      return Response.json({ timezone, timezone_persisted: timezone !== "UTC", local_today: localToday,
        week_start: "2026-09-28", selected_dates: [], placement_revision: 0, plan: null });
    }
    if (url.pathname.endsWith("/history/calendar")) {
      calendarRequests.push(url);
      const start = url.searchParams.get("start_date")!;
      const end = url.searchParams.get("end_date")!;
      return Response.json({ start_date: start, end_date: end, active_days: 1, current_streak_days: 1, longest_streak_days: 1,
        days: start <= localToday && localToday <= end ? [{ date: localToday, weekday: localToday === "2026-10-05" ? 0 : 6,
          set_count: 1, exercise_count: 1, total_volume: 100, completed: true, program_ids: ["pure_bodybuilding_phase_1_full_body"],
          muscles: ["chest"], pr_count: 0, pr_exercises: [] }] : [] });
    }
    if (url.pathname.endsWith("/history/analytics")) return Response.json(emptyAnalytics);
    if (url.pathname.includes("/plan/intelligence/recommendations")) return Response.json({ entries: [] });
    return Response.json({});
  }));
  return calendarRequests;
}

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

test.each([
  { zone: "Pacific/Auckland", instant: "2026-10-04T11:30:00Z", today: "2026-10-05", monthStart: "2026-09-08", weekStart: "2026-09-29", previousStart: "2026-09-22", previousEnd: "2026-09-28" },
  { zone: "America/Los_Angeles", instant: "2026-10-05T02:30:00Z", today: "2026-10-04", monthStart: "2026-09-07", weekStart: "2026-09-28", previousStart: "2026-09-21", previousEnd: "2026-09-27" },
])("History anchors rolling windows to persisted $zone local day across the UTC week boundary", async ({ zone, instant, today, monthStart, weekStart, previousStart, previousEnd }) => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date(instant));
  historyResponses(today, zone);
  render(<HistoryPage />);

  expect(await screen.findByText(new RegExp(`Window ${monthStart} to ${today}`))).toBeInTheDocument();
  expect(screen.getByTitle(`${today}: 1 sets, 1 exercises, 100 volume, 0 PRs`)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Week" }));
  expect(await screen.findByText(new RegExp(`Window ${weekStart} to ${today}`))).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Previous Window" }));
  expect(await screen.findByText("No calendar history yet.")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Next Window" }));
  expect(await screen.findByText(new RegExp(`Window ${weekStart} to ${today}`))).toBeInTheDocument();

  // Query bounds also own the prior window when there is no performed history to render.
  const requests = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls.map(([input]) => new URL(String(input), "http://history.test"));
  expect(requests.some((url) => url.pathname.endsWith("/history/calendar")
    && url.searchParams.get("start_date") === previousStart && url.searchParams.get("end_date") === previousEnd)).toBe(true);
});

test("History retains the explicit UTC day for accounts without a persisted scheduling timezone", async () => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date("2026-10-04T11:30:00Z"));
  historyResponses("2026-10-04", "UTC");
  render(<HistoryPage />);
  expect(await screen.findByText(/Window 2026-09-07 to 2026-10-04/)).toBeInTheDocument();
});

test.each(["unavailable", "invalid"])("History sends no guessed calendar range when its server clock is %s and can retry", async (failure) => {
  let fails = true;
  const requests = historyResponses(failure === "invalid" ? "2026-02-30" : "2026-10-05", "Pacific/Auckland", () => failure === "unavailable" && fails);
  render(<HistoryPage />);
  expect(await screen.findByText("Unable to verify the current local date. Retry calendar load.")).toBeInTheDocument();
  expect(requests).toHaveLength(0);
  fails = false;
  // Replace the invalid response with a qualified date before retrying the same control.
  if (failure === "invalid") historyResponses("2026-10-05", "Pacific/Auckland");
  fireEvent.click(screen.getByRole("button", { name: "Retry Calendar Load" }));
  expect(await screen.findByText(/Window 2026-09-08 to 2026-10-05/)).toBeInTheDocument();
});
