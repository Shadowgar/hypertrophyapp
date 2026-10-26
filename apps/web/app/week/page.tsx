"use client";

import { authoredRepLabel, isBodyweightAuthored } from "@/lib/authored-prescription";
import { authoredRelationshipLabels } from "@/lib/authored-relationships";

import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Disclosure } from "@/components/ui/disclosure";
import { api, getToken, getProgramDisplayName, type GeneratedWeekExercise, type GeneratedWeekPlan, type HistoryOccurrenceStatus, type ProgramTemplateOption, type Profile, type SchedulingContext, type SelectedDatePlanRequest } from "@/lib/api";
import { datesInWeek, formatCalendarDate } from "@/lib/calendar-date";
import { useAppearance } from "@/components/appearance-provider";
import { displayLoad } from "@/lib/appearance";

function formatLabel(value: string): string {
  return value
    .replaceAll("_", " ")
    .trim()
    .split(/\s+/)
    .map((part) => (part.length ? part[0].toUpperCase() + part.slice(1) : part))
    .join(" ");
}

function formatRoleLabel(value: string | null | undefined): string | null {
  const normalized = value?.trim();
  if (!normalized) {
    return null;
  }
  if (normalized === "weak_point_arms") {
    return "Arms & Weak Points";
  }
  return formatLabel(normalized);
}

function formatAuthoredBlockLabel(plan: Pick<GeneratedWeekPlan, "mesocycle"> | null | undefined): string | null {
  const authoredWeekIndex =
    typeof plan?.mesocycle?.authored_week_index === "number" ? plan.mesocycle.authored_week_index : null;
  const authoredWeekRole = formatRoleLabel(plan?.mesocycle?.authored_week_role);
  if (authoredWeekIndex === null && !authoredWeekRole) {
    return null;
  }
  return `Authored block: ${authoredWeekIndex !== null ? `Week ${authoredWeekIndex}` : "Current"} · ${authoredWeekRole ?? "Unspecified"}`;
}

function countSlotRole(exercises: GeneratedWeekExercise[], slotRole: string): number {
  return exercises.filter((exercise) => exercise.slot_role === slotRole).length;
}

function hasWeakPointEmphasis(plan: GeneratedWeekPlan): boolean {
  return (plan.sessions ?? []).some(
    (session) => session.day_role === "weak_point_arms" || countSlotRole(session.exercises ?? [], "weak_point") > 0,
  );
}

function formatSignedPercent(scale: number): string {
  const delta = Math.round((scale - 1) * 100);
  return `${delta >= 0 ? "+" : ""}${delta}%`;
}

function formatExerciseLoad(exercise: GeneratedWeekExercise, unit: "kg" | "lb"): string {
  if (!exercise.customized && isBodyweightAuthored(exercise)) return "Bodyweight";
  const weight = exercise.recommended_working_weight;
  if (typeof weight !== "number" || !Number.isFinite(weight)) {
    return exercise.customized ? "Exercise-specific calibration pending" : "Record actual load";
  }
  return `${displayLoad(weight, unit)} ${unit}`;
}

function formatLeadExercise(exercise: GeneratedWeekExercise | undefined, unit: "kg" | "lb"): string {
  if (!exercise) {
    return "No exercises planned.";
  }
  return `${exercise.name} · ${exercise.sets} sets · ${authoredRepLabel(exercise)} reps @ ${formatExerciseLoad(exercise, unit)}`;
}

function resolveExerciseMediaUrl(exercise: GeneratedWeekExercise): string | null {
  const preferred = exercise.video?.youtube_url ?? exercise.video_url ?? exercise.demo_url;
  return typeof preferred === "string" && preferred.trim().length > 0 ? preferred : null;
}

function resolveAuthoredSubstitutions(exercise: GeneratedWeekExercise): string[] {
  return [exercise.substitution_option_1, exercise.substitution_option_2].filter(
    (value, index, source): value is string =>
      typeof value === "string" && value.trim().length > 0 && source.indexOf(value) === index,
  );
}

function resolveTrackingLoads(exercise: GeneratedWeekExercise): string[] {
  return [exercise.tracking_set_1, exercise.tracking_set_2, exercise.tracking_set_3, exercise.tracking_set_4].filter(
    (value): value is string => typeof value === "string" && value.trim().length > 0,
  );
}

function ExerciseExecutionDetails({ exercise }: Readonly<{ exercise: GeneratedWeekExercise }>) {
  const { preferences } = useAppearance();
  const substitutions = resolveAuthoredSubstitutions(exercise);
  const trackingLoads = resolveTrackingLoads(exercise);
  const mediaUrl = resolveExerciseMediaUrl(exercise);
  const hasPrescription = Boolean(exercise.warm_up_sets || exercise.working_sets || exercise.reps);

  return (
    <div className="rounded-md border border-white/10 bg-black/20 p-2 text-[11px] text-zinc-300">
      <p className="font-semibold text-zinc-100">{exercise.name}</p>
      {authoredRelationshipLabels(exercise).map((label) => (
        <span key={label} className="mr-2 inline-block text-amber-300">{label}</span>
      ))}
      <p className="telemetry-meta">
        {exercise.sets} sets · {authoredRepLabel(exercise)} reps · {formatExerciseLoad(exercise, preferences.weight_unit)}
      </p>
      {hasPrescription ? (
        <p className="mt-1">
          Authored prescription: {exercise.warm_up_sets ?? "Unknown"} warm-up sets · {exercise.working_sets ?? String(exercise.sets)} working sets · {exercise.reps ?? `${authoredRepLabel(exercise)}`}
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
      {exercise.notes ? <p className="mt-1">{exercise.notes}</p> : null}
    </div>
  );
}

function resolveGeneratedWeekReasonSummary(trace: Record<string, unknown> | undefined): string | null {
  const reasonSummary = typeof trace?.reason_summary === "string" ? trace.reason_summary.trim() : "";
  return reasonSummary.length > 0 ? reasonSummary : null;
}

function numberFromTrace(source: Record<string, unknown> | undefined, key: string): number | null {
  const value = source?.[key];
  return typeof value === "number" ? value : null;
}

function stringListFromUnknown(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string" && item.trim().length > 0) : [];
}

function WeekOverviewCards({ plan, selectedProgramId }: Readonly<{ plan: GeneratedWeekPlan; selectedProgramId: string | null }>) {
  const customized=Boolean(plan.customized)||plan.program_template_id==='customized_full_body_v1';
  const muscleCoverage = plan.muscle_coverage ?? {};
  const hasCoverage=typeof muscleCoverage.minimum_sets_per_muscle==='number'&&Array.isArray(muscleCoverage.covered_muscles)&&Array.isArray(muscleCoverage.under_target_muscles);
  const programName = typeof plan.program_template_id === "string" && plan.program_template_id.trim().length > 0
    ? getProgramDisplayName({ id: plan.program_template_id })
    : "Generated Week";
  const weekIndex = plan.mesocycle?.week_index ?? 0;
  const triggerWeeks = plan.mesocycle?.trigger_weeks_effective ?? 0;
  const splitLabel = typeof plan.split === "string" && plan.split.trim().length > 0 ? formatLabel(plan.split) : "Unspecified";
  const deloadActive = plan.deload?.active === true;
  const deloadReason = typeof plan.deload?.reason === "string" && plan.deload.reason.trim().length > 0 ? plan.deload.reason : "n/a";
  const deloadSetPct = typeof plan.deload?.set_reduction_pct === "number" ? plan.deload.set_reduction_pct : 0;
  const deloadLoadPct = typeof plan.deload?.load_reduction_pct === "number" ? plan.deload.load_reduction_pct : 0;
  const weeklyVolumeEntries = Object.entries(plan.weekly_volume_by_muscle ?? {})
    .sort((left, right) => right[1] - left[1])
    .slice(0, 4);
  const coveredMuscles = muscleCoverage.covered_muscles ?? [];
  const visibleCoveredMuscles = Object.entries(plan.weekly_volume_by_muscle ?? {})
    .filter(([, sets]) => typeof sets === "number" && sets > 0)
    .map(([muscle]) => muscle);
  const underTarget = muscleCoverage.under_target_muscles ?? [];
  const authoredBlockLabel = formatAuthoredBlockLabel(plan);
  const weakPointScheduled = hasWeakPointEmphasis(plan);
  const sessionCount = (plan.sessions ?? []).length;

  return (
    <div className="space-y-3">
      <div className="main-card main-card--shell spacing-grid spacing-grid--tight">
        <p className="telemetry-kicker">Week Overview</p>
        <p className="telemetry-value">{programName}</p>
        <p className="text-sm text-zinc-300">
          {!customized&&<>Week {weekIndex} · </>}{sessionCount} sessions · {splitLabel} split
        </p>
        {authoredBlockLabel ? <p className="text-sm text-zinc-400">{authoredBlockLabel}</p> : null}
        {weakPointScheduled ? <p className="text-sm text-zinc-200">Arms & Weak Points emphasis is scheduled this week.</p> : null}
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {!customized&&<Disclosure title="Mesocycle Posture" badge={deloadActive ? "deload" : "standard"} defaultOpen={false}>
          <div className="space-y-1 text-sm text-zinc-200">
            <p>Week {weekIndex}/{triggerWeeks}</p>
            <p>Deload reason: {deloadReason}</p>
            {deloadActive ? (
              <p>Set reduction: {deloadSetPct}% · Load reduction: {deloadLoadPct}%</p>
            ) : null}
          </div>
        </Disclosure>}

        {(!customized||hasCoverage)&&<Disclosure title="Coverage Radar" badge={`${visibleCoveredMuscles.length} covered · ${underTarget.length} gaps`} defaultOpen={false}>
          <div className="space-y-2 text-sm text-zinc-200">
            <p>Minimum {muscleCoverage.minimum_sets_per_muscle ?? 0} sets per muscle</p>
            {visibleCoveredMuscles.length !== coveredMuscles.length ? (
              <p className="text-zinc-400">
                Tracked coverage: {coveredMuscles.length} muscles meeting target.
              </p>
            ) : null}
            {underTarget.length > 0 ? <p className="text-yellow-400/80">Under target: {underTarget.join(", ")}</p> : <p className="text-zinc-400">All muscles on target.</p>}
            <div className="space-y-1 text-xs text-zinc-300">
              {weeklyVolumeEntries.map(([muscle, sets]) => (
                <div key={`volume-${muscle}`} className="flex items-center justify-between rounded-md border border-white/10 bg-zinc-900/70 px-2 py-1">
                  <span>{formatLabel(muscle)}</span>
                  <span>{sets} sets</span>
                </div>
              ))}
            </div>
          </div>
        </Disclosure>}
      </div>
    </div>
  );
}

function WeekExecutionCards({ plan }: Readonly<{ plan: GeneratedWeekPlan }>) {
  const { preferences } = useAppearance();
  const runtimeTrace = plan.generation_runtime_trace ?? {};
  const runtimeOutcome = (runtimeTrace.outcome ?? {}) as Record<string, unknown>;
  const effectiveDays = numberFromTrace(runtimeOutcome, "effective_days_available");
  const severeSorenessCount = numberFromTrace(runtimeOutcome, "severe_soreness_count");
  const priorWeeks = numberFromTrace(runtimeOutcome, "prior_generated_weeks");
  const latestAdherence = numberFromTrace(runtimeOutcome, "latest_adherence_score");
  const templateTrace = plan.template_selection_trace ?? {};
  const decisionTrace = plan.decision_trace ?? {};
  const candidateIds = stringListFromUnknown(templateTrace.ordered_candidate_ids);
  const adaptiveReview = plan.adaptive_review;
  const frequencyAdaptation = plan.applied_frequency_adaptation;
  const reasonSummary = resolveGeneratedWeekReasonSummary(decisionTrace);

  return (
    <div className="grid grid-cols-1 gap-3 xl:grid-cols-[1.3fr_1fr]">
      <div className="space-y-3">
        <p className="telemetry-kicker">Sessions</p>
        {(plan.sessions ?? []).map((session) => {
          const exercises = session.exercises ?? [];
          const totalSets = exercises.reduce((sum, exercise) => sum + exercise.sets, 0);
          const dayRoleLabel = formatRoleLabel(session.day_role);
          const weakPointSlotCount = countSlotRole(exercises, "weak_point");
          return (
            <Disclosure
              key={session.workout_occurrence_id ?? session.session_id}
              title={`${formatCalendarDate(session.date)}: ${session.title}`}
              badge={`${exercises.length} exercises · ${totalSets} sets`}
              defaultOpen={false}
            >
              <div className="space-y-2 text-xs text-zinc-200">
                <p className="telemetry-meta">{formatCalendarDate(session.date)}</p>
                <p>Lead: {formatLeadExercise(exercises[0], preferences.weight_unit)}</p>
                {dayRoleLabel ? <p className="telemetry-meta">Intent: {dayRoleLabel}</p> : null}
                <p className="telemetry-meta">
                  Coverage: {uniqueMuscles(exercises).join(", ") || "Untracked"}
                </p>
                {weakPointSlotCount > 0 ? <p className="telemetry-meta">Weak-point slots: {weakPointSlotCount}</p> : null}
                <div className="mt-2 space-y-2">
                  {exercises.map((exercise) => (
                    <ExerciseExecutionDetails key={exercise.exercise_occurrence_id ?? `${session.session_id}-${exercise.id}`} exercise={exercise} />
                  ))}
                </div>
              </div>
            </Disclosure>
          );
        })}
      </div>

      <div className="space-y-3">
        <Disclosure title="Generation Details" badge={reasonSummary ? "has summary" : null} defaultOpen={false}>
          <div className="space-y-2">
            {reasonSummary ? <p className="text-sm text-zinc-200">{reasonSummary}</p> : null}
            <div className="grid grid-cols-2 gap-2 text-xs text-zinc-300">
              <div className="rounded-md border border-white/10 bg-zinc-900/70 p-2">
                Effective days: {effectiveDays ?? plan.user?.days_available ?? "n/a"}
              </div>
              <div className="rounded-md border border-white/10 bg-zinc-900/70 p-2">Prior generated weeks: {priorWeeks ?? 0}</div>
              <div className="rounded-md border border-white/10 bg-zinc-900/70 p-2">Latest adherence: {latestAdherence ?? "n/a"}</div>
              <div className="rounded-md border border-white/10 bg-zinc-900/70 p-2">Severe soreness flags: {severeSorenessCount ?? 0}</div>
            </div>
            {candidateIds.length > 0 ? <p className="telemetry-meta">Candidate stack: {candidateIds.join(" -> ")}</p> : null}
          </div>
        </Disclosure>

        {adaptiveReview ? (
          <Disclosure title="Adaptive Review" badge={`${adaptiveReview.global_set_delta >= 0 ? "+" : ""}${adaptiveReview.global_set_delta} sets`} defaultOpen={false}>
            <div className="space-y-1 text-sm text-zinc-200">
              <p>Load scale: {formatSignedPercent(adaptiveReview.global_weight_scale)}</p>
              <p>Weak-point slots: {adaptiveReview.weak_point_exercises.length > 0 ? adaptiveReview.weak_point_exercises.join(", ") : "none"}</p>
            </div>
          </Disclosure>
        ) : null}

        {frequencyAdaptation ? (
          <Disclosure title="Frequency Adaptation" badge={`${frequencyAdaptation.target_days} days`} defaultOpen={false}>
            <div className="space-y-1 text-sm text-zinc-200">
              <p>{frequencyAdaptation.weeks_remaining_before_apply} → {frequencyAdaptation.weeks_remaining_after_apply} weeks remaining</p>
              <p>Weak areas preserved: {frequencyAdaptation.weak_areas.length > 0 ? frequencyAdaptation.weak_areas.join(", ") : "none"}</p>
            </div>
          </Disclosure>
        ) : null}
      </div>
    </div>
  );
}

function uniqueMuscles(exercises: GeneratedWeekExercise[]): string[] {
  return Array.from(
    new Set(
      exercises.flatMap((exercise) =>
        Array.isArray(exercise.primary_muscles)
          ? exercise.primary_muscles.filter((muscle) => typeof muscle === "string" && muscle.trim().length > 0)
          : [],
      ),
    ),
  ).map((muscle) => formatLabel(muscle));
}

function SchedulingWarnings({ plan }: { plan: GeneratedWeekPlan }) {
  if (!plan.schedule) return null;
  return <div className="rounded-md border border-amber-600/40 p-3 space-y-2 text-sm" aria-label="Scheduling workload and spacing">
    <p>Timezone: {plan.schedule.timezone}</p>
    {(plan.schedule.spacing?.warnings ?? []).map((warning) => <p key={warning} className="text-amber-300">{warning}</p>)}
    {plan.schedule.spacing?.gap_days.length ? <p>Calendar gaps between workouts: {plan.schedule.spacing.gap_days.join(", ")} days.</p> : null}
    <p>Review each session’s exercises and working sets. Duration estimates are not calibrated; elapsed time is unknown. Spacing advice does not establish safety or hypertrophy results.</p>
    <p>Date changes cannot move started workouts. Changing the number of dates replaces an entirely unstarted placement; performed history remains attached to its original occurrence.</p>
  </div>;
}

class StaleSchedulingContext extends Error {}

export default function WeekPage() {
  const [planStatus, setPlanStatus] = useState("Choose 2–5 dates, then preview your week.");
  const [plan, setPlan] = useState<GeneratedWeekPlan | null>(null);
  const [programs, setPrograms] = useState<ProgramTemplateOption[]>([]);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [selectedProgramId, setSelectedProgramId] = useState<string | null>(null);
  const [context, setContext] = useState<SchedulingContext | null>(null);
  const [contextState, setContextState] = useState<"loading" | "ready" | "error">("loading");
  const [progress, setProgress] = useState<Record<string, HistoryOccurrenceStatus>>({});
  const [progressState, setProgressState] = useState<"loading" | "ready" | "error">("loading");
  const [progressReload, setProgressReload] = useState(0);
  const contextRef = useRef<SchedulingContext | null>(null);
  const contextToken = useRef<string | null | undefined>(undefined);
  const profileToken = useRef<string | null | undefined>(undefined);
  const [timezone, setTimezone] = useState("");
  const timezoneRef = useRef("");
  const [selectedDates, setSelectedDates] = useState<string[]>([]);
  const [preview, setPreview] = useState<{ plan: GeneratedWeekPlan; request: SelectedDatePlanRequest; digest: string } | null>(null);
  const contextRequest = useRef(0);
  const mountedRef = useRef(true);
  const schedulingRef = useRef(false);
  const preferenceSaveRef = useRef(false);
  const weekOffsetRef = useRef(0);
  const [weekOffset, setWeekOffset] = useState(0);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSavingProgramSelection, setIsSavingProgramSelection] = useState(false);
  const [generatedOnboardingPrompt, setGeneratedOnboardingPrompt] = useState<string | null>(null);
  const preferenceDirty = selectedProgramId !== (profile?.selected_program_id ?? null);
  const progressWeek = context?.week_start;
  const progressRevision = context?.placement_revision;
  useEffect(() => {
    if (!progressWeek) return;
    let active = true;
    const token = getToken();
    setProgress({}); setProgressState("loading");
    api.getHistoryCalendar(progressWeek, datesInWeek(progressWeek)[6]).then(history => {
      if (!active || token !== getToken()) return;
      setProgress(Object.fromEntries((history.days ?? []).flatMap(day => day.occurrences ?? []).filter(occurrence => occurrence.workout_occurrence_id).map(occurrence => [occurrence.workout_occurrence_id, occurrence])));
      setProgressState("ready");
    }).catch(() => { if (active && token === getToken()) setProgressState("error"); });
    return () => { active = false; };
  }, [progressWeek, progressRevision, progressReload]);

  async function saveProgramPreference() {
    if (!preferenceDirty || preferenceSaveRef.current) return;
    const token = getToken();
    if (token !== profileToken.current) { setPlanStatus("Account changed. Reload Week before saving preferences."); return; }
    preferenceSaveRef.current = true;
    setIsSavingProgramSelection(true);
    setPreview(null);
    try {
      const updated = await api.updateProgramSelection({ selected_program_id: selectedProgramId, program_selection_mode: selectedProgramId ? "manual" : "auto" });
      if (!mountedRef.current || token !== getToken()) return;
      setProfile(updated);
      setSelectedProgramId(updated.selected_program_id ?? null);
      if (updated.selected_program_id === "full_body_v1") {
        try {
          const onboarding = await api.getGeneratedOnboarding();
          if (!mountedRef.current || token !== getToken()) return;
          setGeneratedOnboardingPrompt(onboarding.generated_onboarding_complete ? "Generated onboarding preferences complete." : "Generated onboarding recommended to improve plan fit.");
        } catch { if (mountedRef.current && token === getToken()) setGeneratedOnboardingPrompt("Generated onboarding recommended to improve plan fit."); }
      } else setGeneratedOnboardingPrompt(null);
      if (!mountedRef.current || token !== getToken()) return;
      setPlanStatus(selectedProgramId ? `Program preference saved: ${getProgramDisplayName({ id: selectedProgramId })}. Preview your dates when ready.` : "Program preference saved: Auto selection. Preview your dates when ready.");
    } catch (error) { if (mountedRef.current && token === getToken()) setPlanStatus(`Failed to save preferences: ${error instanceof Error ? error.message : "Unknown error"}`); }
    finally { preferenceSaveRef.current = false; if (mountedRef.current && token === getToken()) setIsSavingProgramSelection(false); }
  }

  async function refreshContext(suggestedTimezone: string, force = false): Promise<SchedulingContext> {
    const token = getToken();
    const requestNumber = ++contextRequest.current;
    if (!contextRef.current) setContextState("loading");
    let loaded: SchedulingContext;
    try { loaded = await api.getSchedulingContext(suggestedTimezone, weekOffsetRef.current); }
    catch (error) {
      if (!mountedRef.current || token !== getToken() || requestNumber !== contextRequest.current) throw new StaleSchedulingContext("Scheduling context changed. Try again.");
      setContextState("error");
      throw error;
    }
    if (!mountedRef.current || token !== getToken() || requestNumber !== contextRequest.current) throw new StaleSchedulingContext("Scheduling context changed. Try again.");
    setContextState("ready");
    const previous = contextRef.current;
    const changed = !previous || loaded.week_start !== previous.week_start || loaded.timezone !== previous.timezone || loaded.placement_revision !== previous.placement_revision;
    contextRef.current = loaded;
    contextToken.current = token;
    setContext(loaded);
    setPlan(loaded.plan?.week_start === loaded.week_start ? loaded.plan : null);
    if (changed || force) {
      const allowed = datesInWeek(loaded.week_start);
      setSelectedDates(loaded.selected_dates.filter((date) => allowed.includes(date)));
      setPreview(null);
      setTimezone(loaded.timezone);
      timezoneRef.current = loaded.timezone;
      if (previous && changed) setPlanStatus("The local week or placement changed. Review your dates and preview again.");
    }
    return loaded;
  }

  async function switchWeek(offset: number) {
    if (offset === weekOffsetRef.current) return;
    weekOffsetRef.current = offset;
    setWeekOffset(offset);
    ++contextRequest.current;
    contextRef.current = null;
    setContext(null);
    setPlan(null);
    setPreview(null);
    setSelectedDates([]);
    setPlanStatus("Loading selected week...");
    try {
      await refreshContext(timezoneRef.current, true);
      setPlanStatus("Choose 2–5 dates, then preview your week.");
    } catch (error) {
      if (error instanceof StaleSchedulingContext) return;
      setPlanStatus(`Could not load selected week: ${error instanceof Error ? error.message : "Unknown error"}`);
    }
  }

  function makeRequest(): SelectedDatePlanRequest | null {
    if (!context || contextToken.current !== getToken() || profileToken.current !== getToken() || selectedDates.length < 2 || selectedDates.length > 5 || !timezone.trim()) return null;
    return { template_id: selectedProgramId ?? plan?.program_template_id ?? null, week_start: context.week_start,
      selected_dates: [...selectedDates].sort(), timezone: timezone.trim(), expected_placement_revision: context.placement_revision };
  }

  async function schedule(activate = false) {
    if (schedulingRef.current) return;
    const token = getToken();
    if (token !== contextToken.current || token !== profileToken.current) { setPreview(null); setPlanStatus("Account changed. Reload Week before scheduling."); return; }
    const request = activate ? preview?.request : makeRequest();
    if (!request) return;
    if (activate && JSON.stringify(request) !== JSON.stringify(makeRequest())) {
      setPreview(null);
      setPlanStatus("Your inputs changed. Preview your selected dates again.");
      return;
    }
    const targetOffset = weekOffsetRef.current;
    schedulingRef.current = true;
    setIsGenerating(true);
    let acknowledged = false;
    try {
      const fresh = await refreshContext(request.timezone);
      if (token !== getToken() || token !== profileToken.current) return;
      if (fresh.week_start !== request.week_start || fresh.placement_revision !== request.expected_placement_revision || fresh.timezone !== context?.timezone) {
        setPreview(null);
        setPlanStatus("The local week or placement changed. Review your dates and preview again.");
        return;
      }
      if (activate) {
        if (!preview?.digest) throw new Error("Unable to verify this preview. Try previewing your dates again.");
        await api.activateSelectedDates({ ...request, expected_preview_digest: preview.digest });
        if (!mountedRef.current || token !== getToken()) return;
        acknowledged = true;
        setPreview(null);
        setPlanStatus("Selected dates activated. Refreshing your saved schedule…");
        await refreshContext(request.timezone, true);
        setPlanStatus("Selected dates activated. Today follows your local calendar dates.");
      } else {
        const previewRequest = contextRequest.current;
        const data = await api.previewSelectedDates(request);
        if (!mountedRef.current || token !== getToken() || previewRequest !== contextRequest.current || targetOffset !== weekOffsetRef.current) return;
        if (contextRef.current?.week_start !== request.week_start || contextRef.current?.placement_revision !== request.expected_placement_revision) return;
        const digest = data.schedule?.preview_digest;
        if (!digest || !/^[a-f0-9]{64}$/.test(digest)) throw new Error("Unable to verify this preview. Try previewing your dates again.");
        setPreview({ plan: data, request, digest });
        setPlanStatus("Preview only. Review workload and spacing, then activate these dates.");
      }
    } catch (error) {
      if (!mountedRef.current || token !== getToken()) return;
      setPreview(null);
      if (acknowledged) { setPlanStatus(error instanceof StaleSchedulingContext ? "Selected dates activated. The latest schedule is being refreshed." : "Selected dates activated. The refresh failed; retry loading to see your saved schedule."); return; }
      if (error instanceof StaleSchedulingContext) return;
      if (activate) await refreshContext(request.timezone).catch(() => undefined);
      if (!mountedRef.current || token !== getToken()) return;
      setPlanStatus(`Failed to ${activate ? "activate" : "preview"} selected dates: ${error instanceof Error ? error.message : "Unknown error"}`);
    } finally { schedulingRef.current = false; if (mountedRef.current && token === getToken()) setIsGenerating(false); }
  }

  useEffect(() => {
    let mounted = true;
    mountedRef.current = true;
    const token = getToken();
    const requests = contextRequest;
    const browserTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
    timezoneRef.current = browserTimezone;
    Promise.all([api.listPrograms().catch(() => [] as ProgramTemplateOption[]), api.getProfile().catch(() => null as Profile | null)])
      .then(([list, loadedProfile]) => {
        if (!mounted || token !== getToken()) return;
        if (loadedProfile) profileToken.current = token;
        setPrograms(list); setProfile(loadedProfile); setSelectedProgramId(loadedProfile?.selected_program_id ?? null);
      });
    const refresh = () => refreshContext(timezoneRef.current || browserTimezone).catch((error) => {
      if (mounted && token === getToken() && !(error instanceof StaleSchedulingContext)) { setPreview(null); setPlanStatus(`Could not load current local week: ${error instanceof Error ? error.message : "Unknown error"}`); }
    });
    void refresh();
    window.addEventListener("focus", refresh);
    const onVisibility = () => { if (document.visibilityState === "visible") void refresh(); };
    document.addEventListener("visibilitychange", onVisibility);
    return () => { mounted = false; mountedRef.current = false; ++requests.current; window.removeEventListener("focus", refresh); document.removeEventListener("visibilitychange", onVisibility); };
  }, []);

  const visiblePlan = preview?.plan ?? plan;
  const plannedSets = visiblePlan?.sessions.reduce((sum, session) => sum + session.exercises.reduce((total, exercise) => total + exercise.sets, 0), 0);
  return <div className="ux-page-stack ux-week-root">
    <header>
      <p className="ux-eyebrow">Week</p>
      <h1 className="ui-title-page">Your training week</h1>
      <p className="ui-body-sm">Choose the dates you can train. Preview the workouts before activating your schedule.</p>
      {context ? <p className="ui-meta">{formatCalendarDate(context.week_start)} – {formatCalendarDate(datesInWeek(context.week_start)[6])} · {context.timezone}</p> : null}
    </header>
    <p className="text-sm"><a className="underline" href={plan?.customized?.proposal_id?`/customize?proposal=${encodeURIComponent(plan.customized.proposal_id)}`:"/customize"}>{plan?.customized?"Manage Customized dates or replace program":"Customize My Workout"}</a> · Review explicit date changes and program replacement.</p>
    <div className="ux-week-layout">
    <section className="ux-card ux-week-schedule space-y-3" aria-label="Week scheduling">
      <div className="flex flex-wrap gap-2" aria-label="Select planning week">
        <Button aria-pressed={weekOffset === 0} disabled={isGenerating} onClick={() => void switchWeek(0)}>Current week</Button>
        <Button aria-pressed={weekOffset === 1} disabled={isGenerating} onClick={() => void switchWeek(1)}>Next week</Button>
      </div>
      <Disclosure title="Change scheduling timezone" defaultOpen={false}>
      <label htmlFor="scheduling-timezone" className="block space-y-2 text-sm">
        <span>Scheduling timezone</span>
        <input id="scheduling-timezone" className="ui-input w-full min-h-[44px]" value={timezone} disabled={isGenerating} placeholder="America/New_York"
          onChange={(event) => { timezoneRef.current = event.target.value; setTimezone(event.target.value); setPreview(null); }}
          onBlur={() => { if (timezone.trim() && timezone.trim() !== context?.timezone) void refreshContext(timezone.trim()).catch((error) => {
            if (error instanceof StaleSchedulingContext) return;
            setPreview(null); setPlanStatus(`Could not load timezone: ${error instanceof Error ? error.message : "Unknown error"}`);
          }); }} />
      </label>
      <p className="text-xs text-zinc-400">Confirm this IANA timezone when activating your dates. Dates use your local Monday–Sunday week.</p>
      </Disclosure>
      {context ? <fieldset className="ux-date-picker" aria-label="Select actual training dates" disabled={isGenerating}>
        <legend className="mb-2 text-sm">{`${weekOffset === 1 ? "Next week" : "Current week"}: ${formatCalendarDate(context.week_start)} – ${formatCalendarDate(datesInWeek(context.week_start)[6])} (${context.week_start} – ${datesInWeek(context.week_start)[6]}) · Today: ${formatCalendarDate(context.local_today)}`}</legend>
        <div className="ux-week-dates">
          {datesInWeek(context.week_start).map((date) => <label key={date} data-selected={selectedDates.includes(date)} className="ux-week-date">
            <input type="checkbox" aria-label={formatCalendarDate(date)} checked={selectedDates.includes(date)} onChange={() => {
              setSelectedDates((current) => current.includes(date) ? current.filter((item) => item !== date) : [...current, date].sort()); setPreview(null);
            }} /><span aria-hidden="true">{formatCalendarDate(date).split(",")[0]}</span><strong aria-hidden="true">{Number(date.slice(-2))}</strong>
          </label>)}
        </div>
      </fieldset> : null}
      <p className="text-sm" aria-live="polite">{selectedDates.length} of 2–5 dates selected</p>
      {context && selectedDates.some((date) => date < context.local_today) ? <p className="text-sm text-amber-300">Elapsed dates are placements only; selecting them does not create performed workout history.</p> : null}
      <Button aria-label="Preview selected dates" className="w-full min-h-[48px]" disabled={isGenerating || isSavingProgramSelection || !context || !profile || selectedDates.length < 2 || selectedDates.length > 5 || !timezone.trim()} onClick={() => schedule()}>{isGenerating ? "Checking dates..." : "Preview selected dates"}</Button>
      {preview ? <Button aria-label="Activate selected dates" className="w-full min-h-[48px]" disabled={isGenerating} onClick={() => schedule(true)}>Activate selected dates</Button> : null}
      {contextState === "loading" && !context ? <p role="status">Loading your local week…</p> : null}
      {contextState === "error" ? <div role="alert"><p>Could not refresh your week. Any previously loaded plan is still shown.</p><Button variant="secondary" onClick={() => void refreshContext(timezoneRef.current).then(() => setPlanStatus("Week loaded. Review your dates before previewing.")).catch(error => { if (!(error instanceof StaleSchedulingContext)) setPlanStatus("Could not load your week. Try again."); })}>Retry week loading</Button></div> : null}
    </section>
    <section className="ux-card ux-week-sessions" aria-label="Scheduled sessions">
      <h2 className="ui-title-section">{preview ? "Preview your sessions" : "Your sessions"}</h2>
      {visiblePlan?.sessions.length ? visiblePlan.sessions.map((session) => <article className="ux-week-session" key={session.workout_occurrence_id ?? session.session_id}>
        <p className="ui-meta">{formatCalendarDate(session.date)}</p><h3>{session.title}</h3>
        <p className="ui-body-sm">{session.exercises.length} exercises · {session.exercises.reduce((total, exercise) => total + exercise.sets, 0)} planned working sets</p>
        {!preview ? <p className="ui-meta">{progressLabel(progress[session.workout_occurrence_id ?? ""], progressState)}</p> : null}
        {preview ? <p className="ui-meta">Preview · not activated</p> : session.date === context?.local_today ? <a className="ux-button ux-button-secondary px-4" href="/today">Open scheduled workout</a> : <p className="ui-meta">{session.date < (context?.local_today ?? "") ? "Past scheduled date · see History for performed sets" : "Scheduled · prescriptions below"}</p>}
      </article>) : <p className="ui-body-sm">{context ? "No active workouts for this week. Select dates and preview your plan." : contextState === "error" ? "Scheduled workouts are unavailable until the week loads." : "Loading scheduled workouts…"}</p>}
      {plan ? <a className="ux-button ux-button-secondary px-4" href="/history">Review completed sets in History</a> : null}
      {progressState === "error" && plan ? <Button variant="secondary" onClick={() => setProgressReload(value => value + 1)}>Retry saved progress</Button> : null}
    </section>
    </div>
    <Disclosure title="Program Override" badge={selectedProgramId ? "custom" : "auto"} defaultOpen={false}>
      <div className="space-y-2">
        <select id="week-program" aria-label="Week program override selector" className="ui-select" value={selectedProgramId ?? ""} disabled={isGenerating}
          onChange={(event) => { setSelectedProgramId(event.target.value || null); setPreview(null); }}>
          <option value="">Auto — trainer&apos;s recommended program</option>
          {programs.map((program) => <option key={program.id} value={program.id}>{getProgramDisplayName(program)}</option>)}
        </select>
        <Button aria-label="Save program preference" className="min-h-[44px] px-3 text-xs font-semibold" onClick={saveProgramPreference} disabled={isGenerating || isSavingProgramSelection || !preferenceDirty}>{isSavingProgramSelection ? "Saving..." : "Save Preferences"}</Button>
        <p className="text-xs text-zinc-500">Save program preference separately. Activate dates after reviewing the preview.</p>
        {generatedOnboardingPrompt ? <div className="rounded-md border border-zinc-700 p-2 text-xs"><p>{generatedOnboardingPrompt}</p><a className="underline" href="/customize">Update generated plan preferences</a></div> : null}
      </div>
    </Disclosure>
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 px-4 py-3" role="status">
      <p className="text-sm text-zinc-200">{planStatus}</p>
    </div>
    {visiblePlan ? <>
      {preview ? <p className="text-sm font-semibold">Placement preview — awaiting activation</p> : null}
      <p className="text-sm">Planned sets: {plannedSets}</p>
      <SchedulingWarnings plan={visiblePlan} />
      <WeekOverviewCards plan={visiblePlan} selectedProgramId={selectedProgramId} />
      <WeekExecutionCards plan={visiblePlan} />
    </> : null}
  </div>;
}

function progressLabel(receipt: HistoryOccurrenceStatus | undefined, state: "loading" | "ready" | "error") {
  if (state === "loading") return "Checking saved progress…";
  if (!receipt || receipt.status === "unknown" || receipt.working_sets_planned === null) return "Completion unavailable · review recorded sets in History";
  const status = receipt.status === "complete" ? "Complete" : receipt.status === "partial" ? "In progress" : "Scheduled";
  return `${status} · ${receipt.working_sets_completed} of ${receipt.working_sets_planned} working sets saved`;
}
