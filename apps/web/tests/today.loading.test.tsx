import React from "react";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import TodayPage from "@/app/today/page";
import { setAuthToken } from "@/lib/api";

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>(done => { resolve = done; });
  return { promise, resolve };
}
const date = "2026-10-23";
const schedulingContext = { timezone: "UTC", local_today: date, week_start: "2026-10-19", selected_dates: [date], placement_revision: 1, plan: null };
const reviewStatus = { today_is_sunday: false, review_required: false };
function workout(name = "Resume Press", occurrence = "resume-occurrence", completed = 0) {
  return { session_id: "template", workout_occurrence_id: occurrence, title: `${name} workout`, date, resume: true,
    exercises: [{ id: "press", exercise_occurrence_id: `${occurrence}-press`, name, sets: 3, completed_sets: completed, rep_range: [8, 12], recommended_working_weight: 20 }] };
}
function progress(occurrence = "resume-occurrence", count = 1) {
  return { completed_total: count, planned_total: 3, percent_complete: count / 3 * 100,
    exercises: [{ exercise_id: "press", exercise_occurrence_id: `${occurrence}-press`, completed_sets: count }] };
}
function fixture(override: (url: string, init?: RequestInit) => Promise<Response> | Response | undefined = () => undefined) {
  const requests: string[] = [];
  vi.stubGlobal("fetch", vi.fn(async (input, init) => {
    const url = String(input); requests.push(url);
    const custom = override(url, init);
    if (custom !== undefined) return custom;
    if (url.endsWith("/health")) return Response.json({ status: "ok" });
    if (url.includes("/plan/scheduling-context?")) return Response.json(schedulingContext);
    if (url.endsWith("/weekly-review/status")) return Response.json(reviewStatus);
    if (url.endsWith("/workout/today")) return Response.json(workout());
    if (url.endsWith("/progress")) return Response.json(progress());
    if (url.includes("/soreness?")) return Response.json([{ entry_date: date }]);
    return Response.json({});
  }));
  return requests;
}
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

test("date and review checks start together while both still gate Today", async () => {
  const clock = deferred<Response>(); const review = deferred<Response>();
  const requests = fixture(url => url.includes("/plan/scheduling-context?") ? clock.promise
    : url.endsWith("/weekly-review/status") ? review.promise : undefined);
  render(<TodayPage />);
  await waitFor(() => expect(requests.some(url => url.endsWith("/weekly-review/status"))).toBe(true));
  expect(requests.some(url => url.includes("/plan/scheduling-context?"))).toBe(true);
  expect(requests.some(url => url.endsWith("/workout/today"))).toBe(false);
  await act(async () => clock.resolve(Response.json(schedulingContext)));
  expect(requests.some(url => url.endsWith("/workout/today"))).toBe(false);
  await act(async () => review.resolve(Response.json(reviewStatus)));
  expect(await screen.findByRole("button", { name: /Resume Press/ })).toHaveTextContent("1/3");
});

test("a slow display profile does not delay resumed progress or the required soreness check", async () => {
  const profile = deferred<Response>();
  const requests = fixture(url => url.endsWith("/profile") ? profile.promise : undefined);
  render(<TodayPage />);
  await waitFor(() => expect(requests.some(url => url.endsWith("/progress"))).toBe(true));
  expect(await screen.findByRole("button", { name: /Resume Press/ })).toHaveTextContent("1/3");
  await waitFor(() => expect(requests.some(url => url.includes("/soreness?"))).toBe(true));
  await act(async () => profile.resolve(Response.json({ weak_areas: ["arms"] })));
});

test("loading and refresh remain visible until required reads settle", async () => {
  const initial = deferred<Response>(); const refresh = deferred<Response>(); let reads = 0;
  fixture(url => url.endsWith("/workout/today") ? (++reads === 1 ? initial.promise : refresh.promise) : undefined);
  render(<TodayPage />);
  await waitFor(() => expect(screen.getByRole("button", { name: /Load today's workout/ })).toBeDisabled());
  expect(screen.getByText("Loading your scheduled workout…")).toBeInTheDocument();
  await act(async () => initial.resolve(Response.json(workout())));
  const reload = await screen.findByRole("button", { name: "Reload" });
  await waitFor(() => expect(reload).toBeEnabled());
  fireEvent.click(reload);
  expect(reload).toBeDisabled();
  expect(screen.getByText("Refreshing your scheduled workout…")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /Resume Press/ })).not.toBeInTheDocument();
  await act(async () => refresh.resolve(Response.json(workout())));
  await waitFor(() => expect(reload).toBeEnabled());
});

test("unmount invalidates a late Today response before any follow-up request or cache write", async () => {
  const today = deferred<Response>();
  const requests = fixture(url => url.endsWith("/workout/today") ? today.promise : undefined);
  const view = render(<TodayPage />);
  await waitFor(() => expect(requests.some(url => url.endsWith("/workout/today"))).toBe(true));
  view.unmount();
  await act(async () => today.resolve(Response.json(workout())));
  expect(requests.some(url => url.endsWith("/profile") || url.endsWith("/progress") || url.includes("/soreness?"))).toBe(false);
  expect(Object.keys(localStorage).filter(key => key.includes("completed"))).toEqual([]);
});

test.each(["token event", "storage event"])("%s retires an old account's Today response and reloads the current account", async event => {
  setAuthToken("synthetic-account-a");
  const oldToday = deferred<Response>();
  const requests = fixture((url, init) => {
    const token = new Headers(init?.headers).get("Authorization");
    if (url.endsWith("/workout/today")) return token === "Bearer synthetic-account-a" ? oldToday.promise : Response.json(workout("Current Account Press", "current"));
    if (url.endsWith("/progress")) return Response.json(progress("current"));
    return undefined;
  });
  render(<TodayPage />);
  await waitFor(() => expect(requests.some(url => url.endsWith("/workout/today"))).toBe(true));
  act(() => {
    if (event === "token event") setAuthToken("synthetic-account-b");
    else { localStorage.setItem("hypertrophy_token", "synthetic-account-b"); window.dispatchEvent(new StorageEvent("storage", { key: "hypertrophy_token" })); }
  });
  expect(await screen.findByRole("button", { name: /Current Account Press/ })).toBeInTheDocument();
  await act(async () => oldToday.resolve(Response.json(workout("Old Account Press", "old"))));
  expect(screen.queryByRole("button", { name: /Old Account Press/ })).not.toBeInTheDocument();
  expect(requests.some(url => url.endsWith("/old/progress"))).toBe(false);
});

test("a late progress reply from the retired account cannot overwrite the current occurrence", async () => {
  setAuthToken("synthetic-account-a");
  const oldProgress = deferred<Response>();
  const requests = fixture((url, init) => {
    const old = new Headers(init?.headers).get("Authorization") === "Bearer synthetic-account-a";
    if (url.endsWith("/workout/today")) return Response.json(workout(old ? "Old Account Press" : "Current Account Press", old ? "old" : "current"));
    if (url.endsWith("/progress")) return old ? oldProgress.promise : Response.json(progress("current", 1));
    return undefined;
  });
  render(<TodayPage />);
  await waitFor(() => expect(requests.some(url => url.endsWith("/old/progress"))).toBe(true));
  act(() => setAuthToken("synthetic-account-b"));
  expect(await screen.findByRole("button", { name: /Current Account Press/ })).toHaveTextContent("1/3");
  await act(async () => oldProgress.resolve(Response.json(progress("old", 3))));
  expect(screen.getByRole("button", { name: /Current Account Press/ })).toHaveTextContent("1/3");
  expect(requests.some(url => url.endsWith("/old/summary"))).toBe(false);
});


test("StrictMode effect replay still loads the scheduled occurrence", async () => {
  fixture();
  render(<React.StrictMode><TodayPage /></React.StrictMode>);
  await waitFor(() => expect(screen.getByRole("button", { name: /Resume Press/ })).toHaveTextContent("1/3"));
  await waitFor(() => expect(screen.getByRole("button", { name: "Reload" })).toBeEnabled());
});


test.each(["clock", "review"])("failed %s verification never loads Today and releases the retry control", async failedGate => {
  const requests = fixture(url => (failedGate === "clock" ? url.includes("/plan/scheduling-context?") : url.endsWith("/weekly-review/status"))
    ? Response.json({ detail: "unavailable" }, { status: 503 }) : undefined);
  render(<TodayPage />);
  await screen.findByText("Unable to verify soreness status. Try again.");
  expect(requests.some(url => url.endsWith("/workout/today") || url.includes("/soreness?"))).toBe(false);
  expect(screen.getByRole("button", { name: /Load today's workout/ })).toBeEnabled();
});

test("a required Sunday review still prevents Today and soreness reads", async () => {
  const requests = fixture(url => url.endsWith("/weekly-review/status")
    ? Response.json({ today_is_sunday: true, review_required: true }) : undefined);
  render(<TodayPage />);
  await screen.findByText("Sunday review required before starting workout. Go to Check-In to submit weekly review.");
  expect(requests.some(url => url.endsWith("/workout/today") || url.includes("/soreness?"))).toBe(false);
  expect(screen.getByRole("button", { name: /Load today's workout/ })).toBeEnabled();
});

test("initial Today failure clears loading and can be retried without a write", async () => {
  let reads = 0;
  const requests = fixture(url => url.endsWith("/workout/today") && ++reads === 1
    ? Response.json({ detail: "unavailable" }, { status: 503 }) : undefined);
  render(<TodayPage />);
  await screen.findByText("Workout could not be loaded. Retry loading your workout. Your saved history is unchanged.");
  const retry = screen.getByRole("button", { name: /Load today's workout/ });
  expect(retry).toBeEnabled();
  fireEvent.click(retry);
  await waitFor(() => expect(screen.getByRole("button", { name: /Resume Press/ })).toHaveTextContent("1/3"));
  expect(requests.some(url => url.includes("generate"))).toBe(false);
});

test("failed health reports a retryable state without waiting indefinitely", async () => {
  fixture(url => url.endsWith("/health") ? Response.json({ detail: "offline" }, { status: 503 }) : undefined);
  render(<TodayPage />);
  await screen.findByText("Workout service unavailable. Retry loading your workout. Your saved history is unchanged.");
  expect(screen.getByRole("button", { name: /Load today's workout/ })).toBeEnabled();
});


test.each(["clock", "review", "today", "Sunday review"])("a required %s refresh hides prior controls and keeps them unavailable on failure", async failedRead => {
  let refreshing = false;
  const pending = deferred<Response>();
  fixture(url => refreshing && (failedRead === "clock" ? url.includes("/plan/scheduling-context?")
    : failedRead === "today" ? url.endsWith("/workout/today") : url.endsWith("/weekly-review/status")) ? pending.promise : undefined);
  render(<TodayPage />);
  await waitFor(() => expect(screen.getByRole("button", { name: /Resume Press/ })).toHaveTextContent("1/3"));
  await waitFor(() => expect(screen.getByRole("button", { name: "Reload" })).toBeEnabled());
  refreshing = true;
  fireEvent.click(screen.getByRole("button", { name: "Reload" }));
  expect(screen.queryByRole("button", { name: /Resume Press/ })).not.toBeInTheDocument();
  expect(screen.queryByRole("region", { name: "Workout execution" })).not.toBeInTheDocument();
  await act(async () => pending.resolve(failedRead === "Sunday review" ? Response.json({ today_is_sunday: true, review_required: true })
    : Response.json({ detail: "unavailable" }, { status: 503 })));
  await screen.findByText(failedRead === "Sunday review"
    ? "Sunday review required before starting workout. Go to Check-In to submit weekly review."
    : failedRead === "today" ? "Workout could not be loaded. Retry loading your workout. Your saved history is unchanged."
    : "Unable to verify soreness status. Try again.");
  expect(screen.queryByRole("button", { name: /Resume Press/ })).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Load today's workout/ })).toBeEnabled();
});

test("accepted Today controls are usable while profile and progress are still pending", async () => {
  const profile = deferred<Response>(); const projection = deferred<Response>();
  fixture(url => url.endsWith("/profile") ? profile.promise : url.endsWith("/progress") ? projection.promise : undefined);
  render(<TodayPage />);
  const row = await screen.findByRole("button", { name: /Resume Press/ });
  expect(row).toBeEnabled();
  fireEvent.click(row);
  expect(await screen.findByRole("region", { name: "Workout execution" })).toBeInTheDocument();
  expect(screen.getByRole("spinbutton", { name: "Working repetitions" })).toBeEnabled();
  await act(async () => { profile.resolve(Response.json({})); projection.resolve(Response.json(progress())); });
});
