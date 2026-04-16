"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Disclosure } from "@/components/ui/disclosure";
import { UiIcon } from "@/components/ui/icons";
import {
  api,
  clearAuthToken,
  type FrequencyAdaptationResult,
  getProgramDisplayName,
  resolveReasonText,
  type IntelligenceCoachPreviewResponse,
  type Profile,
  type SorenessSeverity,
} from "@/lib/api";

function parseLaggingMuscles(raw: string): string[] {
  return raw
    .split(",")
    .map((item) => item.trim().toLowerCase())
    .filter((item) => item.length > 0);
}

const MIN_TRAINING_DAYS = 2;
const MAX_TRAINING_DAYS = 5;
const MIN_TEMPORARY_DURATION_WEEKS = 1;
const MAX_TEMPORARY_DURATION_WEEKS = 8;

function validateTemporaryDurationInput(raw: string): string | null {
  if (!/^\d+$/.test(raw.trim())) {
    return `Enter a whole number between ${MIN_TEMPORARY_DURATION_WEEKS} and ${MAX_TEMPORARY_DURATION_WEEKS}.`;
  }
  const parsed = Number(raw);
  if (parsed < MIN_TEMPORARY_DURATION_WEEKS || parsed > MAX_TEMPORARY_DURATION_WEEKS) {
    return `Temporary duration must be between ${MIN_TEMPORARY_DURATION_WEEKS} and ${MAX_TEMPORARY_DURATION_WEEKS} weeks.`;
  }
  return null;
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
  const [previewDurationWeeksInput, setPreviewDurationWeeksInput] = useState<string>("4");
  const [previewPhase, setPreviewPhase] = useState<"accumulation" | "intensification" | "deload">("accumulation");
  const [previewSoreness, setPreviewSoreness] = useState<SorenessSeverity>("mild");
  const [previewLaggingMuscles, setPreviewLaggingMuscles] = useState<string>("biceps, shoulders");
  const [applyRecommendationId, setApplyRecommendationId] = useState<string>("");
  const [applyStatus, setApplyStatus] = useState<string | null>(null);
  const [editTrainingLocation, setEditTrainingLocation] = useState<string>("gym");
  const [editEquipment, setEditEquipment] = useState<string[]>([]);
  const [programRecommendationStatus, setProgramRecommendationStatus] = useState<string | null>(null);
  const [programRecommendation, setProgramRecommendation] = useState<{
    current_program_id: string;
    recommended_program_id: string;
    reason: string;
    rationale?: string;
  } | null>(null);

  useEffect(() => {
    let mounted = true;
    api
      .getProfile()
      .then((data) => {
        if (!mounted) return;
        setProfile(data);
        setPreviewFromDays(Math.max(MIN_TRAINING_DAYS, Math.min(MAX_TRAINING_DAYS, data.days_available || 5)));
        setPreviewToDays(Math.max(MIN_TRAINING_DAYS, Math.min(MAX_TRAINING_DAYS, Math.min(data.days_available || 5, 3))));
        setEditTrainingLocation(data.training_location ?? "gym");
        setEditEquipment(Array.isArray(data.equipment_profile) ? data.equipment_profile : []);
      })
      .catch(() => setProfile(null));

    return () => {
      mounted = false;
    };
  }, []);

  const selectedProgramId = profile?.selected_program_id ?? "pure_bodybuilding_phase_1_full_body";
  const selectedProgramName = getProgramDisplayName({ id: selectedProgramId });
  const temporaryDurationValidationMessage = validateTemporaryDurationInput(previewDurationWeeksInput);

  function toggleEquipmentTag(tag: string) {
    setEditEquipment((prev) =>
      prev.includes(tag) ? prev.filter((item) => item !== tag) : [...prev, tag],
    );
  }

  async function saveProfileTraining() {
    setStatus("Saving training settings...");
    try {
      if (!profile) {
        setStatus("Profile not loaded yet.");
        return;
      }
      const updated = await api.updateProfile({
        name: profile.name,
        age: profile.age,
        weight: profile.weight,
        gender: profile.gender,
        split_preference: profile.split_preference,
        selected_program_id: profile.selected_program_id,
        program_selection_mode: profile.program_selection_mode,
        choose_for_me_family: profile.choose_for_me_family ?? null,
        choose_for_me_diagnostics: profile.choose_for_me_diagnostics ?? {},
        training_location: editTrainingLocation,
        equipment_profile: editEquipment,
        weak_areas: profile.weak_areas ?? [],
        onboarding_answers: profile.onboarding_answers ?? {},
        days_available: profile.days_available,
        // The web Profile type does not currently surface session_time_budget_minutes
        // or movement_restrictions/near_failure_tolerance; those are managed via
        // onboarding and check-in flows, not this training-setup editor.
        nutrition_phase: profile.nutrition_phase,
        calories: profile.calories,
        protein: profile.protein,
        fat: profile.fat,
        carbs: profile.carbs,
      });
      setProfile(updated);
      setStatus("Training settings saved.");
    } catch {
      setStatus("Failed to save training settings.");
    }
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
    if (temporaryDurationValidationMessage) {
      setAdaptationStatus(temporaryDurationValidationMessage);
      setAdaptationApplyStatus(null);
      setAdaptationApplyOutcome("idle");
      setPostApplyGenerateStatus(null);
      return;
    }
    setAdaptationStatus("Generating frequency adaptation...");
    setAdaptationApplyStatus(null);
    setAdaptationApplyOutcome("idle");
    setPostApplyGenerateStatus(null);
    try {
      const preview = await api.previewFrequencyAdaptation({
        program_id: selectedProgramId,
        target_days: previewToDays,
        duration_weeks: Number(previewDurationWeeksInput),
        weak_areas: parseLaggingMuscles(previewLaggingMuscles),
      });
      setAdaptationPreview(preview);
      setAdaptationStatus("Frequency adaptation ready");
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Frequency adaptation failed";
      setAdaptationStatus(detail);
    }
  }

  async function applyAdaptation() {
    if (temporaryDurationValidationMessage) {
      setAdaptationApplyStatus(temporaryDurationValidationMessage);
      setAdaptationApplyOutcome("failed");
      setPostApplyGenerateStatus(null);
      return;
    }
    setAdaptationApplyStatus("Applying frequency adaptation...");
    setAdaptationApplyOutcome("idle");
    setPostApplyGenerateStatus(null);
    try {
      const response = await api.applyFrequencyAdaptation({
        program_id: selectedProgramId,
        target_days: previewToDays,
        duration_weeks: Number(previewDurationWeeksInput),
        weak_areas: parseLaggingMuscles(previewLaggingMuscles),
      });
      setAdaptationApplyStatus(
        `Applied (${response.target_days}d for ${response.duration_weeks} weeks, ${response.weeks_remaining} remaining)`,
      );
      setAdaptationApplyOutcome("success");
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Apply frequency adaptation failed";
      setAdaptationApplyStatus(detail);
      setAdaptationApplyOutcome("failed");
    }
  }

  async function generateWeekAfterAdaptation() {
    setIsGeneratingPostApplyWeek(true);
    setPostApplyGenerateStatus("Generating week from adapted state...");
    try {
      const generatedWeek = await api.generateWeek(selectedProgramId, previewToDays);
      setPostApplyGenerateStatus(`Generated week for ${getProgramDisplayName({ id: generatedWeek.program_template_id })}.`);
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Generate week failed. Open Week Plan and retry.";
      setPostApplyGenerateStatus(detail);
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
      clearAuthToken();
      setStatus("Data wiped. Redirecting to onboarding...");
      setTimeout(() => router.push("/onboarding"), 400);
    } catch {
      setStatus("Wipe failed");
    }
  }

  async function loadProgramRecommendation() {
    setProgramRecommendationStatus("Getting recommendation...");
    try {
      const recommendation = await api.getProgramRecommendation();
      setProgramRecommendation(recommendation);
      if (recommendation.current_program_id === recommendation.recommended_program_id) {
        setProgramRecommendationStatus("You are already on the recommended program.");
        return;
      }
      setProgramRecommendationStatus("Recommendation ready.");
    } catch {
      setProgramRecommendationStatus("Failed to fetch recommendation.");
    }
  }

  async function applyRecommendedProgram() {
    if (!programRecommendation?.recommended_program_id) {
      setProgramRecommendationStatus("Get a recommendation first.");
      return;
    }
    setProgramRecommendationStatus("Validating program switch...");
    try {
      const preflight = await api.switchProgram({
        target_program_id: programRecommendation.recommended_program_id,
        confirm: false,
      });

      if (preflight.requires_confirmation) {
        const approved = globalThis.confirm(
          `Switch from ${preflight.current_program_id} to ${preflight.target_program_id}?`,
        );
        if (!approved) {
          setProgramRecommendationStatus("Program switch cancelled.");
          return;
        }
      }

      const applied = await api.switchProgram({
        target_program_id: programRecommendation.recommended_program_id,
        confirm: true,
      });

      const refreshedProfile = await api.getProfile();
      setProfile(refreshedProfile);
      setProgramRecommendation((prev) =>
        prev
          ? {
              ...prev,
              current_program_id: applied.target_program_id,
            }
          : prev,
      );
      setProgramRecommendationStatus(`Program switched to ${applied.target_program_id}.`);
    } catch {
      setProgramRecommendationStatus("Program switch failed.");
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="ui-title-page">Settings</h1>

      <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4 space-y-2">
        <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">Program</p>
        <p className="text-sm font-semibold text-zinc-100">{selectedProgramName}</p>
        <p className="text-xs text-zinc-400">ID: {selectedProgramId}</p>
      </div>

      <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4 space-y-2">
        <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">Choose for me</p>
        <p className="text-xs text-zinc-400">
          Ask the engine for the best-fit program based on your profile and current constraints.
        </p>
        <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
          <Button type="button" variant="secondary" onClick={loadProgramRecommendation}>
            Get Recommendation
          </Button>
          <Button
            type="button"
            variant="secondary"
            onClick={applyRecommendedProgram}
            disabled={!programRecommendation || programRecommendation.current_program_id === programRecommendation.recommended_program_id}
          >
            Apply Recommendation
          </Button>
        </div>
        {programRecommendation ? (
          <div className="rounded-md border border-zinc-800 p-2 text-xs text-zinc-300">
            <p>Current: {programRecommendation.current_program_id}</p>
            <p>Recommended: {programRecommendation.recommended_program_id}</p>
            <p>Reason: {resolveReasonText(programRecommendation.rationale, programRecommendation.reason) ?? "No rationale provided."}</p>
          </div>
        ) : null}
        {programRecommendationStatus ? <p className="text-xs text-zinc-400">{programRecommendationStatus}</p> : null}
      </div>

      <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4 space-y-2">
        <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">Training setup</p>
        <p className="text-xs text-zinc-400">
          Tell the coach where you train and what equipment you have. This shapes substitutions and exercise choices.
        </p>
        <div className="mt-2 space-y-3 text-sm text-zinc-200">
          <div>
            <label htmlFor="training-location" className="text-xs text-zinc-500">
              Training location
            </label>
            <select
              id="training-location"
              className="ui-select mt-1"
              value={editTrainingLocation}
              onChange={(e) => setEditTrainingLocation(e.target.value)}
            >
              <option value="gym">Commercial gym</option>
              <option value="home">Home gym</option>
              <option value="limited">Limited equipment</option>
            </select>
          </div>
          <div>
            <p className="text-xs text-zinc-500 mb-1">Equipment you have</p>
            <div className="flex flex-wrap gap-1.5">
              {["barbell", "bench", "dumbbell", "cable", "machine", "bands", "bodyweight"].map((tag) => {
                const active = editEquipment.includes(tag);
                return (
                  <button
                    key={tag}
                    type="button"
                    className={`rounded-full border px-2 py-0.5 text-[11px] ${
                      active
                        ? "border-red-400 bg-red-500/20 text-red-100"
                        : "border-zinc-700 bg-zinc-900 text-zinc-300"
                    }`}
                    onClick={() => toggleEquipmentTag(tag)}
                  >
                    {tag}
                  </button>
                );
              })}
            </div>
          </div>
          <div className="flex items-center justify-between text-xs text-zinc-500">
            <span>
              Current:{" "}
              {profile
                ? `${profile.training_location ?? "not set"} · ${(profile.equipment_profile ?? []).join(", ") || "no equipment set"}`
                : "loading..."}
            </span>
          </div>
          <Button type="button" variant="secondary" className="w-full" onClick={saveProfileTraining}>
            Save training settings
          </Button>
        </div>
      </div>

      <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4 space-y-2">
        <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">Display</p>
        <p className="text-sm text-zinc-400">Theme is locked to dark for MVP.</p>
      </div>

      <Disclosure title="Coaching Preview" badge="power user" defaultOpen={false}>
        <div className="space-y-3 text-xs text-zinc-300">
          <p className="text-xs text-zinc-400">
            This sandbox lets you ask, &quot;What would the coach do if I changed my schedule or phase?&quot; It does not
            change your plan until you apply a decision.
          </p>
          <div className="grid grid-cols-2 gap-2">
            <label htmlFor="preview-from-days" className="ui-meta">
              From days (your current schedule)
            </label>
            <input id="preview-from-days" className="ui-input" type="number" min={MIN_TRAINING_DAYS} max={MAX_TRAINING_DAYS} value={previewFromDays} onChange={(e) => setPreviewFromDays(Math.max(MIN_TRAINING_DAYS, Math.min(MAX_TRAINING_DAYS, Number(e.target.value) || MIN_TRAINING_DAYS)))} />
            <label htmlFor="preview-to-days" className="ui-meta">
              To days (the schedule you&apos;re testing)
            </label>
            <input id="preview-to-days" className="ui-input" type="number" min={MIN_TRAINING_DAYS} max={MAX_TRAINING_DAYS} value={previewToDays} onChange={(e) => setPreviewToDays(Math.max(MIN_TRAINING_DAYS, Math.min(MAX_TRAINING_DAYS, Number(e.target.value) || MIN_TRAINING_DAYS)))} />
            <label htmlFor="preview-phase" className="ui-meta">
              Current phase (how hard you&apos;re pushing)
            </label>
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
          <p className="text-[11px] text-zinc-500">Allowed range: 1-8 weeks</p>
          <input id="preview-duration" className="ui-input" type="number" min={MIN_TEMPORARY_DURATION_WEEKS} max={MAX_TEMPORARY_DURATION_WEEKS} value={previewDurationWeeksInput} onChange={(e) => setPreviewDurationWeeksInput(e.target.value)} />
          {temporaryDurationValidationMessage ? <p className="text-[11px] text-red-300">{temporaryDurationValidationMessage}</p> : null}
          <Button
            aria-label="Generate coaching preview"
            variant="secondary"
            className="w-full"
            onClick={generateCoachPreview}
          >
            Generate coaching preview (what would the coach suggest?)
          </Button>
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
