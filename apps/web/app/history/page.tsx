"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { API_BASE_URL } from "@/lib/env";

export default function HistoryPage() {
  const [history, setHistory] = useState("No exercise history loaded.");
  const weeklyTrend = [58, 64, 61, 69, 73, 71, 78, 82];
  const readinessMix = [52, 33, 15];

  async function loadHistory() {
    const token = localStorage.getItem("hypertrophy_token");
    if (!token) {
      setHistory("Missing token. Complete onboarding first.");
      return;
    }

    const res = await fetch(`${API_BASE_URL}/history/exercise/bench`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (!res.ok) {
      setHistory("No history yet for bench.");
      return;
    }

    const data = await res.json();
    setHistory(JSON.stringify(data, null, 2));
  }

  return (
    <div className="space-y-4">
      <h1 className="ui-title-page">History</h1>
      <div className="grid grid-cols-2 gap-3">
        <div className="main-card main-card--shell">
          <p className="telemetry-kicker">Adherence</p>
          <p className="telemetry-value">92% over 30 days</p>
        </div>
        <div className="main-card main-card--module main-card--accent">
          <p className="telemetry-kicker">Fatigue</p>
          <p className="telemetry-status">
            <span className="status-dot status-dot--yellow" /> Elevated
          </p>
        </div>
      </div>
      <div className="main-card main-card--module">
        <p className="telemetry-kicker mb-2">History Controls</p>
        <Button className="w-full" onClick={loadHistory}>
          Load Bench History
        </Button>
      </div>
      <div className="main-card main-card--module spacing-grid spacing-grid--tight">
        <p className="telemetry-kicker">History Output</p>
        <pre className="overflow-x-auto text-xs text-zinc-200">{history}</pre>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <div className="main-card main-card--shell spacing-grid spacing-grid--tight">
          <p className="telemetry-kicker">Volume Sparkline</p>
          <div className="flex items-end gap-1 h-16">
            {weeklyTrend.map((value, index) => (
              <div
                key={`trend-${value}-${index}`}
                className="flex-1 rounded-sm bg-zinc-700/70"
                style={{ height: `${Math.max(20, Math.round((value / 85) * 100))}%` }}
                aria-label={`Week ${index + 1} volume ${value}`}
                title={`Week ${index + 1}: ${value}`}
              />
            ))}
          </div>
          <p className="telemetry-meta">Last 8 weeks</p>
        </div>

        <div className="main-card main-card--module main-card--accent spacing-grid spacing-grid--tight">
          <p className="telemetry-kicker">PR Highlights</p>
          <div className="space-y-1 text-xs text-zinc-200">
            <p className="flex items-center justify-between"><span>Bench Press</span><span className="inline-flex items-center gap-2"><span className="status-dot status-dot--green" />+15 lb</span></p>
            <p className="flex items-center justify-between"><span>Romanian Deadlift</span><span className="inline-flex items-center gap-2"><span className="status-dot status-dot--green" />+20 lb</span></p>
            <p className="flex items-center justify-between"><span>Incline DB Press</span><span className="inline-flex items-center gap-2"><span className="status-dot status-dot--green" />+10 lb</span></p>
          </div>
          <p className="telemetry-meta">Window: 8 weeks</p>
        </div>

        <div className="main-card main-card--shell spacing-grid spacing-grid--tight">
          <p className="telemetry-kicker">Readiness Mix</p>
          <div className="h-3 w-full overflow-hidden rounded-full border border-white/10 bg-zinc-900/80 flex">
            <div className="bg-zinc-300/85" style={{ width: `${readinessMix[0]}%` }} />
            <div className="bg-zinc-500/85" style={{ width: `${readinessMix[1]}%` }} />
            <div className="bg-zinc-700/85" style={{ width: `${readinessMix[2]}%` }} />
          </div>
          <p className="telemetry-meta">High {readinessMix[0]}% · Medium {readinessMix[1]}% · Low {readinessMix[2]}%</p>
        </div>
      </div>
    </div>
  );
}
