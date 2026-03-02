"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

export default function WeekPage() {
  const [plan, setPlan] = useState("Generate a weekly plan.");

  async function generate() {
    try {
      const data = await api.generateWeek();
      setPlan(JSON.stringify(data, null, 2));
    } catch {
      setPlan("Failed. Ensure onboarding completed and token exists.");
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Week Plan</h1>
      <div className="main-card">
        <Button className="w-full" onClick={generate}>
          Generate Week
        </Button>
      </div>
      <pre className="main-card overflow-x-auto text-xs text-zinc-200">{plan}</pre>
    </div>
  );
}
