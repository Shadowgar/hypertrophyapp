import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import TodayPage from "@/app/today/page";

beforeEach(() => {
  // @ts-ignore
  globalThis.fetch = vi.fn();
});

test("Today page loads workout and shows exercises", async () => {
  const workout = {
    session_id: "pure_bodybuilding_phase_1_full_body-day1",
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
        last_set_intensity_technique: "Long-length Partials",
        warm_up_sets: "1",
        working_sets: "3",
        reps: "8-12",
        early_set_rpe: "~9",
        last_set_rpe: "10",
        rest: "~1-2 min",
        substitution_option_1: "Cable Curl",
        substitution_option_2: "DB Curl",
        demo_url: "https://example.com/bayesian-demo",
        video_url: "https://example.com/bayesian-video",
        notes: "Focus on full ROM",
        video: { youtube_url: "https://example.com/bayesian-video" },
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
  expect(screen.getByText(/Early-set RPE: ~9/i)).toBeInTheDocument();
  expect(screen.getByText(/Last-set RPE: 10/i)).toBeInTheDocument();
  expect(screen.getByText(/Technique: Long-length Partials/i)).toBeInTheDocument();
  expect(screen.getByText(/Rest: ~1-2 min/i)).toBeInTheDocument();
  expect(screen.getByText(/Authored substitutions: Cable Curl \/ DB Curl/i)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /Demo link/i })).toHaveAttribute("href", "https://example.com/bayesian-video");
  expect(screen.getByText(/Current context/i)).toBeInTheDocument();
  expect(screen.getByText(/Today follows Arms & Weak Points/i)).toBeInTheDocument();

  const guideLink = screen.getByRole("link", { name: /Bayesian Curl/i });
  expect(guideLink).toHaveAttribute("href", "/guides/pure_bodybuilding_phase_1_full_body/exercise/ex-1");
});

test("Today page can recover by generating week when no workout exists yet", async () => {
  const workout = {
    session_id: "pure_bodybuilding_phase_1_full_body-day1",
    title: "Full Body #1",
    date: new Date().toISOString().slice(0, 10),
    resume: false,
    day_role: "full_body_1",
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
        substitution_candidates: [],
        last_set_intensity_technique: "Long-length Partials",
        warm_up_sets: "1",
        working_sets: "3",
        reps: "8-12",
        early_set_rpe: "~9",
        last_set_rpe: "10",
        rest: "~1-2 min",
        substitution_option_1: null,
        substitution_option_2: null,
        demo_url: null,
        video_url: null,
        notes: "Focus on full ROM",
        video: null,
        slot_role: "weak_point",
      },
    ],
  };

  let todayCalls = 0;
  // @ts-ignore
  globalThis.fetch.mockImplementation((input) => {
    const url = typeof input === "string" ? input : input.url;
    if (url.endsWith("/health")) {
      return Promise.resolve(new Response(JSON.stringify({ status: "ok", date: new Date().toISOString() }), { status: 200 }));
    }
    if (url.endsWith("/weekly-review/status")) {
      return Promise.resolve(new Response(JSON.stringify({ today_is_sunday: false, review_required: false }), { status: 200 }));
    }
    if (url.includes("/soreness")) {
      return Promise.resolve(new Response(JSON.stringify([{ id: "s1", entry_date: "2026-03-03" }]), { status: 200 }));
    }
    if (url.endsWith("/workout/today")) {
      todayCalls += 1;
      if (todayCalls === 1) {
        return Promise.resolve(new Response("not found", { status: 404 }));
      }
      return Promise.resolve(new Response(JSON.stringify(workout), { status: 200 }));
    }
    if (url.endsWith("/plan/generate-week")) {
      return Promise.resolve(new Response(JSON.stringify({ status: "ok" }), { status: 200 }));
    }
    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  render(<TodayPage />);

  fireEvent.click(screen.getByRole("button", { name: /Load Today Workout/i }));

  await waitFor(() => {
    expect(screen.getByText(/No workout available\. Generate week plan first\./i)).toBeInTheDocument();
  });

  fireEvent.click(screen.getByRole("button", { name: /Generate Week and Reload Today/i }));

  await waitFor(() => {
    expect(screen.getAllByText(/Bayesian Curl/i).length).toBeGreaterThan(0);
  });

  expect(globalThis.fetch).toHaveBeenCalledWith(
    expect.stringMatching(/\/plan\/generate-week$/),
    expect.objectContaining({ method: "POST" }),
  );
});
