"use client";

import { FormEvent, useEffect, useState } from "react";

import CoachingIntelligencePanel from "@/components/coaching-intelligence-panel";
import { Button } from "@/components/ui/button";
import { Disclosure } from "@/components/ui/disclosure";
import { UiIcon } from "@/components/ui/icons";
import { api, type WeeklyReviewResponse, type WeeklyReviewStatus } from "@/lib/api";
import { kgToLbs } from "@/lib/weight";

const ADHERENCE_LABELS: Record<string, string> = {
  "1": "Missed most sessions",
  "2": "Hit about a quarter",
  "3": "Hit about half",
  "4": "Hit most sessions",
  "5": "Hit every session",
};

function resolveStatusTone(status: string): "green" | "yellow" | "red" {
  const lowered = status.toLowerCase();
  if (lowered.includes("saved")) {
    return "green";
  }
  if (lowered.includes("failed")) {
    return "red";
  }
  return "yellow";
}

function resolveReadinessTone(score: number | null): "green" | "yellow" | "red" {
  if (score === null) {
    return "yellow";
  }
  if (score >= 75) {
    return "green";
  }
  if (score >= 55) {
    return "yellow";
  }
  return "red";
}

export default function CheckinPage() {
  const [reviewStatus, setReviewStatus] = useState<WeeklyReviewStatus | null>(null);
  const [bodyWeight, setBodyWeight] = useState("0");
  const [calories, setCalories] = useState("0");
  const [protein, setProtein] = useState("0");
  const [fat, setFat] = useState("0");
  const [carbs, setCarbs] = useState("0");
  const [adherenceScore, setAdherenceScore] = useState("4");
  const [notes, setNotes] = useState("");
  const [sessionsNextWeek, setSessionsNextWeek] = useState("3");
  const [status, setStatus] = useState("Loading weekly review...");
  const [reviewResult, setReviewResult] = useState<WeeklyReviewResponse | null>(null);
  const [isGeneratingNextWeek, setIsGeneratingNextWeek] = useState(false);
  const [nextWeekGenerationStatus, setNextWeekGenerationStatus] = useState<string | null>(null);
  const statusTone = resolveStatusTone(status);

  useEffect(() => {
    let mounted = true;
    Promise.all([api.getWeeklyReviewStatus(), api.getProfile()])
      .then(([weeklyStatus, profile]) => {
        if (!mounted) {
          return;
        }
        setReviewStatus(weeklyStatus);
        setBodyWeight(String(profile.weight || 0));
        setCalories(String(profile.calories || 0));
        setProtein(String(profile.protein || 0));
        setFat(String(profile.fat || 0));
        setCarbs(String(profile.carbs || 0));
        setSessionsNextWeek(String(Math.max(2, Math.min(5, profile.days_available || 3))));
        setStatus(weeklyStatus.review_required ? "Sunday review required" : "Weekly review ready");
      })
      .catch(() => {
        if (!mounted) {
          return;
        }
        setStatus("Failed to load weekly review status");
      });

    return () => {
      mounted = false;
    };
  }, []);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setStatus("Running Sunday review...");

    try {
      const response = await api.submitWeeklyReview({
        body_weight: Number(bodyWeight),
        calories: Number(calories),
        protein: Number(protein),
        fat: Number(fat),
        carbs: Number(carbs),
        adherence_score: Number(adherenceScore),
        sessions_next_week: Number(sessionsNextWeek),
        notes: notes || undefined,
      });
      setReviewResult(response);
      setStatus("Weekly review saved");
      const refreshedStatus = await api.getWeeklyReviewStatus();
      setReviewStatus(refreshedStatus);
      await handleGenerateNextWeek();
    } catch {
      setStatus("Weekly review failed. Verify your inputs and retry.");
    }
  }

  async function handleGenerateNextWeek() {
    setIsGeneratingNextWeek(true);
    setNextWeekGenerationStatus("Generating next week...");
    try {
      await api.generateWeek();
      setNextWeekGenerationStatus("Next week generated. Open Week Plan to continue.");
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Unknown error";
      setNextWeekGenerationStatus(`Failed to generate next week: ${detail}`);
    } finally {
      setIsGeneratingNextWeek(false);
    }
  }

  const previousSummary = reviewResult?.summary ?? reviewStatus?.previous_week_summary ?? null;
  const readinessScore = reviewResult?.readiness_score ?? null;
  const readinessTone = resolveReadinessTone(readinessScore);
  const reviewGuidance = reviewResult?.global_guidance?.trim() || null;
  const weakPointExercises = reviewResult?.adjustments.weak_point_exercises ?? [];
  const calorieValue = Number(calories || 0);
  const proteinValue = Number(protein || 0);
  const fatValue = Number(fat || 0);
  const carbsValue = Number(carbs || 0);

  return (
    <div className="space-y-4">
      <h1 className="ui-title-page">Sunday Review</h1>
      <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 px-4 py-3">
        <p className="flex items-center gap-2 text-sm text-zinc-200">
          <span className={`status-dot status-dot--${statusTone}`} /> {status}
        </p>
        <p className="mt-1 text-xs text-zinc-400">
          {reviewStatus?.today_is_sunday
            ? "Sunday flow active: review prior-week lifts and set nutrition for the upcoming week."
            : "You can still run the weekly review now to update the next planning cycle."}
        </p>
        {reviewStatus ? (
          <p className="mt-1 text-xs text-zinc-500">
            Target week: {reviewStatus.week_start} · Previous: {reviewStatus.previous_week_start} → {reviewStatus.previous_week_end}
          </p>
        ) : null}
      </div>

      <form className="space-y-4" onSubmit={handleSubmit}>
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4 space-y-3">
          <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">Body Metrics</p>
          <label className="flex flex-col gap-1 text-sm text-zinc-300">
            <span>Current Bodyweight</span>
            <input className="ui-input" min="0.1" onChange={(event) => setBodyWeight(event.target.value)} step="0.1" type="number" value={bodyWeight} />
          </label>
        </div>

        <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4 space-y-3">
          <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">Nutrition</p>
          <label className="flex flex-col gap-1 text-sm text-zinc-300">
            <span>Daily Calories</span>
            <input className="ui-input" min="1" onChange={(event) => setCalories(event.target.value)} step="1" type="number" value={calories} />
          </label>
          <div className="grid grid-cols-3 gap-2">
            <label className="flex flex-col gap-1 text-sm text-zinc-300">
              <span>Protein (g)</span>
              <input className="ui-input" min="1" onChange={(event) => setProtein(event.target.value)} step="1" type="number" value={protein} />
            </label>
            <label className="flex flex-col gap-1 text-sm text-zinc-300">
              <span>Fat (g)</span>
              <input className="ui-input" min="1" onChange={(event) => setFat(event.target.value)} step="1" type="number" value={fat} />
            </label>
            <label className="flex flex-col gap-1 text-sm text-zinc-300">
              <span>Carbs (g)</span>
              <input className="ui-input" min="1" onChange={(event) => setCarbs(event.target.value)} step="1" type="number" value={carbs} />
            </label>
          </div>
        </div>

        <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4 space-y-3">
          <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">Recovery</p>
          <label className="flex flex-col gap-1 text-sm text-zinc-300">
            <span>Sessions next week (2-5)</span>
            <select className="ui-select" onChange={(event) => setSessionsNextWeek(event.target.value)} value={sessionsNextWeek}>
              {["2", "3", "4", "5"].map((val) => (
                <option key={val} value={val}>{val}</option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm text-zinc-300">
            <span>Adherence Score (1-5)</span>
            <select className="ui-select" onChange={(event) => setAdherenceScore(event.target.value)} value={adherenceScore}>
              {["1", "2", "3", "4", "5"].map((val) => (
                <option key={val} value={val}>{val} — {ADHERENCE_LABELS[val]}</option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm text-zinc-300">
            <span>Notes (optional)</span>
            <textarea className="ui-textarea" onChange={(event) => setNotes(event.target.value)} rows={3} value={notes} />
          </label>
        </div>

        <Button className="w-full min-h-[48px] text-sm font-semibold" type="submit">
          <span className="inline-flex items-center gap-2">
            <UiIcon name="review" className="ui-icon--action" />
            Save Weekly Review
          </span>
        </Button>
      </form>

      {previousSummary ? (
        <Disclosure title="Previous Week Lift Audit" badge={`${previousSummary.completion_pct}% complete`} defaultOpen={false}>
          <div className="space-y-2">
            <p className="text-xs text-zinc-400">
              {previousSummary.completed_sets_total}/{previousSummary.planned_sets_total} sets · {previousSummary.faulty_exercise_count} flagged
            </p>
            {previousSummary.exercise_faults.slice(0, 5).map((fault) => (
              <div key={fault.primary_exercise_id} className="rounded-md border border-zinc-800 bg-zinc-900/40 p-2 text-xs text-zinc-300">
                <p className="font-semibold text-zinc-100">{fault.name}</p>
                <p className="text-[11px] uppercase tracking-wide text-zinc-500">{fault.fault_level} fault</p>
                <p>{fault.completed_sets}/{fault.planned_sets} sets · avg {fault.average_performed_reps} reps @ {kgToLbs(fault.average_performed_weight)} lbs</p>
                <p>Target {fault.target_reps_min}-{fault.target_reps_max} reps @ {kgToLbs(fault.target_weight)} lbs</p>
                {fault.guidance ? <p>{fault.guidance}</p> : null}
              </div>
            ))}
          </div>
        </Disclosure>
      ) : null}

      <Disclosure title="Coaching Preview" defaultOpen={false}>
        <CoachingIntelligencePanel contextLabel="Check-In" />
      </Disclosure>

      {reviewResult ? (
        <Disclosure title="Adaptation Results" badge={`Readiness: ${reviewResult.readiness_score}`} defaultOpen>
          <div className="space-y-3">
            {reviewGuidance ? <p className="text-sm text-zinc-200">{reviewGuidance}</p> : null}
            <div className="grid grid-cols-2 gap-2">
              <div className="rounded-md border border-zinc-800 bg-zinc-900/40 px-3 py-2">
                <p className="text-[10px] uppercase tracking-wide text-zinc-500">Volume Shift</p>
                <p className="text-sm font-semibold text-zinc-100">{reviewResult.adjustments.global_set_delta}</p>
              </div>
              <div className="rounded-md border border-zinc-800 bg-zinc-900/40 px-3 py-2">
                <p className="text-[10px] uppercase tracking-wide text-zinc-500">Load Scale</p>
                <p className="text-sm font-semibold text-zinc-100">{reviewResult.adjustments.global_weight_scale}</p>
              </div>
            </div>
            {weakPointExercises.length > 0 ? (
              <div>
                <p className="text-xs text-zinc-400">Weak points: {weakPointExercises.join(", ")}</p>
              </div>
            ) : null}
            {reviewResult.adjustments.exercise_overrides.slice(0, 5).map((item) => (
              <div key={item.primary_exercise_id} className="rounded-md border border-zinc-800 bg-zinc-900/40 p-2 text-xs text-zinc-300">
                <p className="font-semibold text-zinc-100">{item.primary_exercise_id}</p>
                <p>Set delta: {item.set_delta} · Weight scale: {item.weight_scale}</p>
                {item.rationale ? <p>{item.rationale}</p> : null}
              </div>
            ))}
            <Button className="w-full" disabled={isGeneratingNextWeek} onClick={handleGenerateNextWeek} type="button">
              <span className="inline-flex items-center gap-2">
                <UiIcon name="plan" className="ui-icon--action" />
                {isGeneratingNextWeek ? "Generating Next Week..." : "Generate Next Week Now"}
              </span>
            </Button>
            {nextWeekGenerationStatus ? <p className="text-xs text-zinc-400">{nextWeekGenerationStatus}</p> : null}
          </div>
        </Disclosure>
      ) : null}
    </div>
  );
}
