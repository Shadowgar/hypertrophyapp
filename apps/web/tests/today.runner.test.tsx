import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import TodayPage from "@/app/today/page";

beforeEach(() => {
  // @ts-ignore
  globalThis.fetch = vi.fn();
});

test("Today page loads workout and shows exercises", async () => {
  const workout = {
    session_id: "ppl_v1-1",
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
        notes: "Focus on full ROM",
        video: null,
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

  await waitFor(() => expect(screen.getByText(/Bench Press/i)).toBeInTheDocument());
});
