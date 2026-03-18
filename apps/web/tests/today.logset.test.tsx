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

  const loadBtn = screen.getByRole("button", { name: /Load today's workout/i });
  fireEvent.click(loadBtn);

  await waitFor(() => expect(screen.getAllByText(/Bench Press/i).length).toBeGreaterThan(0));

  fireEvent.click(screen.getByRole("button", { name: /Bench Press/ }));
  await waitFor(() => expect(screen.getByRole("dialog")).toBeInTheDocument());

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
    expect(screen.getByText(/1\/3 sets/i)).toBeInTheDocument();
  });

  // Detail overlay shows live_recommendation guidance (rationale) after log-set; no raw codes
  expect(
    screen.getByText(/Reps dropped below target\. Trim load slightly within the session so the remaining sets stay on target\./i),
  ).toBeInTheDocument();
  expect(screen.queryByText(/below_target_reps_reduce_or_hold_load/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/remaining_sets_reduce_load_focus_target_reps/i)).not.toBeInTheDocument();
});

test("Technique checklist auto-opens Coaching and gates last set completion", async () => {
  let completedSets = 0;

  const workout = {
    session_id: "sess-technique-checklist",
    title: "Full Body",
    date: new Date().toISOString().slice(0, 10),
    resume: false,
    exercises: [
      {
        id: "ex-llp",
        name: "Neutral Grip Lat Pulldown",
        sets: 2,
        rep_range: [10, 12],
        recommended_working_weight: 80,
        substitution_candidates: [],
        notes: "Long-length Partials (on all reps of the last set).",
        last_set_intensity_technique: "Long-length Partials (on all reps of the last set)",
        rest: null,
        early_set_rpe: null,
        last_set_rpe: null,
        video: null,
        primary_exercise_id: "pulldown-1",
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
            completed_total: completedSets,
            planned_total: 2,
            percent_complete: Math.floor((completedSets / 2) * 100),
            exercises: [{ exercise_id: "ex-llp", planned_sets: 2, completed_sets: completedSets }],
          }),
          { status: 200 },
        ),
      );
    }
    if (url.includes("/soreness")) {
      return Promise.resolve(new Response(JSON.stringify([{ id: "s1", entry_date: "2026-03-03" }]), { status: 200 }));
    }
    if (url.includes("/log-set") && init?.method === "POST") {
      // advance completion for the working sets
      completedSets = Math.min(2, completedSets + 1);
      return Promise.resolve(
        new Response(
          JSON.stringify({
            id: `log-${completedSets}`,
            primary_exercise_id: "pulldown-1",
            exercise_id: "ex-llp",
            set_index: completedSets,
            reps: 10,
            weight: 80,
            planned_reps_min: 10,
            planned_reps_max: 12,
            planned_weight: 80,
            rep_delta: 0,
            weight_delta: 0,
            next_working_weight: 80,
            guidance: "ok",
            guidance_rationale: "On target.",
            live_recommendation: null,
            created_at: new Date().toISOString(),
          }),
          { status: 200 },
        ),
      );
    }
    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  render(<TodayPage />);
  fireEvent.click(screen.getByRole("button", { name: /Load today's workout/i }));

  await waitFor(() => expect(screen.getAllByText(/Neutral Grip Lat Pulldown/i).length).toBeGreaterThan(0));
  fireEvent.click(screen.getByRole("button", { name: /Neutral Grip Lat Pulldown/i }));
  await waitFor(() => expect(screen.getByRole("dialog")).toBeInTheDocument());

  // Coaching should be auto-open (technique present) and show the technique chip.
  expect(screen.getByText(/Technique: Long-length Partials/i)).toBeInTheDocument();

  // Complete first set.
  fireEvent.click(screen.getByRole("button", { name: /Complete Set/i }));

  // On the last set, the checklist appears inside Coaching and the logger is gated.
  await waitFor(() => expect(screen.getByText(/Technique \(last set\)/i)).toBeInTheDocument());
  expect(screen.getByRole("button", { name: /Complete technique steps first/i })).toBeInTheDocument();

  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(screen.getByRole("button", { name: /Complete Set/i }));

  await waitFor(() => {
    expect(screen.getByText(/2\/2 sets/i)).toBeInTheDocument();
  });
});

test("Technique inline panel logs technique sub-sets with set_kind and parent_set_index", async () => {
  let completedSets = 0;

  const workout = {
    session_id: "sess-technique-inline",
    title: "Pull",
    date: new Date().toISOString().slice(0, 10),
    resume: false,
    exercises: [
      {
        id: "ex-mech",
        name: "Cable Reverse Fly",
        sets: 1,
        rep_range: [12, 15],
        recommended_working_weight: 55,
        substitution_candidates: [],
        notes: "",
        last_set_intensity_technique: "Mechanical dropset",
        rest: null,
        early_set_rpe: null,
        last_set_rpe: null,
        video: null,
        primary_exercise_id: "revfly-1",
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
            completed_total: completedSets,
            planned_total: 1,
            percent_complete: Math.floor((completedSets / 1) * 100),
            exercises: [{ exercise_id: "ex-mech", planned_sets: 1, completed_sets: completedSets }],
          }),
          { status: 200 },
        ),
      );
    }
    if (url.includes("/soreness")) {
      return Promise.resolve(new Response(JSON.stringify([{ id: "s1", entry_date: "2026-03-03" }]), { status: 200 }));
    }
    if (url.includes("/log-set") && init?.method === "POST") {
      const body = init.body ? JSON.parse(String(init.body)) : {};
      // only advance completion for working sets (technique sub-sets shouldn't affect completion)
      if (!body.parent_set_index && !body.set_kind) {
        completedSets = 1;
      }
      return Promise.resolve(
        new Response(
          JSON.stringify({
            id: "log-1",
            primary_exercise_id: "revfly-1",
            exercise_id: "ex-mech",
            set_index: 1,
            reps: body.reps ?? 12,
            weight: body.weight ?? 55,
            planned_reps_min: 12,
            planned_reps_max: 15,
            planned_weight: 55,
            rep_delta: 0,
            weight_delta: 0,
            next_working_weight: 55,
            guidance: "ok",
            guidance_rationale: "On target.",
            live_recommendation: null,
            created_at: new Date().toISOString(),
            set_kind: body.set_kind ?? null,
            parent_set_index: body.parent_set_index ?? null,
            technique: body.technique ?? null,
          }),
          { status: 200 },
        ),
      );
    }
    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  render(<TodayPage />);
  fireEvent.click(screen.getByRole("button", { name: /Load today's workout/i }));

  await waitFor(() => expect(screen.getAllByText(/Cable Reverse Fly/i).length).toBeGreaterThan(0));
  fireEvent.click(screen.getByRole("button", { name: /Cable Reverse Fly/i }));
  await waitFor(() => expect(screen.getByRole("dialog")).toBeInTheDocument());

  fireEvent.click(screen.getByRole("button", { name: /Complete Set/i }));

  // Inline technique panel should appear inside Coaching.
  await waitFor(() => expect(screen.getByText(/Mechanical drop set/i)).toBeInTheDocument());
  fireEvent.click(screen.getByRole("button", { name: /Log technique set #1/i }));

  await waitFor(() => {
    // @ts-ignore
    const postCalls = globalThis.fetch.mock.calls.filter((c) => {
      const url = typeof c[0] === "string" ? c[0] : c[0].url;
      return url.includes(`/workout/${encodeURIComponent(workout.session_id)}/log-set`);
    });
    expect(postCalls.length).toBeGreaterThanOrEqual(2);
    const lastCall = postCalls[postCalls.length - 1];
    const body = JSON.parse(lastCall[1]?.body);
    expect(body.set_kind).toBe("mechanical_drop");
    expect(body.parent_set_index).toBe(1);
    expect(body.technique?.type).toBe("mechanical_drop");
    expect(body.technique?.ordinal).toBe(1);
  });
});
