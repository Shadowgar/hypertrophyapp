"use client";

import Link from 'next/link';
import { useEffect, useRef, useState, type FormEvent } from 'react';
import type { Profile } from '@/lib/api';
import { api, getToken, getProgramDisplayName, savedSetupValue } from '@/lib/api';
import { canonicalLoad, displayLoad } from '@/lib/appearance';
import { SetupCard, setupStyles as styles } from './setup-flow';
const labels: Record<string, string> = {
  primary_goals: 'Training goals', birthday: 'Birthday', training_age_bucket: 'Consistent strength training',
  strength_frequency_bucket: 'Training frequency', motivation_driver: 'What helps you train',
  primary_obstacle: 'Current obstacle', strength_experience_level: 'Lifting experience',
  preferred_workout_duration_minutes: 'Preferred duration (minutes)', training_location: 'Training location',
  equipment_tags: 'Equipment', movement_restrictions: 'Movement limitations', gender: 'Gender',
};
function answer(value: unknown): string {
  if (value === null || value === undefined || value === '' || (Array.isArray(value) && !value.length)) return 'Not reported';
  if (Array.isArray(value)) return value.map(answer).join(', ');
  return typeof value === 'string' ? value.replaceAll('_', ' ') : typeof value === 'number' ? String(value) : 'Not reported';
}
export function SavedSetup({ profile: initialProfile, unit }: { profile: Profile; unit: 'lb' | 'kg' }) {
  const [profile, setProfile] = useState(initialProfile);
  const savedWeight = savedSetupValue(profile, 'weight');
  const [name, setName] = useState(initialProfile.name ?? '');
  const [age, setAge] = useState(String(savedSetupValue(initialProfile, 'age') ?? ''));
  const [weight, setWeight] = useState(savedSetupValue(initialProfile, 'weight') ? String(displayLoad(initialProfile.weight, unit)) : '');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const ownerToken = useRef(getToken());
  const mounted = useRef(true);
  const saving = useRef(false);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => { setWeight(savedWeight ? String(displayLoad(savedWeight, unit)) : ''); }, [unit, savedWeight]);

  async function saveBasics(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving.current) return;
    const token = getToken();
    if (token !== ownerToken.current) { setError('Account changed. Reload setup before editing.'); return; }
    const parsedAge = Number(age);
    // Preserve the exact canonical value if its rounded display was not edited.
    const kg = Number(weight) === displayLoad(profile.weight, unit) ? profile.weight : canonicalLoad(Number(weight), unit);
    if (!name.trim() || !Number.isInteger(parsedAge) || parsedAge < 14 || parsedAge > 90 || !Number.isFinite(kg) || kg <= 0) {
      setError('Enter a name, an age from 14–90, and a positive bodyweight.'); return;
    }
    saving.current = true; setPending(true); setError(null); setSaved(false);
    try {
      const updated = await api.updateSetupBasics({ name: name.trim(), age: parsedAge, weight: kg });
      if (!mounted.current) return;
      if (token !== getToken()) { setError('Account changed. Reload setup before editing.'); return; }
      setProfile(updated); setName(updated.name); setAge(String(updated.age)); setSaved(true);
    } catch (failure) {
      if (mounted.current) setError(token !== getToken() ? 'Account changed. Reload setup before editing.' : `Could not save basics: ${failure instanceof Error ? failure.message : 'Unknown error'}. Try Save basics again.`);
    } finally { saving.current = false; if (mounted.current) setPending(false); }
  }
  const programId = savedSetupValue(profile, 'selected_program_id');
  const flexible = profile.schedule_mode === 'flexible';
  const customized = programId === 'full_body_v1';
  const height = profile.onboarding_answers?.height as { unit?: string; cm?: number; feet?: number; inches?: number } | undefined;
  return <div className={styles.form}>
    <SetupCard title="Your saved answers"><dl className={styles.review}>
      <div><dt>Name</dt><dd>{profile.name || 'Not reported'}</dd></div>
      <div><dt>Program preference</dt><dd>{programId ? getProgramDisplayName({ id: programId }) : profile.program_selection_mode === 'auto' ? 'Auto · choose in Week' : 'Not reported'}</dd></div>
      <div><dt>Age</dt><dd>{savedSetupValue(profile, 'age') ?? 'Not reported'}</dd></div>
      <div><dt>Body weight</dt><dd>{savedWeight ? `${displayLoad(savedWeight, unit)} ${unit}` : 'Not reported'}</dd></div>
      <div><dt>{flexible ? 'Flexible expectation' : 'Training days per week'}</dt><dd>{flexible ? `${profile.expected_sessions_per_week ?? 'No'} expected sessions · dates optional` : savedSetupValue(profile, 'days_available') ?? 'Not reported'}</dd></div>
      <div><dt>Height</dt><dd>{height?.unit === 'cm' && height.cm ? `${height.cm} cm` : height?.feet || height?.inches ? `${height.feet ?? 'Unreported'} ft ${height.inches ?? 'unreported'} in` : 'Not reported'}</dd></div>
      {Object.entries(labels).map(([key, label]) => <div key={key}><dt>{label}</dt><dd>{answer(profile.onboarding_answers?.[key])}</dd></div>)}
    </dl></SetupCard>
    <SetupCard title="Edit current basics">
      <p className={styles.helper}>Update your current name, age and bodyweight. Your program and recorded workouts stay unchanged.</p>
      <form aria-label="Edit current basics" className={styles.fields} onSubmit={saveBasics}>
        <fieldset className={styles.fields} disabled={pending}>
          <label className={styles.field}>Current name<input className="ui-input" value={name} required maxLength={100} onChange={event => { setName(event.target.value); setSaved(false); }} /></label>
          <label className={styles.field}>Current age<input className="ui-input" type="number" min={14} max={90} step={1} value={age} required onChange={event => { setAge(event.target.value); setSaved(false); }} /></label>
          <label className={styles.field}>Current bodyweight ({unit})<input className="ui-input" type="number" min="0.1" step="any" inputMode="decimal" value={weight} required onChange={event => { setWeight(event.target.value); setSaved(false); }} /></label>
        </fieldset>
        {error ? <p role="alert" className={`${styles.notice} ${styles.error}`}>{error}</p> : null}
        <button className="ux-button ux-button-primary min-h-[48px]" type="submit" disabled={pending}>{pending ? 'Saving basics…' : 'Save basics'}</button>
        {saved ? <p role="status" className={styles.notice}>Basics saved. Your setup answers, program and training history are preserved.</p> : null}
      </form>
    </SetupCard>
    <p className={styles.helper}>Review your saved answers here. Edit equipment and display preferences in Settings, or review your program and dates separately. Your workouts and history stay with this account.</p>
    <Link className={styles.secondaryLink} href="/settings#training-preferences">Edit equipment &amp; preferences</Link>
    <Link className={styles.secondaryLink} href={flexible ? profile.setup_status === 'planning' ? '/training/setup' : '/today' : customized ? '/customize' : '/week'}>{flexible ? 'Continue Flexible training' : customized ? 'Continue to Customized' : 'Continue to program & dates'}</Link>
    <Link className={styles.textLink} href="/">Return Home</Link>
  </div>;
}
