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
      return Promise.resolve(new Response(JSON.stringify({ status: "ok" }), { status: 200 }));
    }
    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  render(<TodayPage />);

  const loadBtn = screen.getByRole("button", { name: /Load Today Workout/i });
  fireEvent.click(loadBtn);

  await waitFor(() => expect(screen.getByText(/Bench Press/i)).toBeInTheDocument());

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
});
