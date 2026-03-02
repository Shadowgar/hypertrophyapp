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
      <h1 className="text-xl font-semibold">History</h1>
      <div className="main-card">
        <Button className="w-full" onClick={loadHistory}>
          Load Bench History
        </Button>
      </div>
      <pre className="main-card overflow-x-auto text-xs text-zinc-200">{history}</pre>
    </div>
  );
}
