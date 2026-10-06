import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import TodayPage from "@/app/today/page";

afterEach(cleanup);

test("an unscheduled local date shows a rest state and sends no generation command", async () => {
  const writes: string[] = [];
  globalThis.fetch = vi.fn(async (input, init) => {
    const url = String(input);
    if (init?.method === "POST") writes.push(url);
    if (url.endsWith("/health")) return Response.json({ status: "ok" });
    if (url.includes("/plan/scheduling-context?")) return Response.json({ timezone: "America/Los_Angeles", local_today: "2026-10-11", week_start: "2026-10-05", selected_dates: [], placement_revision: 0, plan: null });
    if (url.endsWith("/weekly-review/status")) return Response.json({ today_is_sunday: false, review_required: false });
    if (url.endsWith("/workout/today")) return Response.json({ detail: "No workout scheduled today" }, { status: 404 });
    return Response.json({});
  });
  render(<TodayPage />);
  expect(await screen.findByRole("heading", { name: "No workout scheduled today" })).toBeInTheDocument();
  expect(await screen.findByText("Sun, Oct 11 · America/Los_Angeles")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Open Week Plan" })).toHaveAttribute("href", "/week");
  expect(screen.queryByRole("list", { name: "Exercise list" })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /Load today's workout/ }));
  await waitFor(() => expect(screen.getByRole("heading", { name: "No workout scheduled today" })).toBeInTheDocument());
  expect(writes).toEqual([]);
});

test("partial selected-date resume uses the original occurrence progress", async () => {
  const progressPaths: string[] = [];
  globalThis.fetch = vi.fn(async (input) => {
    const url = String(input);
    if (url.endsWith("/health")) return Response.json({ status: "ok" });
    if (url.endsWith("/weekly-review/status")) return Response.json({ today_is_sunday: false, review_required: false });
    if (url.endsWith("/workout/today")) return Response.json({
      workout_occurrence_id: "dated-occurrence", session_id: "authored-day1", title: "Selected Tuesday", date: "2026-10-06", resume: true,
      exercises: [{ exercise_occurrence_id: "dated-slot", id: "press", name: "Resume Press", sets: 3, rep_range: [8, 12], recommended_working_weight: 20 }],
    });
    if (url.endsWith("/progress")) {
      progressPaths.push(url);
      return Response.json({ completed_total: 1, planned_total: 3, percent_complete: 33,
        exercises: [{ exercise_occurrence_id: "dated-slot", exercise_id: "press", completed_sets: 1 }] });
    }
    if (url.includes("/soreness")) return Response.json([{ entry_date: "2026-10-06" }]);
    return Response.json({});
  });
  render(<TodayPage />);
  expect(await screen.findByRole("button", { name: /Resume Press/ })).toHaveTextContent("1/3");
  expect(progressPaths).toEqual([expect.stringMatching(/\/workout\/dated-occurrence\/progress$/)]);
  expect(screen.queryByRole("heading", { name: "No workout scheduled today" })).not.toBeInTheDocument();
});
