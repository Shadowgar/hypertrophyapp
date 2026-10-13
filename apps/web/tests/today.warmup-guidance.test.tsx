import React from "react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import TodayPage from "@/app/today/page";

const digest = "a".repeat(64);
let guidance: Record<string, any>;
let context: Record<string, any>;
let receipts: Array<Record<string, any>>;
let completed: number;
let writes: Array<{ path: string; body: Record<string, any> }>;
let failFirst: boolean;
let loseAfterCommitFirst: boolean;
let committedReplies: Map<string, Record<string, any>>;
let staleFirst: boolean;
let failUndoProgress: boolean;
let deferLog: boolean;
let releaseLog: () => void;
let variant: boolean;
let constraint: string;
let loadSemantics: string;
let variantLoadSemantics: string;
const sourceInstructions = "Perform the source warm-up protocol before working sets.";
function envelope() {
  return { next_exposure: { id: digest, evidence_revision: digest, scope: "next_exposure", action: "hold", recommended_weight: 50,
    known_baseline_weight: 50, prefill_available: true, reason_codes: [], explanation: "Working advice", evidence: { completed_exposure_count: 2, comparable_completed_exposure_count: 2, actual_rpe_count: 6 }, equipment_feasibility: { limitations: [] }, decision_trace: {} },
    remaining_sets: null, load_context: context, effective_sets: receipts, warmup_guidance: guidance };
}
function exercise() {
  return { id: "press", exercise_occurrence_id: "warm-slot", name: "Warmup Press", sets: 3, completed_sets: completed,
    warm_up_sets: guidance.source_count, load_semantics: loadSemantics, rep_range: [8, 12], recommended_working_weight: 100, warmups: [90],
    source_lineage: { source_slot_id: "press-source" }, load_intelligence: envelope(),
    authored_prescription: { version: "authored-prescription-v1", raw: { warm_up_sets: guidance.source_count }, sets: [1, 2, 3].map(set_index => ({ set_index, set_type: "work", rep_target: { kind: "reps", raw: "8-12", min: 8, max: 12 }, effort_target: { kind: "rpe", raw: "8" }, rest: "90 sec", intensity_technique: null })) },
    authored_constraint: { status: constraint, revision: 0, reasons: constraint === "ready" ? [] : [{ kind: "pain", details: [] }], allowed_alternatives: [{ option_id: "option", id: "alternative", name: "Approved Variant", load_semantics: "external_load", permission: {} }] },
    ...(variant ? { performed_variant: { option_id: "option", id: "alternative", name: "Approved Variant", load_semantics: variantLoadSemantics, permission: {} } } : {}) };
}
beforeEach(() => {
  context = { unit: "kg", display_unit: "lb", basis: "total_external", increment: 0.5, increment_unit: "kg" };
  guidance = { version: "authored-warmup-v1", id: digest, evidence_revision: digest, source_count: "2", count: 2, status: "suggested", source_instructions: sourceInstructions,
    sets: [{ set_index: 1, suggested_weight: 25.25, reps_min: 5, reps_max: 8, percent: 50 }, { set_index: 2, suggested_weight: 35.25, reps_min: 3, reps_max: 4, percent: 70 }], reason_codes: [], explanation: "Source qualified warm-ups", equipment_feasibility: {}, decision_trace: {} };
  receipts = []; completed = 0; writes = []; failFirst = false; loseAfterCommitFirst = false; committedReplies = new Map(); staleFirst = false; failUndoProgress = false; deferLog = false; variant = false; constraint = "ready"; loadSemantics = "external_load"; variantLoadSemantics = "external_load";
  vi.stubGlobal("fetch", vi.fn(async (input, init) => {
    const path = String(input);
    if (path.includes("/plan/scheduling-context?")) return Response.json({ timezone: "UTC", local_today: new Date().toISOString().slice(0, 10), selected_dates: [], placement_revision: 0, plan: null });
    if (path.endsWith("/workout/today")) return Response.json({ session_id: "warm-template", workout_occurrence_id: "warm-occurrence", title: "Warmup fixture", date: new Date().toISOString().slice(0, 10), exercises: [exercise()] });
    if (path.includes("/progress") && failUndoProgress && writes.some(write => write.path.endsWith("/undo-last-set"))) throw new Error("Progress unavailable");
    if (path.includes("/progress")) return Response.json({ completed_total: completed, planned_total: 3, percent_complete: completed / 3 * 100, exercises: [{ exercise_id: "press", exercise_occurrence_id: "warm-slot", completed_sets: completed, load_intelligence: envelope() }] });
    if (path.includes("/soreness")) return Response.json([{ entry_date: new Date().toISOString().slice(0, 10) }]);
    if (init?.method === "POST") {
      const body = JSON.parse(String(init.body)); writes.push({ path, body });
      if (path.endsWith("/load-guidance")) return Response.json(envelope());
      if (path.endsWith("/authored-substitution")) { constraint = body.action === "confirm" ? "confirmed" : "unresolved"; variant = body.action === "confirm"; return Response.json({ exercise: exercise(), workout_occurrence_id: "warm-occurrence" }); }
      if (path.endsWith("/log-set")) {
        const n = writes.filter(w => w.path.endsWith("/log-set")).length;
        const replay = committedReplies.get(body.command_id);
        if (replay) return Response.json(replay);
        if (failFirst && n === 1) throw new Error("Response lost");
        if (staleFirst && n === 1) return Response.json({ detail: { code: "stale_load_recommendation", message: "Load advice changed; review current guidance" } }, { status: 409 });
        if (body.set_kind !== "warmup") completed = body.set_index;
        const receipt = { ...body, id: `receipt-${n}`, created_at: "2026-10-13T12:00:00", set_kind: body.set_kind ?? "work", parent_set_index: body.parent_set_index ?? null, technique: body.technique ?? null };
        receipts = [...receipts, receipt];
        const reply = { ...receipt, load_intelligence: envelope(), live_recommendation: null };
        committedReplies.set(body.command_id, JSON.parse(JSON.stringify(reply)));
        if (loseAfterCommitFirst && n === 1) throw new Error("Committed response lost");
        const response = Response.json(reply);
        if (deferLog) await new Promise<void>(resolve => { releaseLog = resolve; });
        return response;
      }
      if (path.endsWith("/correct")) {
        receipts = receipts.map(r => ({ ...r, ...body, id: "corrected-receipt" }));
        return Response.json({ status: "ok", original_set_id: "receipt-1", effective_set_id: "corrected-receipt", load_intelligence: envelope() });
      }
      if (path.endsWith("/undo-last-set")) { receipts = receipts.slice(0, -1); return Response.json({ status: "ok", load_intelligence: envelope() }); }
    }
    return Response.json({});
  }));
});
afterEach(() => vi.unstubAllGlobals());
async function open() {
  const view = render(<TodayPage />); fireEvent.click(screen.getByRole("button", { name: /Load today's workout/ }));
  fireEvent.click(await screen.findByRole("button", { name: /Warmup Press|Approved Variant/ })); await screen.findByRole("dialog"); return view;
}
function logs() { return writes.filter(w => w.path.endsWith("/log-set")); }

test("server warm-up canonical kg survives restoring the rounded lb display", async () => {
  await open();
  expect(screen.getByText(sourceInstructions)).toBeInTheDocument();
  expect(screen.queryByText("Baseline Calculator")).toBeNull();
  const load = screen.getByRole("spinbutton", { name: "Warm-up 1 load (lb)" });
  expect(load).toHaveValue(55.7);
  fireEvent.change(load, { target: { value: "60" } }); fireEvent.change(load, { target: { value: "55.70" } });
  fireEvent.change(screen.getByRole("spinbutton", { name: "Warm-up 1 actual RPE (optional)" }), { target: { value: "6.5" } });
  fireEvent.click(screen.getByRole("button", { name: "Log warm-up 1" }));
  await waitFor(() => expect(logs()).toHaveLength(1));
  expect(logs()[0].body).toMatchObject({ weight: 25.25, reps: 5, rpe: 6.5, set_index: 1, set_kind: "warmup", parent_set_index: null, technique: null, load_context: context, load_recommendation_id: digest });
  expect(screen.getByText("Set 1/3")).toBeInTheDocument();
  expect(await screen.findByRole("button", { name: "Edit warm-up 1" })).toBeInTheDocument();
});

test("untouched server kg warm-up and edited kg actual load retain full precision", async () => {
  context.display_unit = "kg"; await open();
  expect(screen.getByRole("spinbutton", { name: "Warm-up 1 load (kg)" })).toHaveValue(25.25);
  fireEvent.click(screen.getByRole("button", { name: "Log warm-up 1" }));
  await screen.findByRole("button", { name: "Edit warm-up 1" });
  fireEvent.change(screen.getByRole("spinbutton", { name: "Warm-up 2 load (kg)" }), { target: { value: "31.125" } });
  fireEvent.click(screen.getByRole("button", { name: "Log warm-up 2" }));
  await waitFor(() => expect(logs()).toHaveLength(2));
  expect(logs()[0].body.weight).toBe(25.25); expect(logs()[1].body.weight).toBe(31.125);
});

test("ambiguous warm-up retry keeps its complete immutable command after edited inputs and refresh", async () => {
  failFirst = true; await open(); fireEvent.click(screen.getByRole("button", { name: "Log warm-up 1" }));
  await screen.findByText(/Warm-up was not confirmed/);
  fireEvent.change(screen.getByRole("spinbutton", { name: "Warm-up 1 load (lb)" }), { target: { value: "70" } });
  fireEvent.change(screen.getByRole("spinbutton", { name: "Warm-up 1 reps" }), { target: { value: "10" } });
  guidance = { ...guidance, id: "b".repeat(64), sets: guidance.sets.map((s: any) => ({ ...s, suggested_weight: 30 })) };
  fireEvent.click(screen.getByRole("button", { name: "Preview load guidance" }));
  fireEvent.click(screen.getByRole("button", { name: "Log warm-up 1" }));
  await waitFor(() => expect(logs()).toHaveLength(2)); expect(logs()[1].body).toEqual(logs()[0].body);
  expect(screen.getByText("Set 1/3")).toBeInTheDocument();
  expect(screen.getByRole("spinbutton", { name: "Warm-up 2 actual RPE (optional)" })).toHaveValue(null);
});

test.each([null, "0", "0.0"])("zero or absent source %s preserves text without inventing a warm-up logger", async source => {
  guidance = { ...guidance, source_count: source, count: source == null ? null : 0, status: "none", sets: [] };
  await open(); expect(screen.queryByText(sourceInstructions)).toBeNull();
  expect(screen.queryByRole("button", { name: /Log warm-up/ })).toBeNull();
  expect(screen.getByText(source == null ? "Warm-up prescription unspecified" : `${source} warm-up sets`)).toBeInTheDocument();
});

test("textual counts expose blank manual actual fields and do not parse a numeric prefix", async () => {
  guidance = { ...guidance, source_count: "2-3 as needed", count: null, status: "manual", sets: [] }; await open();
  expect(screen.getByText("2-3 as needed warm-up sets")).toBeInTheDocument();
  expect(screen.getByRole("spinbutton", { name: "Warm-up 1 load (lb)" })).toHaveValue(null);
  expect(screen.getByRole("spinbutton", { name: "Warm-up 1 reps" })).toHaveValue(null);
  expect(screen.getByRole("button", { name: "Log warm-up 1" })).toBeDisabled();
  fireEvent.change(screen.getByRole("spinbutton", { name: "Warm-up 1 load (lb)" }), { target: { value: "40" } });
  fireEvent.change(screen.getByRole("spinbutton", { name: "Warm-up 1 reps" }), { target: { value: "8" } });
  fireEvent.click(screen.getByRole("button", { name: "Log warm-up 1" }));
  await screen.findByRole("button", { name: "Edit warm-up 1" });
  expect(screen.getByRole("spinbutton", { name: "Warm-up 2 load (lb)" })).toHaveValue(null);
});

test("manual numeric guidance never fills a source planned or frontend 1RM load", async () => {
  guidance = { ...guidance, status: "manual", sets: guidance.sets.map((s: any) => ({ ...s, suggested_weight: null })) }; await open();
  expect(screen.getByRole("spinbutton", { name: "Warm-up 1 load (lb)" })).toHaveValue(null);
  expect(screen.getByRole("spinbutton", { name: "Warm-up 2 load (lb)" })).toHaveValue(null);
});

test("refreshed warm-up guidance does not overwrite an edited draft or its canonical origin", async () => {
  await open(); fireEvent.change(screen.getByRole("spinbutton", { name: "Warm-up 1 load (lb)" }), { target: { value: "55.70" } });
  guidance = { ...guidance, id: "b".repeat(64), sets: guidance.sets.map((s: any) => ({ ...s, suggested_weight: 30 })) };
  fireEvent.click(screen.getByRole("button", { name: "Preview load guidance" }));
  await waitFor(() => expect(writes.some(w => w.path.endsWith("/load-guidance"))).toBe(true));
  fireEvent.click(screen.getByRole("button", { name: "Log warm-up 1" }));
  await waitFor(() => expect(logs()).toHaveLength(1)); expect(logs()[0].body.weight).toBe(25.25);
});

test("warm-up receipt correction and undo remain separately labeled and preserve working count", async () => {
  receipts = [{ id: "receipt-1", set_index: 1, set_kind: "warmup", parent_set_index: null, technique: null, reps: 5, weight: 25.25, rpe: 6, created_at: "2026-10-13T12:00:00" }];
  await open(); fireEvent.click(screen.getByRole("button", { name: "Edit warm-up 1" }));
  fireEvent.change(screen.getByRole("spinbutton", { name: "Corrected reps" }), { target: { value: "7" } });
  fireEvent.click(screen.getByRole("button", { name: "Save correction" }));
  await waitFor(() => expect(writes.some(w => w.path.endsWith("/correct"))).toBe(true));
  expect(writes.find(w => w.path.endsWith("/correct"))!.body).toMatchObject({ reps: 7, weight: 25.25 });
  fireEvent.click(screen.getByRole("button", { name: "Undo Last Warm-up" }));
  await waitFor(() => expect(screen.queryByRole("button", { name: "Edit warm-up 1" })).toBeNull());
  expect(screen.getByText("Set 1/3")).toBeInTheDocument();
});

test("confirmed performed variant cannot reuse source warm-up suggestions", async () => {
  variant = true; constraint = "confirmed"; await open();
  expect(screen.getByRole("spinbutton", { name: "Warm-up 1 load (lb)" })).toHaveValue(null);
});

test("unsupported source ladder keeps an exact count with a blank next actual logger", async () => {
  guidance = { ...guidance, source_count: "4", count: 4, status: "manual", sets: [], equipment_feasibility: { limitations: ["No declared plate inventory"] } };
  context.basis = "per_hand"; await open();
  expect(screen.getByText("No declared plate inventory")).toBeInTheDocument();
  expect(screen.getByText(/Warm-up load basis: Per hand/)).toBeInTheDocument();
  expect(screen.getByRole("spinbutton", { name: "Warm-up 1 load (lb)" })).toHaveValue(null);
  expect(screen.getByRole("spinbutton", { name: "Warm-up 1 reps" })).toHaveValue(null);
  expect(screen.queryByRole("button", { name: "Log warm-up 2" })).toBeNull();
});

test("unconfirmed manual warm-up restores its immutable payload after closing and reopening", async () => {
  guidance = { ...guidance, source_count: "As needed", count: null, status: "manual", sets: [] }; failFirst = true;
  await open();
  fireEvent.change(screen.getByRole("spinbutton", { name: "Warm-up 1 load (lb)" }), { target: { value: "40" } });
  fireEvent.change(screen.getByRole("spinbutton", { name: "Warm-up 1 reps" }), { target: { value: "8" } });
  fireEvent.change(screen.getByRole("spinbutton", { name: "Warm-up 1 actual RPE (optional)" }), { target: { value: "6" } });
  fireEvent.click(screen.getByRole("button", { name: "Log warm-up 1" })); await screen.findByText(/Warm-up was not confirmed/);
  fireEvent.click(screen.getByRole("button", { name: "Back to list" }));
  fireEvent.click(await screen.findByRole("button", { name: /Warmup Press/ }));
  expect(screen.getByRole("spinbutton", { name: "Warm-up 1 reps" })).toHaveValue(8);
  expect(screen.getByRole("spinbutton", { name: "Warm-up 1 actual RPE (optional)" })).toHaveValue(6);
  fireEvent.click(screen.getByRole("button", { name: "Log warm-up 1" }));
  await waitFor(() => expect(logs()).toHaveLength(2)); expect(logs()[1].body).toEqual(logs()[0].body);
});

test("load-context invalidation preserves an edited actual warm-up without retaining source advice", async () => {
  await open();
  fireEvent.change(screen.getByRole("spinbutton", { name: "Warm-up 1 load (lb)" }), { target: { value: "60" } });
  fireEvent.change(screen.getByRole("combobox", { name: "Load basis" }), { target: { value: "per_hand" } });
  expect(screen.getByRole("spinbutton", { name: "Warm-up 1 load (lb)" })).toHaveValue(60);
});

test("kg warm-up correction retains edited precision and unknown effort clearing", async () => {
  context.display_unit = "kg";
  receipts = [{ id: "receipt-1", set_index: 1, set_kind: "warmup", parent_set_index: null, technique: null, reps: 5, weight: 25.25, rpe: 6, created_at: "2026-10-13T12:00:00" }];
  await open(); fireEvent.click(screen.getByRole("button", { name: "Edit warm-up 1" }));
  fireEvent.change(screen.getByRole("spinbutton", { name: "Corrected load (kg)" }), { target: { value: "23.125" } });
  fireEvent.change(screen.getByRole("spinbutton", { name: "Corrected actual RPE" }), { target: { value: "" } });
  fireEvent.click(screen.getByRole("button", { name: "Save correction" }));
  await waitFor(() => expect(writes.some(w => w.path.endsWith("/correct"))).toBe(true));
  expect(writes.find(w => w.path.endsWith("/correct"))!.body).toMatchObject({ weight: 23.125, rpe: null });
});

test("stale warm-up advice rejection refreshes and releases only that rejected logical command", async () => {
  staleFirst = true; await open(); fireEvent.click(screen.getByRole("button", { name: "Log warm-up 1" }));
  await screen.findByText(/Load advice changed/);
  fireEvent.click(screen.getByRole("button", { name: "Log warm-up 1" }));
  await waitFor(() => expect(logs()).toHaveLength(2));
  expect(logs()[1].body.command_id).not.toBe(logs()[0].body.command_id);
});


test("confirmed warm-up undo cannot decrement working count when progress refresh fails", async () => {
  completed = 1; failUndoProgress = true;
  receipts = [{ id: "working-receipt", set_index: 1, set_kind: "work", parent_set_index: null, technique: null, reps: 8, weight: 50, rpe: 8, created_at: "2026-10-13T12:00:00" },
    { id: "warmup-receipt", set_index: 1, set_kind: "warmup", parent_set_index: null, technique: null, reps: 5, weight: 25.25, rpe: 6, created_at: "2026-10-13T12:01:00" }];
  await open(); fireEvent.click(screen.getByRole("button", { name: "Undo Last Warm-up" }));
  await waitFor(() => expect(screen.queryByRole("button", { name: "Edit warm-up 1" })).toBeNull());
  expect(screen.getByText("Set 2/3")).toBeInTheDocument();
});

test("context edits retain actual warm-up receipts and the next independent ordinal", async () => {
  guidance = { ...guidance, source_count: "As needed", count: null, status: "manual", sets: [] };
  receipts = [{ id: "warmup-receipt", set_index: 1, set_kind: "warmup", parent_set_index: null, technique: null, reps: 5, weight: 25.25, rpe: 6, created_at: "2026-10-13T12:00:00" }];
  await open();
  fireEvent.change(screen.getByRole("combobox", { name: "Load basis" }), { target: { value: "per_hand" } });
  expect(screen.getByRole("button", { name: "Edit warm-up 1" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Undo Last Warm-up" })).toBeInTheDocument();
  expect(screen.getByRole("spinbutton", { name: "Warm-up 2 load (lb)" })).toHaveValue(null);
  expect(screen.queryByRole("button", { name: "Log warm-up 1" })).toBeNull();
  expect(screen.queryByText("Source qualified warm-ups")).toBeNull();
});


test("late confirmed warm-up retains actual receipt after a context edit while source advice stays invalidated", async () => {
  guidance = { ...guidance, source_count: "As needed", count: null, status: "manual", sets: [] };
  deferLog = true; await open();
  fireEvent.change(screen.getByRole("spinbutton", { name: "Warm-up 1 load (lb)" }), { target: { value: "40" } });
  fireEvent.change(screen.getByRole("spinbutton", { name: "Warm-up 1 reps" }), { target: { value: "8" } });
  fireEvent.click(screen.getByRole("button", { name: "Log warm-up 1" }));
  await waitFor(() => expect(logs()).toHaveLength(1));
  fireEvent.change(screen.getByRole("combobox", { name: "Load basis" }), { target: { value: "per_hand" } });
  await act(async () => { releaseLog(); });
  expect(await screen.findByRole("button", { name: "Edit warm-up 1" })).toBeInTheDocument();
  expect(screen.getByRole("spinbutton", { name: "Warm-up 2 load (lb)" })).toHaveValue(null);
  expect(screen.queryByText("Source qualified warm-ups")).toBeNull();
});


test.each(["total_external", "bodyweight"])("external warm-up zero load is disabled even when the declared basis is %s", async basis => {
  guidance = { ...guidance, status: "manual", sets: guidance.sets.map((set: any) => ({ ...set, suggested_weight: null })) };
  context.basis = basis; await open();
  const load = screen.getByRole("spinbutton", { name: "Warm-up 1 load (lb)" });
  fireEvent.change(load, { target: { value: "0" } });
  const log = screen.getByRole("button", { name: "Log warm-up 1" });
  expect(log).toBeDisabled(); fireEvent.click(log); expect(logs()).toHaveLength(0);
  fireEvent.change(load, { target: { value: "10" } }); expect(log).toBeEnabled();
});

test.each([false, true])("explicitly bodyweight authored warm-up accepts zero actual load (performed variant %s)", async performedVariant => {
  guidance = { ...guidance, status: "manual", sets: guidance.sets.map((set: any) => ({ ...set, suggested_weight: null })) };
  if (performedVariant) { variant = true; variantLoadSemantics = "bodyweight"; constraint = "confirmed"; }
  else loadSemantics = "bodyweight";
  // User-declared basis does not control the exercise's zero-load permission.
  context.basis = "unknown"; await open();
  fireEvent.change(screen.getByRole("spinbutton", { name: "Warm-up 1 load (lb)" }), { target: { value: "0" } });
  const log = screen.getByRole("button", { name: "Log warm-up 1" });
  expect(log).toBeEnabled(); fireEvent.click(log);
  await waitFor(() => expect(logs()).toHaveLength(1));
  expect(logs()[0].body).toMatchObject({ weight: 0, set_kind: "warmup", reps: 5 });
});

test("a confirmed external-load variant removes the source bodyweight zero-load exception", async () => {
  guidance = { ...guidance, status: "manual", sets: guidance.sets.map((set: any) => ({ ...set, suggested_weight: null })) };
  loadSemantics = "bodyweight"; variant = true; constraint = "confirmed"; await open();
  fireEvent.change(screen.getByRole("spinbutton", { name: "Warm-up 1 load (lb)" }), { target: { value: "0" } });
  expect(screen.getByRole("button", { name: "Log warm-up 1" })).toBeDisabled();
  expect(logs()).toHaveLength(0);
});


test("observing the exact committed warm-up command after reload retires its pending retry before undo and a new attempt", async () => {
  loseAfterCommitFirst = true;
  const firstView = await open();
  fireEvent.click(screen.getByRole("button", { name: "Log warm-up 1" }));
  await screen.findByText(/Warm-up was not confirmed/);
  const original = logs()[0].body;
  expect(receipts).toHaveLength(1);
  firstView.unmount(); await open();
  await screen.findByRole("button", { name: "Edit warm-up 1" });
  expect(screen.queryByRole("button", { name: "Log warm-up 1" })).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Undo Last Warm-up" }));
  await screen.findByRole("button", { name: "Log warm-up 1" });
  expect(receipts).toHaveLength(0);
  fireEvent.change(screen.getByRole("spinbutton", { name: "Warm-up 1 reps" }), { target: { value: "7" } });
  fireEvent.click(screen.getByRole("button", { name: "Log warm-up 1" }));
  await screen.findByRole("button", { name: "Edit warm-up 1" });
  expect(logs()).toHaveLength(2);
  expect(logs()[1].body.command_id).not.toBe(original.command_id);
  expect(logs()[1].body).toMatchObject({ reps: 7, weight: 25.25, set_kind: "warmup" });
  expect(receipts).toHaveLength(1);
  expect(receipts[0]).toMatchObject({ reps: 7, command_id: logs()[1].body.command_id });
  expect(screen.getByText("Set 1/3")).toBeInTheDocument();
});

test.each([null, "another-client-command"])("an observed warm-up receipt with command %s does not retire a different unconfirmed command", async observedCommand => {
  failFirst = true;
  const firstView = await open();
  fireEvent.click(screen.getByRole("button", { name: "Log warm-up 1" }));
  await screen.findByText(/Warm-up was not confirmed/);
  const original = logs()[0].body;
  receipts = [{ ...original, command_id: observedCommand, id: "another-receipt", set_kind: "warmup", parent_set_index: null, technique: null, created_at: "2026-10-13T12:00:00" }];
  firstView.unmount(); await open();
  fireEvent.click(await screen.findByRole("button", { name: "Undo Last Warm-up" }));
  await screen.findByRole("button", { name: "Log warm-up 1" });
  fireEvent.change(screen.getByRole("spinbutton", { name: "Warm-up 1 reps" }), { target: { value: "9" } });
  fireEvent.click(screen.getByRole("button", { name: "Log warm-up 1" }));
  await waitFor(() => expect(logs()).toHaveLength(2));
  expect(logs()[1].body).toEqual(original);
});
