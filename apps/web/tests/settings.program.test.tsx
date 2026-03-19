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
    selected_program_id: "pure_bodybuilding_phase_1_full_body",
    training_location: "gym",
    equipment_profile: ["dumbbell"],
    days_available: 5,
  };

  // @ts-ignore
  globalThis.fetch.mockImplementation((input, init) => {
    const url = typeof input === "string" ? input : input.url;
    if (url.endsWith("/profile") && (!init || init.method === "GET")) {
      return Promise.resolve(new Response(JSON.stringify(profile), { status: 200 }));
    }
    if (url.endsWith("/plan/programs")) {
      return Promise.resolve(
        new Response(
          JSON.stringify([{ id: "pure_bodybuilding_phase_1_full_body", name: "Pure Bodybuilding - Phase 1 Full Body" }]),
          { status: 200 },
        ),
      );
    }
    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  render(<SettingsPage />);

  await waitFor(() => {
    expect(screen.getByText(/Pure Bodybuilding - Phase 1 Full Body/i)).toBeInTheDocument();
  });
  expect(screen.getByRole("button", { name: /Get Recommendation/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Wipe Current User Data/i })).toBeInTheDocument();
});
