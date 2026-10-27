"use client";

import { FormEvent, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { SetupCard, SetupFlow, setupStyles as styles } from '@/components/setup-flow';
import { api, getToken, setAuthToken } from '@/lib/api';
import { setupContinuation } from '@/lib/setup-continuation';
import { PasswordField } from '@/components/password-field';
import { API_BASE_URL } from '@/lib/env';

export default function LoginPage() {
  const router = useRouter();
  const query = useSearchParams();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [continuationToken, setContinuationToken] = useState<string | null>(null);
  const [status, setStatus] = useState('');
  const [pending, setPending] = useState(false);
  const inFlight = useRef(false);
  const mounted = useRef(false);
  useEffect(() => {
    mounted.current = true;
    const token = getToken();
    if (token) {
      setContinuationToken(token); setPending(true); inFlight.current = true;
      void continueSetup(token, true).finally(() => { inFlight.current = false; if (mounted.current) setPending(false); });
    }
    return () => { mounted.current = false; };
    // Existing-session recovery runs once; explicit retry captures the current token.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function continueSetup(token: string, replace = false) {
    try {
      const profile = await api.getProfile();
      if (!mounted.current || getToken() !== token) return;
      const destination = setupContinuation(profile, query.get('next'));
      if (replace) router.replace(destination); else router.push(destination);
    } catch {
      if (!mounted.current) return;
      if (getToken() === token) setStatus('Signed in. Unable to check your setup. Retry to continue with your saved account.');
      else if (!getToken()) { setContinuationToken(null); setStatus('Your session expired. Sign in again to continue setup.'); }
    }
  }

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
      setContinuationToken(payload.access_token); setPassword('');
      await continueSetup(payload.access_token);
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
      <PasswordField value={password} onChange={setPassword} autoComplete="current-password" disabled={pending} />
      <Link className={styles.secondaryLink} href={email ? `/reset-password?email=${encodeURIComponent(email.trim())}` : '/reset-password'}>Forgot password?</Link>
      {status ? <p role="alert" className={`${styles.notice} ${styles.error}`}>{status}</p> : null}
      {continuationToken ? <Button type="button" variant="secondary" disabled={pending} onClick={async () => {
        if (inFlight.current) return;
        const token = getToken();
        if (!token) { setContinuationToken(null); setStatus('Your session expired. Sign in again to continue.'); return; }
        setContinuationToken(token); inFlight.current = true; setPending(true); setStatus('');
        try { await continueSetup(token); } finally { inFlight.current = false; if (mounted.current) setPending(false); }
      }}>{status ? 'Retry setup check' : 'Continue with signed-in account'}</Button> : null}
      <div className={styles.actions}>
        <Button type="submit" disabled={pending || Boolean(continuationToken && getToken())}>{pending ? 'Signing in…' : 'Sign in'}</Button>
        <Link className={styles.textLink} href="/onboarding">Create an account</Link>
      </div>
    </form>
  </SetupFlow>;
}
