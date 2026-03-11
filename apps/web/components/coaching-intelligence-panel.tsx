"use client";

import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  api,
  resolveReasonText,
  type IntelligenceCoachPreviewResponse,
  type SorenessSeverity,
} from "@/lib/api";

type CoachingIntelligencePanelProps = {
  contextLabel: string;
  templateId?: string | null;
  contextNote?: string | null;
};

function parseLaggingMuscles(raw: string): string[] {
  return raw
    .split(",")
    .map((item) => item.trim().toLowerCase())
    .filter((item) => item.length > 0);
}

function formatTransitionAction(action?: string | null): string {
  const normalized = (action ?? "").trim();
  if (!normalized) {
    return "Review next step";
  }
  return normalized
    .split("_")
    .filter((part) => part.length > 0)
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join(" ");
}

export default function CoachingIntelligencePanel({
  contextLabel,
  contextNote,
  templateId,
}: Readonly<CoachingIntelligencePanelProps>) {
  const [profileTemplateId, setProfileTemplateId] = useState<string | null>(null);
  const [coachPreview, setCoachPreview] = useState<IntelligenceCoachPreviewResponse | null>(null);
  const [coachStatus, setCoachStatus] = useState<string | null>(null);
  const [previewFromDays, setPreviewFromDays] = useState<number>(5);
  const [previewToDays, setPreviewToDays] = useState<number>(3);
  const [previewPhase, setPreviewPhase] = useState<"accumulation" | "intensification" | "deload">("accumulation");
  const [previewSoreness, setPreviewSoreness] = useState<SorenessSeverity>("mild");
  const [previewLaggingMuscles, setPreviewLaggingMuscles] = useState<string>("biceps, shoulders");
  const [applyRecommendationId, setApplyRecommendationId] = useState<string>("");
  const [applyStatus, setApplyStatus] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    api.getProfile()
      .then((data) => {
        if (!mounted) {
          return;
        }
        setProfileTemplateId(data.selected_program_id ?? null);
        const daysAvailable = Number(data.days_available) || 5;
        setPreviewFromDays(Math.max(2, Math.min(7, daysAvailable)));
        setPreviewToDays(Math.max(2, Math.min(7, Math.min(daysAvailable, 3))));
      })
      .catch(() => {
        if (!mounted) {
          return;
        }
        setProfileTemplateId(null);
      });

    return () => {
      mounted = false;
    };
  }, []);

  const resolvedTemplateId = useMemo(() => {
    if (templateId && templateId.trim().length > 0) {
      return templateId;
    }
    return profileTemplateId;
  }, [profileTemplateId, templateId]);

  async function generateCoachPreview() {
    setCoachStatus("Generating preview...");
    setApplyStatus(null);
    try {
      const payload = {
        template_id: resolvedTemplateId,
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

  async function runApplyPhase(confirm: boolean) {
    const recommendationId = applyRecommendationId.trim();
    if (!recommendationId) {
      setApplyStatus("Generate a preview first");
      return;
    }

    setApplyStatus(confirm ? "Applying phase decision..." : "Checking phase decision...");
    try {
      const response = await api.applyPhaseDecision({ recommendation_id: recommendationId, confirm });
      setApplyStatus(`Phase: ${response.status} (${resolveReasonText(response.rationale, response.reason)})`);
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

  return (
    <div className="main-card main-card--module spacing-grid spacing-grid--tight">
      <p className="telemetry-kicker">Coaching Intelligence</p>
      <p className="telemetry-meta">Surface: {contextLabel}</p>
      <p className="telemetry-meta">Template: {resolvedTemplateId ?? "profile-selected"}</p>
      {contextNote ? (
        <div className="rounded-md border border-white/10 bg-zinc-950/50 p-2">
          <p className="ui-meta">Current context</p>
          <p className="text-xs text-zinc-200">{contextNote}</p>
        </div>
      ) : null}

      <div className="grid grid-cols-2 gap-2">
        <label htmlFor={`${contextLabel}-preview-from-days`} className="ui-meta">From Days</label>
        <input
          id={`${contextLabel}-preview-from-days`}
          className="ui-input"
          type="number"
          min={2}
          max={7}
          value={previewFromDays}
          onChange={(event) => setPreviewFromDays(Math.max(2, Math.min(7, Number(event.target.value) || 2)))}
        />
        <label htmlFor={`${contextLabel}-preview-to-days`} className="ui-meta">To Days</label>
        <input
          id={`${contextLabel}-preview-to-days`}
          className="ui-input"
          type="number"
          min={2}
          max={7}
          value={previewToDays}
          onChange={(event) => setPreviewToDays(Math.max(2, Math.min(7, Number(event.target.value) || 2)))}
        />
        <label htmlFor={`${contextLabel}-preview-phase`} className="ui-meta">Current Phase</label>
        <select
          id={`${contextLabel}-preview-phase`}
          className="ui-select"
          value={previewPhase}
          onChange={(event) => setPreviewPhase(event.target.value as "accumulation" | "intensification" | "deload")}
        >
          <option value="accumulation">Accumulation</option>
          <option value="intensification">Intensification</option>
          <option value="deload">Deload</option>
        </select>
        <label htmlFor={`${contextLabel}-preview-soreness`} className="ui-meta">Soreness</label>
        <select
          id={`${contextLabel}-preview-soreness`}
          className="ui-select"
          value={previewSoreness}
          onChange={(event) => setPreviewSoreness(event.target.value as SorenessSeverity)}
        >
          <option value="none">None</option>
          <option value="mild">Mild</option>
          <option value="moderate">Moderate</option>
          <option value="severe">Severe</option>
        </select>
      </div>

      <label htmlFor={`${contextLabel}-preview-lagging`} className="ui-meta">Lagging Muscles (comma-separated)</label>
      <input
        id={`${contextLabel}-preview-lagging`}
        className="ui-input"
        value={previewLaggingMuscles}
        onChange={(event) => setPreviewLaggingMuscles(event.target.value)}
      />

      <Button aria-label="Generate coaching preview" variant="secondary" className="w-full" onClick={generateCoachPreview}>
        Generate Coaching Preview
      </Button>

      <p className="telemetry-meta">{coachStatus ?? ""}</p>
      {coachPreview ? (
        <div className="rounded-md border border-zinc-800 p-2 text-xs text-zinc-300">
          <p>Program: {coachPreview.program_name}</p>
          <p>Recommendation ID: {coachPreview.recommendation_id}</p>
          <p>Progression: {coachPreview.progression.action}</p>
          <p>{resolveReasonText(coachPreview.progression.rationale, coachPreview.progression.reason)}</p>
          <p>Phase Recommendation: {coachPreview.phase_transition.next_phase}</p>
          {!coachPreview.phase_transition.transition_pending ? (
            <p>{resolveReasonText(coachPreview.phase_transition.rationale, coachPreview.phase_transition.reason)}</p>
          ) : null}
          {coachPreview.phase_transition.transition_pending ? (
            <div className="mt-2 rounded-md border border-zinc-700/80 bg-zinc-950/50 p-2">
              <p className="font-medium text-zinc-100">Program Transition</p>
              <p>Current block complete</p>
              <p>Recommendation: {formatTransitionAction(coachPreview.phase_transition.recommended_action)}</p>
              <p>{resolveReasonText(undefined, coachPreview.phase_transition.post_authored_behavior)}</p>
              <p>{resolveReasonText(coachPreview.phase_transition.rationale, coachPreview.phase_transition.reason)}</p>
            </div>
          ) : null}
          <p>Adaptation Risk: {coachPreview.schedule.risk_level}</p>
        </div>
      ) : null}

      <p className="telemetry-meta">Recommendation ID: {applyRecommendationId || "Generate preview first"}</p>
      <div className="grid grid-cols-2 gap-2">
        <Button
          aria-label="Check phase decision"
          variant="secondary"
          onClick={() => runApplyPhase(false)}
          disabled={!applyRecommendationId.trim()}
        >
          Check Phase
        </Button>
        <Button
          aria-label="Apply phase decision"
          variant="secondary"
          onClick={() => runApplyPhase(true)}
          disabled={!applyRecommendationId.trim()}
        >
          Apply Phase
        </Button>
        <Button
          aria-label="Check specialization decision"
          variant="secondary"
          onClick={() => runApplySpecialization(false)}
          disabled={!applyRecommendationId.trim()}
        >
          Check Specialization
        </Button>
        <Button
          aria-label="Apply specialization decision"
          variant="secondary"
          onClick={() => runApplySpecialization(true)}
          disabled={!applyRecommendationId.trim()}
        >
          Apply Specialization
        </Button>
      </div>
      <p className="telemetry-meta">{applyStatus ?? ""}</p>
    </div>
  );
}
