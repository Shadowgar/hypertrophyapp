"use client";

import { useEffect, useId, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { UiIcon } from '@/components/ui/icons';
import type { SorenessSeverity } from '@/lib/api';
import styles from './soreness-dialog.module.css';

type Props = {
  muscles: readonly string[];
  values: Record<string, SorenessSeverity>;
  notes: string;
  status: string;
  onSeverity: (muscle: string, severity: SorenessSeverity) => void;
  onNotes: (notes: string) => void;
  onSave: () => Promise<void>;
  onSkip: () => Promise<void>;
};

/** Presentation and interaction only; Today owns the scheduling date and writes. */
export function SorenessDialog({ muscles, values, notes, status, onSeverity, onNotes, onSave, onSkip }: Props) {
  const id = useId();
  const dialog = useRef<HTMLDialogElement>(null);
  const title = useRef<HTMLHeadingElement>(null);
  const inFlight = useRef(false);
  const mounted = useRef(false);
  const [pending, setPending] = useState<'save' | 'skip' | null>(null);
  useEffect(() => {
    const element = dialog.current!;
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const body = document.body;
    const savedStyle = { position: body.style.position, top: body.style.top, left: body.style.left, width: body.style.width, overflow: body.style.overflow };
    const scrollX = window.scrollX, scrollY = window.scrollY;
    // Native modal focus/inert behavior does not itself prevent iOS page scroll.
    Object.assign(body.style, { position: 'fixed', top: `-${scrollY}px`, left: `-${scrollX}px`, width: '100%', overflow: 'hidden' });
    const viewport = window.visualViewport;
    const resize = () => {
      element.style.setProperty('--soreness-viewport-height', `${viewport?.height ?? window.innerHeight}px`);
      element.style.setProperty('--soreness-viewport-top', `${viewport?.offsetTop ?? 0}px`);
    };
    resize(); viewport?.addEventListener('resize', resize); viewport?.addEventListener('scroll', resize);
    window.addEventListener('resize', resize);
    mounted.current = true;
    element.showModal(); title.current?.focus({ preventScroll: true });
    return () => {
      mounted.current = false;
      viewport?.removeEventListener('resize', resize); viewport?.removeEventListener('scroll', resize);
      window.removeEventListener('resize', resize);
      element.close(); Object.assign(body.style, savedStyle);
      window.scrollTo(scrollX, scrollY);
      const destination = previousFocus && previousFocus !== body && previousFocus.isConnected
        ? previousFocus : document.querySelector<HTMLElement>('[data-today-heading]');
      destination?.focus({ preventScroll: true });
    };
  }, []);

  async function run(action: 'save' | 'skip') {
    if (inFlight.current) return;
    inFlight.current = true; setPending(action);
    try { await (action === 'save' ? onSave() : onSkip()); }
    finally { inFlight.current = false; if (mounted.current) setPending(null); }
  }
  const failed = status !== 'Idle' && !pending;
  return <dialog ref={dialog} className={styles.dialog} aria-labelledby={`${id}-title`} aria-describedby={`${id}-description`}
    onCancel={event => { event.preventDefault(); void run('skip'); }}
    onKeyDown={event => {
      if (event.key !== 'Tab') return;
      const controls = event.currentTarget.querySelectorAll<HTMLElement>('button:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex="0"]');
      const first = controls[0], last = controls[controls.length - 1];
      if (event.shiftKey && (document.activeElement === first || document.activeElement === title.current)) {
        event.preventDefault(); last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault(); first?.focus();
      }
    }}>
    <header className={styles.header}>
      <h2 ref={title} tabIndex={-1} id={`${id}-title`}>What&rsquo;s sore today?</h2>
      <p id={`${id}-description`}>Log soreness before starting this workout.</p>
    </header>
    <div className={styles.body} role="region" aria-label="Soreness inputs" tabIndex={0}>
      <fieldset disabled={Boolean(pending)} className={styles.fields}>
        <legend className="sr-only">Soreness by muscle group</legend>
        {muscles.map(muscle => <label key={muscle} className={styles.row}>
          <span>{muscle}</span>
          <select value={values[muscle]} onChange={event => onSeverity(muscle, event.target.value as SorenessSeverity)}>
            <option value="none">None</option><option value="mild">Mild</option>
            <option value="moderate">Moderate</option><option value="severe">Severe</option>
          </select>
        </label>)}
        <label className={styles.notes}>Optional soreness notes
          <textarea placeholder="Optional soreness notes" rows={3} value={notes} onChange={event => onNotes(event.target.value)} />
        </label>
      </fieldset>
    </div>
    <footer className={styles.footer}>
      <p className={failed ? styles.error : styles.status} role={failed ? 'alert' : 'status'} aria-live={failed ? 'assertive' : 'polite'}>
        {pending === 'save' ? 'Saving soreness…' : pending === 'skip' ? 'Opening workout…' : failed ? status : ''}
      </p>
      <div className={styles.actions}>
        <Button onClick={() => void run('save')} type="button" disabled={Boolean(pending)}>
          <UiIcon name="save" className="ui-icon--action" />Save &amp; Start Workout
        </Button>
        <Button onClick={() => void run('skip')} type="button" variant="secondary" disabled={Boolean(pending)}>
          <UiIcon name="skip" className="ui-icon--action" />Skip
        </Button>
      </div>
    </footer>
  </dialog>;
}
