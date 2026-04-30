"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { api, type GeneratedOnboardingPayload } from "@/lib/api";

const EQUIPMENT_TAGS = ["barbell", "bench", "dumbbell", "cable", "machine", "bodyweight", "bands", "rack"] as const;
const MOVEMENT_RESTRICTIONS = [
  "deep_knee_flexion",
  "overhead_pressing",
  "barbell_from_floor",
  "long_length_hamstrings",
  "unsupported_bent_over_rowing",
  "none",
  "other",
] as const;
const WEAKPOINT_TAGS = ["chest", "back", "quads", "hamstrings", "glutes", "delts", "arms", "calves", "core"] as const;
const DISLIKED_EXERCISE_TAGS = [
  "barbell_bench_press",
  "barbell_back_squat",
  "conventional_deadlift",
  "overhead_press",
  "pullup",
  "dip",
] as const;

function toggleTag(current: string[], tag: string): string[] {
  return current.includes(tag) ? current.filter((item) => item !== tag) : [...current, tag];
}

function normalizeMovementRestrictions(tags: string[]): string[] {
  if (tags.includes("none")) {
    return ["none"];
  }
  return tags.filter((item) => item !== "none");
}

function emptyPayload(): GeneratedOnboardingPayload {
  return {
    goal_mode: "hypertrophy",
    target_days: 3,
    session_time_band_source: "50_70",
    training_status: "normal",
    trained_consistently_last_4_weeks: true,
    equipment_pool: ["dumbbell", "bodyweight"],
    movement_restrictions: ["none"],
    recovery_modifier: "normal",
    weakpoint_targets: [],
    preference_bias: "mixed",
    height_cm: null,
    bodyweight_kg: null,
    bodyweight_exercise_comfort: "mixed",
    disliked_tags: {
      disliked_exercises: [],
      disliked_equipment: [],
    },
  };
}

export default function GeneratedOnboardingPage() {
  const [draft, setDraft] = useState<GeneratedOnboardingPayload>(emptyPayload());
  const [status, setStatus] = useState<string>("Loading generated onboarding...");
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    let mounted = true;
    api.getGeneratedOnboarding()
      .then((response) => {
        if (!mounted) return;
        const payload = response.generated_onboarding ?? emptyPayload();
        setDraft({
          ...emptyPayload(),
          ...payload,
          equipment_pool: Array.isArray(payload.equipment_pool) && payload.equipment_pool.length > 0 ? payload.equipment_pool : ["dumbbell", "bodyweight"],
          movement_restrictions: Array.isArray(payload.movement_restrictions) && payload.movement_restrictions.length > 0
            ? payload.movement_restrictions
            : ["none"],
          weakpoint_targets: Array.isArray(payload.weakpoint_targets) ? payload.weakpoint_targets.slice(0, 2) : [],
          disliked_tags: {
            disliked_exercises: payload.disliked_tags?.disliked_exercises ?? [],
            disliked_equipment: payload.disliked_tags?.disliked_equipment ?? [],
          },
        });
        setStatus(
          response.generated_onboarding_complete
            ? `Generated onboarding complete (${response.profile_completeness}).`
            : `Generated onboarding recommended (${response.profile_completeness}). Missing: ${response.missing_fields.join(", ") || "none"}.`,
        );
      })
      .catch((error) => {
        if (!mounted) return;
        const detail = error instanceof Error ? error.message : "Failed to load generated onboarding.";
        setStatus(detail);
      })
      .finally(() => {
        if (!mounted) return;
        setIsLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const validationError = useMemo(() => {
    if (!draft.target_days || draft.target_days < 2 || draft.target_days > 5) {
      return "Target days must be between 2 and 5.";
    }
    if (!Array.isArray(draft.equipment_pool) || draft.equipment_pool.length === 0) {
      return "Select at least one equipment tag.";
    }
    if (draft.equipment_pool.includes("full_gym")) {
      return "Use canonical equipment tags only. 'full_gym' is not allowed.";
    }
    if ((draft.weakpoint_targets ?? []).length > 2) {
      return "Select at most 2 weakpoint targets.";
    }
    return null;
  }, [draft]);

  async function save() {
    if (validationError || isSaving) return;
    setIsSaving(true);
    setStatus("Saving generated onboarding...");
    try {
      const response = await api.saveGeneratedOnboarding({
        generated_onboarding: {
          ...draft,
          movement_restrictions: normalizeMovementRestrictions(draft.movement_restrictions ?? []),
          weakpoint_targets: (draft.weakpoint_targets ?? []).slice(0, 2),
        },
        mark_complete: true,
      });
      setStatus(
        response.generated_onboarding_complete
          ? "Generated onboarding saved and marked complete."
          : `Saved. Missing fields: ${response.missing_fields.join(", ") || "none"}.`,
      );
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Failed to save generated onboarding.";
      setStatus(detail);
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="ui-title-page">Generated Plan Preferences</h1>
      <p className="text-sm text-zinc-400">
        Recommended to improve plan fit. You can still generate with defaults.
      </p>

      <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4 space-y-4">
        <label className="flex flex-col gap-1 text-sm text-zinc-200">
          <span>Goal mode</span>
          <select className="ui-select" value={draft.goal_mode ?? "hypertrophy"} onChange={(e) => setDraft((prev) => ({ ...prev, goal_mode: e.target.value as GeneratedOnboardingPayload["goal_mode"] }))}>
            <option value="hypertrophy">Hypertrophy</option>
            <option value="strength">Strength</option>
            <option value="size_strength">Size + Strength</option>
          </select>
        </label>

        <label className="flex flex-col gap-1 text-sm text-zinc-200">
          <span>Target days</span>
          <select className="ui-select" value={String(draft.target_days ?? 3)} onChange={(e) => setDraft((prev) => ({ ...prev, target_days: Number(e.target.value) as 2 | 3 | 4 | 5 }))}>
            {[2, 3, 4, 5].map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
        </label>

        <label className="flex flex-col gap-1 text-sm text-zinc-200">
          <span>Session time</span>
          <select className="ui-select" value={draft.session_time_band_source ?? "50_70"} onChange={(e) => setDraft((prev) => ({ ...prev, session_time_band_source: e.target.value as GeneratedOnboardingPayload["session_time_band_source"] }))}>
            <option value="30_45">30-45 min</option>
            <option value="50_70">50-70 min</option>
            <option value="75_100">75-100 min</option>
          </select>
        </label>

        <label className="flex flex-col gap-1 text-sm text-zinc-200">
          <span>Training status</span>
          <select className="ui-select" value={draft.training_status ?? "normal"} onChange={(e) => setDraft((prev) => ({ ...prev, training_status: e.target.value as GeneratedOnboardingPayload["training_status"] }))}>
            <option value="new">New</option>
            <option value="returning">Returning</option>
            <option value="normal">Normal</option>
            <option value="advanced">Advanced</option>
          </select>
        </label>

        <label className="flex items-center gap-2 text-sm text-zinc-200">
          <input
            type="checkbox"
            checked={draft.trained_consistently_last_4_weeks === true}
            onChange={(e) => setDraft((prev) => ({ ...prev, trained_consistently_last_4_weeks: e.target.checked }))}
          />
          Trained consistently in the last 4 weeks
        </label>

        <div className="space-y-2">
          <p className="text-sm text-zinc-200">Equipment (at least one)</p>
          <div className="flex flex-wrap gap-2">
            {EQUIPMENT_TAGS.map((tag) => {
              const active = draft.equipment_pool.includes(tag);
              return (
                <button key={tag} type="button" className={`rounded-full border px-2 py-1 text-xs ${active ? "border-red-400 bg-red-500/20 text-red-100" : "border-zinc-700 text-zinc-300"}`} onClick={() => setDraft((prev) => ({ ...prev, equipment_pool: toggleTag(prev.equipment_pool, tag) }))}>
                  {tag}
                </button>
              );
            })}
          </div>
        </div>

        <div className="space-y-2">
          <p className="text-sm text-zinc-200">Movement restrictions</p>
          <div className="flex flex-wrap gap-2">
            {MOVEMENT_RESTRICTIONS.map((tag) => {
              const active = draft.movement_restrictions.includes(tag);
              return (
                <button
                  key={tag}
                  type="button"
                  className={`rounded-full border px-2 py-1 text-xs ${active ? "border-red-400 bg-red-500/20 text-red-100" : "border-zinc-700 text-zinc-300"}`}
                  onClick={() => setDraft((prev) => ({
                    ...prev,
                    movement_restrictions: normalizeMovementRestrictions(toggleTag(prev.movement_restrictions, tag)),
                  }))}
                >
                  {tag}
                </button>
              );
            })}
          </div>
        </div>

        <label className="flex flex-col gap-1 text-sm text-zinc-200">
          <span>Recovery modifier</span>
          <select className="ui-select" value={draft.recovery_modifier ?? "normal"} onChange={(e) => setDraft((prev) => ({ ...prev, recovery_modifier: e.target.value as GeneratedOnboardingPayload["recovery_modifier"] }))}>
            <option value="low">Low</option>
            <option value="normal">Normal</option>
            <option value="high">High</option>
          </select>
        </label>

        <div className="space-y-2">
          <p className="text-sm text-zinc-200">Weakpoint targets (max 2)</p>
          <div className="flex flex-wrap gap-2">
            {WEAKPOINT_TAGS.map((tag) => {
              const active = draft.weakpoint_targets.includes(tag);
              return (
                <button
                  key={tag}
                  type="button"
                  className={`rounded-full border px-2 py-1 text-xs ${active ? "border-red-400 bg-red-500/20 text-red-100" : "border-zinc-700 text-zinc-300"}`}
                  onClick={() => setDraft((prev) => {
                    const next = toggleTag(prev.weakpoint_targets, tag);
                    return { ...prev, weakpoint_targets: next.slice(0, 2) };
                  })}
                >
                  {tag}
                </button>
              );
            })}
          </div>
        </div>

        <label className="flex flex-col gap-1 text-sm text-zinc-200">
          <span>Preference bias</span>
          <select className="ui-select" value={draft.preference_bias ?? "mixed"} onChange={(e) => setDraft((prev) => ({ ...prev, preference_bias: e.target.value as GeneratedOnboardingPayload["preference_bias"] }))}>
            <option value="free_weights">Free weights</option>
            <option value="machines_cables">Machines & cables</option>
            <option value="mixed">Mixed</option>
          </select>
        </label>

        <label className="flex flex-col gap-1 text-sm text-zinc-200">
          <span>Bodyweight exercise comfort</span>
          <select className="ui-select" value={draft.bodyweight_exercise_comfort ?? "mixed"} onChange={(e) => setDraft((prev) => ({ ...prev, bodyweight_exercise_comfort: e.target.value as GeneratedOnboardingPayload["bodyweight_exercise_comfort"] }))}>
            <option value="comfortable">Comfortable</option>
            <option value="mixed">Mixed</option>
            <option value="limited">Limited</option>
          </select>
        </label>

        <div className="space-y-2">
          <p className="text-sm text-zinc-200">Disliked exercise tags</p>
          <div className="flex flex-wrap gap-2">
            {DISLIKED_EXERCISE_TAGS.map((tag) => {
              const active = draft.disliked_tags?.disliked_exercises?.includes(tag) ?? false;
              return (
                <button
                  key={tag}
                  type="button"
                  className={`rounded-full border px-2 py-1 text-xs ${active ? "border-red-400 bg-red-500/20 text-red-100" : "border-zinc-700 text-zinc-300"}`}
                  onClick={() => setDraft((prev) => ({
                    ...prev,
                    disliked_tags: {
                      disliked_exercises: toggleTag(prev.disliked_tags?.disliked_exercises ?? [], tag),
                      disliked_equipment: prev.disliked_tags?.disliked_equipment ?? [],
                    },
                  }))}
                >
                  {tag}
                </button>
              );
            })}
          </div>
        </div>

        <div className="space-y-2">
          <p className="text-sm text-zinc-200">Disliked equipment tags</p>
          <div className="flex flex-wrap gap-2">
            {EQUIPMENT_TAGS.map((tag) => {
              const active = draft.disliked_tags?.disliked_equipment?.includes(tag) ?? false;
              return (
                <button
                  key={tag}
                  type="button"
                  className={`rounded-full border px-2 py-1 text-xs ${active ? "border-red-400 bg-red-500/20 text-red-100" : "border-zinc-700 text-zinc-300"}`}
                  onClick={() => setDraft((prev) => ({
                    ...prev,
                    disliked_tags: {
                      disliked_exercises: prev.disliked_tags?.disliked_exercises ?? [],
                      disliked_equipment: toggleTag(prev.disliked_tags?.disliked_equipment ?? [], tag),
                    },
                  }))}
                >
                  {tag}
                </button>
              );
            })}
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <label className="flex flex-col gap-1 text-sm text-zinc-200">
            <span>Height (cm, optional)</span>
            <input className="ui-input" type="number" min={120} max={230} value={draft.height_cm ?? ""} onChange={(e) => setDraft((prev) => ({ ...prev, height_cm: e.target.value ? Number(e.target.value) : null }))} />
          </label>
          <label className="flex flex-col gap-1 text-sm text-zinc-200">
            <span>Bodyweight (kg, optional)</span>
            <input className="ui-input" type="number" min={35} max={250} value={draft.bodyweight_kg ?? ""} onChange={(e) => setDraft((prev) => ({ ...prev, bodyweight_kg: e.target.value ? Number(e.target.value) : null }))} />
          </label>
        </div>
      </div>

      {validationError ? <p className="text-sm text-red-300">{validationError}</p> : null}
      <p className="text-sm text-zinc-300">{status}</p>
      <div className="flex items-center gap-2">
        <Button onClick={save} disabled={isSaving || isLoading || Boolean(validationError)}>
          {isSaving ? "Saving..." : "Save generated onboarding"}
        </Button>
        <Link className="text-sm text-zinc-300 underline decoration-zinc-500 underline-offset-2" href="/week">
          Back to Week Plan
        </Link>
      </div>
    </div>
  );
}
