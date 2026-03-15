"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { UiIcon } from "@/components/ui/icons";
import ExerciseControlModule from "@/components/exercise-control";
import {
  api,
  type SorenessSeverity,
  type WorkoutExercise,
  type WorkoutLiveRecommendation,
  type WorkoutSession,
  type WorkoutSetFeedback,
  type WorkoutSummary,
} from "@/lib/api";
import { resolveGuidanceText } from "@/lib/today-guidance";
import { kgToLbs, lbsToKg } from "@/lib/weight";

type SwapState = Record<string, number>;
type NotesState = Record<string, boolean>;
const SWAP_STORAGE_PREFIX = "hypertrophy_swap_selection";
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

function formatAuthoredBlockLabel(workout: WorkoutSession | null | undefined): string | null {
  const authoredWeekIndex =
    typeof workout?.mesocycle?.authored_week_index === "number" ? workout.mesocycle.authored_week_index : null;
  const authoredWeekRole = formatRoleLabel(workout?.mesocycle?.authored_week_role);
  if (authoredWeekIndex === null && !authoredWeekRole) {
    return null;
  }
  return `Authored block: ${authoredWeekIndex !== null ? `Week ${authoredWeekIndex}` : "Current"} · ${authoredWeekRole ?? "Unspecified"}`;
}

function countSlotRole(exercises: WorkoutExercise[], slotRole: string): number {
  return exercises.filter((exercise) => exercise.slot_role === slotRole).length;
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
  const substitutions = exercise.substitution_candidates ?? [];
  const selectedIndex = swapIndexByExercise[exercise.id] ?? 0;
  if (selectedIndex === 0) {
    return exercise.name;
  }
  return substitutions[selectedIndex - 1] ?? exercise.name;
}

function resolveExerciseMediaUrl(exercise: WorkoutExercise): string | null {
  const preferred = exercise.video?.youtube_url ?? exercise.video_url ?? exercise.demo_url;
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

function resolveHealthStatus(health: string): "green" | "yellow" | "red" {
  if (health === "ok") {
    return "green";
  }
  if (health === "loading") {
    return "yellow";
  }
  return "red";
}

function SessionIntentCard({
  workout,
  workoutProgress,
}: Readonly<{
  workout: WorkoutSession;
  workoutProgress: { completed: number; planned: number; percent: number } | null;
}>) {
  const leadExercise = workout.exercises[0];
  const authoredDayLabel = formatRoleLabel(workout.day_role);
  const authoredBlockLabel = formatAuthoredBlockLabel(workout);
  const weakPointSlotCount = countSlotRole(workout.exercises, "weak_point");
  const remainingSets = workoutProgress ? Math.max(0, workoutProgress.planned - workoutProgress.completed) : null;
  let intentLabel = "Primary hypertrophy exposure";
  if (authoredDayLabel) {
    intentLabel = authoredDayLabel;
  } else if (workout.deload?.active) {
    intentLabel = "Deload execution";
  } else if (workout.resume) {
    intentLabel = "Resume and finish";
  }
  const pacingLine = workoutProgress
    ? `Progress is ${workoutProgress.percent}%. Finish the remaining ${remainingSets ?? 0} planned sets without drifting off target.`
    : `Open with ${leadExercise?.sets ?? 0} sets on the lead slot, then roll through ${workout.exercises.length} total exercises.`;
  let cautionLine = "Stay in the planned rep range before adding load or extra fatigue.";
  if (workout.deload?.active) {
    cautionLine = `Keep effort controlled and respect the ${workout.deload.load_reduction_pct}% load trim.`;
  } else if (workout.resume) {
    cautionLine = "Resume from the saved state instead of repeating completed work.";
  }

  return (
    <div className="main-card main-card--module main-card--accent spacing-grid spacing-grid--tight">
      <div className="telemetry-header">
        <p className="telemetry-kicker">Session Intent</p>
        <p className="telemetry-status">
          <span className="status-dot status-dot--green" /> {intentLabel}
        </p>
      </div>
      {leadExercise ? (
        <p className="text-sm text-zinc-100">
          Lead exercise: {leadExercise.name} for {leadExercise.sets} sets of {leadExercise.rep_range[0]}-{leadExercise.rep_range[1]} reps @ {kgToLbs(leadExercise.recommended_working_weight)} lbs.
        </p>
      ) : null}
      {authoredDayLabel ? <p className="telemetry-meta">Authored day: {authoredDayLabel}</p> : null}
      {authoredBlockLabel ? <p className="telemetry-meta">{authoredBlockLabel}</p> : null}
      {weakPointSlotCount > 0 ? <p className="telemetry-meta">Weak-point slots planned: {weakPointSlotCount}</p> : null}
      <p className="telemetry-meta">{pacingLine}</p>
      <p className="text-xs text-zinc-200">{cautionLine}</p>
    </div>
  );
}

function BetweenSetCoachCard({
  workout,
  completedSetsByExercise,
  liveRecommendationByExercise,
  setFeedbackByExercise,
  swapIndexByExercise,
}: Readonly<{
  workout: WorkoutSession;
  completedSetsByExercise: Record<string, number>;
  liveRecommendationByExercise: Record<string, WorkoutLiveRecommendation>;
  setFeedbackByExercise: Record<string, WorkoutSetFeedback>;
  swapIndexByExercise: SwapState;
}>) {
  const activeExercise = workout.exercises.find((exercise) => (completedSetsByExercise[exercise.id] ?? 0) < exercise.sets) ?? workout.exercises[0];
  if (!activeExercise) {
    return null;
  }

  const selectedName = resolveExerciseName(activeExercise, swapIndexByExercise);
  const completed = completedSetsByExercise[activeExercise.id] ?? 0;
  const recommendation = liveRecommendationByExercise[activeExercise.id] ?? null;
  const feedback = setFeedbackByExercise[activeExercise.id] ?? null;
  const swapActive = selectedName !== activeExercise.name;
  let coachGuidance = `Do ${activeExercise.rep_range[0]}-${activeExercise.rep_range[1]} reps @ ${kgToLbs(activeExercise.recommended_working_weight)} lbs this set.`;
  if (recommendation) {
    coachGuidance = resolveGuidanceText(recommendation.guidance_rationale, recommendation.guidance);
  } else if (feedback) {
    coachGuidance = resolveGuidanceText(feedback.guidance_rationale, feedback.guidance);
  }

  return (
    <div className="main-card main-card--shell spacing-grid spacing-grid--tight">
      <div className="telemetry-header">
        <p className="telemetry-kicker">Between-Set Coach</p>
        <p className="telemetry-meta">Live lane: {selectedName}</p>
      </div>
      <p className="text-sm text-zinc-100">{selectedName}: {completed}/{activeExercise.sets} sets complete.</p>
      <p className="text-xs text-zinc-200">
        {recommendation
          ? `Next set target: ${recommendation.recommended_reps_min}-${recommendation.recommended_reps_max} reps @ ${kgToLbs(recommendation.recommended_weight)} lbs.`
          : `Start with ${activeExercise.rep_range[0]}-${activeExercise.rep_range[1]} reps @ ${kgToLbs(activeExercise.recommended_working_weight)} lbs.`}
      </p>
      <p className="telemetry-meta">{coachGuidance}</p>
      {swapActive ? <p className="telemetry-meta">Equipment swap active for this slot.</p> : null}
    </div>
  );
}

function WorkoutSummaryCard({ summary }: Readonly<{ summary: WorkoutSummary | null }>) {
  if (!summary) {
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
        {summary.exercises.map((item) => (
          <div key={item.exercise_id} className="rounded-md border border-zinc-800 bg-zinc-900/40 p-2 text-xs text-zinc-300">
            <p className="font-semibold text-zinc-100">{item.name}</p>
            <p>
              Planned: {item.planned_sets} sets · {item.planned_reps_min}-{item.planned_reps_max} reps @ {kgToLbs(item.planned_weight)} lbs
            </p>
            <p>
              Performed: {item.performed_sets} sets · avg {item.average_performed_reps} reps @ {kgToLbs(item.average_performed_weight)} lbs
            </p>
            <p>
              Next: {kgToLbs(item.next_working_weight)} lbs
            </p>
            <p>{resolveGuidanceText(item.guidance_rationale, item.guidance)}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function ExerciseExecutionDetails({ exercise }: Readonly<{ exercise: WorkoutExercise }>) {
  const substitutions = resolveAuthoredSubstitutions(exercise);
  const trackingLoads = resolveTrackingLoads(exercise);
  const mediaUrl = resolveExerciseMediaUrl(exercise);
  const hasPrescription = Boolean(exercise.warm_up_sets || exercise.working_sets || exercise.reps);

  return (
    <div className="rounded-md border border-zinc-800 bg-zinc-900/40 p-2 text-xs text-zinc-300">
      {hasPrescription ? (
        <p>
          Authored prescription: {exercise.warm_up_sets ?? "0"} warm-up sets · {exercise.working_sets ?? String(exercise.sets)} working sets · {exercise.reps ?? `${exercise.rep_range[0]}-${exercise.rep_range[1]}`}
        </p>
      ) : null}
      <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1">
        {exercise.early_set_rpe ? <span>Early-set RPE: {exercise.early_set_rpe}</span> : null}
        {exercise.last_set_rpe ? <span>Last-set RPE: {exercise.last_set_rpe}</span> : null}
        {exercise.last_set_intensity_technique ? <span>Technique: {exercise.last_set_intensity_technique}</span> : null}
        {exercise.rest ? <span>Rest: {exercise.rest}</span> : null}
      </div>
      {trackingLoads.length > 0 ? <p className="mt-1">Tracking loads: {trackingLoads.join(" / ")}</p> : null}
      {substitutions.length > 0 ? <p className="mt-1">Authored substitutions: {substitutions.join(" / ")}</p> : null}
      {mediaUrl ? (
        <a
          className="mt-1 inline-flex text-zinc-100 underline decoration-zinc-500 underline-offset-2"
          href={mediaUrl}
          rel="noreferrer"
          target="_blank"
        >
          Demo link
        </a>
      ) : null}
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
  const [sorenessByMuscle, setSorenessByMuscle] = useState<Record<string, SorenessSeverity>>(createInitialSorenessState());
  const [completedSetsByExercise, setCompletedSetsByExercise] = useState<Record<string, number>>({});
  const [workoutProgress, setWorkoutProgress] = useState<{ completed: number; planned: number; percent: number } | null>(null);
  const [setFeedbackByExercise, setSetFeedbackByExercise] = useState<Record<string, WorkoutSetFeedback>>({});
  const [liveRecommendationByExercise, setLiveRecommendationByExercise] = useState<Record<string, WorkoutLiveRecommendation>>({});
  const [workoutSummary, setWorkoutSummary] = useState<WorkoutSummary | null>(null);
  const [recoveringMissingWorkout, setRecoveringMissingWorkout] = useState(false);
  const [selectedExerciseId, setSelectedExerciseId] = useState<string | null>(null);
  const hasAutoLoadStarted = useRef(false);
  const isBeginWorkoutLoadInProgress = useRef(false);

  async function loadWorkoutSummary(workoutId: string) {
    try {
      const summary = await api.getWorkoutSummary(workoutId);
      setWorkoutSummary(summary);
    } catch {
      setWorkoutSummary(null);
    }
  }

  useEffect(() => {
    api.health()
      .then((data) => setHealth(data.status))
      .catch(() => setHealth("offline"));
  }, []);

  useEffect(() => {
    if (health !== "ok" || workout !== null || hasAutoLoadStarted.current) {
      return;
    }
    hasAutoLoadStarted.current = true;
    beginWorkoutLoad();
  }, [health, workout]);

  async function loadToday() {
    try {
      const data = await api.getTodayWorkout();
      setWorkout(data);
      setMessage("");
      setNotesOpenByExercise({});
      setWorkoutSummary(null);
      setSetFeedbackByExercise({});

      const initialRecommendations = Object.fromEntries(
        (data.exercises ?? [])
          .filter((exercise) => Boolean(exercise.live_recommendation))
          .map((exercise) => [exercise.id, exercise.live_recommendation as WorkoutLiveRecommendation]),
      ) as Record<string, WorkoutLiveRecommendation>;
      setLiveRecommendationByExercise(initialRecommendations);

      const storageKey = `${SWAP_STORAGE_PREFIX}:${data.session_id}`;
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
      // restore completed sets for this session if present
      let localCompleted: Record<string, number> = {};
      try {
        const completedKey = `hypertrophy_completed_sets:${data.session_id}`;
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
        const progress = await api.getWorkoutProgress(data.session_id);
        const serverCompleted = Object.fromEntries(
          (progress.exercises ?? []).map((item) => [item.exercise_id, Number(item.completed_sets) || 0]),
        ) as Record<string, number>;
        const merged = Object.keys(serverCompleted).length > 0 ? serverCompleted : localCompleted;
        setCompletedSetsByExercise(merged);
        setWorkoutProgress({
          completed: Number(progress.completed_total) || 0,
          planned: Number(progress.planned_total) || 0,
          percent: Number(progress.percent_complete) || 0,
        });
        const completedKey = `hypertrophy_completed_sets:${data.session_id}`;
        localStorage.setItem(completedKey, JSON.stringify(merged));
        if ((Number(progress.percent_complete) || 0) >= 100) {
          await loadWorkoutSummary(data.session_id);
        }
      } catch {
        setCompletedSetsByExercise(localCompleted);
        setWorkoutProgress(null);
      }
    } catch {
      setWorkout(null);
      setMessage("No workout available. Generate week plan first.");
    }
  }

  async function recoverMissingWorkout() {
    setRecoveringMissingWorkout(true);
    setMessage("Generating canonical week...");
    try {
      await api.generateWeek(null);
      await loadToday();
    } catch {
      setMessage("Could not generate a week yet. Try again from Week or Onboarding.");
    } finally {
      setRecoveringMissingWorkout(false);
    }
  }

  function resetSorenessForm() {
    setSorenessByMuscle(createInitialSorenessState());
    setSorenessNotes("");
    setSorenessStatus("Idle");
  }

  async function beginWorkoutLoad() {
    if (isBeginWorkoutLoadInProgress.current) {
      return;
    }
    isBeginWorkoutLoadInProgress.current = true;
    const today = new Date().toISOString().slice(0, 10);
    try {
      const reviewStatus = await api.getWeeklyReviewStatus();
      if (reviewStatus.today_is_sunday && reviewStatus.review_required) {
        setMessage("Sunday review required before starting workout. Go to Check-In to submit weekly review.");
        return;
      }

      const entries = await api.listSoreness(today, today);
      if (entries.length > 0) {
        await loadToday();
        return;
      }
      resetSorenessForm();
      setShowSorenessModal(true);
    } catch {
      setMessage("Unable to verify soreness status. Try again.");
    } finally {
      isBeginWorkoutLoadInProgress.current = false;
    }
  }

  async function submitSorenessAndLoad() {
    const today = new Date().toISOString().slice(0, 10);
    setSorenessStatus("Saving soreness...");
    try {
      await api.createSoreness({
        entry_date: today,
        severity_by_muscle: sorenessByMuscle,
        notes: sorenessNotes || undefined,
      });
      setShowSorenessModal(false);
      await loadToday();
    } catch {
      setSorenessStatus("Failed to save soreness");
    }
  }

  useEffect(() => {
    if (!workout) {
      return;
    }
    const storageKey = `${SWAP_STORAGE_PREFIX}:${workout.session_id}`;
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
    performed: { reps: number; weight: number },
  ) {
    if (!workout) return;
    setCompletedSetsByExercise((prev) => {
      const next = { ...prev, [exerciseId]: completedCount };
      try {
        const completedKey = `hypertrophy_completed_sets:${workout.session_id}`;
        localStorage.setItem(completedKey, JSON.stringify(next));
      } catch {
        // ignore storage errors
      }
      return next;
    });

    // find exercise info for payload
    const exercise = workout.exercises.find((e) => e.id === exerciseId);
    if (!exercise) return;

    const payload = {
      primary_exercise_id: exercise.primary_exercise_id ?? null,
      exercise_id: exerciseId,
      set_index: completedCount,
      reps: performed.reps,
      weight: lbsToKg(performed.weight),
      rpe: null,
    } as const;

    try {
      const feedback = await api.logSet(workout.session_id, payload);
      setSetFeedbackByExercise((prev) => ({ ...prev, [exerciseId]: feedback }));
      setLiveRecommendationByExercise((prev) => ({
        ...prev,
        [exerciseId]: feedback.live_recommendation,
      }));

      // refresh from server-side progress to keep client in sync
      try {
        const progress = await api.getWorkoutProgress(workout.session_id);
        const serverCompleted = Object.fromEntries(
          (progress.exercises ?? []).map((item) => [item.exercise_id, Number(item.completed_sets) || 0]),
        ) as Record<string, number>;
        if (Object.keys(serverCompleted).length > 0) {
          setCompletedSetsByExercise(serverCompleted);
          const percent = Number(progress.percent_complete) || 0;
          setWorkoutProgress({
            completed: Number(progress.completed_total) || 0,
            planned: Number(progress.planned_total) || 0,
            percent,
          });
          const completedKey = `hypertrophy_completed_sets:${workout.session_id}`;
          localStorage.setItem(completedKey, JSON.stringify(serverCompleted));
          if (percent >= 100) {
            await loadWorkoutSummary(workout.session_id);
          }
        }
      } catch {
        // keep optimistic state when progress refresh fails
      }
    } catch (e) {
      // log but don't interrupt user flow
      // eslint-disable-next-line no-console
      console.warn("logSet failed", e);
    }
  }

  const swapTarget = workout?.exercises.find((exercise) => exercise.id === swapTargetExerciseId) ?? null;
  const swapTargetCurrentIndex = swapTarget ? (swapIndexByExercise[swapTarget.id] ?? 0) : 0;
  const activeProgramId = workout ? extractProgramId(workout.session_id) : null;

  const todayDate = new Date().toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });

  return (
    <div className="space-y-4">
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
        <div className="main-card main-card--shell space-y-2 ui-body-sm">
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
          {message.startsWith("No workout available") ? (
            <Button type="button" onClick={recoverMissingWorkout} disabled={recoveringMissingWorkout}>
              <span className="inline-flex items-center gap-2">
                <UiIcon name="plan" className="ui-icon--action" />
                {recoveringMissingWorkout ? "Generating..." : "Generate Week and Reload Today"}
              </span>
            </Button>
          ) : null}
        </div>
      ) : null}

      {workout ? (
        <div className="space-y-3">
          <p className="ui-body-sm text-zinc-200">
            {workout.title} · {workoutProgress?.completed ?? 0}/{workoutProgress?.planned ?? 0} sets
          </p>

          <ul className="space-y-1" aria-label="Exercise list">
            {workout.exercises.map((exercise) => {
              const selectedName = resolveExerciseName(exercise, swapIndexByExercise);
              const completed = completedSetsByExercise[exercise.id] ?? 0;
              return (
                <li key={exercise.id}>
                  <button
                    type="button"
                    className="flex min-h-[44px] w-full items-center justify-between gap-2 rounded-md border border-zinc-800 bg-zinc-900/50 px-3 py-2.5 text-left text-sm text-zinc-100 transition-colors hover:border-zinc-700 hover:bg-zinc-800/80"
                    onClick={() => setSelectedExerciseId(exercise.id)}
                  >
                    <span className="font-medium">{selectedName}</span>
                    <span className="text-zinc-400">
                      {completed}/{exercise.sets} · {exercise.rep_range[0]}-{exercise.rep_range[1]} reps @ {kgToLbs(exercise.recommended_working_weight)} lbs
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>


          <WorkoutSummaryCard summary={workoutSummary} />
        </div>
      ) : null}

      {workout && selectedExerciseId ? (() => {
        const exercise = workout.exercises.find((e) => e.id === selectedExerciseId);
        if (!exercise) {
          return null;
        }
        const selectedName = resolveExerciseName(exercise, swapIndexByExercise);
        const guideHref = activeProgramId
          ? `/guides/${activeProgramId}/exercise/${exercise.primary_exercise_id ?? exercise.id}`
          : null;
        const completed = completedSetsByExercise[exercise.id] ?? 0;
        const recommendation = liveRecommendationByExercise[exercise.id];
        const feedback = setFeedbackByExercise[exercise.id];
        const mediaUrl = resolveExerciseMediaUrl(exercise);
        const substitutions = exercise.substitution_candidates ?? [];
        let doThisSetLine: string;
        if (recommendation) {
          const guidance = resolveGuidanceText(recommendation.guidance_rationale, recommendation.guidance);
          doThisSetLine = guidance.trim()
            || `Next set: ${recommendation.recommended_reps_min}-${recommendation.recommended_reps_max} reps @ ${kgToLbs(recommendation.recommended_weight)} lbs`;
        } else if (feedback) {
          const guidance = resolveGuidanceText(feedback.guidance_rationale, feedback.guidance);
          doThisSetLine = guidance.trim()
            || `${exercise.rep_range[0]}-${exercise.rep_range[1]} reps @ ${kgToLbs(exercise.recommended_working_weight)} lbs this set`;
        } else {
          doThisSetLine = `Do ${exercise.rep_range[0]}-${exercise.rep_range[1]} reps @ ${kgToLbs(exercise.recommended_working_weight)} lbs this set`;
        }
        return (
          <div className="fixed inset-0 z-50 flex flex-col bg-zinc-950" aria-modal="true" role="dialog">
            <div className="flex min-h-[44px] items-center gap-2 border-b border-zinc-800 px-3 py-2">
              <Button
                type="button"
                variant="ghost"
                className="min-h-[44px] min-w-[44px]"
                onClick={() => setSelectedExerciseId(null)}
                aria-label="Back to list"
              >
                <UiIcon name="close" className="ui-icon--action" />
              </Button>
              <span className="text-sm font-medium text-zinc-100">Exercise</span>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              <div>
                <h2 className="text-lg font-semibold text-zinc-100">
                  {guideHref ? (
                    <Link href={guideHref} className="underline decoration-zinc-500 underline-offset-2">
                      {selectedName}
                    </Link>
                  ) : (
                    selectedName
                  )}
                </h2>
                <p className="ui-meta mt-1">
                  {exercise.sets} sets · {exercise.rep_range[0]}-{exercise.rep_range[1]} reps @ {kgToLbs(exercise.recommended_working_weight)} lbs
                </p>
              </div>
              <ExerciseExecutionDetails exercise={exercise} />
              <p className="text-sm text-zinc-200">{doThisSetLine}</p>
              <ExerciseControlModule
                exerciseId={exercise.id}
                note={exercise.notes}
                totalSets={exercise.sets}
                defaultRestSeconds={90}
                recommendedWorkingWeight={kgToLbs(exercise.recommended_working_weight)}
                repRange={exercise.rep_range}
                initialCompletedSets={completed}
                onSetComplete={handleSetComplete}
              />
              <div className="space-y-2">
                <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">Options</p>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                  <Button
                    type="button"
                    variant="secondary"
                    className="min-h-[44px] w-full justify-start sm:justify-center"
                    disabled={!mediaUrl}
                    onClick={() => mediaUrl && window.open(mediaUrl, "_blank", "noopener,noreferrer")}
                  >
                    <span className="inline-flex items-center gap-2">
                      <UiIcon name="video" className="ui-icon--action" />
                      Video
                    </span>
                  </Button>
                  <Button
                    type="button"
                    variant="secondary"
                    className="min-h-[44px] w-full justify-start sm:justify-center"
                    disabled={substitutions.length === 0}
                    onClick={() => setSwapTargetExerciseId(exercise.id)}
                  >
                    <span className="inline-flex items-center gap-2">
                      <UiIcon name="swap" className="ui-icon--action" />
                      I don&apos;t have this equipment
                    </span>
                  </Button>
                  <Button
                    type="button"
                    variant="secondary"
                    className="min-h-[44px] w-full justify-start sm:justify-center"
                    onClick={() => toggleNotes(exercise.id)}
                  >
                    <span className="inline-flex items-center gap-2">
                      <UiIcon name="notes" className="ui-icon--action" />
                      Notes
                    </span>
                  </Button>
                </div>
              </div>
              {(notesOpenByExercise[exercise.id] ?? false) && (
                <div className="rounded-md border border-zinc-800 bg-zinc-900/40 p-2 text-xs text-zinc-300">
                  {exercise.notes ?? "No notes for this slot."}
                </div>
              )}
            </div>
          </div>
        );
      })() : null}

      {swapTarget ? (
        <div className="fixed inset-0 z-50 flex items-end bg-black/60 p-4 md:items-center md:justify-center">
          <div className="main-card main-card--elevated w-full max-w-md spacing-grid">
            <div>
              <p className="text-sm font-semibold text-zinc-100">Choose a substitute</p>
              <p className="ui-meta">Slot: {swapTarget.name}</p>
            </div>

            <div className="ui-segmented ui-segmented--auto">
              <Button
                className="w-full justify-start"
                onClick={() => selectSwap(swapTarget.id, 0)}
                type="button"
                variant="segment"
                aria-pressed={swapTargetCurrentIndex === 0}
              >
                {swapTarget.name} (Original)
              </Button>

              {(swapTarget.substitution_candidates ?? []).map((candidate, index) => {
                const value = index + 1;
                return (
                  <Button
                    key={`${swapTarget.id}-${candidate}`}
                    className="w-full justify-start"
                    onClick={() => selectSwap(swapTarget.id, value)}
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
        <div className="fixed inset-0 z-50 flex items-end bg-black/60 p-4 md:items-center md:justify-center">
          <div className="main-card main-card--elevated w-full max-w-md spacing-grid">
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
                  setShowSorenessModal(false);
                  await loadToday();
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
