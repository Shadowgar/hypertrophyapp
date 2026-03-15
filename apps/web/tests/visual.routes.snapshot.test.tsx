import React from "react";
import { render, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import HomePage from "@/app/page";
import WeekPage from "@/app/week/page";
import SettingsPage from "@/app/settings/page";
import TodayPage from "@/app/today/page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
  }),
  useSearchParams: () => ({
    get: () => null,
  }),
  usePathname: () => "/",
}));

function resolveUrl(input: RequestInfo | URL): string {
  if (typeof input === "string") {
    return input;
  }
  if (input instanceof URL) {
    return input.toString();
  }
  return input.url;
}

beforeEach(() => {
  localStorage.clear();
  // @ts-ignore
  globalThis.fetch = vi.fn();
});

test("visual snapshot: home route", () => {
  const { getByText } = render(<HomePage />);
  expect(getByText(/HyperTrophy Plan/i)).toBeInTheDocument();
  expect(getByText(/Start Onboarding/i)).toBeInTheDocument();
});

test("visual snapshot: week route", async () => {
  // @ts-ignore
  globalThis.fetch.mockImplementation((input: RequestInfo | URL) => {
    const url = resolveUrl(input);

    if (url.endsWith("/plan/programs")) {
      return Promise.resolve(
        new Response(
          JSON.stringify([
            {
              id: "pure_bodybuilding_phase_1_full_body",
              name: "Pure Bodybuilding - Phase 1 Full Body",
              version: "1.0.0",
              split: "full_body",
              days_supported: [3, 4, 5],
            },
          ]),
          { status: 200 },
        ),
      );
    }

    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  const { container, getByLabelText } = render(<WeekPage />);
  await waitFor(() => expect(getByLabelText(/Week program override selector/i)).toBeInTheDocument());
  expect(container.firstChild).toMatchSnapshot();
});

test("visual snapshot: settings route", async () => {
  // @ts-ignore
  globalThis.fetch.mockImplementation((input: RequestInfo | URL) => {
    const url = resolveUrl(input);

    if (url.endsWith("/profile") && !url.includes("recommendation")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            name: "Athlete",
            training_location: "home",
            equipment_profile: ["dumbbell", "bodyweight"],
            days_available: 4,
            selected_program_id: "pure_bodybuilding_phase_1_full_body",
          }),
          { status: 200 },
        ),
      );
    }

    if (url.endsWith("/plan/programs")) {
      return Promise.resolve(
        new Response(
          JSON.stringify([
            {
              id: "pure_bodybuilding_phase_1_full_body",
              name: "Pure Bodybuilding - Phase 1 Full Body",
              version: "1.0.0",
              split: "full_body",
              days_supported: [3, 4, 5],
              description: "Deterministic full-body template",
            },
          ]),
          { status: 200 },
        ),
      );
    }

    if (url.endsWith("/profile/program-recommendation")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            current_program_id: "pure_bodybuilding_phase_1_full_body",
            recommended_program_id: "pure_bodybuilding_phase_1_full_body",
            reason: "current_selection_is_compatible",
            compatible_program_ids: ["pure_bodybuilding_phase_1_full_body"],
            generated_at: "2026-03-05T00:00:00Z",
          }),
          { status: 200 },
        ),
      );
    }

    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  const { getByText, getByRole } = render(<SettingsPage />);
  await waitFor(() => expect(getByText(/Program Settings/i)).toBeInTheDocument());
  expect(getByRole("button", { name: /Wipe Current User Data/i })).toBeInTheDocument();
});

test("visual snapshot: today route initial state", async () => {
  // @ts-ignore
  globalThis.fetch.mockImplementation((input: RequestInfo | URL) => {
    const url = resolveUrl(input);
    if (url.endsWith("/health")) {
      return Promise.resolve(new Response(JSON.stringify({ status: "ok", date: "2026-03-05" }), { status: 200 }));
    }
    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  const { container, getByText } = render(<TodayPage />);
  await waitFor(() => expect(getByText(/Load today's workout/i)).toBeInTheDocument());
  expect(container.firstChild).toMatchSnapshot();
});
