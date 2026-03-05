"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { UiIcon } from "@/components/ui/icons";
import { api, getProgramDisplayName, type ProgramTemplateOption } from "@/lib/api";

export default function WeekPage() {
  const [plan, setPlan] = useState("Generate a weekly plan.");
  const [programs, setPrograms] = useState<ProgramTemplateOption[]>([]);
  const [selectedProgramId, setSelectedProgramId] = useState<string | null>(null);

  async function generate() {
    try {
      const reviewStatus = await api.getWeeklyReviewStatus();
      if (reviewStatus.today_is_sunday && reviewStatus.review_required) {
        setPlan("Sunday review required. Open Check-In, submit weekly review, then generate the next week.");
        return;
      }
      const data = await api.generateWeek(selectedProgramId);
      setPlan(JSON.stringify(data, null, 2));
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Unknown error";
      setPlan(`Failed to generate week plan: ${detail}`);
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
      <h1 className="ui-title-page">Week Plan</h1>
      <div className="grid grid-cols-2 gap-3">
        <div className="main-card main-card--shell">
          <p className="telemetry-kicker">Generator</p>
          <p className="telemetry-status">
            <span className="status-dot status-dot--green" /> Ready
          </p>
        </div>
        <div className="main-card main-card--module main-card--accent">
          <p className="telemetry-kicker">Program Source</p>
          <p className="telemetry-value">{selectedProgramId ? "Manual override" : "Auto-select"}</p>
        </div>
      </div>
      <div className="main-card main-card--module">
        <div className="spacing-grid spacing-grid--tight">
          <p className="telemetry-kicker">Generation Controls</p>
          <label htmlFor="week-program" className="ui-meta">Program override (optional)</label>
          <select id="week-program" aria-label="Week program override selector" aria-describedby="week-program-desc" className="ui-select" value={selectedProgramId ?? ""} onChange={(e) => setSelectedProgramId(e.target.value || null)}>
            <option value="">Server-selected — trainer&apos;s recommended program</option>
            {programs.map((p) => <option key={p.id} value={p.id}>{getProgramDisplayName(p)}</option>)}
          </select>
          <p id="week-program-desc" className="text-xs text-zinc-500">Select a program to override the server selection for this generated week.</p>
          <Button aria-label="Generate week plan" className="w-full" onClick={generate}>
            <span className="inline-flex items-center gap-2">
              <UiIcon name="plan" className="ui-icon--action" />
              Generate Week
            </span>
          </Button>
        </div>
      </div>
      <div className="main-card main-card--module spacing-grid spacing-grid--tight">
        <p className="telemetry-kicker">Plan Output</p>
        <pre className="overflow-x-auto text-xs text-zinc-200">{plan}</pre>
      </div>
    </div>
  );
}
