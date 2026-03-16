"use client";

import React, { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";

type Props = Readonly<{
  exerciseId: string;
  note?: string | null;
  totalSets?: number;
  defaultRestSeconds?: number;
  initialCompletedSets?: number;
  recommendedWorkingWeight?: number;
  repRange?: [number, number];
  onSetComplete?: (
    exerciseId: string,
    setIndex: number,
    performed: { reps: number; weight: number },
  ) => Promise<void> | void;
}>;

function formatTime(seconds: number) {
  const m = Math.floor(seconds / 60)
    .toString()
    .padStart(2, "0");
  const s = Math.floor(seconds % 60)
    .toString()
    .padStart(2, "0");
  return `${m}:${s}`;
}

export default function ExerciseControlModule({
  exerciseId,
  note,
  totalSets = 3,
  defaultRestSeconds = 90,
  initialCompletedSets = 0,
  recommendedWorkingWeight,
  repRange,
  onSetComplete,
}: Props) {
  const restCycle = defaultRestSeconds > 0 ? defaultRestSeconds : 1;
  const [secondsLeft, setSecondsLeft] = useState<number>(defaultRestSeconds);
  const [running, setRunning] = useState<boolean>(false);
  const [completedSets, setCompletedSets] = useState<number>(initialCompletedSets ?? 0);
  const [actualReps, setActualReps] = useState<number>(repRange?.[0] ?? 8);
  const [actualWeightInput, setActualWeightInput] = useState<string>(
    recommendedWorkingWeight !== undefined ? String(recommendedWorkingWeight) : "",
  );
  const intervalRef = useRef<ReturnType<typeof globalThis.setInterval> | null>(null);

  useEffect(() => {
    if (recommendedWorkingWeight !== undefined) {
      setActualWeightInput(String(recommendedWorkingWeight));
    }
  }, [recommendedWorkingWeight]);

  useEffect(() => {
    if (repRange) {
      setActualReps(repRange[0]);
    }
  }, [repRange]);

  useEffect(() => {
    return () => stopTimer();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!running && intervalRef.current) {
      globalThis.clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, [running]);

  function startTimer() {
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
  }

  function stopTimer() {
    setRunning(false);
    if (intervalRef.current) {
      globalThis.clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }

  function resetTimer() {
    stopTimer();
    setSecondsLeft(defaultRestSeconds);
  }

  function completeSet() {
    const parsedWeight = Number(actualWeightInput);
    const hasValidWeight = Number.isFinite(parsedWeight) && parsedWeight > 0;
    const safeReps = Number.isFinite(actualReps) ? Math.max(1, Math.round(actualReps)) : repRange?.[0] ?? 8;
    const safeWeight = hasValidWeight
      ? Math.max(0, Math.round(parsedWeight * 100) / 100)
      : recommendedWorkingWeight ?? 0;

    setCompletedSets((prev) => {
      const next = Math.min(prev + 1, totalSets);
      // notify parent of new completed set index
      if (onSetComplete) {
        // fire-and-forget, parent may persist this
        Promise.resolve(onSetComplete(exerciseId, next, { reps: safeReps, weight: safeWeight })).catch(() => {});
      }
      return next;
    });
    resetTimer();
    startTimer();
  }

  return (
    <div
      className={`glass-layer glass-layer--elevated rounded-xl p-3 text-xs text-zinc-300 ${
        running ? "ring-2 ring-accent/30 animate-pulse" : ""
      }`}
      data-testid={`exercise-control-${exerciseId}`}
      aria-live="polite"
    >
      {typeof recommendedWorkingWeight === "number" ? (
        <div className="mb-2 rounded-lg border border-white/10 bg-black/25 px-3 py-2">
          <p className="text-[10px] uppercase tracking-wide text-zinc-500 mb-1">Suggested weight (editable below)</p>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-semibold tracking-tight text-accent">{recommendedWorkingWeight}</span>
            <span className="text-sm text-zinc-300">lbs</span>
            {repRange ? (
              <span className="ml-auto text-xs text-zinc-400">
                {repRange[0]}-{repRange[1]} reps
              </span>
            ) : null}
          </div>
        </div>
      ) : null}

      <div className="flex items-center justify-between gap-3">
        <div className="flex flex-col gap-2">
          <p className="text-[10px] uppercase tracking-wide text-zinc-500">Rest timer</p>
          <p className="text-xs text-zinc-400">
            Tap <strong>Start</strong> after a set to count rest (e.g. 90s). The circle shows time left. Tap <strong>Stop</strong> to pause.
          </p>
          <div className="text-xs text-zinc-400">
            Set {completedSets}/{totalSets}
          </div>
          {note ? <div className="text-xs text-zinc-500">{note}</div> : null}
          <div className="flex items-center gap-2">
            <label className="text-xs uppercase tracking-wide text-zinc-500" htmlFor={`${exerciseId}-actual-reps`}>
              Actual reps
            </label>
            <input
              id={`${exerciseId}-actual-reps`}
              className="ui-input h-8 w-20 px-2 py-1 text-xs"
              type="number"
              min={1}
              value={actualReps}
              onChange={(event) => setActualReps(Number(event.target.value))}
            />
            <label className="text-xs uppercase tracking-wide text-zinc-500" htmlFor={`${exerciseId}-actual-weight`}>
              Actual lbs
            </label>
            <input
              id={`${exerciseId}-actual-weight`}
              className="ui-input h-8 w-24 px-2 py-1 text-xs"
              type="number"
              min={0}
              step={0.5}
              value={actualWeightInput}
              onChange={(event) => setActualWeightInput(event.target.value)}
            />
          </div>
        </div>

        <div
          className="relative z-0 flex flex-shrink-0 h-12 w-12 items-center justify-center rounded-full border border-white/15 overflow-hidden"
          aria-label="Rest countdown: red segment shows time left"
          style={{
            background: `conic-gradient(rgba(220,38,38,0.9) ${(secondsLeft / restCycle) * 360}deg, rgba(255,255,255,0.08) 0deg)`,
          }}
        >
          <div className="absolute inset-[4px] rounded-full bg-black/65" />
          <span className="relative z-10 font-mono text-[10px] font-medium tabular-nums text-zinc-100">
            {formatTime(secondsLeft)}
          </span>
        </div>

        <div className="relative z-10 flex flex-wrap gap-2 min-w-0">
          <Button className="min-h-[44px] px-3 text-xs" onClick={completeSet} type="button" disabled={completedSets >= totalSets}>
            Complete Set
          </Button>
          {running ? (
            <Button className="min-h-[44px] px-3 text-xs" onClick={stopTimer} type="button" variant="secondary">
              Stop
            </Button>
          ) : (
            <Button className="min-h-[44px] px-3 text-xs" onClick={startTimer} type="button" variant="secondary">
              Start
            </Button>
          )}

          <Button className="min-h-[44px] px-3 text-xs" onClick={resetTimer} type="button" variant="ghost">
            Reset
          </Button>
        </div>
      </div>

      <div className="mt-2 space-y-1.5">
        {Array.from({ length: totalSets }).map((_, index) => {
          const setNumber = index + 1;
          const done = setNumber <= completedSets;
          return (
            <div
              key={`${exerciseId}-set-${setNumber}`}
              className={`flex items-center justify-between rounded-md border px-2 py-1 ${
                done ? "border-red-400/40 bg-red-500/10" : "border-white/10 bg-black/20"
              }`}
            >
              <span className="text-xs text-zinc-200">Set {setNumber}</span>
              <span className={`text-[10px] uppercase tracking-wide ${done ? "text-red-300" : "text-zinc-500"}`}>
                {done ? "Done" : "Pending"}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
