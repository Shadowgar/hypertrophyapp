import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import TodayPage from "@/app/today/page";

beforeEach(() => {
  // @ts-ignore
  globalThis.fetch = vi.fn();
  localStorage.clear();
});

test("substitution modal applies choice, keeps notes visible, and persists selection", async () => {
  const workout = {
    session_id: "sess-sub-1",
    title: "Push Day",
    date: new Date().toISOString().slice(0, 10),
    resume: false,
    exercises: [
      {
        id: "ex-1",
        name: "Bench Press",
        sets: 3,
        rep_range: [8, 12],
        recommended_working_weight: 60,
        substitution_candidates: ["Push-Up"],
        notes: "Keep elbows tucked",
        video: null,
        primary_exercise_id: "bench-1",
      },
    ],
  };

  // @ts-ignore
  globalThis.fetch.mockImplementation((input, init) => {
    const url = typeof input === "string" ? input : input.url;
    if (url.endsWith("/health")) {
      return Promise.resolve(new Response(JSON.stringify({ status: "ok", date: new Date().toISOString() }), { status: 200 }));
    }
    if (url.endsWith("/workout/today")) {
      return Promise.resolve(new Response(JSON.stringify(workout), { status: 200 }));
    }
    if (url.endsWith(`/workout/${encodeURIComponent(workout.session_id)}/progress`)) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            workout_id: workout.session_id,
            completed_total: 0,
            planned_total: 3,
            percent_complete: 0,
            exercises: [{ exercise_id: "ex-1", planned_sets: 3, completed_sets: 0 }],
          }),
          { status: 200 },
        ),
      );
    }
    if (url.includes("/soreness")) {
      return Promise.resolve(new Response(JSON.stringify([{ id: "s1", entry_date: "2026-03-03" }]), { status: 200 }));
    }
    if (url.includes("/log-set") && init?.method === "POST") {
      return Promise.resolve(new Response(JSON.stringify({ status: "ok" }), { status: 200 }));
    }
    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  render(<TodayPage />);

  fireEvent.click(screen.getByRole("button", { name: /Load today's workout/i }));
  await waitFor(() => expect(screen.getAllByText(/Bench Press/i).length).toBeGreaterThan(0));

  fireEvent.click(screen.getByRole("button", { name: /Bench Press/ }));
  await waitFor(() => expect(screen.getByRole("dialog")).toBeInTheDocument());

  fireEvent.click(screen.getByRole("button", { name: /Swap/i }));
  await waitFor(() => expect(screen.getByText(/Choose a substitute/i)).toBeInTheDocument());

  fireEvent.click(screen.getByRole("button", { name: "Push-Up" }));

  await waitFor(() => expect(screen.getAllByText(/^Push-Up$/i).length).toBeGreaterThan(0));

  fireEvent.click(screen.getByRole("button", { name: /Notes/i }));
  await waitFor(() => {
    expect(screen.getAllByText(/Keep elbows tucked/i).length).toBeGreaterThanOrEqual(1);
  });

  const key = `hypertrophy_swap_selection:${workout.session_id}`;
  const saved = JSON.parse(localStorage.getItem(key) || "{}");
  expect(saved["ex-1"]).toBe(1);
});
