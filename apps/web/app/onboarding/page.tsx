"use client";

import { FormEvent, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { API_BASE_URL } from "@/lib/env";

const EQUIPMENT_OPTIONS = ["dumbbell", "barbell", "cable", "machine", "bodyweight"];

export default function OnboardingPage() {
  const [email, setEmail] = useState("athlete@example.com");
  const [password, setPassword] = useState("athlete123");
  const [name, setName] = useState("Athlete");
  const [trainingLocation, setTrainingLocation] = useState("home");
  const [equipmentProfile, setEquipmentProfile] = useState<string[]>(["dumbbell"]);
  const [daysAvailable, setDaysAvailable] = useState(5);
  const [programs, setPrograms] = useState<Array<{id: string; slug: string; name: string; description?: string}>>([]);
  const [selectedProgramId, setSelectedProgramId] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/plan/programs`);
        if (!res.ok) return;
        const data = await res.json();
        // expect { programs: [...] } or array
        const list = Array.isArray(data) ? data : data.programs ?? data.items ?? [];
        if (mounted) setPrograms(list);
      } catch {
        // ignore
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);
  const [showPassword, setShowPassword] = useState(false);
  const [status, setStatus] = useState("Idle");

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
          split_preference: "full_body",
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
      <h1 className="text-xl font-semibold">Onboarding</h1>
      <form className="main-card space-y-3" onSubmit={handleSubmit}>
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
            {showPassword ? "Hide Password" : "Show Password"}
          </Button>
        </div>

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

        <div className="space-y-1">
          <label htmlFor="program-select" className="text-xs text-zinc-400">Program</label>
          <select
            id="program-select"
            className="ui-select"
            value={selectedProgramId ?? ""}
            onChange={(e) => setSelectedProgramId(e.target.value || null)}
            aria-label="Program selector"
            aria-describedby="program-desc"
          >
            <option value="">Default — trainer&apos;s recommended program</option>
            {programs.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
          <p id="program-desc" className="text-xs text-zinc-500">
            {selectedProgramId
              ? (programs.find((p) => p.id === selectedProgramId)?.description ?? "No description available.")
              : "Choose \"Default\" to let the trainer decide the best matching program for you."}
          </p>
        </div>

        <div className="space-y-2 rounded-md border border-zinc-800 p-3">
          <p className="text-xs text-zinc-400">Equipment Profile</p>
          <div className="grid grid-cols-2 gap-2">
            {EQUIPMENT_OPTIONS.map((equipment) => {
              const selected = equipmentProfile.includes(equipment);
              return (
                <Button
                  key={equipment}
                  type="button"
                  variant={selected ? "default" : "secondary"}
                  className="h-8 text-xs"
                  onClick={() => toggleEquipment(equipment)}
                >
                  {equipment}
                </Button>
              );
            })}
          </div>
        </div>

        <Button type="submit" className="w-full">Save Onboarding</Button>
      </form>
      <p className="text-sm text-zinc-300">Status: {status}</p>
    </div>
  );
}
