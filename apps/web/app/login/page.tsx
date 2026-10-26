"use client";

import { FormEvent, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { SetupCard, SetupFlow, setupStyles as styles } from '@/components/setup-flow';
import { getToken, setAuthToken } from '@/lib/api';
import { safeReturnPath } from '@/lib/appearance';
import { API_BASE_URL } from '@/lib/env';

export default function LoginPage() {
  const router = useRouter();
  const query = useSearchParams();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [status, setStatus] = useState('');
  const [pending, setPending] = useState(false);
  const inFlight = useRef(false);
  const mounted = useRef(false);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (inFlight.current) return;
    const originalToken = getToken();
    inFlight.current = true;
    setPending(true); setStatus('');
    const isCurrent = () => mounted.current && getToken() === originalToken;
    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim().toLowerCase(), password }),
      });
      if (!isCurrent()) return;
      if (!response.ok) { setStatus('Unable to sign in. Check your email and password and try again.'); return; }
      const payload = await response.json() as { access_token?: string };
      if (!isCurrent()) return;
      if (!payload.access_token) throw new Error('Missing authentication result');
      setAuthToken(payload.access_token);
      router.push(safeReturnPath(query.get('next')));
    } catch {
      if (isCurrent()) setStatus('Unable to sign in. Check your connection and try again.');
    } finally {
      inFlight.current = false;
      if (mounted.current) setPending(false);
    }
  }

  return <SetupFlow title="Welcome back" subtitle="Sign in to continue where you left off." aside={<>
    <SetupCard title="Back to your workout"><p>After sign-in, return to the workout you opened.</p></SetupCard>
    <SetupCard title="Your setup stays yours"><p>Signing in does not recreate a plan or change your program.</p></SetupCard>
  </>}>
    <form className={styles.form} onSubmit={submit}>
      <label className={styles.field}>Email<input type="email" autoComplete="username" required value={email} disabled={pending} onChange={event => setEmail(event.target.value)} /></label>
      <label className={styles.field}>Password<input type={showPassword ? 'text' : 'password'} autoComplete="current-password" required value={password} disabled={pending} onChange={event => setPassword(event.target.value)} /></label>
      <Button type="button" variant="secondary" className={styles.control} aria-pressed={showPassword} onClick={() => setShowPassword(value => !value)}>{showPassword ? 'Hide password' : 'Show password'}</Button>
      <Link className={styles.secondaryLink} href={email ? `/reset-password?email=${encodeURIComponent(email.trim())}` : '/reset-password'}>Forgot password?</Link>
      {status ? <p role="alert" className={`${styles.notice} ${styles.error}`}>{status}</p> : null}
      <div className={styles.actions}>
        <Button type="submit" disabled={pending}>{pending ? 'Signing in…' : 'Sign in'}</Button>
        <Link className={styles.textLink} href="/onboarding">Create an account</Link>
      </div>
    </form>
  </SetupFlow>;
}
