"use client";

import Link from "next/link";
import { FormEvent, useEffect, useRef, useState } from "react";
import { api, ApiError, getToken, type HistoryWeeklyCheckinEntry, type WeeklyCheckinPayload } from "@/lib/api";
import { canonicalLoad, displayLoad } from "@/lib/appearance";
import { useAppearance } from "./appearance-provider";
import { Button } from "./ui/button";

type SaveState = "idle" | "pending" | "saved" | "uncertain";
const adherence = ["Missed most", "About a quarter", "About half", "Most", "All"];

export function CheckinEntry() {
  const { preferences } = useAppearance();
  const unit = preferences.weight_unit;
  const [weight, setWeight] = useState("");
  const canonicalWeight = useRef<number | null>(null);
  const [score, setScore] = useState("");
  const [notes, setNotes] = useState("");
  const [week, setWeek] = useState<string | null>(null);
  const [state, setState] = useState<SaveState>("idle");
  const [message, setMessage] = useState("Loading your local week…");
  const [loadError, setLoadError] = useState(false);
  const [reload, setReload] = useState(0);
  const [entries, setEntries] = useState<HistoryWeeklyCheckinEntry[]>([]);
  const operation = useRef(0);
  const mounted = useRef(false);
  const active = useRef(false);
  const loadedToken = useRef<string | null>(null);
  const frozen = useRef<{ token: string | null; payload: WeeklyCheckinPayload; known: Set<string> } | null>(null);
  useEffect(() => {
    if (canonicalWeight.current !== null) setWeight(String(displayLoad(canonicalWeight.current, unit)));
  }, [unit]);
  useEffect(() => {
    mounted.current = true;
    const token = getToken();
    const version = ++operation.current;
    const retire = () => { ++operation.current; };
    const current = () => mounted.current && version === operation.current && token === getToken();
    setLoadError(false); setWeek(null); setMessage("Loading your local week…");
    Promise.all([api.getSchedulingContext(Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC"), api.getWeeklyCheckinHistory()])
      .then(([clock, history]) => {
        if (!current()) return;
        loadedToken.current = token; setWeek(clock.week_start); setEntries(history.entries);
        setMessage("Report only what you know. Check-in is optional for training.");
      }).catch(() => {
        if (!current()) return;
        setLoadError(true); setMessage("Could not load your check-in. Your entries are still here.");
      });
    return () => { mounted.current = false; retire(); };
  }, [reload]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (active.current || state === "uncertain" || state === "saved" || !week || loadedToken.current !== getToken()) return;
    if (!weight.trim() || canonicalWeight.current === null || canonicalWeight.current <= 0 || !Number.isFinite(canonicalWeight.current) || !score) {
      setMessage("Enter a measured bodyweight and select what actually happened before saving."); return;
    }
    const command = { token: getToken(), payload: { week_start: week, body_weight: canonicalWeight.current, adherence_score: Number(score), ...(notes.trim() ? { notes: notes.trim() } : {}) }, known: new Set(entries.map(entry => entry.created_at)) };
    frozen.current = command; active.current = true; setState("pending"); setMessage("Saving check-in…");
    try {
      await api.weeklyCheckin(command.payload);
      if (!mounted.current || command.token !== getToken()) return;
      setState("saved"); setMessage("Check-in saved.");
    } catch (error) {
      if (!mounted.current || command.token !== getToken()) return;
      if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
        setState("idle"); frozen.current = null; setMessage("Check-in was not saved. Review your entries and retry.");
      } else {
        setState("uncertain"); setMessage("Save result unknown. Check the saved result before sending anything again.");
      }
    } finally { active.current = false; }
  }

  async function reconcile() {
    const command = frozen.current;
    if (!command || command.token !== getToken() || active.current) return;
    active.current = true; setMessage("Checking the saved result…");
    try {
      const history = await api.getWeeklyCheckinHistory();
      if (!mounted.current || command !== frozen.current || command.token !== getToken()) return;
      const found = history.entries.some(entry => !command.known.has(entry.created_at) && entry.week_start === command.payload.week_start && entry.body_weight === command.payload.body_weight && entry.adherence_score === command.payload.adherence_score && (entry.notes || "") === (command.payload.notes || ""));
      setEntries(history.entries);
      if (found) { setState("saved"); setMessage("Check-in saved."); }
      else setMessage("Save result unknown. No matching new check-in is visible yet. Check again or review History; nothing has been resent.");
    } catch {
      if (mounted.current && command.token === getToken()) setMessage("Save result unknown. Could not check History. Try checking again; nothing has been resent.");
    } finally { active.current = false; }
  }

  return <section className="ux-card space-y-4" aria-labelledby="checkin-report-title">
    <div><h2 id="checkin-report-title">Your weekly check-in</h2><p className="ux-muted">{week ? `Week of ${week}` : "Checking your local calendar"}</p></div>
    <p role="status" aria-live="polite" className={state === "saved" ? "ux-saved" : state === "uncertain" || loadError ? "ux-warning" : "ux-muted"}>{message}</p>
    {loadError ? <Button variant="secondary" onClick={() => setReload(value => value + 1)}>Retry check-in load</Button> : null}
    {entries.some(entry => entry.week_start === week) && state !== "saved" ? <p className="ux-muted">You have a check-in for this week. <Link href="/history">Review saved reports in History</Link> before adding another.</p> : null}
    <form onSubmit={submit} className="space-y-4">
      <fieldset disabled={!week || state !== "idle"} className="space-y-4">
        <label className="ux-field">Bodyweight ({unit})<input type="number" min="0.1" step="any" inputMode="decimal" value={weight} onChange={event => { const value = event.target.value; setWeight(value); canonicalWeight.current = value.trim() ? canonicalLoad(Number(value), unit) : null; }} /></label>
        <label className="ux-field">How many planned sessions did you complete?<select value={score} onChange={event => setScore(event.target.value)}><option value="">Choose what actually happened</option>{adherence.map((label, index) => <option key={label} value={index + 1}>{label}</option>)}</select></label>
        <label className="ux-field">Notes (optional)<textarea rows={3} value={notes} onChange={event => setNotes(event.target.value)} /></label>
        <Button type="submit" disabled={!week || state !== "idle"}>{state === "pending" ? "Saving check-in…" : "Save check-in"}</Button>
      </fieldset>
    </form>
    {state === "uncertain" ? <Button variant="secondary" onClick={() => void reconcile()}>Check saved result</Button> : null}
    {state === "saved" ? <div className="flex flex-wrap gap-3"><Link className="ux-button ux-button-primary px-4" href="/today">Back to Today</Link><Link className="ux-button ux-button-secondary px-4" href="/history">View History</Link></div> : <Link href="/today">Skip check-in and open Today</Link>}
  </section>;
}
