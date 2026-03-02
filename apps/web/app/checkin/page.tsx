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

export default function CheckinPage() {
  const defaultWeekStart = useMemo(() => mondayOfCurrentWeek(), []);
  const [weekStart, setWeekStart] = useState(defaultWeekStart);
  const [bodyWeight, setBodyWeight] = useState("82.0");
  const [adherenceScore, setAdherenceScore] = useState("4");
  const [notes, setNotes] = useState("");
  const [status, setStatus] = useState("Idle");

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
      <h1 className="text-xl font-semibold">Weekly Check-In</h1>
      <form className="main-card space-y-3" onSubmit={handleSubmit}>
        <label className="space-y-1 text-xs text-zinc-300">
          <span>Week Start (Monday)</span>
          <input
            className="w-full rounded-md bg-zinc-900 p-2 text-white"
            onChange={(event) => setWeekStart(event.target.value)}
            type="date"
            value={weekStart}
          />
        </label>

        <label className="space-y-1 text-xs text-zinc-300">
          <span>Bodyweight</span>
          <input
            className="w-full rounded-md bg-zinc-900 p-2 text-white"
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
            className="w-full rounded-md bg-zinc-900 p-2 text-white"
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
            className="w-full rounded-md bg-zinc-900 p-2 text-white"
            onChange={(event) => setNotes(event.target.value)}
            rows={3}
            value={notes}
          />
        </label>

        <Button className="w-full" type="submit">
          Save Check-In
        </Button>
      </form>
      <p className="text-sm text-zinc-300">Status: {status}</p>
    </div>
  );
}
