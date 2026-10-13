"use client";
import { useState } from "react";
import type { EffectiveLoadSet, WorkoutExercise } from "@/lib/api";

export type AuthoredDecision = { action: "report" | "confirm" | "decline"; reason?: "equipment" | "pain" | "safety"; option_id?: string };

export default function AuthoredConstraintCard({ exercise, onDecision, effectiveSets = [], onUndoLastSet }: {
  exercise: WorkoutExercise; onDecision: (decision: AuthoredDecision) => Promise<void>;
  effectiveSets?: EffectiveLoadSet[]; onUndoLastSet?: () => Promise<number | false> | void;
}) {
  const [selected, setSelected] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const constraint = exercise.authored_constraint;
  const unresolved = constraint && ["unresolved", "infeasible", "declined"].includes(constraint.execution_status ?? constraint.status);
  const choices = constraint?.allowed_alternatives ?? [];
  const warmupsBlockResolution = unresolved && !exercise.performed_variant && effectiveSets.length > 0
    && effectiveSets.every(receipt => receipt.set_kind === "warmup" && receipt.parent_set_index == null);
  async function undoWarmup() {
    if (!onUndoLastSet) return;
    setBusy(true); setError("");
    try {
      const result = await onUndoLastSet();
      if (result === false) setError("Warm-up undo was not confirmed. Refresh or retry before choosing an alternative.");
      else setSelected("");
    } catch { setError("Warm-up undo was not confirmed. Refresh or retry before choosing an alternative."); }
    finally { setBusy(false); }
  }
  async function decide(decision: AuthoredDecision) {
    setBusy(true); setError("");
    try { await onDecision(decision); setSelected(""); }
    catch { setError("Decision was not confirmed. Refresh or retry before performing this slot."); }
    finally { setBusy(false); }
  }
  return <section className="space-y-2 rounded border border-zinc-700 p-3" aria-label="Authored exercise constraints">
    <p>Original authored exercise: {exercise.name}</p>
    {exercise.performed_variant ? <p>Confirmed performed variant: {exercise.performed_variant.name}</p> : null}
    {unresolved ? <>
      <p role="status">This source slot remains unresolved. Do not perform it until the conflict is resolved.</p>
      <p>Reason: {constraint.reasons.map(r => r.kind === "restriction" ? "Declared movement restriction" : r.kind === "equipment" ? "Equipment unavailable" : r.kind === "pain" ? "Pain reported" : "Safety concern").join("; ")}</p>
      {warmupsBlockResolution ? <>
        <p>Recorded warm-ups belong to the original exercise. Undo them before choosing or declining an alternative.</p>
        <button type="button" className="min-h-[48px]" disabled={busy || !onUndoLastSet} onClick={undoWarmup}>Undo last warm-up to resolve</button>
      </> : null}
      {choices.length && !exercise.performed_variant ? <>
        <label>Source-approved alternative
          <select aria-label="Source-approved alternative" value={selected} disabled={busy || warmupsBlockResolution} onChange={e => setSelected(e.target.value)}>
            <option value="">Choose an alternative</option>
            {choices.map(choice => <option key={choice.option_id} value={choice.option_id}>{choice.name}</option>)}
          </select>
        </label>
        <button type="button" disabled={!selected || busy || warmupsBlockResolution} onClick={() => decide({ action: "confirm", option_id: selected })}>Confirm this alternative</button>
      </> : <p>No qualified source-approved alternative is available. The slot remains infeasible.</p>}
      {!exercise.performed_variant ? <button type="button" disabled={busy || warmupsBlockResolution} onClick={() => decide({ action: "decline" })}>Decline alternatives</button> : null}
    </> : null}
    <div className="flex flex-wrap gap-2">
      {(["equipment", "pain", "safety"] as const).map(reason => <button type="button" key={reason} disabled={busy} onClick={() => decide({ action: "report", reason })}>
        {reason === "equipment" ? "Report unavailable equipment" : reason === "pain" ? "Report pain for this slot" : "Report safety concern"}
      </button>)}
    </div>
    {error ? <p role="alert">{error}</p> : null}
  </section>;
}
