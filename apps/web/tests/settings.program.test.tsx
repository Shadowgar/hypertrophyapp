import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import SettingsPage from "@/app/settings/page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
  }),
}));

beforeEach(() => {
  // @ts-ignore
  globalThis.fetch = vi.fn();
});

test("Settings page shows active program and config in one-program-first mode", async () => {
  const profile = {
    email: "generated@example.com",
    name: "Generated User",
    age: 31,
    weight: 82,
    gender: "male",
    split_preference: "full_body",
    selected_program_id: "full_body_v1",
    program_selection_mode: "manual",
    training_location: "gym",
    equipment_profile: ["dumbbell", "cable"],
    weak_areas: ["chest"],
    onboarding_answers: {},
    days_available: 5,
    nutrition_phase: "maintenance",
    calories: 2600,
    protein: 180,
    fat: 70,
    carbs: 280,
  };

  // @ts-ignore
  globalThis.fetch.mockImplementation((input, init) => {
    const url = typeof input === "string" ? input : input.url;
    if (url.endsWith("/profile") && (!init || !init.method || init.method === "GET")) {
      return Promise.resolve(new Response(JSON.stringify(profile), { status: 200 }));
    }
    if (url.endsWith("/plan/programs")) {
      return Promise.resolve(
        new Response(
          JSON.stringify([
            { id: "pure_bodybuilding_phase_1_full_body", name: "Full Body Phase 1" },
            { id: "pure_bodybuilding_phase_2_full_body", name: "Full Body Phase 2" },
            { id: "full_body_v1", name: "Make me a plan" },
          ]),
          { status: 200 },
        ),
      );
    }
    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  render(<SettingsPage />);

  await waitFor(() => {
    expect(screen.getByText(/Make me a plan/i)).toBeInTheDocument();
  });
  expect(screen.getByRole("link", { name: /Update generated plan preferences/i })).toHaveAttribute("href", "/generated-onboarding");
  expect(screen.getByRole("button", { name: /Get Recommendation/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Wipe Current User Data/i })).toBeInTheDocument();
});
