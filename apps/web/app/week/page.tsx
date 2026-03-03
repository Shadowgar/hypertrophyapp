"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

export default function WeekPage() {
  const [plan, setPlan] = useState("Generate a weekly plan.");
  const [programs, setPrograms] = useState<Array<{id: string; name: string}>>([]);
  const [selectedProgramId, setSelectedProgramId] = useState<string | null>(null);

  async function generate() {
    try {
      const data = await api.generateWeek(selectedProgramId);
      setPlan(JSON.stringify(data, null, 2));
    } catch {
      setPlan("Failed. Ensure onboarding completed and token exists.");
    }
  }

  useEffect(() => {
    let mounted = true;
    api.listPrograms()
      .then((list) => { if (mounted) setPrograms(list); })
      .catch(() => {});
    return () => { mounted = false };
  }, []);

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Week Plan</h1>
      <div className="grid grid-cols-2 gap-3">
        <div className="main-card">
          <p className="text-xs uppercase tracking-wide text-zinc-400">Generator</p>
          <p className="inline-flex items-center gap-2 text-sm text-zinc-200">
            <span className="status-dot status-dot--green" /> Ready
          </p>
        </div>
        <div className="main-card glass-layer--accent">
          <p className="text-xs uppercase tracking-wide text-zinc-400">Program Source</p>
          <p className="text-sm text-zinc-200">{selectedProgramId ? "Manual override" : "Auto-select"}</p>
        </div>
      </div>
      <div className="main-card">
        <div className="space-y-2">
          <label htmlFor="week-program" className="text-xs text-zinc-400">Program override (optional)</label>
          <select id="week-program" aria-label="Week program override selector" aria-describedby="week-program-desc" className="ui-select" value={selectedProgramId ?? ""} onChange={(e) => setSelectedProgramId(e.target.value || null)}>
            <option value="">Server-selected — trainer&apos;s recommended program</option>
            {programs.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <p id="week-program-desc" className="text-xs text-zinc-500">Select a program to override the server selection for this generated week.</p>
          <Button aria-label="Generate week plan" className="w-full" onClick={generate}>
            Generate Week
          </Button>
        </div>
      </div>
      <pre className="main-card overflow-x-auto text-xs text-zinc-200">{plan}</pre>
    </div>
  );
}
