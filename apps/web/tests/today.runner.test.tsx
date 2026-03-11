import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import TodayPage from "@/app/today/page";

beforeEach(() => {
  // @ts-ignore
  globalThis.fetch = vi.fn();
});

test("Today page loads workout and shows exercises", async () => {
  const workout = {
    session_id: "ppl_v1-day1",
    title: "Arms & Weak Points",
    date: new Date().toISOString().slice(0, 10),
    resume: false,
    day_role: "weak_point_arms",
    mesocycle: {
      week_index: 1,
      trigger_weeks_base: 6,
      trigger_weeks_effective: 6,
      is_deload_week: false,
      deload_reason: "none",
      authored_week_index: 1,
      authored_week_role: "adaptation",
      authored_sequence_complete: false,
      post_authored_behavior: "in_authored_sequence",
    },
    deload: {
      active: false,
      set_reduction_pct: 0,
      load_reduction_pct: 0,
      reason: "none",
    },
    exercises: [
      {
        id: "ex-1",
        name: "Bayesian Curl",
        sets: 3,
        rep_range: [8, 12],
        recommended_working_weight: 17.5,
        substitution_candidates: ["Cable Curl"],
        notes: "Focus on full ROM",
        video: null,
        slot_role: "weak_point",
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
    if (url.includes("/soreness")) {
      // indicate soreness already logged to skip modal
      return Promise.resolve(new Response(JSON.stringify([{ id: "s1", entry_date: "2026-03-03" }]), { status: 200 }));
    }
    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  render(<TodayPage />);

  const loadBtn = screen.getByRole("button", { name: /Load Today Workout/i });
  fireEvent.click(loadBtn);

  await waitFor(() => expect(screen.getAllByText(/Bayesian Curl/i).length).toBeGreaterThan(0));

  expect(screen.getByText(/Session Intent/i)).toBeInTheDocument();
  expect(screen.getByText(/Authored day: Arms & Weak Points/i)).toBeInTheDocument();
  expect(screen.getByText(/Authored block: Week 1 · Adaptation/i)).toBeInTheDocument();
  expect(screen.getByText(/Weak-point slots planned: 1/i)).toBeInTheDocument();
  expect(screen.getByText(/Lead exercise: Bayesian Curl for 3 sets of 8-12 reps @ 17.5 kg\./i)).toBeInTheDocument();
  expect(screen.getByText(/Between-Set Coach/i)).toBeInTheDocument();
  expect(screen.getByText(/Live lane: Bayesian Curl/i)).toBeInTheDocument();
  expect(screen.getByText(/Start with 8-12 reps @ 17.5 kg\./i)).toBeInTheDocument();
  expect(screen.getByText(/Current context/i)).toBeInTheDocument();
  expect(screen.getByText(/Today follows Arms & Weak Points/i)).toBeInTheDocument();

  const guideLink = screen.getByRole("link", { name: /Bayesian Curl/i });
  expect(guideLink).toHaveAttribute("href", "/guides/ppl_v1/exercise/ex-1");
});
