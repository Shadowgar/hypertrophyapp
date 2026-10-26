import React from "react";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import ProgramsPage from "@/app/programs/page";
import { setAuthToken } from "@/lib/api";

const phase1 = { id: "pure_bodybuilding_phase_1_full_body", name: "Hypertrophy Phase 1", days_supported: [2, 3, 4, 5] };
const phase2 = { id: "pure_bodybuilding_phase_2_full_body", name: "Hypertrophy Phase 2", days_supported: [2, 3, 4, 5] };
const catalog = [phase1, phase2, { id: "full_body_v1", name: "Make me a plan", days_supported: [2, 3, 4, 5] }];
const profile = { selected_program_id: phase1.id, effective_program_id: phase2.id, program_selection_mode: "manual", scheduling_timezone: "America/New_York" };
const schedule = { week_start: "2026-10-26", timezone: "America/New_York", selected_dates: ["2026-10-27"], plan: { program_template_id: phase2.id } };
function response(value: unknown, status = 200) { return new Response(JSON.stringify(value), { status }); }
function deferred() {
  let resolve!: (value: Response) => void;
  const promise = new Promise<Response>((done) => { resolve = done; });
  return { promise, resolve };
}
function routes(overrides: Record<string, () => Promise<Response>> = {}) {
  vi.mocked(fetch).mockImplementation((input) => {
    const path = String(input).replace(/^.*\/api/, "").split("?")[0];
    if (overrides[path]) return overrides[path]();
    const values: Record<string, unknown> = { "/plan/programs": catalog, "/profile": profile, "/plan/scheduling-context": schedule };
    if (!(path in values)) throw new Error(`Unexpected read: ${path}`);
    return Promise.resolve(response(values[path]));
  });
}
beforeEach(() => { localStorage.clear(); localStorage.setItem("hypertrophy_token", "account-a"); vi.stubGlobal("fetch", vi.fn()); routes(); });
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

test("unauthenticated catalog requests sign-in without reading account data", () => {
  localStorage.clear(); render(<ProgramsPage />);
  expect(screen.getByRole("link", { name: /sign in/i })).toHaveAttribute("href", "/login?next=%2Fprograms");
  expect(fetch).not.toHaveBeenCalled();
});

test("actual catalog admits separate authored phases and one explicit Customized entry without writes", async () => {
  render(<ProgramsPage />);
  expect(await screen.findByRole("link", { name: "View Full Body Phase 1 guide" })).toHaveAttribute("href", `/programs/${phase1.id}`);
  expect(screen.getByRole("link", { name: "View Full Body Phase 2 guide" })).toHaveAttribute("href", `/programs/${phase2.id}`);
  expect(screen.getByRole("link", { name: /review customized options/i })).toHaveAttribute("href", "/customize");
  expect(screen.getByRole("link", { name: /choose dates in week/i })).toHaveAttribute("href", "/week");
  expect(screen.queryByText("Make me a plan")).not.toBeInTheDocument();
  expect(screen.getAllByRole("link").every((link) => !link.getAttribute("href")?.includes("full_body_v1"))).toBe(true);
  await waitFor(() => expect(screen.getByRole("region", { name: "This week’s schedule" })).toHaveTextContent("Full Body Phase 2"));
  expect(vi.mocked(fetch).mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true);
});

test("stored preference and the actual scheduled program are separate", async () => {
  render(<ProgramsPage />);
  await waitFor(() => expect(screen.getByRole("region", { name: "Saved preference" })).toHaveTextContent("Full Body Phase 1"));
  expect(screen.getByRole("region", { name: "This week’s schedule" })).toHaveTextContent("Full Body Phase 2");
});

test("slow profile does not block catalog discovery or imply an empty schedule", async () => {
  const pending = deferred(); routes({ "/profile": () => pending.promise }); render(<ProgramsPage />);
  expect(await screen.findByRole("link", { name: "View Full Body Phase 1 guide" })).toBeVisible();
  expect(screen.getByRole("region", { name: "This week’s schedule" })).toHaveTextContent(/loading/i);
  expect(screen.queryByText(/no dated schedule/i)).not.toBeInTheDocument();
});

test("an acknowledged empty catalog never invents available Authored programs", async () => {
  routes({ "/plan/programs": async () => response([]) }); render(<ProgramsPage />);
  expect(await screen.findByText(/no authored programs are currently listed/i)).toBeVisible();
  expect(screen.queryByRole("link", { name: /view full body phase/i })).not.toBeInTheDocument();
});

test("one missing phase and unknown legacy entries are not silently advertised", async () => {
  routes({ "/plan/programs": async () => response([phase1, { id: "unknown_program", name: "Other" }]) }); render(<ProgramsPage />);
  expect(await screen.findByRole("link", { name: "View Full Body Phase 1 guide" })).toBeVisible();
  expect(screen.queryByRole("link", { name: "View Full Body Phase 2 guide" })).not.toBeInTheDocument();
  expect(screen.queryByText("Other")).not.toBeInTheDocument();
});

test("catalog failure is distinct from empty and retry preserves a usable focused control", async () => {
  let attempt = 0; routes({ "/plan/programs": async () => ++attempt === 1 ? response({ detail: "private diagnostic" }, 503) : response(catalog) });
  render(<ProgramsPage />);
  const retry = await screen.findByRole("button", { name: /retry programs/i }); retry.focus(); fireEvent.click(retry);
  expect(await screen.findByRole("link", { name: "View Full Body Phase 1 guide" })).toBeVisible();
  expect(screen.getByRole("button", { name: /refresh programs/i })).toHaveFocus();
  expect(screen.queryByText(/private diagnostic|no authored programs/i)).not.toBeInTheDocument();
});

test("failed schedule read is unknown even when profile has an effective program fallback", async () => {
  routes({ "/plan/scheduling-context": async () => response({ detail: "failure" }, 500) }); render(<ProgramsPage />);
  const region = screen.getByRole("region", { name: "This week’s schedule" });
  await waitFor(() => expect(region).toHaveTextContent(/could not load/i));
  expect(region).not.toHaveTextContent(/Full Body Phase 2|no dated schedule/i);
});

test("acknowledged absence of a dated schedule keeps Auto as a stored preference", async () => {
  routes({ "/profile": async () => response({ ...profile, selected_program_id: null, program_selection_mode: "auto" }), "/plan/scheduling-context": async () => response({ ...schedule, plan: null }) }); render(<ProgramsPage />);
  await waitFor(() => expect(screen.getByRole("region", { name: "Saved preference" })).toHaveTextContent("Choose For Me"));
  await waitFor(() => expect(screen.getByRole("region", { name: "This week’s schedule" })).toHaveTextContent(/no dated schedule/i));
});

test("profile failure does not hide the catalog or invent an account selection", async () => {
  routes({ "/profile": async () => response({ detail: "failure" }, 500) }); render(<ProgramsPage />);
  expect(await screen.findByRole("link", { name: "View Full Body Phase 1 guide" })).toBeVisible();
  await waitFor(() => expect(screen.getByRole("region", { name: "Saved preference" })).toHaveTextContent(/could not load/i));
});

test("current-account 401 clears displayed account data and offers sign-in", async () => {
  routes({ "/profile": async () => response({ detail: "Expired" }, 401) }); render(<ProgramsPage />);
  expect(await screen.findByRole("link", { name: /sign in/i })).toBeVisible();
  expect(screen.queryByText("Full Body Phase 2")).not.toBeInTheDocument();
});

test("late previous-account profile and 401 cannot overwrite the new account", async () => {
  const oldProfile = deferred(); let profileRead = 0;
  routes({ "/profile": () => ++profileRead === 1 ? oldProfile.promise : Promise.resolve(response({ ...profile, selected_program_id: phase2.id })) });
  render(<ProgramsPage />);
  await screen.findByRole("link", { name: "View Full Body Phase 1 guide" });
  await act(async () => { setAuthToken("account-b"); });
  await waitFor(() => expect(screen.getByRole("region", { name: "Saved preference" })).toHaveTextContent("Full Body Phase 2"));
  await act(async () => { oldProfile.resolve(response({ detail: "expired old account" }, 401)); });
  expect(localStorage.getItem("hypertrophy_token")).toBe("account-b");
  expect(screen.getByRole("region", { name: "Saved preference" })).toHaveTextContent("Full Body Phase 2");
});

test("late catalog from the prior account cannot restore retired availability", async () => {
  const oldCatalog = deferred(); let reads = 0;
  routes({ "/plan/programs": () => ++reads === 1 ? oldCatalog.promise : Promise.resolve(response([phase2])) }); render(<ProgramsPage />);
  await act(async () => { setAuthToken("account-b"); });
  expect(await screen.findByRole("link", { name: "View Full Body Phase 2 guide" })).toBeVisible();
  await act(async () => { oldCatalog.resolve(response([phase1])); });
  expect(screen.queryByRole("link", { name: "View Full Body Phase 1 guide" })).not.toBeInTheDocument();
});
