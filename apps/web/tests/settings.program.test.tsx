import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
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

test("Settings page shows selected program and saves changes", async () => {
  const profile = { selected_program_id: "full_body_v1", training_location: "gym", equipment_profile: ["dumbbell"], days_available: 5 };
  const recommendation = {
    current_program_id: "full_body_v1",
    recommended_program_id: "upper_lower",
    reason: "mesocycle_complete_rotate",
    compatible_program_ids: ["full_body_v1", "upper_lower"],
    generated_at: new Date().toISOString(),
  };
  const programs = [{ id: "full_body_v1", name: "Full Body V1" }, { id: "upper_lower", name: "Upper/Lower" }];

  // @ts-ignore
  globalThis.fetch.mockImplementation((input, init) => {
    const url = typeof input === "string" ? input : input.url;
    if (url.endsWith("/profile") && (!init || init.method === "GET")) {
      return Promise.resolve(new Response(JSON.stringify(profile), { status: 200 }));
    }
    if (url.endsWith("/plan/programs")) {
      return Promise.resolve(new Response(JSON.stringify(programs), { status: 200 }));
    }
    if (url.endsWith("/profile/program-recommendation")) {
      return Promise.resolve(new Response(JSON.stringify(recommendation), { status: 200 }));
    }
    if (url.endsWith("/profile/program-switch") && init?.method === "POST") {
      const payload = init.body ? JSON.parse(init.body as string) : {};
      if (!payload.confirm) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              status: "confirmation_required",
              current_program_id: "full_body_v1",
              target_program_id: payload.target_program_id,
              recommended_program_id: "upper_lower",
              reason: "mesocycle_complete_rotate",
              requires_confirmation: true,
              applied: false,
            }),
            { status: 200 },
          ),
        );
      }
      return Promise.resolve(
        new Response(
          JSON.stringify({
            status: "switched",
            current_program_id: "full_body_v1",
            target_program_id: payload.target_program_id,
            recommended_program_id: "upper_lower",
            reason: "mesocycle_complete_rotate",
            requires_confirmation: false,
            applied: true,
          }),
          { status: 200 },
        ),
      );
    }
    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  render(<SettingsPage />);

  await waitFor(() => {
    expect(screen.getByLabelText(/Settings program selector/i)).toBeInTheDocument();
  });

  // change program
  const select = screen.getByLabelText(/Settings program selector/i);
  fireEvent.change(select, { target: { value: "upper_lower" } });

  const save = screen.getByRole("button", { name: /Save selected program/i });
  fireEvent.click(save);

  await waitFor(() => {
    expect(screen.getByText(/Confirm program switch/i)).toBeInTheDocument();
  });

  const confirm = screen.getByRole("button", { name: /Confirm program switch/i });
  fireEvent.click(confirm);

  await waitFor(() => {
    expect(screen.getByText(/Program switched/i)).toBeInTheDocument();
  });
});
