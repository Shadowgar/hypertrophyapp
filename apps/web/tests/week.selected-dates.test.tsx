import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import WeekPage from "@/app/week/page";

const selected = ["2026-10-06", "2026-10-09", "2026-10-11"];
const plan = {
  program_template_id: "pure_bodybuilding_phase_1_full_body", split: "full_body", phase: "maintenance",
  week_start: "2026-10-05", user: { days_available: 3 },
  sessions: selected.map((date, i) => ({ session_id: `day-${i}`, workout_occurrence_id: `occ-${i}`, title: `Workout ${i + 1}`, date,
    exercises: [{ id: `exercise-${i}`, name: "Press", sets: 4, rep_range: [8, 12], recommended_working_weight: 20 }] })),
  missed_day_policy: "selected_dates", weekly_volume_by_muscle: {}, muscle_coverage: {},
  mesocycle: { week_index: 1, trigger_weeks_base: 6, trigger_weeks_effective: 6, is_deload_week: false, deload_reason: "none" },
  deload: { active: false, set_reduction_pct: 0, load_reduction_pct: 0, reason: "none" },
  template_selection_trace: {}, generation_runtime_trace: {},
  schedule: { mode: "selected_dates_v1", timezone: "America/Los_Angeles", selected_dates: selected, placement_revision: 1,
    spacing: { gap_days: [3, 2], warnings: ["Adjacent-week workout dates are unknown; cross-week spacing is not qualified."] } },
};
let context: { timezone: string; local_today: string; week_start: string; selected_dates: string[]; placement_revision: number; plan: typeof plan | null };
let writes: { path: string; body: Record<string, unknown> }[];
let serverSundayReviewRequired: boolean;

beforeEach(() => {
  writes = [];
  serverSundayReviewRequired = false;
  context = { timezone: "America/Los_Angeles", local_today: "2026-10-06", week_start: "2026-10-05", selected_dates: [], placement_revision: 0, plan: null };
  globalThis.fetch = vi.fn(async (input, init) => {
    const url = String(input);
    if (url.includes("/plan/scheduling-context?")) return Response.json(context);
    if (url.endsWith("/plan/latest-week")) return Response.json({ detail: "No plan generated" }, { status: 404 });
    if (url.endsWith("/profile")) return Response.json({ selected_program_id: plan.program_template_id, days_available: 3 });
    if (url.endsWith("/plan/programs")) return Response.json([{ id: plan.program_template_id, name: "Full Body Phase 1" }]);
    if (url.endsWith("/weekly-review/status")) return Response.json({ today_is_sunday: serverSundayReviewRequired, review_required: serverSundayReviewRequired });
    if (init?.method === "POST") {
      writes.push({ path: url, body: JSON.parse(String(init.body)) });
      if (url.endsWith("/plan/generate-week")) context = { ...context, selected_dates: selected, placement_revision: 1, plan };
      return Response.json(plan);
    }
    return Response.json({});
  });
});
afterEach(cleanup);

async function chooseDates() {
  for (const name of ["Tue, Oct 6", "Fri, Oct 9", "Sun, Oct 11"]) fireEvent.click(await screen.findByRole("checkbox", { name }));
}

test("current local week offers accessible exact dates and preview does not activate", async () => {
  render(<WeekPage />);
  await chooseDates();
  expect(screen.getAllByRole("checkbox")).toHaveLength(7);
  expect(screen.getByLabelText("Scheduling timezone")).toHaveValue("America/Los_Angeles");
  expect(screen.getByText("3 of 2–5 dates selected")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Activate selected dates" })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Preview selected dates" }));
  await screen.findByRole("button", { name: "Activate selected dates" });
  expect(writes).toEqual([{ path: expect.stringMatching(/\/plan\/selected-dates\/preview$/), body: {
    template_id: plan.program_template_id, week_start: "2026-10-05", timezone: "America/Los_Angeles", selected_dates: selected, expected_placement_revision: 0,
  } }]);
  expect(screen.getByRole("button", { name: /Tue, Oct 6: Workout 1/ })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Fri, Oct 9: Workout 2/ })).toBeInTheDocument();
  expect(screen.getByText(/Adjacent-week workout dates are unknown/)).toBeInTheDocument();
  expect(screen.getByText(/duration.*not calibrated/i)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("checkbox", { name: "Mon, Oct 5" }));
  expect(screen.queryByRole("button", { name: "Activate selected dates" })).not.toBeInTheDocument();
  expect(screen.getByText(/Elapsed dates.*history/i)).toBeInTheDocument();
});

test("activation rechecks server week and clears stale previous-week selections", async () => {
  render(<WeekPage />);
  await chooseDates();
  fireEvent.click(screen.getByRole("button", { name: "Preview selected dates" }));
  await screen.findByRole("button", { name: "Activate selected dates" });
  context = { ...context, local_today: "2026-10-12", week_start: "2026-10-12" };
  fireEvent.click(screen.getByRole("button", { name: "Activate selected dates" }));
  await screen.findByRole("checkbox", { name: "Mon, Oct 12" });
  expect(screen.getAllByRole("checkbox").every((el) => !(el as HTMLInputElement).checked)).toBe(true);
  expect(writes.filter((item) => item.path.endsWith("/plan/generate-week"))).toHaveLength(0);
  expect(screen.queryByRole("button", { name: "Activate selected dates" })).not.toBeInTheDocument();
});

test("focus refresh does not reuse old week checkbox state", async () => {
  context = { ...context, selected_dates: selected, placement_revision: 1, plan };
  render(<WeekPage />);
  expect(await screen.findByRole("checkbox", { name: "Tue, Oct 6" })).toBeChecked();
  context = { ...context, local_today: "2026-10-12", week_start: "2026-10-12", selected_dates: [], placement_revision: 0, plan: null };
  fireEvent(window, new Event("focus"));
  await screen.findByRole("checkbox", { name: "Mon, Oct 12" });
  expect(screen.getAllByRole("checkbox").every((el) => !(el as HTMLInputElement).checked)).toBe(true);
  expect(screen.queryByRole("button", { name: /Workout 1/ })).not.toBeInTheDocument();
});

test("unchanged preview requires explicit activation and refreshes placement revision", async () => {
  render(<WeekPage />);
  await chooseDates();
  fireEvent.click(screen.getByRole("button", { name: "Preview selected dates" }));
  fireEvent.click(await screen.findByRole("button", { name: "Activate selected dates" }));
  await screen.findByText(/Selected dates activated/);
  expect(writes.filter((item) => item.path.endsWith("/plan/generate-week"))).toEqual([{
    path: expect.any(String), body: { template_id: plan.program_template_id, week_start: "2026-10-05", timezone: "America/Los_Angeles", selected_dates: selected, expected_placement_revision: 0 },
  }]);
  expect(screen.queryByRole("button", { name: "Activate selected dates" })).not.toBeInTheDocument();
});

test("server Sunday review status cannot block local Saturday date placement", async () => {
  context = { ...context, local_today: "2026-10-10" };
  serverSundayReviewRequired = true;
  render(<WeekPage />);
  await chooseDates();
  fireEvent.click(screen.getByRole("button", { name: "Preview selected dates" }));
  fireEvent.click(await screen.findByRole("button", { name: "Activate selected dates" }));
  await screen.findByText(/Selected dates activated/);
  expect(screen.getByText("Planned sets: 12")).toBeInTheDocument();
  expect(screen.queryByRole("link", { name: /Open Check-In/i })).not.toBeInTheDocument();
  expect(screen.queryByText(/Sunday review required/i)).not.toBeInTheDocument();
  expect(writes.map((write) => write.path)).toEqual([
    expect.stringMatching(/\/plan\/selected-dates\/preview$/),
    expect.stringMatching(/\/plan\/generate-week$/),
  ]);
  expect(writes.every((write) => Object.keys(write.body).sort().join(",") === "expected_placement_revision,selected_dates,template_id,timezone,week_start")).toBe(true);
  expect(writes.map((write) => write.body.selected_dates)).toEqual([selected, selected]);
});

test("a changed placement revision invalidates preview without overwriting it", async () => {
  render(<WeekPage />);
  await chooseDates();
  fireEvent.click(screen.getByRole("button", { name: "Preview selected dates" }));
  await screen.findByRole("button", { name: "Activate selected dates" });
  context = { ...context, selected_dates: ["2026-10-07", "2026-10-10"], placement_revision: 2 };
  fireEvent.click(screen.getByRole("button", { name: "Activate selected dates" }));
  await screen.findByText(/local week or placement changed/);
  expect(screen.getByRole("checkbox", { name: "Wed, Oct 7" })).toBeChecked();
  expect(screen.getByRole("checkbox", { name: "Tue, Oct 6" })).not.toBeChecked();
  expect(writes.filter((item) => item.path.endsWith("/plan/generate-week"))).toHaveLength(0);
});

test("editing timezone invalidates preview and switching local week clears dates", async () => {
  render(<WeekPage />);
  await chooseDates();
  fireEvent.click(screen.getByRole("button", { name: "Preview selected dates" }));
  await screen.findByRole("button", { name: "Activate selected dates" });
  context = { ...context, timezone: "Pacific/Auckland", local_today: "2026-10-12", week_start: "2026-10-12" };
  fireEvent.change(screen.getByLabelText("Scheduling timezone"), { target: { value: "Pacific/Auckland" } });
  expect(screen.queryByRole("button", { name: "Activate selected dates" })).not.toBeInTheDocument();
  fireEvent.blur(screen.getByLabelText("Scheduling timezone"));
  await screen.findByRole("checkbox", { name: "Mon, Oct 12" });
  expect(screen.getAllByRole("checkbox").every((el) => !(el as HTMLInputElement).checked)).toBe(true);
  expect(writes.filter((item) => item.path.endsWith("/plan/generate-week"))).toHaveLength(0);
});

test("selection outside the two to five date limit cannot preview", async () => {
  render(<WeekPage />);
  fireEvent.click(await screen.findByRole("checkbox", { name: "Tue, Oct 6" }));
  expect(screen.getByRole("button", { name: "Preview selected dates" })).toBeDisabled();
  for (const name of ["Wed, Oct 7", "Thu, Oct 8", "Fri, Oct 9", "Sat, Oct 10", "Sun, Oct 11"]) fireEvent.click(screen.getByRole("checkbox", { name }));
  expect(screen.getByRole("button", { name: "Preview selected dates" })).toBeDisabled();
  expect(writes).toEqual([]);
});
