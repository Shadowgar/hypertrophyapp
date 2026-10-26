"use client";

import { FormEvent, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { SetupCard, SetupFlow, setupStyles as styles } from '@/components/setup-flow';
import { API_BASE_URL } from '@/lib/env';

export default function ResetPasswordPage() {
  const query = useSearchParams();
  const [stage, setStage] = useState<'request' | 'confirm' | 'complete'>(() => query.get('token') ? 'confirm' : 'request');
  const [email, setEmail] = useState(() => query.get('email') ?? '');
  const [token, setToken] = useState(() => query.get('token') ?? '');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [pending, setPending] = useState(false);
  const [status, setStatus] = useState('');
  const [error, setError] = useState(false);
  const [expired, setExpired] = useState(false);
  const inFlight = useRef(false);
  const mounted = useRef(false);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (inFlight.current || stage === 'complete') return;
    inFlight.current = true; setPending(true); setStatus(''); setError(false); setExpired(false);
    const requesting = stage === 'request';
    try {
      const response = await fetch(`${API_BASE_URL}/auth/password-reset/${requesting ? 'request' : 'confirm'}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requesting ? { email: email.trim().toLowerCase() } : { token, new_password: password }),
      });
      if (!mounted.current) return;
      if (!response.ok) {
        const invalid = !requesting && [400, 422].includes(response.status);
        setExpired(invalid); setError(true);
        setStatus(invalid ? 'This link is invalid or expired. Request a new link.' : 'Unable to complete this request. Please try again.');
        return;
      }
      if (requesting) {
        // Never consume credentials from an HTTP acknowledgement, even from an old server.
        setStatus('If recovery is available for this account, check your email.');
      } else {
        setPassword(''); setToken(''); setStage('complete');
        setStatus('Password updated. You can sign in with your new password.');
      }
    } catch {
      if (mounted.current) { setError(true); setStatus('Unable to connect. Check your connection and try again.'); }
    } finally {
      inFlight.current = false;
      if (mounted.current) setPending(false);
    }
  }

  function requestAgain() {
    setToken(''); setPassword(''); setShowPassword(false); setStage('request'); setStatus(''); setError(false); setExpired(false);
  }

  return <SetupFlow title={stage === 'confirm' ? 'Choose a new password' : 'Reset your password'} subtitle={stage === 'request' ? 'Request a reset link for your account.' : 'Return to your saved training.'} aside={<>
    <SetupCard title="Your training stays saved"><p>Resetting your password does not clear your profile or workout history.</p></SetupCard>
    <SetupCard title="Use your mailbox"><p>Open the link delivered to your email. A used or expired link needs a new request.</p></SetupCard>
  </>}>
    <form className={styles.form} onSubmit={submit}>
      {stage === 'request' ? <label className={styles.field}>Email<input type="email" autoComplete="email" required value={email} disabled={pending} onChange={event => setEmail(event.target.value)} /></label> : null}
      {stage === 'confirm' ? <>
        <label className={styles.field}>Reset token<input type="password" autoComplete="off" required minLength={16} value={token} disabled={pending} onChange={event => setToken(event.target.value)} /></label>
        <label className={styles.field}>New password<input type={showPassword ? 'text' : 'password'} autoComplete="new-password" required minLength={8} value={password} disabled={pending} onChange={event => setPassword(event.target.value)} /></label>
        <Button type="button" variant="secondary" aria-pressed={showPassword} onClick={() => setShowPassword(value => !value)}>{showPassword ? 'Hide password' : 'Show password'}</Button>
      </> : null}
      {status ? <p role={error ? 'alert' : 'status'} className={`${styles.notice} ${error ? styles.error : ''}`}>{status}</p> : null}
      <div className={styles.actions}>
        {expired ? <Button type="button" onClick={requestAgain}>Request a new link</Button> : stage !== 'complete' ? <Button type="submit" disabled={pending}>{pending ? 'Please wait…' : stage === 'request' ? 'Send reset link' : 'Save new password'}</Button> : null}
        <Link href="/login" className={stage === 'complete' ? styles.secondaryLink : styles.textLink}>Back to sign in</Link>
      </div>
      {stage === 'request' ? <Button type="button" variant="ghost" disabled={pending} onClick={() => { setStage('confirm'); setStatus(''); setError(false); }}>Enter a reset code</Button> : null}
    </form>
  </SetupFlow>;
}
