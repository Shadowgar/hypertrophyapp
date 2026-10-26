import React from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import WeekPage from "@/app/week/page";

const dates = ["2026-10-26", "2026-10-28"];
const profile = { selected_program_id: "pure_bodybuilding_phase_2_full_body", days_available: 2 };
let reads: number;
let retry: () => Promise<Response>;
let writes: Array<{ path: string; body: Record<string, unknown> }>;

beforeEach(() => {
  localStorage.setItem("hypertrophy_token", "profile-recovery-account-a");
  reads = 0;
  writes = [];
  retry = async () => Response.json(profile);
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path.endsWith("/profile")) {
      reads++;
      return reads === 1 ? Response.json({ detail: "Synthetic profile outage" }, { status: 503 }) : retry();
    }
    if (path.includes("/plan/scheduling-context")) return Response.json({
      week_start: dates[0], local_today: dates[0], timezone: "UTC", placement_revision: 7, selected_dates: dates, plan: null,
    });
    if (path.endsWith("/plan/programs")) return Response.json([{ id: profile.selected_program_id, name: "Full Body Phase 2" }]);
    if (path.includes("/history/calendar")) return Response.json({ days: [] });
    if (init?.method === "POST") writes.push({ path, body: JSON.parse(String(init.body)) });
    return Response.json({ detail: "Synthetic preview unavailable" }, { status: 503 });
  }));
});

test("failed profile read can retry without changing selected dates or activating a schedule", async () => {
  render(<WeekPage />);
  const retryButton = await screen.findByRole("button", { name: "Retry profile loading" });
  expect(screen.getByRole("button", { name: "Preview selected dates" })).toBeDisabled();
  expect(screen.getByRole("checkbox", { name: "Mon, Oct 26" })).toBeChecked();
  fireEvent.click(retryButton);
  await waitFor(() => expect(screen.getByRole("button", { name: "Preview selected dates" })).toBeEnabled());
  expect(screen.getByRole("checkbox", { name: "Wed, Oct 28" })).toBeChecked();
  expect(reads).toBe(2);
  expect(writes).toHaveLength(0);
  fireEvent.click(screen.getByRole("button", { name: "Preview selected dates" }));
  await waitFor(() => expect(writes).toHaveLength(1));
  expect(writes[0]).toEqual({ path: expect.stringMatching(/\/plan\/selected-dates\/preview$/), body: {
    template_id: profile.selected_program_id, week_start: dates[0], selected_dates: dates, timezone: "UTC", expected_placement_revision: 7,
  } });
  await screen.findByText(/Failed to preview selected dates/);
});

test("a failed profile retry stays recoverable and keeps preferences unavailable", async () => {
  retry = async () => Response.json({ detail: "Still unavailable" }, { status: 503 });
  render(<WeekPage />);
  fireEvent.click(await screen.findByRole("button", { name: "Retry profile loading" }));
  await waitFor(() => expect(reads).toBe(2));
  fireEvent.click(await screen.findByRole("button", { name: "Retry profile loading" }));
  await waitFor(() => expect(reads).toBe(3));
  expect(screen.getByRole("button", { name: "Preview selected dates" })).toBeDisabled();
  expect(writes).toHaveLength(0);
});

test("a profile retry response from the retired account cannot enable scheduling", async () => {
  let release: ((response: Response) => void) | undefined;
  retry = () => new Promise(resolve => { release = resolve; });
  render(<WeekPage />);
  fireEvent.click(await screen.findByRole("button", { name: "Retry profile loading" }));
  await waitFor(() => expect(release).toBeDefined());
  localStorage.setItem("hypertrophy_token", "profile-recovery-account-b");
  await act(async () => { release!(Response.json(profile)); });
  expect(screen.getByRole("button", { name: "Preview selected dates" })).toBeDisabled();
  expect(writes).toHaveLength(0);
});
