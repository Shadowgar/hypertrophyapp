import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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

test("Settings displays the effective program while saving stored preferences", async () => {
  const profile = {
    email: "synthetic@example.com", name: "Synthetic", age: 30, weight: 80, gender: "male",
    split_preference: "full_body", selected_program_id: null, program_selection_mode: "auto",
    effective_program_id: "pure_bodybuilding_phase_2_full_body", effective_days_available: 2,
    training_location: "gym", equipment_profile: ["dumbbell"], weak_areas: [], onboarding_answers: {},
    days_available: 5, nutrition_phase: "maintenance", calories: 2600, protein: 180, fat: 70, carbs: 280,
  };
  let saved: Record<string, unknown> | undefined;
  vi.mocked(globalThis.fetch).mockImplementation(async (input, init) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    if (url.endsWith("/profile")) {
      if (init?.method === "POST") saved = JSON.parse(String(init.body));
      return Response.json(profile);
    }
    return Response.json({ detail: "Unavailable synthetic optional capability" }, { status: 403 });
  });
  render(<SettingsPage />);
  await screen.findByText("Full Body Phase 2");
  fireEvent.change(screen.getByLabelText("Training location"), { target: { value: "home" } });
  fireEvent.click(screen.getByRole("button", { name: /Save training settings/i }));
  await waitFor(() => expect(saved).toMatchObject({ days_available: 5, selected_program_id: null, program_selection_mode: "auto", training_location: "home" }));
  expect(saved).not.toHaveProperty("effective_days_available");
  expect(saved).not.toHaveProperty("effective_program_id");
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
    if (url.endsWith("/plan/generated-training-profile/debug")) {
      return Promise.resolve(new Response(JSON.stringify({ detail: "Debug endpoints disabled" }), { status: 403 }));
    }
    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  render(<SettingsPage />);

  await waitFor(() => {
    expect(screen.getByText("Customize My Workout")).toBeInTheDocument();
  });
  expect(screen.getByRole("link", { name: /Update generated plan preferences/i })).toHaveAttribute("href", "/customize");
  // Opening preferences must not create or accept a Customized plan.
  expect(vi.mocked(globalThis.fetch).mock.calls.filter(([, init]) => (init?.method ?? "GET") !== "GET")).toHaveLength(0);
  expect(screen.getByRole("button", { name: /Get Recommendation/i })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /Wipe Current User Data/i })).not.toBeInTheDocument();
});

test("Settings page shows wipe action when dev capability is enabled", async () => {
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
      return Promise.resolve(new Response(JSON.stringify([{ id: "full_body_v1", name: "Make me a plan" }]), { status: 200 }));
    }
    if (url.endsWith("/plan/generated-training-profile/debug")) {
      return Promise.resolve(new Response(JSON.stringify({ selected_program_id: "full_body_v1" }), { status: 200 }));
    }
    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  render(<SettingsPage />);
  await waitFor(() => {
    expect(screen.getByText("Customize My Workout")).toBeInTheDocument();
  });
  expect(screen.getByRole("button", { name: /Wipe Current User Data/i })).toBeInTheDocument();
});
