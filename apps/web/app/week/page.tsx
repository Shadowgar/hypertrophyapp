"use client";

import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Disclosure } from "@/components/ui/disclosure";
import { UiIcon } from "@/components/ui/icons";
import { api, getProgramDisplayName, type GeneratedWeekExercise, type GeneratedWeekPlan, type ProgramTemplateOption, type Profile } from "@/lib/api";
import { kgToLbs } from "@/lib/weight";

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

function formatLeadExercise(exercise: GeneratedWeekExercise | undefined): string {
  if (!exercise) {
    return "No exercises planned.";
  }
  return `${exercise.name} · ${exercise.sets} sets · ${exercise.rep_range[0]}-${exercise.rep_range[1]} reps @ ${kgToLbs(exercise.recommended_working_weight)} lbs`;
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
  const substitutions = resolveAuthoredSubstitutions(exercise);
  const trackingLoads = resolveTrackingLoads(exercise);
  const mediaUrl = resolveExerciseMediaUrl(exercise);
  const hasPrescription = Boolean(exercise.warm_up_sets || exercise.working_sets || exercise.reps);

  return (
    <div className="rounded-md border border-white/10 bg-black/20 p-2 text-[11px] text-zinc-300">
      <p className="font-semibold text-zinc-100">{exercise.name}</p>
      <p className="telemetry-meta">
        {exercise.sets} sets · {exercise.rep_range[0]}-{exercise.rep_range[1]} reps · {kgToLbs(exercise.recommended_working_weight)} lbs
      </p>
      {hasPrescription ? (
        <p className="mt-1">
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
      {exercise.notes ? <p className="mt-1">{exercise.notes}</p> : null}
    </div>
  );
}

function formatSessionDate(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
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
  const muscleCoverage = plan.muscle_coverage ?? {};
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
          Week {weekIndex} · {sessionCount} sessions · {splitLabel} split
        </p>
        {authoredBlockLabel ? <p className="text-sm text-zinc-400">{authoredBlockLabel}</p> : null}
        {weakPointScheduled ? <p className="text-sm text-zinc-200">Arms & Weak Points emphasis is scheduled this week.</p> : null}
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <Disclosure title="Mesocycle Posture" badge={deloadActive ? "deload" : "standard"} defaultOpen={false}>
          <div className="space-y-1 text-sm text-zinc-200">
            <p>Week {weekIndex}/{triggerWeeks}</p>
            <p>Deload reason: {deloadReason}</p>
            {deloadActive ? (
              <p>Set reduction: {deloadSetPct}% · Load reduction: {deloadLoadPct}%</p>
            ) : null}
          </div>
        </Disclosure>

        <Disclosure title="Coverage Radar" badge={`${coveredMuscles.length} covered · ${underTarget.length} gaps`} defaultOpen={false}>
          <div className="space-y-2 text-sm text-zinc-200">
            <p>Minimum {muscleCoverage.minimum_sets_per_muscle ?? 0} sets per muscle</p>
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
        </Disclosure>
      </div>
    </div>
  );
}

function WeekExecutionCards({ plan }: Readonly<{ plan: GeneratedWeekPlan }>) {
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
        {(plan.sessions ?? []).map((session, index) => {
          const exercises = session.exercises ?? [];
          const totalSets = exercises.reduce((sum, exercise) => sum + exercise.sets, 0);
          const dayRoleLabel = formatRoleLabel(session.day_role);
          const weakPointSlotCount = countSlotRole(exercises, "weak_point");
          return (
            <Disclosure
              key={session.session_id}
              title={`Day ${index + 1}: ${session.title}`}
              badge={`${exercises.length} exercises · ${totalSets} sets`}
              defaultOpen={false}
            >
              <div className="space-y-2 text-xs text-zinc-200">
                <p className="telemetry-meta">{formatSessionDate(session.date)}</p>
                <p>Lead: {formatLeadExercise(exercises[0])}</p>
                {dayRoleLabel ? <p className="telemetry-meta">Intent: {dayRoleLabel}</p> : null}
                <p className="telemetry-meta">
                  Coverage: {uniqueMuscles(exercises).join(", ") || "Untracked"}
                </p>
                {weakPointSlotCount > 0 ? <p className="telemetry-meta">Weak-point slots: {weakPointSlotCount}</p> : null}
                <div className="mt-2 space-y-2">
                  {exercises.map((exercise) => (
                    <ExerciseExecutionDetails key={`${session.session_id}-${exercise.id}`} exercise={exercise} />
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

function resolvePlanTargetDays(plan: GeneratedWeekPlan | null): number | null {
  if (!plan) {
    return null;
  }
  const adaptationTarget = plan.applied_frequency_adaptation?.target_days;
  if (typeof adaptationTarget === "number") {
    return adaptationTarget;
  }
  const runtimeDays = plan.generation_runtime_trace?.outcome?.effective_days_available;
  if (typeof runtimeDays === "number") {
    return runtimeDays;
  }
  const profileDays = plan.user?.days_available;
  return typeof profileDays === "number" ? profileDays : null;
}

export default function WeekPage() {
  const [planStatus, setPlanStatus] = useState("Generate a weekly plan.");
  const [plan, setPlan] = useState<GeneratedWeekPlan | null>(null);
  const [programs, setPrograms] = useState<ProgramTemplateOption[]>([]);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [selectedProgramId, setSelectedProgramId] = useState<string | null>(null);
  const [targetDays, setTargetDays] = useState<number>(3);
  const [isGenerating, setIsGenerating] = useState(false);

  const commandDeck = useMemo(() => {
    if (!plan) {
      return null;
    }
    const totalPlannedSets = (plan.sessions ?? []).reduce(
      (sum, session) => sum + (session.exercises ?? []).reduce((s, ex) => s + (ex.sets ?? 0), 0),
      0,
    );
    const volumeByMuscle = Object.values(plan.weekly_volume_by_muscle ?? {}).reduce(
      (sum, value) => sum + value,
      0,
    );
    return {
      totalPlannedSets,
      volumeByMuscle,
      underTarget: plan.muscle_coverage?.under_target_muscles ?? [],
      leadSession: (plan.sessions ?? [])[0] ?? null,
    };
  }, [plan]);
  const requiresSundayReview = planStatus.startsWith("Sunday review required.");
  const generationFailed = planStatus.startsWith("Failed to generate week plan:");
  const awaitingInitialGeneration = !plan && !requiresSundayReview && !generationFailed;

  async function generate() {
    setIsGenerating(true);
    try {
      const reviewStatus = await api.getWeeklyReviewStatus();
      if (reviewStatus.today_is_sunday && reviewStatus.review_required) {
        setPlan(null);
        setPlanStatus("Sunday review required. Open Check-In, submit weekly review, then generate the next week.");
        return;
      }
      const templateId = selectedProgramId ?? plan?.program_template_id ?? null;
      const data = await api.generateWeek(templateId, targetDays);
      setPlan(data);
      setPlanStatus(`Week generated for ${getProgramDisplayName({ id: data.program_template_id })}.`);
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Unknown error";
      setPlan(null);
      setPlanStatus(`Failed to generate week plan: ${detail}`);
    } finally {
      setIsGenerating(false);
    }
  }

  useEffect(() => {
    let mounted = true;
    Promise.all([
      api.listPrograms().catch(() => [] as ProgramTemplateOption[]),
      api.getProfile().catch(() => null as Profile | null),
      api.getLatestWeekPlan().catch(() => null as GeneratedWeekPlan | null),
    ]).then(([list, loadedProfile, latestPlan]) => {
      if (!mounted) {
        return;
      }
      setPrograms(list);
      setProfile(loadedProfile);
      const resolvedTargetDays = resolvePlanTargetDays(latestPlan) ?? loadedProfile?.days_available ?? 3;
      setTargetDays(Math.max(2, Math.min(5, resolvedTargetDays)));
      if (latestPlan) {
        setPlan(latestPlan);
        setPlanStatus(`Week generated for ${getProgramDisplayName({ id: latestPlan.program_template_id })}.`);
      }
    });

    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div className="space-y-4">
      <h1 className="ui-title-page">Week Plan</h1>

      <Button aria-label="Generate week plan" className="w-full min-h-[48px] text-sm font-semibold" onClick={generate} disabled={isGenerating}>
        <span className="inline-flex items-center gap-2">
          <UiIcon name="plan" className="ui-icon--action" />
          {isGenerating ? "Generating Week..." : plan ? "Regenerate Week" : "Generate Week"}
        </span>
      </Button>

      <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4 space-y-2">
        <label className="flex flex-col gap-2 text-sm text-zinc-200" htmlFor="week-target-days">
          <span className="font-medium">Target training days</span>
          <select
            id="week-target-days"
            aria-label="Week target training days selector"
            className="ui-select"
            value={String(targetDays)}
            onChange={(event) => setTargetDays(Number(event.target.value))}
          >
            {["2", "3", "4", "5"].map((value) => (
              <option key={value} value={value}>
                {value} days
              </option>
            ))}
          </select>
        </label>
        <p className="text-xs text-zinc-400">
          Generating for <span className="font-medium text-zinc-200">{targetDays}</span> training day{targetDays === 1 ? "" : "s"} this week.
          {profile ? ` Profile default: ${profile.days_available} day${profile.days_available === 1 ? "" : "s"}.` : ""}
        </p>
      </div>

      <Disclosure title="Program Override" badge={selectedProgramId ? "custom" : "auto"} defaultOpen={false}>
        <div className="space-y-2">
          <select id="week-program" aria-label="Week program override selector" className="ui-select" value={selectedProgramId ?? ""} onChange={(e) => setSelectedProgramId(e.target.value || null)}>
            <option value="">Auto — trainer&apos;s recommended program</option>
            {programs.map((p) => <option key={p.id} value={p.id}>{getProgramDisplayName(p)}</option>)}
          </select>
          <p className="text-xs text-zinc-500">Override the server selection for this week generation request.</p>
        </div>
      </Disclosure>

      {planStatus ? (
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 px-4 py-3">
          <p className="text-sm text-zinc-200">{planStatus}</p>
          {requiresSundayReview ? (
            <a className="mt-2 inline-flex items-center justify-center rounded-md border border-white/10 bg-zinc-900/70 px-3 py-2 text-xs text-zinc-100 hover:bg-zinc-900" href="/checkin">
              Open Check-In
            </a>
          ) : null}
        </div>
      ) : null}

      {commandDeck ? (
        <div className="grid grid-cols-3 gap-2">
          <div className="rounded-md border border-white/10 bg-zinc-900/70 p-2 text-center">
            <p className="text-[10px] uppercase tracking-wide text-zinc-500">Planned sets</p>
            <p className="text-sm font-semibold text-zinc-100">{commandDeck.totalPlannedSets}</p>
            {commandDeck.volumeByMuscle !== commandDeck.totalPlannedSets ? (
              <p className="text-[10px] text-zinc-500">Volume by muscle: {commandDeck.volumeByMuscle}</p>
            ) : null}
          </div>
          <div className="rounded-md border border-white/10 bg-zinc-900/70 p-2 text-center">
            <p className="text-[10px] uppercase tracking-wide text-zinc-500">Lead</p>
            <p className="text-sm font-semibold text-zinc-100 truncate">{commandDeck.leadSession?.title ?? "—"}</p>
          </div>
          <div className="rounded-md border border-white/10 bg-zinc-900/70 p-2 text-center">
            <p className="text-[10px] uppercase tracking-wide text-zinc-500">Gaps</p>
            <p className="text-sm font-semibold text-zinc-100">{commandDeck.underTarget.length > 0 ? commandDeck.underTarget.map((muscle) => formatLabel(muscle)).join(", ") : "none"}</p>
          </div>
        </div>
      ) : null}

      {plan ? (
        <>
          <WeekOverviewCards plan={plan} selectedProgramId={selectedProgramId} />
          <WeekExecutionCards plan={plan} />
        </>
      ) : null}
    </div>
  );
}
