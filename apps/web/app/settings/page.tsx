"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Disclosure } from "@/components/ui/disclosure";
import { UiIcon } from "@/components/ui/icons";
import {
  api,
  type FrequencyAdaptationResult,
  getProgramDisplayName,
  resolveReasonText,
  type IntelligenceCoachPreviewResponse,
  type Profile,
  type SorenessSeverity,
} from "@/lib/api";

const CANONICAL_PROGRAM_ID = "pure_bodybuilding_phase_1_full_body";
const CANONICAL_PROGRAM_NAME = "Pure Bodybuilding - Phase 1 Full Body";

function parseLaggingMuscles(raw: string): string[] {
  return raw
    .split(",")
    .map((item) => item.trim().toLowerCase())
    .filter((item) => item.length > 0);
}

export default function SettingsPage() {
  const router = useRouter();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [coachPreview, setCoachPreview] = useState<IntelligenceCoachPreviewResponse | null>(null);
  const [coachStatus, setCoachStatus] = useState<string | null>(null);
  const [adaptationPreview, setAdaptationPreview] = useState<FrequencyAdaptationResult | null>(null);
  const [adaptationStatus, setAdaptationStatus] = useState<string | null>(null);
  const [adaptationApplyStatus, setAdaptationApplyStatus] = useState<string | null>(null);
  const [adaptationApplyOutcome, setAdaptationApplyOutcome] = useState<"idle" | "success" | "failed">("idle");
  const [postApplyGenerateStatus, setPostApplyGenerateStatus] = useState<string | null>(null);
  const [isGeneratingPostApplyWeek, setIsGeneratingPostApplyWeek] = useState(false);
  const [previewFromDays, setPreviewFromDays] = useState<number>(5);
  const [previewToDays, setPreviewToDays] = useState<number>(3);
  const [previewDurationWeeks, setPreviewDurationWeeks] = useState<number>(4);
  const [previewPhase, setPreviewPhase] = useState<"accumulation" | "intensification" | "deload">("accumulation");
  const [previewSoreness, setPreviewSoreness] = useState<SorenessSeverity>("mild");
  const [previewLaggingMuscles, setPreviewLaggingMuscles] = useState<string>("biceps, shoulders");
  const [applyRecommendationId, setApplyRecommendationId] = useState<string>("");
  const [applyStatus, setApplyStatus] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    api.getProfile()
      .then((data) => {
        if (!mounted) return;
        setProfile(data);
        setPreviewFromDays(Math.max(2, Math.min(7, data.days_available || 5)));
        setPreviewToDays(Math.max(2, Math.min(7, Math.min(data.days_available || 5, 3))));
      })
      .catch(() => setProfile(null));

    return () => { mounted = false };
  }, []);

  async function generateCoachPreview() {
    setCoachStatus("Generating preview...");
    setAdaptationStatus(null);
    setApplyStatus(null);
    try {
      const payload = {
        template_id: CANONICAL_PROGRAM_ID,
        from_days: previewFromDays,
        to_days: previewToDays,
        completion_pct: 90,
        adherence_score: 4,
        soreness_level: previewSoreness,
        average_rpe: 8.5,
        current_phase: previewPhase,
        weeks_in_phase: 4,
        stagnation_weeks: 0,
        lagging_muscles: parseLaggingMuscles(previewLaggingMuscles),
        target_min_sets: 8,
      } as const;
      const preview = await api.coachPreview(payload);
      setCoachPreview(preview);
      setApplyRecommendationId(preview.recommendation_id);
      setCoachStatus("Preview ready");
    } catch {
      setCoachStatus("Preview failed");
    }
  }

  async function generateAdaptationPreview() {
    setAdaptationStatus("Generating frequency adaptation...");
    setAdaptationApplyStatus(null);
    setAdaptationApplyOutcome("idle");
    setPostApplyGenerateStatus(null);
    try {
      const preview = await api.previewFrequencyAdaptation({
        program_id: CANONICAL_PROGRAM_ID,
        target_days: previewToDays,
        duration_weeks: previewDurationWeeks,
        weak_areas: parseLaggingMuscles(previewLaggingMuscles),
      });
      setAdaptationPreview(preview);
      setAdaptationStatus("Frequency adaptation ready");
    } catch {
      setAdaptationStatus("Frequency adaptation failed");
    }
  }

  async function applyAdaptation() {
    setAdaptationApplyStatus("Applying frequency adaptation...");
    setAdaptationApplyOutcome("idle");
    setPostApplyGenerateStatus(null);
    try {
      const response = await api.applyFrequencyAdaptation({
        program_id: CANONICAL_PROGRAM_ID,
        target_days: previewToDays,
        duration_weeks: previewDurationWeeks,
        weak_areas: parseLaggingMuscles(previewLaggingMuscles),
      });
      setAdaptationApplyStatus(
        `Applied (${response.target_days}d for ${response.duration_weeks} weeks, ${response.weeks_remaining} remaining)`,
      );
      setAdaptationApplyOutcome("success");
    } catch {
      setAdaptationApplyStatus("Apply frequency adaptation failed");
      setAdaptationApplyOutcome("failed");
    }
  }

  async function generateWeekAfterAdaptation() {
    setIsGeneratingPostApplyWeek(true);
    setPostApplyGenerateStatus("Generating week from adapted state...");
    try {
      const generatedWeek = await api.generateWeek(CANONICAL_PROGRAM_ID);
      setPostApplyGenerateStatus(`Generated week for ${getProgramDisplayName({ id: generatedWeek.program_template_id })}.`);
    } catch {
      setPostApplyGenerateStatus("Generate week failed. Open Week Plan and retry.");
    } finally {
      setIsGeneratingPostApplyWeek(false);
    }
  }

  async function runApplyPhase(confirm: boolean) {
    const recommendationId = applyRecommendationId.trim();
    if (!recommendationId) {
      setApplyStatus("Generate a preview first");
      return;
    }

    setApplyStatus(confirm ? "Applying phase decision..." : "Checking phase decision...");
    try {
      const response = await api.applyPhaseDecision({ recommendation_id: recommendationId, confirm });
      const explanation = resolveReasonText(response.rationale, response.reason);
      setApplyStatus(explanation ? `Phase: ${response.status} (${explanation})` : `Phase: ${response.status}`);
    } catch {
      setApplyStatus("Phase apply failed");
    }
  }

  async function runApplySpecialization(confirm: boolean) {
    const recommendationId = applyRecommendationId.trim();
    if (!recommendationId) {
      setApplyStatus("Generate a preview first");
      return;
    }

    setApplyStatus(confirm ? "Applying specialization decision..." : "Checking specialization decision...");
    try {
      const response = await api.applySpecializationDecision({ recommendation_id: recommendationId, confirm });
      setApplyStatus(`Specialization: ${response.status} (focus ${response.focus_muscles.join(", ") || "none"})`);
    } catch {
      setApplyStatus("Specialization apply failed");
    }
  }

  async function wipeUserData() {
    const confirmed = globalThis.confirm("This will permanently wipe your current user account and all related data. Continue?");
    if (!confirmed) {
      return;
    }

    setStatus("Wiping account data...");
    try {
      await api.wipeProfileData();
      localStorage.removeItem("hypertrophy_token");
      setStatus("Data wiped. Redirecting to onboarding...");
      setTimeout(() => router.push("/onboarding"), 400);
    } catch {
      setStatus("Wipe failed");
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="ui-title-page">Settings</h1>

      <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4 space-y-2">
        <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">Program</p>
        <p className="text-sm font-semibold text-zinc-100">{CANONICAL_PROGRAM_NAME}</p>
        <p className="text-xs text-zinc-400">ID: {CANONICAL_PROGRAM_ID}</p>
        {profile?.selected_program_id && profile.selected_program_id !== CANONICAL_PROGRAM_ID ? (
          <p className="text-xs text-yellow-400/80">Alias: {profile.selected_program_id} → {CANONICAL_PROGRAM_ID}</p>
        ) : null}
      </div>

      <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4 space-y-2">
        <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">Profile</p>
        <div className="grid grid-cols-2 gap-2 text-sm text-zinc-200">
          <div>
            <p className="text-xs text-zinc-500">Training Location</p>
            <p>{profile?.training_location ?? "not set"}</p>
          </div>
          <div>
            <p className="text-xs text-zinc-500">Equipment</p>
            <p>{(profile?.equipment_profile ?? []).join(", ") || "not set"}</p>
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4 space-y-2">
        <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">Display</p>
        <p className="text-sm text-zinc-400">Theme is locked to dark for MVP.</p>
      </div>

      <Disclosure title="Coaching Preview" badge="power user" defaultOpen={false}>
        <div className="space-y-3 text-xs text-zinc-300">
          <div className="grid grid-cols-2 gap-2">
            <label htmlFor="preview-from-days" className="ui-meta">From Days</label>
            <input id="preview-from-days" className="ui-input" type="number" min={2} max={7} value={previewFromDays} onChange={(e) => setPreviewFromDays(Math.max(2, Math.min(7, Number(e.target.value) || 2)))} />
            <label htmlFor="preview-to-days" className="ui-meta">To Days</label>
            <input id="preview-to-days" className="ui-input" type="number" min={2} max={7} value={previewToDays} onChange={(e) => setPreviewToDays(Math.max(2, Math.min(7, Number(e.target.value) || 2)))} />
            <label htmlFor="preview-phase" className="ui-meta">Current Phase</label>
            <select id="preview-phase" className="ui-select" value={previewPhase} onChange={(e) => setPreviewPhase(e.target.value as "accumulation" | "intensification" | "deload")}>
              <option value="accumulation">Accumulation</option>
              <option value="intensification">Intensification</option>
              <option value="deload">Deload</option>
            </select>
            <label htmlFor="preview-soreness" className="ui-meta">Soreness</label>
            <select id="preview-soreness" className="ui-select" value={previewSoreness} onChange={(e) => setPreviewSoreness(e.target.value as SorenessSeverity)}>
              <option value="none">None</option>
              <option value="mild">Mild</option>
              <option value="moderate">Moderate</option>
              <option value="severe">Severe</option>
            </select>
          </div>
          <label htmlFor="preview-lagging" className="ui-meta">Lagging Muscles (comma-separated)</label>
          <input id="preview-lagging" className="ui-input" value={previewLaggingMuscles} onChange={(e) => setPreviewLaggingMuscles(e.target.value)} />
          <label htmlFor="preview-duration" className="ui-meta">Temporary Duration (weeks)</label>
          <input id="preview-duration" className="ui-input" type="number" min={1} max={12} value={previewDurationWeeks} onChange={(e) => setPreviewDurationWeeks(Math.max(1, Math.min(12, Number(e.target.value) || 1)))} />
          <Button aria-label="Generate coaching preview" variant="secondary" className="w-full" onClick={generateCoachPreview}>Generate Coaching Preview</Button>
          {coachStatus ? <p className="text-xs text-zinc-400">{coachStatus}</p> : null}
          {coachPreview ? (
            <div className="rounded-md border border-zinc-800 p-2 space-y-1">
              <p>Program: {coachPreview.program_name}</p>
              <p className="flex items-center gap-2">Recommendation ID: <code className="rounded bg-zinc-800 px-1.5 py-0.5 text-[11px] text-zinc-300 select-all">{coachPreview.recommendation_id}</code></p>
              <p>Progression: {coachPreview.progression.action}</p>
              {resolveReasonText(coachPreview.progression.rationale, coachPreview.progression.reason) ? (
                <p>{resolveReasonText(coachPreview.progression.rationale, coachPreview.progression.reason)}</p>
              ) : null}
              <p>Phase: {coachPreview.phase_transition.next_phase}</p>
              {coachPreview.phase_transition.transition_pending ? (
                <div className="mt-1 rounded-md border border-zinc-700/80 bg-zinc-950/50 p-2">
                  <p className="font-medium text-zinc-100">Program Transition</p>
                  {coachPreview.phase_transition.recommended_action ? <p>Action: {coachPreview.phase_transition.recommended_action}</p> : null}
                  {resolveReasonText(coachPreview.phase_transition.rationale, coachPreview.phase_transition.reason) ? (
                    <p>{resolveReasonText(coachPreview.phase_transition.rationale, coachPreview.phase_transition.reason)}</p>
                  ) : null}
                </div>
              ) : null}
              <p>Risk: {coachPreview.schedule.risk_level} · Focus: {coachPreview.specialization.focus_muscles.join(", ") || "none"}</p>
            </div>
          ) : null}
          <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
            <Button aria-label="Generate frequency adaptation preview" variant="secondary" className="w-full" onClick={generateAdaptationPreview}>Adaptation Preview</Button>
            <Button aria-label="Apply frequency adaptation" variant="secondary" className="w-full" onClick={applyAdaptation}>Apply Adaptation</Button>
          </div>
          {adaptationStatus ? <p className="text-xs text-zinc-400">{adaptationStatus}</p> : null}
          {adaptationApplyStatus ? <p className="text-xs text-zinc-400">{adaptationApplyStatus}</p> : null}
          {adaptationApplyOutcome === "success" ? (
            <div className="rounded-md border border-zinc-800 p-2 space-y-2">
              <Button aria-label="Generate Week Now" variant="secondary" className="w-full" onClick={generateWeekAfterAdaptation} disabled={isGeneratingPostApplyWeek}>
                {isGeneratingPostApplyWeek ? "Generating Week..." : "Generate Week Now"}
              </Button>
              {postApplyGenerateStatus ? <p className="text-xs text-zinc-400">{postApplyGenerateStatus}</p> : null}
            </div>
          ) : null}
          {adaptationPreview ? (
            <div className="rounded-md border border-zinc-800 p-2 space-y-1">
              <p>Adaptation: {adaptationPreview.from_days}d → {adaptationPreview.to_days}d · {adaptationPreview.duration_weeks} week(s)</p>
              <p>Weak Areas: {adaptationPreview.weak_areas.join(", ") || "none"}</p>
            </div>
          ) : null}
        </div>
      </Disclosure>

      <Disclosure title="Apply Coaching Decision" defaultOpen={false}>
        <div className="space-y-2 text-xs text-zinc-300">
          <p className="flex items-center gap-2">Recommendation ID: <code className="rounded bg-zinc-800 px-1.5 py-0.5 text-[11px] text-zinc-300 select-all">{applyRecommendationId || "Generate preview first"}</code></p>
          <p className="text-zinc-400">Check = preview only. Apply = save recommendation and submit via Check-In.</p>
          <div className="grid grid-cols-2 gap-2">
            <Button aria-label="Check phase decision" variant="secondary" onClick={() => runApplyPhase(false)} disabled={!applyRecommendationId.trim()}>Check Phase</Button>
            <Button aria-label="Apply phase decision" variant="secondary" onClick={() => runApplyPhase(true)} disabled={!applyRecommendationId.trim()}>Apply Phase</Button>
            <Button aria-label="Check specialization decision" variant="secondary" onClick={() => runApplySpecialization(false)} disabled={!applyRecommendationId.trim()}>Check Specialization</Button>
            <Button aria-label="Apply specialization decision" variant="secondary" onClick={() => runApplySpecialization(true)} disabled={!applyRecommendationId.trim()}>Apply Specialization</Button>
          </div>
          {applyStatus ? <p className="text-xs text-zinc-400">{applyStatus}</p> : null}
          {applyStatus?.toLowerCase().includes("phase: applied") ? (
            <Link href="/checkin" className="mt-1 inline-flex items-center gap-2 rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 hover:bg-zinc-800">
              <UiIcon name="body" className="ui-icon--action" />
              Go to Check-In
            </Link>
          ) : null}
        </div>
      </Disclosure>

      <div className="rounded-lg border border-red-700/40 bg-red-950/20 p-4 space-y-3">
        <p className="text-xs font-medium uppercase tracking-wide text-red-400/80">Developer Tools</p>
        <p className="text-xs text-zinc-400">Wipe your current user and retest onboarding from scratch.</p>
        <Button className="w-full" variant="secondary" onClick={wipeUserData}>
          <span className="inline-flex items-center gap-2">
            <UiIcon name="reset" className="ui-icon--action" />
            Wipe Current User Data
          </span>
        </Button>
        {status ? <p className="text-xs text-zinc-400">{status}</p> : null}
      </div>

      <p className="text-center text-[10px] text-zinc-600">
        {process.env.NEXT_PUBLIC_APP_VERSION ?? "dev"}
      </p>
    </div>
  );
}
