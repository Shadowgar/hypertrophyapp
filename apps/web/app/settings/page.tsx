"use client";

import Link from "next/link";
import {AppearanceSettings} from "@/components/appearance-settings";
import { useCallback, useEffect, useRef, useState } from "react";
import styles from "./settings.module.css";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Disclosure } from "@/components/ui/disclosure";
import { UiIcon } from "@/components/ui/icons";
import {
  api,
  clearAuthToken,
  type FrequencyAdaptationResult,
  getProgramDisplayName,
  getToken,
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
  const token = useRef(getToken());
  const [accountEpoch, setAccountEpoch] = useState(0);
  useEffect(() => {
    const syncAccount = () => {
      const current = getToken();
      if (current === token.current) return;
      token.current = current;
      setAccountEpoch((value) => value + 1);
    };
    const onStorage = (event: StorageEvent) => {
      if (event.key === "hypertrophy_token" || event.key === null) syncAccount();
    };
    window.addEventListener("hypertrophy:auth-token-changed", syncAccount);
    window.addEventListener("storage", onStorage);
    syncAccount();
    return () => {
      window.removeEventListener("hypertrophy:auth-token-changed", syncAccount);
      window.removeEventListener("storage", onStorage);
    };
  }, []);
  return <SettingsContent key={accountEpoch} />;
}

function SettingsContent() {
  const sessionToken = useRef(getToken());
  const mounted = useRef(true);
  const isCurrentSession = useCallback(() => mounted.current && getToken() === sessionToken.current, []);
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);
  const router = useRouter();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [profileLoad, setProfileLoad] = useState<"loading" | "ready" | "error">("loading");
  const [profileRetry, setProfileRetry] = useState(0);
  const [trainingSave, setTrainingSave] = useState<"idle" | "pending" | "saved" | "error">("idle");
  const trainingSaveActive = useRef(false);
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
  const [previewLaggingMuscles, setPreviewLaggingMuscles] = useState<string>("");
  const [applyRecommendationId, setApplyRecommendationId] = useState<string>("");
  const [applyStatus, setApplyStatus] = useState<string | null>(null);
  const [editTrainingLocation, setEditTrainingLocation] = useState<string>("");
  const [editEquipment, setEditEquipment] = useState<string[]>([]);
  const [programRecommendationStatus, setProgramRecommendationStatus] = useState<string | null>(null);
  const [programRecommendation, setProgramRecommendation] = useState<{
    current_program_id: string;
    recommended_program_id: string;
    reason: string;
    rationale?: string;
  } | null>(null);
  const [devWipeEnabled, setDevWipeEnabled] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setProfileLoad("loading");
    api.getProfile().then((data) => {
      if (cancelled || !isCurrentSession()) return;
      setProfile(data);
      setProfileLoad("ready");
      const currentDays = (data.effective_days_available ?? data.days_available) || 5;
      setPreviewFromDays(Math.max(MIN_TRAINING_DAYS, Math.min(MAX_TRAINING_DAYS, currentDays)));
      setPreviewToDays(Math.max(MIN_TRAINING_DAYS, Math.min(MAX_TRAINING_DAYS, Math.min(currentDays, 3))));
      setEditTrainingLocation(data.training_location === "home" || data.training_location === "gym" ? data.training_location : "");
      setEditEquipment(Array.isArray(data.equipment_profile) ? data.equipment_profile : []);
    }).catch(() => {
      if (cancelled || !isCurrentSession()) return;
      setProfileLoad("error");
    });
    return () => { cancelled = true; };
  }, [isCurrentSession, profileRetry]);

  useEffect(() => {
    let cancelled = false;
    api.getGeneratedTrainingProfileDebug().then(() => {
      if (!cancelled && isCurrentSession()) setDevWipeEnabled(true);
    }).catch(() => {
      if (!cancelled && isCurrentSession()) setDevWipeEnabled(false);
    });
    return () => { cancelled = true; };
  }, [isCurrentSession]);

  const selectedProgramId = profile?.effective_program_id ?? profile?.selected_program_id ?? null;
  const selectedProgramName = selectedProgramId ? getProgramDisplayName({ id: selectedProgramId }) : "No active program";
  const trainingPending = trainingSave === "pending";
  const trainingReady = profileLoad === "ready" && (editTrainingLocation === "home" || editTrainingLocation === "gym");
  const temporaryDurationValidationMessage = validateTemporaryDurationInput(previewDurationWeeksInput);

  function toggleEquipmentTag(tag: string) {
    setEditEquipment((prev) =>
      prev.includes(tag) ? prev.filter((item) => item !== tag) : [...prev, tag],
    );
  }

  async function saveProfileTraining() {
    if (trainingSaveActive.current || !profile || !isCurrentSession()) return;
    if (editTrainingLocation !== "home" && editTrainingLocation !== "gym") return;
    trainingSaveActive.current = true;
    setTrainingSave("pending");
    try {
      const updated = await api.updateEquipment({
        training_location: editTrainingLocation,
        equipment_profile: [...editEquipment],
      });
      if (!isCurrentSession()) return;
      setProfile(updated);
      setTrainingSave("saved");
    } catch {
      if (isCurrentSession()) setTrainingSave("error");
    } finally {
      trainingSaveActive.current = false;
    }
  }

  async function generateCoachPreview() {
    if (!selectedProgramId || !isCurrentSession()) return;
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
      if (!isCurrentSession()) return;
      setCoachPreview(preview);
      setApplyRecommendationId(preview.recommendation_id);
      setCoachStatus("Preview ready");
    } catch {
      if (!isCurrentSession()) return;
      setCoachStatus("Preview failed");
    }
  }

  async function generateAdaptationPreview() {
    if (!selectedProgramId || !isCurrentSession()) return;
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
      if (!isCurrentSession()) return;
      setAdaptationPreview(preview);
      setAdaptationStatus("Frequency adaptation ready");
    } catch (error) {
      if (!isCurrentSession()) return;
      const detail = error instanceof Error ? error.message : "Frequency adaptation failed";
      setAdaptationStatus(detail);
    }
  }

  async function applyAdaptation() {
    if (!selectedProgramId || !isCurrentSession()) return;
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
      if (!isCurrentSession()) return;
      setAdaptationApplyStatus(
        `Applied (${response.target_days}d for ${response.duration_weeks} weeks, ${response.weeks_remaining} remaining)`,
      );
      setAdaptationApplyOutcome("success");
    } catch (error) {
      if (!isCurrentSession()) return;
      const detail = error instanceof Error ? error.message : "Apply frequency adaptation failed";
      setAdaptationApplyStatus(detail);
      setAdaptationApplyOutcome("failed");
    }
  }

  async function generateWeekAfterAdaptation() {
    if (!selectedProgramId || !isCurrentSession()) return;
    setIsGeneratingPostApplyWeek(true);
    setPostApplyGenerateStatus("Generating week from adapted state...");
    try {
      const generatedWeek = await api.generateWeek(selectedProgramId, previewToDays);
      if (!isCurrentSession()) return;
      setPostApplyGenerateStatus(`Generated week for ${getProgramDisplayName({ id: generatedWeek.program_template_id })}.`);
    } catch (error) {
      if (!isCurrentSession()) return;
      const detail = error instanceof Error ? error.message : "Generate week failed. Open Week Plan and retry.";
      setPostApplyGenerateStatus(detail);
    } finally {
      setIsGeneratingPostApplyWeek(false);
    }
  }

  async function runApplyPhase(confirm: boolean) {
    if (!isCurrentSession()) return;
    const recommendationId = applyRecommendationId.trim();
    if (!recommendationId) {
      setApplyStatus("Generate a preview first");
      return;
    }

    setApplyStatus(confirm ? "Applying phase decision..." : "Checking phase decision...");
    try {
      const response = await api.applyPhaseDecision({ recommendation_id: recommendationId, confirm });
      if (!isCurrentSession()) return;
      const explanation = resolveReasonText(response.rationale, response.reason);
      setApplyStatus(explanation ? `Phase: ${response.status} (${explanation})` : `Phase: ${response.status}`);
    } catch {
      if (!isCurrentSession()) return;
      setApplyStatus("Phase apply failed");
    }
  }

  async function runApplySpecialization(confirm: boolean) {
    if (!isCurrentSession()) return;
    const recommendationId = applyRecommendationId.trim();
    if (!recommendationId) {
      setApplyStatus("Generate a preview first");
      return;
    }

    setApplyStatus(confirm ? "Applying specialization decision..." : "Checking specialization decision...");
    try {
      const response = await api.applySpecializationDecision({ recommendation_id: recommendationId, confirm });
      if (!isCurrentSession()) return;
      setApplyStatus(`Specialization: ${response.status} (focus ${response.focus_muscles.join(", ") || "none"})`);
    } catch {
      if (!isCurrentSession()) return;
      setApplyStatus("Specialization apply failed");
    }
  }

  async function wipeUserData() {
    if (!isCurrentSession()) return;
    if (!devWipeEnabled) {
      setStatus("Developer wipe is disabled.");
      return;
    }
    const confirmed = globalThis.confirm("This will permanently wipe your current user account and all related data. Continue?");
    if (!confirmed) {
      return;
    }

    setStatus("Wiping account data...");
    try {
      await api.wipeProfileData();
      if (!isCurrentSession()) return;
      clearAuthToken();
      setStatus("Data wiped. Redirecting to onboarding...");
      router.push("/onboarding");
    } catch {
      if (!isCurrentSession()) return;
      setStatus("Wipe failed");
    }
  }

  async function loadProgramRecommendation() {
    if (!isCurrentSession()) return;
    setProgramRecommendationStatus("Getting recommendation...");
    try {
      const recommendation = await api.getProgramRecommendation();
      if (!isCurrentSession()) return;
      setProgramRecommendation(recommendation);
      if (recommendation.current_program_id === recommendation.recommended_program_id) {
        setProgramRecommendationStatus("You are already on the recommended program.");
        return;
      }
      setProgramRecommendationStatus("Recommendation ready.");
    } catch {
      if (!isCurrentSession()) return;
      setProgramRecommendationStatus("Failed to fetch recommendation.");
    }
  }

  async function applyRecommendedProgram() {
    if (!isCurrentSession()) return;
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

      if (!isCurrentSession()) return;
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

      if (!isCurrentSession()) return;
      const refreshedProfile = await api.getProfile();
      if (!isCurrentSession()) return;
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
      if (!isCurrentSession()) return;
      setProgramRecommendationStatus("Program switch failed.");
    }
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <p className={styles.eyebrow}>Your account</p>
        <h1 className="ui-title-page">Settings</h1>
        <p className={styles.muted}>Your preferences, clearly separated.</p>
      </header>

      <nav className={styles.sections} aria-label="Settings sections">
        <a href="#appearance-preferences"><strong>Theme &amp; appearance</strong><span>Choose how WorkoutApp looks</span></a>
        <a href="#appearance-preferences"><strong>Weight display</strong><span>Pounds or kilograms</span></a>
        <a href="#training-preferences"><strong>Equipment &amp; training preferences</strong><span>Your location, equipment and program</span></a>
        <a href="#account-preferences"><strong>Account &amp; accessibility</strong><span>Your profile and account access</span></a>
      </nav>

      {profileLoad === "error" ? (
        <div className={styles.notice} role="alert">
          <p>We couldn&apos;t load your profile. Training settings are unavailable until it loads.</p>
          <Button variant="secondary" onClick={() => setProfileRetry((value) => value + 1)}>Retry loading profile</Button>
        </div>
      ) : null}

      <div className={styles.content}>
        <div id="appearance-preferences" className={styles.appearance}>
          <AppearanceSettings />
        </div>

        <section id="training-preferences" className={styles.card} aria-labelledby="training-heading">
          <h2 id="training-heading">Equipment &amp; training preferences</h2>
          <p className={styles.muted}>Save your training location and available equipment. Source-approved substitutions still require confirmation.</p>
          <fieldset disabled={profileLoad !== "ready" || trainingPending} className={styles.fields}>
            <label htmlFor="training-location">Training location</label>
            <select id="training-location" className="ui-select" value={editTrainingLocation} onChange={(event) => {
              setEditTrainingLocation(event.target.value);
              setTrainingSave("idle");
            }}>
              <option value="" disabled>Choose your training location</option>
              <option value="gym">Commercial gym</option>
              <option value="home">Home gym</option>
            </select>
            <div role="group" aria-labelledby="equipment-label">
              <p id="equipment-label" className={styles.fieldLabel}>Equipment you have</p>
              <div className={styles.equipment}>
                {["barbell", "bench", "dumbbell", "cable", "machine", "bands", "bodyweight"].map((tag) => (
                  <button key={tag} type="button" aria-pressed={editEquipment.includes(tag)} onClick={() => {
                    toggleEquipmentTag(tag);
                    setTrainingSave("idle");
                  }}>{tag}</button>
                ))}
              </div>
            </div>
            <p className={styles.muted}>
              {profile ? `Saved: ${profile.training_location ?? "location not set"} · ${(profile.equipment_profile ?? []).join(", ") || "no equipment set"}` : profileLoad === "loading" ? "Loading training settings…" : "Training settings unavailable."}
            </p>
            <Button type="button" variant="secondary" disabled={!trainingReady || trainingPending} onClick={saveProfileTraining}>
              {trainingSave === "error" ? "Retry training settings" : "Save training settings"}
            </Button>
          </fieldset>
          {trainingSave !== "idle" ? <p role="status" className={styles.muted}>{trainingPending ? "Saving training settings…" : trainingSave === "saved" ? "Training settings saved." : "Save not confirmed. Your choices are still here; retry to save these training settings."}</p> : null}
          <div className={styles.program}>
            <h3>Active program</h3>
            <p>{profileLoad === "ready" ? selectedProgramName : profileLoad === "loading" ? "Loading program…" : "Program unavailable"}</p>
            {profileLoad === "ready" ? <p className={styles.muted}>Program selection: {profile?.program_selection_mode === "auto" ? "Auto" : "Manual"}</p> : null}
            <p className={styles.muted}>Choose an original Customized Full Body program, review dates and accept its exact version.</p>
            <Link href="/customize" className={styles.link}>Update generated plan preferences</Link>
          </div>
        </section>

        <section id="account-preferences" className={styles.card} aria-labelledby="account-heading">
          <h2 id="account-heading">Account &amp; accessibility</h2>
          {profile ? <dl className={styles.account}><div><dt>Name</dt><dd>{profile.name || "Not set"}</dd></div><div><dt>Email</dt><dd>{profile.email}</dd></div></dl> : <p className={styles.muted}>{profileLoad === "loading" ? "Loading profile…" : "Profile unavailable."}</p>}
          <p className={styles.muted}>Appearance follows your selected preference. Follow Device Settings uses this device&apos;s light or dark setting.</p>
          <Button variant="secondary" disabled={trainingPending} onClick={() => {
            if (!isCurrentSession()) return;
            clearAuthToken();
            router.replace("/login");
          }}>Sign out</Button>
        </section>
      </div>

      <section className={styles.advanced} aria-labelledby="advanced-heading">
        <div><h2 id="advanced-heading">Advanced training controls</h2><p className={styles.muted}>Review recommendations and hypothetical coaching inputs before applying any change.</p></div>
        <Disclosure title="Program recommendation" defaultOpen={false}>
          <div className="space-y-3">
            <p>Ask for a program recommendation based on your profile and current constraints.</p>
            <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
              <Button type="button" variant="secondary" onClick={loadProgramRecommendation} disabled={profileLoad !== "ready"}>Get Recommendation</Button>
              <Button type="button" variant="secondary" onClick={applyRecommendedProgram} disabled={!programRecommendation || programRecommendation.current_program_id === programRecommendation.recommended_program_id}>Apply Recommendation</Button>
            </div>
            {programRecommendation ? <div className={styles.notice}><p>Current: {programRecommendation.current_program_id}</p><p>Recommended: {programRecommendation.recommended_program_id}</p><p>Reason: {resolveReasonText(programRecommendation.rationale, programRecommendation.reason) ?? "No rationale provided."}</p></div> : null}
            {programRecommendationStatus ? <p role="status">{programRecommendationStatus}</p> : null}
          </div>
        </Disclosure>

      <Disclosure title="Coaching Preview" badge="power user" defaultOpen={false}>
        <div className="space-y-3 text-xs text-zinc-300">
          <p className="text-xs text-zinc-400">
            These are hypothetical inputs, not observations from your workout history. The preview uses example
            completion (90%), adherence (4/5), average RPE (8.5), phase duration (4 weeks), stagnation (0 weeks)
            and minimum sets (8), plus the inputs below. Generating a preview does not change your plan.
            Apply controls submit a change to the existing coaching service.
          </p>
          <div className="grid grid-cols-2 gap-2">
            <label htmlFor="preview-from-days" className="ui-meta">
              From days (preview scenario)
            </label>
            <input id="preview-from-days" className="ui-input" type="number" min={MIN_TRAINING_DAYS} max={MAX_TRAINING_DAYS} value={previewFromDays} onChange={(e) => setPreviewFromDays(Math.max(MIN_TRAINING_DAYS, Math.min(MAX_TRAINING_DAYS, Number(e.target.value) || MIN_TRAINING_DAYS)))} />
            <label htmlFor="preview-to-days" className="ui-meta">
              To days (the schedule you&apos;re testing)
            </label>
            <input id="preview-to-days" className="ui-input" type="number" min={MIN_TRAINING_DAYS} max={MAX_TRAINING_DAYS} value={previewToDays} onChange={(e) => setPreviewToDays(Math.max(MIN_TRAINING_DAYS, Math.min(MAX_TRAINING_DAYS, Number(e.target.value) || MIN_TRAINING_DAYS)))} />
            <label htmlFor="preview-phase" className="ui-meta">
              Example phase
            </label>
            <select id="preview-phase" className="ui-select" value={previewPhase} onChange={(e) => setPreviewPhase(e.target.value as "accumulation" | "intensification" | "deload")}>
              <option value="accumulation">Accumulation</option>
              <option value="intensification">Intensification</option>
              <option value="deload">Deload</option>
            </select>
            <label htmlFor="preview-soreness" className="ui-meta">Example soreness</label>
            <select id="preview-soreness" className="ui-select" value={previewSoreness} onChange={(e) => setPreviewSoreness(e.target.value as SorenessSeverity)}>
              <option value="none">None</option>
              <option value="mild">Mild</option>
              <option value="moderate">Moderate</option>
              <option value="severe">Severe</option>
            </select>
          </div>
          <label htmlFor="preview-lagging" className="ui-meta">Example focus muscles (comma-separated)</label>
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
            disabled={!selectedProgramId}
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
            <Button aria-label="Generate frequency adaptation preview" variant="secondary" className="w-full" onClick={generateAdaptationPreview} disabled={!selectedProgramId}>Adaptation Preview</Button>
            <Button aria-label="Apply frequency adaptation" variant="secondary" className="w-full" onClick={applyAdaptation} disabled={!selectedProgramId}>Apply Adaptation</Button>
          </div>
          {adaptationStatus ? <p className="text-xs text-zinc-400">{adaptationStatus}</p> : null}
          {adaptationApplyStatus ? <p className="text-xs text-zinc-400">{adaptationApplyStatus}</p> : null}
          {adaptationApplyOutcome === "success" ? (
            <div className="rounded-md border border-zinc-800 p-2 space-y-2">
              <Button aria-label="Generate Week Now" variant="secondary" className="w-full" onClick={generateWeekAfterAdaptation} disabled={!selectedProgramId || isGeneratingPostApplyWeek}>
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

      </section>

      {devWipeEnabled ? (
      <Disclosure title="Developer tools" defaultOpen={false}>
      <div className="rounded-lg border border-red-700/40 bg-red-950/20 p-4 space-y-3">
        <p className="text-xs text-zinc-400">Permanently delete this account and its data. This is a developer reset, not recovery for a failed save.</p>
        <Button className="w-full" variant="secondary" onClick={wipeUserData}>
          <span className="inline-flex items-center gap-2">
            <UiIcon name="reset" className="ui-icon--action" />
            Wipe Current User Data
          </span>
        </Button>
        {status ? <p className="text-xs text-zinc-400">{status}</p> : null}
      </div>
      </Disclosure>
      ) : null}

      <p className="text-center text-[10px] text-zinc-600">
        {process.env.NEXT_PUBLIC_APP_VERSION ?? "dev"}
      </p>
    </div>
  );
}
