"use client";

import { FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { API_BASE_URL } from "@/lib/env";

const EQUIPMENT_OPTIONS = ["dumbbell", "barbell", "cable", "machine", "bodyweight"];

export default function OnboardingPage() {
  const [email, setEmail] = useState("athlete@example.com");
  const [password, setPassword] = useState("athlete123");
  const [name, setName] = useState("Athlete");
  const [trainingLocation, setTrainingLocation] = useState("home");
  const [equipmentProfile, setEquipmentProfile] = useState<string[]>(["dumbbell"]);
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

      if (!registerRes.ok) {
        setStatus("Registration failed");
        return;
      }

      const token = (await registerRes.json()) as { access_token: string };
      localStorage.setItem("hypertrophy_token", token.access_token);

      const profileRes = await fetch(`${API_BASE_URL}/profile`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token.access_token}`,
        },
        body: JSON.stringify({
          name,
          age: 30,
          weight: 82,
          gender: "male",
          split_preference: "full_body",
          training_location: trainingLocation,
          equipment_profile: equipmentProfile,
          days_available: 3,
          nutrition_phase: "maintenance",
          calories: 2600,
          protein: 180,
          fat: 70,
          carbs: 280,
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
        <input className="w-full rounded-md bg-zinc-900 p-2 text-white" value={name} onChange={(e) => setName(e.target.value)} placeholder="Name" />
        <input className="w-full rounded-md bg-zinc-900 p-2 text-white" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" />
        <input className="w-full rounded-md bg-zinc-900 p-2 text-white" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" />

        <select
          className="w-full rounded-md bg-zinc-900 p-2 text-white"
          value={trainingLocation}
          onChange={(event) => setTrainingLocation(event.target.value)}
        >
          <option value="home">Home</option>
          <option value="gym">Gym</option>
        </select>

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
