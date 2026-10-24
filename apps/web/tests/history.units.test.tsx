import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import HistoryPage from "@/app/history/page";

const saved = vi.hoisted(() => ({ weight_unit: "kg" as "kg" | "lb" }));
vi.mock("@/components/appearance-provider", () => ({ useAppearance: () => ({ preferences: saved }) }));
const analytics = {
  checkins: [{ adherence_score: 4 }, { adherence_score: 5 }],
  adherence: { average_pct: 90, high_readiness_streak: 2, trend_delta: 1 },
  bodyweight_trend: [{ body_weight: 80 }, { body_weight: 82.5 }],
  strength_trends: [{ exercise_id: "bench", pr_weight: 90, pr_delta: 10, points: [{ week_start: "2026-03-02", max_weight: 80 }, { week_start: "2026-03-09", max_weight: 90 }] }],
  pr_highlights: [{ exercise_id: "bench", pr_weight: 90, pr_delta: 10 }],
  body_measurement_trends: [{ name: "waist", unit: "cm", latest_value: 82, delta: -2, points: [{ measured_on: "2026-03-09", value: 82 }] }],
  volume_heatmap: { max_volume: 800, weeks: [{ week_start: "2026-03-09", days: [{ day_index: 0, sets: 1, volume: 800 }] }] },
};
const day = (date: string, volume: number) => ({ date, weekday: 0, set_count: 1, exercise_count: 1, total_volume: volume, completed: true, program_ids: [], muscles: [], pr_count: 0, pr_exercises: [] });
const receipt = { date: "2026-03-09", totals: { set_count: 1, exercise_count: 1, total_volume: 800 }, workouts: [{ workout_id: "receipt", total_sets: 1, total_volume: 800, exercises: [{ exercise_id: "bench", total_sets: 1, total_volume: 800, sets: [{ set_index: 1, reps: 10, weight: 80, actual_rir: 2 }] }] }] };
beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/history/analytics")) return Response.json(analytics);
    if (url.includes("/plan/scheduling-context")) return Response.json({ local_today: "2026-03-09" });
    if (url.includes("/history/calendar")) return Response.json({ days: [day("2026-03-02", 400), day("2026-03-09", 800)] });
    if (url.includes("/history/day/")) return Response.json(receipt);
    return Response.json({ entries: [] });
  }));
});
test.each(["kg", "lb"] as const)("History uses saved %s and updates every mass surface when preferences switch", async (initialUnit) => {
  saved.weight_unit = initialUnit;
  const original = JSON.stringify({ analytics, receipt });
  const { rerender } = render(<HistoryPage />);
  await waitFor(() => expect(screen.getByTitle(/2026-03-09: 1 sets/)).toBeInTheDocument());
  fireEvent.click(screen.getByTitle(/2026-03-09: 1 sets/));
  await waitFor(() => expect(screen.getByText("Workout receipt")).toBeInTheDocument());
  for (const title of ["Bodyweight Trend", "Strength Trend", "PR Highlights", "Body Measurements", "Volume Heat Map"]) fireEvent.click(screen.getByRole("button", { name: new RegExp(`^${title}`) }));
  const requestCount = vi.mocked(fetch).mock.calls.length;
  const assertUnit = (unit: "kg" | "lb") => {
    const kg = unit === "kg";
    expect(screen.getByText(`Set 1: 10 × ${kg ? 80 : 176.4} ${unit} · Actual RIR 2`)).toBeInTheDocument();
    expect(screen.getAllByText(`PR ${kg ? 90 : 198.4} ${unit} (+${kg ? 10 : 22} ${unit})`).length).toBeGreaterThan(0);
    expect(screen.getAllByText(`+${kg ? 2.5 : 5.5} ${unit}`).length).toBeGreaterThan(0);
    expect(screen.getByLabelText(`Week 1 bodyweight ${kg ? 80 : 176.4} ${unit}`)).toHaveAttribute("title", `Week 1: ${kg ? 80 : 176.4} ${unit}`);
    expect(screen.getByLabelText(`2026-03-09 strength ${kg ? 90 : 198.4} ${unit}`)).toHaveAttribute("title", `2026-03-09: ${kg ? 90 : 198.4} ${unit}`);
    expect(screen.getByText(`Volume +${kg ? 400 : 881.8} ${unit} × reps`)).toBeInTheDocument();
    expect(screen.getByTitle(`Day 1: ${kg ? 800 : 1763.7} ${unit} × reps volume (1 sets)`)).toHaveTextContent(kg ? "800" : "1763.7");
    expect(screen.getByTitle(/2026-03-09: 1 sets/)).toHaveAttribute("title", `2026-03-09: 1 sets, 1 exercises, ${kg ? 800 : 1763.7} ${unit} × reps volume, 0 PRs`);
    expect(screen.getByTitle("2026-03-09: 82 cm")).toBeInTheDocument();
    expect(screen.queryByText(/\blbs\b/)).not.toBeInTheDocument();
  };
  assertUnit(initialUnit);
  saved.weight_unit = initialUnit === "kg" ? "lb" : "kg";
  rerender(<HistoryPage />);
  assertUnit(saved.weight_unit);
  saved.weight_unit = initialUnit;
  rerender(<HistoryPage />);
  assertUnit(initialUnit);
  expect(vi.mocked(fetch).mock.calls).toHaveLength(requestCount);
  expect(vi.mocked(fetch).mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true);
  expect(JSON.stringify({ analytics, receipt })).toBe(original);
});
