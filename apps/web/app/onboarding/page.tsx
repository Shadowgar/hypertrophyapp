"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { SetupCard, SetupFlow, setupStyles as styles } from '@/components/setup-flow';
import { useAppearance } from '@/components/appearance-provider';
import { api, ApiError, getProgramDisplayName, getToken, setAuthToken, type ProgramTemplateOption } from '@/lib/api';
import { accountScope, canonicalLoad } from '@/lib/appearance';
import { PasswordField } from '@/components/password-field';
import { SavedSetup } from '@/components/saved-setup';
import { clearAuthToken, type Profile } from '@/lib/api';
import { API_BASE_URL } from '@/lib/env';
import { discardCachedDraft, emptyAnswers, EQUIPMENT, GOALS, OPTIONAL_OPTIONS, readCachedDraft, readDraft, RESTRICTIONS, setupPayload, validBasics, writeCachedDraft, type SetupAnswers } from './setup-draft';

type Stage = 'welcome' | 'account' | 'program' | 'authored' | 'program-detail' | 'help' | 'basics' | 'equipment' | 'review' | 'saved';
const AUTHORED_IDS = ['pure_bodybuilding_phase_1_full_body', 'pure_bodybuilding_phase_2_full_body'];

function withWeightUnit(previous: SetupAnswers, unit: 'lb' | 'kg'): SetupAnswers {
  if (previous.weightUnit === unit) return previous;
  const kg = canonicalLoad(Number(previous.weightValue), previous.weightUnit);
  const value = previous.weightValue.trim() && Number.isFinite(kg) ? String(unit === 'kg' ? kg : kg / 0.45359237) : '';
  return { ...previous, weightUnit: unit, weightValue: value };
}

async function responseError(response: Response, fallback: string): Promise<string> {
  try {
    const value = await response.json() as { detail?: unknown };
    if (typeof value.detail === 'string') return value.detail;
    if (Array.isArray(value.detail)) return value.detail.map(item => typeof item?.msg === 'string' ? item.msg : '').filter(Boolean).join('; ') || fallback;
  } catch { /* Keep the bounded fallback; never render rejected inputs or credentials. */ }
  return fallback;
}

export default function OnboardingPage() {
  const [accountRevision, setAccountRevision] = useState(0);
  const reset = useCallback(() => { discardCachedDraft(); setAccountRevision(value => value + 1); }, []);
  return <>
    {accountRevision > 0 ? <p role="status" className={styles.notice}>Account changed. Sign in to continue with the current account; no other profile was changed. <Link href="/login">Sign in</Link></p> : null}
    <SetupForm key={accountRevision} recoverDraft={accountRevision === 0} onAccountChanged={reset} />
  </>;
}

function SetupForm({ onAccountChanged, recoverDraft }: { onAccountChanged: () => void; recoverDraft: boolean }) {
  const router = useRouter();
  const appearance = useAppearance();
  const [savedProfile, setSavedProfile] = useState<Profile | null>(null);
  const [stage, setStage] = useState<Stage>('welcome');
  const [answers, setAnswers] = useState<SetupAnswers>(emptyAnswers);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [targets, setTargets] = useState({ calories: '', protein: '', fat: '', carbs: '' });
  const [programs, setPrograms] = useState<ProgramTemplateOption[]>([]);
  const [catalogState, setCatalogState] = useState<'loading' | 'ready' | 'failed'>('loading');
  const [catalogAttempt, setCatalogAttempt] = useState(0);
  const [status, setStatus] = useState('');
  const [error, setError] = useState(false);
  const [pending, setPending] = useState(false);
  const [hasSession, setHasSession] = useState(false);
  const [draftReady, setDraftReady] = useState(false);
  const [hasDraft, setHasDraft] = useState(false);
  const [cacheAvailable, setCacheAvailable] = useState(true);
  const [unitTouched, setUnitTouched] = useState(false);
  const [preferenceRecovery, setPreferenceRecovery] = useState<'none' | 'reload' | 'review'>('none');
  const draftToken = useRef(getToken());
  const createdAccount = useRef<{ email: string; token: string } | null>(null);
  const submissionRevision = useRef(0);
  const submitting = useRef(false);
  const completed = useRef(false);
  const installingOwnToken = useRef(false);
  const mounted = useRef(false);

  useEffect(() => {
    mounted.current = true;
    let observedToken = getToken(); setHasSession(Boolean(observedToken));
    const retireSubmission = () => { submissionRevision.current += 1; };
    const changed = () => {
      const next = getToken(); if (next === observedToken) return;
      observedToken = next; setHasSession(Boolean(next));
      if (installingOwnToken.current) return;
      retireSubmission(); submitting.current = false; createdAccount.current = null; onAccountChanged();
    };
    window.addEventListener('hypertrophy:auth-token-changed', changed);
    window.addEventListener('storage', changed); window.addEventListener('focus', changed);
    return () => {
      mounted.current = false; retireSubmission(); submitting.current = false;
      window.removeEventListener('hypertrophy:auth-token-changed', changed);
      window.removeEventListener('storage', changed); window.removeEventListener('focus', changed);
    };
  }, [onAccountChanged]);

  useEffect(() => {
    let active = true; setCatalogState('loading');
    api.listPrograms().then(result => {
      if (!active) return;
      setPrograms(Array.isArray(result) ? result : []); setCatalogState('ready');
    }).catch(() => { if (active) setCatalogState('failed'); });
    return () => { active = false; };
  }, [catalogAttempt]);

  useEffect(() => {
    // An account change must not recover the prior draft if its removal was denied.
    if (!recoverDraft) { setDraftReady(true); return; }
    const raw = readCachedDraft(draftToken.current);
    if (raw === undefined) setCacheAvailable(false);
    if (raw) {
      const restored = readDraft(raw);
      if (restored) { setAnswers(restored); setHasDraft(true); setStatus('Recovered saved onboarding draft. Review your choices and re-enter private measurements.'); }
      else if (!discardCachedDraft()) setCacheAvailable(false);
    }
    setDraftReady(true);
  }, [recoverDraft]);

  useEffect(() => {
    if (!draftReady || !cacheAvailable || completed.current || stage === 'welcome' || stage === 'account') return;
    const saved = writeCachedDraft(answers, draftToken.current); setHasDraft(saved);
    if (!saved) setCacheAvailable(false);
  }, [answers, cacheAvailable, draftReady, stage]);

  useEffect(() => {
    if (appearance.ready && !unitTouched) setAnswers(value => withWeightUnit(value, appearance.preferences.weight_unit));
  }, [appearance.ready, appearance.preferences.weight_unit, unitTouched]);

  function update<K extends keyof SetupAnswers>(key: K, value: SetupAnswers[K]) { setAnswers(previous => ({ ...previous, [key]: value })); }
  function move(next: Stage) {
    const safe = getToken() && (next === 'welcome' || next === 'account') ? 'program' : next;
    setStage(safe); setStatus(''); setError(false);
    const scope = accountScope(getToken());
    if (scope) { try { localStorage.setItem(`hypertrophy_setup_position_${scope}`, safe); } catch { /* Optional recovery. */ } }
    const state = { ...window.history.state, onboardingStage: safe };
    if (getToken() && (stage === 'account' || stage === 'welcome')) window.history.replaceState(state, '', '/onboarding');
    else window.history.pushState(state, '', '/onboarding');
  }

  useEffect(() => {
    const back = () => {
      const next = window.history.state?.onboardingStage as Stage | undefined;
      const allowed: Stage[] = ['program', 'authored', 'program-detail', 'help', 'basics', 'equipment', 'review'];
      if (savedProfile) { setStage('saved'); return; }
      if (getToken()) setStage(next && allowed.includes(next) ? next : 'program');
      else setStage(next === 'account' ? 'account' : 'welcome');
      setStatus(''); setError(false);
    };
    window.addEventListener('popstate', back);
    return () => window.removeEventListener('popstate', back);
  }, [savedProfile]);

  useEffect(() => {
    if (getToken()) void resumeInitialSetup();
    // External identity changes remount this form; registration owns its handoff.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  function toggle(key: 'equipmentTags' | 'movementRestrictions' | 'primaryGoals', value: string) {
    setAnswers(previous => ({ ...previous, [key]: previous[key].includes(value) ? previous[key].filter(item => item !== value) : [...previous[key], value] }));
  }
  function changeUnit(unit: 'lb' | 'kg') {
    setUnitTouched(true);
    setAnswers(previous => withWeightUnit(previous, unit));
  }
  function beginRequest() {
    const revision = ++submissionRevision.current;
    submitting.current = true; setPending(true); setError(false); setStatus('');
    return revision;
  }
  function endRequest(revision: number) {
    if (mounted.current && revision === submissionRevision.current) { submitting.current = false; setPending(false); }
  }
  function fail(message: string) { setStatus(message); setError(true); }

  async function register(event: FormEvent) {
    event.preventDefault(); if (submitting.current) return;
    if (getToken()) { fail('An account is already signed in. Continue account setup or use Settings for that account.'); return; }
    const revision = beginRequest();
    let expectedToken = getToken();
    const isCurrent = () => mounted.current && submissionRevision.current === revision && getToken() === expectedToken;
    const normalizedEmail = email.trim().toLowerCase();
    try {
      const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: normalizedEmail, password, name: name.trim() }),
      });
      if (!isCurrent()) return;
      if (!response.ok) {
        const detail = await responseError(response, 'Please try again.');
        if (!isCurrent()) return;
        fail(response.status === 400 && /already used/i.test(detail) ? 'An account already exists. Sign in to keep your existing training settings.' : `Registration failed: ${detail}`);
        return;
      }
      const result = await response.json() as { access_token?: string };
      if (!isCurrent()) return;
      if (!result.access_token) throw new Error('Missing authentication result');
      expectedToken = result.access_token;
      draftToken.current = result.access_token;
      createdAccount.current = { email: normalizedEmail, token: result.access_token };
      installingOwnToken.current = true;
      try { setAuthToken(result.access_token); } finally { installingOwnToken.current = false; }
      setEmail(normalizedEmail); setPassword(''); move('program');
    } catch { if (isCurrent()) fail('Registration failed. Check your connection and try again.'); }
    finally { endRequest(revision); }
  }

  async function resumeInitialSetup() {
    const token = getToken();
    if (token !== draftToken.current) { onAccountChanged(); return; }
    if (!token || submitting.current) return;
    const revision = beginRequest();
    const isCurrent = () => mounted.current && submissionRevision.current === revision && getToken() === token;
    try {
      const response = await fetch(`${API_BASE_URL}/profile`, { headers: { Authorization: `Bearer ${token}` } });
      if (!isCurrent()) return;
      if (response.status === 401) { clearAuthToken(); return; }
      if (!response.ok) throw new Error('Setup unavailable');
      const profile = await response.json() as Profile;
      if (!isCurrent()) return;
      if (profile.initial_setup_available === false) { setSavedProfile(profile); setStage('saved'); setStatus('Your saved setup is available to review. Continue planning separately.'); return; }
      if (profile.initial_setup_available !== true || !profile.email) throw new Error('Setup status unavailable');
      createdAccount.current = { email: profile.email, token };
      setEmail(profile.email); setName(profile.name || ''); setPassword('');
      setAnswers(previous => ({ ...previous, age: '', weightValue: '', birthday: '', heightFeet: '', heightInches: '', heightCm: '' }));
      setTargets({ calories: '', protein: '', fat: '', carbs: '' });
      let position: Stage = 'program';
      const scope = accountScope(token);
      try {
        const saved = scope && localStorage.getItem(`hypertrophy_setup_position_${scope}`);
        if (saved && ['program', 'authored', 'program-detail', 'help', 'basics', 'equipment', 'review'].includes(saved)) position = saved as Stage;
      } catch { /* Optional stage recovery. */ }
      if (position === 'equipment' || position === 'review') position = 'basics';
      setStage(position); setStatus('Review your answers to finish this account. Private measurements are not saved in the browser draft; enter them again before saving.');
    } catch { if (isCurrent()) fail('Unable to check saved setup. Retry Continue account setup; no profile was changed.'); }
    finally { endRequest(revision); }
  }

  async function reloadSetupPreferences() {
    const account = createdAccount.current;
    if (!account || getToken() !== account.token || submitting.current) return;
    const revision = beginRequest();
    // A reread reconciles server state without reinterpreting the entered weight
    // or changing the unit the user is reviewing for this setup.
    setUnitTouched(true);
    try {
      await appearance.reload();
      if (mounted.current && submissionRevision.current === revision && getToken() === account.token) {
        setPreferenceRecovery('review');
      }
    } catch {
      if (mounted.current && submissionRevision.current === revision && getToken() === account.token) {
        fail('Saved display preferences could not be reloaded. Retry the reload; your setup answers are still here.');
      }
    } finally { endRequest(revision); }
  }

  async function saveSetup(preferencesReviewed = false) {
    if (submitting.current || completed.current) return;
    if (preferenceRecovery !== 'none' && !preferencesReviewed) return;
    const account = createdAccount.current;
    if (!account || getToken() !== account.token || email !== account.email) { fail('Continue account setup before saving. No existing profile was changed.'); return; }
    if (!validBasics(answers) || !name.trim()) { fail('Complete the required setup answers before saving.'); return; }
    if (answers.selectedProgramId && !programs.some(program => program.id === answers.selectedProgramId)) { fail('Selected program is unavailable. Choose another option or reload the catalog; your choice was not replaced.'); return; }
    if (!appearance.ready) { fail('Saved display preferences are unavailable. Reload preferences before saving setup.'); return; }
    const revision = beginRequest();
    const isCurrent = () => mounted.current && submissionRevision.current === revision && getToken() === account.token;
    try {
      if (answers.weightUnit !== appearance.preferences.weight_unit) {
        try {
          await appearance.save({ theme_family: appearance.preferences.theme_family, appearance: appearance.preferences.appearance, weight_unit: answers.weightUnit }, appearance.preferences.revision);
        } catch (cause) {
          if (isCurrent()) {
            setPreferenceRecovery('reload');
            fail(cause instanceof ApiError && cause.status === 409
              ? 'Display preferences changed elsewhere. Reload and review the saved preferences before continuing. Your setup answers are still here.'
              : 'The display preference save was not confirmed. Reload and review the saved preferences before continuing. Your setup answers are still here.');
          }
          return;
        }
        if (!isCurrent()) return;
      }
      setPreferenceRecovery('none');
      const response = await fetch(`${API_BASE_URL}/profile/initial-setup`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${account.token}` },
        body: JSON.stringify(setupPayload(answers, name, targets)),
      });
      if (!isCurrent()) return;
      if (!response.ok) {
        const detail = await responseError(response, 'Please try again.');
        if (isCurrent()) fail(`Profile save failed: ${detail}`);
        return;
      }
      completed.current = true;
      if (!discardCachedDraft()) setCacheAvailable(false);
      setHasDraft(false);
      setStatus('Profile saved. Choose your training dates next.');
      router.push(answers.selectedProgramId === 'full_body_v1' ? '/customize' : '/week');
    } catch { if (isCurrent()) fail('Profile save failed. Your account is created; retry to finish setup.'); }
    finally { endRequest(revision); }
  }

  const selectedProgram = programs.find(program => program.id === answers.selectedProgramId);
  const programName = selectedProgram ? getProgramDisplayName(selectedProgram) : answers.selectedProgramId ? 'Selected program unavailable' : 'Auto · choose a program in Week';
  const isCustomized = answers.selectedProgramId === 'full_body_v1';
  const titles: Record<Stage, [string, string]> = {
    saved: ['Your saved setup', 'Review your answers and continue planning.'],
    welcome: ['Ready for your next session?', 'A clear plan. Your actual progress.'], account: ['Make it yours', 'Create your account, then choose a program.'],
    program: ['How would you like to train?', 'Start with a clear choice. You can review it next.'], authored: ['Follow an Authored program', 'Each phase keeps its own exercises and training instructions.'],
    'program-detail': [programName, 'Authored program'], help: ['Compare your options', 'Choose a path, or keep an Auto preference until you review the available programs.'],
    basics: ['A few essentials', 'Setup · 1 of 3'], equipment: ['Your equipment', 'Setup · 2 of 3'], review: ['Review your setup', 'Setup · 3 of 3'],
  };
  const choice = (title: string, description: string, action: () => void) => <button type="button" className={styles.choice} onClick={action}><strong className={styles.choiceTitle}>{title}<span aria-hidden="true">›</span></strong><span>{description}</span></button>;
  const field = (key: keyof SetupAnswers, label: string, type = 'text') => <label className={styles.field}>{label}<input type={type} value={String(answers[key])} onChange={event => update(key, event.target.value as never)} /></label>;
  const select = (key: keyof typeof OPTIONAL_OPTIONS, label: string) => <label className={styles.field}>{label}<select value={answers[key]} onChange={event => update(key, event.target.value)}><option value="">Not reported</option>{OPTIONAL_OPTIONS[key].map(([value, text]) => <option key={value} value={value}>{text}</option>)}</select></label>;

  return <SetupFlow title={titles[stage][0]} subtitle={titles[stage][1]} eyebrow={stage === 'welcome' ? 'Home' : stage === 'account' ? 'Account' : 'Programs'} aside={<>
    <SetupCard title={stage === 'program' ? 'Two distinct paths' : 'Your setup'}><p>{stage === 'program' ? 'Authored follows a source program. Customized creates an original program only with your permission.' : 'Account → Program → Equipment → Review'}</p></SetupCard>
    <SetupCard title="Keep your choices clear"><p>Review each step before saving. Optional answers can stay unknown.</p></SetupCard>
    <SetupCard title="Already have an account?"><p><Link href="/login">Sign in</Link> to return to your saved training.</p></SetupCard>
  </>}>
    {status ? <p role={error ? 'alert' : 'status'} className={`${styles.notice} ${error ? styles.error : ''}`}>{status}</p> : null}
    {!cacheAvailable ? <p role="status" className={styles.notice}>Browser draft storage is unavailable. Keep this page open until setup is saved.</p> : null}
    {hasSession && !createdAccount.current && !savedProfile ? <Button type="button" variant="secondary" disabled={pending} onClick={resumeInitialSetup}>Continue account setup</Button> : null}
    {hasDraft ? <details className={styles.disclosure}><summary>Saved setup choices</summary><p className={styles.helper}>Credentials and private measurements are not stored in this browser draft.</p><Button type="button" variant="ghost" onClick={() => { if (discardCachedDraft()) setHasDraft(false); else setCacheAvailable(false); }}>Clear Saved Draft</Button></details> : null}

    {stage === 'saved' && savedProfile ? <SavedSetup profile={savedProfile} unit={appearance.preferences.weight_unit} /> : null}

    {stage === 'welcome' && !hasSession ? <div className={styles.form}>
      <SetupCard title="Train with your program"><p>Follow an Authored program or choose to build a Customized program.</p></SetupCard>
      <Link href="/login" className={styles.choice}><strong>Already training here?</strong><span>Sign in to return to your workouts and history.</span></Link>
      <div className={styles.actions}><Button type="button" onClick={() => move('account')}>Create an account</Button><Link href="/login" className={styles.textLink}>Sign in</Link></div>
    </div> : null}

    {stage === 'account' && !hasSession ? <form className={styles.form} onSubmit={register}>
      <label className={styles.field}>Name<input autoComplete="name" required value={name} disabled={pending} onChange={event => setName(event.target.value)} /></label>
      <label className={styles.field}>Email<input type="email" autoComplete="email" required value={email} disabled={pending} onChange={event => setEmail(event.target.value)} /></label>
      <PasswordField value={password} onChange={setPassword} autoComplete="new-password" disabled={pending} minLength={8} />
      <SetupCard title="Your choice comes next"><p>You can review your setup before starting training.</p></SetupCard>
      <div className={styles.actions}><Button type="submit" disabled={pending}>{pending ? 'Creating account…' : 'Create account'}</Button><Link href="/login" className={styles.textLink}>I already have an account</Link></div>
    </form> : null}

    {stage === 'program' ? <div className={styles.form}>
      {choice('Follow an Authored program', 'Keep the original exercises, sets and training instructions.', () => move('authored'))}
      {choice('Create a Customized program', 'Review a separate program around your needs. Consent and activation come later.', () => { update('selectedProgramId', 'full_body_v1'); move('basics'); })}
      {choice('Help me choose', 'Compare the options before deciding.', () => move('help'))}
    </div> : null}

    {stage === 'authored' ? <div className={styles.form}>
      {programs.filter(program => AUTHORED_IDS.includes(program.id)).map(program => <div key={program.id}>{choice(getProgramDisplayName(program), program.description || 'Follow the source program and review actual training dates separately.', () => { update('selectedProgramId', program.id); move('program-detail'); })}</div>)}
      {catalogState !== 'ready' || !programs.some(program => AUTHORED_IDS.includes(program.id)) ? <p role="status" className={styles.notice}>{catalogState === 'loading' ? 'Loading available programs…' : 'Program catalog unavailable. Retry to confirm your choice.'}</p> : null}
      {catalogState === 'failed' ? <Button type="button" variant="secondary" onClick={() => setCatalogAttempt(value => value + 1)}>Retry program catalog</Button> : null}
      <div className={styles.actions}><Button type="button" variant="secondary" onClick={() => move('program')}>Back to program choices</Button></div>
    </div> : null}

    {stage === 'program-detail' ? <div className={styles.form}>
      <SetupCard title="Follow the original plan"><p>Exercises, set targets and techniques stay as authored. Working loads can adapt.</p></SetupCard>
      <SetupCard title="Choose actual training dates"><p>Review each session’s workload before activating a schedule. Phase 1 and Phase 2 stay separate.</p></SetupCard>
      <Link className={styles.secondaryLink} href={`/guides/${encodeURIComponent(answers.selectedProgramId || '')}`}>Read the program guide</Link>
      <div className={styles.actions}><Button type="button" disabled={!selectedProgram} onClick={() => move('basics')}>Use {programName}</Button><Button type="button" variant="ghost" onClick={() => move('authored')}>Compare programs</Button></div>
    </div> : null}

    {stage === 'help' ? <div className={styles.form}>
      <SetupCard title="Authored"><p>Follow a distinct source program with its original prescriptions. Review scheduling separately.</p></SetupCard>
      <SetupCard title="Customized"><p>Create an original Full Body program after reviewing its inputs and giving explicit consent in Customize.</p></SetupCard>
      <SetupCard title="Auto preference"><p>Keep the choice open and review available programs in Week. Auto does not activate a plan or grant Customized consent.</p></SetupCard>
      <label className={styles.field}>Choose-for-me family<select value={answers.chooseForMeFamily} onChange={event => update('chooseForMeFamily', event.target.value as SetupAnswers['chooseForMeFamily'])}><option value="full_body">Full body</option><option value="upper_lower">Upper/Lower</option><option value="push_pull">Push/Pull</option></select></label>
      <div className={styles.actions}><Button type="button" onClick={() => { update('selectedProgramId', null); move('basics'); }}>Keep Auto preference</Button><Button type="button" variant="ghost" onClick={() => move('program')}>Choose a path</Button></div>
    </div> : null}

    {stage === 'basics' ? <form className={styles.form} onSubmit={event => { event.preventDefault(); if (validBasics(answers)) move('equipment'); }}>
      <label className={styles.field}>Weight display<select value={answers.weightUnit} onChange={event => changeUnit(event.target.value as 'lb' | 'kg')}><option value="lb">Pounds · lb</option><option value="kg">Kilograms · kg</option></select></label>
      <div className={styles.pair}>
        <label className={styles.field}>Age<input type="number" min={14} max={90} step={1} required value={answers.age} onChange={event => update('age', event.target.value)} /></label>
        <label className={styles.field}>Body weight ({answers.weightUnit})<input type="number" min="0.1" step="any" required value={answers.weightValue} onChange={event => update('weightValue', event.target.value)} /></label>
      </div>
      <p className={styles.helper}>Age and body weight are required for setup. Optional details can stay blank.</p>
      <label className={styles.field}>Training days per week<select required value={answers.daysAvailable} onChange={event => update('daysAvailable', event.target.value)}><option value="">Choose a count</option>{[2, 3, 4, 5].map(days => <option key={days} value={days}>{days} days</option>)}</select></label>
      <label className={styles.field}>Training location<select value={answers.trainingLocation} onChange={event => update('trainingLocation', event.target.value)}><option value="">Not reported</option><option value="gym">Gym</option><option value="home">Home</option></select></label>
      <SetupCard title="Only what this plan needs"><p>{isCustomized ? 'Exact equipment, dates and program inputs are reviewed in Customize before you consent.' : 'Setup does not change an Authored exercise, set target or technique. You will choose actual dates in Week.'}</p></SetupCard>
      <details className={styles.disclosure}><summary>Training context (optional)</summary><div className={styles.fields}>
        <fieldset className={styles.checks}><legend>Training goals</legend>{GOALS.map(([value, label]) => <label key={value} className={styles.check}><input type="checkbox" checked={answers.primaryGoals.includes(value)} onChange={() => toggle('primaryGoals', value)} />{label}</label>)}</fieldset>
        {select('trainingAgeBucket', 'Consistent strength training')}{select('strengthFrequency', 'Current training frequency')}{select('experienceLevel', 'Lifting experience')}
        {select('motivationDriver', 'What helps you train?')}{select('obstacle', 'Current obstacle')}
        <label className={styles.field}>Preferred workout duration (minutes)<input type="number" min={15} max={240} step={1} value={answers.workoutDurationMinutes} onChange={event => update('workoutDurationMinutes', event.target.value)} /></label>
        {field('weakAreasRaw', 'Weak areas (comma-separated)')}
      </div></details>
      <details className={styles.disclosure}><summary>Personal details (optional)</summary><div className={styles.fields}>
        {select('gender', 'Gender')}{field('birthday', 'Birthday', 'date')}
        <label className={styles.field}>Height unit<select value={answers.heightUnit} onChange={event => update('heightUnit', event.target.value as 'in' | 'cm')}><option value="in">Feet and inches</option><option value="cm">Centimeters</option></select></label>
        {answers.heightUnit === 'cm' ? field('heightCm', 'Height (cm)', 'number') : <div className={styles.pair}>{field('heightFeet', 'Height (feet)', 'number')}{field('heightInches', 'Height (inches)', 'number')}</div>}
      </div></details>
      <div className={styles.actions}><Button type="submit" disabled={!validBasics(answers)}>Continue to equipment</Button><Button type="button" variant="ghost" onClick={() => move('program')}>Back to program choices</Button></div>
    </form> : null}

    {stage === 'equipment' ? <div className={styles.form}>
      <p className={styles.helper}>{answers.trainingLocation === 'gym' ? 'Gym' : answers.trainingLocation === 'home' ? 'Home' : 'Location not reported'} · select the equipment you have. Nothing is selected for you.</p>
      <div className={styles.checks}>{EQUIPMENT.map(([value, label]) => <label key={value} className={styles.check}><input type="checkbox" checked={answers.equipmentTags.includes(value)} onChange={() => toggle('equipmentTags', value)} />{label}</label>)}</div>
      <SetupCard title="What this changes"><p>Equipment records availability. It does not rewrite an Authored exercise. Exact locations, setup identities and available loads for Customized are reviewed in Customize; no loads are invented here.</p></SetupCard>
      <details className={styles.disclosure}><summary>Movement limitations (optional)</summary><div className={styles.checks}>{RESTRICTIONS.map(([value, label]) => <label key={value} className={styles.check}><input type="checkbox" checked={answers.movementRestrictions.includes(value)} onChange={() => toggle('movementRestrictions', value)} />{label}</label>)}</div></details>
      <div className={styles.actions}><Button type="button" onClick={() => move('review')}>Review setup</Button><Button type="button" variant="ghost" onClick={() => move('basics')}>Back</Button></div>
    </div> : null}

    {stage === 'review' ? <form className={styles.form} onSubmit={event => { event.preventDefault(); void saveSetup(); }}>
      <SetupCard title="Your choices"><dl className={styles.review}>
        <div><dt>Program</dt><dd>{answers.selectedProgramId ? `${isCustomized ? 'Customized' : 'Authored'} · ${programName}` : programName}</dd></div>
        <div><dt>Weight display</dt><dd>{answers.weightUnit === 'lb' ? 'Pounds · lb' : 'Kilograms · kg'}</dd></div>
        <div><dt>About you</dt><dd>{name} · {answers.age} years · {answers.weightValue} {answers.weightUnit}</dd></div>
        <div><dt>Training days</dt><dd>{answers.daysAvailable} per week · actual dates still to choose</dd></div>
        <div><dt>Equipment</dt><dd>{answers.trainingLocation || 'Location not reported'} · {answers.equipmentTags.length ? answers.equipmentTags.map(value => EQUIPMENT.find(([id]) => id === value)?.[1] || value).join(', ') : 'No equipment reported'}</dd></div>
        <div><dt>Limitations</dt><dd>{answers.movementRestrictions.length ? answers.movementRestrictions.map(value => RESTRICTIONS.find(([id]) => id === value)?.[1] || value).join(', ') : 'No limitations reported'}</dd></div>
        <div><dt>Optional context</dt><dd>{answers.workoutDurationMinutes ? `${answers.workoutDurationMinutes} minutes requested. ` : 'Workout duration not reported. '}Unanswered optional fields remain unknown.</dd></div>
      </dl></SetupCard>
      <details className={styles.disclosure}><summary>Review optional answers</summary><dl className={styles.review}>
        <div><dt>Training goals</dt><dd>{answers.primaryGoals.length ? answers.primaryGoals.map(value => GOALS.find(([id]) => id === value)?.[1] || value).join(', ') : 'Not reported'}</dd></div>
        {([['trainingAgeBucket', 'Consistent strength training'], ['strengthFrequency', 'Current training frequency'], ['experienceLevel', 'Lifting experience'], ['motivationDriver', 'What helps you train?'], ['obstacle', 'Current obstacle'], ['gender', 'Gender']] as const).map(([key, label]) => <div key={key}><dt>{label}</dt><dd>{OPTIONAL_OPTIONS[key].find(([value]) => value === answers[key])?.[1] || 'Not reported'}</dd></div>)}
        <div><dt>Birthday</dt><dd>{answers.birthday || 'Not reported'}</dd></div>
        <div><dt>Height</dt><dd>{answers.heightUnit === 'cm' ? answers.heightCm ? `${answers.heightCm} cm` : 'Not reported' : answers.heightFeet || answers.heightInches ? `${answers.heightFeet || 'Unreported'} ft ${answers.heightInches || 'unreported'} in` : 'Not reported'}</dd></div>
        <div><dt>Weak areas</dt><dd>{answers.weakAreasRaw || 'Not reported'}</dd></div>
        {!answers.selectedProgramId ? <div><dt>Auto family preference</dt><dd>{answers.chooseForMeFamily === 'upper_lower' ? 'Upper/Lower' : answers.chooseForMeFamily === 'push_pull' ? 'Push/Pull' : 'Full body'}</dd></div> : null}
      </dl></details>
      <details className={styles.disclosure}><summary>Nutrition targets (optional)</summary><p className={styles.helper}>Enter targets you have chosen. These are goals, not a report of intake or adherence. Blank values stay unknown.</p><div className={styles.pair}>
        {([['calories', 'Daily calorie target'], ['protein', 'Protein target (g)'], ['fat', 'Fat target (g)'], ['carbs', 'Carbohydrate target (g)']] as const).map(([key, label]) => <label key={key} className={styles.field}>{label}<input type="number" min={key === 'calories' ? 1 : 0} step={1} value={targets[key]} disabled={pending || completed.current} onChange={event => setTargets(previous => ({ ...previous, [key]: event.target.value }))} /></label>)}
      </div></details>
      <SetupCard title={isCustomized ? 'Ready to review Customized' : 'Ready to choose dates'}><p>Your setup is saved separately from your schedule. {isCustomized ? 'You will review the original program and give explicit consent in Customize.' : 'Week previews the actual dates before you activate a schedule.'}</p></SetupCard>
      {preferenceRecovery !== 'none' ? <SetupCard title="Review saved display preferences">
        {preferenceRecovery === 'review' && appearance.ready && !pending ? <>
          <p>Saved: {({ classic: 'Classic WorkoutApp', graphite: 'Graphite', charcoal: 'Charcoal' })[appearance.preferences.theme_family]} · {({ light: 'Light', dark: 'Dark', system: 'Follow Device Settings' })[appearance.preferences.appearance]} · {appearance.preferences.weight_unit === 'lb' ? 'Pounds (lb)' : 'Kilograms (kg)'}.</p>
          <p>Your setup uses {answers.weightUnit === 'lb' ? 'pounds (lb)' : 'kilograms (kg)'}. {answers.weightUnit === appearance.preferences.weight_unit ? 'The saved unit already matches; continuing will save only your setup.' : 'Continuing will replace the saved unit with your selected unit and keep the saved appearance.'}</p>
          <Button type="button" disabled={pending || completed.current} onClick={event => { if (event.currentTarget.form?.reportValidity()) void saveSetup(true); }}>{answers.weightUnit === appearance.preferences.weight_unit ? 'Continue with saved preferences' : 'Use selected unit and save setup'}</Button>
        </> : <>
          <p role={appearance.error ? 'alert' : 'status'}>{appearance.error || 'Reload the saved preferences to check whether the unit changed. Reloading does not submit your setup.'}</p>
          <Button type="button" variant="secondary" disabled={pending} onClick={() => void reloadSetupPreferences()}>Reload saved preferences</Button>
        </>}
      </SetupCard> : !appearance.ready ? <><p className={styles.notice}>Saved display preferences are unavailable.</p><Button type="button" variant="secondary" disabled={pending} onClick={() => void appearance.reload()}>Reload preferences</Button></> : null}
      {error && preferenceRecovery === 'none' ? <Button type="button" variant="secondary" disabled={pending} onClick={resumeInitialSetup}>Check saved setup</Button> : null}
      <div className={styles.actions}><Button type="submit" disabled={pending || completed.current || preferenceRecovery !== 'none'}>{pending ? 'Saving setup…' : isCustomized ? 'Save setup & review Customized' : 'Save setup & choose dates'}</Button><Button type="button" variant="ghost" disabled={pending || completed.current} onClick={() => move('basics')}>Edit setup</Button></div>
    </form> : null}
  </SetupFlow>;
}
