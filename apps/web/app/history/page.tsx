"use client";

import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { UiIcon } from "@/components/ui/icons";
import { api, type HistoryWeeklyCheckinEntry } from "@/lib/api";
import { API_BASE_URL } from "@/lib/env";

export default function HistoryPage() {
  const [history, setHistory] = useState("No exercise history loaded.");
  const [weeklyCheckins, setWeeklyCheckins] = useState<HistoryWeeklyCheckinEntry[]>([]);
  const [trendStatus, setTrendStatus] = useState("Loading trend data...");

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const payload = await api.getWeeklyCheckinHistory(12);
        if (!mounted) {
          return;
        }
        setWeeklyCheckins(payload.entries ?? []);
        setTrendStatus(payload.entries.length > 0 ? "" : "No weekly check-ins yet.");
      } catch {
        if (!mounted) {
          return;
        }
        setWeeklyCheckins([]);
        setTrendStatus("Unable to load weekly check-in trends.");
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  const adherencePct = useMemo(() => {
    if (weeklyCheckins.length === 0) {
      return 0;
    }
    const averageScore = weeklyCheckins.reduce((sum, item) => sum + item.adherence_score, 0) / weeklyCheckins.length;
    return Math.round((averageScore / 5) * 100);
  }, [weeklyCheckins]);

  const bodyWeightTrend = useMemo(() => weeklyCheckins.map((item) => item.body_weight), [weeklyCheckins]);

  const adherenceMix = useMemo(() => {
    if (weeklyCheckins.length === 0) {
      return [0, 0, 0] as const;
    }
    const high = weeklyCheckins.filter((item) => item.adherence_score >= 4).length;
    const medium = weeklyCheckins.filter((item) => item.adherence_score === 3).length;
    const low = weeklyCheckins.filter((item) => item.adherence_score <= 2).length;
    const total = weeklyCheckins.length;
    return [
      Math.round((high / total) * 100),
      Math.round((medium / total) * 100),
      Math.round((low / total) * 100),
    ] as const;
  }, [weeklyCheckins]);

  const [mixHigh, mixMedium, mixLow] = adherenceMix;

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
          <p className="telemetry-value">{adherencePct}% recent average</p>
        </div>
        <div className="main-card main-card--module main-card--accent">
          <p className="telemetry-kicker">Check-ins Logged</p>
          <p className="telemetry-value">{weeklyCheckins.length}</p>
        </div>
      </div>
      <div className="main-card main-card--module">
        <p className="telemetry-kicker mb-2">History Controls</p>
        <Button className="w-full" onClick={loadHistory}>
          <span className="inline-flex items-center gap-2">
            <UiIcon name="history" className="ui-icon--action" />
            Load Bench History
          </span>
        </Button>
      </div>
      <div className="main-card main-card--module spacing-grid spacing-grid--tight">
        <p className="telemetry-kicker">History Output</p>
        <pre className="overflow-x-auto text-xs text-zinc-200">{history}</pre>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <div className="main-card main-card--shell spacing-grid spacing-grid--tight">
          <p className="telemetry-kicker">Bodyweight Trend</p>
          <div className="flex items-end gap-1 h-16">
            {bodyWeightTrend.length > 0 ? (
              bodyWeightTrend.map((value, index) => {
                const minValue = Math.min(...bodyWeightTrend);
                const maxValue = Math.max(...bodyWeightTrend);
                const spread = Math.max(0.1, maxValue - minValue);
                const normalized = 25 + ((value - minValue) / spread) * 75;
                return (
                  <div
                    key={`weight-${value}-${index}`}
                    className="flex-1 rounded-sm bg-zinc-700/70"
                    style={{ height: `${Math.round(normalized)}%` }}
                    aria-label={`Week ${index + 1} bodyweight ${value}`}
                    title={`Week ${index + 1}: ${value} kg`}
                  />
                );
              })
            ) : (
              <div className="text-xs text-zinc-500">No trend data</div>
            )}
          </div>
          <p className="telemetry-meta">Last {Math.max(weeklyCheckins.length, 0)} check-ins</p>
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
            <div className="bg-zinc-300/85" style={{ width: `${mixHigh}%` }} />
            <div className="bg-zinc-500/85" style={{ width: `${mixMedium}%` }} />
            <div className="bg-zinc-700/85" style={{ width: `${mixLow}%` }} />
          </div>
          <p className="telemetry-meta">High {mixHigh}% · Medium {mixMedium}% · Low {mixLow}%</p>
        </div>
      </div>

      {trendStatus ? <p className="text-xs text-zinc-500">{trendStatus}</p> : null}
    </div>
  );
}
