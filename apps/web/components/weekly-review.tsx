"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import Link from "next/link";

import CoachingIntelligencePanel from "@/components/coaching-intelligence-panel";
import { Button } from "@/components/ui/button";
import { Disclosure } from "@/components/ui/disclosure";
import { UiIcon } from "@/components/ui/icons";
import { api, ApiError, getToken, type WeeklyReviewResponse, type WeeklyReviewStatus } from "@/lib/api";
import { useAppearance } from "@/components/appearance-provider";
import { canonicalLoad, displayLoad } from "@/lib/appearance";

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

export default function WeeklyReview() {
  const { preferences } = useAppearance();
  const unit = preferences.weight_unit;
  const [reviewStatus, setReviewStatus] = useState<WeeklyReviewStatus | null>(null);
  const [bodyWeight, setBodyWeight] = useState("");
  const weightKg = useRef<number | null>(null);
  const unitRef = useRef(unit);
  useEffect(() => { unitRef.current = unit; }, [unit]);
  const mountedRef = useRef(false);
  const loadedToken = useRef<string | null>(null);
  const saving = useRef(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveState, setSaveState] = useState<"idle" | "pending" | "uncertain" | "saved">("idle");
  const frozen = useRef<{ token: string | null; week: string; previouslySubmitted: boolean } | null>(null);
  const generating = useRef(false);
  const [generated, setGenerated] = useState(false);
  useEffect(() => { if (weightKg.current !== null) setBodyWeight(String(displayLoad(weightKg.current, unit))); }, [unit]);
  const [calories, setCalories] = useState("");
  const [protein, setProtein] = useState("");
  const [fat, setFat] = useState("");
  const [carbs, setCarbs] = useState("");
  const [adherenceScore, setAdherenceScore] = useState("");
  const [notes, setNotes] = useState("");
  const [sessionsNextWeek, setSessionsNextWeek] = useState("3");
  const [usesSelectedDates, setUsesSelectedDates] = useState(false);
  const [flexible, setFlexible] = useState(false);
  const [status, setStatus] = useState("Loading weekly review...");
  const [reviewResult, setReviewResult] = useState<WeeklyReviewResponse | null>(null);
  const [isGeneratingNextWeek, setIsGeneratingNextWeek] = useState(false);
  const [nextWeekGenerationStatus, setNextWeekGenerationStatus] = useState<string | null>(null);
  const statusTone = resolveStatusTone(status);

  useEffect(() => {
    let mounted = true; mountedRef.current = true;
    const token = getToken();
    api.getProfile()
      .then(async profile => {
        if (!mounted || token !== getToken()) return;
        if (profile.schedule_mode === "flexible") { setFlexible(true); return; }
        const weeklyStatus = await api.getWeeklyReviewStatus();
        if (!mounted || token !== getToken()) {
          return;
        }
        setReviewStatus(weeklyStatus);
        loadedToken.current = token;
        weightKg.current = profile.weight == null ? null : Number(profile.weight);
        setBodyWeight(weightKg.current === null ? "" : String(displayLoad(weightKg.current, unitRef.current)));
        setCalories(profile.calories == null ? "" : String(profile.calories));
        setProtein(profile.protein == null ? "" : String(profile.protein));
        setFat(profile.fat == null ? "" : String(profile.fat));
        setCarbs(profile.carbs == null ? "" : String(profile.carbs));
        setSessionsNextWeek(String(Math.max(2, Math.min(5, (profile.effective_days_available ?? profile.days_available) || 3))));
        setUsesSelectedDates(Boolean(profile.scheduling_timezone));
        setStatus(weeklyStatus.review_required ? "Weekly review available" : "Weekly review ready");
      })
      .catch(() => {
        if (!mounted || token !== getToken()) {
          return;
        }
        setStatus("Failed to load weekly review status");
      });

    return () => {
      mounted = false; mountedRef.current = false;
    };
  }, []);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const token = getToken();
    if (saving.current || saveState !== "idle" || !reviewStatus || token !== loadedToken.current) return;
    if (!bodyWeight.trim() || weightKg.current === null || weightKg.current <= 0 || !Number.isFinite(weightKg.current)) { setStatus("Enter your measured bodyweight before saving."); return; }
    if ([calories, protein, fat, carbs, adherenceScore].some(value => value.trim() === "")) {
      setStatus("Enter your chosen nutrition targets and report your actual adherence before saving a review. A review is optional for training.");
      return;
    }
    saving.current = true; setIsSaving(true);
    frozen.current = { token, week: reviewStatus.week_start, previouslySubmitted: reviewStatus.existing_review_submitted };
    setSaveState("pending");
    setStatus("Saving weekly review...");

    try {
      if (!reviewStatus) throw new Error("Weekly review status unavailable");
      const response = await api.submitWeeklyReview({
        week_start: reviewStatus.week_start,
        body_weight: weightKg.current,
        calories: Number(calories),
        protein: Number(protein),
        fat: Number(fat),
        carbs: Number(carbs),
        adherence_score: Number(adherenceScore),
        sessions_next_week: Number(sessionsNextWeek),
        notes: notes || undefined,
      });
      if (!mountedRef.current || token !== getToken()) return;
      setReviewResult(response);
      setSaveState("saved");
      setStatus("Weekly review saved");
      void api.getWeeklyReviewStatus().then(refreshed => {
        if (mountedRef.current && token === getToken()) setReviewStatus(refreshed);
      }).catch(() => { /* A failed refresh cannot undo the acknowledged save. */ });
      // Saving a report never activates a plan. Scheduling is an explicit action.
    } catch (error) {
      if (mountedRef.current && token === getToken()) {
        if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
          frozen.current = null; setSaveState("idle"); setStatus("Weekly review was not saved. Review your entries and retry.");
        } else { setSaveState("uncertain"); setStatus("Weekly review result unknown. Check the saved review before sending anything again."); }
      }
    } finally {
      saving.current = false;
      if (mountedRef.current && token === getToken()) setIsSaving(false);
    }
  }

  async function reconcileReview() {
    const command = frozen.current;
    if (!command || saving.current || command.token !== getToken()) return;
    saving.current = true; setIsSaving(true);
    try {
      const current = await api.getWeeklyReviewStatus();
      if (!mountedRef.current || command !== frozen.current || command.token !== getToken()) return;
      setReviewStatus(current);
      if (current.week_start === command.week && !command.previouslySubmitted && current.existing_review_submitted) {
        setSaveState("saved"); setStatus("A weekly review is now recorded; nothing was resent. Review History and Settings for the saved details.");
      } else setStatus("Weekly review result unknown. The current status cannot identify this save. Review History and Settings; nothing was resent.");
    } catch {
      if (mountedRef.current && command.token === getToken()) setStatus("Weekly review result unknown. Could not check saved status; try checking again.");
    } finally { saving.current = false; if (mountedRef.current && command.token === getToken()) setIsSaving(false); }
  }

  async function handleGenerateNextWeek() {
    const token = getToken();
    if (generating.current || generated || token !== loadedToken.current || saveState !== "saved") return;
    generating.current = true;
    setIsGeneratingNextWeek(true);
    setNextWeekGenerationStatus("Generating next week...");
    try {
      await api.generateNextWeek(null, Number(sessionsNextWeek));
      if (!mountedRef.current || token !== getToken()) return;
      setGenerated(true);
      setNextWeekGenerationStatus("Next week generated. Open Week Plan to continue.");
    } catch (error) {
      if (!mountedRef.current || token !== getToken()) return;
      const detail = error instanceof Error ? error.message : "Unknown error";
      setNextWeekGenerationStatus(`Failed to generate next week: ${detail}`);
    } finally {
      generating.current = false;
      if (mountedRef.current && token === getToken()) setIsGeneratingNextWeek(false);
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

  if (flexible) return <div className="space-y-3">
    <p>Calendar-based weekly review is unavailable for Flexible training. A source block can span weeks, so calendar completion percentages and dose adjustments would be misleading.</p>
    <p>Optional check-ins remain available. History shows actual performance and incomplete closures; your original prescriptions stay unchanged.</p>
    <Link href="/today" className="ux-button ux-button-secondary">Continue Flexible training</Link>
  </div>;

  return (
    <div className="space-y-4">
      <h2>Detailed weekly review</h2>
      <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 px-4 py-3">
        <p role="status" className="flex items-center gap-2 text-sm text-zinc-200">
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
      {reviewStatus?.existing_review_submitted && saveState === "idle" ? <p>A weekly review is already recorded. <Link href="/history">Check History</Link> before submitting another report.</p> : null}
      {saveState === "uncertain" ? <div className="space-y-2"><Button disabled={isSaving} onClick={() => void reconcileReview()}>Check saved review</Button><p><Link href="/history">Review History</Link> · <Link href="/settings">Review saved targets in Settings</Link></p></div> : null}

      <form className="space-y-4" onSubmit={handleSubmit}>
        <fieldset className="space-y-4" disabled={saveState !== "idle" || !reviewStatus}>
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4 space-y-3">
          <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">Body Metrics</p>
          <label className="flex flex-col gap-1 text-sm text-zinc-300">
            <span>Current Bodyweight ({unit})</span>
            <input className="ui-input" min="0.1" onChange={(event) => { setBodyWeight(event.target.value); weightKg.current = event.target.value.trim() ? canonicalLoad(Number(event.target.value), unit) : null; }} step="0.1" type="number" value={bodyWeight} />
          </label>
        </div>

        <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4 space-y-3">
          <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">Nutrition targets</p>
          <p className="ui-meta">These are your chosen goals for the upcoming week, not measured intake. Leave the review unsaved if you do not know them.</p>
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
            <select className="ui-select" required onChange={(event) => setAdherenceScore(event.target.value)} value={adherenceScore}>
              <option value="">Choose what actually happened</option>
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

        <Button disabled={isSaving || saveState !== "idle" || !reviewStatus} className="w-full min-h-[48px] text-sm font-semibold" type="submit">
          <span className="inline-flex items-center gap-2">
            <UiIcon name="review" className="ui-icon--action" />
            Save Weekly Review
          </span>
        </Button>
        </fieldset>
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
                <p>{fault.completed_sets}/{fault.planned_sets} sets · avg {fault.average_performed_reps} reps @ {displayLoad(fault.average_performed_weight, unit)} {unit}</p>
                <p>Target {fault.target_reps_min}-{fault.target_reps_max} reps @ {displayLoad(fault.target_weight, unit)} {unit}</p>
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
            {usesSelectedDates ? <Link href="/week" className="inline-flex min-h-[48px] w-full items-center justify-center rounded-md border border-zinc-700 text-sm">Schedule next week in Week</Link> : <Button className="w-full" disabled={isGeneratingNextWeek || generated} onClick={handleGenerateNextWeek} type="button">
              <span className="inline-flex items-center gap-2">
                <UiIcon name="plan" className="ui-icon--action" />
                {isGeneratingNextWeek ? "Generating Next Week..." : "Generate Next Week Now"}
              </span>
            </Button>}
            {nextWeekGenerationStatus ? <p className="text-xs text-zinc-400">{nextWeekGenerationStatus}</p> : null}
          </div>
        </Disclosure>
      ) : null}
    </div>
  );
}
