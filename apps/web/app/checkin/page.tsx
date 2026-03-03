"use client";

import { FormEvent, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

function mondayOfCurrentWeek(): string {
  const now = new Date();
  const day = now.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  const monday = new Date(now);
  monday.setDate(now.getDate() + diff);
  return monday.toISOString().slice(0, 10);
}

function resolveStatusTone(status: string): "green" | "yellow" | "red" {
  const lowered = status.toLowerCase();
  if (lowered.includes("saved")) {
    return "green";
  }
  if (lowered.includes("failed")) {
    return "red";
  }
  return "yellow";
}

export default function CheckinPage() {
  const defaultWeekStart = useMemo(() => mondayOfCurrentWeek(), []);
  const [weekStart, setWeekStart] = useState(defaultWeekStart);
  const [bodyWeight, setBodyWeight] = useState("82.0");
  const [adherenceScore, setAdherenceScore] = useState("4");
  const [notes, setNotes] = useState("");
  const [status, setStatus] = useState("Idle");
  const statusTone = resolveStatusTone(status);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setStatus("Saving check-in...");

    try {
      await api.weeklyCheckin({
        week_start: weekStart,
        body_weight: Number(bodyWeight),
        adherence_score: Number(adherenceScore),
        notes: notes || undefined,
      });
      setStatus("Weekly check-in saved");
    } catch {
      setStatus("Check-in failed. Ensure week_start is Monday and not in the future.");
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="ui-title-page">Weekly Check-In</h1>
      <div className="main-card main-card--module main-card--accent spacing-grid spacing-grid--tight">
        <div className="telemetry-header">
          <p className="telemetry-kicker">Check-In State</p>
          <p className="telemetry-status">
            <span className={`status-dot status-dot--${statusTone}`} /> {status}
          </p>
        </div>
        <p className="telemetry-meta">Capture weekly recovery and adherence markers before generating the next cycle.</p>
      </div>
      <form className="main-card main-card--module spacing-grid" onSubmit={handleSubmit}>
        <p className="telemetry-kicker">Weekly Inputs</p>
        <label className="space-y-1 text-xs text-zinc-300">
          <span>Week Start (Monday)</span>
          <input
            className="ui-input"
            onChange={(event) => setWeekStart(event.target.value)}
            type="date"
            value={weekStart}
          />
        </label>

        <label className="space-y-1 text-xs text-zinc-300">
          <span>Bodyweight</span>
          <input
            className="ui-input"
            min="0.1"
            onChange={(event) => setBodyWeight(event.target.value)}
            step="0.1"
            type="number"
            value={bodyWeight}
          />
        </label>

        <label className="space-y-1 text-xs text-zinc-300">
          <span>Adherence Score (1-5)</span>
          <select
            className="ui-select"
            onChange={(event) => setAdherenceScore(event.target.value)}
            value={adherenceScore}
          >
            <option value="1">1</option>
            <option value="2">2</option>
            <option value="3">3</option>
            <option value="4">4</option>
            <option value="5">5</option>
          </select>
        </label>

        <label className="space-y-1 text-xs text-zinc-300">
          <span>Notes (optional)</span>
          <textarea
            className="ui-textarea"
            onChange={(event) => setNotes(event.target.value)}
            rows={3}
            value={notes}
          />
        </label>

        <Button className="w-full" type="submit">
          Save Check-In
        </Button>
      </form>
      <div className="grid grid-cols-3 gap-2">
        <div className="main-card main-card--shell">
          <p className="telemetry-kicker">Sleep</p>
          <p className="telemetry-status">
            <span className="status-dot status-dot--green" /> Stable
          </p>
        </div>
        <div className="main-card main-card--shell">
          <p className="telemetry-kicker">Stress</p>
          <p className="telemetry-status">
            <span className="status-dot status-dot--yellow" /> Moderate
          </p>
        </div>
        <div className="main-card main-card--shell">
          <p className="telemetry-kicker">Readiness</p>
          <p className="telemetry-status">
            <span className="status-dot status-dot--red" /> Watch
          </p>
        </div>
      </div>
    </div>
  );
}
