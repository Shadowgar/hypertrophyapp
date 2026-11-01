"use client";

import { FormEvent, useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { getToken } from '@/lib/api';
import { API_BASE_URL } from '@/lib/env';
import styles from './account-recovery.module.css';

type SecurityEvent = { id: string; kind: string; created_at: string; acknowledged_at: string | null };
type RecoveryState = { remaining: number; events: SecurityEvent[] };
const notices: Record<string, string> = {
  password_recovered: 'Your password was recovered. Previous sign-ins were invalidated.',
  recovery_codes_generated: 'A new set of recovery codes was generated.',
  recovery_codes_revoked: 'Previously saved recovery codes were revoked.',
};

export function AccountRecovery() {
  const [session, setSession] = useState(getToken);
  const [state, setState] = useState<RecoveryState | null>(null);
  const [password, setPassword] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const [codes, setCodes] = useState<string[]>([]);
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState('');
  const [retry, setRetry] = useState(0);
  const epoch = useRef(0);
  const inFlight = useRef(false);

  useEffect(() => {
    function changed() {
      epoch.current += 1;
      setSession(getToken()); setCodes([]); setPassword(''); setConfirmed(false);
      setState(null); setMessage(''); setPending(false); inFlight.current = false;
    }
    function storage(event: StorageEvent) { if (!event.key || event.key === 'hypertrophy_token') changed(); }
    window.addEventListener('hypertrophy:auth-token-changed', changed);
    window.addEventListener('storage', storage);
    return () => {
      epoch.current += 1;
      window.removeEventListener('hypertrophy:auth-token-changed', changed);
      window.removeEventListener('storage', storage);
    };
  }, []);

  useEffect(() => {
    if (!session) return;
    const controller = new AbortController();
    const current = epoch.current;
    fetch(`${API_BASE_URL}/auth/recovery-codes`, { headers: { Authorization: `Bearer ${session}` }, cache: 'no-store', signal: controller.signal })
      .then(async response => { if (!response.ok) throw new Error('unavailable'); return response.json() as Promise<RecoveryState>; })
      .then(result => { if (epoch.current === current && getToken() === session) setState(result); })
      .catch(() => { if (!controller.signal.aborted && epoch.current === current && getToken() === session) setMessage('Recovery settings unavailable. Sign in again or retry.'); });
    return () => controller.abort();
  }, [session, retry]);

  async function generate(event: FormEvent) {
    event.preventDefault();
    if (!session || !confirmed || inFlight.current) return;
    inFlight.current = true; setPending(true); setCodes([]); setMessage('');
    const current = epoch.current;
    try {
      const response = await fetch(`${API_BASE_URL}/auth/recovery-codes`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${session}` }, cache: 'no-store',
        body: JSON.stringify({ current_password: password, confirmed: true, command_id: crypto.randomUUID() }),
      });
      if (epoch.current !== current || getToken() !== session) return;
      if (!response.ok) {
        setMessage(response.status === 429 ? 'Too many attempts. Wait before trying again.' : 'Unable to generate codes. Check your current password and sign in again if needed.');
        return;
      }
      const result = await response.json() as { status: string; codes: string[] };
      if (epoch.current !== current || getToken() !== session) return;
      setCodes(result.codes); setConfirmed(false); setRetry(value => value+1);
      if (!result.codes.length) setMessage('This request already completed. Codes cannot be displayed again; generate a new set if you did not save them.');
    } catch {
      if (epoch.current === current && getToken() === session) setMessage('Request outcome unknown. Codes cannot be retrieved; sign in and generate a new set if needed.');
    } finally {
      if (epoch.current === current && getToken() === session) { setPassword(''); setPending(false); inFlight.current = false; }
    }
  }

  async function acknowledge(id: string) {
    const current = epoch.current;
    try {
      const response = await fetch(`${API_BASE_URL}/auth/recovery-events/${encodeURIComponent(id)}/acknowledge`, { method: 'POST', headers: { Authorization: `Bearer ${session}` } });
      if (epoch.current !== current || getToken() !== session) return;
      if (!response.ok) throw new Error('unavailable');
      setRetry(value => value+1);
    } catch { if (epoch.current === current && getToken() === session) setMessage('Unable to acknowledge the notice. Try again.'); }
  }

  if (!session) return null;
  return <section id="account-recovery" className={styles.panel} aria-labelledby="recovery-title">
    <h2 id="recovery-title">Password recovery</h2>
    <p>Save one-time recovery codes to regain access without email or SMS. Anyone with a code can reset your password. Keep them private, outside FERRAVIS.</p>
    {state ? <p>{state.remaining} unused recovery codes remain.</p> : <Button variant="secondary" onClick={() => setRetry(value => value+1)}>Retry recovery settings</Button>}
    {state?.events.filter(event => !event.acknowledged_at).map(event => <div key={event.id} className={styles.notice}>
      <p>{notices[event.kind] ?? 'Account security settings changed.'}</p>
      <time>{new Date(event.created_at+'Z').toLocaleString()}</time>{' '}
      <Button variant="secondary" onClick={() => acknowledge(event.id)}>Acknowledge security notice</Button>
    </div>)}
    {codes.length ? <div className={styles.notice}>
      <h3>Save these codes now</h3>
      <p>They are shown only once. Each works once. Generating another set invalidates this set.</p>
      <ol className={styles.codes}>{codes.map(code => <li key={code}><code>{code}</code></li>)}</ol>
      <Button onClick={() => { setCodes([]); setMessage('Codes hidden. FERRAVIS cannot display them again.'); }}>I saved these codes</Button>
    </div> : null}
    <form onSubmit={generate} className={styles.form}>
      <label>Current password<input type="password" autoComplete="current-password" required minLength={8} maxLength={72} disabled={pending} value={password} onChange={event => setPassword(event.target.value)} /></label>
      <label className={styles.confirm}><input type="checkbox" checked={confirmed} disabled={pending} onChange={event => setConfirmed(event.target.checked)} />I will save the new codes privately. Replacing codes invalidates all previously unused codes.</label>
      <Button type="submit" disabled={!state || !confirmed || pending}>{pending ? 'Generating…' : 'Generate recovery codes'}</Button>
    </form>
    {message ? <p role="status">{message}</p> : null}
  </section>;
}
