"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { UiIcon } from "@/components/ui/icons";
import { api, getProgramDisplayName, type ProgramTemplateOption } from "@/lib/api";
import { API_BASE_URL } from "@/lib/env";

const EQUIPMENT_OPTIONS = ["dumbbell", "barbell", "cable", "machine", "bodyweight"];

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
        setPrograms(Array.isArray(list) ? list : []);
        setProgramCatalogStatus(
          list.length > 0
            ? `Loaded ${list.length} training templates from reference-derived catalog.`
            : "Program catalog returned no templates.",
        );
      } catch {
        if (!mounted) {
          return;
        }
        setPrograms([]);
        setProgramCatalogStatus("Program catalog unavailable. Confirm API is reachable at /api.");
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
    const splitMatched = programs.filter((program) => !program.split || program.split === splitPreference);
    const splitAndDaysMatched = splitMatched.filter((program) => {
      if (!Array.isArray(program.days_supported) || program.days_supported.length === 0) {
        return true;
      }
      return program.days_supported.includes(daysAvailable);
    });

    if (splitAndDaysMatched.length > 0) {
      return splitAndDaysMatched;
    }
    if (splitMatched.length > 0) {
      return splitMatched;
    }
    return programs;
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

      setStatus(profileRes.ok ? "Onboarding saved" : "Profile save failed");
    } catch {
      setStatus("Network error during onboarding");
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="ui-title-page">Onboarding</h1>
      <div className="grid grid-cols-2 gap-3">
        <div className="main-card main-card--module main-card--accent spacing-grid spacing-grid--tight">
          <div className="telemetry-header">
            <p className="telemetry-kicker">Setup Flow</p>
            <p className="telemetry-status">
              <span className={`status-dot status-dot--${statusTone}`} /> {status}
            </p>
          </div>
          <p className="telemetry-meta">Create account, set profile constraints, and select a training program baseline.</p>
        </div>
        <div className="main-card main-card--shell spacing-grid spacing-grid--tight">
          <p className="telemetry-kicker">Profile Scope</p>
          <p className="telemetry-value">Program + Equipment + Schedule</p>
          <p className="telemetry-meta">Deterministic defaults are applied where fields are not explicitly changed.</p>
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
            <Button
              className="h-8 w-full text-xs"
              onClick={() => setShowPassword((prev) => !prev)}
              type="button"
              variant="secondary"
            >
              <span className="inline-flex items-center gap-2">
                <UiIcon name="settings" className="ui-icon--action" />
                {showPassword ? "Hide Password" : "Show Password"}
              </span>
            </Button>
          </div>
        </div>

        <div className="spacing-grid spacing-grid--tight">
          <p className="telemetry-kicker">Training Context</p>
          <select
            className="ui-select"
            value={trainingLocation}
            onChange={(event) => setTrainingLocation(event.target.value)}
          >
            <option value="home">Home</option>
            <option value="gym">Gym</option>
          </select>

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
                  {getProgramDisplayName(p)}
                </option>
              ))}
            </select>
            <p id="program-desc" className="text-xs text-zinc-500">
              {selectedProgramId
                ? (programs.find((p) => p.id === selectedProgramId)?.description ?? "No description available.")
                : "Choose \"Default\" to let the trainer decide the best matching program for you."}
            </p>
            <p className="text-xs text-zinc-500">{programCatalogStatus}</p>
          </div>
        </div>

        <div className="space-y-2 rounded-md border border-zinc-800 p-3">
          <p className="telemetry-kicker">Equipment Profile</p>
          <div className="ui-segmented ui-segmented--2">
            {EQUIPMENT_OPTIONS.map((equipment) => {
              const selected = equipmentProfile.includes(equipment);
              return (
                <Button
                  key={equipment}
                  type="button"
                  variant="segment"
                  className="h-8 text-xs"
                  aria-pressed={selected}
                  onClick={() => toggleEquipment(equipment)}
                >
                  {equipment}
                </Button>
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
