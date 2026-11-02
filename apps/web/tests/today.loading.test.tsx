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
afterEach(() => { vi.restoreAllMocks(); cleanup(); vi.unstubAllGlobals(); });

test.each([
  { mode: "Authored Phase 1", program: "pure_bodybuilding_phase_1_full_body", customized: undefined, label: "Manage training dates", href: "/week" },
  { mode: "Authored Phase 2", program: "pure_bodybuilding_phase_2_full_body", customized: false, label: "Manage training dates", href: "/week" },
  { mode: "Customized boolean response", program: "customized_full_body_v1", customized: true, label: "Manage Customized programs", href: "/customize" },
  { mode: "Customized without proposal metadata", program: "customized_full_body_v1", customized: {}, label: "Manage Customized programs", href: "/customize" },
  { mode: "Customized with proposal metadata", program: "customized_full_body_v1", customized: { proposal_id: "saved/proposal?revision=4" }, label: "Manage Customized dates or replace program", href: "/customize?proposal=saved%2Fproposal%3Frevision%3D4" },
])("$mode date navigation preserves the actual workout mode without writes", async ({ program, customized, label, href }) => {
  fixture(url => url.endsWith("/workout/today") ? Response.json({
    ...workout(), session_id: `${program}_day_1`, program_template_id: program,
    ...(customized === undefined ? {} : { customized }),
  }) : undefined);
  render(<TodayPage />);
  await screen.findByRole("button", { name: /Resume Press/ });
  expect(screen.getByRole("link", { name: label })).toHaveAttribute("href", href);
  for (const other of ["Manage training dates", "Manage Customized programs", "Manage Customized dates or replace program"].filter(value => value !== label)) {
    expect(screen.queryByRole("link", { name: other })).not.toBeInTheDocument();
  }
  expect(vi.mocked(fetch).mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true);
});

test.each(["read", "write"])("a failed optional browser cache %s cannot discard a verified workout", async operation => {
  fixture();
  if (operation === "read") {
    const read = Storage.prototype.getItem;
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(function (this: Storage, key: string) {
      if (key.includes(":swaps:")) throw new DOMException("Storage unavailable", "SecurityError");
      return read.call(this, key);
    });
  } else {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("Storage full", "QuotaExceededError");
    });
  }
  render(<TodayPage />);
  const row = await screen.findByRole("button", { name: /Resume Press/ });
  await waitFor(() => expect(row).toHaveTextContent("1/3"));
  fireEvent.click(row);
  expect(await screen.findByRole("spinbutton", { name: "Working repetitions" })).toBeEnabled();
  expect(screen.queryByText(/Workout could not be loaded/)).not.toBeInTheDocument();
});

test("full browser storage still permits a frozen in-page set retry in canonical units", async () => {
  let count = 0;
  const attempts: Record<string, unknown>[] = [];
  fixture((url, init) => {
    if (url.endsWith("/progress")) return Response.json(progress("quota-occurrence", count));
    if (url.endsWith("/workout/today")) return Response.json(workout("Quota Press", "quota-occurrence", count));
    if (url.endsWith("/log-set")) {
      attempts.push(JSON.parse(String(init?.body)));
      if (attempts.length === 1) throw new TypeError("Reply lost");
      count = 1;
      return Response.json({ live_recommendation: { completed_sets: 1, remaining_sets: 2,
        recommended_reps_min: 8, recommended_reps_max: 12, recommended_weight: 45.359237 } });
    }
    return undefined;
  });
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
    throw new DOMException("Storage full", "QuotaExceededError");
  });
  render(<TodayPage />);
  fireEvent.click(await screen.findByRole("button", { name: /Quota Press/ }));
  fireEvent.change(screen.getByLabelText("Working weight (lb)"), { target: { value: "100" } });
  fireEvent.change(screen.getByLabelText("Working repetitions"), { target: { value: "8" } });
  fireEvent.click(screen.getByRole("button", { name: "Save set 1" }));
  const retry = await screen.findByRole("button", { name: "Retry same set" });
  expect(screen.getByLabelText("Working weight (lb)")).toHaveAttribute("readonly");
  fireEvent.click(retry);
  await screen.findByText(/Set 1 saved/);
  expect(attempts).toHaveLength(2);
  expect(attempts[1]).toEqual(attempts[0]);
  expect(attempts[1]).toMatchObject({ exercise_occurrence_id: "quota-occurrence-press", set_index: 1, reps: 8, weight: 45.359237 });
});

test("a pending or unavailable review cannot block an accepted scheduling date and workout", async () => {
  const clock = deferred<Response>(); const review = deferred<Response>();
  const requests = fixture(url => url.includes("/plan/scheduling-context?") ? clock.promise
    : url.endsWith("/weekly-review/status") ? review.promise : undefined);
  render(<TodayPage />);
  await waitFor(() => expect(requests.some(url => url.includes("/plan/scheduling-context?"))).toBe(true));
  expect(requests.some(url => url.endsWith("/workout/today"))).toBe(false);
  await act(async () => clock.resolve(Response.json(schedulingContext)));
  expect(await screen.findByRole("button", { name: /Resume Press/ })).toHaveTextContent("1/3");
  expect(requests.some(url => url.endsWith("/weekly-review/status"))).toBe(false);
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

test.each(["retry", "continue"])("a failed soreness lookup preserves the accepted workout and supports %s without inventing a report", async action => {
  let sorenessReads = 0;
  const writes: string[] = [];
  fixture((url, init) => {
    if (init?.method && init.method !== "GET") writes.push(url);
    if (url.includes("/soreness?")) return ++sorenessReads === 1
      ? Response.json({ detail: "unavailable" }, { status: 503 }) : Response.json([]);
    return undefined;
  });
  render(<TodayPage />);
  await screen.findByRole("button", { name: "Retry soreness check" });
  expect(screen.getByRole("button", { name: /Resume Press/ })).toHaveTextContent("1/3");
  expect(screen.queryByText(/sore today\?/i)).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: action === "retry" ? "Retry soreness check" : "Continue workout" }));
  if (action === "retry") {
    await screen.findByText(/sore today\?/i);
    expect(sorenessReads).toBe(2);
    expect(screen.queryByRole("button", { name: "Retry soreness check" })).not.toBeInTheDocument();
  } else {
    expect(sorenessReads).toBe(1);
    fireEvent.click(screen.getByRole("button", { name: /Resume Press/ }));
    expect(await screen.findByRole("spinbutton", { name: "Working repetitions" })).toBeEnabled();
  }
  expect(writes).toEqual([]);
});

test.each([true, false])("a retired account's late soreness lookup (failed=%s) cannot affect the current workout", async failed => {
  setAuthToken("synthetic-account-a");
  const oldSoreness = deferred<Response>();
  let oldSorenessStarted = false;
  fixture((url, init) => {
    const old = new Headers(init?.headers).get("Authorization") === "Bearer synthetic-account-a";
    if (url.endsWith("/workout/today")) return Response.json(workout(old ? "Old Account Press" : "Current Account Press", old ? "old" : "current"));
    if (url.endsWith("/progress")) return Response.json(progress(old ? "old" : "current"));
    if (url.includes("/soreness?") && old) { oldSorenessStarted = true; return oldSoreness.promise; }
    return undefined;
  });
  render(<TodayPage />);
  await waitFor(() => expect(oldSorenessStarted).toBe(true));
  act(() => setAuthToken("synthetic-account-b"));
  await waitFor(() => expect(screen.getByRole("button", { name: /Current Account Press/ })).toHaveTextContent("1/3"));
  await act(async () => oldSoreness.resolve(failed ? Response.json({}, { status: 503 }) : Response.json([])));
  expect(screen.queryByText(/sore today\?/i)).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Retry soreness check" })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /Current Account Press/ }));
  expect(await screen.findByRole("spinbutton", { name: "Working repetitions" })).toBeEnabled();
});

test("loading and refresh remain visible until required reads settle", async () => {
  const initial = deferred<Response>(); const refresh = deferred<Response>(); let reads = 0;
  fixture(url => url.endsWith("/workout/today") ? (++reads === 1 ? initial.promise : refresh.promise) : undefined);
  render(<TodayPage />);
  await waitFor(() => expect(screen.getByRole("button", { name: /Load today's workout/ })).toBeDisabled());
  expect(screen.getByText("Loading your workout…")).toBeInTheDocument();
  await act(async () => initial.resolve(Response.json(workout())));
  const reload = await screen.findByRole("button", { name: "Reload" });
  await waitFor(() => expect(reload).toBeEnabled());
  fireEvent.click(reload);
  expect(reload).toBeDisabled();
  expect(screen.getByText("Refreshing your workout…")).toBeInTheDocument();
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


test("failed clock verification never loads Today and releases the retry control", async () => {
  const requests = fixture(url => url.includes("/plan/scheduling-context?")
    ? Response.json({ detail: "unavailable" }, { status: 503 }) : undefined);
  render(<TodayPage />);
  await screen.findByText("The local training date could not be verified. Retry loading your workout. Your saved history is unchanged.");
  expect(requests.some(url => url.endsWith("/workout/today") || url.includes("/soreness?"))).toBe(false);
  expect(screen.getByRole("button", { name: /Load today's workout/ })).toBeEnabled();
});

test.each(["missing", "failed"])("a %s Sunday review cannot block Today or fabricate a submission", async state => {
  const requests = fixture(url => url.endsWith("/weekly-review/status")
    ? state === "missing" ? Response.json({ today_is_sunday: true, review_required: true }) : Response.json({}, { status: 503 }) : undefined);
  render(<TodayPage />);
  expect(await screen.findByRole("button", { name: /Resume Press/ })).toHaveTextContent("1/3");
  expect(requests.some(url => url.includes("weekly-review"))).toBe(false);
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

test("workout authorization is independent of a failed diagnostic health endpoint", async () => {
  const requests=fixture(url => url.endsWith("/health") ? Response.json({ detail:"offline" },{ status:503 }) : undefined);
  render(<TodayPage/>);await screen.findByRole("button",{name:/Resume Press/});
  expect(requests.some(url=>url.endsWith("/health"))).toBe(false);
});


test.each(["clock", "today"])("a required %s refresh hides prior controls and keeps them unavailable on failure", async failedRead => {
  let refreshing = false;
  const pending = deferred<Response>();
  fixture(url => refreshing && (failedRead === "clock" ? url.includes("/plan/scheduling-context?")
    : url.endsWith("/workout/today")) ? pending.promise : undefined);
  render(<TodayPage />);
  await waitFor(() => expect(screen.getByRole("button", { name: /Resume Press/ })).toHaveTextContent("1/3"));
  await waitFor(() => expect(screen.getByRole("button", { name: "Reload" })).toBeEnabled());
  refreshing = true;
  fireEvent.click(screen.getByRole("button", { name: "Reload" }));
  expect(screen.queryByRole("button", { name: /Resume Press/ })).not.toBeInTheDocument();
  expect(screen.queryByRole("region", { name: "Workout execution" })).not.toBeInTheDocument();
  await act(async () => pending.resolve(Response.json({ detail: "unavailable" }, { status: 503 })));
  await screen.findByText(failedRead === "today" ? "Workout refresh failed. Retry to verify your workout. Your draft and saved history are kept."
    : "The local training date could not be verified. Retry loading your workout. Your saved history is unchanged.");
  expect(screen.queryByRole("button", { name: /Resume Press/ })).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Reload" })).toBeEnabled();
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

test("a diagnostic health ping cannot postpone an authenticated workout",async()=>{
 const never=deferred<Response>();const requests=fixture(url=>url.endsWith("/health")?never.promise:undefined);
 render(<TodayPage/>);await screen.findByRole("button",{name:/Resume Press/});
 expect(requests.some(url=>url.endsWith("/health"))).toBe(false);
});

test("the optional soreness prompt does not wait behind progress",async()=>{
 const pending=deferred<Response>();const requests=fixture(url=>url.endsWith("/progress")?pending.promise:url.includes("/soreness?")?Response.json([]):undefined);
 render(<TodayPage/>);
 await screen.findByRole("button",{name:"Skip"});
 expect(requests.some(url=>url.endsWith("/progress"))).toBe(true);
 await act(async()=>pending.resolve(Response.json(progress())));
});

test("same-day Skip preserves verified workout and does not fetch Today twice",async()=>{
 const requests=fixture(url=>url.includes("/soreness?")?Response.json([]):undefined);render(<TodayPage/>);
 fireEvent.click(await screen.findByRole("button",{name:"Skip"}));
 await waitFor(()=>expect(requests.filter(url=>url.includes("/plan/scheduling-context?")).length).toBe(2));
 await waitFor(()=>expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
 expect(requests.filter(url=>url.endsWith("/workout/today"))).toHaveLength(1);
 expect(requests.filter(url=>url.endsWith("/progress"))).toHaveLength(1);
});

test("an unavailable training decision blocks Today and exposes its own retry",async()=>{
 setAuthToken(`header.${btoa(JSON.stringify({sub:"mode-retry"}))}.signature`);
 let reads=0;const requests=fixture(url=>url.endsWith("/training/next")?++reads===1?Response.json({detail:"unavailable"},{status:503}):Response.json({mode:"calendar",action:"none"}):undefined);
 render(<TodayPage/>);const retry=await screen.findByRole("button",{name:"Retry training state"});
 expect(screen.getByRole("button",{name:/Load today's workout/})).toBeDisabled();
 expect(screen.queryByText("Loading your workout…")).not.toBeInTheDocument();
 expect(requests.some(url=>url.endsWith("/workout/today"))).toBe(false);
 fireEvent.click(retry);await screen.findByRole("button",{name:/Resume Press/});
});

test("failed auxiliary progress keeps Today counts and explains the limited refresh",async()=>{
 fixture(url=>url.endsWith("/workout/today")?Response.json(workout("Verified Press","verified",1)):url.endsWith("/progress")?Response.json({detail:"unavailable"},{status:503}):undefined);
 render(<TodayPage/>);expect(await screen.findByRole("button",{name:/Verified Press/})).toHaveTextContent("1/3");
 await screen.findByText(/Latest set refresh unavailable/);
 expect(screen.getByText(/Verified Press workout.*1\/3 sets/)).toBeInTheDocument();
 expect(screen.queryByText(/No workout available/)).not.toBeInTheDocument();
});

test("a temporary refresh failure keeps the selected composer mounted but unavailable until verified",async()=>{
 let fail=false;fixture(url=>fail&&url.endsWith("/workout/today")?Response.json({detail:"unavailable"},{status:503}):undefined);
 render(<TodayPage/>);fireEvent.click(await screen.findByRole("button",{name:/Resume Press/}));
 const weight=screen.getByLabelText("Working weight (lb)");fireEvent.change(weight,{target:{value:"73"}});
 const stored=Storage.prototype.setItem;vi.spyOn(Storage.prototype,"setItem").mockImplementation(function(this:Storage,key,value){if(key.includes(":draft:"))throw new DOMException("Unavailable","SecurityError");return stored.call(this,key,value)});
 fireEvent.change(weight,{target:{value:"74"}});fail=true;
 fireEvent.click(screen.getByRole("button",{name:"Reload",hidden:true}));
 await screen.findByText(/Workout refresh failed/);
 expect(weight.isConnected).toBe(true);expect(weight).not.toBeVisible();expect(weight).toBeDisabled();
 expect(screen.queryByRole("region",{name:"Working set entry"})).not.toBeInTheDocument();
 fail=false;fireEvent.click(screen.getByRole("button",{name:"Reload"}));
 await waitFor(()=>expect(weight).toBeVisible());expect(weight).toHaveValue(74);expect(weight).toBeEnabled();
 expect(screen.getByLabelText("Working weight (lb)")).toBe(weight);
});

test("an authoritative no-session response retires the old view instead of presenting cached work as current",async()=>{
 let missing=false;fixture(url=>missing&&url.endsWith("/workout/today")?Response.json({detail:"No workout scheduled today"},{status:404}):undefined);
 render(<TodayPage/>);fireEvent.click(await screen.findByRole("button",{name:/Resume Press/}));const input=screen.getByLabelText("Working weight (lb)");missing=true;
 fireEvent.click(screen.getByRole("button",{name:"Reload",hidden:true}));await screen.findByText(/Rest day — no workout/);expect(input.isConnected).toBe(false);
});

test("a new account's failed first read cannot retain the previous private view",async()=>{
 setAuthToken("account-a");const pending=deferred<Response>();fixture((url,init)=>{
  const account=new Headers(init?.headers).get("Authorization");
  if(url.endsWith("/workout/today"))return account==="Bearer account-b"?pending.promise:Response.json(workout("Private Account A","private-a"));
  return undefined;
 });
 render(<TodayPage/>);fireEvent.click(await screen.findByRole("button",{name:/Private Account A/}));const old=screen.getByLabelText("Working weight (lb)");
 act(()=>setAuthToken("account-b"));await act(async()=>pending.resolve(Response.json({detail:"offline"},{status:503})));
 await screen.findByText(/Workout could not be loaded/);expect(old.isConnected).toBe(false);expect(screen.queryByText("Private Account A",{exact:false})).not.toBeInTheDocument();
});
