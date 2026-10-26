import React from "react";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import SettingsPage from "@/app/settings/page";
import { setAuthToken } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn(), replace: vi.fn() }) }));

const token = (account: string) => `a.${btoa(JSON.stringify({ sub: account }))}.c`;
const profile = {
  email: "settings@example.com", name: "Settings owner", age: 30, weight: 80, gender: "male",
  split_preference: "full_body", selected_program_id: null, effective_program_id: null,
  program_selection_mode: "auto", days_available: 3, training_location: "gym",
  equipment_profile: ["dumbbell"], weak_areas: [], onboarding_answers: {},
  nutrition_phase: null, calories: null, protein: null, fat: null, carbs: null,
};
const unavailable = () => Response.json({ detail: "Optional capability unavailable" }, { status: 403 });
const urlOf = (input: RequestInfo | URL) => typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
function deferred() {
  let resolve!: (response: Response) => void;
  const promise = new Promise<Response>((done) => { resolve = done; });
  return { promise, resolve };
}

beforeEach(() => {
  localStorage.clear();
  setAuthToken(token("first"));
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => urlOf(input).endsWith("/profile") ? Response.json(profile) : unavailable()));
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

test("Auto without an effective or selected program cannot display or preview an invented Phase 1", async () => {
  render(<SettingsPage />);
  expect(screen.queryByText("Full Body Phase 1")).not.toBeInTheDocument();
  await screen.findByText("No active program");
  fireEvent.click(screen.getByRole("button", { name: /Coaching Preview/i }));
  expect(screen.getByRole("button", { name: /Generate coaching preview/i })).toBeDisabled();
  expect(vi.mocked(fetch).mock.calls.every(([, init]) => (init?.method ?? "GET") === "GET")).toBe(true);
});

test("a failed profile load exposes retry and cannot submit guessed training defaults", async () => {
  let loads = 0;
  vi.mocked(fetch).mockImplementation(async (input) => {
    if (!urlOf(input).endsWith("/profile")) return unavailable();
    return ++loads === 1 ? Response.json({ detail: "Unavailable" }, { status: 503 }) : Response.json(profile);
  });
  render(<SettingsPage />);
  const retry = await screen.findByRole("button", { name: /Retry loading profile/i });
  expect(screen.getByRole("button", { name: /Save training settings/i })).toBeDisabled();
  fireEvent.click(retry);
  await waitFor(() => expect(screen.getByRole("button", { name: /Save training settings/i })).toBeEnabled());
  expect(screen.getByRole("button", { name: /^dumbbell$/i })).toHaveAttribute("aria-pressed", "true");
  expect(loads).toBe(2);
});

test("equipment edits expose selected state and freeze one scoped save until acknowledgment", async () => {
  const pending = deferred();
  const writes: Record<string, unknown>[] = [];
  vi.mocked(fetch).mockImplementation(async (input, init) => {
    if (urlOf(input).endsWith("/profile/equipment")) {
      writes.push(JSON.parse(String(init?.body)));
      return pending.promise;
    }
    return urlOf(input).endsWith("/profile") ? Response.json(profile) : unavailable();
  });
  render(<SettingsPage />);
  const save = screen.getByRole("button", { name: /Save training settings/i });
  await waitFor(() => expect(save).toBeEnabled());
  const barbell = screen.getByRole("button", { name: /^barbell$/i });
  expect(barbell).toHaveAttribute("aria-pressed", "false");
  fireEvent.click(barbell);
  expect(barbell).toHaveAttribute("aria-pressed", "true");
  fireEvent.change(screen.getByLabelText("Training location"), { target: { value: "home" } });
  fireEvent.click(save);
  fireEvent.click(save);
  expect(writes).toEqual([{ training_location: "home", equipment_profile: ["dumbbell", "barbell"] }]);
  expect(save).toBeDisabled();
  expect(barbell).toBeDisabled();
  expect(screen.queryByText("Training settings saved.")).not.toBeInTheDocument();
  await act(async () => pending.resolve(Response.json({ ...profile, training_location: "home", equipment_profile: ["dumbbell", "barbell"] })));
  await screen.findByText("Training settings saved.");
  expect(save).toBeEnabled();
});

test("an unconfirmed equipment save retains the user's choices and offers a scoped retry", async () => {
  let attempt = 0;
  const writes: unknown[] = [];
  vi.mocked(fetch).mockImplementation(async (input, init) => {
    if (urlOf(input).endsWith("/profile/equipment")) {
      const body = JSON.parse(String(init?.body)); writes.push(body);
      return ++attempt === 1 ? Response.json({ detail: "Unavailable" }, { status: 503 }) : Response.json({ ...profile, ...body });
    }
    return urlOf(input).endsWith("/profile") ? Response.json(profile) : unavailable();
  });
  render(<SettingsPage />);
  await screen.findByText("No active program");
  fireEvent.change(screen.getByLabelText("Training location"), { target: { value: "home" } });
  fireEvent.click(screen.getByRole("button", { name: /Save training settings/i }));
  const retry = await screen.findByRole("button", { name: /Retry training settings/i });
  expect(screen.getByLabelText("Training location")).toHaveValue("home");
  expect(screen.queryByText("Training settings saved.")).not.toBeInTheDocument();
  fireEvent.click(retry);
  await screen.findByText("Training settings saved.");
  expect(writes).toEqual([
    { training_location: "home", equipment_profile: ["dumbbell"] },
    { training_location: "home", equipment_profile: ["dumbbell"] },
  ]);
});

test("an old account's delayed save cannot replace the new account's profile or report success", async () => {
  const pending = deferred();
  vi.mocked(fetch).mockImplementation(async (input, init) => {
    if (urlOf(input).endsWith("/profile/equipment")) return pending.promise;
    if (!urlOf(input).endsWith("/profile")) return unavailable();
    const second = new Headers(init?.headers).get("Authorization")?.includes(token("second"));
    return Response.json(second ? { ...profile, name: "Second owner", email: "second@example.com", training_location: "home", equipment_profile: ["bands"] } : profile);
  });
  render(<SettingsPage />);
  await screen.findByText("No active program");
  fireEvent.click(screen.getByRole("button", { name: /Save training settings/i }));
  act(() => setAuthToken(token("second")));
  await screen.findByText("second@example.com");
  await act(async () => pending.resolve(Response.json(profile)));
  expect(screen.getByLabelText("Training location")).toHaveValue("home");
  expect(screen.getByRole("button", { name: /^bands$/i })).toHaveAttribute("aria-pressed", "true");
  expect(screen.queryByText("Training settings saved.")).not.toBeInTheDocument();
  expect(screen.queryByText("settings@example.com")).not.toBeInTheDocument();
});

test("an unknown saved training location requires an explicit supported choice", async () => {
  vi.mocked(fetch).mockImplementation(async (input) => urlOf(input).endsWith("/profile")
    ? Response.json({ ...profile, training_location: null }) : unavailable());
  render(<SettingsPage />);
  await screen.findByText("No active program");
  expect(screen.getByLabelText("Training location")).toHaveValue("");
  expect(screen.getByRole("button", { name: /Save training settings/i })).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Training location"), { target: { value: "home" } });
  expect(screen.getByRole("button", { name: /Save training settings/i })).toBeEnabled();
  expect(vi.mocked(fetch).mock.calls.every(([, init]) => (init?.method ?? "GET") === "GET")).toBe(true);
});

test("an account change during a program preflight cannot confirm that switch for the new account", async () => {
  const preflight = deferred();
  const writes: unknown[] = [];
  vi.stubGlobal("confirm", vi.fn(() => true));
  vi.mocked(fetch).mockImplementation(async (input, init) => {
    const url = urlOf(input);
    if (url.endsWith("/profile")) return Response.json(profile);
    if (url.includes("program-recommendation")) return Response.json({ current_program_id: "old", recommended_program_id: "new", reason: "server recommendation" });
    if (url.includes("program-switch")) {
      writes.push(JSON.parse(String(init?.body)));
      return preflight.promise;
    }
    return unavailable();
  });
  render(<SettingsPage />);
  await screen.findByText("No active program");
  fireEvent.click(screen.getByRole("button", { name: /Program recommendation/i }));
  fireEvent.click(screen.getByRole("button", { name: /Get Recommendation/i }));
  await screen.findByText("Recommendation ready.");
  fireEvent.click(screen.getByRole("button", { name: /Apply Recommendation/i }));
  expect(writes).toEqual([{ target_program_id: "new", confirm: false }]);
  act(() => setAuthToken(token("second")));
  await act(async () => preflight.resolve(Response.json({ current_program_id: "old", target_program_id: "new", requires_confirmation: true })));
  expect(writes).toHaveLength(1);
  expect(globalThis.confirm).not.toHaveBeenCalled();
});
