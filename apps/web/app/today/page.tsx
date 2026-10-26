"use client";
import {InlineTechniquePanel,type TechniqueModalState} from "@/components/technique-entry";
import { AtlasRunner } from "@/components/atlas-runner";
import { useAppearance } from "@/components/appearance-provider";
import { AuthoredWarmups, type PerformedWarmup } from "@/components/authored-warmups";
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
  isObsoleteCorrectionTarget,
  type PerformedSet,
} from "@/components/exercise-control";
import {
  api,
  getToken,
  ApiError,
  type SorenessSeverity,
  type WorkoutExercise,
  type WorkoutLiveRecommendation,
  type WorkoutSession,
  type WorkoutSetFeedback,
  type WorkoutSummary,
  type LoadContext,
  type InitialCalibrationCommand,
  type LoadIntelligence,
  type EffectiveLoadSet,
} from "@/lib/api";
import { accountScope, canonicalLoad, displayLoad } from "@/lib/appearance";
import { parseRestToSeconds } from "@/lib/rest";
import { authoredRelationshipLabels } from "@/lib/authored-relationships";
import { formatCalendarDate } from "@/lib/calendar-date";
import { resolveGuidanceText, currentLoadDecision, prefillLoadKg, useDeclaredLoadContextGuard, type LoadProjectionGeneration } from "@/lib/today-guidance";
import { lbsToKg } from "@/lib/weight";

import { exerciseKey, workoutReference, occurrenceStorageKey, pendingCommandKey, getLogCommand, acknowledgeLogCommand, retainLogPayload, pendingLogPayload } from "@/lib/workout-identity";

type PageReadScope = { token: string | null; epoch: number };
function exerciseAuthorityIdentity(exercise: WorkoutExercise): string {
  const variant = exercise.performed_variant;
  return JSON.stringify([exercise.source_lineage ?? null, variant ? [variant.option_id, variant.id, variant.load_semantics] : null],
    (_key, value) => value && typeof value === "object" && !Array.isArray(value)
      ? Object.fromEntries(Object.entries(value).sort(([left], [right]) => left.localeCompare(right))) : value);
}

type UndoAttempt = { scope: string; workoutId: string; exerciseId: string; exerciseIdentity: string; exerciseOccurrenceId?: string; command: string };
function isDefinitiveUndoRejection(error: unknown): error is ApiError {
  return error instanceof ApiError && error.status === 409 && error.message === "Historical replay context unavailable; original record retained without changes";
}
function undoRecoveryStorageKey() {
  return `hypertrophy_undo_recovery_v1:${accountScope(getToken()) ?? "guest"}`;
}

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
  if (exercise.customized) return exercise.name;
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
  if (exercise.customized || !isWeakPointExercise(exercise)) {
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
  if (exercise.customized || exercise.authored_prescription || exercise.authored_constraint) return [];
  const explicit = (exercise.substitution_candidates ?? []).filter((item) => item.trim().length > 0);
  if (explicit.length > 0) {
    return explicit;
  }
  return resolveWeakPointFallbackCandidates(exercise, weakAreas);
}

function resolveDisplayExerciseName(exercise: WorkoutExercise, selectedName: string, weakAreas: string[]): string {
  if (exercise.customized || !isWeakPointExercise(exercise)) {
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
  if (exercise.customized || !isWeakPointExercise(exercise)) {
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
  const {preferences} = useAppearance();
  const load = (kg: number) => `${displayLoad(kg, preferences.weight_unit)} ${preferences.weight_unit}`;
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
      <p className="telemetry-meta">Review load guidance for each exercise below.</p>
      <div className="space-y-2">
        {exercises.map((item) => {
          const customized = item.decision_trace?.owner === "api.workout_customized-v1";
          return (
          <div key={item.exercise_occurrence_id ?? item.exercise_id} className="rounded-md border border-zinc-800 bg-zinc-900/40 p-2 text-xs text-zinc-300">
            <p className="font-semibold text-zinc-100">{item.performed_variant?.name ?? item.name}</p>
            {item.performed_variant ? <p>Original authored exercise: {item.name} · confirmed source-approved variant</p> : null}
            <p>
              Planned: {item.planned_sets} sets · {item.planned_reps_min != null ? `${item.planned_reps_min}-${item.planned_reps_max}` : "authored target"} reps · {item.load_semantics === "bodyweight" ? "Bodyweight" : item.load_recommendation_available === false ? "Record actual load" : item.planned_weight == null ? "Load unknown" : load(item.planned_weight)}
            </p>
            <p>
              Performed: {item.performed_sets} sets · avg {item.average_performed_reps} reps · {item.load_semantics === "bodyweight" ? (item.average_performed_weight > 0 ? `Bodyweight + ${load(item.average_performed_weight)} added` : "Bodyweight (no added load)") : load(item.average_performed_weight)}
            </p>
            {item.load_intelligence ? <>
              <p>Next exposure: {item.load_intelligence.next_exposure.action}{item.load_intelligence.next_exposure.recommended_weight != null ? ` · ${load(item.load_intelligence.next_exposure.recommended_weight)}` : " · no new load inferred"}</p>
              <p>{item.load_intelligence.next_exposure.explanation}</p>
              {item.load_intelligence.next_exposure.known_baseline_weight != null ? <p>Known baseline: {load(item.load_intelligence.next_exposure.known_baseline_weight)}</p> : null}
            </> : <>
              <p>Next: {item.load_semantics === "bodyweight" ? "Bodyweight" : item.load_recommendation_available === false || item.next_working_weight == null ? "Load advice pending comparable evidence" : load(item.next_working_weight)}</p>
              <p>{customized ? item.guidance : resolveGuidanceText(item.guidance_rationale, item.guidance)}</p>
            </>}
          </div>
        );})}
      </div>
    </div>
  );
}

function ExerciseDetailOverlay({
  exercise,
  navigation,
  onSelectExercise,
  selectedName,
  guideHref,
  completed,
  techniquePanelState,
  onCloseTechniquePanel,
  onLogTechniquePanel,
  mediaUrl,
  weakPointInstruction,
  liveGuidance,
  onUndoLastSet,
  undoRecovery,
  onClose,
  onSwapTarget,
  onSetComplete,
  onAuthoredDecision,
  globalRestTimer,
  onClearGlobalRestTimer,
  loadIntelligence,
  loadContext,
  onLoadContextChange,
  onPreviewLoad,
  onSaveCalibration,
  overrideReason,
  onOverrideReason,
  onCorrectSet,
  onWarmupComplete,
  warmupCommandScope,
  effectiveSets,
}: Readonly<{
  exercise: WorkoutExercise;
  navigation: Array<{id:string;name:string;completed:number;total:number}>;
  onSelectExercise: (id:string)=>void;
  selectedName: string;
  guideHref: string | null;
  completed: number;
  techniquePanelState: NonNullable<TechniqueModalState> | null;
  onCloseTechniquePanel: () => void;
  onLogTechniquePanel: (performed: { reps: number; weight: number }, ordinal: number) => Promise<void>;
  mediaUrl: string | null;
  weakPointInstruction: string | null;
  liveGuidance: string;
  onUndoLastSet?: () => Promise<number | false> | void;
  undoRecovery: boolean;
  onClose: () => void;
  onSwapTarget: () => void;
  onSetComplete: (exerciseId: string, count: number, performed: PerformedSet) => Promise<void> | void;
  onAuthoredDecision: (decision: AuthoredDecision) => Promise<void>;
  globalRestTimer: { exerciseId: string; exerciseName: string; secondsLeft: number; restCycle: number } | null;
  onClearGlobalRestTimer: () => void;
  loadIntelligence: LoadIntelligence | null | undefined;
  loadContext: LoadContext;
  onLoadContextChange: (context: LoadContext) => void;
  onPreviewLoad: (context: LoadContext) => Promise<void>;
  onSaveCalibration: (command: InitialCalibrationCommand, isRetry?: boolean) => Promise<void>;
  overrideReason: string;
  onOverrideReason: (reason: string) => void;
  effectiveSets: EffectiveLoadSet[];
  warmupCommandScope: string;
  onWarmupComplete: (ordinal: number, performed: PerformedWarmup) => Promise<void>;
  onCorrectSet: (receipt: EffectiveLoadSet, values: { reps: number; weight: number; rpe?: number | null;actual_rir?:number|null;technique_quality?:"acceptable"|"poor"|"unknown"|null;pain?:boolean|null; reason: string }) => Promise<void>;
}>) {

  const bodyweight = isBodyweightAuthored(exercise) || Boolean(exercise.customized && exercise.load_semantics === "bodyweight");
  return <AtlasRunner exercise={exercise} name={selectedName} completed={completed} scope={warmupCommandScope}
    guidance={loadIntelligence} context={loadContext} receipts={effectiveSets} navigation={navigation} onSelect={onSelectExercise}
    onSaveCalibration={exercise.customized ? undefined : onSaveCalibration}
    onClose={onClose} submit={onSetComplete} onUndo={onUndoLastSet} undoRecovery={undoRecovery} onCorrect={onCorrectSet} rest={globalRestTimer} endRest={onClearGlobalRestTimer}
    warmups={exercise.authored_prescription ? <AuthoredWarmups guidance={loadIntelligence?.warmup_guidance} sourceCount={authoredWarmupLabel(exercise)}
      receipts={effectiveSets} loadContext={loadContext} commandScope={warmupCommandScope} exerciseId={exerciseKey(exercise)}
      performedVariant={Boolean(exercise.performed_variant)} bodyweight={bodyweight}
      disabled={["unresolved", "infeasible", "declined"].includes(exercise.authored_constraint?.execution_status ?? exercise.authored_constraint?.status ?? "")}
      onLog={onWarmupComplete}/> : <p>{exercise.warm_up_sets ? `Prescribed warm-up: ${exercise.warm_up_sets}. ${exercise.notes ?? ""}` : "No numeric warm-up prescription is provided for this exercise. Follow the program’s preparation instructions."}</p>}
    technique={techniquePanelState ? <InlineTechniquePanel key={`${techniquePanelState.exerciseId}:${techniquePanelState.kind}:${techniquePanelState.parentSetIndex}`} scope={warmupCommandScope} receipts={effectiveSets} state={techniquePanelState} onClose={onCloseTechniquePanel} onLog={onLogTechniquePanel}/> : null}
    details={<div className="space-y-4">
      {authoredRelationshipLabels(exercise).map(label=><p key={label}>{label}</p>)}
      <p>{exercise.notes ?? "No additional instructions for this slot."}</p>
      {exercise.last_set_intensity_technique ? <p>Source technique: {exercise.last_set_intensity_technique}</p> : null}
      {liveGuidance ? <p>{liveGuidance}</p> : null}
      {weakPointInstruction ? <p>{weakPointInstruction}</p> : null}
      {!exercise.customized && !exercise.authored_prescription && !exercise.authored_constraint ? <Button variant="secondary" onClick={() => { document.querySelectorAll<HTMLDialogElement>("dialog[open]").forEach(dialog=>dialog.close()); onSwapTarget(); }}>Swap</Button> : null}
      {guideHref ? <Link className="ux-button ux-button-secondary" href={guideHref}>Exercise guide</Link> : null}
      {mediaUrl ? <a className="ux-button ux-button-secondary" href={mediaUrl} target="_blank" rel="noreferrer">Watch demonstration</a> : null}
      {exercise.authored_prescription || exercise.authored_constraint ? <AuthoredConstraintCard exercise={exercise} onDecision={onAuthoredDecision} effectiveSets={effectiveSets} onUndoLastSet={onUndoLastSet}/> : null}
      <LoadIntelligencePanel hideReceipts guidance={loadIntelligence ?? null} completed={completed} total={exercise.sets} loadContext={loadContext}
        onContextChange={onLoadContextChange} onPreview={onPreviewLoad} overrideReason={overrideReason} onOverrideReason={onOverrideReason}
        onCorrect={onCorrectSet} effectiveSets={effectiveSets} requireExternalWeight={!bodyweight}/>
      {exercise.customized ? <><p>Recorded setup: {exercise.customized.identity.setup}. Load basis: {exercise.load_semantics?.replaceAll("_"," ")}.</p><p>{exercise.customized_load_decision?.reason_codes.map(reason=>reason.replaceAll("_"," ")).join("; ")}{exercise.customized_load_decision?.reason_codes.length ? "." : ""}</p></> : null}
    </div>}/>
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
  const {preferences} = useAppearance();
  const [health, setHealth] = useState("loading");
  const [workoutLoading, setWorkoutLoading] = useState(false);
  const [occurrenceVerified, setOccurrenceVerified] = useState(false);
  const [accountGeneration, setAccountGeneration] = useState(0);
  const pageReadEpoch = useRef(0);
  const todayReadVersion = useRef(0);
  const mounted = useRef(true);
  const invalidatePageReads = useCallback(() => { ++pageReadEpoch.current; ++todayReadVersion.current; }, []);
  const capturePageRead = useCallback((): PageReadScope => ({ token: getToken(), epoch: pageReadEpoch.current }), []);
  const isCurrentPageRead = useCallback((scope: PageReadScope) =>
    mounted.current && scope.epoch === pageReadEpoch.current && scope.token === getToken(), []);
  const [workout, setWorkout] = useState<WorkoutSession | null>(null);
  const currentWorkout = useRef(workout);
  useEffect(() => { currentWorkout.current = workout; }, [workout]);
  const [message, setMessage] = useState("Loading your scheduled workout…");
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
  const [effectiveSetsByExercise, setEffectiveSetsByExercise] = useState<Record<string, EffectiveLoadSet[]>>({});
  const [loadContextByExercise, setLoadContextByExercise] = useState<Record<string, LoadContext>>({});
  const [loadOverrideByExercise, setLoadOverrideByExercise] = useState<Record<string, string>>({});
  const loadPreviewVersions = useRef<Record<string, number>>({});
  const { reset: resetSelectedLoadContext, select: selectLoadContext, matches: matchesSelectedLoadContext, forget: forgetSelectedLoadContext, capture: captureLoadGeneration, isCurrent: isCurrentLoadGeneration, advance: advanceLoadGeneration } = useDeclaredLoadContextGuard();
  const updateLoadIntelligence = useCallback((key: string, guidance: LoadIntelligence | null) => {
    // Actual receipts remain authoritative across a declared-context edit;
    // only advice is constrained by the selected context signature.
    if (guidance) setEffectiveSetsByExercise(previous => ({ ...previous, [key]: guidance.effective_sets }));
    if (matchesSelectedLoadContext(key, guidance)) setLoadIntelligenceByExercise(previous => ({ ...previous, [key]: guidance }));
  }, [matchesSelectedLoadContext]);

  function intelligenceFor(exercise: WorkoutExercise): LoadIntelligence | null | undefined {
    if (exercise.customized) return undefined;
    const key = exerciseKey(exercise);
    return Object.prototype.hasOwnProperty.call(loadIntelligenceByExercise, key) ? loadIntelligenceByExercise[key] : exercise.load_intelligence;
  }
  const applyProgressLoad = useCallback((exercises: Array<{ exercise_occurrence_id?: string; exercise_id: string; load_intelligence?: LoadIntelligence | null }>, generation?: LoadProjectionGeneration) => {
    const current = exercises.filter(item => item.load_intelligence !== undefined && isCurrentLoadGeneration(item.exercise_occurrence_id ?? item.exercise_id, generation));
    const accepted = current.filter(item => matchesSelectedLoadContext(item.exercise_occurrence_id ?? item.exercise_id, item.load_intelligence));
    setEffectiveSetsByExercise(previous => {
      const next = { ...previous };
      for (const item of current) if (item.load_intelligence) next[item.exercise_occurrence_id ?? item.exercise_id] = item.load_intelligence.effective_sets;
      return next;
    });
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
  /** Last logged set per exercise (reps, weight) to suggest next set. Keyed by exercise id. */
  const [lastSetByExercise, setLastSetByExercise] = useState<Record<string, { reps: number; weight: number }>>({});
  const [techniqueModal, setTechniqueModal] = useState<TechniqueModalState>(null);
  /** Persistent rest timer when overlay is closed; single source of truth. */
  const [globalRestTimer, setGlobalRestTimer] = useState<{
    exerciseId: string;
    exerciseName: string;
    secondsLeft: number;
    restCycle: number;
    deadline: number;
  } | null>(null);
  const currentOccurrence = useRef<string | null>(null);
  const undoInFlight = useRef(false);
  const [undoRecovery, setUndoRecovery] = useState<UndoAttempt | null>(() => pendingLogPayload<UndoAttempt>(undoRecoveryStorageKey()));
  const undoRecoveryRef = useRef(undoRecovery);
  const [priorUndoBusy, setPriorUndoBusy] = useState(false);
  const hasAutoLoadStarted = useRef(false);
  const isBeginWorkoutLoadInProgress = useRef(false);
  const sorenessDismissedDate = useRef<string | null>(null);
  const sorenessPromptDate = useRef<string | null>(null);

  const resetExerciseAuthority = useCallback((key: string, refreshed: WorkoutExercise, hadGuidance: boolean) => {
    forgetSelectedLoadContext(key);
    if (refreshed.load_intelligence) setEffectiveSetsByExercise(previous => ({ ...previous, [key]: refreshed.load_intelligence!.effective_sets }));
    setLoadIntelligenceByExercise(previous => {
      const next = { ...previous };
      if (Object.prototype.hasOwnProperty.call(previous, key) || hadGuidance || refreshed.load_intelligence !== undefined) next[key] = refreshed.load_intelligence ?? null;
      else delete next[key];
      return next;
    });
    setLoadContextByExercise(previous => { const next = { ...previous }; delete next[key]; return next; });
    setLoadOverrideByExercise(previous => { const next = { ...previous }; delete next[key]; return next; });
    setLastSetByExercise(previous => { const next = { ...previous }; delete next[key]; return next; });
    setLiveRecommendationByExercise(previous => { const next = { ...previous }; delete next[key]; return next; });
    setSetFeedbackByExercise(previous => { const next = { ...previous }; delete next[key]; return next; });
    setWorkoutSummary(null);
  }, [forgetSelectedLoadContext]);

  const loadWorkoutSummary = useCallback(async (workoutId: string) => {
    const scope = capturePageRead();
    const generation = captureLoadGeneration();
    const isCurrent = () => isCurrentPageRead(scope) && currentOccurrence.current === workoutId &&
      JSON.stringify(captureLoadGeneration()) === JSON.stringify(generation);
    try {
      const summary = await api.getWorkoutSummary(workoutId);
      if (isCurrent()) setWorkoutSummary(summary);
    } catch {
      if (isCurrent()) setWorkoutSummary(null);
    }
  }, [capturePageRead, isCurrentPageRead, captureLoadGeneration]);

  useEffect(() => {
    mounted.current = true;
    let token = getToken();
    const syncAccount = () => {
      if (getToken() === token) return;
      token = getToken();
      invalidatePageReads();
      currentOccurrence.current = null;
      hasAutoLoadStarted.current = false;
      isBeginWorkoutLoadInProgress.current = false;
      undoInFlight.current = false;
      setPriorUndoBusy(false);
      sorenessDismissedDate.current = null;
      sorenessPromptDate.current = null;
      setWorkout(null);
      setOccurrenceVerified(false);
      setSelectedExerciseId(null);
      setTechniqueModal(null);
      setGlobalRestTimer(null);
      setSwapTargetExerciseId(null);
      setLocalToday(null);
      setWeakAreas([]);
      setWorkoutSummary(null);
      setWorkoutProgress(null);
      setCompletedSetsByExercise({});
      setShowSorenessModal(false);
      setSorenessByMuscle(createInitialSorenessState());
      setSorenessNotes("");
      setSorenessStatus("Idle");
      const recovery = pendingLogPayload<UndoAttempt>(undoRecoveryStorageKey());
      undoRecoveryRef.current = recovery;
      setUndoRecovery(recovery);
      resetSelectedLoadContext();
      setWorkoutLoading(false);
      setMessage("Loading your scheduled workout…");
      setAccountGeneration(value => value + 1);
    };
    const storageSync = (event: StorageEvent) => {
      if (event.key === "hypertrophy_token" || event.key === null) syncAccount();
    };
    window.addEventListener("hypertrophy:auth-token-changed", syncAccount);
    window.addEventListener("storage", storageSync);
    return () => {
      mounted.current = false;
      invalidatePageReads();
      hasAutoLoadStarted.current = false;
      isBeginWorkoutLoadInProgress.current = false;
      window.removeEventListener("hypertrophy:auth-token-changed", syncAccount);
      window.removeEventListener("storage", storageSync);
    };
  }, [resetSelectedLoadContext, invalidatePageReads]);

  // Global rest timer countdown
  useEffect(() => {
    if (!globalRestTimer) return;
    const id = setInterval(() => {
      setGlobalRestTimer((prev) => {
        if (!prev) return null;
        const secondsLeft = Math.max(0, Math.ceil((prev.deadline - Date.now()) / 1000));
        return secondsLeft > 0 ? { ...prev, secondsLeft } : null;
      });
    }, 1000);
    return () => clearInterval(id);
  }, [globalRestTimer]);

  useEffect(() => {
    if (!workout) return;
    try {
      const key = occurrenceStorageKey("rest", workout);
      if (globalRestTimer) localStorage.setItem(key, JSON.stringify(globalRestTimer));
      else localStorage.removeItem(key);
    } catch { /* countdown remains available in memory */ }
  }, [globalRestTimer, workout]);
  useEffect(() => {
    if(!workout)return;
    try { const key=occurrenceStorageKey("technique",workout);
      if(techniqueModal)localStorage.setItem(key,JSON.stringify({
        workoutId:techniqueModal.workoutId, exerciseId:techniqueModal.exerciseId,
        parentSetIndex:techniqueModal.parentSetIndex, kind:techniqueModal.kind, unit:techniqueModal.unit,
      }));else localStorage.removeItem(key);
    } catch { /* in-memory technique remains usable */ }
  }, [techniqueModal,workout]);
  useEffect(() => {
    if (!workout || !selectedExerciseId) return;
    try { localStorage.setItem(occurrenceStorageKey("selected", workout), selectedExerciseId); } catch { /* in-memory selection */ }
  }, [selectedExerciseId, workout]);

  useEffect(() => {
    let active = true;
    api.health()
      .then(data => { if (active) setHealth(data.status); })
      .catch(() => {
        if (!active) return;
        setHealth("offline");
        setMessage("Workout service unavailable. Retry loading your workout. Your saved history is unchanged.");
      });
    return () => { active = false; };
  }, []);

  const resolveLocalToday = useCallback(async (): Promise<string> => {
    const scope = capturePageRead();
    const browserTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
    const context = await api.getSchedulingContext(browserTimezone);
    if (!isCurrentPageRead(scope)) throw new Error("Workout read superseded");
    if (!/^\d{4}-\d{2}-\d{2}$/.test(context.local_today) || !context.timezone) {
      throw new Error("Scheduling date unavailable");
    }
    setLocalToday({ date: context.local_today, timezone: context.timezone });
    return context.local_today;
  }, [capturePageRead, isCurrentPageRead]);

  const loadToday = useCallback(async (): Promise<WorkoutSession | null> => {
    const scope = capturePageRead();
    const version = ++todayReadVersion.current;
    const requestGeneration = captureLoadGeneration();
    const isCurrent = () => isCurrentPageRead(scope) && version === todayReadVersion.current;
    setOccurrenceVerified(false);
    try {
      const data = await api.getTodayWorkout();
      if (!isCurrent()) return null;
      const sameOccurrence = currentOccurrence.current === workoutReference(data);
      // A read begun before a saved set or context edit cannot replace newer state.
      if (sameOccurrence && data.exercises.some(exercise => !isCurrentLoadGeneration(exerciseKey(exercise), requestGeneration))) {
        setMessage("Workout changed while loading. Reload to verify the current workout. Your saved history is unchanged.");
        return null;
      }
      currentOccurrence.current = workoutReference(data);
      setOccurrenceVerified(true);
      if (!sameOccurrence) {
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
        const savedUndo = pendingLogPayload<UndoAttempt>(undoRecoveryStorageKey());
        undoRecoveryRef.current = savedUndo; setUndoRecovery(savedUndo);
        setWorkout(data);
        setCompletedSetsByExercise(Object.fromEntries(data.exercises.map(item => [exerciseKey(item), item.completed_sets ?? 0])));
        setWorkoutProgress(null);
        setMessage("");
        setNotesOpenByExercise({});
        setWorkoutSummary(null);
        setSetFeedbackByExercise({});
        setLoadIntelligenceByExercise({});
        setEffectiveSetsByExercise(Object.fromEntries(data.exercises.filter(item => item.load_intelligence || item.customized_receipts).map(item => [exerciseKey(item), item.customized_receipts ?? item.load_intelligence!.effective_sets])));
        setLoadContextByExercise({});
        resetSelectedLoadContext();
        setLoadOverrideByExercise({});
        setLastSetByExercise({});
        let selected: string | null = null;
        let restoredTechnique: TechniqueModalState = null;
        let restoredRest: typeof globalRestTimer = null;
        try {
          selected = localStorage.getItem(occurrenceStorageKey("selected", data));
          const savedTechnique = JSON.parse(localStorage.getItem(occurrenceStorageKey("technique",data)) ?? "null");
          const techniqueExercise = data.exercises.find(e => exerciseKey(e) === savedTechnique?.exerciseId);
          if (savedTechnique?.workoutId === workoutReference(data) && techniqueExercise
              && Number.isInteger(savedTechnique.parentSetIndex) && savedTechnique.parentSetIndex > 0
              && savedTechnique.parentSetIndex <= techniqueExercise.sets && ["kg","lb"].includes(savedTechnique.unit)) {
            // Rehydrate source instructions from this occurrence, never browser storage.
            const instruction = authoredSetTechnique(techniqueExercise, savedTechnique.parentSetIndex);
            const kind = resolveTechniqueKind(techniqueExercise.authored_prescription
              ? {...techniqueExercise,last_set_intensity_technique:instruction} : techniqueExercise);
            if (kind && kind === savedTechnique.kind && (!techniqueExercise.authored_prescription || instruction)) {
              restoredTechnique = {workoutId:workoutReference(data),exerciseId:exerciseKey(techniqueExercise),
                exerciseName:resolveExerciseName(techniqueExercise,{}),parentSetIndex:savedTechnique.parentSetIndex,
                kind,unit:savedTechnique.unit,instruction,authored:Boolean(techniqueExercise.authored_prescription),
                bodyweight:isBodyweightAuthored(techniqueExercise)};
            }
          }
          const savedRest = JSON.parse(localStorage.getItem(occurrenceStorageKey("rest", data)) ?? "null");
          if (savedRest && Number.isFinite(savedRest.deadline) && savedRest.deadline > Date.now() && data.exercises.some(e => exerciseKey(e) === savedRest.exerciseId)) {
            restoredRest = {...savedRest, secondsLeft: Math.ceil((savedRest.deadline-Date.now())/1000)};
          }
        } catch { /* storage is optional */ }
        if (savedUndo) selected = savedUndo.scope === occurrenceStorageKey("attempt", data) ? savedUndo.exerciseIdentity : null;
        setSelectedExerciseId(data.exercises.some(e => exerciseKey(e) === selected) ? selected : null);
        setTechniqueModal(restoredTechnique);
        setGlobalRestTimer(restoredRest);

        setWeakAreas([]);
      } else {
        // A confirmed source/variant change retires only that slot's old authority caches.
        for (const exercise of data.exercises) {
          const previous = currentWorkout.current?.exercises.find(item => exerciseKey(item) === exerciseKey(exercise));
          if (previous && exerciseAuthorityIdentity(previous) !== exerciseAuthorityIdentity(exercise)) {
            const key = exerciseKey(exercise);
            loadPreviewVersions.current[key] = (loadPreviewVersions.current[key] ?? 0) + 1;
            resetExerciseAuthority(key, exercise, previous.load_intelligence !== undefined);
          }
        }
        const projectionGeneration = captureLoadGeneration();
        // Keep unchanged edited drafts, declared contexts and pending commands.
        setWorkout(data);
        setCompletedSetsByExercise(Object.fromEntries(data.exercises.map(item => [exerciseKey(item), item.completed_sets ?? 0])));
        applyProgressLoad(data.exercises.map(item => ({ exercise_id: item.id,
          exercise_occurrence_id: item.exercise_occurrence_id, load_intelligence: item.load_intelligence })), projectionGeneration);
        setEffectiveSetsByExercise(previous => ({ ...previous, ...Object.fromEntries(
          data.exercises.filter(item => item.customized_receipts).map(item => [exerciseKey(item), item.customized_receipts!]),
        ) }));
      }

      setLiveRecommendationByExercise(Object.fromEntries(data.exercises
        .filter(exercise => exercise.live_recommendation)
        .map(exercise => [exerciseKey(exercise), exercise.live_recommendation as WorkoutLiveRecommendation])));

      // Display-only profile context must not delay authoritative progress or soreness.
      void api.getProfile().then(profile => {
        if (!isCurrent()) return;
        const profileWeakAreas = Array.isArray(profile.weak_areas)
          ? profile.weak_areas.filter((value): value is string => typeof value === "string" && value.trim().length > 0)
          : [];
        setWeakAreas(profileWeakAreas);
      }).catch(() => {
        if (isCurrent()) setWeakAreas([]);
      });

      // Confirmed server state is authoritative; local caches are never receipts.
      const localCompleted: Record<string,number> = Object.fromEntries(data.exercises.map(exercise=>[exerciseKey(exercise),exercise.completed_sets??0]));
      const initialProgressGeneration = captureLoadGeneration();

      // prefer server-side progress when available
      try {
        const { progress, generation } = await getScopedWorkoutProgress(workoutReference(data));
        if (!isCurrent() || currentOccurrence.current !== workoutReference(data)) return null;
        applyProgressLoad(progress.exercises ?? [], generation);
        if ((progress.exercises ?? []).some(item => !isCurrentLoadGeneration(item.exercise_occurrence_id ?? item.exercise_id, generation))) return data;
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
        if(isCurrent() && currentOccurrence.current===workoutReference(data) && data.exercises.every(exercise=>isCurrentLoadGeneration(exerciseKey(exercise),initialProgressGeneration))){
          setCompletedSetsByExercise(localCompleted);
          setWorkoutProgress(null);
        }
      }
      return data;
    } catch (error) {
      if (!isCurrent()) return null;
      if (JSON.stringify(captureLoadGeneration()) !== JSON.stringify(requestGeneration)) {
        setMessage("Workout changed while loading. Reload to verify the current workout. Your saved history is unchanged.");
        return null;
      }
      setWorkout(null);
      currentOccurrence.current = null;
      setOccurrenceVerified(false);
      setSelectedExerciseId(null);
      setTechniqueModal(null);
      setGlobalRestTimer(null);
      setMessage(error instanceof Error && error.message === "No workout scheduled today"
        ? "Rest day — no workout is scheduled for your local date. Check Week for your selected dates."
        : error instanceof ApiError && error.status === 404
        ? "No workout available. Open Week to review your schedule."
        : "Workout could not be loaded. Retry loading your workout. Your saved history is unchanged.");
      return null;
    }
  }, [loadWorkoutSummary, applyProgressLoad, resetSelectedLoadContext, getScopedWorkoutProgress, capturePageRead, isCurrentPageRead, captureLoadGeneration, isCurrentLoadGeneration, resetExerciseAuthority]);

  async function recoverPriorUndo() {
    const pageScope = capturePageRead();
    const attempt = undoRecoveryRef.current;
    if (!attempt || undoInFlight.current) return;
    undoInFlight.current = true; setPriorUndoBusy(true);
    const recoveryKey = undoRecoveryStorageKey();
    try {
      const reply = await api.undoLastSet(attempt.workoutId, attempt.exerciseId, attempt.exerciseOccurrenceId, attempt.command);
      if (!isCurrentPageRead(pageScope)) return;
      const progress = await api.getWorkoutProgress(attempt.workoutId);
      if (!isCurrentPageRead(pageScope) || undoRecoveryStorageKey() !== recoveryKey) return;
      const count = progress.exercises?.find(item => (item.exercise_occurrence_id ?? item.exercise_id) === attempt.exerciseIdentity)?.completed_sets ?? reply.live_recommendation?.completed_sets;
      if (count == null || !Number.isInteger(count) || count < 0) throw new Error("Saved sets unavailable");
      acknowledgeLogCommand(pendingCommandKey(attempt.scope, attempt.exerciseIdentity, "undo"));
      acknowledgeLogCommand(recoveryKey); undoRecoveryRef.current = null; setUndoRecovery(null);
      await loadToday();
    } catch (error) {
      if (!isCurrentPageRead(pageScope)) return;
      if (isDefinitiveUndoRejection(error) && undoRecoveryStorageKey() === recoveryKey) {
        acknowledgeLogCommand(pendingCommandKey(attempt.scope, attempt.exerciseIdentity, "undo"));
        acknowledgeLogCommand(recoveryKey); undoRecoveryRef.current = null; setUndoRecovery(null); setMessage(error.message);
      } else setMessage("Undo not confirmed. Retry the original undo; workout changes remain paused.");
    } finally { if (isCurrentPageRead(pageScope)) { undoInFlight.current = false; setPriorUndoBusy(false); } }
  }

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
    const scope = capturePageRead();
    isBeginWorkoutLoadInProgress.current = true;
    setOccurrenceVerified(false);
    setWorkoutLoading(true);
    setMessage(currentOccurrence.current ? "Refreshing your scheduled workout…" : "Loading your scheduled workout…");
    try {
      // The account's scheduling clock owns occurrence/date routing. A missing
      // weekly report is not authority to block an already scheduled workout.
      const today = await resolveLocalToday();
      if (!isCurrentPageRead(scope)) return;
      const sorenessSkipKey = `hypertrophy_soreness_skip:${today}`;

      const loadedWorkout = await loadToday();
      if (!loadedWorkout || !isCurrentPageRead(scope)) {
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
      if (!isCurrentPageRead(scope)) return;
      if (entriesToday.length > 0) {
        return;
      }
      resetSorenessForm();
      sorenessPromptDate.current = today;
      setShowSorenessModal(true);
    } catch {
      if (isCurrentPageRead(scope)) {
        setWorkout(null);
        currentOccurrence.current = null;
        setOccurrenceVerified(false);
        setSelectedExerciseId(null);
        setMessage("Unable to verify soreness status. Try again.");
      }
    } finally {
      if (isCurrentPageRead(scope)) {
        isBeginWorkoutLoadInProgress.current = false;
        setWorkoutLoading(false);
        setMessage(previous => previous === "Refreshing your scheduled workout…" ? "" : previous);
      }
    }
  }, [loadToday, resolveLocalToday, resetSorenessForm, showSorenessModal, capturePageRead, isCurrentPageRead]);

  useEffect(() => {
    if (health !== "ok" || workout !== null || hasAutoLoadStarted.current) {
      return;
    }
    hasAutoLoadStarted.current = true;
    beginWorkoutLoad();
  }, [health, workout, beginWorkoutLoad, accountGeneration]);

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
    const scope = capturePageRead();
    setSorenessStatus("Saving soreness...");
    try {
      const today = await resolveLocalToday();
      if (!isCurrentPageRead(scope)) return;
      if (restartForChangedSorenessDate(today)) return;
      const sorenessSkipKey = `hypertrophy_soreness_skip:${today}`;
      await api.createSoreness({
        entry_date: today,
        severity_by_muscle: sorenessByMuscle,
        notes: sorenessNotes || undefined,
      });
      if (!isCurrentPageRead(scope)) return;
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
      if (isCurrentPageRead(scope)) setSorenessStatus("Failed to save soreness");
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
    if (undoRecoveryRef.current) return;
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
    if (undoRecoveryRef.current) throw new Error("Confirm the original undo before recording more work.");
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
      ...(exercise.customized?{actual_rir:performed.actual_rir,technique_quality:performed.technique_quality,pain:performed.pain,load_context:{unit:"kg" as const,display_unit:performed.display_unit??"kg",basis:exercise.customized.identity.basis,equipment_key:exercise.customized.identity.equipment_key}}:{}),
      ...(!exercise.customized&&context ? { load_context: {...context, display_unit: performed.display_unit ?? context.display_unit} } : {}),
      ...(offeredDecision && intelligence?.load_context.display_unit === (performed.display_unit ?? context?.display_unit) ? { load_recommendation_id: offeredDecision.id } : {}),
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
      if (feedback.customized_receipts) setEffectiveSetsByExercise(previous=>({...previous,[exerciseId]:feedback.customized_receipts!}));
      if (feedback.load_intelligence !== undefined) updateLoadIntelligence(exerciseId, feedback.load_intelligence ?? null);
      setLiveRecommendationByExercise((prev) => ({
        ...prev,
        [exerciseId]: feedback.live_recommendation,
      }));

      const restCycle = exercise.customized?.rest_seconds.high ?? parseRestToSeconds(exercise.rest) ?? 90;
      setGlobalRestTimer({
        exerciseId,
        exerciseName: resolveExerciseName(exercise, swapIndexByExercise),
        secondsLeft: restCycle,
        restCycle,
        deadline: Date.now() + restCycle * 1000,
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
          unit: performed.display_unit ?? "lb",
          instruction: prescribedTechnique,
          authored: Boolean(exercise.authored_prescription),
          bodyweight: isBodyweightAuthored(exercise),
        });
      }

      // refresh from server-side progress to keep client in sync
      void (async () => { try {
        const { progress, generation } = await getScopedWorkoutProgress(workoutReference(workout));
        if (currentOccurrence.current !== workoutReference(workout)) return;
        applyProgressLoad(progress.exercises ?? [], generation);
        if ((progress.exercises ?? []).some(item => !isCurrentLoadGeneration(item.exercise_occurrence_id ?? item.exercise_id, generation))) return;
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
      } })();

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
    if (undoRecoveryRef.current) throw new Error("Confirm the original undo before recording technique work.");
    const exercise = (workout?.exercises ?? []).find((entry) => exerciseKey(entry) === state.exerciseId);
    if (!exercise) throw new Error("Exercise occurrence is unavailable");
    const commandKey = pendingCommandKey(workout ? occurrenceStorageKey("attempt", workout) : state.workoutId, state.exerciseId, `${state.kind}:${state.parentSetIndex}:${ordinal}`);
    const payload = retainLogPayload(commandKey, {
      command_id: getLogCommand(commandKey),
      primary_exercise_id: exercise.primary_exercise_id,
      exercise_id: exercise.id,
      exercise_occurrence_id: exercise.exercise_occurrence_id,
      set_index: state.parentSetIndex,
      reps: performed.reps,
      weight: canonicalLoad(performed.weight,state.unit),
      rpe: null,
      set_kind: state.kind,
      parent_set_index: state.parentSetIndex,
      technique: { type: state.kind, ordinal },
    });
    try {const feedback=await api.logSet(state.workoutId,payload);
      if(currentOccurrence.current===state.workoutId && feedback.load_intelligence!==undefined)updateLoadIntelligence(state.exerciseId,feedback.load_intelligence??null);
    } catch(error){if(error instanceof ApiError&&error.status===422)acknowledgeLogCommand(commandKey);throw error;}
    acknowledgeLogCommand(commandKey);
  }

  // Invoked by the technique entry's event handler, never during rendering.
  const handleTechniqueLog = async (performed: {reps:number;weight:number}, ordinal:number) => {
    if (techniqueModal) await handleLogTechniqueSubSet(techniqueModal, performed, ordinal);
  };

  async function handleUndoLastSet(exercise: WorkoutExercise): Promise<number | false> {
    if (!workout) return false;
    const pageScope = capturePageRead();
    const loadIntelligence = intelligenceFor(exercise);
    if (undoInFlight.current) return false;
    undoInFlight.current = true;
    const scope = occurrenceStorageKey("attempt", workout);
    const recoveryKey = undoRecoveryStorageKey();
    const commandKey = pendingCommandKey(scope, exerciseKey(exercise), "undo");
    const attempt = retainLogPayload<UndoAttempt>(recoveryKey, undoRecovery ?? {
      scope, workoutId: workoutReference(workout), exerciseId: exercise.id, exerciseIdentity: exerciseKey(exercise),
      exerciseOccurrenceId: exercise.exercise_occurrence_id, command: getLogCommand(commandKey),
    });
    undoRecoveryRef.current = attempt; setUndoRecovery(attempt);
    try {
      if (attempt.scope !== scope || attempt.exerciseIdentity !== exerciseKey(exercise)) return false;
      const result = await api.undoLastSet(attempt.workoutId, attempt.exerciseId, attempt.exerciseOccurrenceId, attempt.command);
      if (!isCurrentPageRead(pageScope) || undoRecoveryStorageKey() !== recoveryKey || currentOccurrence.current !== attempt.workoutId) return false;
      advanceLoadGeneration(exerciseKey(exercise));
      setGlobalRestTimer(timer => timer?.exerciseId === exerciseKey(exercise) ? null : timer);
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
      if (!isCurrentPageRead(pageScope) || currentOccurrence.current !== workoutReference(workout)) return false;
      if (todayResult.status === "fulfilled" && workoutReference(todayResult.value) === workoutReference(workout)) {
        setWorkout(todayResult.value);
        const receipts=todayResult.value.exercises.find(e=>exerciseKey(e)===exerciseKey(exercise))?.customized_receipts;
        if(receipts)setEffectiveSetsByExercise(previous=>({...previous,[exerciseKey(exercise)]:receipts}));
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
      const progressCount = progressResult.status === "fulfilled" ? progressResult.value.progress.exercises?.find(item => (item.exercise_occurrence_id ?? item.exercise_id) === attempt.exerciseIdentity)?.completed_sets : undefined;
      const todayCount = todayResult.status === "fulfilled" && workoutReference(todayResult.value) === attempt.workoutId ? todayResult.value.exercises.find(item => exerciseKey(item) === attempt.exerciseIdentity)?.completed_sets : undefined;
      const confirmedCount = progressCount ?? todayCount ?? result.live_recommendation?.completed_sets ?? (result.load_intelligence ? result.load_intelligence.effective_sets.filter(item => item.parent_set_index == null && item.set_kind !== "warmup").length : undefined);
      if (confirmedCount == null || !Number.isInteger(confirmedCount) || confirmedCount < 0) {
        setMessage("Undo confirmed, but saved sets could not be refreshed. Retry the original undo to reconcile.");
        return false;
      }
      setCompletedSetsByExercise(previous => ({ ...previous, [attempt.exerciseIdentity]: confirmedCount }));
      // Keep the original command until both its reply and the resulting
      // count are confirmed. Reload never turns an uncertain undo into a
      // new request against the latest set.
      acknowledgeLogCommand(commandKey); acknowledgeLogCommand(recoveryKey);
      undoRecoveryRef.current = null; setUndoRecovery(null); setMessage("");
      return confirmedCount;
    } catch (error) {
      if (!isCurrentPageRead(pageScope)) return false;
      if (isDefinitiveUndoRejection(error) && undoRecoveryStorageKey() === recoveryKey) {
        acknowledgeLogCommand(commandKey); acknowledgeLogCommand(recoveryKey);
        undoRecoveryRef.current = null; setUndoRecovery(null); setMessage(error.message);
        throw error;
      }
      setMessage("Undo was not confirmed. Retry to confirm the same action.");
      return false;
    } finally { if (isCurrentPageRead(pageScope)) undoInFlight.current = false; }
  }

  const swapTarget = (workout?.exercises ?? []).find((exercise) => exerciseKey(exercise) === swapTargetExerciseId) ?? null;
  const swapTargetCurrentIndex = swapTarget ? (swapIndexByExercise[exerciseKey(swapTarget)] ?? 0) : 0;
  const activeProgramId = workout ? extractProgramId(workout.session_id) : null;
  const executionVisible = occurrenceVerified && Boolean(selectedExerciseId);

  const todayDate = localToday
    ? `${formatCalendarDate(localToday.date)} · ${localToday.timezone}`
    : `${new Date().toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" })} · browser local date`;

  return (
    <div className={executionVisible ? "atlas-page" : "space-y-4 pb-8"}>
      <div className={executionVisible ? "hidden" : "flex flex-wrap items-baseline justify-between gap-2"}>
        <h1 className="ui-title-page">Today</h1>
        {!undoRecovery ? <Link className="inline-flex min-h-11 items-center underline" href={workout?.customized?.proposal_id?`/customize?proposal=${encodeURIComponent(workout.customized.proposal_id)}`:"/customize"}>Manage Customized dates or replace program</Link> : null}
        <p className="ui-meta text-zinc-400">{todayDate}</p>
      </div>
      <div className={executionVisible ? "hidden" : "main-card main-card--module main-card--accent spacing-grid spacing-grid--tight"}>
        <Button className="min-h-[44px] w-full" onClick={beginWorkoutLoad} disabled={workoutLoading} aria-busy={workoutLoading}>
          <span className="inline-flex items-center gap-2">
            <UiIcon name="workout" className="ui-icon--action" />
            {workout ? "Reload" : "Load today's workout"}
          </span>
        </Button>
      </div>

      {message && !executionVisible ? (
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

      {undoRecovery && (!workout || undoRecovery.scope !== occurrenceStorageKey("attempt", workout) || !workout.exercises.some(item => exerciseKey(item) === undoRecovery.exerciseIdentity)) ? <div role="alert"><p>An undo for a previous workout is unconfirmed. This workout is read-only until the original undo is reconciled.</p><Button disabled={priorUndoBusy} onClick={recoverPriorUndo}>Retry original undo</Button></div> : null}
      {workout && occurrenceVerified ? (
        <div className={selectedExerciseId ? "hidden" : "space-y-3"}>
          <p className="ui-body-sm text-zinc-200">
            {workout.title} · {workoutProgress?.completed ?? 0}/{workoutProgress?.planned ?? 0} sets
          </p>

          <ul className="space-y-1.5" aria-label="Exercise list">
            {(workout.exercises ?? []).map((exercise) => {
              const selectedName = resolveExerciseName(exercise, swapIndexByExercise);
              const displayName = resolveDisplayExerciseName(exercise, selectedName, weakAreas);
              const completed = completedSetsByExercise[exerciseKey(exercise)] ?? 0;
              const done = completed >= exercise.sets;
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
                    disabled={Boolean(undoRecovery)}
                    onClick={() => { if (!undoRecoveryRef.current) setSelectedExerciseId(exerciseKey(exercise)); }}
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
                      <span>{intelligence !== undefined ? (ownedRowLoad === undefined ? "Record actual load" : `${displayLoad(ownedRowLoad,preferences.weight_unit)} ${preferences.weight_unit}`)
                        : exercise.customized ? (exercise.load_semantics === "bodyweight" ? "Bodyweight" : "Record actual load") : isBodyweightAuthored(exercise) ? "Bodyweight" : exercise.performed_variant ? "Record actual load" : "Record actual load"}</span>
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

      {workout && occurrenceVerified && selectedExerciseId ? (() => {
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
        const loadIntelligence = intelligenceFor(exercise);
        const effectiveSets = effectiveSetsByExercise[exerciseKey(exercise)] ?? exercise.customized_receipts ?? loadIntelligence?.effective_sets ?? [];
        const loadContext: LoadContext = {...(loadContextByExercise[exerciseKey(exercise)] ?? loadIntelligence?.load_context ?? (exercise.customized?{unit:"kg",display_unit:"kg",basis:exercise.customized.identity.basis,equipment_key:exercise.customized.identity.equipment_key}:null) ?? { unit: "kg", display_unit: "lb", basis: "unknown" } as LoadContext), display_unit: preferences.weight_unit};
        const canUndo = completed > 0 || effectiveSets.length > 0 || undoRecovery?.exerciseIdentity === exerciseKey(exercise);

        return (
          <ExerciseDetailOverlay
            key={`${exerciseKey(exercise)}/${exercise.performed_variant?.option_id ?? "source"}`}
            exercise={exercise.customized?{...exercise,customized_load_decision:(recommendation?.decision_trace?.load_decision as typeof exercise.customized_load_decision)??exercise.customized_load_decision}:exercise}
            navigation={workout.exercises.map(item=>({id:exerciseKey(item),name:resolveDisplayExerciseName(item,resolveExerciseName(item,swapIndexByExercise),weakAreas),completed:completedSetsByExercise[exerciseKey(item)]??0,total:item.sets}))}
            onSelectExercise={id => { if (!undoRecoveryRef.current) setSelectedExerciseId(id); }}
            undoRecovery={Boolean(undoRecovery)}
            selectedName={displayName}
            guideHref={guideHref}
            completed={completed}
            loadIntelligence={loadIntelligence}
            effectiveSets={effectiveSets}
            loadContext={loadContext}
            onLoadContextChange={context => {
              if (undoRecoveryRef.current) return;
              const key = exerciseKey(exercise);
              loadPreviewVersions.current[key] = (loadPreviewVersions.current[key] ?? 0) + 1;
              selectLoadContext(key, context);
              setLoadContextByExercise(previous => ({ ...previous, [exerciseKey(exercise)]: context }));
              setLoadIntelligenceByExercise(previous => ({ ...previous, [exerciseKey(exercise)]: null }));
            }}
            onSaveCalibration={async (command, isRetry = false) => {
              if (undoRecoveryRef.current) throw new Error("Resolve the pending undo before saving a benchmark");
              const key = exerciseKey(exercise);
              const version = (loadPreviewVersions.current[key] ?? 0) + 1;
              loadPreviewVersions.current[key] = version;
              // Retry the original write without reselecting a setup the user has since changed.
              if (!isRetry) {
                selectLoadContext(key, command.load_context);
                setLoadContextByExercise(previous => ({ ...previous, [key]: command.load_context }));
                setLoadIntelligenceByExercise(previous => ({ ...previous, [key]: null }));
              }
              const generation = captureLoadGeneration();
              const result = await api.saveInitialCalibration(workoutReference(workout), command);
              if (currentOccurrence.current !== workoutReference(workout) || loadPreviewVersions.current[key] !== version || !isCurrentLoadGeneration(key, generation)) return;
              updateLoadIntelligence(key, result);
            }}
            onPreviewLoad={async context => {
              if (!exercise.exercise_occurrence_id) throw new Error("Exercise occurrence unavailable");
              const key = exerciseKey(exercise);
              const version = (loadPreviewVersions.current[key] ?? 0) + 1;
              loadPreviewVersions.current[key] = version;
              const generation = captureLoadGeneration();
              const result = await api.previewLoadGuidance(workoutReference(workout), exercise.exercise_occurrence_id, context);
              if (currentOccurrence.current !== workoutReference(workout) || loadPreviewVersions.current[key] !== version || !isCurrentLoadGeneration(key, generation)) return;
              updateLoadIntelligence(exerciseKey(exercise), result);
            }}
            overrideReason={loadOverrideByExercise[exerciseKey(exercise)] ?? ""}
            onOverrideReason={reason => setLoadOverrideByExercise(previous => ({ ...previous, [exerciseKey(exercise)]: reason }))}
            warmupCommandScope={occurrenceStorageKey("attempt", workout)}
            onWarmupComplete={async (ordinal, performed) => {
              if (undoRecoveryRef.current) throw new Error("Confirm the original undo before recording warm-ups.");
              const key = exerciseKey(exercise);
              const commandKey = pendingCommandKey(occurrenceStorageKey("attempt", workout), key, `warmup:${ordinal}`);
              const payload = retainLogPayload(commandKey, { exercise_id: exercise.id,
                primary_exercise_id: exercise.primary_exercise_id ?? null, exercise_occurrence_id: exercise.exercise_occurrence_id,
                command_id: getLogCommand(commandKey), set_index: ordinal, reps: performed.reps, weight: performed.weight, rpe: performed.rpe,
                set_kind: "warmup", parent_set_index: null, technique: null, load_context: loadContext,
                ...(loadIntelligence?.warmup_guidance?.id && loadIntelligence.load_context.display_unit === loadContext.display_unit ? { load_recommendation_id: loadIntelligence.warmup_guidance.id } : {}) });
              try {
                const feedback = await api.logSet(workoutReference(workout), payload);
                acknowledgeLogCommand(commandKey);
                if (currentOccurrence.current !== workoutReference(workout)) return;
                advanceLoadGeneration(key);
                updateLoadIntelligence(key, feedback.load_intelligence ?? null);
                setMessage("");
                try { const { progress, generation } = await getScopedWorkoutProgress(workoutReference(workout));
                  if (currentOccurrence.current === workoutReference(workout)) applyProgressLoad(progress.exercises ?? [], generation);
                } catch { /* confirmed warm-up receipt owns current evidence */ }
              } catch (error) {
                if (error instanceof ApiError && (error.status === 422 || (error.status === 409 && error.code === "stale_load_recommendation"))) {
                  acknowledgeLogCommand(commandKey);
                  if (error.status === 409 && exercise.exercise_occurrence_id) {
                    try { const refreshed = await api.previewLoadGuidance(workoutReference(workout), exercise.exercise_occurrence_id, loadContext);
                      if (currentOccurrence.current === workoutReference(workout)) updateLoadIntelligence(key, refreshed);
                    } catch { /* the draft remains reviewable without new advice */ }
                  }
                }
                throw error;
              }
            }}
            onCorrectSet={async (receipt, values) => {
              if (undoRecoveryRef.current) throw new Error("Confirm the original undo before correcting sets.");
              const commandKey = pendingCommandKey(occurrenceStorageKey("attempt", workout), exerciseKey(exercise), `correct:${receipt.id}`);
              const payload = retainLogPayload(commandKey, { ...values, command_id: getLogCommand(commandKey) });
              let result;
              try { result = await api.correctSet(receipt.id, payload); }
              catch (error) {
                if (isObsoleteCorrectionTarget(error)) {
                  acknowledgeLogCommand(commandKey);
                  if (currentOccurrence.current !== workoutReference(workout)) throw error;
                  const key = exerciseKey(exercise);
                  const workoutId = workoutReference(workout);
                  advanceLoadGeneration(key);
                  const generation = captureLoadGeneration();
                  const knownReceipts = effectiveSetsByExercise[key] ?? exercise.customized_receipts ?? intelligenceFor(exercise)?.effective_sets ?? [];
                  setEffectiveSetsByExercise(previous => ({ ...previous, [key]: (previous[key] ?? knownReceipts).filter(item => item.id !== receipt.id) }));
                  setLoadIntelligenceByExercise(previous => ({ ...previous, [key]: null }));
                  setLiveRecommendationByExercise(previous => { const next = { ...previous }; delete next[key]; return next; });
                  setSetFeedbackByExercise(previous => { const next = { ...previous }; delete next[key]; return next; });
                  setWorkoutSummary(null);
                  const [todayResult, progressResult] = await Promise.allSettled([api.getTodayWorkout(), getScopedWorkoutProgress(workoutId)]);
                  if (currentOccurrence.current !== workoutId || !isCurrentLoadGeneration(key, generation)) throw error;
                  if (todayResult.status === "fulfilled" && workoutReference(todayResult.value) === workoutId) {
                    const refreshed = todayResult.value.exercises.find(item => exerciseKey(item) === key);
                    if (refreshed) {
                      setWorkout(previous => previous ? { ...previous, exercises: previous.exercises.map(item => exerciseKey(item) === key ? refreshed : item) } : previous);
                      setEffectiveSetsByExercise(previous => ({ ...previous, [key]: refreshed.customized_receipts ?? refreshed.load_intelligence?.effective_sets ?? [] }));
                      if (refreshed.load_intelligence !== undefined) updateLoadIntelligence(key, refreshed.load_intelligence);
                      if (refreshed.completed_sets != null) setCompletedSetsByExercise(previous => ({ ...previous, [key]: refreshed.completed_sets! }));
                      if (refreshed.live_recommendation) setLiveRecommendationByExercise(previous => ({ ...previous, [key]: refreshed.live_recommendation! }));
                    }
                  }
                  if (progressResult.status === "fulfilled") {
                    const { progress, generation: progressGeneration } = progressResult.value;
                    applyProgressLoad(progress.exercises ?? [], progressGeneration);
                    const count = progress.exercises?.find(item => (item.exercise_occurrence_id ?? item.exercise_id) === key)?.completed_sets;
                    if (count != null) setCompletedSetsByExercise(previous => ({ ...previous, [key]: count }));
                    setWorkoutProgress({ completed: Number(progress.completed_total) || 0, planned: Number(progress.planned_total) || 0, percent: Number(progress.percent_complete) || 0 });
                  }
                } else if (error instanceof ApiError && error.status === 422) acknowledgeLogCommand(commandKey);
                throw error;
              }
              acknowledgeLogCommand(commandKey);
              if (currentOccurrence.current !== workoutReference(workout)) return;
              advanceLoadGeneration(exerciseKey(exercise));
              if (result.customized_receipts) setEffectiveSetsByExercise(previous=>({...previous,[exerciseKey(exercise)]:result.customized_receipts!}));
              updateLoadIntelligence(exerciseKey(exercise), result.load_intelligence ?? null);
              setSetFeedbackByExercise(previous => { const next = { ...previous }; delete next[exerciseKey(exercise)]; return next; });
              setLiveRecommendationByExercise(previous => { const next = { ...previous }; delete next[exerciseKey(exercise)]; if(exercise.customized && result.live_recommendation) next[exerciseKey(exercise)] = result.live_recommendation; return next; });
              setWorkoutSummary(null);
              try { const { progress, generation } = await getScopedWorkoutProgress(workoutReference(workout));
                if (currentOccurrence.current === workoutReference(workout)) applyProgressLoad(progress.exercises ?? [], generation);
              } catch { /* confirmed receipt already invalidated old advice */ }
            }}
            techniquePanelState={techniqueModal && techniqueModal.exerciseId === exerciseKey(exercise) ? techniqueModal : null}
            onCloseTechniquePanel={() => setTechniqueModal(null)}
            onLogTechniquePanel={handleTechniqueLog}
            mediaUrl={mediaUrl}
            weakPointInstruction={weakPointInstruction}
            liveGuidance={!loadIntelligence && !exercise.customized ? resolveGuidanceText(recommendation?.guidance_rationale ?? feedback?.guidance_rationale, recommendation?.guidance ?? feedback?.guidance) : ""}
            onUndoLastSet={canUndo ? () => handleUndoLastSet(exercise) : undefined}
            onAuthoredDecision={async (decision) => {
              if (undoRecoveryRef.current) throw new Error("Confirm the original undo before changing this exercise.");
              if (!exercise.exercise_occurrence_id) throw new Error("Occurrence unavailable");
              const input = { ...decision, exercise_id: exercise.id, exercise_occurrence_id: exercise.exercise_occurrence_id,
                expected_revision: exercise.authored_constraint?.revision ?? 0, expected_source_lineage: exercise.source_lineage ?? {} };
              const commandKey = pendingCommandKey(occurrenceStorageKey("attempt", workout), exerciseKey(exercise), JSON.stringify(input));
              const result = await api.decideAuthoredSubstitution(workoutReference(workout), { ...input, command_id: getLogCommand(commandKey) });
              acknowledgeLogCommand(commandKey);
              if (currentOccurrence.current !== workoutReference(workout)) return;
              const key = exerciseKey(exercise);
              loadPreviewVersions.current[key] = (loadPreviewVersions.current[key] ?? 0) + 1;
              resetExerciseAuthority(key, result.exercise, loadIntelligence !== undefined);
              setWorkout(previous => previous ? { ...previous, exercises: previous.exercises.map(item =>
                exerciseKey(item) === exerciseKey(exercise) ? result.exercise : item) } : previous);
              setWorkoutSummary(null);
            }}
            onClose={() => { if (!undoRecoveryRef.current) setSelectedExerciseId(null); }}
            onSwapTarget={() => setSwapTargetExerciseId(exerciseKey(exercise))}
            onSetComplete={handleSetComplete}
            globalRestTimer={globalRestTimer}
            onClearGlobalRestTimer={() => setGlobalRestTimer(null)}
          />
        );
      })() : null}

      {/* Global rest bar when overlay is closed (timer persists) */}
      {occurrenceVerified && globalRestTimer != null && selectedExerciseId !== globalRestTimer.exerciseId ? (
        <div className="ux-rest-bar">
          <span className="text-sm font-medium tabular-nums text-zinc-200">
            Rest: {Math.floor(globalRestTimer.secondsLeft / 60)}:{(globalRestTimer.secondsLeft % 60).toString().padStart(2, "0")} — {globalRestTimer.exerciseName}
          </span>
          <div className="flex gap-2">
            <Button
              type="button"
              variant="secondary"
              className="min-h-[36px] px-3 text-xs"
              disabled={Boolean(undoRecovery)}
              onClick={() => { if (!undoRecoveryRef.current) setSelectedExerciseId(globalRestTimer.exerciseId); }}
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

      {occurrenceVerified && swapTarget ? (
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
                  const scope = capturePageRead();
                  try {
                    const today = await resolveLocalToday();
                    if (!isCurrentPageRead(scope)) return;
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
                    if (isCurrentPageRead(scope)) setSorenessStatus("Unable to verify the local date. Try again.");
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
