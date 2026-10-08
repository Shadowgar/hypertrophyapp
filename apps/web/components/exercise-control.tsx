"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import type { EffectiveLoadSet, LoadContext, LoadIntelligence } from "@/lib/api";
import { ApiError } from "@/lib/api";
import { kgToLbs, lbsToKg } from "@/lib/weight";

export type PerformedSet = { reps: number; weight: number; rpe: number | null; canonicalWeight?: number };

/* ------------------------------------------------------------------ */
/*  Hook: useExerciseControl                                          */
/* ------------------------------------------------------------------ */

type UseExerciseControlProps = {
  exerciseId: string;
  totalSets?: number;
  defaultRestSeconds?: number;
  initialCompletedSets?: number;
  recommendedWorkingWeight?: number;
  recommendedWeightCanonicalKg?: number;
  requireWeight?: boolean;
  repRange?: [number, number] | null;
  /** When true, completeSet does not start the rest timer (e.g. parent owns global timer). */
  skipTimerOnComplete?: boolean;
  onSetComplete?: (
    exerciseId: string,
    setIndex: number,
    performed: PerformedSet,
  ) => Promise<void> | void;
};

export function useExerciseControl({
  exerciseId,
  totalSets = 3,
  defaultRestSeconds = 90,
  initialCompletedSets = 0,
  recommendedWorkingWeight,
  recommendedWeightCanonicalKg,
  requireWeight = false,
  repRange,
  skipTimerOnComplete = false,
  onSetComplete,
}: UseExerciseControlProps) {
  const restCycle = defaultRestSeconds > 0 ? defaultRestSeconds : 1;
  const [secondsLeft, setSecondsLeft] = useState(defaultRestSeconds);
  const [running, setRunning] = useState(false);
  const [completedSets, setCompletedSets] = useState(initialCompletedSets ?? 0);
  const [actualReps, setActualReps] = useState(repRange === null ? 0 : repRange?.[0] ?? 8);
  const [actualRpeInput, setActualRpeInput] = useState("");
  const [actualWeightInput, setActualWeightInput] = useState(
    recommendedWorkingWeight !== undefined ? String(recommendedWorkingWeight) : "",
  );
  const intervalRef = useRef<ReturnType<typeof globalThis.setInterval> | null>(null);
  const userHasEditedWeightRef = useRef(false);
  const userHasEditedRepsRef = useRef(false);
  const pendingPerformed = useRef<PerformedSet | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    userHasEditedWeightRef.current = false;
    userHasEditedRepsRef.current = false;
  }, [exerciseId]);

  useEffect(() => {
    if (!userHasEditedWeightRef.current && !pendingPerformed.current) {
      setActualWeightInput(recommendedWorkingWeight === undefined ? "" : String(recommendedWorkingWeight));
    }
  }, [recommendedWorkingWeight, submitting]);

  useEffect(() => {
    if (userHasEditedRepsRef.current) return;
    if (repRange) setActualReps(repRange[0]);
    else if (repRange === null) setActualReps(0);
  }, [repRange, submitting]);

  useEffect(() => {
    return () => {
      if (intervalRef.current) globalThis.clearInterval(intervalRef.current);
    };
  }, []);

  useEffect(() => {
    if (!running && intervalRef.current) {
      globalThis.clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, [running]);

  const stopTimer = useCallback(() => {
    setRunning(false);
    if (intervalRef.current) {
      globalThis.clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const startTimer = useCallback(() => {
    if (running) return;
    setRunning(true);
    setSecondsLeft((prev) => (prev <= 0 ? defaultRestSeconds : prev));
    intervalRef.current = globalThis.setInterval(() => {
      setSecondsLeft((prev) => {
        if (prev <= 1) {
          stopTimer();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  }, [running, defaultRestSeconds, stopTimer]);

  const resetTimer = useCallback(() => {
    stopTimer();
    setSecondsLeft(defaultRestSeconds);
  }, [stopTimer, defaultRestSeconds]);

  const markWeightEdited = useCallback(() => {
    userHasEditedWeightRef.current = true;
  }, []);
  const changeActualReps = useCallback((value: number) => {
    userHasEditedRepsRef.current = true;
    setActualReps(value);
  }, []);

  const [loggedSets, setLoggedSets] = useState<{ setIndex: number; reps: number; weight: number }[]>([]);

  const submissionPending = useRef(false);
  const validRpe = actualRpeInput.trim() === "" || (Number.isFinite(Number(actualRpeInput)) && Number(actualRpeInput) >= 0 && Number(actualRpeInput) <= 10);
  const validWeight = !requireWeight || (actualWeightInput.trim() !== "" && Number.isFinite(Number(actualWeightInput)) && Number(actualWeightInput) > 0);
  const completeSet = useCallback(async () => {
    if (submissionPending.current || completedSets >= totalSets) return;
    if (repRange === null && (!Number.isFinite(actualReps) || actualReps < 1)) return;
    if (!pendingPerformed.current && (!validRpe || !validWeight)) return;
    submissionPending.current = true;
    setSubmitting(true);
    const parsedWeight = Number(actualWeightInput);
    const hasValidWeight = actualWeightInput.trim() !== "" && Number.isFinite(parsedWeight) && parsedWeight >= 0;
    const safeReps = Number.isFinite(actualReps) ? Math.max(1, Math.round(actualReps)) : repRange?.[0] ?? 8;
    const safeWeight = hasValidWeight
      ? Math.max(0, Math.round(parsedWeight * 100) / 100)
      : recommendedWorkingWeight ?? 0;

    const performed = pendingPerformed.current ?? {
      reps: safeReps, weight: safeWeight, rpe: actualRpeInput.trim() === "" ? null : Number(actualRpeInput),
      ...(safeWeight === recommendedWorkingWeight && recommendedWeightCanonicalKg !== undefined ? { canonicalWeight: recommendedWeightCanonicalKg } : {}),
    };
    pendingPerformed.current = performed;
    const next = Math.min(completedSets + 1, totalSets);
    try {
      if (onSetComplete) await onSetComplete(exerciseId, next, performed);
      pendingPerformed.current = null;
      // The acknowledged receipt closes this draft. The next logical set can
      // adopt its own source target and rebuilt advice; retries keep the guards.
      userHasEditedWeightRef.current = false;
      userHasEditedRepsRef.current = false;
      setActualRpeInput("");
      setCompletedSets(next);
      setLoggedSets((logs) => [...logs, { setIndex: next, reps: performed.reps, weight: performed.weight }]);
    } catch (error) {
      if (error instanceof ApiError && (error.status === 422 || (error.status === 409 && error.code === "stale_load_recommendation"))) pendingPerformed.current = null;
      // Unconfirmed requests keep the logical slot available for the same retry.
      return;
    } finally {
      submissionPending.current = false;
      setSubmitting(false);
    }
    if (!skipTimerOnComplete) {
      resetTimer();
      startTimer();
    }
  }, [completedSets, actualWeightInput, actualReps, actualRpeInput, validRpe, validWeight, repRange, recommendedWorkingWeight, recommendedWeightCanonicalKg, totalSets, skipTimerOnComplete, onSetComplete, exerciseId, resetTimer, startTimer]);

  const undoLastLoggedSet = useCallback((confirmedCompletedSets?: number) => {
    setLoggedSets((logs) => {
      if (logs.length === 0) return logs;
      const nextLogs = logs.slice(0, -1);
      return nextLogs;
    });
    setCompletedSets((prev) => confirmedCompletedSets ?? (prev > 0 ? prev - 1 : 0));
  }, []);

  return {
    submitting,
    secondsLeft,
    restCycle,
    running,
    completedSets,
    totalSets,
    actualReps,
    actualRpeInput,
    setActualRpeInput,
    validRpe,
    validWeight,
    setActualReps: changeActualReps,
    actualWeightInput,
    setActualWeightInput,
    markWeightEdited,
    loggedSets,
    undoLastLoggedSet,
    startTimer,
    stopTimer,
    resetTimer,
    completeSet,
  };
}

export type ExerciseControlState = ReturnType<typeof useExerciseControl>;

export function LoadIntelligencePanel({ guidance, completed, total, loadContext, onContextChange, onPreview, overrideReason, onOverrideReason, onCorrect, requireExternalWeight = false }: {
  guidance: LoadIntelligence | null; completed: number; total: number; loadContext: LoadContext; requireExternalWeight?: boolean;
  onContextChange: (context: LoadContext) => void; onPreview: (context: LoadContext) => Promise<void>;
  overrideReason: string; onOverrideReason: (reason: string) => void;
  onCorrect: (receipt: EffectiveLoadSet, values: { reps: number; weight: number; rpe?: number | null; reason: string }) => Promise<void>;
}) {
  const [pending, setPending] = useState(false);
  const [status, setStatus] = useState("");
  const [increment, setIncrement] = useState(loadContext.increment == null ? "" : String(loadContext.increment));
  const [editing, setEditing] = useState<EffectiveLoadSet | null>(null);
  const [reps, setReps] = useState("");
  const [weight, setWeight] = useState("");
  const [rpe, setRpe] = useState("");
  const [rpeEdited, setRpeEdited] = useState(false);
  const [reason, setReason] = useState("");
  const pendingAction = useRef(false);
  const validIncrement = increment.trim() === "" || (Number.isFinite(Number(increment)) && Number(increment) > 0);
  const shown = completed > 0 && completed < total ? guidance?.remaining_sets : guidance?.next_exposure;
  return <section className="space-y-3 rounded-xl border border-white/10 p-3" aria-label="Load guidance">
    <p className="text-sm font-medium">{completed > 0 && completed < total ? "Remaining sets" : "Next exposure"} load guidance</p>
    {shown ? <>
      <p className="text-sm">{shown.action}{shown.recommended_weight != null ? ` · ${kgToLbs(shown.recommended_weight)} lb` : " · no new load inferred"}</p>
      <p className="text-sm text-zinc-300">{shown.explanation}</p>
      {shown.known_baseline_weight != null ? <p className="text-xs text-zinc-400">Known baseline: {kgToLbs(shown.known_baseline_weight)} lb; separate from newly qualified advice.</p> : null}
      <details><summary className="min-h-[44px] cursor-pointer py-2">Why this load?</summary>
        <p className="text-xs">Completed exposures: {shown.evidence.completed_exposure_count}; comparable: {shown.evidence.comparable_completed_exposure_count}; recorded actual RPE: {shown.evidence.actual_rpe_count}.</p>
        {shown.equipment_feasibility.limitations.map((limitation, index) => <p className="text-xs text-zinc-400" key={index}>{limitation}</p>)}
      </details>
    </> : <p className="text-xs text-zinc-400">No qualified load advice for this set. Enter the actual load you choose.</p>}
    <label className="block text-xs">Load basis
      <select className="ui-select min-h-[48px] w-full" value={loadContext.basis} onChange={event => onContextChange({ ...loadContext, basis: event.target.value as LoadContext["basis"] })}>
        <option value="unknown">Unknown</option><option value="total_external">Total external load</option><option value="per_hand">Per hand</option>
        <option value="machine_stack">Machine stack</option><option value="bodyweight">Bodyweight</option><option value="added_bodyweight">Added bodyweight load</option><option value="assistance">Assistance</option>
      </select>
    </label>
    <label className="block text-xs">Equipment reference (optional)
      <input className="ui-input min-h-[48px] w-full" maxLength={128} value={loadContext.equipment_key ?? ""}
        onChange={event => onContextChange({ ...loadContext, equipment_key: event.target.value.trim() || null })} />
    </label>
    <div className="grid grid-cols-2 gap-2">
      <label className="text-xs">Known increment (optional)
        <input className="ui-input min-h-[48px] w-full" type="number" min={0} step="any" value={increment} onChange={event => {
          setIncrement(event.target.value); const value = event.target.value.trim() === "" ? null : Number(event.target.value);
          onContextChange({ ...loadContext, increment: value, increment_unit: loadContext.increment_unit ?? "lb" });
        }} />
      </label>
      <label className="text-xs">Increment unit
        <select className="ui-select min-h-[48px] w-full" value={loadContext.increment_unit ?? "lb"} onChange={event => onContextChange({ ...loadContext, increment_unit: event.target.value as "lb" | "kg" })}>
          <option value="lb">lb</option><option value="kg">kg</option>
        </select>
      </label>
    </div>
    <Button className="min-h-[48px] w-full" disabled={pending || !validIncrement} onClick={async () => {
      if (pendingAction.current) return; pendingAction.current = true; setPending(true); setStatus("");
      try { await onPreview(loadContext); } catch { setStatus("Load guidance could not be refreshed. Your draft is preserved."); }
      finally { pendingAction.current = false; setPending(false); }
    }}>Preview load guidance</Button>
    <label className="block text-xs">Load override reason (optional)
      <input className="ui-input min-h-[48px] w-full" value={overrideReason} maxLength={500} onChange={event => onOverrideReason(event.target.value)} />
    </label>
    {guidance?.effective_sets.filter(entry => entry.parent_set_index == null && (["work", "working", "top", "backoff"].includes(entry.set_kind?.trim().toLowerCase() || "work"))).map(entry => <div className="rounded border border-white/10 p-2" key={entry.id}>
      <p className="text-xs">Set {entry.set_index}: {entry.reps} reps @ {kgToLbs(entry.weight)} lb · Actual RPE {entry.rpe ?? "unknown"}</p>
      <Button className="min-h-[44px] w-full" variant="secondary" disabled={pending} onClick={() => {
        setEditing(entry); setReps(String(entry.reps)); setWeight(String(kgToLbs(entry.weight))); setRpe(entry.rpe == null ? "" : String(entry.rpe));
        setRpeEdited(false); setReason(""); setStatus("");
      }}>Edit set {entry.set_index}</Button>
    </div>)}
    {editing ? <div className="space-y-2 rounded border border-white/10 p-3">
      <label className="block text-xs">Corrected reps<input className="ui-input min-h-[48px] w-full" type="number" min={1} step={1} value={reps} onChange={e => setReps(e.target.value)} /></label>
      <label className="block text-xs">Corrected load (lb)<input className="ui-input min-h-[48px] w-full" type="number" min={0} step="any" value={weight} onChange={e => setWeight(e.target.value)} /></label>
      <label className="block text-xs">Corrected actual RPE<input className="ui-input min-h-[48px] w-full" type="number" min={0} max={10} step={0.5} value={rpe} onChange={e => { setRpeEdited(true); setRpe(e.target.value); }} /></label>
      <p className="text-xs text-zinc-400">Leave RPE unchanged to preserve it; clear the field to record unknown.</p>
      <label className="block text-xs">Correction reason<input className="ui-input min-h-[48px] w-full" value={reason} maxLength={500} onChange={e => setReason(e.target.value)} /></label>
      <Button className="min-h-[48px] w-full" disabled={pending || !Number.isInteger(Number(reps)) || Number(reps) < 1 || weight.trim() === "" || !Number.isFinite(Number(weight)) || (requireExternalWeight ? Number(weight) <= 0 : Number(weight) < 0) || (rpe.trim() !== "" && (!Number.isFinite(Number(rpe)) || Number(rpe) < 0 || Number(rpe) > 10))} onClick={async () => {
        if (pendingAction.current) return; pendingAction.current = true; setPending(true); setStatus("");
        try { await onCorrect(editing, { reps: Number(reps), weight: Number(weight) === kgToLbs(editing.weight) ? editing.weight : lbsToKg(Number(weight)),
          ...(rpeEdited ? { rpe: rpe.trim() === "" ? null : Number(rpe) } : {}), reason: reason.trim() || "User corrected set" }); setEditing(null); }
        catch { setStatus("Correction was not confirmed. Retry the same correction."); }
        finally { pendingAction.current = false; setPending(false); }
      }}>Save correction</Button>
      <Button variant="ghost" className="min-h-[44px] w-full" disabled={pending} onClick={() => setEditing(null)}>Cancel correction</Button>
    </div> : null}
    {status ? <p role="status" className="text-xs text-zinc-400">{status}</p> : null}
  </section>;
}

/* ------------------------------------------------------------------ */
/*  Utility                                                           */
/* ------------------------------------------------------------------ */

function formatTime(seconds: number) {
  const m = Math.floor(seconds / 60).toString().padStart(2, "0");
  const s = Math.floor(seconds % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

/* ------------------------------------------------------------------ */
/*  SetInputCard                                                      */
/* ------------------------------------------------------------------ */

type SetInputCardProps = Readonly<{
  exerciseId: string;
  guidanceLine: string;
  ctrl: ExerciseControlState;
  weightLabel?: string;
  disableComplete?: boolean;
  disabledReason?: string;
}>;

export function SetInputCard({ exerciseId, guidanceLine, ctrl, weightLabel, disableComplete, disabledReason }: SetInputCardProps) {
  const allDone = ctrl.completedSets >= ctrl.totalSets;
  const isDisabled = allDone || ctrl.submitting || !ctrl.validRpe || !ctrl.validWeight || Boolean(disableComplete);

  return (
    <div className="glass-layer glass-layer--elevated rounded-xl p-4 space-y-3">
      <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">Log Set</p>
      <p className="text-sm text-zinc-200 leading-snug">{guidanceLine}</p>

      <div className="grid grid-cols-2 gap-3">
        <label className="flex flex-col gap-1.5">
          <span className="text-[11px] uppercase tracking-wide text-zinc-500">Reps</span>
          <input
            id={`${exerciseId}-reps`}
            className="ui-input h-12 w-full rounded-lg px-3 text-center text-lg font-semibold tabular-nums"
            type="number"
            min={1}
            value={ctrl.actualReps}
            onChange={(e) => ctrl.setActualReps(Number(e.target.value))}
            style={{ fontSize: "18px" }}
          />
        </label>
        <label className="flex flex-col gap-1.5">
          <span className="text-[11px] uppercase tracking-wide text-zinc-500">{weightLabel ?? "Weight (lb)"}</span>
          <input
            id={`${exerciseId}-weight`}
            className="ui-input h-12 w-full rounded-lg px-3 text-center text-lg font-semibold tabular-nums"
            type="number"
            min={0}
            step={0.5}
            value={ctrl.actualWeightInput}
            onChange={(e) => {
              ctrl.setActualWeightInput(e.target.value);
              ctrl.markWeightEdited?.();
            }}
            style={{ fontSize: "18px" }}
          />
        </label>
      </div>

      <label className="flex flex-col gap-1.5">
        <span className="text-[11px] uppercase tracking-wide text-zinc-500">Actual RPE (optional,0–10)</span>
        <input className="ui-input min-h-[48px] w-full" type="number" min={0} max={10} step={0.5}
          value={ctrl.actualRpeInput} onChange={event => ctrl.setActualRpeInput(event.target.value)} />
        <span className="text-xs text-zinc-500">Your effort on this set. Leave blank when unknown; source targets stay unchanged.</span>
      </label>
      {!ctrl.validRpe ? <p role="alert" className="text-xs text-red-300">Actual RPE must be between0 and10.</p> : null}

      <Button
        className="min-h-[48px] w-full text-sm font-semibold"
        onClick={ctrl.completeSet}
        type="button"
        disabled={isDisabled}
      >
        {ctrl.submitting ? "Saving Set..." : allDone ? "All Sets Complete" : disableComplete ? (disabledReason ?? "Complete technique steps first") : "Complete Set"}
      </Button>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  RestTimerCard                                                     */
/* ------------------------------------------------------------------ */

type RestTimerCardProps = Readonly<{
  ctrl: ExerciseControlState;
  /** When provided, display this rest state instead of ctrl (e.g. global timer from parent). */
  externalRest?: { secondsLeft: number; restCycle: number; onStop?: () => void };
}>;

export function RestTimerCard({ ctrl, externalRest }: RestTimerCardProps) {
  const useExternal = externalRest != null;
  const secondsLeft = useExternal ? externalRest.secondsLeft : ctrl.secondsLeft;
  const restCycle = useExternal ? externalRest.restCycle : ctrl.restCycle;
  const running = useExternal ? externalRest.secondsLeft > 0 : ctrl.running;

  return (
    <div
      className={`glass-layer rounded-xl p-3 transition-all ${
        running ? "ring-2 ring-red-500/30" : ""
      }`}
    >
      <div className="flex items-center gap-3">
        <div
          className="relative flex h-14 w-14 flex-shrink-0 items-center justify-center rounded-full border border-white/15 overflow-hidden"
          aria-label="Rest countdown"
          style={{
            background: `conic-gradient(rgba(220,38,38,0.9) ${(restCycle > 0 ? secondsLeft / restCycle : 0) * 360}deg, rgba(255,255,255,0.08) 0deg)`,
          }}
        >
          <div className="absolute inset-[4px] rounded-full bg-black/65" />
          <span className="relative z-10 font-mono text-xs font-medium tabular-nums text-zinc-100">
            {formatTime(secondsLeft)}
          </span>
        </div>

        <div className="flex-1">
          <p className="text-[10px] uppercase tracking-wide text-zinc-500">Rest Timer</p>
          <p className="text-lg font-semibold tabular-nums text-zinc-100">{formatTime(secondsLeft)}</p>
        </div>

        <div className="flex gap-1.5">
          {useExternal ? (
            running && externalRest.onStop ? (
              <Button className="min-h-[40px] px-3 text-xs" onClick={externalRest.onStop} type="button" variant="secondary">
                Stop
              </Button>
            ) : null
          ) : ctrl.running ? (
            <Button className="min-h-[40px] px-3 text-xs" onClick={ctrl.stopTimer} type="button" variant="secondary">
              Stop
            </Button>
          ) : (
            <Button className="min-h-[40px] px-3 text-xs" onClick={ctrl.startTimer} type="button" variant="secondary">
              Start
            </Button>
          )}
          {!useExternal && (
            <Button className="min-h-[40px] px-3 text-xs" onClick={ctrl.resetTimer} type="button" variant="ghost">
              Reset
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  SetProgressTimeline                                               */
/* ------------------------------------------------------------------ */

type SetProgressTimelineProps = Readonly<{
  exerciseId: string;
  ctrl: ExerciseControlState;
}>;

export function SetProgressTimeline({ exerciseId, ctrl }: SetProgressTimelineProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {Array.from({ length: ctrl.totalSets }).map((_, index) => {
        const setNumber = index + 1;
        const done = setNumber <= ctrl.completedSets;
        return (
          <div
            key={`${exerciseId}-set-${setNumber}`}
            className={`flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs ${
              done
                ? "border-red-400/40 bg-red-500/10 text-red-300"
                : "border-zinc-700 bg-zinc-900/40 text-zinc-500"
            }`}
          >
            <span className={`inline-block h-2 w-2 rounded-full ${done ? "bg-red-400" : "bg-zinc-600"}`} />
            Set {setNumber}
          </div>
        );
      })}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  SetLogDisplay                                                     */
/* ------------------------------------------------------------------ */

type SetLogDisplayProps = Readonly<{
  ctrl: ExerciseControlState;
  onUndoLastSet?: () => Promise<number | false> | void;
  hideLocalReceipts?: boolean;
}>;

export function SetLogDisplay({ ctrl, onUndoLastSet, hideLocalReceipts }: SetLogDisplayProps) {
  const pending = useRef(false);
  const [undoing, setUndoing] = useState(false);
  if (ctrl.loggedSets.length === 0 && ctrl.completedSets === 0) {
    return null;
  }

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">Set Log</p>
        {onUndoLastSet && ctrl.completedSets > 0 ? (
          <Button
            type="button"
            variant="ghost"
            className="px-2 py-0.5 text-[11px] text-zinc-400 hover:text-red-300"
            disabled={undoing || ctrl.submitting}
            onClick={async () => {
              if (pending.current) return;
              pending.current = true;
              setUndoing(true);
              try {
                const confirmed = await onUndoLastSet();
                if (confirmed !== false) ctrl.undoLastLoggedSet(typeof confirmed === "number" ? confirmed : undefined);
              } finally { pending.current = false; setUndoing(false); }
            }}
          >
            Undo Last Set
          </Button>
        ) : null}
      </div>
      {!hideLocalReceipts && ctrl.loggedSets.map((entry) => (
        <div
          key={`log-${entry.setIndex}`}
          className="flex items-center justify-between rounded-md border border-red-400/30 bg-red-500/10 px-3 py-1.5 text-sm"
        >
          <span className="font-medium text-zinc-200">Set {entry.setIndex}</span>
          <span className="tabular-nums text-zinc-300">{entry.reps} reps @ {entry.weight} lb</span>
        </div>
      ))}
      {!hideLocalReceipts && Array.from({ length: Math.max(0, ctrl.totalSets - ctrl.loggedSets.length) }).map((_, i) => (
        <div
          key={`pending-${ctrl.loggedSets.length + i + 1}`}
          className="flex items-center justify-between rounded-md border border-zinc-700 bg-zinc-900/40 px-3 py-1.5 text-sm"
        >
          <span className="text-zinc-500">Set {ctrl.loggedSets.length + i + 1}</span>
          <span className="text-zinc-600">pending</span>
        </div>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Legacy default export (backward compat during transition)         */
/* ------------------------------------------------------------------ */

type LegacyProps = Readonly<{
  exerciseId: string;
  note?: string | null;
  totalSets?: number;
  defaultRestSeconds?: number;
  initialCompletedSets?: number;
  recommendedWorkingWeight?: number;
  repRange?: [number, number] | null;
  onSetComplete?: (
    exerciseId: string,
    setIndex: number,
    performed: PerformedSet,
  ) => Promise<void> | void;
}>;

export default function ExerciseControlModule(props: LegacyProps) {
  const ctrl = useExerciseControl(props);

  const guidanceLine = props.repRange
    ? `${props.repRange[0]}-${props.repRange[1]} reps @ ${props.recommendedWorkingWeight ?? "?"} lbs`
    : "";

  return (
    <div className="space-y-3" data-testid={`exercise-control-${props.exerciseId}`} aria-live="polite">
      <SetInputCard exerciseId={props.exerciseId} guidanceLine={guidanceLine} ctrl={ctrl} />
      <RestTimerCard ctrl={ctrl} />
      <SetProgressTimeline exerciseId={props.exerciseId} ctrl={ctrl} />
    </div>
  );
}
