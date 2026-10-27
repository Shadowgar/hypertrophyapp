"use client";
import { useId, useRef, useState, type CSSProperties } from 'react';
import { Button } from './ui/button';
import { setupStyles as styles } from './setup-flow';

export function PasswordField({ value, onChange, autoComplete, disabled, minLength }: {
  value: string; onChange: (value: string) => void;
  autoComplete: 'current-password' | 'new-password'; disabled?: boolean; minLength?: number;
}) {
  const id = useId(); const input = useRef<HTMLInputElement>(null);
  const [visible, setVisible] = useState(false);
  return <div className={styles.fields}>
    <label className={styles.field} htmlFor={id}>Password</label>
    <input ref={input} id={id} name="password" type={visible ? 'text' : 'password'}
      autoComplete={autoComplete} autoCapitalize="none" autoCorrect="off" spellCheck={false}
      required minLength={minLength} value={value} disabled={disabled}
      style={visible ? { WebkitTextSecurity: 'none' } as CSSProperties : undefined}
      onChange={event => onChange(event.target.value)} />
    <Button type="button" variant="secondary" className={styles.control} disabled={disabled}
      aria-controls={id} aria-pressed={visible}
      onPointerDown={event => { if (document.activeElement === input.current) event.preventDefault(); }}
      onClick={() => {
        // Autofill can update the live value before its input event arrives.
        if (input.current && input.current.value !== value) onChange(input.current.value);
        setVisible(previous => !previous);
      }}>{visible ? 'Hide password' : 'Show password'}</Button>
    <p className={styles.helper} role="status" aria-live="polite">{visible ? 'Password visible' : 'Password hidden'}</p>
  </div>;
}
