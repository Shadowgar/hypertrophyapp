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
  vi.mocked(fetch).mockReturnValue(response.promise);
  navigation.query.set('next', '/today?workout=owned-occurrence#sets');
  render(<LoginPage />);
  fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'returning@example.com' } });
  fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'Synthetic-only-password' } });
  fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));
  expect(screen.getByRole('button', { name: 'Signing in…' })).toBeDisabled();
  fireEvent.submit(screen.getByLabelText('Email').closest('form')!);
  expect(fetch).toHaveBeenCalledTimes(1);
  await act(async () => response.resolve(Response.json({ access_token: 'synthetic-login-token' })));
  expect(navigation.push).toHaveBeenCalledWith('/today?workout=owned-occurrence#sets');
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

test('recovery starts with empty email and a separate request stage, ignores response credentials, and guards duplicates', async () => {
  const response = deferred<Response>(); vi.mocked(fetch).mockReturnValue(response.promise);
  render(<ResetPasswordPage />);
  expect(screen.getByLabelText('Email')).toHaveValue('');
  expect(screen.queryByLabelText('New password')).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'synthetic@example.com' } });
  fireEvent.click(screen.getByRole('button', { name: 'Send reset link' }));
  fireEvent.submit(screen.getByLabelText('Email').closest('form')!);
  expect(fetch).toHaveBeenCalledTimes(1);
  await act(async () => response.resolve(Response.json({ status: 'accepted', reset_token: 'must-never-be-displayed' })));
  expect(screen.getByRole('status')).toHaveTextContent('If recovery is available for this account');
  expect(screen.queryByDisplayValue('must-never-be-displayed')).not.toBeInTheDocument();
  expect(screen.queryByLabelText('New password')).not.toBeInTheDocument();
});

test('an expired mailbox link offers a fresh request without retaining the token or password', async () => {
  navigation.query = new URLSearchParams({ token: 'expired-synthetic-link' });
  vi.mocked(fetch).mockResolvedValue(Response.json({ detail: 'invalid' }, { status: 400 }));
  render(<ResetPasswordPage />);
  fireEvent.change(screen.getByLabelText('New password'), { target: { value: 'Synthetic-only-password' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save new password' }));
  await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent(/invalid or expired/i));
  fireEvent.click(screen.getByRole('button', { name: 'Request a new link' }));
  expect(screen.getByLabelText('Email')).toHaveValue('');
  expect(screen.queryByDisplayValue('expired-synthetic-link')).not.toBeInTheDocument();
  expect(screen.queryByDisplayValue('Synthetic-only-password')).not.toBeInTheDocument();
});
