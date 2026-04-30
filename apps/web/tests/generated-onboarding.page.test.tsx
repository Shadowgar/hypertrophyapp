import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import GeneratedOnboardingPage from "@/app/generated-onboarding/page";

beforeEach(() => {
  // @ts-ignore
  globalThis.fetch = vi.fn();
});

test("Generated onboarding page loads persisted state and saves without generating a week", async () => {
  // @ts-ignore
  globalThis.fetch.mockImplementation((input, init) => {
    const url = typeof input === "string" ? input : input.url;
    if (url.endsWith("/profile/generated-onboarding") && (!init?.method || init.method === "GET")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            generated_onboarding: {
              goal_mode: "hypertrophy",
              target_days: 3,
              session_time_band_source: "50_70",
              training_status: "normal",
              trained_consistently_last_4_weeks: true,
              equipment_pool: ["barbell", "bench", "dumbbell", "cable", "machine"],
              movement_restrictions: ["none"],
              recovery_modifier: "normal",
              weakpoint_targets: ["chest"],
              preference_bias: "mixed",
              height_cm: null,
              bodyweight_kg: null,
              bodyweight_exercise_comfort: "mixed",
              disliked_tags: { disliked_exercises: [], disliked_equipment: [] },
            },
            generated_onboarding_version: "v1",
            generated_onboarding_completed_at: null,
            generated_onboarding_complete: false,
            missing_fields: ["weakpoint_targets"],
            profile_completeness: "medium",
          }),
          { status: 200 },
        ),
      );
    }
    if (url.endsWith("/profile/generated-onboarding") && init?.method === "POST") {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            generated_onboarding: JSON.parse(String(init.body)).generated_onboarding,
            generated_onboarding_version: "v1",
            generated_onboarding_completed_at: "2026-04-30T12:00:00Z",
            generated_onboarding_complete: true,
            missing_fields: [],
            profile_completeness: "high",
          }),
          { status: 200 },
        ),
      );
    }
    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  render(<GeneratedOnboardingPage />);

  await waitFor(() => {
    expect(screen.getByText(/Generated onboarding recommended/i)).toBeInTheDocument();
  });

  fireEvent.click(screen.getByRole("button", { name: /^arms$/i }));
  fireEvent.click(screen.getByRole("button", { name: /Save generated onboarding/i }));

  await waitFor(() => {
    expect(screen.getByText(/saved and marked complete/i)).toBeInTheDocument();
  });

  // @ts-ignore
  const postCalls = globalThis.fetch.mock.calls.filter((entry) => {
    const url = typeof entry[0] === "string" ? entry[0] : entry[0].url;
    const method = entry[1]?.method ?? "GET";
    return url.endsWith("/profile/generated-onboarding") && method === "POST";
  });
  expect(postCalls.length).toBe(1);

  // @ts-ignore
  const generateCalls = globalThis.fetch.mock.calls.filter((entry) => {
    const url = typeof entry[0] === "string" ? entry[0] : entry[0].url;
    return url.endsWith("/plan/generate-week");
  });
  expect(generateCalls.length).toBe(0);
});

test("Generated onboarding blocks invalid full_gym equipment tag and caps weakpoints", async () => {
  // @ts-ignore
  globalThis.fetch.mockImplementation((input, init) => {
    const url = typeof input === "string" ? input : input.url;
    if (url.endsWith("/profile/generated-onboarding") && (!init?.method || init.method === "GET")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            generated_onboarding: {
              goal_mode: "hypertrophy",
              target_days: 3,
              session_time_band_source: "50_70",
              training_status: "normal",
              trained_consistently_last_4_weeks: true,
              equipment_pool: ["barbell", "full_gym"],
              movement_restrictions: ["none"],
              recovery_modifier: "normal",
              weakpoint_targets: [],
              preference_bias: "mixed",
              height_cm: null,
              bodyweight_kg: null,
              bodyweight_exercise_comfort: "mixed",
              disliked_tags: { disliked_exercises: [], disliked_equipment: [] },
            },
            generated_onboarding_version: "v1",
            generated_onboarding_completed_at: null,
            generated_onboarding_complete: false,
            missing_fields: [],
            profile_completeness: "high",
          }),
          { status: 200 },
        ),
      );
    }
    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  render(<GeneratedOnboardingPage />);

  await waitFor(() => {
    expect(screen.getByRole("button", { name: /Save generated onboarding/i })).toBeInTheDocument();
  });

  await waitFor(() => {
    expect(screen.getByText(/'full_gym' is not allowed/i)).toBeInTheDocument();
  });
  expect(screen.getByRole("button", { name: /Save generated onboarding/i })).toBeDisabled();

  fireEvent.click(screen.getByRole("button", { name: /^chest$/i }));
  fireEvent.click(screen.getByRole("button", { name: /^arms$/i }));
  fireEvent.click(screen.getByRole("button", { name: /^back$/i }));
  expect(screen.getByRole("button", { name: /^back$/i })).not.toHaveClass("border-red-400");
});
