import React from "react";
import { describe, test, expect, beforeEach, vi } from "vitest";
import { act, renderHook, render, screen, fireEvent, waitFor } from "@testing-library/react";
import TodayPage from "@/app/today/page";
import { useExerciseControl } from "@/components/exercise-control";
import { acknowledgeLogCommand, exerciseKey, getLogCommand, occurrenceStorageKey, pendingCommandKey } from "@/lib/workout-identity";
import type { WorkoutSession } from "@/lib/api";

beforeEach(() => localStorage.clear());

describe("occurrence caches and retry commands", () => {
  test("the same template and catalog IDs in later weeks cannot recover prior caches", () => {
    const first = { session_id: "same-template", workout_occurrence_id: "week-one" } as WorkoutSession;
    const second = { ...first, workout_occurrence_id: "week-two" };
    for (const kind of ["swaps", "completed"]) {
      localStorage.setItem(occurrenceStorageKey(kind, first), JSON.stringify({ old: 3 }));
      expect(localStorage.getItem(occurrenceStorageKey(kind, second))).toBeNull();
    }
    const left = { id: "same-catalog", exercise_occurrence_id: "slot-one" } as WorkoutSession["exercises"][number];
    expect(exerciseKey(left)).not.toBe(exerciseKey({ ...left, exercise_occurrence_id: "slot-two" }));
    localStorage.setItem("hypertrophy_completed_sets:same-template", "legacy");
    expect(localStorage.getItem(occurrenceStorageKey("completed", second))).toBeNull();
  });

  test("a failed attempt retains its command, including browser storage; acknowledged attempts advance", () => {
    const key = pendingCommandKey("week-one", "slot-one", "work:1");
    const first = getLogCommand(key);
    expect(getLogCommand(key)).toBe(first);
    expect(localStorage.getItem(key)).toBe(first);
    expect(getLogCommand(pendingCommandKey("week-two", "slot-one", "work:1"))).not.toBe(first);
    acknowledgeLogCommand(key);
    expect(getLogCommand(key)).not.toBe(first);
  });

  test("failed submissions do not advance the logical set; simultaneous clicks are one attempt", async () => {
    let release!: () => void;
    const pending = new Promise<void>((resolve) => { release = resolve; });
    const save = vi.fn().mockRejectedValueOnce(new Error("lost response")).mockReturnValueOnce(pending);
    const { result } = renderHook(() => useExerciseControl({ exerciseId: "slot-one", initialCompletedSets: 0, totalSets: 3,
      recommendedWorkingWeight: 25, repRange: [8, 12], skipTimerOnComplete: true, onSetComplete: save }));
    await act(async () => { await result.current.completeSet(); });
    expect(result.current.completedSets).toBe(0);
    let attempt!: Promise<void>;
    act(() => { attempt = result.current.completeSet(); void result.current.completeSet(); });
    expect(save).toHaveBeenCalledTimes(2);
    await act(async () => { release(); await attempt; });
    expect(result.current.completedSets).toBe(1);
    expect(save.mock.calls.map((call) => call[1])).toEqual([1, 1]);
  });

  test("Today sends occurrence IDs, retries its command and clears prior-week state on reload", async () => {
    let week = "week-one";
    let attempts = 0;
    const bodies: Record<string, unknown>[] = [];
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/plan/scheduling-context?")) return Promise.resolve(Response.json({ timezone: "UTC", local_today: new Date().toISOString().slice(0, 10), week_start: "2026-10-05", selected_dates: [], placement_revision: 0, plan: null }));
      const json = (value: unknown) => new Response(JSON.stringify(value), { status: 200 });
      if (url.endsWith("/health")) return json({ status: "ok" });
      if (url.endsWith("/workout/today")) return json({ session_id: "same-template", workout_occurrence_id: week,
        title: "Synthetic workout", date: new Date().toISOString().slice(0, 10), exercises: [
          { id: "same-catalog", exercise_occurrence_id: `${week}-slot`, name: "Synthetic Bench", sets: 3, rep_range: [8, 12], recommended_working_weight: 25 },
          { id: "same-catalog", exercise_occurrence_id: `${week}-second-slot`, name: "Second Bench Slot", sets: 3, rep_range: [8, 12], recommended_working_weight: 25 }] });
      if (url.includes("/soreness")) return json([{ entry_date: new Date().toISOString().slice(0, 10) }]);
      if (url.includes("/progress")) throw new Error("progress unavailable");
      if (url.includes("/log-set")) {
        expect(url).toContain(`/workout/${week}/log-set`);
        bodies.push(JSON.parse(String(init?.body)));
        attempts += 1;
        if (attempts === 1) throw new Error("lost response");
        return json({ live_recommendation: { completed_sets: 1, remaining_sets: 2, recommended_reps_min: 8,
          recommended_reps_max: 12, recommended_weight: 25, guidance: "hold" } });
      }
      return json({});
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<TodayPage />);
    fireEvent.click(screen.getByRole("button", { name: /Load today's workout/i }));
    await screen.findByRole("button", { name: /Synthetic Bench/ });
    fireEvent.click(screen.getByRole("button", { name: /Synthetic Bench/ }));
    fireEvent.click(screen.getByRole("button", { name: "Complete Set" }));
    await screen.findByText(/Set was not confirmed/);
    fireEvent.click(screen.getByRole("button", { name: "Complete Set" }));
    await waitFor(() => expect(bodies).toHaveLength(2));
    expect(bodies[0].command_id).toBe(bodies[1].command_id);
    expect(bodies[0].exercise_id).toBe("same-catalog");
    expect(bodies[0].exercise_occurrence_id).toBe("week-one-slot");
    await waitFor(() => expect(localStorage.getItem("hypertrophy_occurrence_v2:completed:week-one")).toContain('"week-one-slot":1'));
    expect(screen.getByRole("button", { name: /Second Bench Slot/ })).toHaveTextContent("0/3");
    localStorage.setItem("hypertrophy_occurrence_v2:swaps:week-one", JSON.stringify({ "week-one-slot": 1 }));
    week = "week-two";
    fireEvent.click(screen.getByRole("button", { name: "Reload" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(screen.getByRole("button", { name: /Synthetic Bench/ })).toHaveTextContent("0/3");
    expect(localStorage.getItem("hypertrophy_occurrence_v2:completed:week-two")).toBeNull();
    expect(JSON.parse(localStorage.getItem("hypertrophy_occurrence_v2:swaps:week-two") ?? "{}" )).toEqual({});
    vi.unstubAllGlobals();
  });
});
