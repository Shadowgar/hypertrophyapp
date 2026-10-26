import { act, fireEvent, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, test, vi } from 'vitest';
import { getToken, setAuthToken } from '@/lib/api';
import { Call, fillAccount, installSetupApi, renderSetup } from './helpers/onboarding-driver';
const push = vi.hoisted(() => vi.fn());
vi.mock('next/navigation', () => ({ useRouter: () => ({ push, replace: vi.fn() }) }));
const calls: Call[] = [];
beforeEach(() => { localStorage.clear(); calls.length = 0; push.mockReset(); });
test('registration validation failure retains inputs and never falls back to login', async () => {
  installSetupApi(calls, call => call.url.endsWith('/auth/register') ? Promise.resolve(Response.json({ detail: 'Password must be at least 8 characters' }, { status: 422 })) : undefined);
  renderSetup(); await fillAccount(); fireEvent.click(screen.getByRole('button', { name: 'Create account' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Registration failed: Password must be at least 8 characters');
  expect(screen.getByLabelText('Email')).toHaveValue('synthetic-onboarding@example.com');
  expect(calls.some(call => call.url.endsWith('/auth/login') || call.url.endsWith('/profile/initial-setup'))).toBe(false);
});
test('registration normalizes email casing and whitespace', async () => {
  installSetupApi(calls); renderSetup(); await fillAccount('  ATHLETE@Example.COM  ');
  fireEvent.click(screen.getByRole('button', { name: 'Create account' }));
  await screen.findByRole('heading', { name: 'How would you like to train?' });
  expect(calls.find(call => call.url.endsWith('/auth/register'))?.payload.email).toBe('athlete@example.com');
});
test('an existing-account response offers sign-in without authenticating or modifying its profile', async () => {
  installSetupApi(calls, call => call.url.endsWith('/auth/register') ? Promise.resolve(Response.json({ detail: 'Email already used' }, { status: 400 })) : undefined);
  renderSetup(); await fillAccount(); fireEvent.click(screen.getByRole('button', { name: 'Create account' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('An account already exists');
  expect(screen.getByRole('link', { name: 'I already have an account' })).toHaveAttribute('href', '/login');
  expect(calls.filter(call => call.method === 'POST')).toHaveLength(1); expect(getToken()).toBeNull();
});
test('duplicate registration and a late response after an account switch cannot install a stale token', async () => {
  let resolve!: (value: Response) => void;
  const pending = new Promise<Response>(done => { resolve = done; });
  installSetupApi(calls, call => call.url.endsWith('/auth/register') ? pending : undefined);
  renderSetup(); await fillAccount(); fireEvent.click(screen.getByRole('button', { name: 'Create account' }));
  fireEvent.submit(screen.getByLabelText('Email').closest('form')!);
  expect(calls.filter(call => call.url.endsWith('/auth/register'))).toHaveLength(1);
  act(() => setAuthToken('another-account'));
  await act(async () => resolve(Response.json({ access_token: 'stale-registration-token' })));
  await waitFor(() => expect(screen.getByText(/Account changed/)).toBeInTheDocument());
  expect(getToken()).toBe('another-account'); expect(push).not.toHaveBeenCalled();
  expect(calls.some(call => call.url.endsWith('/profile/initial-setup'))).toBe(false);
});
