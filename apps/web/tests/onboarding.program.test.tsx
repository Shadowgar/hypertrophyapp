import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import OnboardingPage from "@/app/onboarding/page";

const ONBOARDING_DRAFT_KEY = "hypertrophy_onboarding_draft_v1";

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
  }),
}));

beforeEach(() => {
  // reset fetch mock
  // @ts-ignore
  globalThis.fetch = vi.fn();
  localStorage.clear();
});

async function completeQuestionnaireToAccountStep() {
  fireEvent.click(screen.getByRole("button", { name: /next slide/i }));
  fireEvent.click(screen.getByRole("button", { name: /next slide/i }));
  fireEvent.click(screen.getByRole("button", { name: /get started/i }));

  fireEvent.click(screen.getByRole("button", { name: /^male$/i }));
  fireEvent.click(screen.getByRole("button", { name: /^next$/i }));

  fireEvent.click(screen.getByRole("button", { name: /build muscle/i }));
  fireEvent.click(screen.getByRole("button", { name: /^next$/i }));

  fireEvent.click(screen.getByRole("button", { name: /^next$/i })); // height
  fireEvent.click(screen.getByRole("button", { name: /^next$/i })); // weight

  fireEvent.change(screen.getByLabelText(/birthday/i), { target: { value: "1990-01-01" } });
  fireEvent.click(screen.getByRole("button", { name: /^next$/i }));

  fireEvent.click(screen.getByRole("button", { name: /getting started/i }));
  fireEvent.click(screen.getByRole("button", { name: /^next$/i }));

  for (let index = 0; index < 8; index += 1) {
    fireEvent.click(screen.getByRole("button", { name: /skip/i }));
  }

  await waitFor(() => {
    expect(screen.getByLabelText(/first name/i)).toBeInTheDocument();
  });
  fireEvent.change(screen.getByLabelText(/first name/i), { target: { value: "Rocco" } });
  fireEvent.click(screen.getByRole("button", { name: /^next$/i }));
}

test("Onboarding wizard reaches account step with program catalog and password toggle", async () => {
  const programs = [
    {
      id: "pure_bodybuilding_phase_1_full_body",
      name: "Pure Bodybuilding - Phase 1 Full Body",
      description: "A 5-day full body",
    },
    { id: "upper_lower", name: "Upper/Lower", description: "4 day" },
  ];

  // mock /plan/programs
  // @ts-ignore
  globalThis.fetch.mockImplementation((input, init) => {
    if (typeof input === "string" && input.endsWith("/plan/programs")) {
      return Promise.resolve(new Response(JSON.stringify(programs), { status: 200 }));
    }
    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  render(<OnboardingPage />);

  await waitFor(() => {
    expect(screen.getByRole("button", { name: /next slide/i })).toBeInTheDocument();
  });

  await completeQuestionnaireToAccountStep();

  await waitFor(() => {
    expect(screen.getByLabelText(/program/i)).toBeInTheDocument();
  });

  expect(screen.getByText("Pure Bodybuilding - Phase 1 Full Body")).toBeInTheDocument();

  const password = screen.getByLabelText(/Password/i);
  expect(password).toHaveAttribute("type", "password");
  fireEvent.click(screen.getByRole("button", { name: /show password/i }));
  expect(password).toHaveAttribute("type", "text");
});

test("Onboarding restores saved draft progress from local storage", async () => {
  const programs = [
    {
      id: "pure_bodybuilding_phase_1_full_body",
      name: "Pure Bodybuilding - Phase 1 Full Body",
      description: "A 5-day full body",
    },
  ];

  localStorage.setItem(
    ONBOARDING_DRAFT_KEY,
    JSON.stringify({
      phase: "account",
      authMode: "login",
      introIndex: 2,
      questionIndex: 14,
      gender: "male",
      primaryGoal: "build_muscle",
      heightUnit: "in",
      heightFeet: "5",
      heightInches: "10",
      heightCm: "178",
      weightUnit: "lbs",
      weightValue: "185",
      birthday: "1990-01-01",
      trainingAgeBucket: "1_2_years",
      strengthFrequency: "3_4_per_week",
      motivationDriver: "self_motivated",
      obstacle: "not_enough_time",
      trainingLocation: "gym",
      gymSetup: "rack_dumbbells_machines_cables",
      experienceLevel: "intermediate",
      workoutDurationMinutes: 45,
      daysAvailable: 4,
      firstName: "Rocco",
      lastName: "Tester",
      email: "restored@example.com",
      weakAreasRaw: "chest",
      selectedProgramId: "pure_bodybuilding_phase_1_full_body",
    }),
  );

  // @ts-ignore
  globalThis.fetch.mockImplementation((input, _init) => {
    if (typeof input === "string" && input.endsWith("/plan/programs")) {
      return Promise.resolve(new Response(JSON.stringify(programs), { status: 200 }));
    }
    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  render(<OnboardingPage />);

  await waitFor(() => {
    expect(screen.getByDisplayValue("restored@example.com")).toBeInTheDocument();
  });

  expect(screen.getByText(/Recovered saved onboarding draft/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Clear Saved Draft/i })).toBeInTheDocument();
});

test("Developer reset control calls canonical phase1 reset endpoint", async () => {
  const programs = [
    {
      id: "pure_bodybuilding_phase_1_full_body",
      name: "Pure Bodybuilding - Phase 1 Full Body",
      description: "A 5-day full body",
    },
  ];

  const originalConfirm = globalThis.confirm;
  // @ts-ignore
  globalThis.confirm = vi.fn(() => true);

  // @ts-ignore
  globalThis.fetch.mockImplementation((input, _init) => {
    if (typeof input === "string" && input.endsWith("/plan/programs")) {
      return Promise.resolve(new Response(JSON.stringify(programs), { status: 200 }));
    }
    if (typeof input === "string" && input.endsWith("/profile/dev/reset-phase1")) {
      return Promise.resolve(new Response(JSON.stringify({ status: "reset_to_phase1" }), { status: 200 }));
    }
    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  render(<OnboardingPage />);

  await waitFor(() => {
    expect(screen.getByRole("button", { name: /Reset Current User to Clean Phase 1/i })).toBeInTheDocument();
  });

  fireEvent.click(screen.getByRole("button", { name: /Reset Current User to Clean Phase 1/i }));

  await waitFor(() => {
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringMatching(/\/profile\/dev\/reset-phase1$/),
      expect.any(Object),
    );
  });

  globalThis.confirm = originalConfirm;
});
