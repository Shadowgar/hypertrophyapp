import React from "react";
import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import HomePage from "@/app/page";
import { AppearanceProvider } from "@/components/appearance-provider";
import { clearAuthToken, setAuthToken } from "@/lib/api";
const workout = (title = "Synthetic workout", resume = false) => ({ session_id: "synthetic-session", title, date: "2026-10-26", resume, exercises: [{ id: "press", name: "Synthetic press", sets: 2, rep_range: [8, 12], recommended_working_weight: 20 }] });
const context = (plan: unknown = null) => ({ timezone: "America/New_York", local_today: "2026-10-26", week_start: "2026-10-26", selected_dates: [], placement_revision: 0, plan });
const unavailable = () => Response.json({ detail: "Synthetic unavailable" }, { status: 503 });
function deferred() { let resolve!: (value: Response) => void; const promise = new Promise<Response>(done => { resolve = done; }); return { promise, resolve }; }
beforeEach(() => { localStorage.clear(); localStorage.setItem("hypertrophy_token", "synthetic-a"); globalThis.fetch = vi.fn(async () => unavailable()); });

test("available workout appears while analytics remains unresolved", async () => {
  const analytics = deferred();
  vi.mocked(fetch).mockImplementation(async input => String(input).endsWith("/training/next") ? Response.json({ mode: "calendar", action: "none" }) : String(input).includes("/history/analytics") ? analytics.promise : String(input).endsWith("/workout/today") ? Response.json(workout()) : unavailable());
  render(<HomePage />);
  expect(await screen.findByRole("link", { name: "Open today's workout" })).toHaveAttribute("href", "/today");
  expect(screen.getByText("Training summary is still loading.")).toBeInTheDocument();
});
test.each(["No plan generated", "No workout scheduled today", "No workouts available"])("recognizes API empty state: %s", async detail => {
  vi.mocked(fetch).mockImplementation(async input => String(input).endsWith("/training/next") ? Response.json({ mode: "calendar", action: "none" }) : String(input).endsWith("/workout/today") ? Response.json({ detail }, { status: 404 }) : String(input).includes("/plan/scheduling-context") ? Response.json(context()) : unavailable());
  render(<HomePage />);
  expect(await screen.findByRole("link", { name: "Choose dates" })).toHaveAttribute("href", "/week");
  expect(screen.getByRole("heading", { name: "Your week is open" })).toBeInTheDocument();
  expect(screen.queryByText(/Rest day/)).not.toBeInTheDocument();
});
test.each([404, 409])("unknown %s remains a retryable failure", async status => {
  vi.mocked(fetch).mockImplementation(async input => String(input).endsWith("/training/next") ? Response.json({ mode: "calendar", action: "none" }) : String(input).endsWith("/workout/today") ? Response.json({ detail: "Synthetic unresolved route" }, { status }) : unavailable());
  render(<HomePage />);
  expect(await screen.findByRole("button", { name: "Retry Home" })).toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: "Your week is open" })).not.toBeInTheDocument();
});
test("calendar dates do not invent a next workout when its authoritative preview fails", async () => {
  const plan = { program_template_id: "pure_bodybuilding_phase_2_full_body", schedule: { mode: "selected_dates_v1" }, sessions: [{ ...workout("Future Phase 2"), date: "2026-10-28" }] };
  vi.mocked(fetch).mockImplementation(async input => String(input).endsWith("/training/next") ? Response.json({ mode: "calendar", action: "none" }) : String(input).endsWith("/workout/today") ? Response.json({ detail: "No workout scheduled today" }, { status: 404 }) : String(input).includes("/plan/scheduling-context") ? Response.json(context(plan)) : unavailable());
  render(<HomePage />);
  expect(await screen.findByRole("heading", { name: "Review your schedule" })).toBeInTheDocument();
  await screen.findByText(/next workout preview could not be loaded/);
  expect(screen.queryByRole("heading", { name: "Future Phase 2" })).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Review Week" })).toHaveAttribute("href", "/week");
  expect(screen.queryByRole("link", { name: /Open today's workout/ })).not.toBeInTheDocument();
});
test("account switch clears a rendered workout and ignores delayed prior account data", async () => {
  const oldAnalytics = deferred();
  vi.mocked(fetch).mockImplementation(async (input, init) => {
    if (String(input).endsWith("/training/next")) return Response.json({ mode: "calendar", action: "none" });
    const account = new Headers(init?.headers).get("Authorization");
    if (String(input).includes("/history/analytics") && account === "Bearer synthetic-a") return oldAnalytics.promise;
    if (String(input).endsWith("/workout/today")) return Response.json(workout(account === "Bearer synthetic-a" ? "Account A workout" : "Account B workout"));
    return unavailable();
  });
  render(<HomePage />);
  await screen.findByRole("heading", { name: "Account A workout" });
  act(() => setAuthToken("synthetic-b"));
  expect(screen.queryByText("Account A workout")).not.toBeInTheDocument();
  await screen.findByRole("heading", { name: "Account B workout" });
  await act(async () => oldAnalytics.resolve(Response.json({ bodyweight_trend: [{ body_weight: 999 }], strength_trends: [], pr_highlights: [], window: { limit_weeks: 8 } })));
  expect(screen.queryByText(/2202\.4/)).not.toBeInTheDocument();
  expect(screen.queryByText("Account A workout")).not.toBeInTheDocument();
});
test.each(["logout", "storage", "expired"])("%s removes private content without waiting for analytics", async mode => {
  const pending = deferred();
  vi.mocked(fetch).mockImplementation(async input => String(input).endsWith("/training/next") ? Response.json({ mode: "calendar", action: "none" }) : String(input).endsWith("/workout/today") ? Response.json(workout()) : String(input).includes("/history/analytics") ? pending.promise : unavailable());
  render(<HomePage />); await screen.findByRole("link", { name: "Open today's workout" });
  if (mode === "expired") await act(async () => pending.resolve(Response.json({ detail: "Invalid token" }, { status: 401 })));
  else act(() => { if (mode === "logout") clearAuthToken(); else { localStorage.removeItem("hypertrophy_token"); window.dispatchEvent(new StorageEvent("storage", { key: "hypertrophy_token" })); } });
  expect(await screen.findByRole("link", { name: "Sign in" })).toBeInTheDocument();
  expect(screen.queryByText("Synthetic workout")).not.toBeInTheDocument();
});
test("retry remains mounted and retains focus during the next request", async () => {
  const pending = deferred(); let attempt = 0;
  vi.mocked(fetch).mockImplementation(async input => String(input).endsWith("/training/next") ? Response.json({ mode: "calendar", action: "none" }) : String(input).endsWith("/workout/today") && attempt++ > 0 ? pending.promise : unavailable());
  render(<HomePage />); const retry = await screen.findByRole("button", { name: "Retry Home" });
  retry.focus(); fireEvent.click(retry);
  expect(screen.getByRole("button", { name: "Retry Home" })).toBe(retry); expect(retry).toHaveFocus();
  await act(async () => pending.resolve(Response.json(workout("Recovered", true))));
  expect(await screen.findByRole("link", { name: "Resume your workout" })).toBeInTheDocument();
  expect(vi.mocked(fetch).mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true);
});

test("a late unauthorized workout from the old account cannot sign out the new one", async () => {
  const old = deferred();
  vi.mocked(fetch).mockImplementation(async (input, init) => String(input).endsWith("/training/next") ? Response.json({ mode: "calendar", action: "none" }) : String(input).endsWith("/workout/today")
    ? new Headers(init?.headers).get("Authorization") === "Bearer synthetic-a" ? old.promise : Response.json(workout("New account workout")) : unavailable());
  render(<HomePage />);
  act(() => setAuthToken("synthetic-b"));
  await screen.findByRole("heading", { name: "New account workout" });
  await act(async () => old.resolve(Response.json({ detail: "Expired old session" }, { status: 401 })));
  expect(screen.getByRole("heading", { name: "New account workout" })).toBeInTheDocument();
  expect(localStorage.getItem("hypertrophy_token")).toBe("synthetic-b");
});

test("a stale previous-attempt response cannot overwrite the retry", async () => {
  const old = deferred(); let analyticsCalls = 0;
  vi.mocked(fetch).mockImplementation(async input => {
    if (String(input).endsWith("/training/next")) return Response.json({ mode: "calendar", action: "none" });
    if (String(input).includes("/history/analytics") && analyticsCalls++ === 0) return old.promise;
    return String(input).endsWith("/workout/today") ? Response.json(workout()) : unavailable();
  });
  render(<HomePage />);
  const retry = await screen.findByRole("button", { name: "Retry Home" });
  fireEvent.click(retry);
  await screen.findByRole("link", { name: "Open today's workout" });
  await act(async () => old.resolve(Response.json({ bodyweight_trend: [{ body_weight: 999 }], strength_trends: [], pr_highlights: [], window: { limit_weeks: 8 } })));
  expect(screen.queryByText(/2202\.4/)).not.toBeInTheDocument();
});

test.each(["classic", "graphite", "charcoal"].flatMap(theme => ["light", "dark"].map(appearance => ({ theme, appearance }))))("preserves $theme/$appearance and kilograms without account writes", async ({ theme, appearance }) => {
  vi.stubGlobal("matchMedia", vi.fn(() => ({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() })));
  vi.mocked(fetch).mockImplementation(async input => String(input).endsWith("/training/next") ? Response.json({ mode: "calendar", action: "none" }) : String(input).endsWith("/profile/preferences")
    ? Response.json({ theme_family: theme, appearance, weight_unit: "kg", revision: 8 })
    : String(input).endsWith("/workout/today") ? Response.json(workout()) : unavailable());
  render(<AppearanceProvider><HomePage /></AppearanceProvider>);
  expect(await screen.findByText(/Synthetic press · 2 x 8-12 @ 20 kg/)).toBeInTheDocument();
  expect(document.documentElement.dataset.theme).toBe(theme);
  expect(document.documentElement.dataset.appearance).toBe(appearance);
  expect(vi.mocked(fetch).mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true);
});

test("future preview cannot bypass an unresolved Today request", async () => {
  vi.mocked(fetch).mockImplementation(async input => String(input).endsWith("/training/next") ? Response.json({ mode: "calendar", action: "none" }) : String(input).includes("/plan/scheduling-context")
    ? Response.json(context({ schedule: { mode: "selected_dates_v1" }, sessions: [{ ...workout("Future not actionable"), date: "2026-10-28" }] })) : unavailable());
  render(<HomePage />);
  await screen.findByRole("button", { name: "Retry Home" });
  expect(screen.queryByRole("heading", { name: "Future not actionable" })).not.toBeInTheDocument();
  expect(screen.queryByRole("link", { name: "Open today's workout" })).not.toBeInTheDocument();
});

test("a future program does not relabel this week's saved program", async () => {
  const current = { program_template_id: "pure_bodybuilding_phase_1_full_body", schedule: { mode: "selected_dates_v1" }, sessions: [] };
  const future = { program_template_id: "pure_bodybuilding_phase_2_full_body", schedule: { mode: "selected_dates_v1" }, sessions: [{ ...workout("Next week Phase 2"), date: "2026-11-03" }] };
  vi.mocked(fetch).mockImplementation(async input => {
    if (String(input).endsWith("/training/next")) return Response.json({ mode: "calendar", action: "none" });
    const url = String(input);
    if (url.endsWith("/profile")) return Response.json({ effective_days_available: 3, effective_program_id: "pure_bodybuilding_phase_1_full_body" });
    if (url.includes("/plan/scheduling-context")) return Response.json(context(url.includes("week_offset=1") ? future : current));
    if (url.endsWith("/workout/today")) return Response.json({ detail: "No workout scheduled today" }, { status: 404 });
    return unavailable();
  });
  render(<HomePage />);
  await screen.findByRole("heading", { name: "Review your schedule" });
  expect(screen.queryByRole("heading", { name: "Next week Phase 2" })).not.toBeInTheDocument();
  expect(screen.getByText("3 training days · Full Body Phase 1")).toBeInTheDocument();
});

test("unavailable program reads do not tell a returning account to choose again", async () => {
  vi.mocked(fetch).mockImplementation(async input => String(input).endsWith("/training/next") ? Response.json({ mode: "calendar", action: "none" }) : String(input).endsWith("/workout/today") ? Response.json(workout()) : unavailable());
  render(<HomePage />);
  await screen.findByRole("link", { name: "Open today's workout" });
  expect(screen.getByText("Program details unavailable")).toBeInTheDocument();
  expect(screen.queryByText("Choose a program")).not.toBeInTheDocument();
});

test("pending program reads remain checking even when the workout is ready", async () => {
  vi.mocked(fetch).mockImplementation(async input => String(input).endsWith("/training/next") ? Response.json({ mode: "calendar", action: "none" }) : String(input).endsWith("/workout/today") ? Response.json(workout()) : new Promise<Response>(() => {}));
  render(<HomePage />);
  await screen.findByRole("link", { name: "Open today's workout" });
  expect(screen.getByText("Checking your program…")).toBeInTheDocument();
  expect(screen.queryByText("Choose a program")).not.toBeInTheDocument();
});

test.each([
  { fields: { program_template_id: "pure_bodybuilding_phase_2_full_body" }, label: "Full Body Phase 2" },
  { fields: { selected_program_id: "pure_bodybuilding_phase_2_full_body" }, label: "Full Body Phase 2" },
  { fields: { customized: { proposal_id: "synthetic-consented" } }, label: "Customized workout" },
  { fields: {}, label: "Program details unavailable" },
])("the active workout owns its program identity: $label", async ({ fields, label }) => {
  vi.mocked(fetch).mockImplementation(async input => {
    if (String(input).endsWith("/training/next")) return Response.json({ mode: "calendar", action: "none" });
    const url = String(input);
    if (url.endsWith("/workout/today")) return Response.json({ ...workout(), workout_occurrence_id: "active-occurrence", ...fields });
    if (url.endsWith("/profile")) return Response.json({ selected_program_id: "pure_bodybuilding_phase_1_full_body", days_available: 3 });
    if (url.includes("/plan/scheduling-context")) return Response.json(context({ program_template_id: "pure_bodybuilding_phase_1_full_body", sessions: [{ ...workout(), workout_occurrence_id: "different-occurrence" }] }));
    return unavailable();
  });
  render(<HomePage />);
  await screen.findByRole("link", { name: "Open today's workout" });
  const nextStep = within(screen.getByRole("region", { name: "Next step" }));
  expect(nextStep.getByText(label)).toBeInTheDocument();
  expect(nextStep.queryByText("Full Body Phase 1")).not.toBeInTheDocument();
});
