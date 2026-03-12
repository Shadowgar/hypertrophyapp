"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { UiIcon } from "@/components/ui/icons";
import {
  api,
  type FrequencyAdaptationResult,
  getProgramDisplayName,
  resolveReasonText,
  type IntelligenceCoachPreviewResponse,
  type Profile,
  type ProgramRecommendation,
  type ProgramTemplateOption,
  type SorenessSeverity,
} from "@/lib/api";

function parseLaggingMuscles(raw: string): string[] {
  return raw
    .split(",")
    .map((item) => item.trim().toLowerCase())
    .filter((item) => item.length > 0);
}

export default function SettingsPage() {
  const router = useRouter();
  const [theme] = useState("dark");
  const [profile, setProfile] = useState<Profile | null>(null);
  const [programs, setPrograms] = useState<ProgramTemplateOption[]>([]);
  const [selectedProgramId, setSelectedProgramId] = useState<string | null>(null);
  const [recommendation, setRecommendation] = useState<ProgramRecommendation | null>(null);
  const [pendingSwitch, setPendingSwitch] = useState<{ targetProgramId: string; rationale: string } | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [coachPreview, setCoachPreview] = useState<IntelligenceCoachPreviewResponse | null>(null);
  const [coachStatus, setCoachStatus] = useState<string | null>(null);
  const [adaptationPreview, setAdaptationPreview] = useState<FrequencyAdaptationResult | null>(null);
  const [adaptationStatus, setAdaptationStatus] = useState<string | null>(null);
  const [adaptationApplyStatus, setAdaptationApplyStatus] = useState<string | null>(null);
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
        setSelectedProgramId(data.selected_program_id ?? null);
        setPreviewFromDays(Math.max(2, Math.min(7, data.days_available || 5)));
        setPreviewToDays(Math.max(2, Math.min(7, Math.min(data.days_available || 5, 3))));
      })
      .catch(() => setProfile(null));

    api.listPrograms()
      .then((list) => {
        if (!mounted) return;
        setPrograms(list);
      })
      .catch(() => {});

    api.getProgramRecommendation()
      .then((data) => {
        if (!mounted) return;
        setRecommendation(data);
      })
      .catch(() => {});

    return () => { mounted = false };
  }, []);

  async function saveProgram() {
    if (!profile) return;
    if (!selectedProgramId) {
      setStatus("Choose a program first");
      setTimeout(() => setStatus(null), 2000);
      return;
    }

    if (selectedProgramId === (profile.selected_program_id ?? null)) {
      setStatus("Already selected");
      setPendingSwitch(null);
      setTimeout(() => setStatus(null), 1500);
      return;
    }

    setStatus("Saving...");
    try {
      const response = await api.switchProgram({ target_program_id: selectedProgramId, confirm: false });
      if (response.requires_confirmation) {
        setPendingSwitch({
          targetProgramId: selectedProgramId,
          rationale: resolveReasonText(response.rationale, response.reason) ?? response.reason,
        });
        setStatus("Confirm program switch");
      } else if (response.applied) {
        const updated = await api.getProfile();
        setProfile(updated);
        setPendingSwitch(null);
        setStatus("Saved");
      } else {
        setPendingSwitch(null);
        setStatus("No change");
      }
    } catch {
      setStatus("Save failed");
    }
    setTimeout(() => setStatus(null), 2000);
  }

  async function generateCoachPreview() {
    setCoachStatus("Generating preview...");
    setAdaptationStatus(null);
    setApplyStatus(null);
    try {
      const payload = {
        template_id: selectedProgramId,
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
    try {
      const preview = await api.previewFrequencyAdaptation({
        program_id: selectedProgramId,
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
    try {
      const response = await api.applyFrequencyAdaptation({
        program_id: selectedProgramId,
        target_days: previewToDays,
        duration_weeks: previewDurationWeeks,
        weak_areas: parseLaggingMuscles(previewLaggingMuscles),
      });
      setAdaptationApplyStatus(
        `Applied (${response.target_days}d for ${response.duration_weeks} weeks, ${response.weeks_remaining} remaining)`,
      );
    } catch {
      setAdaptationApplyStatus("Apply frequency adaptation failed");
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

  async function confirmProgramSwitch() {
    if (!pendingSwitch) return;
    setStatus("Applying switch...");
    try {
      const response = await api.switchProgram({
        target_program_id: pendingSwitch.targetProgramId,
        confirm: true,
      });
      if (response.applied) {
        const updated = await api.getProfile();
        setProfile(updated);
        const recommendationUpdated = await api.getProgramRecommendation();
        setRecommendation(recommendationUpdated);
        setStatus("Program switched");
      } else {
        setStatus("No change");
      }
      setPendingSwitch(null);
    } catch {
      setStatus("Switch failed");
    }
    setTimeout(() => setStatus(null), 2000);
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
      <div className="grid grid-cols-2 gap-3">
        <div className="main-card main-card--shell">
          <p className="telemetry-kicker">Profile Link</p>
          <p className="telemetry-status">
            <span className="status-dot status-dot--green" /> Connected
          </p>
        </div>
        <div className="main-card main-card--module main-card--accent">
          <p className="telemetry-kicker">Config Scope</p>
          <p className="telemetry-value">Program + recovery</p>
        </div>
      </div>
      <div className="main-card main-card--module spacing-grid">
        <p className="telemetry-kicker">Program Intelligence</p>
        <div className="rounded-md border border-zinc-800 p-3 text-xs text-zinc-300">
          <p>
            Recommended Program: {recommendation ? getProgramDisplayName({ id: recommendation.recommended_program_id }) : "not available"}
          </p>
          {recommendation && resolveReasonText(recommendation.rationale, recommendation.reason) ? (
            <p>
              Reason: {resolveReasonText(recommendation.rationale, recommendation.reason)}
            </p>
          ) : null}
        </div>

        <div className="rounded-md border border-zinc-800 p-3 text-xs text-zinc-300 space-y-2">
          <p className="telemetry-kicker">Coaching Preview</p>
          <div className="grid grid-cols-2 gap-2">
            <label htmlFor="preview-from-days" className="ui-meta">From Days</label>
            <input
              id="preview-from-days"
              className="ui-input"
              type="number"
              min={2}
              max={7}
              value={previewFromDays}
              onChange={(e) => setPreviewFromDays(Math.max(2, Math.min(7, Number(e.target.value) || 2)))}
            />
            <label htmlFor="preview-to-days" className="ui-meta">To Days</label>
            <input
              id="preview-to-days"
              className="ui-input"
              type="number"
              min={2}
              max={7}
              value={previewToDays}
              onChange={(e) => setPreviewToDays(Math.max(2, Math.min(7, Number(e.target.value) || 2)))}
            />
            <label htmlFor="preview-phase" className="ui-meta">Current Phase</label>
            <select
              id="preview-phase"
              className="ui-select"
              value={previewPhase}
              onChange={(e) => setPreviewPhase(e.target.value as "accumulation" | "intensification" | "deload")}
            >
              <option value="accumulation">Accumulation</option>
              <option value="intensification">Intensification</option>
              <option value="deload">Deload</option>
            </select>
            <label htmlFor="preview-soreness" className="ui-meta">Soreness</label>
            <select
              id="preview-soreness"
              className="ui-select"
              value={previewSoreness}
              onChange={(e) => setPreviewSoreness(e.target.value as SorenessSeverity)}
            >
              <option value="none">None</option>
              <option value="mild">Mild</option>
              <option value="moderate">Moderate</option>
              <option value="severe">Severe</option>
            </select>
          </div>
          <label htmlFor="preview-lagging" className="ui-meta">Lagging Muscles (comma-separated)</label>
          <input
            id="preview-lagging"
            className="ui-input"
            value={previewLaggingMuscles}
            onChange={(e) => setPreviewLaggingMuscles(e.target.value)}
          />
          <label htmlFor="preview-duration" className="ui-meta">Temporary Duration (weeks)</label>
          <input
            id="preview-duration"
            className="ui-input"
            type="number"
            min={1}
            max={12}
            value={previewDurationWeeks}
            onChange={(e) => setPreviewDurationWeeks(Math.max(1, Math.min(12, Number(e.target.value) || 1)))}
          />
          <Button aria-label="Generate coaching preview" variant="secondary" className="w-full" onClick={generateCoachPreview}>
            Generate Coaching Preview
          </Button>
          <p className="telemetry-meta">{coachStatus ?? ""}</p>
          {coachPreview ? (
            <div className="rounded-md border border-zinc-800 p-2">
              <p>Program: {coachPreview.program_name}</p>
              <p>Recommendation ID: {coachPreview.recommendation_id}</p>
              <p>Progression: {coachPreview.progression.action}</p>
              {resolveReasonText(coachPreview.progression.rationale, coachPreview.progression.reason) ? (
                <p>{resolveReasonText(coachPreview.progression.rationale, coachPreview.progression.reason)}</p>
              ) : null}
              <p>Phase Recommendation: {coachPreview.phase_transition.next_phase}</p>
              {!coachPreview.phase_transition.transition_pending && resolveReasonText(coachPreview.phase_transition.rationale, coachPreview.phase_transition.reason) ? (
                <p>{resolveReasonText(coachPreview.phase_transition.rationale, coachPreview.phase_transition.reason)}</p>
              ) : null}
              {coachPreview.phase_transition.transition_pending ? (
                <div className="mt-2 rounded-md border border-zinc-700/80 bg-zinc-950/50 p-2">
                  <p className="font-medium text-zinc-100">Program Transition</p>
                  {coachPreview.phase_transition.recommended_action ? (
                    <p>Recommended action: {coachPreview.phase_transition.recommended_action}</p>
                  ) : null}
                  {coachPreview.phase_transition.post_authored_behavior ? (
                    <p>Post-authored behavior: {coachPreview.phase_transition.post_authored_behavior}</p>
                  ) : null}
                  {resolveReasonText(coachPreview.phase_transition.rationale, coachPreview.phase_transition.reason) ? (
                    <p>{resolveReasonText(coachPreview.phase_transition.rationale, coachPreview.phase_transition.reason)}</p>
                  ) : null}
                </div>
              ) : null}
              <p>Adaptation Risk: {coachPreview.schedule.risk_level}</p>
              <p>Focus Muscles: {coachPreview.specialization.focus_muscles.join(", ") || "none"}</p>
            </div>
          ) : null}

          <Button aria-label="Generate frequency adaptation preview" variant="secondary" className="w-full" onClick={generateAdaptationPreview}>
            Generate Frequency Adaptation Preview
          </Button>
          <p className="telemetry-meta">{adaptationStatus ?? ""}</p>
          <Button aria-label="Apply frequency adaptation" variant="secondary" className="w-full" onClick={applyAdaptation}>
            Apply Frequency Adaptation
          </Button>
          <p className="telemetry-meta">{adaptationApplyStatus ?? ""}</p>
          {adaptationPreview ? (
            <div className="rounded-md border border-zinc-800 p-2">
              <p>Adaptation: {adaptationPreview.from_days}d -&gt; {adaptationPreview.to_days}d</p>
              <p>Duration: {adaptationPreview.duration_weeks} week(s)</p>
              <p>Weak Areas: {adaptationPreview.weak_areas.join(", ") || "none"}</p>
              <p>Week Plans: {adaptationPreview.weeks.length}</p>
              <p>
                First Week Decisions: {adaptationPreview.weeks[0]?.decisions.length ?? 0}
              </p>
            </div>
          ) : null}
        </div>

        <div className="rounded-md border border-zinc-800 p-3 text-xs text-zinc-300 space-y-2">
          <p className="telemetry-kicker">Apply Coaching Decision</p>
          <p className="telemetry-meta">Recommendation ID: {applyRecommendationId || "Generate preview first"}</p>
          <div className="grid grid-cols-2 gap-2">
            <Button aria-label="Check phase decision" variant="secondary" onClick={() => runApplyPhase(false)} disabled={!applyRecommendationId.trim()}>
              Check Phase
            </Button>
            <Button aria-label="Apply phase decision" variant="secondary" onClick={() => runApplyPhase(true)} disabled={!applyRecommendationId.trim()}>
              Apply Phase
            </Button>
            <Button aria-label="Check specialization decision" variant="secondary" onClick={() => runApplySpecialization(false)} disabled={!applyRecommendationId.trim()}>
              Check Specialization
            </Button>
            <Button aria-label="Apply specialization decision" variant="secondary" onClick={() => runApplySpecialization(true)} disabled={!applyRecommendationId.trim()}>
              Apply Specialization
            </Button>
          </div>
          <p className="telemetry-meta">{applyStatus ?? ""}</p>
        </div>

        <p className="telemetry-kicker">Display</p>
        <p className="ui-body-sm">Theme is locked to dark for MVP.</p>
        <Button variant="secondary" className="w-full" disabled>
          <span className="inline-flex items-center gap-2">
            <UiIcon name="settings" className="ui-icon--action" />
            Theme: {theme}
          </span>
        </Button>

        <p className="telemetry-kicker">Profile Context</p>
        <div className="rounded-md border border-zinc-800 p-3 text-xs text-zinc-300">
          <p>Training Location: {profile?.training_location ?? "not set"}</p>
          <p>Equipment: {(profile?.equipment_profile ?? []).join(", ") || "not set"}</p>
        </div>

        <div className="space-y-2">
          <p className="telemetry-kicker">Program Override</p>
          <label htmlFor="settings-program" className="ui-meta">Program</label>
          <select
            id="settings-program"
            className="ui-select"
            value={selectedProgramId ?? ""}
            onChange={(e) => setSelectedProgramId(e.target.value || null)}
            aria-label="Settings program selector"
            aria-describedby="settings-program-desc"
          >
            <option value="">Default — trainer&apos;s recommended program</option>
            {programs.map((p) => (
              <option key={p.id} value={p.id}>{getProgramDisplayName(p)}</option>
            ))}
          </select>
          <p id="settings-program-desc" className="text-xs text-zinc-500">{selectedProgramId ? (programs.find((p) => p.id === selectedProgramId)?.description ?? "No description available.") : "Default uses trainer recommendation."}</p>
          <div className="flex gap-2">
            <Button aria-label="Save selected program" className="mt-2" onClick={saveProgram}>
              <span className="inline-flex items-center gap-2">
                <UiIcon name="save" className="ui-icon--action" />
                Save Program
              </span>
            </Button>
            {pendingSwitch ? (
              <Button aria-label="Confirm program switch" className="mt-2" onClick={confirmProgramSwitch} variant="secondary">
                <span className="inline-flex items-center gap-2">
                  <UiIcon name="swap" className="ui-icon--action" />
                  Confirm Switch
                </span>
              </Button>
            ) : null}
            <p className="telemetry-meta mt-3">{status ?? ""}</p>
          </div>
          {pendingSwitch ? (
            <p className="text-xs text-zinc-500">
              Switching to <span className="text-zinc-300">{getProgramDisplayName({ id: pendingSwitch.targetProgramId })}</span> requires confirmation ({pendingSwitch.rationale}).
            </p>
          ) : null}
        </div>

        <div className="rounded-md border border-red-700/40 bg-red-950/20 p-3">
          <p className="telemetry-kicker">Developer Tools</p>
          <p className="telemetry-meta">Use this to wipe your current user and retest onboarding from scratch.</p>
          <Button className="mt-2 w-full" variant="secondary" onClick={wipeUserData}>
            <span className="inline-flex items-center gap-2">
              <UiIcon name="reset" className="ui-icon--action" />
              Wipe Current User Data
            </span>
          </Button>
        </div>
      </div>
    </div>
  );
}
