"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { API_BASE_URL } from "@/lib/env";

export default function HistoryPage() {
  const [history, setHistory] = useState("No exercise history loaded.");

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
          <p className="ui-label">Adherence</p>
          <p className="text-sm text-zinc-200">92% over 30 days</p>
        </div>
        <div className="main-card main-card--module main-card--accent">
          <p className="ui-label">Fatigue</p>
          <p className="inline-flex items-center gap-2 text-sm text-zinc-200">
            <span className="status-dot status-dot--yellow" /> Elevated
          </p>
        </div>
      </div>
      <div className="main-card main-card--module">
        <Button className="w-full" onClick={loadHistory}>
          Load Bench History
        </Button>
      </div>
      <pre className="main-card main-card--module overflow-x-auto text-xs text-zinc-200">{history}</pre>
    </div>
  );
}
