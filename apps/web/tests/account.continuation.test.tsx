import React from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, test, vi } from 'vitest';
import LoginPage from '@/app/login/page';
import OnboardingPage from '@/app/onboarding/page';
import { setAuthToken } from '@/lib/api';
import { installSetupApi, renderSetup, createAccount, chooseProgram, type Call } from './helpers/onboarding-driver';
const nav = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn(), query: new URLSearchParams() }));
vi.mock('next/navigation', () => ({ useRouter: () => nav, useSearchParams: () => nav.query }));
beforeEach(() => { localStorage.clear(); sessionStorage.clear(); nav.push.mockReset(); nav.replace.mockReset(); nav.query = new URLSearchParams(); });
function signIn() {
 fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'synthetic@example.com' } });
 fireEvent.change(screen.getByLabelText('Password', { exact: true }), { target: { value: 'Synthetic-only-password' } });
 fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));
}
for (const [state, program, expected] of [['initial', null, '/onboarding'], ['planning', 'pure_bodybuilding_phase_1_full_body', '/week'], ['planning', 'full_body_v1', '/customize'], ['established', 'full_body_v1', '/today?workout=owned#sets']] as const) {
 test(`login resumes ${state} ${program} using server state without writes`, async () => {
  const calls: string[] = []; nav.query.set('next', '/today?workout=owned#sets');
  vi.stubGlobal('fetch', vi.fn(async (url, init) => { calls.push(`${init?.method ?? 'GET'} ${url}`); return Response.json(String(url).endsWith('/auth/login') ? { access_token: 'login-account' } : { setup_status: state, initial_setup_available: state === 'initial', selected_program_id: program }); }));
  render(<LoginPage />); signIn();
  await waitFor(() => expect(nav.push).toHaveBeenCalledWith(expected));
  expect(calls.filter(call => call.startsWith('POST'))).toEqual(['POST /api/auth/login']);
 });
}
test('setup-status failure offers retry without resubmitting credentials', async () => {
 let fail = true; const calls: string[] = [];
 vi.stubGlobal('fetch', vi.fn(async (url) => { calls.push(String(url)); if (String(url).endsWith('/auth/login')) return Response.json({ access_token: 'login-account' }); return fail ? Response.json({}, { status: 503 }) : Response.json({ setup_status: 'initial', initial_setup_available: true }); }));
 render(<LoginPage />); signIn();
 await screen.findByRole('button', { name: 'Retry setup check' }); fail = false;
 fireEvent.click(screen.getByRole('button', { name: 'Retry setup check' }));
 await waitFor(() => expect(nav.push).toHaveBeenCalledWith('/onboarding'));
 expect(calls.filter(url => url.endsWith('/auth/login'))).toHaveLength(1);
});
test('authenticated onboarding cannot return to registration through stale browser history', async () => {
 const calls: Call[] = []; installSetupApi(calls); renderSetup(); await createAccount(); await chooseProgram();
 act(() => { history.replaceState({ onboardingStage: 'account' }, '', '/onboarding'); window.dispatchEvent(new PopStateEvent('popstate', { state: { onboardingStage: 'account' } })); });
 expect(screen.queryByRole('button', { name: 'Create account' })).not.toBeInTheDocument();
 expect(screen.queryByRole('button', { name: 'Create an account' })).not.toBeInTheDocument();
 expect(calls.filter(call => call.url.endsWith('/auth/register'))).toHaveLength(1);
});
test('authenticated reload resumes program choice automatically without registration', async () => {
 setAuthToken('reload-account'); const calls: Call[] = [];
 installSetupApi(calls, call => call.url.endsWith('/profile') ? Promise.resolve(Response.json({ email: 'synthetic@example.com', name: 'Synthetic', initial_setup_available: true, setup_status: 'initial' })) : undefined);
 renderSetup(); await screen.findByRole('heading', { name: 'How would you like to train?' });
 expect(screen.queryByRole('button', { name: 'Create an account' })).not.toBeInTheDocument();
 expect(calls.some(call => call.method === 'POST')).toBe(false);
});
test('saved setup review does not reopen first initialization or alter consent', async () => {
 setAuthToken('saved-account'); const calls: Call[] = [];
 installSetupApi(calls, call => call.url.endsWith('/profile') ? Promise.resolve(Response.json({ email: 'synthetic@example.com', name: 'Synthetic', initial_setup_available: false, setup_status: 'planning', selected_program_id: 'full_body_v1', onboarding_answers: { primary_goals: ['build_muscle'], generated_onboarding: { consent: 'preserved' } } })) : undefined);
 renderSetup(); await screen.findByRole('heading', { name: 'Your saved setup' });
 expect(screen.getByRole('link', { name: 'Continue to Customized' })).toHaveAttribute('href', '/customize');
 expect(calls.some(call => call.method !== 'GET')).toBe(false);
});
for (const form of ['login', 'registration'] as const) {
 test(`${form} password visibility retains autofilled value and input focus with explicit visible state`, async () => {
  vi.stubGlobal('fetch', vi.fn(async () => Response.json([])));
  if (form === 'login') render(<LoginPage />);
  else { render(<OnboardingPage />); fireEvent.click(screen.getByRole('button', { name: 'Create an account' })); }
  const input = screen.getByLabelText('Password', { exact: true });
  fireEvent.input(input, { target: { value: 'Synthetic-autofill-only' } }); input.focus();
  fireEvent.pointerDown(screen.getByRole('button', { name: 'Show password' }));
  fireEvent.click(screen.getByRole('button', { name: 'Show password' }));
  expect(input).toHaveAttribute('type', 'text'); expect(input).toHaveValue('Synthetic-autofill-only'); expect(input).toHaveFocus();
  expect(screen.getByText('Password visible')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Hide password' })).toHaveAttribute('aria-controls', input.id);
  fireEvent.click(screen.getByRole('button', { name: 'Hide password' })); expect(input).toHaveAttribute('type', 'password');
  expect(screen.getByText('Password hidden')).toBeInTheDocument();
  expect(vi.mocked(fetch).mock.calls.some(([, init]) => init?.method === 'POST')).toBe(false);
 });
}

test('a delayed autofill value survives the visibility toggle before its input event arrives', () => {
 vi.stubGlobal('fetch', vi.fn(async () => Response.json([]))); render(<LoginPage />);
 const input = screen.getByLabelText('Password', { exact: true }) as HTMLInputElement;
 Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')!.set!.call(input, 'Synthetic-delayed-autofill');
 fireEvent.click(screen.getByRole('button', { name: 'Show password' }));
 expect(input).toHaveValue('Synthetic-delayed-autofill'); expect(input).toHaveAttribute('type', 'text');
});
test('returning to login while authenticated replaces the account form with setup continuation', async () => {
 setAuthToken('existing-token'); vi.stubGlobal('fetch', vi.fn(async () => Response.json({ initial_setup_available: true, setup_status: 'initial' })));
 render(<LoginPage />); await waitFor(() => expect(nav.replace).toHaveBeenCalledWith('/onboarding'));
 expect(vi.mocked(fetch).mock.calls.some(([, init]) => init?.method === 'POST')).toBe(false);
});
test('expired session during setup check explains reauthentication and never initializes a profile', async () => {
 vi.stubGlobal('fetch', vi.fn(async url => String(url).endsWith('/auth/login') ? Response.json({ access_token: 'expires' }) : Response.json({}, { status: 401 })));
 render(<LoginPage />); signIn(); await screen.findByText(/Your session expired/);
 expect(localStorage.getItem('hypertrophy_token')).toBeNull(); expect(nav.push).not.toHaveBeenCalled();
 expect(screen.getByRole('button', { name: 'Sign in' })).not.toBeDisabled();
});
test('a late profile reply cannot navigate an account switched after authentication', async () => {
 let resolve!: (response: Response) => void;
 const pending = new Promise<Response>(done => { resolve = done; });
 vi.stubGlobal('fetch', vi.fn(url => String(url).endsWith('/auth/login') ? Promise.resolve(Response.json({ access_token: 'account-a' })) : pending));
 render(<LoginPage />); signIn(); await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
 act(() => setAuthToken('account-b'));
 await act(async () => resolve(Response.json({ initial_setup_available: true, setup_status: 'initial' })));
 expect(nav.push).not.toHaveBeenCalled(); expect(localStorage.getItem('hypertrophy_token')).toBe('account-b');
});
