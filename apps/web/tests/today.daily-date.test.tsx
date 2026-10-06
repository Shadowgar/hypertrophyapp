import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import TodayPage from "@/app/today/page";

afterEach(() => { cleanup(); vi.useRealTimers(); localStorage.clear(); });

function dailyFixture(instant: string, timezone: string, initialDay: string) {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date(instant));
  let day = initialDay;
  const sorenessDates: string[] = [];
  const saves: string[] = [];
  const workouts: string[] = [];
  globalThis.fetch = vi.fn(async (input, init) => {
    const url = String(input);
    if (url.endsWith("/health")) return Response.json({ status: "ok" });
    if (url.includes("/plan/scheduling-context?")) return Response.json({ timezone, local_today: day, week_start: "2026-10-05", selected_dates: [day], placement_revision: 1, plan: null });
    if (url.endsWith("/weekly-review/status")) return Response.json({ today_is_sunday: false, review_required: false });
    if (url.endsWith("/workout/today")) {
      workouts.push(day);
      return Response.json({ session_id: "daily", workout_occurrence_id: "daily-occurrence", title: "Daily Workout", date: day,
        exercises: [{ id: "press", name: "Daily Press", sets: 3, rep_range: [8, 12], recommended_working_weight: 20 }] });
    }
    if (url.includes("/soreness?")) { sorenessDates.push(url); return Response.json([]); }
    if (url.endsWith("/soreness") && init?.method === "POST") {
      saves.push(JSON.parse(String(init.body)).entry_date);
      return Response.json({});
    }
    return Response.json({});
  });
  return { sorenessDates, saves, workouts, setDay: (value: string) => { day = value; } };
}

test.each([
  ["2026-10-11T02:00:00Z", "America/Los_Angeles", "2026-10-10"],
  ["2026-10-10T13:00:00Z", "Pacific/Auckland", "2026-10-11"],
])("daily lookup and saved soreness use the scheduling date at %s", async (instant, zone, day) => {
  const fixture = dailyFixture(instant, zone, day);
  render(<TodayPage />);
  expect(await screen.findByText(/sore today\?/i)).toBeInTheDocument();
  expect(fixture.sorenessDates).toEqual([expect.stringContaining(`start_date=${day}&end_date=${day}`)]);
  fireEvent.click(screen.getByRole("button", { name: /Save & Start Workout/ }));
  await waitFor(() => expect(fixture.saves).toEqual([day]));
  await waitFor(() => expect(screen.queryByText(/sore today\?/i)).not.toBeInTheDocument());
});

test.each([
  ["2026-10-11T02:00:00Z", "America/Los_Angeles", "2026-10-10"],
  ["2026-10-10T13:00:00Z", "Pacific/Auckland", "2026-10-11"],
])("Skip suppresses the local day across remount at %s", async (instant, zone, day) => {
  const fixture = dailyFixture(instant, zone, day);
  const { unmount } = render(<TodayPage />);
  await screen.findByText(/sore today\?/i);
  fireEvent.click(screen.getByRole("button", { name: /^Skip$/ }));
  await waitFor(() => expect(localStorage.getItem(`hypertrophy_soreness_skip:${day}`)).toBe("1"));
  unmount();
  render(<TodayPage />);
  await screen.findByRole("button", { name: /Daily Press/ });
  await waitFor(() => expect(fixture.workouts.length).toBeGreaterThanOrEqual(3));
  expect(fixture.sorenessDates).toHaveLength(1);
  expect(screen.queryByText(/sore today\?/i)).not.toBeInTheDocument();
});

test("a skipped date does not suppress the next local day's prompt in the same page", async () => {
  const fixture = dailyFixture("2026-10-11T06:59:00Z", "America/Los_Angeles", "2026-10-10");
  render(<TodayPage />);
  await screen.findByText(/sore today\?/i);
  fireEvent.click(screen.getByRole("button", { name: /^Skip$/ }));
  await waitFor(() => expect(screen.queryByText(/sore today\?/i)).not.toBeInTheDocument());
  fixture.setDay("2026-10-11");
  fireEvent.click(screen.getByRole("button", { name: /^Reload$/ }));
  await screen.findByText(/sore today\?/i);
  expect(fixture.sorenessDates.at(-1)).toContain("start_date=2026-10-11&end_date=2026-10-11");
});

test("a missing scheduling clock blocks daily writes and workout loading", async () => {
  const fixture = dailyFixture("2026-10-11T02:00:00Z", "America/Los_Angeles", "2026-10-10");
  const original = globalThis.fetch;
  globalThis.fetch = vi.fn(async (input, init) => String(input).includes("/plan/scheduling-context?")
    ? Response.json({ detail: "unavailable" }, { status: 503 }) : original(input, init));
  render(<TodayPage />);
  await screen.findByText("Unable to verify soreness status. Try again.");
  expect(fixture.workouts).toEqual([]);
  expect(fixture.sorenessDates).toEqual([]);
  expect(fixture.saves).toEqual([]);
});

test.each(["Save & Start Workout", "Skip"])("%s rechecks the review gate instead of using a prior-day soreness modal", async (action) => {
  const fixture = dailyFixture("2026-10-11T06:59:00Z", "America/Los_Angeles", "2026-10-10");
  render(<TodayPage />);
  await screen.findByText(/sore today\?/i);
  fixture.setDay("2026-10-11");
  const original = globalThis.fetch;
  globalThis.fetch = vi.fn(async (input, init) => String(input).endsWith("/weekly-review/status")
    ? Response.json({ today_is_sunday: true, review_required: true }) : original(input, init));
  fireEvent.click(screen.getByRole("button", { name: action }));
  await screen.findByText("Sunday review required before starting workout. Go to Check-In to submit weekly review.");
  expect(fixture.saves).toEqual([]);
  expect(fixture.workouts).toEqual(["2026-10-10"]);
  expect(localStorage.getItem("hypertrophy_soreness_skip:2026-10-11")).toBeNull();
});
