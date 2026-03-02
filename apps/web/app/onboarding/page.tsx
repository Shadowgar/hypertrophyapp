"use client";

import { FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { API_BASE_URL } from "@/lib/env";

export default function OnboardingPage() {
  const [email, setEmail] = useState("athlete@example.com");
  const [password, setPassword] = useState("athlete123");
  const [name, setName] = useState("Athlete");
  const [status, setStatus] = useState("Idle");

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setStatus("Registering...");

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
        days_available: 3,
        nutrition_phase: "maintenance",
        calories: 2600,
        protein: 180,
        fat: 70,
        carbs: 280,
      }),
    });

    setStatus(profileRes.ok ? "Onboarding saved" : "Profile save failed");
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Onboarding</h1>
      <form className="main-card space-y-3" onSubmit={handleSubmit}>
        <input className="w-full rounded-md bg-zinc-900 p-2 text-white" value={name} onChange={(e) => setName(e.target.value)} placeholder="Name" />
        <input className="w-full rounded-md bg-zinc-900 p-2 text-white" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" />
        <input className="w-full rounded-md bg-zinc-900 p-2 text-white" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" />
        <Button type="submit" className="w-full">Save Onboarding</Button>
      </form>
      <p className="text-sm text-zinc-300">Status: {status}</p>
    </div>
  );
}
