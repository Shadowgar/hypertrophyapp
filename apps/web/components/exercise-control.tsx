"use client";

import React, { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";

type Props = Readonly<{
  exerciseId: string;
  note?: string | null;
  totalSets?: number;
  defaultRestSeconds?: number;
  initialCompletedSets?: number;
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
  onSetComplete,
}: Props) {
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
      className={`glass-layer rounded-lg p-2 text-xs text-zinc-300 ${
        running ? "ring-2 ring-accent/30 animate-pulse" : ""
      }`}
      data-testid={`exercise-control-${exerciseId}`}
      aria-live="polite"
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex flex-col">
          <div className="flex items-baseline gap-2">
            <span className="font-mono text-sm">{formatTime(secondsLeft)}</span>
            <span className="text-xs text-zinc-400">rest</span>
          </div>
          <div className="text-xs text-zinc-400">
            Set {completedSets}/{totalSets}
          </div>
          {note ? <div className="text-xs text-zinc-500">{note}</div> : null}
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
    </div>
  );
}
