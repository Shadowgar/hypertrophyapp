"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ApiError,
  declaredLoadContext,
  type InitialCalibrationCommand,
  type LoadContext,
  type LoadIntelligence,
  type WorkoutExercise,
} from "@/lib/api";
import { canonicalLoad, displayLoad } from "@/lib/appearance";
import { Button } from "./ui/button";

type Props = {
  scope: string;
  exercise: WorkoutExercise;
  context: LoadContext;
  guidance?: LoadIntelligence | null;
  disabled: boolean;
  eligible?: boolean;
  onSave: (
    command: InitialCalibrationCommand,
    isRetry?: boolean,
  ) => Promise<void>;
};
type Draft = {
  method: "manual" | "known_1rm" | "recent_set";
  load: string;
  unit: "lb" | "kg";
  date: string;
  reps: string;
  rir: string;
  setup: string;
  equipment: string;
  basis: LoadContext["basis"];
  attainableUnit: "lb" | "kg";
  grid: boolean;
  values: string;
  min: string;
  step: string;
  max: string;
  confirmed: boolean;
  attempt?: InitialCalibrationCommand;
};
export function AuthoredCalibration(p: Props) {
  const variant = p.exercise.performed_variant?.id ?? p.exercise.id;
  const key = `${p.scope}:initial-calibration:${p.exercise.exercise_occurrence_id}:${variant}`;
  const saved = p.guidance?.calibration;
  const [draft, setDraft] = useState<Draft>(() => {
    try {
      const cached = JSON.parse(localStorage.getItem(key) ?? "null");
      if (cached && typeof cached.load === "string") return { ...cached, attainableUnit: cached.attainableUnit ?? cached.attempt?.calibration.attainable.unit ?? cached.unit };
    } catch {
      /* in-memory fallback */
    }
    const input = saved?.input;
    const attainable = input?.attainable;
    const reportUnit = input?.unit ?? p.context.display_unit;
    return {
      method: input?.method ?? "manual",
      load: input ? String(input.load) : "",
      unit: reportUnit,
      date: input?.observed_date ?? "",
      reps: input?.reps == null ? "" : String(input.reps),
      rir: input?.rir == null ? "" : String(input.rir),
      setup: input?.setup_details ?? "",
      equipment:
        p.context.equipment_key ?? saved?.load_context.equipment_key ?? "",
      basis:
        p.context.basis === "unknown"
          ? (saved?.load_context.basis ?? "unknown")
          : p.context.basis,
      attainableUnit: attainable?.unit ?? p.context.display_unit,
      grid: Boolean(attainable && "min" in attainable),
      values:
        attainable && "values" in attainable
          ? attainable.values.join(", ")
          : "",
      min: attainable && "min" in attainable ? String(attainable.min) : "",
      step: attainable && "step" in attainable ? String(attainable.step) : "",
      max: attainable && "max" in attainable ? String(attainable.max) : "",
      confirmed: Boolean(input?.confirmed && !saved?.requires_confirmation),
    };
  });
  const contextSignature = JSON.stringify(declaredLoadContext(p.context));
  const previousContext = useRef(contextSignature);
  useEffect(() => {
    if (previousContext.current === contextSignature || draft.attempt) return;
    previousContext.current = contextSignature;
    setDraft((current) =>
      current.equipment === (p.context.equipment_key ?? "") &&
      current.basis === p.context.basis
        ? current
        : {
            ...current,
            equipment: p.context.equipment_key ?? "",
            basis: p.context.basis,
            confirmed: false,
          },
    );
  }, [contextSignature, draft.attempt, p.context]);
  const [busy, setBusy] = useState(false);
  const inFlight = useRef(false);
  const [message, setMessage] = useState(
    draft.attempt
      ? "Benchmark save not confirmed. Retry the exact benchmark."
      : "",
  );
  const [storage, setStorage] = useState(true);
  const persist = useCallback(
    (value: Draft) => {
      try {
        localStorage.setItem(key, JSON.stringify(value));
        setStorage(true);
      } catch {
        setStorage(false);
      }
    },
    [key],
  );
  useEffect(() => {
    persist(draft);
  }, [draft, persist]);
  const [offered, setOffered] = useState(p.eligible !== false || Boolean(draft.attempt));
  if (!offered && (p.eligible !== false || draft.attempt)) setOffered(true);
  const locked = p.disabled || busy || Boolean(draft.attempt) || p.eligible === false;
  const unit = draft.attempt ? draft.unit : p.context.display_unit;
  const shownLoad = !draft.load.trim() || unit === draft.unit || !Number.isFinite(Number(draft.load))
    ? draft.load : String(displayLoad(canonicalLoad(Number(draft.load), draft.unit), unit));
  function editBenchmark(value: string) {
    if (locked) return;
    // A new entry is an exact declaration in the displayed unit, not a
    // conversion into a prior report's unit. Equipment keeps its own unit.
    setDraft(d => ({ ...d, load: value, unit, confirmed: false }));
  }
  function changeAttainableUnit(value: "lb" | "kg") {
    if (locked || value === draft.attainableUnit) return;
    setDraft(d => ({ ...d, attainableUnit: value, values: "", min: "", step: "", max: "", confirmed: false }));
  }
  const choices = [
    ["known_1rm", "I know my 1-rep max."],
    ["recent_set", "I know a recent weight and repetitions."],
    ["manual", "I'll choose a comfortable starting weight myself."],
  ] as const;
  function edit<K extends keyof Draft>(field: K, value: Draft[K]) {
    if (locked) return;
    setDraft((d) => ({
      ...d,
      [field]: value,
      ...(field === "method" && ![d.values, d.min, d.step, d.max].some(v => v.trim()) ? { attainableUnit: unit } : {}),
      confirmed: field === "confirmed" ? Boolean(value) : false,
    }));
  }
  const positive = (value: string) =>
    value.trim() !== "" && Number.isFinite(Number(value)) && Number(value) > 0;
  const values = draft.values.split(",").map((v) => v.trim());
  const available = draft.grid
    ? positive(draft.min) &&
      positive(draft.step) &&
      positive(draft.max) &&
      Number(draft.max) >= Number(draft.min)
    : values.length > 0 && values.every(positive);
  const recent =
    draft.method !== "recent_set" ||
    (draft.reps !== "" &&
      Number.isInteger(Number(draft.reps)) &&
      Number(draft.reps) >= 1 &&
      Number(draft.reps) <= 10 &&
      draft.rir !== "" &&
      Number.isFinite(Number(draft.rir)) &&
      Number(draft.rir) >= 0 &&
      Number(draft.rir) <= 3 &&
      Number(draft.reps) + Number(draft.rir) <= 10);
  const valid =
    draft.method !== "manual" &&
    positive(draft.load) &&
    /^\d{4}-\d{2}-\d{2}$/.test(draft.date) &&
    draft.setup.trim() !== "" &&
    draft.equipment.trim() !== "" &&
    ["total_external", "per_hand", "machine_stack"].includes(draft.basis) &&
    available &&
    recent &&
    draft.confirmed;
  async function save() {
    if (
      inFlight.current ||
      p.disabled ||
      (!draft.attempt && (!valid || p.eligible === false)) ||
      !p.exercise.exercise_occurrence_id
    )
      return;
    const command = draft.attempt ?? {
      command_id: crypto.randomUUID(),
      exercise_occurrence_id: p.exercise.exercise_occurrence_id,
      load_context: declaredLoadContext({
        ...p.context,
        basis: draft.basis,
        equipment_key: draft.equipment.trim(),
      }),
      calibration: {
        method: draft.method as "known_1rm" | "recent_set",
        load: Number(draft.load),
        unit: draft.unit,
        observed_date: draft.date,
        ...(draft.method === "recent_set"
          ? { reps: Number(draft.reps), rir: Number(draft.rir) }
          : {}),
        confirmed: true,
        variant_id: variant,
        setup_details: draft.setup.trim(),
        attainable: draft.grid
          ? {
              unit: draft.attainableUnit,
              min: Number(draft.min),
              step: Number(draft.step),
              max: Number(draft.max),
            }
          : { unit: draft.attainableUnit, values: values.map(Number) },
      },
    };
    const retained = { ...draft, attempt: command };
    setDraft(retained);
    persist(retained);
    inFlight.current = true;
    setBusy(true);
    try {
      await p.onSave(command, Boolean(draft.attempt));
      const next = { ...retained, attempt: undefined };
      setDraft(next);
      persist(next);
      setMessage(
        "Benchmark saved. Review the current load guidance; no working set was recorded.",
      );
    } catch (error) {
      // Only schema/domain validation proves this command was rejected before writes.
      // Proxy errors and unknown conflicts retain the original command for retry.
      if (error instanceof ApiError && error.status === 422) {
        const next = { ...retained, attempt: undefined, confirmed: false };
        setDraft(next);
        persist(next);
        setMessage(error.message);
      } else
        setMessage("Benchmark save not confirmed. Retry the exact benchmark.");
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }
  if (!offered && !draft.attempt) return null;
  return (
    <div className="space-y-4 ux-card">
      {p.guidance?.initial_estimate?.status === "unavailable" ? <p className="ux-muted">
        {p.guidance.initial_estimate.explanation.match(/^.*?[.!?](?=\s|$)/)?.[0] ?? "No supported estimate yet. Choose an actual load or review load details."}
      </p> : null}
      {saved ? (
        <p>
          {saved.requires_confirmation
            ? "Confirm that your saved benchmark still represents this exact setup."
            : "Saved benchmark available for this occurrence."}
        </p>
      ) : null}
      <fieldset disabled={locked} className="min-w-0 space-y-4">
        <legend className="font-semibold">Starting weight · optional help</legend>
        {choices.map(([method, label]) => (
          <label className="flex items-start gap-3" key={method}>
            <input type="radio" name={`${key}:path`} value={method}
              checked={draft.method === method}
              disabled={method !== "manual" && p.eligible === false}
              onChange={() => edit("method", method)} />
            {label}
          </label>
        ))}
        {draft.method === "manual" ? <p className="ux-muted">
          Enter your actual load and reps above, then Save Set. No benchmark or equipment form is required.
          Stop for pain or deteriorating technique.
        </p> : null}
        {draft.method !== "manual" ? (
          <>
            <p>
              Use an existing benchmark for{" "}
              {p.exercise.performed_variant?.name ?? p.exercise.name}. No
              maximum test is required. This report is separate from recorded
              workout sets.
            </p>
            <label className="ux-field">
              Benchmark load ({unit})
              <input
                type="number"
                min="0"
                step="any"
                value={shownLoad}
                inputMode="decimal"
                onChange={(e) => editBenchmark(e.target.value)}
              />
            </label>
            {unit !== draft.unit ? <p className="ux-muted">Converted from your saved {draft.unit} values. Unedited loads keep their original precision.</p> : null}
            <label className="ux-field">
              Observed date
              <input
                type="date"
                value={draft.date}
                onChange={(e) => edit("date", e.target.value)}
              />
            </label>
            {draft.method === "recent_set" ? (
              <>
                <label className="ux-field">
                  Benchmark reps (1–10)
                  <input
                    type="number"
                    min="1"
                    max="10"
                    step="1"
                    value={draft.reps}
                    onChange={(e) => edit("reps", e.target.value)}
                  />
                </label>
                <label className="ux-field">
                  Benchmark RIR (0–3)
                  <input
                    type="number"
                    min="0"
                    max="3"
                    step="0.5"
                    value={draft.rir}
                    onChange={(e) => edit("rir", e.target.value)}
                  />
                </label>
                <p>
                  Repetitions left must be known; reps plus RIR must not exceed
                  10.
                </p>
              </>
            ) : null}
            <details className="ux-card space-y-3">
              <summary className="cursor-pointer font-semibold">Equipment and available loads</summary>
              <p className="ux-muted">Required for an estimate, not for logging. Use only this exact setup; no machine conversion is assumed.</p>
            <label className="ux-field">
              Benchmark load basis
              <select
                value={draft.basis}
                onChange={(e) =>
                  edit("basis", e.target.value as Draft["basis"])
                }
              >
                <option value="unknown">Choose basis</option>
                <option value="total_external">Total external load</option>
                <option value="per_hand">Per hand</option>
                <option value="machine_stack">Machine stack</option>
              </select>
            </label>
            <label className="ux-field">
              Equipment identity
              <input
                placeholder="Your name for this exact machine or equipment setup"
                value={draft.equipment}
                onChange={(e) => edit("equipment", e.target.value)}
              />
            </label>
            <label className="ux-field">
              Setup details
              <input
                placeholder="Attachment, grip, settings, side and range of motion"
                value={draft.setup}
                onChange={(e) => edit("setup", e.target.value)}
              />
            </label>
            <p>
              Include attachment, grip, settings, side and range of motion.
              Machine load applies only to this setup.
            </p>
            <label className="ux-field">
              Available load format
              <select
                value={draft.grid ? "grid" : "list"}
                onChange={(e) => edit("grid", e.target.value === "grid")}
              >
                <option value="list">List of available loads</option>
                <option value="grid">Minimum, increment and maximum</option>
              </select>
            </label>
            <label className="ux-field">
              Available load unit
              <select value={draft.attainableUnit} onChange={e => changeAttainableUnit(e.target.value as "lb" | "kg")}>
                <option value="lb">lb</option><option value="kg">kg</option>
              </select>
            </label>
            <p>Available loads in {draft.attainableUnit}, using the same load basis.
              Use the labels on this equipment. Changing units clears this draft list or grid; enter the labeled loads again.
              {draft.attainableUnit !== unit ? ` Your working load displays in ${unit}; these equipment declarations stay in ${draft.attainableUnit}.` : ""}
            </p>
            {draft.grid ? (
              <>
                {(["min", "step", "max"] as const).map((field, index) => (
                  <label className="ux-field" key={field}>
                    {
                      [
                        "Minimum available load",
                        "Available increment",
                        "Maximum available load",
                      ][index]
                    }
                    <input
                      type="number"
                      min="0"
                      step="any"
                      value={draft[field]}
                      onChange={(e) => edit(field, e.target.value)}
                    />
                  </label>
                ))}
              </>
            ) : (
              <label className="ux-field">
                Available loads (comma separated)
                <input
                  value={draft.values}
                  onChange={(e) => edit("values", e.target.value)}
                />
              </label>
            )}
            </details>
            <label className="flex gap-3">
              <input
                type="checkbox"
                checked={draft.confirmed}
                onChange={(e) => edit("confirmed", e.target.checked)}
              />
              I confirm this benchmark still represents this performed variant,
              side, range of motion and exact equipment setup.
            </label>
          </>
        ) : null}
      </fieldset>
      {draft.method !== "manual" && !valid && !draft.attempt ? <p className="ux-muted">
        To estimate, enter the benchmark and date, add equipment and available loads, and confirm the exact setup.
        You can instead record an actual load above without saving a benchmark.
      </p> : null}
      {draft.method !== "manual" || draft.attempt ? (
        <Button
          disabled={busy || p.disabled || (!draft.attempt && (!valid || p.eligible === false))}
          onClick={save}
        >
          {busy
            ? "Saving benchmark…"
            : draft.attempt
              ? "Retry exact benchmark"
              : "Save benchmark and estimate"}
        </Button>
      ) : null}
      {message ? <p role="status">{message}</p> : null}
      {!storage ? (
        <p role="status">
          Benchmark draft is in memory only. Keep this page open until save is
          confirmed.
        </p>
      ) : null}
    </div>
  );
}
