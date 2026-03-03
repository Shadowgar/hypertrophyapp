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
  onSetComplete?: (exerciseId: string, setIndex: number) => Promise<void> | void;
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
  const intervalRef = useRef<ReturnType<typeof globalThis.setInterval> | null>(null);

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
    setCompletedSets((prev) => {
      const next = Math.min(prev + 1, totalSets);
      // notify parent of new completed set index
      if (onSetComplete) {
        // fire-and-forget, parent may persist this
        Promise.resolve(onSetComplete(exerciseId, next)).catch(() => {});
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
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-semibold tracking-tight text-accent">{recommendedWorkingWeight}</span>
            <span className="text-sm text-zinc-300">kg</span>
            {repRange ? (
              <span className="ml-auto text-xs text-zinc-400">
                {repRange[0]}-{repRange[1]} reps
              </span>
            ) : null}
          </div>
        </div>
      ) : null}

      <div className="flex items-center justify-between gap-3">
        <div className="flex flex-col">
          <div className="flex items-baseline gap-2">
            <span className="font-mono text-sm">{formatTime(secondsLeft)}</span>
            <span className="text-xs text-zinc-400">REST</span>
          </div>
          <div className="text-xs text-zinc-400">
            Set {completedSets}/{totalSets}
          </div>
          {note ? <div className="text-xs text-zinc-500">{note}</div> : null}
        </div>

        <div
          className="relative h-10 w-10 rounded-full border border-white/15"
          aria-label="Rest countdown ring"
          style={{
            background: `conic-gradient(rgba(220,38,38,0.9) ${(secondsLeft / restCycle) * 360}deg, rgba(255,255,255,0.08) 0deg)`,
          }}
        >
          <div className="absolute inset-[4px] rounded-full bg-black/65" />
        </div>

        <div className="flex gap-2">
          <Button className="h-8 px-3 text-xs" onClick={completeSet} type="button" disabled={completedSets >= totalSets}>
            Complete Set
          </Button>
          {running ? (
            <Button className="h-8 px-3 text-xs" onClick={stopTimer} type="button" variant="secondary">
              Stop
            </Button>
          ) : (
            <Button className="h-8 px-3 text-xs" onClick={startTimer} type="button" variant="secondary">
              Start
            </Button>
          )}

          <Button className="h-8 px-3 text-xs" onClick={resetTimer} type="button" variant="ghost">
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
