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

test("Settings coaching panel previews and applies intelligence decisions", async () => {
  const profile = {
    selected_program_id: "full_body_v1",
    training_location: "gym",
    equipment_profile: ["dumbbell"],
    days_available: 5,
  };
  const recommendation = {
    current_program_id: "full_body_v1",
    recommended_program_id: "upper_lower",
    reason: "mesocycle_complete_rotate",
    compatible_program_ids: ["full_body_v1", "upper_lower"],
    generated_at: new Date().toISOString(),
  };
  const programs = [{ id: "full_body_v1", name: "Full Body V1" }, { id: "upper_lower", name: "Upper/Lower" }];
  const preview = {
    recommendation_id: "rec_123",
    template_id: "full_body_v1",
    program_name: "Full Body V1",
    schedule: {
      from_days: 5,
      to_days: 3,
      kept_sessions: ["A", "B", "C"],
      dropped_sessions: ["D", "E"],
      added_sessions: [],
      risk_level: "medium",
      muscle_set_delta: { chest: -1 },
      tradeoffs: ["Higher per-session density"],
    },
    progression: {
      action: "hold",
      load_scale: 1,
      set_delta: 0,
      reason: "maintain_until_stable",
    },
    phase_transition: {
      next_phase: "accumulation",
      reason: "continue_accumulation",
    },
    specialization: {
      focus_muscles: ["biceps"],
      focus_adjustments: { biceps: 2 },
      donor_adjustments: { quads: -1 },
      uncompensated_added_sets: 1,
    },
    media_warmups: {
      total_exercises: 10,
      video_linked_exercises: 2,
      video_coverage_pct: 20,
      sample_warmups: [],
    },
  };

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
    if (url.endsWith("/plan/intelligence/reference-pairs")) {
      return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }));
    }
    if (url.endsWith("/plan/intelligence/coach-preview") && init?.method === "POST") {
      return Promise.resolve(new Response(JSON.stringify(preview), { status: 200 }));
    }
    if (url.endsWith("/plan/intelligence/apply-phase") && init?.method === "POST") {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            status: "applied",
            recommendation_id: "rec_123",
            applied_recommendation_id: "rec_applied_456",
            requires_confirmation: false,
            applied: true,
            next_phase: "accumulation",
            reason: "continue_accumulation",
          }),
          { status: 200 },
        ),
      );
    }

    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  render(<SettingsPage />);

  await waitFor(() => {
    expect(screen.getByRole("button", { name: /Generate coaching preview/i })).toBeInTheDocument();
  });

  fireEvent.click(screen.getByRole("button", { name: /Generate coaching preview/i }));

  await waitFor(() => {
    expect(screen.getByText(/Progression: hold/i)).toBeInTheDocument();
    expect(screen.getByText(/Adaptation Risk: medium/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Recommendation ID: rec_123/i).length).toBeGreaterThan(0);
  });

  fireEvent.click(screen.getByRole("button", { name: /Apply phase decision/i }));

  await waitFor(() => {
    expect(screen.getByText(/Phase: applied/i)).toBeInTheDocument();
  });

  // @ts-ignore
  const fetchCalls = globalThis.fetch.mock.calls as Array<[RequestInfo | URL, RequestInit | undefined]>;
  const phaseApplyCall = fetchCalls.find(
    ([input, init]) => {
      let requestUrl: string;
      if (typeof input === "string") {
        requestUrl = input;
      } else if (input instanceof URL) {
        requestUrl = input.toString();
      } else {
        requestUrl = input.url;
      }
      return requestUrl.endsWith("/plan/intelligence/apply-phase") && init?.method === "POST";
    },
  );
  expect(phaseApplyCall).toBeDefined();
  if (!phaseApplyCall) {
    throw new Error("Expected apply-phase request to be issued");
  }
  const phaseApplyInit = phaseApplyCall[1];
  const rawBody = phaseApplyInit?.body;
  const phaseApplyBody = typeof rawBody === "string" ? JSON.parse(rawBody) : {};
  expect(phaseApplyBody).toMatchObject({
    recommendation_id: "rec_123",
  });
});
