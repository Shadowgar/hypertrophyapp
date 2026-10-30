import React from "react";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import WeekPage from "@/app/week/page";

const dates = ["2026-10-26", "2026-10-28", "2026-10-30"];
const plan = {
  program_template_id: "pure_bodybuilding_phase_1_full_body", week_start: dates[0],
  sessions: dates.map((date, i) => ({ session_id: `session-${i}`, workout_occurrence_id: `occurrence-${i}`, date,
    title: `Authored session ${i + 1}`, exercises: [{ id: "press", name: "Press", sets: i + 2, rep_range: [8, 10] }] })),
  schedule: { timezone: "UTC", selected_dates: dates, placement_revision: 1, preview_digest: "a".repeat(64), spacing: { warnings: [], gap_days: [2, 2] } },
};

beforeEach(() => {
  localStorage.setItem("hypertrophy_token", "workload-only-disposable-fixture");
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path.endsWith("/profile")) return Response.json({ selected_program_id: plan.program_template_id, days_available: 3, session_time_budget_minutes: 60 });
    if (path.includes("/plan/scheduling-context")) return Response.json({ week_start: dates[0], local_today: dates[0], timezone: "UTC", placement_revision: 1, selected_dates: dates, plan });
    if (path.endsWith("/plan/programs")) return Response.json([{ id: plan.program_template_id, name: "Full Body Phase 1" }]);
    if (path.includes("/history/calendar")) return Response.json({ days: [] });
    if (path.endsWith("/plan/selected-dates/preview") && init?.method === "POST") return Response.json(plan);
    return Response.json({});
  }));
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

test("active Week discloses each session's dose, saved time goal and source-preserving review", async () => {
  render(<WeekPage />);
  const sessions = within(screen.getByRole("region", { name: "Scheduled sessions" }));
  await sessions.findByText("Authored session 1");
  expect(await sessions.findAllByText(/Your session-time goal: 60 minutes/)).toHaveLength(3);
  expect(sessions.getAllByLabelText("Workout workload and time")).toHaveLength(3);
  expect(sessions.getByText("1 exercise · 2 planned working sets")).toBeInTheDocument();
  expect(sessions.getByText("1 exercise · 4 planned working sets")).toBeInTheDocument();
  expect(sessions.getAllByText(/Duration is unknown/)).toHaveLength(3);
  expect(sessions.getAllByRole("link", { name: /Review 2–5 selected visits/ })).toHaveLength(3);
});

test("unactivated preview exposes workload and time uncertainty before activation", async () => {
  render(<WeekPage />);
  const button = await screen.findByRole("button", { name: "Preview selected dates" });
  await vi.waitFor(() => expect(button).toBeEnabled());
  fireEvent.click(button);
  await screen.findByRole("button", { name: "Activate selected dates" });
  const sessions = within(screen.getByRole("region", { name: "Scheduled sessions" }));
  expect(sessions.getAllByLabelText("Workout workload and time")).toHaveLength(3);
  expect(sessions.getAllByText(/may exceed your available time/)).toHaveLength(3);
  expect(sessions.getAllByText("Preview · not activated")).toHaveLength(3);
});


test.each(["full_body_v1", "unknown_program", null])("Week does not claim source-preserving redistribution for %s", async programId => {
  const request = vi.mocked(fetch).getMockImplementation()!;
  vi.stubGlobal("fetch", vi.fn((input, init) => String(input).includes("/plan/scheduling-context")
    ? Promise.resolve(Response.json({week_start:dates[0],local_today:dates[0],timezone:"UTC",placement_revision:1,selected_dates:dates,plan:{...plan,program_template_id:programId}}))
    : request(input, init)));
  render(<WeekPage/>);
  const sessions = within(screen.getByRole("region", {name:"Scheduled sessions"}));
  await sessions.findByText("Authored session 1");
  expect(sessions.queryByText(/spread all source exercises/)).not.toBeInTheDocument();
});
