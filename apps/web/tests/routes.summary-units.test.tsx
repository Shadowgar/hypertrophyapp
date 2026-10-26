import React from "react";
import { fireEvent, render, screen, waitFor, cleanup } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import HomePage from "@/app/page";
import WeekPage from "@/app/week/page";
import CheckinPage from "@/app/checkin/page";

const saved = vi.hoisted(() => ({ weight_unit: "kg" as "kg" | "lb" }));
vi.mock("@/components/appearance-provider", () => ({ useAppearance: () => ({ preferences: saved }) }));
vi.mock("@/components/coaching-intelligence-panel", () => ({ default: () => null }));
const exercise = { id: "press", name: "Qualified press", sets: 3, rep_range: [8, 12], recommended_working_weight: 80 };
const summary = { completion_pct: 100, exercise_faults: [{ primary_exercise_id: "press", name: "Press audit", completed_sets: 3, planned_sets: 3, average_performed_reps: 10, average_performed_weight: 80, target_reps_min: 8, target_reps_max: 12, target_weight: 90 }] };
const profile = { weight: 82.5, calories: 2400, protein: 150, fat: 70, carbs: 250, equipment_profile: [], days_available: 3, weak_areas: [], nutrition_phase: "maintenance", selected_program_id: "pure_bodybuilding_phase_1_full_body", scheduling_timezone: "UTC" };
const analytics = { window: { limit_weeks: 8 }, adherence: { average_pct: 100 }, bodyweight_trend: [{ body_weight: 85 }], strength_trends: [{ exercise_id: "press", latest_weight: 80, points: [] }], pr_highlights: [] };
const review = { week_start: "2026-10-19", previous_week_summary: summary };
const custom = { target_kind: "rir", target_min: 2, target_max: 3, rest_seconds: { low: 90, high: 120 }, identity: { unit: "kg", basis: "total_external" } };
let customized = false;
let useAnalyticsWeight = true;
const fixture = { exercise, profile, analytics, summary };
beforeEach(() => {
  localStorage.setItem("hypertrophy_token", "synthetic-token");
  customized = false;
  useAnalyticsWeight = true;
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith("/profile")) return Response.json(profile);
    if (url.endsWith("/workout/today")) return Response.json({ title: "Unit fixture", exercises: [exercise] });
    if (url.includes("/history/analytics")) return Response.json({ ...analytics, bodyweight_trend: useAnalyticsWeight ? analytics.bodyweight_trend : [] });
    if (url.includes("/weekly-review/status")) return Response.json(review);
    if (url.endsWith("/weekly-review") && init?.method === "POST") return Response.json({ summary, adjustments: { exercise_overrides: [] }, readiness_score: 75 });
    if (url.endsWith("/plan/programs")) return Response.json([]);
    if (url.includes("/plan/scheduling-context?")) return Response.json({ timezone: "UTC", local_today: "2026-10-20", week_start: "2026-10-19", selected_dates: ["2026-10-20"], placement_revision: 1, plan: { week_start: "2026-10-19", program_template_id: customized ? "customized_full_body_v1" : "pure_bodybuilding_phase_1_full_body", customized: customized ? {} : undefined, sessions: [{ session_id: "session", date: "2026-10-20", title: "Unit fixture", exercises: [ { ...exercise, customized: customized ? custom : undefined }, { ...exercise, id: "unknown", name: "Unknown press", recommended_working_weight: null, customized: customized ? custom : undefined } ] }] } });
    return Response.json({});
  }));
});

function switchUnits(rerender: (ui: React.ReactNode) => void, page: React.ReactElement, initial: "kg" | "lb", check: (unit: "kg" | "lb") => void) {
  const requests = vi.mocked(fetch).mock.calls.length;
  for (const unit of [initial, initial === "kg" ? "lb" : "kg", initial] as const) {
    saved.weight_unit = unit;
    rerender(React.cloneElement(page));
    check(unit);
  }
  expect(vi.mocked(fetch).mock.calls).toHaveLength(requests);
}

test.each(["kg", "lb"] as const)("Home mass summaries honor saved %s and switching, including analytics and profile fallback", async initial => {
  saved.weight_unit = initial;
  const canonical = JSON.stringify(fixture);
  for (const analyticsWeight of [true, false]) {
    useAnalyticsWeight = analyticsWeight;
    const page = <HomePage />;
    const { rerender } = render(page);
    await screen.findByText(/Qualified press · 3 x/);
    switchUnits(rerender, page, initial, unit => {
      const kg = unit === "kg";
      expect(screen.getByText(`Qualified press · 3 x 8-12 @ ${kg ? 80 : 176.4} ${unit}`)).toBeInTheDocument();
      expect(screen.getByText(`Latest ${kg ? 80 : 176.4} ${unit} top set across 0 tracked sessions`)).toBeInTheDocument();
      expect(screen.getByText(`Bodyweight: ${analyticsWeight ? (kg ? 85 : 187.4) : (kg ? 82.5 : 181.9)} ${unit}`)).toBeInTheDocument();
    });
    cleanup();
  }
  expect(JSON.stringify(fixture)).toBe(canonical);
});

test.each(["kg", "lb"] as const)("Week authored and Customized numeric kg payloads render saved %s once and preserve unknown loads", async initial => {
  for (const mode of [false, true]) {
    saved.weight_unit = initial;
    customized = mode;
    const page = <WeekPage />;
    const { rerender } = render(page);
    await screen.findByText("Week Overview");
    fireEvent.click(screen.getByRole("button", { name: /Tue, Oct 20: Unit fixture/ }));
    switchUnits(rerender, page, initial, unit => {
      expect(screen.getByText(`3 sets · 8-12 reps · ${unit === "kg" ? 80 : 176.4} ${unit}`)).toBeInTheDocument();
      expect(screen.getByText(`Lead: Qualified press · 3 sets · 8-12 reps @ ${unit === "kg" ? 80 : 176.4} ${unit}`)).toBeInTheDocument();
      expect(screen.getByText(mode ? /Exercise-specific calibration pending/ : /3 sets · 8-12 reps · Record actual load/)).toBeInTheDocument();
    });
    cleanup();
  }
});

test.each(["kg", "lb"] as const)("Review audit renders saved %s while kg bodyweight input and submission remain canonical", async initial => {
  saved.weight_unit = initial;
  const canonical = JSON.stringify(fixture);
  const page = <CheckinPage />;
  const { rerender } = render(page);
  await screen.findByText("Weekly review ready");
  fireEvent.click(screen.getByRole("button", { name: /Previous Week Lift Audit/ }));
  switchUnits(rerender, page, initial, unit => {
    expect(screen.getByText(`3/3 sets · avg 10 reps @ ${unit === "kg" ? 80 : 176.4} ${unit}`)).toBeInTheDocument();
    expect(screen.getByText(`Target 8-12 reps @ ${unit === "kg" ? 90 : 198.4} ${unit}`)).toBeInTheDocument();
    expect(screen.getByLabelText("Current Bodyweight (kg)")).toHaveValue(82.5);
  });
  fireEvent.change(screen.getByLabelText("Current Bodyweight (kg)"), { target: { value: "83.2" } });
  fireEvent.click(screen.getByRole("button", { name: /Save Weekly Review/ }));
  await waitFor(() => expect(vi.mocked(fetch).mock.calls.some(([url, init]) => String(url).endsWith("/weekly-review") && init?.method === "POST")).toBe(true));
  const payload = vi.mocked(fetch).mock.calls.find(([url, init]) => String(url).endsWith("/weekly-review") && init?.method === "POST")![1];
  expect(JSON.parse(String(payload?.body)).body_weight).toBe(83.2);
  expect(JSON.stringify(fixture)).toBe(canonical);
});
