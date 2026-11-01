import React from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, test, vi } from 'vitest';
import LoginPage from '@/app/login/page';
import ResetPasswordPage from '@/app/reset-password/page';
import { getToken, setAuthToken } from '@/lib/api';

const navigation = vi.hoisted(() => ({ push: vi.fn(), query: new URLSearchParams() }));
vi.mock('next/navigation', () => ({ useRouter: () => ({ push: navigation.push }), useSearchParams: () => navigation.query }));
function deferred<T>() { let resolve!: (value: T) => void; return { promise: new Promise<T>(done => { resolve = done; }), resolve }; }
beforeEach(() => { localStorage.clear(); navigation.push.mockReset(); navigation.query = new URLSearchParams(); vi.stubGlobal('fetch', vi.fn()); });

test('sign-in disables duplicate submits and preserves the entire safe destination without profile writes', async () => {
  const response = deferred<Response>();
  vi.mocked(fetch).mockImplementation(input => String(input).endsWith('/auth/login') ? response.promise : Promise.resolve(Response.json({ setup_status: 'established', initial_setup_available: false })));
  navigation.query.set('next', '/today?workout=owned-occurrence#sets');
  render(<LoginPage />);
  fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'returning@example.com' } });
  fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'Synthetic-only-password' } });
  fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));
  expect(screen.getByRole('button', { name: 'Signing in…' })).toBeDisabled();
  fireEvent.submit(screen.getByLabelText('Email').closest('form')!);
  expect(fetch).toHaveBeenCalledTimes(1);
  await act(async () => response.resolve(Response.json({ access_token: 'synthetic-login-token' })));
  await waitFor(() => expect(navigation.push).toHaveBeenCalledWith('/today?workout=owned-occurrence#sets'));
  expect(fetch).toHaveBeenCalledWith(expect.stringMatching(/\/auth\/login$/), expect.any(Object));
});

test('late sign-in cannot replace an account that changed while authentication was pending', async () => {
  const response = deferred<Response>(); vi.mocked(fetch).mockReturnValue(response.promise);
  render(<LoginPage />);
  fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'returning@example.com' } });
  fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'Synthetic-only-password' } });
  fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));
  act(() => setAuthToken('different-account'));
  await act(async () => response.resolve(Response.json({ access_token: 'stale-login-token' })));
  expect(getToken()).toBe('different-account');
  expect(navigation.push).not.toHaveBeenCalled();
});

test('recovery defaults to a saved code, never requests email, and guards duplicate submits', async () => {
  const response = deferred<Response>(); vi.mocked(fetch).mockReturnValue(response.promise);
  render(<ResetPasswordPage />);
  expect(screen.queryByLabelText('Email')).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Recovery code'), { target: { value: 'synthetic-recovery-code' } });
  fireEvent.change(screen.getByLabelText('New password'), { target: { value: 'Synthetic-only-password' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save new password' }));
  fireEvent.submit(screen.getByLabelText('Recovery code').closest('form')!);
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(fetch).toHaveBeenCalledWith(expect.stringContaining('/auth/password-reset/confirm'), expect.anything());
  await act(async () => response.resolve(Response.json({ status: 'password_updated' })));
  expect(screen.getByRole('status')).toHaveTextContent('Password updated');
  expect(screen.queryByDisplayValue('Synthetic-only-password')).not.toBeInTheDocument();
});
test('legacy link remains usable and invalid code offers another code without email promises', async () => {
  navigation.query = new URLSearchParams({ token: 'expired-synthetic-link' });
  vi.mocked(fetch).mockResolvedValue(Response.json({ detail: 'invalid' }, { status: 400 }));
  render(<ResetPasswordPage />);
  expect(screen.getByLabelText('Recovery code')).toHaveValue('expired-synthetic-link');
  fireEvent.change(screen.getByLabelText('New password'), { target: { value: 'Synthetic-only-password' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save new password' }));
  await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent(/invalid or no longer available/i));
  fireEvent.click(screen.getByRole('button', { name: 'Try another code' }));
  expect(screen.getByLabelText('Recovery code')).toHaveValue(''); expect(screen.getByLabelText('New password')).toHaveValue('');
});
