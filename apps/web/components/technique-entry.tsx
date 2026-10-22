"use client";
import { useState, useEffect, useRef } from "react";
import { ApiError, type EffectiveLoadSet } from "@/lib/api";
import { Button } from "./ui/button";
import {
  pendingCommandKey,
  pendingLogPayload,
  acknowledgeLogCommand,
} from "@/lib/workout-identity";
export type TechniqueModalState = {
  exerciseId: string;
  exerciseName: string;
  workoutId: string;
  parentSetIndex: number;
  kind: "dropset" | "mechanical_drop" | "rest_pause_cluster";
  baseWeight: number;
  unit: "kg" | "lb";
  baseReps: number;
  authored?: boolean;
  bodyweight?: boolean;
  instruction?: string | null;
} | null;

export function InlineTechniquePanel({
  state,
  onClose,
  onLog,
  scope,
  receipts,
}: Readonly<{
  state: NonNullable<TechniqueModalState>;
  scope: string;
  receipts: EffectiveLoadSet[];
  onClose: () => void;
  onLog: (
    performed: { reps: number; weight: number },
    ordinal: number,
  ) => Promise<void>;
}>) {
  const draftKey = `${scope}:technique-draft:${state.exerciseId}:${state.kind}:${state.parentSetIndex}`;
  const [restored] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(draftKey) ?? "null");
    } catch {
      return null;
    }
  });
  const [ordinal, setOrdinal] = useState<number>(restored?.ordinal ?? 1);
  const [reps, setReps] = useState<string>(restored?.reps ?? "");
  const [weight, setWeight] = useState<string>(
    restored?.weight ?? (state.bodyweight ? "0" : ""),
  );
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState(Boolean(restored?.attempt));
  const inFlight = useRef(false);
  const acknowledgedOrdinals = useRef(new Set<number>());
  const attempted = useRef<{ reps: number; weight: number } | null>(
    restored?.attempt ?? null,
  );
  const [status, setStatus] = useState<string | null>(
    restored?.attempt
      ? "Technique save not confirmed. Retry the same values."
      : null,
  );
  const persist = (
    attempt = attempted.current,
    nextOrdinal = ordinal,
    nextReps = reps,
  ) => {
    try {
      localStorage.setItem(
        draftKey,
        JSON.stringify({
          ordinal: nextOrdinal,
          reps: nextReps,
          weight,
          attempt,
        }),
      );
    } catch {
      /* keep draft in memory */
    }
  };
  useEffect(() => {
    persist();
  }, [ordinal, reps, weight, uncertain]);
  useEffect(() => {
    const key = pendingCommandKey(
      scope,
      state.exerciseId,
      `${state.kind}:${state.parentSetIndex}:${ordinal}`,
    );
    const pending = pendingLogPayload<{ command_id: string }>(key);
    if (pending && receipts.some((r) => r.command_id === pending.command_id)) {
      acknowledgedOrdinals.current.add(ordinal);
      acknowledgeLogCommand(key);
      attempted.current = null;
      setUncertain(false);
      setReps("");
      setOrdinal(ordinal + 1);
      persist(null, ordinal + 1, "");
      setStatus("Technique set confirmed. Add another or close.");
    }
  }, [
    receipts,
    ordinal,
    scope,
    state.exerciseId,
    state.kind,
    state.parentSetIndex,
  ]);

  const title =
    state.kind === "rest_pause_cluster"
      ? "Rest-pause / myo-reps"
      : state.kind === "mechanical_drop"
        ? "Mechanical drop set"
        : "Drop set";

  async function handleLog() {
    if (inFlight.current) return;
    inFlight.current = true;
    setPending(true);
    setStatus("Logging technique set...");
    try {
      const actualReps = Number(reps);
      const actualWeight = Number(weight);
      if (
        !Number.isInteger(actualReps) ||
        actualReps < 1 ||
        !Number.isFinite(actualWeight) ||
        (state.bodyweight ? actualWeight < 0 : actualWeight <= 0)
      ) {
        setStatus(
          "Enter actual reps and external load for this technique set.",
        );
        return;
      }
      const values = attempted.current ?? {
        reps: actualReps,
        weight: actualWeight,
      };
      attempted.current = values;
      persist(values);
      await onLog(values, ordinal);
      attempted.current = null;
      setUncertain(false);
      setReps("");
      acknowledgedOrdinals.current.add(ordinal);
      setOrdinal((prev) => Math.max(prev, ordinal + 1));
      setStatus("Logged. Add another or close.");
    } catch (error) {
      if (acknowledgedOrdinals.current.has(ordinal)) return;
      if (error instanceof ApiError && error.status === 422) {
        attempted.current = null;
        setUncertain(false);
        setStatus(error.message);
      } else {
        setUncertain(true);
        setStatus("Technique save not confirmed. Retry the same values.");
      }
    } finally {
      inFlight.current = false;
      setPending(false);
    }
  }

  return (
    <div className="rounded-xl border border-zinc-700 bg-zinc-900/60 p-3 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-zinc-100">{title}</p>
          <p className="ui-meta">
            {state.exerciseName} · after working set {state.parentSetIndex}
          </p>
        </div>
        <Button
          type="button"
          variant="ghost"
          className="min-h-[32px] px-2 text-xs"
          disabled={pending || uncertain}
          onClick={onClose}
        >
          Close
        </Button>
      </div>

      <div className="rounded-md border border-zinc-800 bg-zinc-900/40 p-3 text-xs text-zinc-300 space-y-1">
        {state.authored ? (
          <p>{state.instruction}</p>
        ) : state.kind === "mechanical_drop" ? (
          <p>
            Keep the same load, change the leverage/position to make it easier,
            then continue.
          </p>
        ) : state.kind === "dropset" ? (
          <p>
            Reduce load and continue with strict form (this logs as a technique
            sub-set).
          </p>
        ) : (
          <p>
            Take a short rest (10–20s), then continue with the same load
            (technique sub-set).
          </p>
        )}
        <p className="text-zinc-400">
          These technique sub-sets do not count as extra working sets.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <label className="flex flex-col gap-1.5">
          <span className="text-[11px] uppercase tracking-wide text-zinc-500">
            Reps
          </span>
          <input
            className="ui-input h-12 w-full rounded-lg px-3 text-center text-lg font-semibold tabular-nums"
            type="number"
            min={1}
            readOnly={pending || uncertain}
            value={reps}
            onChange={(e) => setReps(e.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1.5">
          <span className="text-[11px] uppercase tracking-wide text-zinc-500">
            {state.bodyweight
              ? `Technique added load (${state.unit}), optional`
              : `Technique weight (${state.unit})`}
          </span>
          <input
            className="ui-input h-12 w-full rounded-lg px-3 text-center text-lg font-semibold tabular-nums"
            type="number"
            min={0}
            step={0.5}
            readOnly={pending || uncertain}
            value={weight}
            onChange={(e) => setWeight(e.target.value)}
          />
        </label>
      </div>

      {status ? <p className="text-xs text-zinc-400">{status}</p> : null}

      <Button
        type="button"
        variant="secondary"
        className="min-h-[44px] w-full"
        disabled={pending}
        onClick={handleLog}
      >
        {pending
          ? "Saving technique…"
          : `${uncertain ? "Retry" : "Log"} technique set #${ordinal}`}
      </Button>
    </div>
  );
}
