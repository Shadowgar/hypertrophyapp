"use client";

import { FormEvent, useEffect, useState } from "react";

import CoachingIntelligencePanel from "@/components/coaching-intelligence-panel";
import { Button } from "@/components/ui/button";
import { UiIcon } from "@/components/ui/icons";
import { api, type WeeklyReviewResponse, type WeeklyReviewStatus } from "@/lib/api";
import { kgToLbs } from "@/lib/weight";

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
        notes: notes || undefined,
      });
      setReviewResult(response);
      setStatus("Weekly review saved");
      const refreshedStatus = await api.getWeeklyReviewStatus();
      setReviewStatus(refreshedStatus);
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
      <div className="main-card main-card--module main-card--accent spacing-grid spacing-grid--tight">
        <div className="telemetry-header">
          <p className="telemetry-kicker">Review State</p>
          <p className="telemetry-status">
            <span className={`status-dot status-dot--${statusTone}`} /> {status}
          </p>
        </div>
        <p className="telemetry-meta">
          {reviewStatus?.today_is_sunday
            ? "Sunday flow active: review prior-week lifts and set nutrition for the upcoming week."
            : "You can still run the weekly review now to update the next planning cycle."}
        </p>
        {reviewStatus ? (
          <p className="telemetry-meta text-zinc-300">
            Target week: {reviewStatus.week_start} · Previous week: {reviewStatus.previous_week_start} → {reviewStatus.previous_week_end}
          </p>
        ) : null}
      </div>

      <CoachingIntelligencePanel contextLabel="Check-In" />

      <div className="grid gap-3 lg:grid-cols-2">
        <div className="main-card main-card--module spacing-grid spacing-grid--tight">
          <div className="telemetry-header">
            <div>
              <p className="telemetry-kicker">Review Command Center</p>
              <p className="telemetry-value">{readinessScore === null ? "Awaiting review result" : readinessScore}</p>
            </div>
            <span className="telemetry-status">
              <span className={`status-dot status-dot--${readinessTone}`} />
              {readinessScore === null ? "Pending" : readinessScore}
            </span>
          </div>
          {reviewGuidance ? (
            <p className="telemetry-meta text-zinc-300">{reviewGuidance}</p>
          ) : (
            <p className="telemetry-meta text-zinc-300">No review result recorded.</p>
          )}
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-md border border-zinc-800 bg-zinc-900/40 px-3 py-2">
              <p className="telemetry-kicker">Volume Shift</p>
              <p className="text-sm text-zinc-100">
                {reviewResult ? reviewResult.adjustments.global_set_delta : "Awaiting output"}
              </p>
            </div>
            <div className="rounded-md border border-zinc-800 bg-zinc-900/40 px-3 py-2">
              <p className="telemetry-kicker">Load Scale</p>
              <p className="text-sm text-zinc-100">
                {reviewResult ? reviewResult.adjustments.global_weight_scale : "Awaiting output"}
              </p>
            </div>
            <div className="rounded-md border border-zinc-800 bg-zinc-900/40 px-3 py-2">
              <p className="telemetry-kicker">Weak Point Targets</p>
              {weakPointExercises.length ? (
                <div className="space-y-1 text-sm text-zinc-100">
                  {weakPointExercises.map((exerciseId) => (
                    <p key={exerciseId}>{exerciseId}</p>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-zinc-100">None</p>
              )}
            </div>
            <div className="rounded-md border border-zinc-800 bg-zinc-900/40 px-3 py-2">
              <p className="telemetry-kicker">Fault Count</p>
              <p className="text-sm text-zinc-100">{previousSummary ? previousSummary.faulty_exercise_count : 0} flagged lifts</p>
            </div>
          </div>
        </div>

        <div className="main-card main-card--module spacing-grid spacing-grid--tight">
          <div className="telemetry-header">
            <div>
              <p className="telemetry-kicker">Nutrition Snapshot</p>
              <p className="telemetry-value">Next week fuel plan</p>
            </div>
            <p className="telemetry-meta">Adjust before saving if recovery or scale trend is off.</p>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-md border border-zinc-800 bg-zinc-900/40 px-3 py-2">
              <p className="telemetry-kicker">Calories</p>
              <p className="text-sm text-zinc-100">{calorieValue} kcal</p>
            </div>
            <div className="rounded-md border border-zinc-800 bg-zinc-900/40 px-3 py-2">
              <p className="telemetry-kicker">Protein</p>
              <p className="text-sm text-zinc-100">{proteinValue} g</p>
            </div>
            <div className="rounded-md border border-zinc-800 bg-zinc-900/40 px-3 py-2">
              <p className="telemetry-kicker">Fat</p>
              <p className="text-sm text-zinc-100">{fatValue} g</p>
            </div>
            <div className="rounded-md border border-zinc-800 bg-zinc-900/40 px-3 py-2">
              <p className="telemetry-kicker">Carbs</p>
              <p className="text-sm text-zinc-100">{carbsValue} g</p>
            </div>
          </div>
        </div>
      </div>

      {previousSummary ? (
        <div className="main-card main-card--module spacing-grid spacing-grid--tight">
          <p className="telemetry-kicker">Previous Week Lift Audit</p>
          <p className="telemetry-meta text-zinc-300">
            Completion: {previousSummary.completed_sets_total}/{previousSummary.planned_sets_total} sets ({previousSummary.completion_pct}%)
          </p>
          <p className="telemetry-meta text-zinc-300">Faulty exercises: {previousSummary.faulty_exercise_count}</p>
          <div className="space-y-2">
            {previousSummary.exercise_faults.slice(0, 5).map((fault) => (
              <div key={fault.primary_exercise_id} className="rounded-md border border-zinc-800 bg-zinc-900/40 p-2 text-xs text-zinc-300">
                <p className="font-semibold text-zinc-100">{fault.name}</p>
                <p className="text-[11px] uppercase tracking-wide text-zinc-500">{fault.fault_level} fault</p>
                <p>
                  {fault.completed_sets}/{fault.planned_sets} sets · avg {fault.average_performed_reps} reps @ {kgToLbs(fault.average_performed_weight)} lbs
                </p>
                <p>
                  Target {fault.target_reps_min}-{fault.target_reps_max} reps @ {kgToLbs(fault.target_weight)} lbs
                </p>
                {fault.guidance ? <p>{fault.guidance}</p> : null}
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <form className="main-card main-card--module spacing-grid" onSubmit={handleSubmit}>
        <p className="telemetry-kicker">Upcoming Week Targets</p>

        <label className="space-y-1 text-xs text-zinc-300">
          <span>Current Bodyweight</span>
          <input
            className="ui-input"
            min="0.1"
            onChange={(event) => setBodyWeight(event.target.value)}
            step="0.1"
            type="number"
            value={bodyWeight}
          />
        </label>

        <label className="space-y-1 text-xs text-zinc-300">
          <span>Daily Calories</span>
          <input
            className="ui-input"
            min="1"
            onChange={(event) => setCalories(event.target.value)}
            step="1"
            type="number"
            value={calories}
          />
        </label>

        <div className="grid grid-cols-3 gap-2">
          <label className="space-y-1 text-xs text-zinc-300">
            <span>Protein (g)</span>
            <input
              className="ui-input"
              min="1"
              onChange={(event) => setProtein(event.target.value)}
              step="1"
              type="number"
              value={protein}
            />
          </label>
          <label className="space-y-1 text-xs text-zinc-300">
            <span>Fat (g)</span>
            <input
              className="ui-input"
              min="1"
              onChange={(event) => setFat(event.target.value)}
              step="1"
              type="number"
              value={fat}
            />
          </label>
          <label className="space-y-1 text-xs text-zinc-300">
            <span>Carbs (g)</span>
            <input
              className="ui-input"
              min="1"
              onChange={(event) => setCarbs(event.target.value)}
              step="1"
              type="number"
              value={carbs}
            />
          </label>
        </div>

        <label className="space-y-1 text-xs text-zinc-300">
          <span>Adherence Score (1-5)</span>
          <select
            className="ui-select"
            onChange={(event) => setAdherenceScore(event.target.value)}
            value={adherenceScore}
          >
            <option value="1">1</option>
            <option value="2">2</option>
            <option value="3">3</option>
            <option value="4">4</option>
            <option value="5">5</option>
          </select>
        </label>

        <label className="space-y-1 text-xs text-zinc-300">
          <span>Notes (optional)</span>
          <textarea
            className="ui-textarea"
            onChange={(event) => setNotes(event.target.value)}
            rows={3}
            value={notes}
          />
        </label>

        <Button className="w-full" type="submit">
          <span className="inline-flex items-center gap-2">
            <UiIcon name="review" className="ui-icon--action" />
            Save Weekly Review
          </span>
        </Button>
      </form>

      {reviewResult ? (
        <div className="main-card main-card--module spacing-grid spacing-grid--tight">
          <p className="telemetry-kicker">Adaptive Output</p>
          <div className="space-y-1">
            <p className="telemetry-meta text-zinc-300">Readiness score</p>
            <p className="text-sm text-zinc-100">{reviewResult.readiness_score}</p>
          </div>
          {reviewGuidance ? <p className="telemetry-meta text-zinc-300">{reviewGuidance}</p> : null}
          <div className="space-y-1">
            <p className="telemetry-meta text-zinc-300">Weak points</p>
            {weakPointExercises.length ? (
              <div className="space-y-1 text-sm text-zinc-100">
                {weakPointExercises.map((exerciseId) => (
                  <p key={exerciseId}>{exerciseId}</p>
                ))}
              </div>
            ) : (
              <p className="telemetry-meta text-zinc-300">None</p>
            )}
          </div>
          <div className="space-y-2">
            {reviewResult.adjustments.exercise_overrides.slice(0, 5).map((item) => (
              <div key={item.primary_exercise_id} className="rounded-md border border-zinc-800 bg-zinc-900/40 p-2 text-xs text-zinc-300">
                <p className="font-semibold text-zinc-100">{item.primary_exercise_id}</p>
                <p>set_delta {item.set_delta}, weight_scale {item.weight_scale}</p>
                {item.rationale ? <p>{item.rationale}</p> : null}
              </div>
            ))}
          </div>
          <div className="space-y-2">
            <Button className="w-full" disabled={isGeneratingNextWeek} onClick={handleGenerateNextWeek} type="button">
              <span className="inline-flex items-center gap-2">
                <UiIcon name="plan" className="ui-icon--action" />
                {isGeneratingNextWeek ? "Generating Next Week..." : "Generate Next Week Now"}
              </span>
            </Button>
            {nextWeekGenerationStatus ? <p className="telemetry-meta text-zinc-300">{nextWeekGenerationStatus}</p> : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}
