"use client";

import { FormEvent, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { SetupCard, SetupFlow, setupStyles as styles } from '@/components/setup-flow';
import { API_BASE_URL } from '@/lib/env';
import { clearAuthToken } from '@/lib/api';

export default function ResetPasswordPage() {
  const query = useSearchParams();
  const [complete, setComplete] = useState(false);
  const [token, setToken] = useState(() => query.get('token') ?? '');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [pending, setPending] = useState(false);
  const [status, setStatus] = useState('');
  const [error, setError] = useState(false);
  const inFlight = useRef(false);
  const mounted = useRef(false);
  useEffect(() => {
    mounted.current = true;
    // Legacy emailed links remain accepted; remove the bearer from the address
    // bar once loaded. New recovery codes are submitted only in POST bodies.
    if (query.get('token') || query.get('email')) window.history.replaceState(null, '', window.location.pathname);
    return () => { mounted.current = false; };
  }, [query]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (inFlight.current || complete) return;
    inFlight.current = true; setPending(true); setStatus(''); setError(false);
    try {
      const response = await fetch(`${API_BASE_URL}/auth/password-reset/confirm`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, cache: 'no-store',
        body: JSON.stringify({ token: token.trim(), new_password: password }),
      });
      if (!mounted.current) return;
      if (!response.ok) {
        setError(true);
        setStatus([400, 422].includes(response.status) ? 'This code is invalid or no longer available. Try another saved code or contact your trusted operator.' : response.status === 429 ? 'Too many attempts. Wait before trying again.' : 'Unable to complete this request. Please try again.');
        return;
      }
      setPassword(''); setToken(''); setComplete(true);
      setStatus('Password updated. You can sign in with your new password.');
    } catch {
      if (mounted.current) { setError(true); setStatus('Unable to connect. Check your connection and try again.'); }
    } finally {
      inFlight.current = false;
      if (mounted.current) { setPending(false); setPassword(''); }
    }
  }

  return <SetupFlow title="Reset your password" subtitle="Use a saved recovery code or a code issued by your trusted operator." aside={<>
    <SetupCard title="Your training stays saved"><p>Resetting your password does not clear your profile or workout history.</p></SetupCard>
    <SetupCard title="No email needed"><p>Use one unused code saved from Settings, or ask your trusted operator for a private, short-lived code. An email address alone cannot recover an account.</p></SetupCard>
  </>}>
    <form className={styles.form} onSubmit={submit}>
      {!complete ? <>
        <label className={styles.field}>Recovery code<input type="password" autoComplete="off" required minLength={16} maxLength={128} value={token} disabled={pending} onChange={event => setToken(event.target.value)} /></label>
        <label className={styles.field}>New password<input type={showPassword ? 'text' : 'password'} autoComplete="new-password" required minLength={8} maxLength={72} value={password} disabled={pending} onChange={event => setPassword(event.target.value)} /></label>
        <Button type="button" variant="secondary" aria-pressed={showPassword} onClick={() => setShowPassword(value => !value)}>{showPassword ? 'Hide password' : 'Show password'}</Button>
      </> : null}
      {status ? <p role={error ? 'alert' : 'status'} className={`${styles.notice} ${error ? styles.error : ''}`}>{status}</p> : null}
      <div className={styles.actions}>
        {!complete ? <Button type="submit" disabled={pending}>{pending ? 'Please wait…' : 'Save new password'}</Button> : null}
        {error ? <Button type="button" disabled={pending} onClick={() => { setToken(''); setPassword(''); setShowPassword(false); setStatus(''); setError(false); }}>Try another code</Button> : null}
        <Link href="/login" onClick={() => clearAuthToken()} className={complete ? styles.secondaryLink : styles.textLink}>Back to sign in</Link>
      </div>
    </form>
  </SetupFlow>;
}
