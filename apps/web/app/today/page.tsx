"use client";
import AuthoredConstraintCard, { type AuthoredDecision } from "@/components/AuthoredConstraintCard";

import { authoredRepLabel, authoredSetRepRange, authoredSetDetails, authoredWarmupLabel, isBodyweightAuthored, authoredSetTechnique } from "@/lib/authored-prescription";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Disclosure } from "@/components/ui/disclosure";
import { UiIcon } from "@/components/ui/icons";
import {
  useExerciseControl,
  SetInputCard,
  RestTimerCard,
  SetProgressTimeline,
  SetLogDisplay,
  LoadIntelligencePanel,
  type PerformedSet,
} from "@/components/exercise-control";
import {
  api,
  ApiError,
  type SorenessSeverity,
  type WorkoutExercise,
  type WorkoutLiveRecommendation,
  type WorkoutSession,
  type WorkoutSetFeedback,
  type WorkoutSummary,
  type LoadContext,
  type LoadIntelligence,
  type EffectiveLoadSet,
} from "@/lib/api";
import {
  epleyEstimate1RMLbs,
  warmupsFromWorkingWeightLb,
  workingWeightFrom1RMLb,
} from "@/lib/oneRepMax";
import { parseRestToSeconds } from "@/lib/rest";
import { authoredRelationshipLabels } from "@/lib/authored-relationships";
import { formatCalendarDate } from "@/lib/calendar-date";
import { resolveGuidanceText, currentLoadDecision, prefillLoadKg, useDeclaredLoadContextGuard, type LoadProjectionGeneration } from "@/lib/today-guidance";
import { kgToLbs, lbsToKg, snapToHalfLb } from "@/lib/weight";

import { exerciseKey, workoutReference, occurrenceStorageKey, pendingCommandKey, getLogCommand, acknowledgeLogCommand, retainLogPayload } from "@/lib/workout-identity";

type SwapState = Record<string, number>;
type NotesState = Record<string, boolean>;
const WEAK_POINT_PLACEHOLDER_RE = /^weak point exercise/i;
const MUSCLE_GROUPS = [
  "chest",
  "back",
  "quads",
  "hamstrings",
  "glutes",
  "shoulders",
  "biceps",
  "triceps",
  "calves",
] as const;

const WEAK_POINT_FALLBACK_BY_AREA: Record<string, string[]> = {
  chest: ["Machine Chest Press", "Cable Fly"],
  back: ["Chest-Supported Row", "Lat Pulldown"],
  lats: ["Lat Pulldown", "Single-Arm Cable Pulldown"],
  quads: ["Hack Squat", "Leg Extension"],
  hamstrings: ["Seated Leg Curl", "Romanian Deadlift"],
  glutes: ["Hip Thrust", "Bulgarian Split Squat"],
  shoulders: ["Cable Lateral Raise", "Machine Shoulder Press"],
  side_delts: ["Cable Lateral Raise", "Machine Lateral Raise"],
  rear_delts: ["Reverse Pec Deck", "Cable Rear Delt Fly"],
  front_delts: ["Machine Shoulder Press", "Dumbbell Overhead Press"],
  biceps: ["Incline Dumbbell Curl", "Cable Curl"],
  triceps: ["Cable Pressdown", "Overhead Cable Extension"],
  calves: ["Standing Calf Raise", "Seated Calf Raise"],
  core: ["Cable Crunch", "Hanging Knee Raise"],
  abs: ["Cable Crunch", "Decline Sit-Up"],
};

function formatRoleLabel(value: string | null | undefined): string | null {
  const normalized = value?.trim();
  if (!normalized) {
    return null;
  }
  if (normalized === "weak_point_arms") {
    return "Arms & Weak Points";
  }
  return normalized
    .replaceAll("_", " ")
    .trim()
    .split(/\s+/)
    .map((part) => (part.length ? part[0].toUpperCase() + part.slice(1) : part))
    .join(" ");
}

function buildTodayContextNote(workout: WorkoutSession | null): string | null {
  if (!workout) {
    return null;
  }
  const dayRole = formatRoleLabel(workout.day_role);
  const authoredWeekIndex =
    typeof workout.mesocycle?.authored_week_index === "number" ? workout.mesocycle.authored_week_index : null;
  const authoredWeekRole = formatRoleLabel(workout.mesocycle?.authored_week_role)?.toLowerCase() ?? null;
  if (dayRole && authoredWeekIndex !== null && authoredWeekRole) {
    return `Today follows ${dayRole} in week ${authoredWeekIndex} of the ${authoredWeekRole} block.`;
  }
  if (dayRole) {
    return `Today follows ${dayRole}.`;
  }
  return null;
}

function createInitialSorenessState(): Record<string, SorenessSeverity> {
  return Object.fromEntries(MUSCLE_GROUPS.map((muscle) => [muscle, "none"])) as Record<string, SorenessSeverity>;
}

function extractProgramId(sessionId: string): string | null {
  const match = /^(.*)-day\d+$/.exec(sessionId);
  return match ? match[1] : null;
}

function ExerciseTitleLink({
  selectedName,
  guideHref,
}: Readonly<{ selectedName: string; guideHref: string | null }>) {
  if (!guideHref) {
    return <>{selectedName}</>;
  }
  return (
    <Link href={guideHref} className="underline decoration-zinc-600 underline-offset-2">
      {selectedName}
    </Link>
  );
}

function resolveExerciseStatus(completed: number, totalSets: number, resumed: boolean): "green" | "yellow" | "red" {
  if (completed >= totalSets) {
    return "green";
  }
  if (resumed && completed === 0) {
    return "red";
  }
  return "yellow";
}

function resolveExerciseName(exercise: WorkoutExercise, swapIndexByExercise: SwapState): string {
  if (exercise.authored_prescription || exercise.authored_constraint) return exercise.performed_variant?.name ?? exercise.name;
  const substitutions = exercise.substitution_candidates ?? [];
  const selectedIndex = swapIndexByExercise[exerciseKey(exercise)] ?? 0;
  if (selectedIndex === 0) {
    return exercise.name;
  }
  return substitutions[selectedIndex - 1] ?? exercise.name;
}

function humanizeToken(value: string): string {
  return value
    .split(/[_-]/)
    .filter(Boolean)
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join(" ");
}

function isWeakPointExercise(exercise: WorkoutExercise): boolean {
  const slotRole = String(exercise.slot_role ?? "").trim().toLowerCase();
  const exerciseId = String(exercise.primary_exercise_id ?? exercise.id).trim().toLowerCase();
  return slotRole === "weak_point" || exerciseId.startsWith("weak_point_");
}

function resolveWeakPointTargetsLabel(weakAreas: string[]): string {
  const normalized = weakAreas
    .map((value) => value.trim().toLowerCase())
    .filter((value) => value.length > 0);
  if (normalized.length === 0) {
    return "your selected weak area";
  }
  return normalized.map(humanizeToken).slice(0, 2).join(" + ");
}

function resolveWeakPointFallbackCandidates(exercise: WorkoutExercise, weakAreas: string[]): string[] {
  if (!isWeakPointExercise(exercise)) {
    return [];
  }
  const options: string[] = [];
  for (const areaRaw of weakAreas) {
    const area = areaRaw.trim().toLowerCase();
    const areaOptions = WEAK_POINT_FALLBACK_BY_AREA[area] ?? [];
    for (const option of areaOptions) {
      if (!options.includes(option)) {
        options.push(option);
      }
    }
  }
  if (options.length > 0) {
    return options;
  }
  return ["Machine Chest Press", "Cable Row", "Leg Press", "Cable Lateral Raise", "Cable Curl"];
}

function resolveSubstitutionCandidates(exercise: WorkoutExercise, weakAreas: string[]): string[] {
  if (exercise.authored_prescription || exercise.authored_constraint) return [];
  const explicit = (exercise.substitution_candidates ?? []).filter((item) => item.trim().length > 0);
  if (explicit.length > 0) {
    return explicit;
  }
  return resolveWeakPointFallbackCandidates(exercise, weakAreas);
}

function resolveDisplayExerciseName(exercise: WorkoutExercise, selectedName: string, weakAreas: string[]): string {
  if (!isWeakPointExercise(exercise)) {
    return selectedName;
  }
  if (!WEAK_POINT_PLACEHOLDER_RE.test(selectedName.trim())) {
    return selectedName;
  }
  const isOptional = exercise.id.toLowerCase().includes("_2");
  const slotLabel = isOptional ? "Weak Point Slot 2 (optional)" : "Weak Point Slot 1";
  return `${slotLabel} · ${resolveWeakPointTargetsLabel(weakAreas)}`;
}

function resolveWeakPointInstruction(exercise: WorkoutExercise, weakAreas: string[]): string | null {
  if (!isWeakPointExercise(exercise)) {
    return null;
  }
  const targetLabel = resolveWeakPointTargetsLabel(weakAreas);
  if (exercise.id.toLowerCase().includes("_2")) {
    return `Optional slot: add a second ${targetLabel} movement only if recovery feels good today.`;
  }
  return `Primary weak-point slot: choose one ${targetLabel} movement and keep it consistent week to week for cleaner progression data.`;
}

function resolveExerciseMediaUrl(exercise: WorkoutExercise): string | null {
  const preferred = exercise.performed_variant
    ? exercise.performed_variant.video_url
    : exercise.video?.youtube_url ?? exercise.video_url ?? exercise.demo_url;
  return typeof preferred === "string" && preferred.trim().length > 0 ? preferred : null;
}

function resolveAuthoredSubstitutions(exercise: WorkoutExercise): string[] {
  return [exercise.substitution_option_1, exercise.substitution_option_2].filter(
    (value, index, source): value is string =>
      typeof value === "string" && value.trim().length > 0 && source.indexOf(value) === index,
  );
}

function resolveTrackingLoads(exercise: WorkoutExercise): string[] {
  return [exercise.tracking_set_1, exercise.tracking_set_2, exercise.tracking_set_3, exercise.tracking_set_4].filter(
    (value): value is string => typeof value === "string" && value.trim().length > 0,
  );
}

type TechniqueModalState =
  | {
      exerciseId: string;
      exerciseName: string;
      workoutId: string;
      parentSetIndex: number;
      kind: "dropset" | "mechanical_drop" | "rest_pause_cluster";
      baseWeightLb: number;
      baseReps: number;
      authored?: boolean;
      bodyweight?: boolean;
      instruction?: string | null;
    }
  | null;

type TechniqueKind = NonNullable<TechniqueModalState>["kind"];

function resolveTechniqueKind(exercise: WorkoutExercise): TechniqueKind | null {
  const technique = String(exercise.last_set_intensity_technique ?? "").toLowerCase();
  const notes = String(exercise.notes ?? "").toLowerCase();
  if (technique.includes("mechanical")) return "mechanical_drop";
  if (technique.includes("dropset") || technique.includes("drop set")) return "dropset";
  if (technique.includes("rest-pause") || technique.includes("rest pause") || technique.includes("myo")) return "rest_pause_cluster";
  if (notes.includes("myo") || notes.includes("rest-pause") || notes.includes("rest pause")) return "rest_pause_cluster";
  return null;
}

function requiresLastSetChecklist(exercise: WorkoutExercise): string[] {
  const notes = String(exercise.notes ?? "").toLowerCase();
  const technique = String(exercise.last_set_intensity_technique ?? "").toLowerCase();
  const text = `${technique}\n${notes}`;
  const items: string[] = [];

  // Long-length / stretch partials (common authored variants).
  const hasPartials = text.includes("partial");
  const hasLengthenedCue =
    text.includes("long-length")
    || text.includes("long length")
    || text.includes("lengthened")
    || text.includes("stretch")
    || text.includes("stretched")
    || text.includes("bottom");
  if (
    text.includes("long-length partial")
    || text.includes("long length partial")
    || text.includes("long-length partials")
    || (hasPartials && hasLengthenedCue)
  ) {
    items.push("Long-length partials (lengthened range) on the last set");
  }

  // Pauses.
  if (text.includes("pause") || text.includes("paused")) {
    items.push("Pause prescription (per coaching notes)");
  }

  // Tempo / eccentrics.
  if (text.includes("tempo") || text.includes("eccentric") || text.includes("negative") || text.includes("controlled")) {
    items.push("Tempo / controlled eccentric (per coaching notes)");
  }

  return items;
}

function InlineTechniquePanel({
  state,
  onClose,
  onLog,
}: Readonly<{
  state: NonNullable<TechniqueModalState>;
  onClose: () => void;
  onLog: (performed: { reps: number; weight: number }, ordinal: number) => Promise<void>;
}>) {
  const [ordinal, setOrdinal] = useState(1);
  const [reps, setReps] = useState(state.authored ? "" : String(Math.max(1, Math.round(state.baseReps / 2))));
  const [weight, setWeight] = useState(
    state.authored ? (state.bodyweight ? "0" : "") : String(state.kind === "dropset" ? Math.max(2.5, Math.round(state.baseWeightLb * 0.85 * 10) / 10) : state.baseWeightLb),
  );
  const [status, setStatus] = useState<string | null>(null);

  const title =
    state.kind === "rest_pause_cluster"
      ? "Rest-pause / myo-reps"
      : state.kind === "mechanical_drop"
        ? "Mechanical drop set"
        : "Drop set";

  async function handleLog() {
    setStatus("Logging technique set...");
    try {
      const actualReps = Number(reps);
      const actualWeight = Number(weight);
      if (state.authored && (!Number.isInteger(actualReps) || actualReps < 1 || !Number.isFinite(actualWeight) || (state.bodyweight ? actualWeight < 0 : actualWeight <= 0))) {
        setStatus("Enter actual reps and external load for this technique set.");
        return;
      }
      await onLog({ reps: state.authored ? actualReps : actualReps || 1, weight: state.authored ? actualWeight : actualWeight || state.baseWeightLb }, ordinal);
      setOrdinal((prev) => prev + 1);
      setStatus("Logged. Add another or close.");
    } catch {
      setStatus("Failed to log. Try again.");
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
        <Button type="button" variant="ghost" className="min-h-[32px] px-2 text-xs" onClick={onClose}>
          Close
        </Button>
      </div>

      <div className="rounded-md border border-zinc-800 bg-zinc-900/40 p-3 text-xs text-zinc-300 space-y-1">
        {state.authored ? (
          <p>{state.instruction}</p>
        ) : state.kind === "mechanical_drop" ? (
          <p>Keep the same load, change the leverage/position to make it easier, then continue.</p>
        ) : state.kind === "dropset" ? (
          <p>Reduce load and continue with strict form (this logs as a technique sub-set).</p>
        ) : (
          <p>Take a short rest (10–20s), then continue with the same load (technique sub-set).</p>
        )}
        <p className="text-zinc-400">These technique sub-sets do not count as extra working sets.</p>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <label className="flex flex-col gap-1.5">
          <span className="text-[11px] uppercase tracking-wide text-zinc-500">Reps</span>
          <input
            className="ui-input h-12 w-full rounded-lg px-3 text-center text-lg font-semibold tabular-nums"
            type="number"
            min={1}
            value={reps}
            onChange={(e) => setReps(e.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1.5">
          <span className="text-[11px] uppercase tracking-wide text-zinc-500">{state.bodyweight ? "Added load (lb), optional" : "Weight (lb)"}</span>
          <input
            className="ui-input h-12 w-full rounded-lg px-3 text-center text-lg font-semibold tabular-nums"
            type="number"
            min={0}
            step={0.5}
            value={weight}
            onChange={(e) => setWeight(e.target.value)}
          />
        </label>
      </div>

      {status ? <p className="text-xs text-zinc-400">{status}</p> : null}

      <Button type="button" variant="secondary" className="min-h-[44px] w-full" onClick={handleLog}>
        Log technique set #{ordinal}
      </Button>
    </div>
  );
}

function resolveHealthStatus(health: string): "green" | "yellow" | "red" {
  if (health === "ok") {
    return "green";
  }
  if (health === "loading") {
    return "yellow";
  }
  return "red";
}

function WorkoutSummaryCard({ summary }: Readonly<{ summary: WorkoutSummary | null }>) {
  if (!summary) {
    return null;
  }
  const exercises = Array.isArray(summary.exercises) ? summary.exercises : [];
  if (exercises.length === 0) {
    return null;
  }

  return (
    <div className="main-card main-card--module spacing-grid">
      <div className="telemetry-header">
        <p className="telemetry-kicker">Day Summary</p>
        <p className="telemetry-status">
          <span className="status-dot status-dot--green" /> {summary.percent_complete}% complete
        </p>
      </div>
      <p className="telemetry-meta">Overall guidance: {resolveGuidanceText(summary.overall_rationale, summary.overall_guidance)}</p>
      <div className="space-y-2">
        {exercises.map((item) => (
          <div key={item.exercise_occurrence_id ?? item.exercise_id} className="rounded-md border border-zinc-800 bg-zinc-900/40 p-2 text-xs text-zinc-300">
            <p className="font-semibold text-zinc-100">{item.performed_variant?.name ?? item.name}</p>
            {item.performed_variant ? <p>Original authored exercise: {item.name} · confirmed source-approved variant</p> : null}
            <p>
              Planned: {item.planned_sets} sets · {item.planned_reps_min != null ? `${item.planned_reps_min}-${item.planned_reps_max}` : "authored target"} reps · {item.load_semantics === "bodyweight" ? "Bodyweight" : item.load_recommendation_available === false ? "Record actual variant load" : `${kgToLbs(item.planned_weight)} lbs`}
            </p>
            <p>
              Performed: {item.performed_sets} sets · avg {item.average_performed_reps} reps · {item.load_semantics === "bodyweight" ? (item.average_performed_weight > 0 ? `Bodyweight + ${kgToLbs(item.average_performed_weight)} lb added` : "Bodyweight (no added load)") : `${kgToLbs(item.average_performed_weight)} lbs`}
            </p>
            {item.load_intelligence ? <>
              <p>Next exposure: {item.load_intelligence.next_exposure.action}{item.load_intelligence.next_exposure.recommended_weight != null ? ` · ${kgToLbs(item.load_intelligence.next_exposure.recommended_weight)} lb` : " · no new load inferred"}</p>
              <p>{item.load_intelligence.next_exposure.explanation}</p>
              {item.load_intelligence.next_exposure.known_baseline_weight != null ? <p>Known baseline: {kgToLbs(item.load_intelligence.next_exposure.known_baseline_weight)} lb</p> : null}
            </> : <>
              <p>Next: {item.load_semantics === "bodyweight" ? "Bodyweight" : item.load_recommendation_available === false || item.next_working_weight == null ? "Load advice pending comparable evidence" : `${kgToLbs(item.next_working_weight)} lbs`}</p>
              <p>{resolveGuidanceText(item.guidance_rationale, item.guidance)}</p>
            </>}
          </div>
        ))}
      </div>
    </div>
  );
}

function BaselineBlock({
  exerciseId,
  repRange,
  currentBaseline,
  onCalculate,
}: Readonly<{
  exerciseId: string;
  repRange: [number, number] | null;
  currentBaseline: { weightLb: number; reps: number; estimated1RM: number; workingWeightLb: number; warmupLbs: number[] } | undefined;
  onCalculate: (weightLb: number, reps: number) => void;
}>) {
  const [weightLb, setWeightLb] = useState<string>(() => (currentBaseline ? String(currentBaseline.weightLb) : ""));
  const [reps, setReps] = useState<string>(() => (currentBaseline ? String(currentBaseline.reps) : String(repRange?.[0] ?? "")));
  useEffect(() => {
    if (currentBaseline) {
      setWeightLb(String(currentBaseline.weightLb));
      setReps(String(currentBaseline.reps));
    }
  }, [currentBaseline]);

  function handleCalculate() {
    const w = Number(weightLb);
    const r = Number(reps);
    if (Number.isFinite(w) && w > 0 && Number.isFinite(r) && r >= 1) {
      onCalculate(w, Math.round(r));
    }
  }

  return (
    <div className="rounded-lg border border-zinc-700 bg-zinc-900/60 p-3 space-y-3">
      <p className="text-sm font-medium text-zinc-200">Your baseline</p>
      <p className="text-xs text-zinc-400">
        Enter a recent set (e.g. &quot;I did 100 lb × 3 reps&quot;). We&apos;ll estimate your 1RM and suggest warm-up and working weights.
      </p>
      <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1">
          <span className="text-xs uppercase tracking-wide text-zinc-500">Weight (lb)</span>
          <input
            className="ui-input h-9 w-20 px-2 text-base"
            type="number"
            min={1}
            step={2.5}
            value={weightLb}
            onChange={(e) => setWeightLb(e.target.value)}
            aria-label="Baseline weight in pounds"
            style={{ fontSize: "16px" }}
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs uppercase tracking-wide text-zinc-500">Reps</span>
          <input
            className="ui-input h-9 w-16 px-2 text-base"
            type="number"
            min={1}
            value={reps}
            onChange={(e) => setReps(e.target.value)}
            aria-label="Baseline reps"
            style={{ fontSize: "16px" }}
          />
        </label>
        <Button type="button" className="h-9" onClick={handleCalculate}>
          Calculate
        </Button>
      </div>
      {currentBaseline ? (
        <div className="rounded border border-zinc-600 bg-zinc-800/40 px-3 py-2 text-xs text-zinc-200 space-y-1">
          <p className="font-medium">Estimated 1RM: {Math.round(currentBaseline.estimated1RM)} lb</p>
          <p>Suggested working weight: {currentBaseline.workingWeightLb} lb (for {repRange ? `${repRange[0]}-${repRange[1]}` : "authored target"} reps)</p>
        </div>
      ) : null}
    </div>
  );
}

function ExerciseDetailOverlay({
  exercise,
  selectedName,
  guideHref,
  completed,
  doThisSetLine,
  derivedWorkingLb,
  warmUpCount,
  baseline,
  warmupLbs,
  hasWarmup,
  hasCoachingDetails,
  techniquePanelState,
  onCloseTechniquePanel,
  onLogTechniquePanel,
  currentSwapIndex,
  altCandidates,
  lastSet,
  mediaUrl,
  substitutions,
  weakPointInstruction,
  notesOpen,
  isDeloadWeek,
  onUndoLastSet,
  onClose,
  onSwap,
  onToggleNotes,
  onSwapTarget,
  onSetComplete,
  onAuthoredDecision,
  onCalculateBaseline,
  globalRestTimer,
  onClearGlobalRestTimer,
  loadIntelligence,
  loadContext,
  onLoadContextChange,
  onPreviewLoad,
  overrideReason,
  onOverrideReason,
  onCorrectSet,
}: Readonly<{
  exercise: WorkoutExercise;
  selectedName: string;
  guideHref: string | null;
  completed: number;
  doThisSetLine: string;
  derivedWorkingLb: number;
  warmUpCount: number;
  baseline: { weightLb: number; reps: number; estimated1RM: number; workingWeightLb: number; warmupLbs: number[] } | undefined;
  warmupLbs: number[];
  hasWarmup: boolean;
  hasCoachingDetails: boolean;
  techniquePanelState: NonNullable<TechniqueModalState> | null;
  onCloseTechniquePanel: () => void;
  onLogTechniquePanel: (performed: { reps: number; weight: number }, ordinal: number) => Promise<void>;
  currentSwapIndex: number;
  altCandidates: string[];
  lastSet: { reps: number; weight: number } | null;
  mediaUrl: string | null;
  substitutions: string[];
  weakPointInstruction: string | null;
  notesOpen: boolean;
  onUndoLastSet?: () => Promise<number | false> | void;
  onClose: () => void;
  onSwap: (exerciseId: string, index: number) => void;
  onToggleNotes: () => void;
  onSwapTarget: () => void;
  isDeloadWeek: boolean;
  onSetComplete: (exerciseId: string, count: number, performed: PerformedSet) => Promise<void> | void;
  onAuthoredDecision: (decision: AuthoredDecision) => Promise<void>;
  onCalculateBaseline: (weightLb: number, reps: number) => void;
  globalRestTimer: { exerciseId: string; exerciseName: string; secondsLeft: number; restCycle: number } | null;
  onClearGlobalRestTimer: () => void;
  loadIntelligence: LoadIntelligence | null | undefined;
  loadContext: LoadContext;
  onLoadContextChange: (context: LoadContext) => void;
  onPreviewLoad: (context: LoadContext) => Promise<void>;
  overrideReason: string;
  onOverrideReason: (reason: string) => void;
  onCorrectSet: (receipt: EffectiveLoadSet, values: { reps: number; weight: number; rpe?: number | null; reason: string }) => Promise<void>;
}>) {
  const defaultRestSeconds = parseRestToSeconds(exercise.rest) ?? 90;
  const bodyweight = isBodyweightAuthored(exercise);
  const sourceWarmups = authoredWarmupLabel(exercise);
  const currentRepRange = useMemo(() => authoredSetRepRange(exercise, Math.min(completed + 1, exercise.sets)), [exercise, completed]);
  const intelligenceActive = loadIntelligence !== undefined;
  const currentDecision = currentLoadDecision(loadIntelligence, completed, exercise.sets);
  const canonicalLoad = prefillLoadKg(currentDecision);
  const invalidKnownIncrement = intelligenceActive && loadContext.increment != null &&
    (!Number.isFinite(loadContext.increment) || loadContext.increment <= 0);
  const ctrl = useExerciseControl({
    exerciseId: exerciseKey(exercise),
    totalSets: exercise.sets,
    defaultRestSeconds,
    recommendedWorkingWeight: intelligenceActive ? (canonicalLoad === undefined ? undefined : kgToLbs(canonicalLoad))
      : bodyweight ? 0 : exercise.performed_variant ? undefined : snapToHalfLb(derivedWorkingLb),
    recommendedWeightCanonicalKg: canonicalLoad,
    requireWeight: intelligenceActive && !bodyweight,
    repRange: currentRepRange,
    initialCompletedSets: completed,
    skipTimerOnComplete: true,
    onSetComplete: onSetComplete,
  });
  const externalRest =
    globalRestTimer?.exerciseId === exerciseKey(exercise)
      ? {
          secondsLeft: globalRestTimer.secondsLeft,
          restCycle: globalRestTimer.restCycle,
          onStop: onClearGlobalRestTimer,
        }
      : undefined;

  const isAssistance = String(exercise.load_semantics ?? "").toLowerCase() === "assistance";
  const currentTechnique = authoredSetTechnique(exercise, ctrl.completedSets + 1);
  const techniqueExercise = exercise.authored_prescription ? { ...exercise, last_set_intensity_technique: currentTechnique } : exercise;
  const checklistItems = exercise.authored_prescription ? (currentTechnique ? [currentTechnique] : []) : requiresLastSetChecklist(exercise);
  const techniqueKind = resolveTechniqueKind(techniqueExercise);
  const [checklistAccepted, setChecklistAccepted] = useState(false);
  useEffect(() => {
    // Reset checklist gate when changing exercise or moving off last set.
    setChecklistAccepted(false);
  }, [exerciseKey(exercise), ctrl.completedSets]);

  const isLastSetNext = ctrl.completedSets === ctrl.totalSets - 1;
  const techniqueApplies = exercise.authored_prescription ? Boolean(currentTechnique) : isLastSetNext;
  const gateLastSet = checklistItems.length > 0 && techniqueApplies && !checklistAccepted;
  const hasTechnique = checklistItems.length > 0 || techniqueKind != null || techniquePanelState != null;

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-zinc-950 min-h-[100dvh] max-h-[100dvh]" aria-modal="true" role="dialog">
      {/* ---- Header: name + set counter ---- */}
      <div className="sticky top-0 z-10 flex min-h-[48px] shrink-0 items-center gap-3 border-b border-zinc-800 bg-zinc-950/95 px-4 py-2 backdrop-blur">
        <Button
          type="button"
          variant="ghost"
          className="min-h-[44px] min-w-[44px]"
          onClick={onClose}
          aria-label="Back to list"
        >
          <UiIcon name="close" className="ui-icon--action" />
        </Button>
        <span className="flex-1 truncate text-sm font-semibold text-zinc-100">
          {guideHref ? (
            <Link href={guideHref} className="underline decoration-zinc-600 underline-offset-2">
              {selectedName}
            </Link>
          ) : (
            selectedName
          )}
        </span>
        {isDeloadWeek ? (
          <span className="rounded-full bg-yellow-500/15 px-2 py-0.5 text-[10px] font-medium text-yellow-300">Deload</span>
        ) : null}
        <span className="text-xs tabular-nums text-zinc-400">
          Set {Math.min(ctrl.completedSets + 1, exercise.sets)}/{exercise.sets}
        </span>
      </div>

      {/* ---- Scrollable body ---- */}
      <div className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden p-4 pb-[max(7rem,env(safe-area-inset-bottom))] space-y-4 overscroll-contain">

        {/* == ZONE 1: Baseline calculator (expanded when no baseline) == */}
        {exercise.rep_range && !bodyweight && !exercise.performed_variant ? <Disclosure title="Baseline Calculator" badge={baseline ? `1RM: ${Math.round(baseline.estimated1RM)} lb` : null} defaultOpen={!baseline}>
          <BaselineBlock
            exerciseId={exerciseKey(exercise)}
            repRange={exercise.rep_range}
            currentBaseline={baseline}
            onCalculate={onCalculateBaseline}
          />
        </Disclosure> : null}

        {/* == ZONE 2: Warm-up sets (expanded when warm-ups exist) == */}
        {exercise.authored_prescription ? (
          <Disclosure title="Warm-up Sets" badge={sourceWarmups ? `${sourceWarmups} sets` : null} defaultOpen>
            <p className="text-sm text-zinc-200">{sourceWarmups != null ? `${sourceWarmups} warm-up sets` : "Warm-up prescription unspecified"}</p>
          </Disclosure>
        ) : hasWarmup && (
          <Disclosure title="Warm-up Sets" badge={`${warmupLbs.length} sets`} defaultOpen>
            <div className="space-y-2">
              <p className="text-xs text-zinc-400">
                {baseline != null
                  ? "From your baseline. Do these before working sets."
                  : "Based on your working weight. Do these before working sets."}
              </p>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                {warmupLbs.map((lb, i) => (
                  <div key={i} className="flex items-center justify-between rounded-md border border-zinc-700 bg-zinc-800/40 px-3 py-2">
                    <span className="text-xs text-zinc-400">Set {i + 1}</span>
                    <span className="text-sm font-medium tabular-nums text-zinc-200">{lb} lb</span>
                  </div>
                ))}
              </div>
            </div>
          </Disclosure>
        )}

        {/* == ZONE 3: Coaching details (collapsible) == */}
        {hasCoachingDetails && (
          <Disclosure title="Coaching" defaultOpen={hasTechnique}>
            <div className="space-y-3">
              {techniquePanelState ? (
                <InlineTechniquePanel
                  state={techniquePanelState}
                  onClose={onCloseTechniquePanel}
                  onLog={onLogTechniquePanel}
                />
              ) : null}

              <div className="flex flex-wrap gap-2">
                {exercise.last_set_intensity_technique ? (
                  <span className="rounded-full border border-zinc-700 bg-zinc-800/60 px-2.5 py-1 text-[11px] text-zinc-300">
                    Technique: {exercise.last_set_intensity_technique}
                  </span>
                ) : null}
                {exercise.rest ? (
                  <span className="rounded-full border border-zinc-700 bg-zinc-800/60 px-2.5 py-1 text-[11px] text-zinc-300">
                    Rest: {exercise.rest}
                  </span>
                ) : null}
                {exercise.early_set_rpe ? (
                  <span className="rounded-full border border-zinc-700 bg-zinc-800/60 px-2.5 py-1 text-[11px] text-zinc-300">
                    Early RPE: {exercise.early_set_rpe}
                  </span>
                ) : null}
                {exercise.last_set_rpe ? (
                  <span className="rounded-full border border-zinc-700 bg-zinc-800/60 px-2.5 py-1 text-[11px] text-zinc-300">
                    Last RPE: {exercise.last_set_rpe}
                  </span>
                ) : null}
              </div>
              {lastSet != null ? (
                <p className="text-xs text-zinc-400">
                  Suggestion updated from your last set ({lastSet.weight} lb x {lastSet.reps} reps).
                </p>
              ) : null}
              {/* Substitution buttons */}
              {(currentSwapIndex > 0 || altCandidates.length > 0) && (
                <div className="flex flex-wrap gap-2 pt-1">
                  {currentSwapIndex > 0 ? (
                    <Button type="button" variant="secondary" className="min-h-[32px] px-2 text-xs" onClick={() => onSwap(exerciseKey(exercise), 0)}>
                      Use original exercise
                    </Button>
                  ) : null}
                  {altCandidates.map((name, index) => (
                    <Button
                      key={`${exercise.id}-alt-${index}`}
                      type="button"
                      variant="secondary"
                      className="min-h-[32px] px-2 text-xs"
                      onClick={() => onSwap(exerciseKey(exercise), index + 1)}
                    >
                      Use {name}
                    </Button>
                  ))}
                </div>
              )}

              {/* Technique (last set) checklist at bottom so user can confirm before Complete Set */}
              {checklistItems.length > 0 && techniqueApplies ? (
                <div className="rounded-xl border border-amber-500/50 bg-amber-950/30 p-3 space-y-2">
                  <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">{exercise.authored_prescription ? "Technique (this set)" : "Technique (last set)"}</p>
                  <ul className="list-disc pl-5 text-xs text-zinc-200 space-y-1">
                    {checklistItems.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                  <label className="flex items-center gap-2 text-xs text-zinc-200">
                    <input
                      type="checkbox"
                      checked={checklistAccepted}
                      onChange={(e) => setChecklistAccepted(e.target.checked)}
                    />
                    I will execute these technique cues on this set.
                  </label>
                </div>
              ) : null}
            </div>
          </Disclosure>
        )}

        {exercise.authored_prescription || exercise.authored_constraint ? <AuthoredConstraintCard exercise={exercise} onDecision={onAuthoredDecision} /> : null}
        {/* == ZONE 4: Primary action (log set) == */}
        {intelligenceActive ? <LoadIntelligencePanel guidance={loadIntelligence ?? null} completed={completed} total={exercise.sets}
          loadContext={loadContext} onContextChange={onLoadContextChange} onPreview={onPreviewLoad}
          overrideReason={overrideReason} onOverrideReason={onOverrideReason} onCorrect={onCorrectSet} requireExternalWeight={!bodyweight} /> : null}
        <SetInputCard
          exerciseId={exerciseKey(exercise)}
          guidanceLine={doThisSetLine}
          ctrl={ctrl}
          weightLabel={bodyweight ? "Added load (lb), optional" : isAssistance ? "Assistance (lb) — lower is harder" : "Weight (lb)"}
          disabledReason={["unresolved", "infeasible", "declined"].includes(exercise.authored_constraint?.execution_status ?? exercise.authored_constraint?.status ?? "") ? "Resolve authored slot first" : invalidKnownIncrement ? "Enter a positive increment or leave it blank" : undefined}
          disableComplete={invalidKnownIncrement || gateLastSet || ["unresolved", "infeasible", "declined"].includes(exercise.authored_constraint?.execution_status ?? exercise.authored_constraint?.status ?? "")}
        />

        {/* == ZONE 5: Set log (per-set logged values) == */}
        <SetLogDisplay ctrl={ctrl} onUndoLastSet={onUndoLastSet} hideLocalReceipts={intelligenceActive} />

        {/* == ZONE 6: Set progress == */}
        <SetProgressTimeline exerciseId={exerciseKey(exercise)} ctrl={ctrl} />

        {/* == ZONE 7: Rest timer == */}
        <RestTimerCard ctrl={ctrl} externalRest={externalRest} />

        {/* == ZONE 8: Quick actions toolbar == */}
        <div className="grid grid-cols-4 gap-2">
          <Button
            type="button"
            variant="secondary"
            className="min-h-[44px] flex-col gap-1 px-2 py-2 text-center"
            disabled={!mediaUrl}
            onClick={() => mediaUrl && window.open(mediaUrl, "_blank", "noopener,noreferrer")}
          >
            <UiIcon name="video" className="ui-icon--action" />
            <span className="text-[10px]">Video</span>
          </Button>
          <Button
            type="button"
            variant="secondary"
            className="min-h-[44px] flex-col gap-1 px-2 py-2 text-center"
            disabled={substitutions.length === 0}
            onClick={onSwapTarget}
          >
            <UiIcon name="swap" className="ui-icon--action" />
            <span className="text-[10px]">Swap</span>
          </Button>
          <Button
            type="button"
            variant="secondary"
            className="min-h-[44px] flex-col gap-1 px-2 py-2 text-center"
            onClick={onToggleNotes}
          >
            <UiIcon name="notes" className="ui-icon--action" />
            <span className="text-[10px]">Notes</span>
          </Button>
          <Link
            href="/checkin"
            className="inline-flex min-h-[44px] flex-col items-center justify-center gap-1 rounded-md border border-[var(--ui-edge-idle)] bg-[var(--ui-surface-1)] px-2 py-2 text-center text-[10px] text-zinc-100 hover:border-[var(--ui-edge-active)]"
          >
            <UiIcon name="body" className="ui-icon--action" />
            <span>Check-In</span>
          </Link>
        </div>

        {notesOpen && (
          <div className="rounded-md border border-zinc-800 bg-zinc-900/40 p-3 text-xs text-zinc-300">
            {weakPointInstruction ? <p className="mb-2 text-zinc-200">{weakPointInstruction}</p> : null}
            {exercise.notes ?? "No notes for this slot."}
          </div>
        )}
      </div>
    </div>
  );
}

function WorkoutHeaderCard({
  workout,
  workoutProgress,
}: Readonly<{
  workout: WorkoutSession;
  workoutProgress: { completed: number; planned: number; percent: number } | null;
}>) {
  return (
    <div className="main-card main-card--shell spacing-grid spacing-grid--tight">
      <div className="telemetry-header">
        <p className="telemetry-value">{workout.title}</p>
        <p className="telemetry-meta">{workout.date}</p>
      </div>
      {workout.daily_quote ? (
        <div className="rounded-md border border-white/10 bg-black/25 p-2">
          <p className="text-xs text-zinc-200">&quot;{workout.daily_quote.text}&quot;</p>
          <p className="mt-1 text-[11px] uppercase tracking-wide text-zinc-400">
            {workout.daily_quote.author} · {workout.daily_quote.source}
          </p>
        </div>
      ) : null}
      {workout.mesocycle ? (
        <p className="telemetry-meta text-zinc-300">
          Mesocycle Week {workout.mesocycle.week_index}/{workout.mesocycle.trigger_weeks_effective}
        </p>
      ) : null}
      {workout.deload?.active ? (
        <p className="telemetry-status text-amber-300">
          <span className="status-dot status-dot--yellow" /> Deload Week Active ({workout.deload.reason})
        </p>
      ) : null}
      {workout.resume ? <p className="telemetry-meta text-accent">Resumed unfinished workout</p> : null}
      {workoutProgress ? (
        <p className="telemetry-meta text-zinc-300">
          Progress: {workoutProgress.completed}/{workoutProgress.planned} sets ({workoutProgress.percent}%)
        </p>
      ) : null}
    </div>
  );
}

export default function TodayPage() {
  const [health, setHealth] = useState("loading");
  const [workout, setWorkout] = useState<WorkoutSession | null>(null);
  const [message, setMessage] = useState("No workout loaded");
  const [swapIndexByExercise, setSwapIndexByExercise] = useState<SwapState>({});
  const [notesOpenByExercise, setNotesOpenByExercise] = useState<NotesState>({});
  const [swapTargetExerciseId, setSwapTargetExerciseId] = useState<string | null>(null);
  const [showSorenessModal, setShowSorenessModal] = useState(false);
  const [sorenessStatus, setSorenessStatus] = useState("Idle");
  const [sorenessNotes, setSorenessNotes] = useState("");
  const [weakAreas, setWeakAreas] = useState<string[]>([]);
  const [sorenessByMuscle, setSorenessByMuscle] = useState<Record<string, SorenessSeverity>>(createInitialSorenessState());
  const [completedSetsByExercise, setCompletedSetsByExercise] = useState<Record<string, number>>({});
  const [workoutProgress, setWorkoutProgress] = useState<{ completed: number; planned: number; percent: number } | null>(null);
  const [setFeedbackByExercise, setSetFeedbackByExercise] = useState<Record<string, WorkoutSetFeedback>>({});
  const [loadIntelligenceByExercise, setLoadIntelligenceByExercise] = useState<Record<string, LoadIntelligence | null>>({});
  const [loadContextByExercise, setLoadContextByExercise] = useState<Record<string, LoadContext>>({});
  const [loadOverrideByExercise, setLoadOverrideByExercise] = useState<Record<string, string>>({});
  const loadPreviewVersions = useRef<Record<string, number>>({});
  const { reset: resetSelectedLoadContext, select: selectLoadContext, matches: matchesSelectedLoadContext, forget: forgetSelectedLoadContext, capture: captureLoadGeneration, isCurrent: isCurrentLoadGeneration, advance: advanceLoadGeneration } = useDeclaredLoadContextGuard();
  const updateLoadIntelligence = useCallback((key: string, guidance: LoadIntelligence | null) => {
    if (matchesSelectedLoadContext(key, guidance)) setLoadIntelligenceByExercise(previous => ({ ...previous, [key]: guidance }));
  }, [matchesSelectedLoadContext]);

  function intelligenceFor(exercise: WorkoutExercise): LoadIntelligence | null | undefined {
    const key = exerciseKey(exercise);
    return Object.prototype.hasOwnProperty.call(loadIntelligenceByExercise, key) ? loadIntelligenceByExercise[key] : exercise.load_intelligence;
  }
  const applyProgressLoad = useCallback((exercises: Array<{ exercise_occurrence_id?: string; exercise_id: string; load_intelligence?: LoadIntelligence | null }>, generation?: LoadProjectionGeneration) => {
    const accepted = exercises.filter(item => item.load_intelligence !== undefined && isCurrentLoadGeneration(item.exercise_occurrence_id ?? item.exercise_id, generation) && matchesSelectedLoadContext(item.exercise_occurrence_id ?? item.exercise_id, item.load_intelligence));
    setLoadIntelligenceByExercise(previous => {
      const next = { ...previous };
      for (const item of accepted) next[item.exercise_occurrence_id ?? item.exercise_id] = item.load_intelligence ?? null;
      return next;
    });
  }, [matchesSelectedLoadContext, isCurrentLoadGeneration]);
  const getScopedWorkoutProgress = useCallback(async (workoutId: string) => {
    const generation = captureLoadGeneration();
    const progress = await api.getWorkoutProgress(workoutId);
    return { progress, generation };
  }, [captureLoadGeneration]);
  const [liveRecommendationByExercise, setLiveRecommendationByExercise] = useState<Record<string, WorkoutLiveRecommendation>>({});
  const [workoutSummary, setWorkoutSummary] = useState<WorkoutSummary | null>(null);
  const [localToday, setLocalToday] = useState<{ date: string; timezone: string } | null>(null);
  const [selectedExerciseId, setSelectedExerciseId] = useState<string | null>(null);
  /** User-entered baseline: "I did X lb × Y reps" → 1RM, working weight, warmups. Keyed by exercise id. */
  const [baselineByExercise, setBaselineByExercise] = useState<
    Record<string, { weightLb: number; reps: number; estimated1RM: number; workingWeightLb: number; warmupLbs: number[] }>
  >({});
  /** Last logged set per exercise (reps, weight) to suggest next set. Keyed by exercise id. */
  const [lastSetByExercise, setLastSetByExercise] = useState<Record<string, { reps: number; weight: number }>>({});
  const [techniqueModal, setTechniqueModal] = useState<TechniqueModalState>(null);
  /** Persistent rest timer when overlay is closed; single source of truth. */
  const [globalRestTimer, setGlobalRestTimer] = useState<{
    exerciseId: string;
    exerciseName: string;
    secondsLeft: number;
    restCycle: number;
  } | null>(null);
  const currentOccurrence = useRef<string | null>(null);
  const undoInFlight = useRef(false);
  const hasAutoLoadStarted = useRef(false);
  const isBeginWorkoutLoadInProgress = useRef(false);
  const sorenessDismissedDate = useRef<string | null>(null);
  const sorenessPromptDate = useRef<string | null>(null);

  const loadWorkoutSummary = useCallback(async (workoutId: string) => {
    try {
      const summary = await api.getWorkoutSummary(workoutId);
      setWorkoutSummary(summary);
    } catch {
      setWorkoutSummary(null);
    }
  }, []);

  // When an exercise is opened, pin the page to the top and lock background
  // scrolling so the overlay is stable regardless of where the row sits in
  // the list. Restore scroll behavior when the overlay is closed.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const body = window.document.body;
    if (selectedExerciseId) {
      const userAgent = window.navigator?.userAgent ?? "";
      if (!userAgent.toLowerCase().includes("jsdom")) {
        window.scrollTo({ top: 0, behavior: "instant" as ScrollBehavior });
      }
      const previousOverflow = body.style.overflow;
      body.dataset.hypertrophyPrevOverflow = previousOverflow;
      body.style.overflow = "hidden";
      body.dataset.todayOverlayOpen = "true";
      window.dispatchEvent(new Event("hypertrophy:today-overlay-changed"));
      return () => {
        body.style.overflow = body.dataset.hypertrophyPrevOverflow || "";
        delete body.dataset.hypertrophyPrevOverflow;
        delete body.dataset.todayOverlayOpen;
        window.dispatchEvent(new Event("hypertrophy:today-overlay-changed"));
      };
    }
    delete body.dataset.todayOverlayOpen;
    window.dispatchEvent(new Event("hypertrophy:today-overlay-changed"));
    return undefined;
  }, [selectedExerciseId]);

  // Global rest timer countdown
  useEffect(() => {
    if (!globalRestTimer) return;
    const id = setInterval(() => {
      setGlobalRestTimer((prev) => {
        if (!prev || prev.secondsLeft <= 1) return null;
        return { ...prev, secondsLeft: prev.secondsLeft - 1 };
      });
    }, 1000);
    return () => clearInterval(id);
  }, [globalRestTimer]);

  useEffect(() => {
    api.health()
      .then((data) => setHealth(data.status))
      .catch(() => setHealth("offline"));
  }, []);

  const resolveLocalToday = useCallback(async (): Promise<string> => {
    const browserTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
    const context = await api.getSchedulingContext(browserTimezone);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(context.local_today) || !context.timezone) {
      throw new Error("Scheduling date unavailable");
    }
    setLocalToday({ date: context.local_today, timezone: context.timezone });
    return context.local_today;
  }, []);

  const loadToday = useCallback(async (): Promise<WorkoutSession | null> => {
    try {
      const data = await api.getTodayWorkout();
      currentOccurrence.current = workoutReference(data);
      const storageKey = occurrenceStorageKey("swaps", data);
      const saved = localStorage.getItem(storageKey);
      if (saved) {
        try {
          const parsed = JSON.parse(saved) as SwapState;
          setSwapIndexByExercise(parsed);
        } catch {
          setSwapIndexByExercise({});
        }
      } else {
        setSwapIndexByExercise({});
      }
      setWorkout(data);
      setCompletedSetsByExercise({});
      setWorkoutProgress(null);
      setMessage("");
      setNotesOpenByExercise({});
      setWorkoutSummary(null);
      setSetFeedbackByExercise({});
      setLoadIntelligenceByExercise({});
      setLoadContextByExercise({});
      resetSelectedLoadContext();
      setLoadOverrideByExercise({});
      setLastSetByExercise({});
      setBaselineByExercise({});
      setSelectedExerciseId(null);
      setTechniqueModal(null);
      setGlobalRestTimer(null);

      const initialRecommendations = Object.fromEntries(
        (data.exercises ?? [])
          .filter((exercise) => Boolean(exercise.live_recommendation))
          .map((exercise) => [exerciseKey(exercise), exercise.live_recommendation as WorkoutLiveRecommendation]),
      ) as Record<string, WorkoutLiveRecommendation>;
      setLiveRecommendationByExercise(initialRecommendations);

      try {
        const profile = await api.getProfile();
        const profileWeakAreas = Array.isArray(profile.weak_areas)
          ? profile.weak_areas.filter((value): value is string => typeof value === "string" && value.trim().length > 0)
          : [];
        setWeakAreas(profileWeakAreas);
      } catch {
        setWeakAreas([]);
      }

      // restore completed sets for this session if present
      let localCompleted: Record<string, number> = {};
      try {
        const completedKey = occurrenceStorageKey("completed", data);
        const savedCompleted = localStorage.getItem(completedKey);
        if (savedCompleted) {
          const parsed = JSON.parse(savedCompleted) as Record<string, number>;
          localCompleted = parsed;
        } else {
          localCompleted = {};
        }
      } catch {
        localCompleted = {};
      }

      // prefer server-side progress when available
      try {
        const { progress, generation } = await getScopedWorkoutProgress(workoutReference(data));
        applyProgressLoad(progress.exercises ?? [], generation);
        const serverCompleted = Object.fromEntries(
          (progress.exercises ?? []).map((item) => [item.exercise_occurrence_id ?? item.exercise_id, Number(item.completed_sets) || 0]),
        ) as Record<string, number>;
        const merged = Object.keys(serverCompleted).length > 0 ? serverCompleted : localCompleted;
        setCompletedSetsByExercise(merged);
        setWorkoutProgress({
          completed: Number(progress.completed_total) || 0,
          planned: Number(progress.planned_total) || 0,
          percent: Number(progress.percent_complete) || 0,
        });
        const completedKey = occurrenceStorageKey("completed", data);
        localStorage.setItem(completedKey, JSON.stringify(merged));
        if ((Number(progress.percent_complete) || 0) >= 100) {
          await loadWorkoutSummary(workoutReference(data));
        }
      } catch {
        setCompletedSetsByExercise(localCompleted);
        setWorkoutProgress(null);
      }
      return data;
    } catch (error) {
      setWorkout(null);
      setMessage(error instanceof Error && error.message === "No workout scheduled today"
        ? "Rest day — no workout is scheduled for your local date. Check Week for your selected dates."
        : "No workout available. Choose dates in Week first.");
      return null;
    }
  }, [loadWorkoutSummary, applyProgressLoad, resetSelectedLoadContext, getScopedWorkoutProgress]);

  const resetSorenessForm = useCallback(() => {
    setSorenessByMuscle(createInitialSorenessState());
    setSorenessNotes("");
    setSorenessStatus("Idle");
  }, []);

  const beginWorkoutLoad = useCallback(async () => {
    if (showSorenessModal) {
      return;
    }
    if (isBeginWorkoutLoadInProgress.current) {
      return;
    }
    isBeginWorkoutLoadInProgress.current = true;
    try {
      const today = await resolveLocalToday();
      const sorenessSkipKey = `hypertrophy_soreness_skip:${today}`;
      const reviewStatus = await api.getWeeklyReviewStatus();
      if (reviewStatus.today_is_sunday && reviewStatus.review_required) {
        setMessage("Sunday review required before starting workout. Go to Check-In to submit weekly review.");
        return;
      }

      const loadedWorkout = await loadToday();
      if (!loadedWorkout) {
        return;
      }

      if (sorenessDismissedDate.current === today) {
        return;
      }

      // Daily prompt policy:
      // - show the soreness modal once per calendar day
      // - Skip suppresses the modal for that same date
      try {
        if (localStorage.getItem(sorenessSkipKey)) {
          return;
        }
      } catch {
        // Ignore localStorage errors; fall back to normal behavior.
      }

      const entriesToday = await api.listSoreness(today, today);
      if (entriesToday.length > 0) {
        return;
      }
      resetSorenessForm();
      sorenessPromptDate.current = today;
      setShowSorenessModal(true);
    } catch {
      setMessage("Unable to verify soreness status. Try again.");
    } finally {
      isBeginWorkoutLoadInProgress.current = false;
    }
  }, [loadToday, resolveLocalToday, resetSorenessForm, showSorenessModal]);

  useEffect(() => {
    if (health !== "ok" || workout !== null || hasAutoLoadStarted.current) {
      return;
    }
    hasAutoLoadStarted.current = true;
    beginWorkoutLoad();
  }, [health, workout, beginWorkoutLoad]);

  function restartForChangedSorenessDate(today: string): boolean {
    if (sorenessPromptDate.current === today) return false;
    resetSorenessForm();
    sorenessPromptDate.current = null;
    sorenessDismissedDate.current = null;
    setShowSorenessModal(false);
    hasAutoLoadStarted.current = false;
    setWorkout(null);
    return true;
  }

  async function submitSorenessAndLoad() {
    setSorenessStatus("Saving soreness...");
    try {
      const today = await resolveLocalToday();
      if (restartForChangedSorenessDate(today)) return;
      const sorenessSkipKey = `hypertrophy_soreness_skip:${today}`;
      await api.createSoreness({
        entry_date: today,
        severity_by_muscle: sorenessByMuscle,
        notes: sorenessNotes || undefined,
      });
      // Once soreness is saved for today, suppress future modal prompts for this date.
      try {
        localStorage.removeItem(sorenessSkipKey);
      } catch {
        // ignore localStorage errors
      }
      setShowSorenessModal(false);
      sorenessPromptDate.current = null;
      await loadToday();
    } catch {
      setSorenessStatus("Failed to save soreness");
    }
  }

  useEffect(() => {
    if (!workout) {
      return;
    }
    const storageKey = occurrenceStorageKey("swaps", workout);
    localStorage.setItem(storageKey, JSON.stringify(swapIndexByExercise));
  }, [swapIndexByExercise, workout]);

  function toggleNotes(exerciseId: string) {
    setNotesOpenByExercise((prev) => ({ ...prev, [exerciseId]: !prev[exerciseId] }));
  }

  function selectSwap(exerciseId: string, selectedIndex: number) {
    setSwapIndexByExercise((prev) => {
      return { ...prev, [exerciseId]: selectedIndex };
    });
    setSwapTargetExerciseId(null);
  }

  async function handleSetComplete(
    exerciseId: string,
    completedCount: number,
    performed: PerformedSet,
  ) {
    if (!workout) return;
    // find exercise info for payload
    const exercise = (workout.exercises ?? []).find((e) => exerciseKey(e) === exerciseId);
    if (!exercise) return;

    const intelligence = intelligenceFor(exercise);
    const offeredDecision = currentLoadDecision(intelligence, completedCount - 1, exercise.sets);
    const context = loadContextByExercise[exerciseId] ?? intelligence?.load_context;
    const payload = {
      primary_exercise_id: exercise.primary_exercise_id ?? null,
      exercise_id: exercise.id,
      exercise_occurrence_id: exercise.exercise_occurrence_id,
      set_index: completedCount,
      reps: performed.reps,
      weight: performed.canonicalWeight ?? lbsToKg(performed.weight),
      rpe: performed.rpe,
      ...(context ? { load_context: context } : {}),
      ...(offeredDecision ? { load_recommendation_id: offeredDecision.id } : {}),
      ...(loadOverrideByExercise[exerciseId]?.trim() ? { load_override_reason: loadOverrideByExercise[exerciseId].trim() } : {}),
    } as const;

    const commandKey = pendingCommandKey(occurrenceStorageKey("attempt", workout), exerciseId, `work:${completedCount}`);
    try {
      const retained = retainLogPayload(commandKey, { ...payload, command_id: getLogCommand(commandKey) });
      const feedback = await api.logSet(workoutReference(workout), retained);
      acknowledgeLogCommand(commandKey);
      if (currentOccurrence.current !== workoutReference(workout)) return;
      setLastSetByExercise((prev) => ({ ...prev, [exerciseId]: performed }));
      setCompletedSetsByExercise((prev) => {
        const next = { ...prev, [exerciseId]: completedCount };
        try {
          const completedKey = occurrenceStorageKey("completed", workout);
          localStorage.setItem(completedKey, JSON.stringify(next));
        } catch {
          // ignore storage errors
        }
        return next;
      });

      advanceLoadGeneration(exerciseId);
      setMessage("");
      setSetFeedbackByExercise((prev) => ({ ...prev, [exerciseId]: feedback }));
      if (feedback.load_intelligence !== undefined) updateLoadIntelligence(exerciseId, feedback.load_intelligence ?? null);
      setLiveRecommendationByExercise((prev) => ({
        ...prev,
        [exerciseId]: feedback.live_recommendation,
      }));

      const restCycle = parseRestToSeconds(exercise.rest) ?? 90;
      setGlobalRestTimer({
        exerciseId,
        exerciseName: resolveExerciseName(exercise, swapIndexByExercise),
        secondsLeft: restCycle,
        restCycle,
      });

      const prescribedTechnique = authoredSetTechnique(exercise, completedCount);
      const techniqueKind = resolveTechniqueKind(exercise.authored_prescription ? { ...exercise, last_set_intensity_technique: prescribedTechnique } : exercise);
      if (techniqueKind && (exercise.authored_prescription ? Boolean(prescribedTechnique) : completedCount >= exercise.sets)) {
        setTechniqueModal({
          exerciseId,
          exerciseName: resolveExerciseName(exercise, swapIndexByExercise),
          workoutId: workoutReference(workout),
          parentSetIndex: completedCount,
          kind: techniqueKind,
          baseWeightLb: performed.weight,
          baseReps: performed.reps,
          instruction: prescribedTechnique,
          authored: Boolean(exercise.authored_prescription),
          bodyweight: isBodyweightAuthored(exercise),
        });
      }

      // refresh from server-side progress to keep client in sync
      try {
        const { progress, generation } = await getScopedWorkoutProgress(workoutReference(workout));
        if (currentOccurrence.current !== workoutReference(workout)) return;
        applyProgressLoad(progress.exercises ?? [], generation);
        const serverCompleted = Object.fromEntries(
          (progress.exercises ?? []).map((item) => [item.exercise_occurrence_id ?? item.exercise_id, Number(item.completed_sets) || 0]),
        ) as Record<string, number>;
        if (Object.keys(serverCompleted).length > 0) {
          setCompletedSetsByExercise(serverCompleted);
          const percent = Number(progress.percent_complete) || 0;
          setWorkoutProgress({
            completed: Number(progress.completed_total) || 0,
            planned: Number(progress.planned_total) || 0,
            percent,
          });
          const completedKey = occurrenceStorageKey("completed", workout);
          localStorage.setItem(completedKey, JSON.stringify(serverCompleted));
          if (percent >= 100) {
            await loadWorkoutSummary(workoutReference(workout));
          }
        }
      } catch {
        // keep optimistic state when progress refresh fails
      }
    } catch (e) {
      if (e instanceof ApiError && e.status === 422) {
        acknowledgeLogCommand(commandKey);
        if (currentOccurrence.current === workoutReference(workout)) setMessage(e.message);
        throw e;
      }
      if (e instanceof ApiError && e.status === 409 && e.code === "stale_load_recommendation") {
        acknowledgeLogCommand(commandKey);
        setLoadIntelligenceByExercise(previous => ({ ...previous, [exerciseId]: null }));
        if (exercise.exercise_occurrence_id && context) {
          try { const refreshed = await api.previewLoadGuidance(workoutReference(workout), exercise.exercise_occurrence_id, context);
            if (currentOccurrence.current === workoutReference(workout)) updateLoadIntelligence(exerciseId, refreshed);
          } catch { /* unknown advice remains cleared; draft can be reviewed */ }
        }
        if (currentOccurrence.current === workoutReference(workout)) setMessage(e.message);
        throw e;
      }
      if (currentOccurrence.current === workoutReference(workout)) setMessage("Set was not confirmed. Retry the same set before continuing.");
      throw e;
    }
  }

  async function handleLogTechniqueSubSet(
    state: NonNullable<TechniqueModalState>,
    performed: { reps: number; weight: number },
    ordinal: number,
  ) {
    const exercise = (workout?.exercises ?? []).find((entry) => exerciseKey(entry) === state.exerciseId);
    if (!exercise) throw new Error("Exercise occurrence is unavailable");
    const commandKey = pendingCommandKey(workout ? occurrenceStorageKey("attempt", workout) : state.workoutId, state.exerciseId, `${state.kind}:${state.parentSetIndex}:${ordinal}`);
    await api.logSet(state.workoutId, {
      command_id: getLogCommand(commandKey),
      primary_exercise_id: exercise.primary_exercise_id,
      exercise_id: exercise.id,
      exercise_occurrence_id: exercise.exercise_occurrence_id,
      set_index: state.parentSetIndex,
      reps: performed.reps,
      weight: lbsToKg(performed.weight),
      rpe: null,
      set_kind: state.kind,
      parent_set_index: state.parentSetIndex,
      technique: { type: state.kind, ordinal },
    });
    acknowledgeLogCommand(commandKey);
  }

  const swapTarget = (workout?.exercises ?? []).find((exercise) => exerciseKey(exercise) === swapTargetExerciseId) ?? null;
  const swapTargetCurrentIndex = swapTarget ? (swapIndexByExercise[exerciseKey(swapTarget)] ?? 0) : 0;
  const activeProgramId = workout ? extractProgramId(workout.session_id) : null;

  const todayDate = localToday
    ? `${formatCalendarDate(localToday.date)} · ${localToday.timezone}`
    : `${new Date().toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" })} · browser local date`;

  return (
    <div className="space-y-4 pb-[max(7rem,env(safe-area-inset-bottom))]">
      <div className="flex items-baseline justify-between gap-2">
        <h1 className="ui-title-page">Today</h1>
        <p className="ui-meta text-zinc-400">{todayDate}</p>
      </div>
      <div className="main-card main-card--module main-card--accent spacing-grid spacing-grid--tight">
        <Button className="min-h-[44px] w-full" onClick={beginWorkoutLoad}>
          <span className="inline-flex items-center gap-2">
            <UiIcon name="workout" className="ui-icon--action" />
            {workout ? "Reload" : "Load today's workout"}
          </span>
        </Button>
      </div>

      {message ? (
        <div className="main-card main-card--shell space-y-2 ui-body-sm" role="status">
          {message.startsWith("Rest day") ? <h2 className="text-base font-semibold">No workout scheduled today</h2> : null}
          <p>{message}</p>
          {message.includes("Check-In") ? (
            <Link
              href="/checkin"
              className="inline-flex items-center gap-2 rounded-md border border-[var(--ui-edge-idle)] bg-[var(--ui-surface-1)] px-3 py-2 text-sm text-zinc-100 hover:border-[var(--ui-edge-active)]"
            >
              <UiIcon name="body" className="ui-icon--action" />
              Go to Check-In
            </Link>
          ) : null}
          {message.startsWith("No workout available") || message.startsWith("Rest day") ? (
            <Link href="/week" className="inline-flex items-center gap-2 rounded-md border border-white/10 bg-zinc-900/70 px-3 py-2 text-sm text-zinc-100">
              <UiIcon name="plan" className="ui-icon--action" />
              Open Week Plan
            </Link>
          ) : null}
        </div>
      ) : null}

      {workout ? (
        <div className="space-y-3">
          <p className="ui-body-sm text-zinc-200">
            {workout.title} · {workoutProgress?.completed ?? 0}/{workoutProgress?.planned ?? 0} sets
          </p>

          <ul className="space-y-1.5" aria-label="Exercise list">
            {(workout.exercises ?? []).map((exercise) => {
              const selectedName = resolveExerciseName(exercise, swapIndexByExercise);
              const displayName = resolveDisplayExerciseName(exercise, selectedName, weakAreas);
              const completed = completedSetsByExercise[exerciseKey(exercise)] ?? 0;
              const done = completed >= exercise.sets;
              const baseline = exercise.performed_variant ? undefined : baselineByExercise[exerciseKey(exercise)];
              const lastSet = lastSetByExercise[exerciseKey(exercise)];
              const live = liveRecommendationByExercise[exerciseKey(exercise)];
              const plannedWorkingLb = exercise.recommended_working_weight == null ? 0 : kgToLbs(exercise.recommended_working_weight);
              const baselineWorkingLb =
                baseline != null ? baseline.workingWeightLb : plannedWorkingLb;
              const hasLive = live && typeof live.recommended_weight === "number";
              // Authoritative row working weight:
              // Before first working set:
              //   1) baseline estimate (if present)
              //   2) backend live recommendation (if any)
              //   3) planned working weight
              // After working sets have started:
              //   1) backend live recommendation
              //   2) planned working weight
              const rowWorkingLb =
                completed === 0
                  ? (baseline != null
                      ? baselineWorkingLb
                      : hasLive
                        ? kgToLbs(live!.recommended_weight!)
                        : plannedWorkingLb)
                  : hasLive
                    ? kgToLbs(live!.recommended_weight!)
                    : plannedWorkingLb;
              const intelligence = intelligenceFor(exercise);
              const ownedRowLoad = prefillLoadKg(currentLoadDecision(intelligence, completed, exercise.sets));
              return (
                <li key={exerciseKey(exercise)}>
                  <button
                    type="button"
                    className={`w-full rounded-lg border px-3 py-3 text-left transition-colors hover:border-zinc-700 hover:bg-zinc-800/80 ${
                      done
                        ? "border-red-500/30 bg-red-500/5"
                        : "border-zinc-800 bg-zinc-900/50"
                    }`}
                    onClick={() => setSelectedExerciseId(exerciseKey(exercise))}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-semibold leading-tight text-zinc-100">{displayName}</span>
                      <span className={`flex-shrink-0 rounded-full px-2 py-0.5 text-xs font-medium tabular-nums ${
                        done
                          ? "bg-red-500/15 text-red-300"
                          : completed > 0
                            ? "bg-zinc-800 text-zinc-300"
                            : "text-zinc-500"
                      }`}>
                        {completed}/{exercise.sets}
                      </span>
                    </div>
                    <div className="mt-1 flex items-center gap-2 text-xs text-zinc-500">
                      <span>{authoredRepLabel(exercise)} reps</span>
                      <span className="text-zinc-700">·</span>
                      <span>{intelligence !== undefined ? (ownedRowLoad === undefined ? "Record actual load" : `${kgToLbs(ownedRowLoad)} lb`)
                        : isBodyweightAuthored(exercise) ? "Bodyweight" : exercise.performed_variant ? "Record actual load" : `~${rowWorkingLb} lb`}</span>
                    </div>
                    {authoredRelationshipLabels(exercise).map((label) => (
                      <span key={label} className="mt-1 mr-2 inline-block text-xs text-amber-300">{label}</span>
                    ))}
                  </button>
                </li>
              );
            })}
          </ul>


          <WorkoutSummaryCard summary={workoutSummary} />
        </div>
      ) : null}

      {workout && selectedExerciseId ? (() => {
        const exercise = (workout.exercises ?? []).find((e) => exerciseKey(e) === selectedExerciseId);
        if (!exercise) {
          return null;
        }
        const selectedName = resolveExerciseName(exercise, swapIndexByExercise);
        const displayName = resolveDisplayExerciseName(exercise, selectedName, weakAreas);
        const weakPointInstruction = resolveWeakPointInstruction(exercise, weakAreas);
        const guideHref = activeProgramId && !exercise.performed_variant
          ? `/guides/${activeProgramId}/exercise/${exercise.primary_exercise_id ?? exercise.id}`
          : null;
        const completed = completedSetsByExercise[exerciseKey(exercise)] ?? 0;
        const recommendation = liveRecommendationByExercise[exerciseKey(exercise)];
        const feedback = setFeedbackByExercise[exerciseKey(exercise)];
        const mediaUrl = resolveExerciseMediaUrl(exercise);
        const substitutions = resolveSubstitutionCandidates(exercise, weakAreas);
        const warmUpCount = Math.max(0, parseInt(String(exercise.warm_up_sets ?? "0"), 10) || 0);
        const baseline = exercise.performed_variant ? undefined : baselineByExercise[exerciseKey(exercise)];
        const loadIntelligence = intelligenceFor(exercise);
        const loadContext = loadContextByExercise[exerciseKey(exercise)] ?? loadIntelligence?.load_context ?? { unit: "kg", display_unit: "lb", basis: "unknown" } as LoadContext;
        const lastSet = lastSetByExercise[exerciseKey(exercise)];
        const plannedWorkingLb = exercise.recommended_working_weight == null ? 0 : kgToLbs(exercise.recommended_working_weight);
        const baselineWorkingLb =
          baseline != null ? baseline.workingWeightLb : plannedWorkingLb;
        const hasRecommendation =
          recommendation && typeof recommendation.recommended_weight === "number";
        // Authoritative working weight for this set:
        // Before first working set:
        //   1) baseline estimate (if present)
        //   2) backend live recommendation (if any)
        //   3) planned working weight
        // After working sets have started:
        //   1) backend live recommendation
        //   2) planned working weight
        const derivedWorkingLb =
          exercise.performed_variant || isBodyweightAuthored(exercise) ? 0 : completed === 0
            ? (baseline != null
                ? baselineWorkingLb
                : hasRecommendation
                  ? kgToLbs(recommendation!.recommended_weight!)
                  : plannedWorkingLb)
            : hasRecommendation
              ? kgToLbs(recommendation!.recommended_weight!)
              : plannedWorkingLb;
        let doThisSetLine: string;
        if (exercise.authored_prescription) {
          const index = Math.min(completed + 1, exercise.sets);
          doThisSetLine = `${isBodyweightAuthored(exercise) ? "Bodyweight · " : ""}${authoredRepLabel(exercise, index)} reps · ${authoredSetDetails(exercise, index)}`;
        } else if (recommendation) {
          const guidance = resolveGuidanceText(recommendation.guidance_rationale, recommendation.guidance);
          doThisSetLine = guidance.trim()
            || `Next set: ${recommendation.recommended_reps_min}-${recommendation.recommended_reps_max} reps @ ${recommendation.recommended_weight == null ? "record actual load" : kgToLbs(recommendation.recommended_weight)} lbs`;
        } else if (feedback) {
          const guidance = resolveGuidanceText(feedback.guidance_rationale, feedback.guidance);
          doThisSetLine = guidance.trim()
            || `${authoredRepLabel(exercise)} reps @ ${Math.round(derivedWorkingLb)} lbs this set`;
        } else {
          doThisSetLine = `Do ${authoredRepLabel(exercise)} reps @ ${Math.round(derivedWorkingLb)} lbs this set`;
        }

        const currentSwapIndex = swapIndexByExercise[exerciseKey(exercise)] ?? 0;
        const altCandidates = resolveSubstitutionCandidates(exercise, weakAreas);
        const warmupLbs =
          exercise.performed_variant ? [] : baseline != null && baseline.warmupLbs.length > 0
            ? baseline.warmupLbs.slice(0, warmUpCount)
            : (exercise.warmups ?? []).slice(0, warmUpCount).map((kg) => kgToLbs(kg));
        const hasWarmup = warmUpCount > 0 && warmupLbs.length > 0;
        const hasCoachingDetails = !!(
          exercise.last_set_intensity_technique
          || exercise.rest
          || exercise.early_set_rpe
          || exercise.last_set_rpe
          || (typeof exercise.notes === "string" && exercise.notes.trim().length > 0)
        );

        const handleUndoLastSet = completed > 0 ? async (): Promise<number | false> => {
          if (undoInFlight.current) return false;
          undoInFlight.current = true;
          const commandKey = pendingCommandKey(occurrenceStorageKey("attempt", workout), exerciseKey(exercise), "undo");
          try {
            const result = await api.undoLastSet(workoutReference(workout), exercise.id, exercise.exercise_occurrence_id, getLogCommand(commandKey));
            acknowledgeLogCommand(commandKey);
            if (currentOccurrence.current !== workoutReference(workout)) return false;
            advanceLoadGeneration(exerciseKey(exercise));
            setLastSetByExercise((prev) => { const next = { ...prev }; delete next[exerciseKey(exercise)]; return next; });
            if (loadIntelligence !== undefined) updateLoadIntelligence(exerciseKey(exercise), result.load_intelligence ?? null);
            setSetFeedbackByExercise((prev) => { const next = { ...prev }; delete next[exerciseKey(exercise)]; return next; });
            setLiveRecommendationByExercise((prev) => {
              const next = { ...prev }; delete next[exerciseKey(exercise)];
              if (result.live_recommendation) next[exerciseKey(exercise)] = result.live_recommendation;
              return next;
            });
            setWorkoutSummary(null);
            const todayGeneration = captureLoadGeneration();
            const [progressResult, todayResult] = await Promise.allSettled([
              getScopedWorkoutProgress(workoutReference(workout)), api.getTodayWorkout(),
            ]);
            if (currentOccurrence.current !== workoutReference(workout)) return false;
            if (todayResult.status === "fulfilled" && workoutReference(todayResult.value) === workoutReference(workout)) {
              setWorkout(todayResult.value);
              applyProgressLoad(todayResult.value.exercises.map(item => ({ ...item, exercise_id: item.id })), todayGeneration);
              setLiveRecommendationByExercise(Object.fromEntries((todayResult.value.exercises ?? [])
                .filter((item) => item.live_recommendation).map((item) => [exerciseKey(item), item.live_recommendation as WorkoutLiveRecommendation])));
            }
            if (progressResult.status === "fulfilled") {
              const { progress, generation } = progressResult.value;
              applyProgressLoad(progress.exercises ?? [], generation);
              const serverCompleted = Object.fromEntries((progress.exercises ?? []).map((item) =>
                [item.exercise_occurrence_id ?? item.exercise_id, Number(item.completed_sets) || 0])) as Record<string, number>;
              setCompletedSetsByExercise(serverCompleted);
              setWorkoutProgress({ completed: Number(progress.completed_total) || 0, planned: Number(progress.planned_total) || 0, percent: Number(progress.percent_complete) || 0 });
              try { localStorage.setItem(occurrenceStorageKey("completed", workout), JSON.stringify(serverCompleted)); } catch { /* server still confirmed */ }
            } else if (result.live_recommendation) {
              setCompletedSetsByExercise((prev) => ({ ...prev, [exerciseKey(exercise)]: result.live_recommendation!.completed_sets }));
            }
            setMessage("");
            if (progressResult.status === "fulfilled") {
              return Number(progressResult.value.progress.exercises?.find((item) => (item.exercise_occurrence_id ?? item.exercise_id) === exerciseKey(exercise))?.completed_sets) || 0;
            }
            return result.live_recommendation?.completed_sets ?? Math.max(0, completed - 1);
          } catch {
            setMessage("Undo was not confirmed. Retry to confirm the same action.");
            return false;
          } finally { undoInFlight.current = false; }
        } : undefined;

        return (
          <ExerciseDetailOverlay
            key={`${exerciseKey(exercise)}/${exercise.performed_variant?.option_id ?? "source"}`}
            exercise={exercise}
            selectedName={displayName}
            guideHref={guideHref}
            completed={completed}
            doThisSetLine={doThisSetLine}
            derivedWorkingLb={derivedWorkingLb}
            loadIntelligence={loadIntelligence}
            loadContext={loadContext}
            onLoadContextChange={context => {
              const key = exerciseKey(exercise);
              loadPreviewVersions.current[key] = (loadPreviewVersions.current[key] ?? 0) + 1;
              selectLoadContext(key, context);
              setLoadContextByExercise(previous => ({ ...previous, [exerciseKey(exercise)]: context }));
              setLoadIntelligenceByExercise(previous => ({ ...previous, [exerciseKey(exercise)]: null }));
            }}
            onPreviewLoad={async context => {
              if (!exercise.exercise_occurrence_id) throw new Error("Exercise occurrence unavailable");
              const key = exerciseKey(exercise);
              const version = (loadPreviewVersions.current[key] ?? 0) + 1;
              loadPreviewVersions.current[key] = version;
              const result = await api.previewLoadGuidance(workoutReference(workout), exercise.exercise_occurrence_id, context);
              if (currentOccurrence.current !== workoutReference(workout) || loadPreviewVersions.current[key] !== version) return;
              updateLoadIntelligence(exerciseKey(exercise), result);
            }}
            overrideReason={loadOverrideByExercise[exerciseKey(exercise)] ?? ""}
            onOverrideReason={reason => setLoadOverrideByExercise(previous => ({ ...previous, [exerciseKey(exercise)]: reason }))}
            onCorrectSet={async (receipt, values) => {
              const commandKey = pendingCommandKey(occurrenceStorageKey("attempt", workout), exerciseKey(exercise), `correct:${receipt.id}`);
              const payload = retainLogPayload(commandKey, { ...values, command_id: getLogCommand(commandKey) });
              let result;
              try { result = await api.correctSet(receipt.id, payload); }
              catch (error) { if (error instanceof ApiError && error.status === 422) acknowledgeLogCommand(commandKey); throw error; }
              acknowledgeLogCommand(commandKey);
              if (currentOccurrence.current !== workoutReference(workout)) return;
              advanceLoadGeneration(exerciseKey(exercise));
              updateLoadIntelligence(exerciseKey(exercise), result.load_intelligence ?? null);
              setSetFeedbackByExercise(previous => { const next = { ...previous }; delete next[exerciseKey(exercise)]; return next; });
              setLiveRecommendationByExercise(previous => { const next = { ...previous }; delete next[exerciseKey(exercise)]; return next; });
              setWorkoutSummary(null);
              try { const { progress, generation } = await getScopedWorkoutProgress(workoutReference(workout));
                if (currentOccurrence.current === workoutReference(workout)) applyProgressLoad(progress.exercises ?? [], generation);
              } catch { /* confirmed receipt already invalidated old advice */ }
            }}
            warmUpCount={warmUpCount}
            baseline={baseline}
            warmupLbs={warmupLbs}
            hasWarmup={hasWarmup}
            hasCoachingDetails={hasCoachingDetails}
            techniquePanelState={techniqueModal && techniqueModal.exerciseId === exerciseKey(exercise) ? techniqueModal : null}
            onCloseTechniquePanel={() => setTechniqueModal(null)}
            onLogTechniquePanel={async (performed, ordinal) => {
              if (!techniqueModal || techniqueModal.exerciseId !== exerciseKey(exercise)) {
                return;
              }
              await handleLogTechniqueSubSet(techniqueModal, performed, ordinal);
            }}
            currentSwapIndex={currentSwapIndex}
            altCandidates={altCandidates}
            lastSet={lastSet ?? null}
            mediaUrl={mediaUrl}
            substitutions={substitutions}
            weakPointInstruction={weakPointInstruction}
            notesOpen={notesOpenByExercise[exerciseKey(exercise)] ?? false}
            isDeloadWeek={workout.deload?.active === true}
            onUndoLastSet={handleUndoLastSet}
            onAuthoredDecision={async (decision) => {
              if (!exercise.exercise_occurrence_id) throw new Error("Occurrence unavailable");
              const input = { ...decision, exercise_id: exercise.id, exercise_occurrence_id: exercise.exercise_occurrence_id,
                expected_revision: exercise.authored_constraint?.revision ?? 0, expected_source_lineage: exercise.source_lineage ?? {} };
              const commandKey = pendingCommandKey(occurrenceStorageKey("attempt", workout), exerciseKey(exercise), JSON.stringify(input));
              const result = await api.decideAuthoredSubstitution(workoutReference(workout), { ...input, command_id: getLogCommand(commandKey) });
              acknowledgeLogCommand(commandKey);
              if (currentOccurrence.current !== workoutReference(workout)) return;
              const key = exerciseKey(exercise);
              loadPreviewVersions.current[key] = (loadPreviewVersions.current[key] ?? 0) + 1;
              forgetSelectedLoadContext(key);
              setLoadIntelligenceByExercise(previous => {
                const next = { ...previous };
                if (loadIntelligence !== undefined || result.exercise.load_intelligence !== undefined) next[key] = result.exercise.load_intelligence ?? null;
                else delete next[key];
                return next;
              });
              setLoadContextByExercise(previous => { const next = { ...previous }; delete next[key]; return next; });
              setLoadOverrideByExercise(previous => { const next = { ...previous }; delete next[key]; return next; });
              setBaselineByExercise(previous => { const next = { ...previous }; delete next[key]; return next; });
              setLastSetByExercise(previous => { const next = { ...previous }; delete next[key]; return next; });
              setLiveRecommendationByExercise(previous => { const next = { ...previous }; delete next[key]; return next; });
              setSetFeedbackByExercise(previous => { const next = { ...previous }; delete next[key]; return next; });
              setWorkout(previous => previous ? { ...previous, exercises: previous.exercises.map(item =>
                exerciseKey(item) === exerciseKey(exercise) ? result.exercise : item) } : previous);
              setWorkoutSummary(null);
            }}
            onClose={() => setSelectedExerciseId(null)}
            onSwap={selectSwap}
            onToggleNotes={() => toggleNotes(exerciseKey(exercise))}
            onSwapTarget={() => setSwapTargetExerciseId(exerciseKey(exercise))}
            onSetComplete={handleSetComplete}
            onCalculateBaseline={(weightLb, reps) => {
              const estimated1RM = epleyEstimate1RMLbs(weightLb, reps);
              const workingWeightLb = workingWeightFrom1RMLb(estimated1RM);
              const warmupLbsCalc = warmupsFromWorkingWeightLb(workingWeightLb, warmUpCount || 3);
              setBaselineByExercise((prev) => ({
                ...prev,
                [exerciseKey(exercise)]: { weightLb, reps, estimated1RM, workingWeightLb, warmupLbs: warmupLbsCalc },
              }));
            }}
            globalRestTimer={globalRestTimer}
            onClearGlobalRestTimer={() => setGlobalRestTimer(null)}
          />
        );
      })() : null}

      {/* Global rest bar when overlay is closed (timer persists) */}
      {globalRestTimer != null && selectedExerciseId !== globalRestTimer.exerciseId ? (
        <div className="fixed bottom-0 left-0 right-0 z-40 flex items-center justify-between gap-3 border-t border-zinc-800 bg-zinc-900/95 px-4 py-3 backdrop-blur safe-area-pb">
          <span className="text-sm font-medium tabular-nums text-zinc-200">
            Rest: {Math.floor(globalRestTimer.secondsLeft / 60)}:{(globalRestTimer.secondsLeft % 60).toString().padStart(2, "0")} — {globalRestTimer.exerciseName}
          </span>
          <div className="flex gap-2">
            <Button
              type="button"
              variant="secondary"
              className="min-h-[36px] px-3 text-xs"
              onClick={() => setSelectedExerciseId(globalRestTimer.exerciseId)}
            >
              Open
            </Button>
            <Button
              type="button"
              variant="ghost"
              className="min-h-[36px] px-3 text-xs"
              onClick={() => setGlobalRestTimer(null)}
            >
              Stop
            </Button>
          </div>
        </div>
      ) : null}

      {swapTarget ? (
        <div className="fixed inset-0 z-[70] flex items-start justify-center bg-black/60 px-4 pb-6 pt-[max(1rem,env(safe-area-inset-top))] overflow-y-auto">
          <div className="main-card main-card--elevated w-full max-w-md spacing-grid max-h-[90dvh] overflow-y-auto">
            <div>
              <p className="text-sm font-semibold text-zinc-100">Choose a substitute</p>
              <p className="ui-meta">Slot: {swapTarget.name}</p>
            </div>

            {(() => {
              const weakPointHint = resolveWeakPointInstruction(swapTarget, weakAreas);
              if (!weakPointHint) {
                return null;
              }
              return (
                <p className="ui-meta">
                  {weakPointHint}
                </p>
              );
            })()}

            <div className="ui-segmented ui-segmented--auto">
              <Button
                className="w-full justify-start"
                onClick={() => selectSwap(exerciseKey(swapTarget), 0)}
                type="button"
                variant="segment"
                aria-pressed={swapTargetCurrentIndex === 0}
              >
                {swapTarget.name} (Original)
              </Button>

              {resolveSubstitutionCandidates(swapTarget, weakAreas).map((candidate, index) => {
                const value = index + 1;
                return (
                  <Button
                    key={`${swapTarget.id}-${candidate}`}
                    className="w-full justify-start"
                    onClick={() => selectSwap(exerciseKey(swapTarget), value)}
                    type="button"
                    variant="segment"
                    aria-pressed={swapTargetCurrentIndex === value}
                  >
                    {candidate}
                  </Button>
                );
              })}
            </div>

            <Button
              className="w-full"
              onClick={() => setSwapTargetExerciseId(null)}
              type="button"
              variant="ghost"
            >
              <span className="inline-flex items-center gap-2">
                <UiIcon name="close" className="ui-icon--action" />
                Close
              </span>
            </Button>
          </div>
        </div>
      ) : null}

      {showSorenessModal ? (
        <div className="fixed inset-0 z-[70] flex items-start justify-center bg-black/60 px-4 pb-6 pt-[max(1rem,env(safe-area-inset-top))] overflow-y-auto">
          <div className="main-card main-card--elevated w-full max-w-md spacing-grid max-h-[90dvh] overflow-y-auto">
            <div>
              <p className="text-sm font-semibold text-zinc-100">What&rsquo;s sore today?</p>
              <p className="ui-meta">Log soreness before starting this workout.</p>
            </div>

            <div className="space-y-2">
              {MUSCLE_GROUPS.map((muscle) => (
                <div key={muscle} className="flex items-center justify-between gap-2">
                  <span className="ui-label text-zinc-300">{muscle}</span>
                  <select
                    className="ui-select p-1 text-xs"
                    onChange={(event) => {
                      const value = event.target.value as SorenessSeverity;
                      setSorenessByMuscle((prev) => ({ ...prev, [muscle]: value }));
                    }}
                    value={sorenessByMuscle[muscle]}
                  >
                    <option value="none">None</option>
                    <option value="mild">Mild</option>
                    <option value="moderate">Moderate</option>
                    <option value="severe">Severe</option>
                  </select>
                </div>
              ))}
            </div>

            <textarea
              className="ui-textarea text-xs"
              onChange={(event) => setSorenessNotes(event.target.value)}
              placeholder="Optional soreness notes"
              rows={3}
              value={sorenessNotes}
            />

            <p className="ui-meta">{sorenessStatus}</p>

            <div className="flex gap-2">
              <Button className="w-full" onClick={submitSorenessAndLoad} type="button">
                <span className="inline-flex items-center gap-2">
                  <UiIcon name="save" className="ui-icon--action" />
                  Save & Start Workout
                </span>
              </Button>
              <Button
                className="w-full"
                onClick={async () => {
                  try {
                    const today = await resolveLocalToday();
                    if (restartForChangedSorenessDate(today)) return;
                    const sorenessSkipKey = `hypertrophy_soreness_skip:${today}`;
                    try {
                      localStorage.setItem(sorenessSkipKey, "1");
                    } catch {
                      // ignore localStorage errors
                    }
                    sorenessDismissedDate.current = today;
                    sorenessPromptDate.current = null;
                    setShowSorenessModal(false);
                    await loadToday();
                  } catch {
                    setSorenessStatus("Unable to verify the local date. Try again.");
                  }
                }}
                type="button"
                variant="secondary"
              >
                <span className="inline-flex items-center gap-2">
                  <UiIcon name="skip" className="ui-icon--action" />
                  Skip
                </span>
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
