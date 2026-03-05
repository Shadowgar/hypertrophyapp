"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { UiIcon } from "@/components/ui/icons";
import { api, getProgramDisplayName, type ProgramTemplateOption } from "@/lib/api";
import { API_BASE_URL } from "@/lib/env";

const EQUIPMENT_OPTIONS = ["dumbbell", "barbell", "cable", "machine", "bodyweight"];

const FALLBACK_PROGRAMS: ProgramTemplateOption[] = [
  {
    id: "pure_bodybuilding_full_body",
    name: "Pure Bodybuilding Phase 1 - Full Body",
    split: "full_body",
    days_supported: [2, 3, 4],
    description: "Foundational full body progression with deterministic sessions.",
  },
  {
    id: "pure_bodybuilding_phase_2_full_body_sheet",
    name: "Pure Bodybuilding Phase 2 - Full Body",
    split: "full_body",
    days_supported: [2, 3, 4],
    description: "Phase 2 full-body variant from your reference corpus.",
  },
  {
    id: "pure_bodybuilding_phase_2_ppl_sheet",
    name: "Pure Bodybuilding Phase 2 - PPL",
    split: "ppl",
    days_supported: [2, 3, 4],
    description: "Phase 2 push/pull/legs variant.",
  },
  {
    id: "pure_bodybuilding_phase_2_upper_lower_sheet",
    name: "Pure Bodybuilding Phase 2 - Upper Lower",
    split: "upper_lower",
    days_supported: [2, 3, 4],
    description: "Phase 2 upper/lower variant.",
  },
  {
    id: "the_bodybuilding_transformation_system_beginner",
    name: "Bodybuilding Transformation System - Beginner",
    split: "full_body",
    days_supported: [2, 3, 4],
    description: "Beginner track from the transformation system.",
  },
];

function resolveStatusTone(status: string): "green" | "yellow" | "red" {
  const lowered = status.toLowerCase();
  if (lowered.includes("saved") || lowered.includes("logged in")) {
    return "green";
  }
  if (lowered.includes("failed") || lowered.includes("error")) {
    return "red";
  }
  return "yellow";
}

export default function OnboardingPage() {
  const router = useRouter();
  const [email, setEmail] = useState("athlete@example.com");
  const [password, setPassword] = useState("athlete123");
  const [name, setName] = useState("Athlete");
  const [splitPreference, setSplitPreference] = useState("full_body");
  const [trainingLocation, setTrainingLocation] = useState("home");
  const [equipmentProfile, setEquipmentProfile] = useState<string[]>(["dumbbell"]);
  const [daysAvailable, setDaysAvailable] = useState(5);
  const [programs, setPrograms] = useState<ProgramTemplateOption[]>([]);
  const [programCatalogStatus, setProgramCatalogStatus] = useState("Loading program catalog...");
  const [selectedProgramId, setSelectedProgramId] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const list = await api.listPrograms();
        if (!mounted) {
          return;
        }
        const normalized = Array.isArray(list) && list.length > 0 ? list : FALLBACK_PROGRAMS;
        setPrograms(normalized);
        setProgramCatalogStatus(`Loaded ${normalized.length} training templates.`);
      } catch {
        if (!mounted) {
          return;
        }
        setPrograms(FALLBACK_PROGRAMS);
        setProgramCatalogStatus("Program catalog API unavailable. Using local fallback options.");
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);
  const [showPassword, setShowPassword] = useState(false);
  const [status, setStatus] = useState("Idle");
  const statusTone = resolveStatusTone(status);

  const visiblePrograms = useMemo(() => {
    const scored = programs.map((program) => {
      const splitCompatible = !program.split || program.split === splitPreference;
      const daysCompatible = !Array.isArray(program.days_supported)
        || program.days_supported.length === 0
        || program.days_supported.includes(daysAvailable);

      return {
        program,
        score: (splitCompatible ? 2 : 0) + (daysCompatible ? 1 : 0),
      };
    });

    scored.sort((a, b) => {
      if (a.score !== b.score) {
        return b.score - a.score;
      }
      return getProgramDisplayName(a.program).localeCompare(getProgramDisplayName(b.program));
    });

    return scored.map((entry) => entry.program);
  }, [daysAvailable, programs, splitPreference]);

  useEffect(() => {
    if (selectedProgramId && !visiblePrograms.some((program) => program.id === selectedProgramId)) {
      setSelectedProgramId(null);
    }
  }, [selectedProgramId, visiblePrograms]);

  function toggleEquipment(equipment: string) {
    setEquipmentProfile((prev) => {
      if (prev.includes(equipment)) {
        return prev.filter((item) => item !== equipment);
      }
      return [...prev, equipment];
    });
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setStatus("Registering...");

    try {
      const registerRes = await fetch(`${API_BASE_URL}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, name }),
      });

      let accessToken: string | null = null;
      if (registerRes.ok) {
        const token = (await registerRes.json()) as { access_token: string };
        accessToken = token.access_token;
      } else {
        const loginRes = await fetch(`${API_BASE_URL}/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
        });
        if (!loginRes.ok) {
          setStatus("Registration/login failed");
          return;
        }
        const token = (await loginRes.json()) as { access_token: string };
        accessToken = token.access_token;
      }

      localStorage.setItem("hypertrophy_token", accessToken);

      const profileRes = await fetch(`${API_BASE_URL}/profile`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          name,
          age: 30,
          weight: 82,
          gender: "male",
          split_preference: splitPreference,
          training_location: trainingLocation,
          equipment_profile: equipmentProfile,
          days_available: daysAvailable,
          nutrition_phase: "maintenance",
          calories: 2600,
          protein: 180,
          fat: 70,
          carbs: 280,
          selected_program_id: selectedProgramId,
        }),
      });

      if (!profileRes.ok) {
        setStatus("Profile save failed");
        return;
      }

      setStatus("Onboarding saved");
      router.push("/today");
    } catch {
      setStatus("Network error during onboarding");
    }
  }

  return (
    <div className="space-y-5">
      <h1 className="ui-title-page">Onboarding</h1>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <div className="main-card main-card--module main-card--accent spacing-grid spacing-grid--tight md:col-span-2">
          <div className="telemetry-header">
            <p className="telemetry-kicker">Hypertrophy Setup</p>
            <p className="telemetry-status">
              <span className={`status-dot status-dot--${statusTone}`} /> {status}
            </p>
          </div>
          <p className="telemetry-meta">Create your account, pick your split and constraints, then lock in a program from your ingested template catalog.</p>
        </div>
      </div>

      <form className="main-card main-card--module spacing-grid" onSubmit={handleSubmit}>
        <div className="spacing-grid spacing-grid--tight">
          <p className="telemetry-kicker">Account</p>
          <input aria-label="Full name" className="ui-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Name" />
          <input aria-label="Email address" className="ui-input" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" />
          <div className="space-y-2">
            <input
              className="ui-input"
              type={showPassword ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password"
              aria-label="Password"
            />
            <button
              className="h-8 w-full rounded-md border border-[var(--ui-edge-idle)] bg-[var(--ui-surface-1)] px-3 text-xs text-zinc-100 transition-colors hover:border-[var(--ui-edge-active)]"
              onClick={() => setShowPassword((prev) => !prev)}
              type="button"
            >
              <span className="inline-flex items-center gap-2">
                <UiIcon name="settings" className="ui-icon--action" />
                {showPassword ? "Hide Password" : "Show Password"}
              </span>
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <div className="spacing-grid spacing-grid--tight">
            <p className="telemetry-kicker">Training Location</p>
            <select
              className="ui-select"
              value={trainingLocation}
              onChange={(event) => setTrainingLocation(event.target.value)}
            >
              <option value="home">Home</option>
              <option value="gym">Gym</option>
            </select>
          </div>

          <div className="spacing-grid spacing-grid--tight">
            <p className="telemetry-kicker">Days Per Week</p>
            <select
              className="ui-select"
              value={daysAvailable}
              onChange={(event) => setDaysAvailable(Number(event.target.value))}
            >
              <option value={2}>2 days / week</option>
              <option value={3}>3 days / week</option>
              <option value={4}>4 days / week</option>
              <option value={5}>5 days / week</option>
            </select>
          </div>

          <div className="spacing-grid spacing-grid--tight">
            <p className="telemetry-kicker">Split Preference</p>
            <select
              className="ui-select"
              value={splitPreference}
              onChange={(event) => setSplitPreference(event.target.value)}
              aria-label="Split preference"
            >
              <option value="full_body">Full Body</option>
              <option value="ppl">Push Pull Legs</option>
              <option value="upper_lower">Upper Lower</option>
            </select>
          </div>
        </div>

        <div className="spacing-grid spacing-grid--tight">
          <p className="telemetry-kicker">Training Context</p>
          <p className="telemetry-meta">Catalog status: {programCatalogStatus}</p>
        </div>

        <div className="spacing-grid spacing-grid--tight">
          <p className="telemetry-kicker">Program Selection</p>
          <div className="space-y-1">
            <label htmlFor="program-select" className="ui-meta">Program</label>
            <select
              id="program-select"
              className="ui-select"
              value={selectedProgramId ?? ""}
              onChange={(e) => setSelectedProgramId(e.target.value || null)}
              aria-label="Program selector"
              aria-describedby="program-desc"
            >
              <option value="">Default — trainer&apos;s recommended program</option>
              {visiblePrograms.map((p) => (
                <option key={p.id} value={p.id}>
                  {getProgramDisplayName(p)}{Array.isArray(p.days_supported) ? ` (${p.days_supported.join("/")}d)` : ""}
                </option>
              ))}
            </select>
            <p id="program-desc" className="text-xs text-zinc-500">
              {selectedProgramId
                ? (programs.find((p) => p.id === selectedProgramId)?.description ?? "No description available.")
                : "Choose \"Default\" to let the trainer decide the best matching program for you."}
            </p>
          </div>
        </div>

        <div className="space-y-2 rounded-md border border-zinc-800 p-3">
          <p className="telemetry-kicker">Equipment Profile</p>
          <div className="grid grid-cols-2 gap-2 md:grid-cols-5">
            {EQUIPMENT_OPTIONS.map((equipment) => {
              const selected = equipmentProfile.includes(equipment);
              return (
                <button
                  key={equipment}
                  type="button"
                  className={`h-9 rounded-md border px-2 text-xs transition-all ${
                    selected
                      ? "border-[var(--ui-edge-active)] bg-[var(--ui-accent-active)] text-white shadow-[var(--ui-glow-active)]"
                      : "border-[var(--ui-edge-idle)] bg-[var(--ui-surface-1)] text-zinc-200 hover:border-[var(--ui-edge-hover)]"
                  }`}
                  aria-pressed={selected}
                  onClick={() => toggleEquipment(equipment)}
                >
                  {equipment}
                </button>
              );
            })}
          </div>
        </div>

        <Button type="submit" className="w-full">
          <span className="inline-flex items-center gap-2">
            <UiIcon name="save" className="ui-icon--action" />
            Save Onboarding
          </span>
        </Button>
      </form>
      <div className="main-card main-card--shell">
        <p className="telemetry-status">
          <span className={`status-dot status-dot--${statusTone}`} /> Status: {status}
        </p>
      </div>
    </div>
  );
}
