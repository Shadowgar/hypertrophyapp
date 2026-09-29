"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";

/* ------------------------------------------------------------------ */
/*  Hook: useExerciseControl                                          */
/* ------------------------------------------------------------------ */

type UseExerciseControlProps = {
  exerciseId: string;
  totalSets?: number;
  defaultRestSeconds?: number;
  initialCompletedSets?: number;
  recommendedWorkingWeight?: number;
  repRange?: [number, number] | null;
  /** When true, completeSet does not start the rest timer (e.g. parent owns global timer). */
  skipTimerOnComplete?: boolean;
  onSetComplete?: (
    exerciseId: string,
    setIndex: number,
    performed: { reps: number; weight: number },
  ) => Promise<void> | void;
};

export function useExerciseControl({
  exerciseId,
  totalSets = 3,
  defaultRestSeconds = 90,
  initialCompletedSets = 0,
  recommendedWorkingWeight,
  repRange,
  skipTimerOnComplete = false,
  onSetComplete,
}: UseExerciseControlProps) {
  const restCycle = defaultRestSeconds > 0 ? defaultRestSeconds : 1;
  const [secondsLeft, setSecondsLeft] = useState(defaultRestSeconds);
  const [running, setRunning] = useState(false);
  const [completedSets, setCompletedSets] = useState(initialCompletedSets ?? 0);
  const [actualReps, setActualReps] = useState(repRange === null ? 0 : repRange?.[0] ?? 8);
  const [actualWeightInput, setActualWeightInput] = useState(
    recommendedWorkingWeight !== undefined ? String(recommendedWorkingWeight) : "",
  );
  const intervalRef = useRef<ReturnType<typeof globalThis.setInterval> | null>(null);
  const userHasEditedWeightRef = useRef(false);

  useEffect(() => {
    userHasEditedWeightRef.current = false;
  }, [exerciseId]);

  useEffect(() => {
    if (recommendedWorkingWeight !== undefined && !userHasEditedWeightRef.current) {
      setActualWeightInput(String(recommendedWorkingWeight));
    }
  }, [recommendedWorkingWeight]);

  useEffect(() => {
    if (repRange) setActualReps(repRange[0]);
    else if (repRange === null) setActualReps(0);
  }, [repRange]);

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

  const [loggedSets, setLoggedSets] = useState<{ setIndex: number; reps: number; weight: number }[]>([]);

  const submissionPending = useRef(false);
  const [submitting, setSubmitting] = useState(false);
  const completeSet = useCallback(async () => {
    if (submissionPending.current || completedSets >= totalSets) return;
    if (repRange === null && (!Number.isFinite(actualReps) || actualReps < 1)) return;
    submissionPending.current = true;
    setSubmitting(true);
    const parsedWeight = Number(actualWeightInput);
    const hasValidWeight = Number.isFinite(parsedWeight) && parsedWeight > 0;
    const safeReps = Number.isFinite(actualReps) ? Math.max(1, Math.round(actualReps)) : repRange?.[0] ?? 8;
    const safeWeight = hasValidWeight
      ? Math.max(0, Math.round(parsedWeight * 100) / 100)
      : recommendedWorkingWeight ?? 0;

    const next = Math.min(completedSets + 1, totalSets);
    try {
      if (onSetComplete) await onSetComplete(exerciseId, next, { reps: safeReps, weight: safeWeight });
      setCompletedSets(next);
      setLoggedSets((logs) => [...logs, { setIndex: next, reps: safeReps, weight: safeWeight }]);
    } catch {
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
  }, [completedSets, actualWeightInput, actualReps, repRange, recommendedWorkingWeight, totalSets, skipTimerOnComplete, onSetComplete, exerciseId, resetTimer, startTimer]);

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
    setActualReps,
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
  const isDisabled = allDone || ctrl.submitting || Boolean(disableComplete);

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
            onBlur={() => ctrl.markWeightEdited?.()}
            style={{ fontSize: "18px" }}
          />
        </label>
      </div>

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
}>;

export function SetLogDisplay({ ctrl, onUndoLastSet }: SetLogDisplayProps) {
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
      {ctrl.loggedSets.map((entry) => (
        <div
          key={`log-${entry.setIndex}`}
          className="flex items-center justify-between rounded-md border border-red-400/30 bg-red-500/10 px-3 py-1.5 text-sm"
        >
          <span className="font-medium text-zinc-200">Set {entry.setIndex}</span>
          <span className="tabular-nums text-zinc-300">{entry.reps} reps @ {entry.weight} lb</span>
        </div>
      ))}
      {Array.from({ length: ctrl.totalSets - ctrl.loggedSets.length }).map((_, i) => (
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
    performed: { reps: number; weight: number },
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
