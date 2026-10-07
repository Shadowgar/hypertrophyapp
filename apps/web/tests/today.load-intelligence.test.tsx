import React from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import TodayPage from "@/app/today/page";

const digest = "b".repeat(64);
const context = { unit: "kg", display_unit: "lb", basis: "total_external", increment: 0.5, increment_unit: "kg" };
const decision = (weight: number | null = 25.25, scope = "next_exposure", action = "increase") => ({
  id: digest, evidence_revision: digest, scope, action, recommended_weight: weight,
  known_baseline_weight: 20, prefill_available: weight !== null, reason_codes: ["qualified"],
  explanation: "Owned explanation from completed comparable exposures.",
  evidence: { completed_exposure_count: 2, comparable_completed_exposure_count: 2,
    consecutive_underperformance_count: 0, actual_rpe_count: 6, required_working_set_count: 3,
    actual_rpe_sufficient: true, effective_set_ids: [], exposure_ids: [] },
  equipment_feasibility: { status: "declared_increment", increment: 0.5, increment_unit: "kg", limitations: [] }, decision_trace: {},
});
let count: number;
let envelope: ReturnType<typeof guidance>;
let writes: Array<{ path: string; body: Record<string, unknown> }>;
let failFirst: boolean;
let staleFirst: boolean;
let validationFirst: boolean;
let correctionValidationFirst: boolean;
let variantFlow: boolean;
let reported: boolean;
let confirmed: boolean;
let deferPreview: boolean;
let deferMutation: boolean;
let releaseMutation: () => void;
let releasePreview: () => void;
let deferProgress: boolean;
let releaseProgress: () => void;
function guidance(weight: number | null = 25.25) {
  return { next_exposure: decision(weight, "next_exposure", weight === null ? "monitor" : "increase"),
    remaining_sets: null as ReturnType<typeof decision> | null, load_context: { ...context, version: "declared-load-context-v1", equipment_tags: ["dumbbell"], equipment_provenance: "profile_tags_not_inventory" },
    effective_sets: [] as Array<{ id: string; set_index: number; reps: number; weight: number; rpe: number | null; created_at: string; set_kind: string | null; parent_set_index: number | null; technique: null }> };
}
function fixtureExercise() {
  return { id: "press", exercise_occurrence_id: "press-slot", name: "Intelligence Press", sets: 3, completed_sets: count,
    rep_range: [8, 12], recommended_working_weight: 50, load_intelligence: confirmed ? null : envelope,
    source_lineage: { source_slot_id: "source-press" },
    ...(variantFlow ? { authored_constraint: { status: reported && !confirmed ? "unresolved" : confirmed ? "confirmed" : "ready",
      revision: confirmed ? 2 : reported ? 1 : 0, reasons: reported ? [{ kind: "pain", details: [] }] : [],
      allowed_alternatives: [{ option_id: "approved-option", id: "approved-variant", name: "Approved Variant", load_semantics: "external_load", permission: { source_slot_id: "source-press" } }] },
      ...(confirmed ? { performed_variant: { option_id: "approved-option", id: "approved-variant", name: "Approved Variant", load_semantics: "external_load", permission: { source_slot_id: "source-press" } }, substitution_consent: { confirmed: true } } : {}) } : {}),
    authored_prescription: { version: "authored-prescription-v1", raw: {}, sets: [1, 2, 3].map(set_index => ({ set_index, set_type: "work", rep_target: { kind: "reps", raw: "8-12", min: 8, max: 12 }, effort_target: { kind: "rpe", raw: "8", min: 8, max: 8 }, rest: "90 sec", intensity_technique: null })) },
  };
}
beforeEach(() => {
  count = 0; envelope = guidance(); writes = []; failFirst = false; staleFirst = false; deferPreview = false; deferMutation = false; validationFirst = false; correctionValidationFirst = false; variantFlow = false; reported = false; confirmed = false; deferProgress = false;
  vi.stubGlobal("fetch", vi.fn(async (input, init) => {
    const url = String(input);
    if (url.includes("/plan/scheduling-context?")) return Response.json({ timezone: "UTC", local_today: new Date().toISOString().slice(0, 10), week_start: "2026-10-05", selected_dates: [], placement_revision: 0, plan: null });
    if (url.endsWith("/workout/today")) return Response.json({ session_id: "template", workout_occurrence_id: "load-occurrence", title: "Synthetic load", date: new Date().toISOString().slice(0, 10), exercises: [fixtureExercise()] });
    if (url.includes("/progress")) {
      const response = Response.json({ completed_total: count, planned_total: 3, percent_complete: count / 3 * 100, exercises: [{ exercise_id: "press", exercise_occurrence_id: "press-slot", completed_sets: count, load_intelligence: envelope }] });
      if (deferProgress) await new Promise<void>(resolve => { releaseProgress = resolve; });
      return response;
    }
    if (url.endsWith("/summary")) return Response.json({ percent_complete: count / 3 * 100, exercises: [{
      exercise_id: "press", name: "Intelligence Press", planned_sets: 3, planned_reps_min: 8, planned_reps_max: 12,
      planned_weight: 20, performed_sets: count, average_performed_reps: 10, average_performed_weight: 20,
      next_working_weight: 99, guidance: "Legacy compatibility cause", load_intelligence: envelope,
    }] });
    if (url.includes("/soreness")) return Response.json([{ entry_date: new Date().toISOString().slice(0, 10) }]);
    if (init?.method === "POST") {
      const body = JSON.parse(String(init.body)); writes.push({ path: url, body });
      if (url.endsWith("/load-guidance")) { const response = Response.json(envelope);
        if (deferPreview) await new Promise<void>(resolve => { releasePreview = resolve; });
        return response;
      }
      if (url.endsWith("/authored-substitution")) { reported = true; if (body.action === "confirm") confirmed = true;
        return Response.json({ exercise: fixtureExercise(), workout_occurrence_id: "load-occurrence" }); }
      if (url.endsWith("/log-set")) {
        if (validationFirst && writes.filter(w => w.path.endsWith("/log-set")).length === 1) return Response.json({ detail: "Actual load rejected before writes" }, { status: 422 });
        if (staleFirst && writes.filter(w => w.path.endsWith("/log-set")).length === 1) return Response.json({ detail: { code: "stale_load_recommendation", message: "Load advice changed; refresh and review the current recommendation" } }, { status: 409 });
        if (failFirst && writes.filter(w => w.path.endsWith("/log-set")).length === 1) throw new Error("Lost response");
        count = Number(body.set_index);
        const response = Response.json({ id: "receipt-1", reps: body.reps, weight: body.weight, rpe: body.rpe, set_index: count, load_intelligence: envelope, live_recommendation: null });
        if (deferMutation) await new Promise<void>(resolve => { releaseMutation = resolve; });
        return response;
      }
      if (url.includes("/correct")) {
        if (correctionValidationFirst && writes.filter(w => w.path.endsWith("/correct")).length === 1) return Response.json({ detail: "Correction rejected before writes" }, { status: 422 });
        const response = Response.json({ status: "ok", original_set_id: "receipt-1", effective_set_id: "receipt-2", load_intelligence: envelope });
        if (deferMutation) await new Promise<void>(resolve => { releaseMutation = resolve; });
        return response;
      }
      if (url.endsWith("/undo-last-set")) { count = 0; envelope = guidance(null); return Response.json({ status: "ok", load_intelligence: envelope }); }
    }
    return Response.json({});
  }));
});
afterEach(() => vi.unstubAllGlobals());
async function open() {
  render(<TodayPage />); fireEvent.click(screen.getByRole("button", { name: /Load today's workout/ }));
  fireEvent.click(await screen.findByRole("button", { name: /Intelligence Press/ }));
  await screen.findByRole("dialog");
}

test("qualified server load owns untouched prefill without display rounding changing canonical kg", async () => {
  await open();
  expect(screen.getByRole("spinbutton", { name: "Weight (lb)" })).toHaveValue(55.7);
  expect(screen.getByText("Owned explanation from completed comparable exposures.")).toBeInTheDocument();
  fireEvent.change(screen.getByRole("spinbutton", { name: /Actual RPE/ }), { target: { value: "8.5" } });
  fireEvent.click(screen.getByRole("button", { name: "Complete Set" }));
  await waitFor(() => expect(writes.some(w => w.path.endsWith("/log-set"))).toBe(true));
  expect(writes.find(w => w.path.endsWith("/log-set"))!.body).toMatchObject({ weight: 25.25, rpe: 8.5, load_recommendation_id: digest, load_context: context });
});

test("focusing and blurring an unchanged prefill preserves the exact canonical performed load", async () => {
  await open();
  const weight = screen.getByRole("spinbutton", { name: "Weight (lb)" });
  fireEvent.focus(weight);
  fireEvent.blur(weight);
  fireEvent.click(screen.getByRole("button", { name: "Complete Set" }));
  await waitFor(() => expect(writes.some(w => w.path.endsWith("/log-set"))).toBe(true));
  expect(writes.find(w => w.path.endsWith("/log-set"))!.body.weight).toBe(25.25);
});

test.each(["log", "correct", "undo"])("a preview from before %s cannot overwrite rebuilt receipt evidence", async operation => {
  if (operation !== "log") {
    count = 1; envelope.remaining_sets = decision(20, "remaining_sets", "hold");
    envelope.effective_sets = [{ id: "receipt-1", set_index: 1, reps: 8, weight: 30, rpe: 8.5, created_at: "2026-10-06T12:00:00", set_kind: "work", parent_set_index: null, technique: null }];
  }
  await open(); deferPreview = true;
  fireEvent.click(screen.getByRole("button", { name: "Preview load guidance" }));
  await waitFor(() => expect(writes.some(w => w.path.endsWith("/load-guidance"))).toBe(true));
  if (operation === "correct") {
    fireEvent.click(screen.getByRole("button", { name: "Back to list" }));
    fireEvent.click(await screen.findByRole("button", { name: /Intelligence Press/ }));
    await screen.findByRole("dialog");
  }
  const receipts = envelope.effective_sets;
  envelope = guidance(); envelope.effective_sets = receipts;
  envelope.remaining_sets = decision(40, "remaining_sets", "decrease");
  envelope.remaining_sets.explanation = "Rebuilt guidance from the changed effective receipts.";
  if (operation === "log") fireEvent.click(screen.getByRole("button", { name: "Complete Set" }));
  else if (operation === "correct") {
    fireEvent.click(screen.getByRole("button", { name: "Edit set 1" }));
    fireEvent.click(screen.getByRole("button", { name: "Save correction" }));
  } else fireEvent.click(screen.getByRole("button", { name: "Undo Last Set" }));
  if (operation === "undo") await waitFor(() => expect(screen.getByRole("spinbutton", { name: "Weight (lb)" })).toHaveValue(null));
  else await screen.findByText("Rebuilt guidance from the changed effective receipts.");
  await act(async () => { releasePreview(); });
  if (operation === "undo") expect(screen.getByRole("spinbutton", { name: "Weight (lb)" })).toHaveValue(null);
  else expect(screen.getByText("Rebuilt guidance from the changed effective receipts.")).toBeInTheDocument();
});

test("manual next-set draft survives a refreshed recommendation and override is recorded", async () => {
  await open();
  fireEvent.change(screen.getByRole("spinbutton", { name: "Weight (lb)" }), { target: { value: "60" } });
  envelope = guidance(30);
  fireEvent.click(screen.getByRole("button", { name: "Preview load guidance" }));
  await waitFor(() => expect(writes.some(w => w.path.endsWith("/load-guidance"))).toBe(true));
  expect(screen.getByRole("spinbutton", { name: "Weight (lb)" })).toHaveValue(60);
  fireEvent.change(screen.getByRole("textbox", { name: "Load override reason (optional)" }), { target: { value: "equipment" } });
  fireEvent.click(screen.getByRole("button", { name: "Complete Set" }));
  await waitFor(() => expect(writes.some(w => w.path.endsWith("/log-set"))).toBe(true));
  expect(writes.find(w => w.path.endsWith("/log-set"))!.body).toMatchObject({ weight: 27.2, load_override_reason: "equipment" });
});

test("unknown monitor displays baseline separately without inferring a zero or planned load", async () => {
  envelope = guidance(null); envelope.load_context = { ...envelope.load_context, basis: "unknown" };
  await open();
  expect(screen.getByRole("spinbutton", { name: "Weight (lb)" })).toHaveValue(null);
  expect(screen.getByRole("combobox", { name: "Load basis" })).toHaveValue("unknown");
  expect(screen.getByText(/Known baseline.*44.1.*lb/)).toBeInTheDocument();
  expect(screen.getByRole("spinbutton", { name: /Actual RPE/ })).toHaveValue(null);
});

test("partial exposure uses remaining-set scope; completed exercise does not prefill next-exposure advice", async () => {
  count = 1; envelope.remaining_sets = decision(20, "remaining_sets", "decrease");
  await open();
  expect(screen.getByRole("spinbutton", { name: "Weight (lb)" })).toHaveValue(44.1);
  expect(screen.getByText(/Remaining sets/)).toBeInTheDocument();
});

test("failed working command retains RPE/context/recommendation and exact request after draft edits", async () => {
  failFirst = true; await open();
  fireEvent.change(screen.getByRole("spinbutton", { name: /Actual RPE/ }), { target: { value: "9" } });
  fireEvent.click(screen.getByRole("button", { name: "Complete Set" }));
  await screen.findByText(/Set was not confirmed/);
  fireEvent.change(screen.getByRole("spinbutton", { name: /Actual RPE/ }), { target: { value: "6" } });
  fireEvent.change(screen.getByRole("spinbutton", { name: "Weight (lb)" }), { target: { value: "70" } });
  fireEvent.click(screen.getByRole("button", { name: "Complete Set" }));
  await waitFor(() => expect(writes.filter(w => w.path.endsWith("/log-set"))).toHaveLength(2));
  const requests = writes.filter(w => w.path.endsWith("/log-set"));
  expect(requests[1].body).toEqual(requests[0].body);
  expect(requests[0].body.rpe).toBe(9);
});

test.each([false, true])("effective receipt correction distinguishes untouched RPE from explicit clearing(%s)", async clear => {
  count = 1; envelope.effective_sets = [{ id: "receipt-1", set_index: 1, reps: 8, weight: 30, rpe: 8.5,
    created_at: "2026-10-06T12:00:00", set_kind: "work", parent_set_index: null, technique: null }];
  await open();
  fireEvent.click(screen.getByRole("button", { name: "Edit set 1" }));
  fireEvent.change(screen.getByRole("spinbutton", { name: "Corrected reps" }), { target: { value: "10" } });
  if (clear) fireEvent.change(screen.getByRole("spinbutton", { name: "Corrected actual RPE" }), { target: { value: "" } });
  fireEvent.click(screen.getByRole("button", { name: "Save correction" }));
  await waitFor(() => expect(writes.some(w => w.path.endsWith("/correct"))).toBe(true));
  const body = writes.find(w => w.path.endsWith("/correct"))!.body;
  expect(body).toMatchObject({ reps: 10, weight: 30 });
  if (clear) expect(body.rpe).toBeNull(); else expect(body).not.toHaveProperty("rpe");
});

test("load-context changes invalidate advice and discard an older in-flight preview", async () => {
  await open(); deferPreview = true;
  fireEvent.click(screen.getByRole("button", { name: "Preview load guidance" }));
  await waitFor(() => expect(writes.some(w => w.path.endsWith("/load-guidance"))).toBe(true));
  fireEvent.change(screen.getByRole("combobox", { name: "Load basis" }), { target: { value: "per_hand" } });
  await waitFor(() => expect(screen.getByRole("spinbutton", { name: "Weight (lb)" })).toHaveValue(null));
  releasePreview();
  await waitFor(() => expect(screen.getByRole("button", { name: "Preview load guidance" })).toBeEnabled());
  expect(screen.getByRole("spinbutton", { name: "Weight (lb)" })).toHaveValue(null);
  expect(screen.queryByText("Owned explanation from completed comparable exposures.")).toBeNull();
});

test("definitive stale-advice rejection refreshes advice and releases only the rejected command", async () => {
  staleFirst = true; await open();
  fireEvent.change(screen.getByRole("spinbutton", { name: /Actual RPE/ }), { target: { value: "9" } });
  fireEvent.click(screen.getByRole("button", { name: "Complete Set" }));
  await screen.findByText(/Load advice changed.*review/);
  expect(screen.getByRole("spinbutton", { name: /Actual RPE/ })).toHaveValue(9);
  await waitFor(() => expect(writes.some(w => w.path.endsWith("/load-guidance"))).toBe(true));
  fireEvent.click(screen.getByRole("button", { name: "Complete Set" }));
  await waitFor(() => expect(writes.filter(w => w.path.endsWith("/log-set"))).toHaveLength(2));
  const requests = writes.filter(w => w.path.endsWith("/log-set"));
  expect(requests[1].body.command_id).not.toBe(requests[0].body.command_id);
  expect(requests[1].body.rpe).toBe(9);
});

test("undo replaces authoritative receipts and clears previously qualified next load", async () => {
  count = 1; envelope.remaining_sets = decision(20, "remaining_sets", "decrease");
  envelope.effective_sets = [{ id: "receipt-1", set_index: 1, reps: 8, weight: 30, rpe: 8.5, created_at: "2026-10-06T12:00:00", set_kind: "work", parent_set_index: null, technique: null }];
  await open(); fireEvent.click(screen.getByRole("button", { name: "Undo Last Set" }));
  await waitFor(() => expect(screen.queryByRole("button", { name: "Edit set 1" })).toBeNull());
  expect(screen.getByRole("spinbutton", { name: "Weight (lb)" })).toHaveValue(null);
  expect(screen.getByRole("button", { name: "Complete Set" })).toBeDisabled();
});

test("completed exercise presents next-exposure advice without prefilling another set", async () => {
  count = 3; await open();
  expect(screen.getByText(/Next exposure.*load guidance/)).toBeInTheDocument();
  expect(screen.getByRole("spinbutton", { name: "Weight (lb)" })).toHaveValue(null);
  expect(screen.getByRole("button", { name: "All Sets Complete" })).toBeDisabled();
});

test("resolved context metadata is omitted from guidance and logging request contracts", async () => {
  await open();
  fireEvent.click(screen.getByRole("button", { name: "Preview load guidance" }));
  await waitFor(() => expect(writes.some(w => w.path.endsWith("/load-guidance"))).toBe(true));
  fireEvent.click(screen.getByRole("button", { name: "Complete Set" }));
  await waitFor(() => expect(writes.some(w => w.path.endsWith("/log-set"))).toBe(true));
  for (const request of writes.filter(w => /load-guidance|log-set/.test(w.path))) expect(request.body.load_context).toEqual(context);
});

test("summary monitor uses owned explanation without presenting legacy next-load advice", async () => {
  count = 3; envelope = guidance(null);
  render(<TodayPage />); fireEvent.click(screen.getByRole("button", { name: /Load today's workout/ }));
  await screen.findByText("Day Summary");
  expect(screen.getByText(/Next exposure: monitor/)).toBeInTheDocument();
  expect(screen.getByText("Owned explanation from completed comparable exposures.")).toBeInTheDocument();
  expect(screen.queryByText(/Next: 218.3/)).toBeNull();
  expect(screen.queryByText("Legacy compatibility cause")).toBeNull();
});


test("first log preserves the offered server display context without requiring a preview", async () => {
  envelope.load_context.display_unit = "kg";
  await open();
  fireEvent.click(screen.getByRole("button", { name: "Complete Set" }));
  await waitFor(() => expect(writes.some(w => w.path.endsWith("/log-set"))).toBe(true));
  expect(writes.find(w => w.path.endsWith("/log-set"))!.body).toMatchObject({ load_recommendation_id: digest, load_context: { display_unit: "kg" } });
});


test.each(["top", "backoff"])("effective %s working receipts remain editable while technique children are excluded", async kind => {
  count = 1;
  envelope.effective_sets = [
    { id: "working-receipt", set_index: 1, reps: 10, weight: 40, rpe: 8, created_at: "2026-10-06T12:00:00", set_kind: kind, parent_set_index: null, technique: null },
    { id: "child-receipt", set_index: 2, reps: 6, weight: 20, rpe: null, created_at: "2026-10-06T12:00:00", set_kind: "drop", parent_set_index: 1, technique: null },
  ];
  await open();
  expect(screen.getByRole("button", { name: "Edit set 1" })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Edit set 2" })).toBeNull();
});


test.each(["log", "correct"])("late %s and progress responses cannot repopulate advice after a declared basis edit", async operation => {
  envelope.remaining_sets = decision(20, "remaining_sets", "hold");
  if (operation === "correct") {
    count = 1;
    envelope.effective_sets = [{ id: "receipt-1", set_index: 1, reps: 8, weight: 30, rpe: 8.5, created_at: "2026-10-06T12:00:00", set_kind: "work", parent_set_index: null, technique: null }];
  }
  await open(); deferMutation = true;
  if (operation === "log") fireEvent.click(screen.getByRole("button", { name: "Complete Set" }));
  else {
    fireEvent.click(screen.getByRole("button", { name: "Edit set 1" }));
    fireEvent.click(screen.getByRole("button", { name: "Save correction" }));
  }
  await waitFor(() => expect(writes.some(w => operation === "log" ? w.path.endsWith("/log-set") : w.path.endsWith("/correct"))).toBe(true));
  fireEvent.change(screen.getByRole("combobox", { name: "Load basis" }), { target: { value: "per_hand" } });
  releaseMutation();
  if (operation === "log") await waitFor(() => expect(screen.getByRole("button", { name: "Complete Set" })).toBeEnabled());
  else await waitFor(() => expect(screen.queryByRole("button", { name: "Save correction" })).toBeNull());
  await waitFor(() => expect(screen.queryByText("Owned explanation from completed comparable exposures.")).toBeNull());
  expect(screen.getByRole("combobox", { name: "Load basis" })).toHaveValue("per_hand");
  expect(screen.getByRole("spinbutton", { name: "Weight (lb)" })).toHaveValue(null);
  if (operation === "log") expect(writes.find(w => w.path.endsWith("/log-set"))!.body.load_context).toMatchObject({ basis: "total_external" });
});


test.each(["cached", "preview", "progress"])("confirmed variant discards cached source advice and deferred projection (%s)", async deferred => {
  variantFlow = true; deferProgress = deferred === "progress"; await open();
  deferPreview = deferred === "preview";
  fireEvent.click(screen.getByRole("button", { name: "Preview load guidance" }));
  await waitFor(() => expect(writes.some(w => w.path.endsWith("/load-guidance"))).toBe(true));
  fireEvent.click(screen.getByRole("button", { name: "Report pain for this slot" }));
  await screen.findByRole("combobox", { name: "Source-approved alternative" });
  fireEvent.change(screen.getByRole("combobox", { name: "Source-approved alternative" }), { target: { value: "approved-option" } });
  fireEvent.click(screen.getByRole("button", { name: "Confirm this alternative" }));
  await screen.findByText("Confirmed performed variant: Approved Variant");
  if (deferred === "preview") releasePreview();
  if (deferred === "progress") releaseProgress();
  await new Promise(resolve => setTimeout(resolve, 0));
  await waitFor(() => expect(screen.getByRole("spinbutton", { name: "Weight (lb)" })).toHaveValue(null));
  expect(screen.queryByText("Owned explanation from completed comparable exposures.")).toBeNull();
  expect(screen.getByRole("combobox", { name: "Load basis" })).toHaveValue("unknown");
});

test.each(["0", "-0.5"])("invalid declared increment %s blocks logging before a retained command exists", async increment => {
  await open(); fireEvent.change(screen.getByRole("spinbutton", { name: "Known increment (optional)" }), { target: { value: increment } });
  fireEvent.change(screen.getByRole("spinbutton", { name: "Weight (lb)" }), { target: { value: "60" } });
  expect(screen.getByRole("button", { name: "Enter a positive increment or leave it blank" })).toBeDisabled();
  fireEvent.change(screen.getByRole("spinbutton", { name: "Known increment (optional)" }), { target: { value: "" } });
  expect(screen.getByRole("button", { name: "Complete Set" })).toBeEnabled();
  expect(writes.some(w => w.path.endsWith("/log-set"))).toBe(false);
});

test("required external actual load rejects zero while monitor keeps an empty load unknown", async () => {
  await open(); fireEvent.change(screen.getByRole("spinbutton", { name: "Weight (lb)" }), { target: { value: "0" } });
  expect(screen.getByRole("button", { name: "Complete Set" })).toBeDisabled();
  expect(writes.some(w => w.path.endsWith("/log-set"))).toBe(false);
});

test("definitive log validation rejection releases only that command and preserves an editable RPE draft", async () => {
  validationFirst = true; await open(); fireEvent.change(screen.getByRole("spinbutton", { name: /Actual RPE/ }), { target: { value: "9" } });
  fireEvent.click(screen.getByRole("button", { name: "Complete Set" }));
  await waitFor(() => expect(screen.getByRole("button", { name: "Complete Set" })).toBeEnabled());
  fireEvent.change(screen.getByRole("spinbutton", { name: "Weight (lb)" }), { target: { value: "60" } });
  fireEvent.change(screen.getByRole("spinbutton", { name: /Actual RPE/ }), { target: { value: "8" } });
  fireEvent.click(screen.getByRole("button", { name: "Complete Set" }));
  await waitFor(() => expect(writes.filter(w => w.path.endsWith("/log-set"))).toHaveLength(2));
  const [before, after] = writes.filter(w => w.path.endsWith("/log-set"));
  expect(after.body.command_id).not.toBe(before.body.command_id);
  expect(after.body).toMatchObject({ weight: 27.2, rpe: 8 });
});

test("definitive correction validation rejection releases its command so revised values can submit", async () => {
  count = 1; correctionValidationFirst = true;
  envelope.effective_sets = [{ id: "receipt-1", set_index: 1, reps: 8, weight: 30, rpe: 8.5, created_at: "2026-10-06T12:00:00", set_kind: "work", parent_set_index: null, technique: null }];
  await open(); fireEvent.click(screen.getByRole("button", { name: "Edit set 1" })); fireEvent.click(screen.getByRole("button", { name: "Save correction" }));
  await screen.findByText("Correction was not confirmed. Retry the same correction.");
  fireEvent.change(screen.getByRole("spinbutton", { name: "Corrected reps" }), { target: { value: "10" } });
  fireEvent.click(screen.getByRole("button", { name: "Save correction" }));
  await waitFor(() => expect(writes.filter(w => w.path.endsWith("/correct"))).toHaveLength(2));
  const [before, after] = writes.filter(w => w.path.endsWith("/correct"));
  expect(after.body.command_id).not.toBe(before.body.command_id);
  expect(after.body.reps).toBe(10);
});
