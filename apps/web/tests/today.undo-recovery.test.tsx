import React from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";

const date = new Date().toISOString().slice(0, 10);
function server(lost: "before" | "after", initial: number, identity: string) {
  let count = initial;
  const writes: { path: string; body: Record<string, any> }[] = [];
  const undos = new Map<string, unknown>();
  let removed = 0;
  let occurrence = identity;
  let evidenceUnavailable = false;
  let restDay = false;
  let rejection: string | null = null;
  const context = { unit: "kg", display_unit: "lb", basis: "total_external" };
  const receipts = () => Array.from({ length: count }, (_, i) => ({ id: `receipt-${i + 1}`, set_index: i + 1, reps: 8, weight: 20, rpe: null, set_kind: "work", parent_set_index: null, technique: null, created_at: date }));
  const guidance = () => ({ next_exposure: null, remaining_sets: null, load_context: context, effective_sets: receipts(), warmup_guidance: {
    source_count: "1", count: 1, status: "suggested", source_instructions: "Source preparation", sets: [{ set_index: 1, suggested_weight: 10, reps_min: 5, reps_max: 8 }], reason_codes: [], explanation: "Source warm-up", equipment_feasibility: {}, decision_trace: {} } });
  const exercise = () => ({ id: "press", exercise_occurrence_id: "press-slot", name: "Recovery Press", sets: 3, completed_sets: count,
    load_semantics: "external_load", rep_range: [8, 12], recommended_working_weight: 20, load_intelligence: guidance(),
    authored_prescription: { version: "authored-prescription-v1", raw: { warm_up_sets: "1" }, sets: [1, 2, 3].map(set_index => ({ set_index, set_type: "work", rep_target: { kind: "reps", raw: "8-12", min: 8, max: 12 }, effort_target: { kind: "rpe", raw: "8" }, rest: "90 sec", intensity_technique: null })) } });
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path.includes("/plan/scheduling-context?")) return Response.json({ timezone: "UTC", local_today: date, selected_dates: [], placement_revision: 0, plan: null });
    if (path.endsWith("/health")) return Response.json({ status: "ok" });
    if (evidenceUnavailable && (path.endsWith("/workout/today") || path.includes("/progress"))) throw new Error("Projection unavailable");
    if (path.endsWith("/workout/today") && restDay) return Response.json({ detail: "No workout scheduled today" }, { status: 404 });
    if (path.endsWith("/workout/today")) return Response.json({ session_id: "template", workout_occurrence_id: occurrence, title: "Recovery workout", date,
      exercises: [exercise(), { id: "row", exercise_occurrence_id: "row-slot", name: "Other Row", sets: 3, completed_sets: 0, rep_range: [8, 12] }] });
    if (path.includes("/progress")) return Response.json({ completed_total: count, planned_total: 6, percent_complete: count / 6 * 100, exercises: [{ exercise_id: "press", exercise_occurrence_id: "press-slot", completed_sets: count, load_intelligence: guidance() }] });
    if (path.includes("/soreness")) return Response.json([{ entry_date: date }]);
    if (init?.method === "POST") {
      const body = JSON.parse(String(init.body)); writes.push({ path, body });
      if (path.endsWith("/undo-last-set")) {
        if (rejection) return Response.json({ detail: rejection }, { status: 409 });
        if (undos.has(body.command_id)) return Response.json(undos.get(body.command_id));
        if (lost === "before" && writes.filter(w => w.path.endsWith("/undo-last-set")).length === 1) throw new Error("Disconnected before commit");
        count -= 1; removed += 1;
        const reply = evidenceUnavailable ? { status: "ok" } : { status: "ok", load_intelligence: guidance() };
        undos.set(body.command_id, reply);
        if (lost === "after" && removed === 1) throw new Error("Committed reply lost");
        return Response.json(reply);
      }
      if (path.endsWith("/log-set")) {
        count = body.set_index;
        return Response.json({ status: "ok", load_intelligence: guidance() });
      }
    }
    return Response.json({});
  }));
  return { writes, count: () => count, removed: () => removed, advance: () => { occurrence = `${identity}-next`; }, evidence: (available: boolean) => { evidenceUnavailable = !available; }, rest: () => { restDay = true; }, reject: (message: string) => { rejection = message; } };
}
async function openPress() {
  const nav = await screen.findByRole("button", { name: /Recovery Press/ });
  fireEvent.click(nav);
  await screen.findByRole("region", { name: "Workout execution" });
  fireEvent.change(screen.getByLabelText("Working weight (lb)"), { target: { value: "44" } });
}
async function failUndo() {
  fireEvent.click(screen.getByRole("button", { name: /^Recorded sets ·/ }));
  fireEvent.click(screen.getByRole("button", { name: "Undo last set" }));
  await screen.findAllByText(/Undo not confirmed/);
}

test.each([["before", 2], ["after", 2], ["after", 1]] as const)("%s-commit undo loss with %s saved sets blocks writes and restores exact recovery on reload", async (lost, initial) => {
  vi.resetModules();
  const { default: TodayPage } = await import("@/app/today/page");
  const simulated = server(lost, initial, `undo-${lost}-${initial}`);
  const view = render(<TodayPage />);
  await openPress();
  await failUndo();
  expect(screen.getByRole("button", { name: "Edit set 1" })).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "Close Recorded sets" }));
  const save = screen.getByRole("button", { name: /^Save set / });
  expect(save).toHaveAttribute("aria-disabled", "true");
  fireEvent.click(save);
  expect(screen.getByLabelText("Working repetitions")).toHaveAttribute("readonly");
  expect(screen.getByRole("button", { name: "Next exercise" })).toBeDisabled();
  expect(screen.getByLabelText("Select exercise")).toBeDisabled();
  for (const button of screen.getAllByRole("button", { name: "Review workout" })) expect(button).toBeDisabled();
  expect(screen.queryByRole("link", { name: "Back to Week" })).not.toBeInTheDocument();
  expect(screen.queryByText("Manage training dates")).not.toBeInTheDocument();
  expect(screen.queryByText("Manage Customized dates or replace program")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /^Warm-up ·/ }));
  expect(screen.getByRole("button", { name: "Log warm-up 1" })).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "Close Warm-up" }));
  expect(simulated.writes).toHaveLength(1);
  view.unmount();
  // Cold imports remove in-memory component and command caches, as a reload does.
  vi.resetModules();
  const { default: ReloadedToday } = await import("@/app/today/page");
  render(<ReloadedToday />);
  await screen.findByRole("region", { name: "Workout execution" });
  expect(screen.getByRole("button", { name: "Retry original undo" })).toBeEnabled();
  fireEvent.click(screen.getByRole("button", { name: /^Save set / }));
  expect(simulated.writes).toHaveLength(1);
  fireEvent.click(screen.getByRole("button", { name: "Retry original undo" }));
  await waitFor(() => expect(screen.queryByRole("button", { name: "Retry original undo" })).not.toBeInTheDocument());
  expect(simulated.writes).toHaveLength(2);
  expect(simulated.writes[1]).toEqual(simulated.writes[0]);
  expect(simulated.removed()).toBe(1);
  expect(simulated.count()).toBe(initial - 1);
  expect(screen.getByText(`SET ${initial} OF 3 · ACTUAL WORK`)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Next exercise" })).toBeEnabled();
  fireEvent.change(screen.getByLabelText("Working repetitions"), { target: { value: "9" } });
  fireEvent.click(screen.getByRole("button", { name: `Save set ${initial}` }));
  await waitFor(() => expect(simulated.writes).toHaveLength(3));
  expect(simulated.writes[2].body.set_index).toBe(initial);
}, 15000);

test("an unconfirmed prior-occurrence undo keeps the next workout read-only", async () => {
  vi.resetModules();
  const { default: TodayPage } = await import("@/app/today/page");
  const simulated = server("before", 2, "previous-undo");
  const view = render(<TodayPage />);
  await openPress();
  await failUndo();
  view.unmount(); simulated.advance();
  render(<TodayPage />);
  await screen.findByText(/previous workout is unconfirmed/i);
  expect(screen.getByRole("button", { name: /Recovery Press/ })).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: /Recovery Press/ }));
  expect(screen.queryByRole("region", { name: "Workout execution" })).not.toBeInTheDocument();
  expect(simulated.writes).toHaveLength(1);
  fireEvent.click(screen.getByRole("button", { name: "Retry original undo" }));
  await waitFor(() => expect(screen.queryByText(/previous workout is unconfirmed/i)).not.toBeInTheDocument());
  expect(simulated.writes[1]).toEqual(simulated.writes[0]);
  expect(simulated.removed()).toBe(1);
  expect(screen.getByRole("button", { name: /Recovery Press/ })).toBeEnabled();
});


test("an acknowledged undo stays frozen until authoritative progress can reconcile", async () => {
  vi.resetModules();
  const { default: TodayPage } = await import("@/app/today/page");
  const simulated = server("before", 2, "undo-progress-unavailable");
  render(<TodayPage />); await openPress(); await failUndo();
  fireEvent.click(screen.getByRole("button", { name: "Close Recorded sets" }));
  simulated.evidence(false);
  fireEvent.click(screen.getByRole("button", { name: "Retry original undo" }));
  await waitFor(() => expect(simulated.writes).toHaveLength(2));
  await waitFor(() => expect(screen.getByRole("button", { name: "Retry original undo" })).toBeEnabled());
  expect(screen.getByRole("button", { name: /^Save set / })).toHaveAttribute("aria-disabled", "true");
  simulated.evidence(true);
  fireEvent.click(screen.getByRole("button", { name: "Retry original undo" }));
  await waitFor(() => expect(screen.queryByRole("button", { name: "Retry original undo" })).not.toBeInTheDocument());
  expect(simulated.writes).toHaveLength(3);
  expect(simulated.writes[1]).toEqual(simulated.writes[0]);
  expect(simulated.writes[2]).toEqual(simulated.writes[0]);
  expect(simulated.removed()).toBe(1);
}, 15000);

test("undo recovery is private to the authenticated account", async () => {
  const token = (sub: string) => `header.${btoa(JSON.stringify({ sub }))}.signature`;
  localStorage.setItem("hypertrophy_token", token("undo-account-one"));
  vi.resetModules();
  const { default: TodayPage } = await import("@/app/today/page");
  const simulated = server("before", 2, "account-scoped-undo");
  const first = render(<TodayPage />); await openPress(); await failUndo(); first.unmount();
  localStorage.setItem("hypertrophy_token", token("undo-account-two"));
  vi.resetModules();
  const { default: OtherAccountToday } = await import("@/app/today/page");
  const other = render(<OtherAccountToday />); await openPress();
  expect(screen.queryByRole("button", { name: "Retry original undo" })).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Next exercise" })).toBeEnabled();
  other.unmount();
  localStorage.setItem("hypertrophy_token", token("undo-account-one"));
  vi.resetModules();
  const { default: OriginalAccountToday } = await import("@/app/today/page");
  render(<OriginalAccountToday />);
  expect(await screen.findByRole("button", { name: "Retry original undo" })).toBeEnabled();
  expect(simulated.writes).toHaveLength(1);
}, 15000);


test("cold reload on a rest day still exposes and reconciles the original undo", async () => {
  vi.resetModules();
  const { default: TodayPage } = await import("@/app/today/page");
  const simulated = server("before", 2, "rest-day-undo");
  const first = render(<TodayPage />); await openPress(); await failUndo(); first.unmount();
  simulated.rest(); vi.resetModules();
  const { default: RestDayToday } = await import("@/app/today/page");
  render(<RestDayToday />);
  await screen.findByText(/Rest day —/);
  expect(screen.getByRole("button", { name: "Retry original undo" })).toBeEnabled();
  fireEvent.click(screen.getByRole("button", { name: "Retry original undo" }));
  await waitFor(() => expect(screen.queryByRole("button", { name: "Retry original undo" })).not.toBeInTheDocument());
  expect(simulated.writes[1]).toEqual(simulated.writes[0]);
  expect(simulated.removed()).toBe(1);
}, 15000);


test.each([
  ["Historical replay context unavailable; original record retained without changes", true],
  ["Command payload conflicts with the recorded request", false],
] as const)("definitive rejection boundary: %s", async (message, definitive) => {
  vi.resetModules();
  const { default: TodayPage } = await import("@/app/today/page");
  const simulated = server("before", 2, `undo-rejected-${definitive}`);
  simulated.reject(message);
  render(<TodayPage />); await openPress();
  fireEvent.click(screen.getByRole("button", { name: /^Recorded sets ·/ }));
  fireEvent.click(screen.getByRole("button", { name: "Undo last set" }));
  if (definitive) {
    await screen.findByText(message);
    expect(screen.getByRole("button", { name: "Edit set 1" })).toBeEnabled();
    expect(screen.queryByRole("button", { name: "Retry original undo" })).not.toBeInTheDocument();
  } else {
    await screen.findAllByText(/Undo not confirmed/);
    expect(screen.getByRole("button", { name: "Edit set 1" })).toBeDisabled();
  }
  fireEvent.click(screen.getByRole("button", { name: "Close Recorded sets" }));
  expect(screen.getByRole("button", { name: "Next exercise" })).toHaveProperty("disabled", !definitive);
  expect(screen.getByRole("button", { name: /^Save set / })).toHaveAttribute("aria-disabled", String(!definitive));
  expect(simulated.count()).toBe(2);
  expect(simulated.removed()).toBe(0);
}, 15000);


test.each([["current", "success"], ["current", "failure"], ["prior", "success"], ["prior", "failure"]] as const)("retired account's %s undo %s cannot block or alter the new account's recovery", async (origin, outcome) => {
  vi.resetModules();
  const { default: TodayPage } = await import("@/app/today/page");
  const { setAuthToken } = await import("@/lib/api");
  const token = (sub: string) => `header.${btoa(JSON.stringify({ sub }))}.signature`;
  const tokenA = token(`undo-live-a-${origin}`); const tokenB = token(`undo-live-b-${origin}`);
  const recoveryKey = (account: string) => `hypertrophy_undo_recovery_v1:${account}:payload`;
  const attempt = (account: string) => ({scope:`hypertrophy_occurrence_v3:${account}:attempt:prior-${account}`,workoutId:`prior-${account}`,exerciseId:"press",exerciseIdentity:"press-slot",exerciseOccurrenceId:"press-slot",command:`original-${account}`});
  localStorage.setItem("hypertrophy_token", tokenA);
  if(origin === "prior") localStorage.setItem(recoveryKey(`undo-live-a-${origin}`),JSON.stringify(attempt(`undo-live-a-${origin}`)));
  localStorage.setItem(recoveryKey(`undo-live-b-${origin}`),JSON.stringify(attempt(`undo-live-b-${origin}`)));
  let oldReply!: (reply: Response) => void;
  let newReply!: (reply: Response) => void;
  const requests: Array<{path:string;account:string}> = [];
  vi.stubGlobal("fetch",vi.fn(async(input,init) => {
    const path=String(input); const old=new Headers(init?.headers).get("Authorization") === `Bearer ${tokenA}`;
    requests.push({path,account:old?"A":"B"});
    if(path.endsWith("/health")) return Response.json({status:"ok"});
    if(path.includes("/plan/scheduling-context?")) return Response.json({timezone:"UTC",local_today:date,selected_dates:[],placement_revision:0,plan:null});
    if(path.endsWith("/workout/today")) return old && origin === "current" ? Response.json({session_id:"template",workout_occurrence_id:"account-a-workout",title:"Account A workout",date,exercises:[{id:"press",exercise_occurrence_id:"press-slot",name:"Recovery Press",sets:3,completed_sets:1,rep_range:[8,12]}]}) : Response.json({detail:"No workout scheduled today"},{status:404});
    if(path.includes("/soreness")) return Response.json([{entry_date:date}]);
    if(path.endsWith("/undo-last-set")) return new Promise<Response>(resolve => {if(old) oldReply=resolve; else newReply=resolve;});
    if(path.endsWith("/progress")) return Response.json({completed_total:old?1:0,planned_total:3,percent_complete:0,exercises:[{exercise_id:"press",exercise_occurrence_id:"press-slot",completed_sets:old?1:0}]});
    return Response.json({});
  }));
  render(<TodayPage/>);
  if(origin === "current") {
    await openPress();
    fireEvent.click(screen.getByRole("button",{name:/Recorded sets ·/}));
    fireEvent.click(screen.getByRole("button",{name:"Undo last set"}));
  } else fireEvent.click(await screen.findByRole("button",{name:"Retry original undo"}));
  await waitFor(() => expect(oldReply).toBeDefined());
  act(() => setAuthToken(tokenB));
  const retry = await screen.findByRole("button",{name:"Retry original undo"});
  expect(retry).toBeEnabled();
  fireEvent.click(retry);
  await waitFor(() => expect(newReply).toBeDefined());
  expect(retry).toBeDisabled();
  await act(async () => oldReply(outcome === "success" ? Response.json({status:"ok"}) : Response.json({detail:"old account unavailable"},{status:503})));
  expect(retry).toBeDisabled();
  expect(screen.queryByText(/Undo (was )?not confirmed/)).not.toBeInTheDocument();
  expect(requests.some(item => item.account === "B" && (item.path.includes("/account-a-workout/") || item.path.includes(`/prior-undo-live-a-${origin}/`)))).toBe(false);
  await act(async () => newReply(Response.json({status:"ok"})));
  await waitFor(() => expect(screen.queryByRole("button",{name:"Retry original undo"})).not.toBeInTheDocument());
  expect(localStorage.getItem(recoveryKey(`undo-live-a-${origin}`))).not.toBeNull();
  expect(localStorage.getItem(recoveryKey(`undo-live-b-${origin}`))).toBeNull();
  vi.unstubAllGlobals();
});
