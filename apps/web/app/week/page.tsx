"use client";

import { useEffect, useMemo, useState } from "react";

import CoachingIntelligencePanel from "@/components/coaching-intelligence-panel";
import { Button } from "@/components/ui/button";
import { UiIcon } from "@/components/ui/icons";
import { api, getProgramDisplayName, resolveReasonText, type GeneratedWeekExercise, type GeneratedWeekPlan, type ProgramTemplateOption } from "@/lib/api";

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
  return plan.sessions.some(
    (session) => session.day_role === "weak_point_arms" || countSlotRole(session.exercises, "weak_point") > 0,
  );
}

function buildWeekContextNote(plan: GeneratedWeekPlan | null): string | null {
  if (!plan) {
    return null;
  }
  const authoredWeekIndex =
    typeof plan.mesocycle.authored_week_index === "number" ? plan.mesocycle.authored_week_index : null;
  const authoredWeekRole = formatRoleLabel(plan.mesocycle.authored_week_role)?.toLowerCase() ?? null;
  const parts: string[] = [];
  if (authoredWeekIndex !== null && authoredWeekRole) {
    parts.push(`Week ${authoredWeekIndex} ${authoredWeekRole} block.`);
  }
  if (hasWeakPointEmphasis(plan)) {
    parts.push("Arms & Weak Points emphasis is scheduled.");
  }
  return parts.length > 0 ? parts.join(" ") : null;
}

function formatSignedPercent(scale: number): string {
  const delta = Math.round((scale - 1) * 100);
  return `${delta >= 0 ? "+" : ""}${delta}%`;
}

function formatLeadExercise(exercise: GeneratedWeekExercise | undefined): string {
  if (!exercise) {
    return "No exercises planned.";
  }
  return `${exercise.name} · ${exercise.sets} sets · ${exercise.rep_range[0]}-${exercise.rep_range[1]} reps @ ${exercise.recommended_working_weight} kg`;
}

function formatSessionDate(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
}

function resolveSelectionReason(trace: Record<string, unknown> | undefined): string {
  const rationale = typeof trace?.rationale === "string" ? trace.rationale : null;
  const reason = typeof trace?.reason === "string" ? trace.reason : null;
  return resolveReasonText(rationale, reason);
}

function numberFromTrace(source: Record<string, unknown> | undefined, key: string): number | null {
  const value = source?.[key];
  return typeof value === "number" ? value : null;
}

function stringListFromUnknown(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string" && item.trim().length > 0) : [];
}

function WeekOverviewCards({ plan, selectedProgramId }: Readonly<{ plan: GeneratedWeekPlan; selectedProgramId: string | null }>) {
  const weeklyVolumeEntries = Object.entries(plan.weekly_volume_by_muscle ?? {})
    .sort((left, right) => right[1] - left[1])
    .slice(0, 4);
  const coveredMuscles = plan.muscle_coverage.covered_muscles ?? [];
  const underTarget = plan.muscle_coverage.under_target_muscles ?? [];
  const authoredBlockLabel = formatAuthoredBlockLabel(plan);
  const weakPointScheduled = hasWeakPointEmphasis(plan);

  return (
    <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
      <div className="main-card main-card--shell spacing-grid spacing-grid--tight">
        <p className="telemetry-kicker">Week Command Deck</p>
        <p className="telemetry-value">{getProgramDisplayName({ id: plan.program_template_id })}</p>
        <p className="telemetry-meta">
          Week {plan.mesocycle.week_index} · {plan.sessions.length} sessions · {formatLabel(plan.split)} split
        </p>
        <p className="telemetry-meta">
          Source: {selectedProgramId ? "Manual override" : "Server-selected recommendation"}
        </p>
        <p className="telemetry-meta">Missed day policy: {formatLabel(plan.missed_day_policy)}</p>
        {authoredBlockLabel ? <p className="telemetry-meta">{authoredBlockLabel}</p> : null}
        {weakPointScheduled ? <p className="text-xs text-zinc-200">Arms & Weak Points emphasis is scheduled this week.</p> : null}
      </div>

      <div className="main-card main-card--module main-card--accent spacing-grid spacing-grid--tight">
        <p className="telemetry-kicker">Mesocycle Posture</p>
        <p className="telemetry-value">
          {plan.deload.active ? "Deload Precision" : "Progressive Overload"}
        </p>
        <p className="telemetry-meta">
          Week {plan.mesocycle.week_index}/{plan.mesocycle.trigger_weeks_effective}
        </p>
        <p className="text-xs text-zinc-200">
          {plan.deload.active
            ? `Volume trims ${plan.deload.set_reduction_pct}% and load trims ${plan.deload.load_reduction_pct}% this week.`
            : "Run full-volume exposures and accumulate clean reps before the next review gate."}
        </p>
        <p className="telemetry-meta">Reason: {resolveReasonText(undefined, plan.mesocycle.deload_reason || plan.deload.reason)}</p>
      </div>

      <div className="main-card main-card--module spacing-grid spacing-grid--tight">
        <p className="telemetry-kicker">Coverage Radar</p>
        <p className="telemetry-value">
          {coveredMuscles.length} covered · {underTarget.length} under target
        </p>
        <p className="telemetry-meta">
          Minimum {plan.muscle_coverage.minimum_sets_per_muscle ?? 0} sets per muscle
        </p>
        <p className="text-xs text-zinc-200">
          {underTarget.length > 0 ? `Bring up ${underTarget.join(", ")}.` : "All tracked muscles clear the minimum set floor."}
        </p>
        <div className="space-y-1 text-xs text-zinc-300">
          {weeklyVolumeEntries.map(([muscle, sets]) => (
            <div key={`volume-${muscle}`} className="flex items-center justify-between rounded-md border border-white/10 bg-zinc-900/70 px-2 py-1">
              <span>{formatLabel(muscle)}</span>
              <span>{sets} sets</span>
            </div>
          ))}
        </div>
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
  const candidateIds = stringListFromUnknown(templateTrace.ordered_candidate_ids);
  const adaptiveReview = plan.adaptive_review;
  const frequencyAdaptation = plan.applied_frequency_adaptation;

  return (
    <div className="grid grid-cols-1 gap-3 xl:grid-cols-[1.3fr_1fr]">
      <div className="main-card main-card--module spacing-grid spacing-grid--tight">
        <p className="telemetry-kicker">Session Blueprint</p>
        <div className="space-y-2">
          {plan.sessions.map((session, index) => {
            const totalSets = session.exercises.reduce((sum, exercise) => sum + exercise.sets, 0);
            const dayRoleLabel = formatRoleLabel(session.day_role);
            const weakPointSlotCount = countSlotRole(session.exercises, "weak_point");
            return (
              <div key={session.session_id} className="rounded-md border border-white/10 bg-zinc-900/70 p-3 text-xs text-zinc-200">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold text-zinc-100">Day {index + 1}: {session.title}</p>
                    <p className="telemetry-meta">{formatSessionDate(session.date)} · {session.exercises.length} exercises · {totalSets} total sets</p>
                  </div>
                  <span className="rounded-full border border-white/10 bg-black/25 px-2 py-1 text-[10px] uppercase tracking-wide text-zinc-300">
                    {session.session_id}
                  </span>
                </div>
                <p className="mt-2">Lead slot: {formatLeadExercise(session.exercises[0])}</p>
                {dayRoleLabel ? <p className="telemetry-meta mt-1">Session intent: {dayRoleLabel}</p> : null}
                <p className="telemetry-meta mt-1">
                  Coverage: {uniqueMuscles(session.exercises).join(", ") || "Untracked"}
                </p>
                {weakPointSlotCount > 0 ? <p className="telemetry-meta mt-1">Weak-point slots: {weakPointSlotCount}</p> : null}
              </div>
            );
          })}
        </div>
      </div>

      <div className="space-y-3">
        <div className="main-card main-card--shell spacing-grid spacing-grid--tight">
          <p className="telemetry-kicker">Generation Read</p>
          <p className="text-xs text-zinc-200">{resolveSelectionReason(templateTrace)}</p>
          <div className="grid grid-cols-2 gap-2 text-xs text-zinc-300">
            <div className="rounded-md border border-white/10 bg-zinc-900/70 p-2">Effective days: {effectiveDays ?? plan.user.days_available}</div>
            <div className="rounded-md border border-white/10 bg-zinc-900/70 p-2">Prior generated weeks: {priorWeeks ?? 0}</div>
            <div className="rounded-md border border-white/10 bg-zinc-900/70 p-2">Latest adherence: {latestAdherence ?? "n/a"}</div>
            <div className="rounded-md border border-white/10 bg-zinc-900/70 p-2">Severe soreness flags: {severeSorenessCount ?? 0}</div>
          </div>
          {candidateIds.length > 0 ? <p className="telemetry-meta">Candidate stack: {candidateIds.join(" -> ")}</p> : null}
        </div>

        {adaptiveReview ? (
          <div className="main-card main-card--module spacing-grid spacing-grid--tight">
            <p className="telemetry-kicker">Adaptive Review Carryover</p>
            <p className="telemetry-value">{adaptiveReview.global_set_delta >= 0 ? "+" : ""}{adaptiveReview.global_set_delta} set bias</p>
            <p className="telemetry-meta">Load scale {formatSignedPercent(adaptiveReview.global_weight_scale)}</p>
            <p className="text-xs text-zinc-200">
              Weak-point slots: {adaptiveReview.weak_point_exercises.length > 0 ? adaptiveReview.weak_point_exercises.join(", ") : "none"}
            </p>
          </div>
        ) : null}

        {frequencyAdaptation ? (
          <div className="main-card main-card--module main-card--accent spacing-grid spacing-grid--tight">
            <p className="telemetry-kicker">Frequency Adaptation Runtime</p>
            <p className="telemetry-value">{frequencyAdaptation.target_days} day landing</p>
            <p className="telemetry-meta">
              {frequencyAdaptation.weeks_remaining_before_apply}{" -> "}{frequencyAdaptation.weeks_remaining_after_apply} weeks remaining
            </p>
            <p className="text-xs text-zinc-200">
              Weak areas preserved: {frequencyAdaptation.weak_areas.length > 0 ? frequencyAdaptation.weak_areas.join(", ") : "none"}
            </p>
          </div>
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

export default function WeekPage() {
  const [planStatus, setPlanStatus] = useState("Generate a weekly plan.");
  const [plan, setPlan] = useState<GeneratedWeekPlan | null>(null);
  const [programs, setPrograms] = useState<ProgramTemplateOption[]>([]);
  const [selectedProgramId, setSelectedProgramId] = useState<string | null>(null);

  const commandDeck = useMemo(() => {
    if (!plan) {
      return null;
    }
    const weeklyVolume = Object.values(plan.weekly_volume_by_muscle ?? {}).reduce((sum, value) => sum + value, 0);
    return {
      weeklyVolume,
      underTarget: plan.muscle_coverage.under_target_muscles ?? [],
      leadSession: plan.sessions[0] ?? null,
    };
  }, [plan]);
  const coachingContextNote = useMemo(() => buildWeekContextNote(plan), [plan]);

  async function generate() {
    try {
      const reviewStatus = await api.getWeeklyReviewStatus();
      if (reviewStatus.today_is_sunday && reviewStatus.review_required) {
        setPlan(null);
        setPlanStatus("Sunday review required. Open Check-In, submit weekly review, then generate the next week.");
        return;
      }
      const data = await api.generateWeek(selectedProgramId);
      setPlan(data);
      setPlanStatus(`Week generated for ${getProgramDisplayName({ id: data.program_template_id })}.`);
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Unknown error";
      setPlan(null);
      setPlanStatus(`Failed to generate week plan: ${detail}`);
    }
  }

  useEffect(() => {
    let mounted = true;
    api.listPrograms()
      .then((list) => { if (mounted) setPrograms(list); })
      .catch(() => {});
    return () => { mounted = false };
  }, []);

  return (
    <div className="space-y-4">
      <h1 className="ui-title-page">Week Plan</h1>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <div className="main-card main-card--shell">
          <p className="telemetry-kicker">Generator</p>
          <p className="telemetry-status">
            <span className="status-dot status-dot--green" /> Ready
          </p>
        </div>
        <div className="main-card main-card--module main-card--accent">
          <p className="telemetry-kicker">Program Source</p>
          <p className="telemetry-value">{selectedProgramId ? "Manual override" : "Auto-select"}</p>
        </div>
      </div>
      <div className="main-card main-card--module">
        <div className="spacing-grid spacing-grid--tight">
          <p className="telemetry-kicker">Generation Controls</p>
          <label htmlFor="week-program" className="ui-meta">Program override (optional)</label>
          <select id="week-program" aria-label="Week program override selector" aria-describedby="week-program-desc" className="ui-select" value={selectedProgramId ?? ""} onChange={(e) => setSelectedProgramId(e.target.value || null)}>
            <option value="">Server-selected — trainer&apos;s recommended program</option>
            {programs.map((p) => <option key={p.id} value={p.id}>{getProgramDisplayName(p)}</option>)}
          </select>
          <p id="week-program-desc" className="text-xs text-zinc-500">Select a program to override the server selection for this generated week.</p>
          <Button aria-label="Generate week plan" className="w-full" onClick={generate}>
            <span className="inline-flex items-center gap-2">
              <UiIcon name="plan" className="ui-icon--action" />
              Generate Week
            </span>
          </Button>
        </div>
      </div>
      <CoachingIntelligencePanel contextLabel="Week Plan" templateId={selectedProgramId} contextNote={coachingContextNote} />
      <div className="main-card main-card--shell spacing-grid spacing-grid--tight">
        <p className="telemetry-kicker">Planner Status</p>
        <p className="text-sm text-zinc-200">{planStatus}</p>
        {commandDeck ? (
          <div className="grid grid-cols-1 gap-2 md:grid-cols-3">
            <div className="rounded-md border border-white/10 bg-zinc-900/70 p-2 text-xs text-zinc-200">
              Weekly volume footprint: {commandDeck.weeklyVolume} sets
            </div>
            <div className="rounded-md border border-white/10 bg-zinc-900/70 p-2 text-xs text-zinc-200">
              Lead session: {commandDeck.leadSession?.title ?? "Not generated"}
            </div>
            <div className="rounded-md border border-white/10 bg-zinc-900/70 p-2 text-xs text-zinc-200">
              Focus gaps: {commandDeck.underTarget.length > 0 ? commandDeck.underTarget.map((muscle) => formatLabel(muscle)).join(", ") : "none"}
            </div>
          </div>
        ) : null}
      </div>

      {plan ? (
        <>
          <WeekOverviewCards plan={plan} selectedProgramId={selectedProgramId} />
          <WeekExecutionCards plan={plan} />
          <div className="main-card main-card--module spacing-grid spacing-grid--tight">
            <p className="telemetry-kicker">Plan Output</p>
            <pre className="overflow-x-auto text-xs text-zinc-200">{JSON.stringify(plan, null, 2)}</pre>
          </div>
        </>
      ) : null}
    </div>
  );
}
