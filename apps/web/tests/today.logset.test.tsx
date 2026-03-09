import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import TodayPage from "@/app/today/page";

beforeEach(() => {
  // @ts-ignore
  globalThis.fetch = vi.fn();
  localStorage.clear();
});

test("Completing a set calls log-set POST and persists completed sets", async () => {
  let completedSets = 0;

  const workout = {
    session_id: "sess-1",
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
        substitution_candidates: [],
        notes: "",
        video: null,
        primary_exercise_id: "bench-1",
      },
    ],
  };

  // capture fetch calls
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
            completed_total: completedSets,
            planned_total: 3,
            percent_complete: Math.floor((completedSets / 3) * 100),
            exercises: [{ exercise_id: "ex-1", planned_sets: 3, completed_sets: completedSets }],
          }),
          { status: 200 },
        ),
      );
    }
    if (url.includes("/soreness")) {
      return Promise.resolve(new Response(JSON.stringify([{ id: "s1", entry_date: "2026-03-03" }]), { status: 200 }));
    }
    if (url.includes("/log-set") && init?.method === "POST") {
      completedSets = 1;
      return Promise.resolve(
        new Response(
          JSON.stringify({
            id: "log-1",
            primary_exercise_id: "bench-1",
            exercise_id: "ex-1",
            set_index: 1,
            reps: 8,
            weight: 60,
            planned_reps_min: 8,
            planned_reps_max: 12,
            planned_weight: 60,
            rep_delta: 0,
            weight_delta: 0,
            next_working_weight: 60,
            guidance: "below_target_reps_reduce_or_hold_load",
            guidance_rationale: "Performance fell below the target range. Hold load on the first miss and only reduce if it repeats across 2 exposures.",
            live_recommendation: {
              completed_sets: 1,
              remaining_sets: 2,
              recommended_reps_min: 8,
              recommended_reps_max: 10,
              recommended_weight: 57.5,
              guidance: "remaining_sets_reduce_load_focus_target_reps",
              guidance_rationale: "Reps dropped below target. Trim load slightly within the session so the remaining sets stay on target.",
            },
            created_at: new Date().toISOString(),
          }),
          { status: 200 },
        ),
      );
    }
    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  render(<TodayPage />);

  const loadBtn = screen.getByRole("button", { name: /Load Today Workout/i });
  fireEvent.click(loadBtn);

  await waitFor(() => expect(screen.getAllByText(/Bench Press/i).length).toBeGreaterThan(0));
  expect(screen.getByText(/Progress:\s*0\/3 sets \(0%\)/i)).toBeInTheDocument();
  expect(screen.getByText(/Live lane: Bench Press/i)).toBeInTheDocument();

  // find Complete Set button within the exercise control
  const completeBtn = screen.getByRole("button", { name: /Complete Set/i });
  fireEvent.click(completeBtn);

  // expect fetch to have been called with log-set POST
  await waitFor(() => {
    // @ts-ignore
    const postCalls = globalThis.fetch.mock.calls.filter((c) => {
      const url = typeof c[0] === "string" ? c[0] : c[0].url;
      return url.includes(`/workout/${encodeURIComponent(workout.session_id)}/log-set`);
    });
    expect(postCalls.length).toBeGreaterThanOrEqual(1);
    const lastCall = postCalls[postCalls.length - 1];
    const body = lastCall[1]?.body;
    expect(body).toBeDefined();
    const parsed = JSON.parse(body);
    expect(parsed.exercise_id).toBe("ex-1");
    expect(parsed.set_index).toBe(1);
  });

  // verify localStorage persisted completed sets for session
  const key = `hypertrophy_completed_sets:${workout.session_id}`;
  const stored = JSON.parse(localStorage.getItem(key) || "{}");
  expect(stored["ex-1"]).toBe(1);

  await waitFor(() => {
    expect(screen.getByText(/Progress:\s*1\/3 sets \(33%\)/i)).toBeInTheDocument();
  });

  expect(screen.getByText(/Bench Press: 1\/3 sets complete\./i)).toBeInTheDocument();
  expect(screen.getAllByText(/Next set target: 8-10 reps @ 57.5 kg/i).length).toBeGreaterThan(0);

  expect(
    screen.getByText(/Performance fell below the target range\. Hold load on the first miss and only reduce if it repeats across 2 exposures\./i),
  ).toBeInTheDocument();
  expect(
    screen.getAllByText(/Reps dropped below target\. Trim load slightly within the session so the remaining sets stay on target\./i).length,
  ).toBeGreaterThan(0);
  expect(screen.queryByText(/below_target_reps_reduce_or_hold_load/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/remaining_sets_reduce_load_focus_target_reps/i)).not.toBeInTheDocument();
});
