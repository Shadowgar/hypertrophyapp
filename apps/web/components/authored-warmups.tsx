"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { ApiError, type AuthoredWarmupGuidance, type EffectiveLoadSet, type LoadContext } from "@/lib/api";
import { pendingCommandKey, pendingLogPayload } from "@/lib/workout-identity";
import { kgToLbs, lbsToKg } from "@/lib/weight";

export type PerformedWarmup = { reps: number; weight: number; rpe: number | null };
type WarmupSet = AuthoredWarmupGuidance["sets"][number];

function WarmupInput({ set, unit, suggested, disabled, restored, onLog }: {
  restored: PerformedWarmup | null;
  set: WarmupSet; unit: LoadContext["display_unit"]; suggested: boolean; disabled: boolean;
  onLog: (ordinal: number, performed: PerformedWarmup) => Promise<void>;
}) {
  const canonical = suggested && set.suggested_weight != null && set.suggested_weight > 0 ? set.suggested_weight : null;
  const initialWeight = canonical == null ? "" : String(unit === "kg" ? canonical : kgToLbs(canonical));
  const [weight, setWeight] = useState(restored ? String(unit === "kg" ? restored.weight : kgToLbs(restored.weight)) : initialWeight);
  const [draftUnit, setDraftUnit] = useState(unit);
  const [reps, setReps] = useState(restored ? String(restored.reps) : set.reps_min == null ? "" : String(set.reps_min));
  const [rpe, setRpe] = useState(restored?.rpe == null ? "" : String(restored.rpe));
  const [saving, setSaving] = useState(false);
  const [retryPending, setRetryPending] = useState(Boolean(restored));
  const [status, setStatus] = useState(restored ? "Warm-up was not confirmed. Retry the same warm-up before continuing." : "");
  const edited = useRef(false);
  // Keep the exact canonical origin of an edited/restored rounded display.
  const origin = useRef({ canonical, displayed: initialWeight });
  const pending = useRef<PerformedWarmup | null>(restored);
  const inFlight = useRef(false);
  useEffect(() => {
    if (edited.current || pending.current) return;
    origin.current = { canonical, displayed: initialWeight };
    setDraftUnit(unit);
    setWeight(initialWeight);
    setReps(set.reps_min == null ? "" : String(set.reps_min));
  }, [canonical, initialWeight, set.reps_min, unit, saving]);
  const valid = weight.trim() !== "" && Number.isFinite(Number(weight)) && Number(weight) >= 0 &&
    reps.trim() !== "" && Number.isInteger(Number(reps)) && Number(reps) > 0 &&
    (rpe.trim() === "" || (Number.isFinite(Number(rpe)) && Number(rpe) >= 0 && Number(rpe) <= 10));
  return <div className="space-y-2 rounded-lg border border-zinc-700 p-3">
    <p className="text-sm font-medium">Warm-up {set.set_index}{set.reps_min != null ? ` · ${set.reps_min}${set.reps_max != null && set.reps_max !== set.reps_min ? `–${set.reps_max}` : ""} reps` : " · record actual reps"}</p>
    <div className="grid grid-cols-2 gap-2">
      <label className="text-xs">Warm-up {set.set_index} reps
        <input className="ui-input min-h-[48px] w-full min-w-0" type="number" min={1} step={1} value={reps}
          onChange={event => { edited.current = true; setReps(event.target.value); }} />
      </label>
      <label className="text-xs">Warm-up {set.set_index} load ({draftUnit})
        <input className="ui-input min-h-[48px] w-full min-w-0" type="number" min={0} step="any" value={weight}
          onChange={event => { edited.current = true; setWeight(event.target.value); }} />
      </label>
    </div>
    <label className="block text-xs">Warm-up {set.set_index} actual RPE (optional)
      <input className="ui-input min-h-[48px] w-full" type="number" min={0} max={10} step={0.5} value={rpe}
        onChange={event => { edited.current = true; setRpe(event.target.value); }} />
    </label>
    <Button className="min-h-[48px] w-full" disabled={saving || disabled || (!retryPending && !valid)} onClick={async () => {
      if (inFlight.current || (!pending.current && !valid)) return;
      inFlight.current = true; setSaving(true); setStatus("");
      const performed = pending.current ?? { reps: Number(reps),
        weight: origin.current.canonical != null && Number(weight) === Number(origin.current.displayed)
          ? origin.current.canonical : draftUnit === "kg" ? Number(weight) : lbsToKg(Number(weight)),
        rpe: rpe.trim() === "" ? null : Number(rpe) };
      pending.current = performed; setRetryPending(true);
      try {
        await onLog(set.set_index, performed);
        pending.current = null; setRetryPending(false); edited.current = false; setRpe("");
      } catch (error) {
        if (error instanceof ApiError && (error.status === 422 || (error.status === 409 && error.code === "stale_load_recommendation"))) {
          pending.current = null; setRetryPending(false); setStatus(error.message);
        } else setStatus("Warm-up was not confirmed. Retry the same warm-up before continuing.");
      } finally { inFlight.current = false; setSaving(false); }
    }}>{saving ? "Saving warm-up…" : `Log warm-up ${set.set_index}`}</Button>
    {status ? <p role="status" className="text-xs text-zinc-400">{status}</p> : null}
  </div>;
}

export function AuthoredWarmups({ guidance, sourceCount, receipts, loadContext, performedVariant, disabled, commandScope, exerciseId, onLog }: {
  guidance: AuthoredWarmupGuidance | null | undefined; sourceCount: string | null;
  commandScope: string; exerciseId: string;
  receipts: EffectiveLoadSet[]; loadContext: LoadContext; performedVariant: boolean; disabled: boolean;
  onLog: (ordinal: number, performed: PerformedWarmup) => Promise<void>;
}) {
  // A temporary context invalidation clears advice while keeping existing actual drafts.
  const [lastProjection, setLastProjection] = useState(guidance);
  useEffect(() => { if (guidance) setLastProjection(guidance); }, [guidance]);
  const projection = guidance ?? lastProjection;
  const warmups = receipts.filter(receipt => receipt.set_kind === "warmup");
  const recorded = new Set(warmups.map(receipt => receipt.set_index));
  const countText = projection?.source_count ?? sourceCount;
  const canLog = projection != null && projection.status !== "none";
  const nextOrdinal = Math.max(0, ...recorded) + 1;
  const manualNext = projection?.count == null || (projection.sets.length === 0 && nextOrdinal <= projection.count);
  const sets: WarmupSet[] = !canLog ? [] : manualNext
    ? [{ set_index: nextOrdinal, suggested_weight: null, reps_min: null, reps_max: null, percent: null }]
    : projection!.sets.filter(set => !recorded.has(set.set_index));
  return <section className="space-y-3" aria-label="Authored warm-up guidance">
    <p className="text-sm text-zinc-200">{countText != null ? `${countText} warm-up sets` : "Warm-up prescription unspecified"}</p>
    {projection?.status !== "none" && projection?.source_instructions ? <p className="whitespace-pre-line text-xs text-zinc-300">{projection.source_instructions}</p> : null}
    {guidance?.explanation ? <p className="text-xs text-zinc-400">{guidance.explanation}</p> : null}
    {canLog ? <p className="text-xs text-zinc-400">Record actual warm-ups separately from working sets.{projection?.count == null ? " The source does not specify an exact count." : ""}</p> : null}
    {canLog ? <p className="text-xs text-zinc-400">Warm-up load basis: {({ unknown: "Unknown", total_external: "Total external load", per_hand: "Per hand", machine_stack: "Machine stack", bodyweight: "Bodyweight", added_bodyweight: "Added bodyweight load", assistance: "Assistance" })[loadContext.basis]}</p> : null}
    {canLog && Array.isArray(guidance?.equipment_feasibility.limitations) ? guidance.equipment_feasibility.limitations.filter((limit): limit is string => typeof limit === "string").map((limit, index) => <p className="text-xs text-zinc-400" key={index}>{limit}</p>) : null}
    {sets.map(set => <WarmupInput key={set.set_index} set={set} unit={loadContext.display_unit}
      suggested={guidance?.status === "suggested" && !performedVariant} disabled={disabled} restored={pendingLogPayload<PerformedWarmup>(pendingCommandKey(commandScope, exerciseId, `warmup:${set.set_index}`))} onLog={onLog} />)}
  </section>;
}
