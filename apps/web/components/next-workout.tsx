"use client";

import { useCallback, useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import { WorkoutWorkload, workloadMode } from "@/components/workout-workload";
import { api, ApiError, getProgramDisplayName, getToken, type NextPlannedWorkout } from "@/lib/api";
import { accountScope } from "@/lib/appearance";
import { formatCalendarDate } from "@/lib/calendar-date";

/** Read-only placement preview. The server owns eligibility and every move decision. */
export function NextWorkout({ accountToken, enabled, onMoved, canMoveNow, timeBudgetMinutes }: {
  timeBudgetMinutes?: number | null;
  accountToken: string | null;
  enabled: boolean;
  onMoved: () => void;
  canMoveNow?: () => boolean;
}) {
  const [preview, setPreview] = useState<NextPlannedWorkout | null>(null);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [moving, setMoving] = useState(false);
  const [reload, setReload] = useState(0);
  const [retired, setRetired] = useState(false);
  const [recoveryBlocked, setRecoveryBlocked] = useState(false);
  const epoch = useRef(0);
  const inFlight = useRef(false);
  const recoverySeen = useRef(false);
  const dialog = useRef<HTMLDialogElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const guard = useRef({ enabled, accountToken, canMoveNow });
  useLayoutEffect(() => { guard.current = { enabled, accountToken, canMoveNow }; }, [enabled, accountToken, canMoveNow]);
  const invalidate = useCallback(() => { ++epoch.current; }, []);
  const id = useId();

  function hasRecovery() {
    try {
      const scope = accountScope(getToken()) ?? "guest";
      // Even an unreadable/malformed retained command must not grant mutation permission.
      return localStorage.getItem(`hypertrophy_undo_recovery_v1:${scope}:payload`) !== null;
    } catch { return true; }
  }
  function permitted() {
    return guard.current.enabled && getToken() === accountToken && Boolean(accountToken)
      && !hasRecovery() && (guard.current.canMoveNow?.() ?? true);
  }

  useEffect(() => {
    const generation = ++epoch.current;
    setRetired(false); setConfirming(false); setMoving(false); inFlight.current = false;
    setPreview(null); setLoading(true);
    const blocked = hasRecovery(); recoverySeen.current = blocked; setRecoveryBlocked(blocked);
    let active = true;
    const current = () => active && generation === epoch.current && getToken() === accountToken;
    if (!enabled || !accountToken || blocked) { setLoading(false); return () => { active = false; invalidate(); }; }
    void api.getNextPlannedWorkout().then(value => {
      if (!current()) return;
      if (value && !Array.isArray(value.session?.exercises)) throw new Error("Invalid preview");
      setPreview(value);
    }).catch(() => {
      if (current()) setNotice("The next workout preview could not be loaded. Check the preview again.");
    }).finally(() => { if (current()) setLoading(false); });
    return () => { active = false; invalidate(); };
  }, [accountToken, enabled, reload, invalidate]);

  useEffect(() => {
    const sync = () => {
      if (getToken() !== accountToken) {
        ++epoch.current; setRetired(true); setPreview(null); setConfirming(false); return;
      }
      const blocked = hasRecovery();
      const wasBlocked = recoverySeen.current;
      recoverySeen.current = blocked;
      setRecoveryBlocked(blocked);
      if (blocked) { ++epoch.current; setPreview(null); setConfirming(false); }
      else if (wasBlocked) setReload(value => value + 1);
    };
    window.addEventListener("hypertrophy:auth-token-changed", sync);
    window.addEventListener("storage", sync);
    window.addEventListener("focus", sync);
    return () => {
      window.removeEventListener("hypertrophy:auth-token-changed", sync);
      window.removeEventListener("storage", sync);
      window.removeEventListener("focus", sync);
    };
  }, [accountToken]);

  useEffect(() => {
    if (!confirming) return;
    const element = dialog.current;
    if (!element) return;
    const triggerElement = trigger.current;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    element.showModal();
    return () => {
      element.close(); document.body.style.overflow = previousOverflow;
      if (triggerElement?.isConnected && getToken() === accountToken) triggerElement.focus();
    };
  }, [confirming, accountToken]);

  function openConfirmation() {
    if (!permitted()) { setConfirming(false); recoverySeen.current = hasRecovery(); setRecoveryBlocked(recoverySeen.current); return; }
    if (loading || inFlight.current || !preview?.can_move || !preview.preview_digest) return;
    setNotice(""); setConfirming(true);
  }
  async function move() {
    if (!permitted()) { setConfirming(false); recoverySeen.current = hasRecovery(); setRecoveryBlocked(recoverySeen.current); return; }
    if (inFlight.current || !preview?.can_move || !preview.preview_digest) return;
    const generation = epoch.current;
    const current = () => generation === epoch.current && getToken() === accountToken && guard.current.enabled;
    inFlight.current = true; setMoving(true);
    try {
      await api.moveNextPlannedWorkout({
        plan_id: preview.plan_id, workout_occurrence_id: preview.workout_occurrence_id,
        expected_original_date: preview.original_date, expected_local_today: preview.local_today,
        expected_placement_revision: preview.placement_revision, expected_preview_digest: preview.preview_digest,
        confirmed: true,
      });
      if (!current()) return;
      if (!permitted()) { setConfirming(false); recoverySeen.current = hasRecovery(); setRecoveryBlocked(recoverySeen.current); return; }
      setConfirming(false); setPreview(null);
      onMoved();
    } catch (error) {
      if (!current()) return;
      setConfirming(false);
      setNotice(error instanceof ApiError && error.status === 409
        ? "Your schedule or workout changed. Review the refreshed preview again before confirming."
        : "The move was not confirmed. Check Today and review the refreshed preview before trying again.");
      setReload(value => value + 1);
    } finally {
      if (current()) { inFlight.current = false; setMoving(false); }
    }
  }

  if (!enabled || !accountToken || retired || recoveryBlocked) return null;
  if (loading) return <div className="ux-card" role="status">Checking your next unstarted workout…</div>;
  if (!preview) return notice ? <div className="ux-card space-y-3"><p role="status">{notice}</p><button type="button" className="ux-button ux-button-secondary" onClick={() => setReload(value => value + 1)}>Check next workout</button></div> : null;
  const totalSets = preview.session.exercises.reduce((total, exercise) => total + exercise.sets, 0);
  const counts = `${preview.session.exercises.length} exercises · ${totalSets} working sets`;
  return <section className="ux-card space-y-3" aria-label="Next unstarted workout">
    <p className="ux-eyebrow">Next unstarted workout · read-only preview</p>
    <h2>{preview.session.title}</h2>
    <p className="ux-muted">{preview.program_template_id ? getProgramDisplayName({ id: preview.program_template_id }) : "Program details unavailable"}</p>
    <p>Original date: {formatCalendarDate(preview.original_date)} · {preview.timezone}</p>
    <WorkoutWorkload exercises={preview.session.exercises} timeBudgetMinutes={timeBudgetMinutes} mode={workloadMode(preview.program_template_id, Boolean(preview.session.customized))} />
    <ul className="space-y-2" aria-label="Next workout exercises">{preview.session.exercises.map((exercise, index) => <li key={`${exercise.id}-${index}`} className="flex flex-wrap justify-between gap-2"><span>{exercise.name}</span><span>{exercise.sets} working sets</span></li>)}</ul>
    {!preview.can_move ? <p role="status">{preview.blocked_reason ?? "This workout cannot be moved to today."}</p> : null}
    {notice ? <p role="status">{notice}</p> : null}
    <div className="flex flex-wrap gap-2">
      <button ref={trigger} type="button" className="ux-button ux-button-primary" disabled={!preview.can_move || !preview.preview_digest || moving} onClick={openConfirmation}>Do this workout today</button>
      <button type="button" className="ux-button ux-button-secondary" disabled={moving} onClick={() => { setConfirming(false); setNotice(`Original date kept: ${formatCalendarDate(preview.original_date)}. No schedule changes made.`); }}>Keep original date</button>
    </div>
    {confirming ? <dialog ref={dialog} aria-labelledby={`${id}-title`} aria-describedby={`${id}-description`} className="ux-card fixed inset-0 m-auto max-h-[90dvh] w-[calc(100%-2rem)] max-w-lg space-y-4 overflow-y-auto backdrop:bg-black/70" onCancel={event => { event.preventDefault(); if (!inFlight.current) setConfirming(false); }}>
      <h2 id={`${id}-title`}>Move this workout to today?</h2>
      <p id={`${id}-description`}>{preview.session.title}: move from {formatCalendarDate(preview.original_date)} to today, {formatCalendarDate(preview.local_today)} · {preview.timezone}.</p>
      <p>{counts}. Exercise prescriptions stay the same. Moving the date does not start the workout.</p>
      <div className="flex flex-wrap gap-2">
        <button type="button" className="ux-button ux-button-primary" disabled={moving} onClick={() => void move()}>{moving ? "Moving workout…" : "Confirm move to today"}</button>
        <button type="button" className="ux-button ux-button-secondary" disabled={moving} onClick={() => setConfirming(false)}>Cancel</button>
      </div>
    </dialog> : null}
  </section>;
}
