import React from "react";
import { test, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import TodayPage from "@/app/today/page";

beforeEach(() => localStorage.clear());
test("lost undo acknowledgement retains command and state; confirmation clears stale load guidance", async () => {
  let count = 1;
  let attempts = 0;
  const bodies: Record<string, unknown>[] = [];
  const live = (sets: number, weight: number) => ({ completed_sets: sets, remaining_sets: 3 - sets,
    recommended_reps_min: 8, recommended_reps_max: 12, recommended_weight: weight,
    guidance: "hold", guidance_rationale: sets ? "Old higher load" : "Rebuilt guidance", decision_trace: {} });
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.includes("/plan/scheduling-context?")) return Promise.resolve(Response.json({ timezone: "UTC", local_today: new Date().toISOString().slice(0, 10), week_start: "2026-10-05", selected_dates: [], placement_revision: 0, plan: null }));
    const json = (value: unknown) => new Response(JSON.stringify(value), { status: 200 });
    if (url.endsWith("/health")) return json({ status: "ok" });
    if (url.endsWith("/workout/today")) return json({ session_id: "template", workout_occurrence_id: "occurrence", title: "Synthetic",
      date: new Date().toISOString().slice(0, 10), exercises: [{ id: "bench", exercise_occurrence_id: "bench-slot", name: "Undo Bench",
        sets: 3, rep_range: [8, 12], completed_sets: count, recommended_working_weight: count ? 30 : 25, live_recommendation: live(count, count ? 30 : 25) }] });
    if (url.includes("/progress")) return json({ completed_total: count, planned_total: 3, percent_complete: count ? 33 : 0,
      exercises: [{ exercise_id: "bench", exercise_occurrence_id: "bench-slot", completed_sets: count }] });
    if (url.includes("/soreness")) return json([{ entry_date: new Date().toISOString().slice(0, 10) }]);
    if (url.endsWith("/undo-last-set")) {
      bodies.push(JSON.parse(String(init?.body))); attempts++;
      if (attempts === 1) throw new Error("Lost acknowledgement");
      count = 0;
      return json({ status: "ok", live_recommendation: live(0, 25) });
    }
    return json({});
  }));
  render(<TodayPage />);
  fireEvent.click(screen.getByRole("button", { name: /Load today's workout/i }));
  fireEvent.click(await screen.findByRole("button", { name: /Undo Bench/ }));
  fireEvent.click(screen.getByRole("button", { name: /Undo Last Set/ }));
  await screen.findByText(/Undo was not confirmed/);
  expect(screen.getByRole("button", { name: /Undo Last Set/ })).toBeEnabled();
  fireEvent.click(screen.getByRole("button", { name: /Undo Last Set/ }));
  await waitFor(() => expect(bodies).toHaveLength(2));
  expect(bodies[0].command_id).toBe(bodies[1].command_id);
  expect(bodies[0].exercise_occurrence_id).toBe("bench-slot");
  await waitFor(() => expect(screen.queryByRole("button", { name: /Undo Last Set/ })).toBeNull());
  expect(screen.queryByText("Old higher load")).toBeNull();
  await screen.findByText("Rebuilt guidance");
  vi.unstubAllGlobals();
});
