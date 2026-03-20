import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

const mockedParams = vi.hoisted(() => ({
  value: {} as Record<string, string | undefined>,
}));

vi.mock("next/navigation", () => ({
  useParams: () => mockedParams.value,
}));

import GuidesIndex from "@/app/guides/page";
import ProgramGuidePhaseIndexPage from "@/app/guides/[programId]/page";
import ProgramPhaseGuidePage from "@/app/guides/[programId]/phase/[phaseId]/page";
import ProgramPhaseDayGuidePage from "@/app/guides/[programId]/phase/[phaseId]/day/[dayIndex]/page";

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
  mockedParams.value = {};
  // @ts-ignore
  globalThis.fetch = vi.fn();
});

test("guides index links programs to /guides/{programId}", async () => {
  // @ts-ignore
  globalThis.fetch.mockImplementation((input: RequestInfo | URL) => {
    const url = resolveUrl(input);
    if (url.endsWith("/plan/guides/programs")) {
      return Promise.resolve(
        new Response(
          JSON.stringify([
            {
              id: "pure_bodybuilding_phase_1_full_body",
              name: "Hypertrophy Phase 1",
              split: "full_body",
              description: "Deterministic full-body program",
            },
          ]),
          { status: 200 },
        ),
      );
    }

    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  render(<GuidesIndex />);

  const link = await screen.findByRole("link", { name: /Open guide for Hypertrophy Phase 1/i });
  expect(link).toHaveAttribute("href", "/guides/pure_bodybuilding_phase_1_full_body");
});

test("program guide resolves params and links to phase route", async () => {
  mockedParams.value = { programId: "pure_bodybuilding_phase_1_full_body" };

  // @ts-ignore
  globalThis.fetch.mockImplementation((input: RequestInfo | URL) => {
    const url = resolveUrl(input);
    if (url.endsWith("/plan/guides/programs/pure_bodybuilding_phase_1_full_body")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            id: "pure_bodybuilding_phase_1_full_body",
            name: "Hypertrophy Phase 1",
            split: "full_body",
            description: "Deterministic full-body program",
            days: [
              {
                day_index: 1,
                day_name: "Day 1",
                exercise_count: 5,
                first_exercise_id: "bench_press",
              },
            ],
          }),
          { status: 200 },
        ),
      );
    }

    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  render(<ProgramGuidePhaseIndexPage />);

  await waitFor(() => expect(screen.getByText("Main Phase")).toBeInTheDocument());
  const phaseLink = screen.getByRole("link", { name: /Open phase guide/i });
  expect(phaseLink).toHaveAttribute("href", "/guides/pure_bodybuilding_phase_1_full_body/phase/main");
});

test("phase and day guides preserve phase-aware routing to day and exercise pages", async () => {
  mockedParams.value = { programId: "pure_bodybuilding_phase_1_full_body", phaseId: "main" };

  // @ts-ignore
  globalThis.fetch.mockImplementation((input: RequestInfo | URL) => {
    const url = resolveUrl(input);
    if (url.endsWith("/plan/guides/programs/pure_bodybuilding_phase_1_full_body")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            id: "pure_bodybuilding_phase_1_full_body",
            name: "Hypertrophy Phase 1",
            split: "full_body",
            description: "Deterministic full-body program",
            days: [
              {
                day_index: 1,
                day_name: "Day 1",
                exercise_count: 5,
                first_exercise_id: "bench_press",
              },
            ],
          }),
          { status: 200 },
        ),
      );
    }

    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  const { unmount } = render(<ProgramPhaseGuidePage />);

  await waitFor(() => expect(screen.getByText(/Day 1: Day 1/i)).toBeInTheDocument());
  expect(screen.getByRole("link", { name: /Open day guide/i })).toHaveAttribute(
    "href",
    "/guides/pure_bodybuilding_phase_1_full_body/phase/main/day/1",
  );
  expect(screen.getByRole("link", { name: /Open first exercise/i })).toHaveAttribute(
    "href",
    "/guides/pure_bodybuilding_phase_1_full_body/exercise/bench_press",
  );

  unmount();

  mockedParams.value = { programId: "pure_bodybuilding_phase_1_full_body", phaseId: "main", dayIndex: "1" };

  // @ts-ignore
  globalThis.fetch.mockImplementation((input: RequestInfo | URL) => {
    const url = resolveUrl(input);
    if (url.endsWith("/plan/guides/programs/pure_bodybuilding_phase_1_full_body/days/1")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            program_id: "pure_bodybuilding_phase_1_full_body",
            day_index: 1,
            day_name: "Day 1",
            exercises: [
              {
                id: "slot_1",
                primary_exercise_id: "bench_press",
                name: "Bench Press",
                notes: "Control eccentric",
              },
            ],
          }),
          { status: 200 },
        ),
      );
    }

    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  render(<ProgramPhaseDayGuidePage />);

  await waitFor(() => expect(screen.getByText(/Bench Press/i)).toBeInTheDocument());
  expect(screen.getByText(/Main Phase/i)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /Open exercise guide/i })).toHaveAttribute(
    "href",
    "/guides/pure_bodybuilding_phase_1_full_body/exercise/bench_press",
  );
});
