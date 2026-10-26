import React from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, test, vi } from 'vitest';
import OnboardingPage from '@/app/onboarding/page';
import { getToken, setAuthToken } from '@/lib/api';
const push = vi.hoisted(() => vi.fn());
vi.mock('next/navigation', () => ({ useRouter: () => ({ push, replace: vi.fn() }) }));
const phase1 = 'pure_bodybuilding_phase_1_full_body';
const phase2 = 'pure_bodybuilding_phase_2_full_body';
const programs = [phase1, phase2, 'full_body_v1'].map(id => ({ id, name: id, days_supported: [3], split: 'full_body' }));
const calls: Array<{url: string; method: string; payload: Record<string, unknown>; token: string | null}> = [];
function deferred<T>() { let resolve!: (value: T) => void; return { promise: new Promise<T>(done => { resolve = done; }), resolve }; }
beforeEach(() => { localStorage.clear(); push.mockReset(); calls.length = 0; });
function setup(selectedProgramId: string | null, profile?: () => Promise<Response>) {
  localStorage.setItem('hypertrophy_onboarding_draft_v1', JSON.stringify({ phase: 'account', authMode: 'register', selectedProgramId,
    firstName: 'Synthetic', birthday: '1990-01-01', email: 'synthetic-onboarding@example.com' }));
  vi.stubGlobal('fetch', vi.fn(async (input, init) => {
    const url = String(input); const method = init?.method ?? 'GET';
    calls.push({ url, method, payload: init?.body ? JSON.parse(String(init.body)) : {}, token: new Headers(init?.headers).get('Authorization') });
    if (url.endsWith('/plan/programs')) return Response.json(programs);
    if (url.endsWith('/auth/register')) return Response.json({ access_token: 'new-synthetic-account' });
    if (url.endsWith('/profile/initial-setup')) return profile ? profile() : Response.json({});
    // Generating during registration cannot be hidden behind success or retried to create another plan.
    return Response.json({ detail: 'Generation/review unavailable' }, { status: 503 });
  }));
  render(<OnboardingPage />);
}
async function submit() {
  fireEvent.change(await screen.findByLabelText('Password'), { target: { value: 'Synthetic-only-Q98z!' } });
  fireEvent.click(screen.getByRole('button', { name: /^Continue$/ }));
}
test.each([[null, '/week', 'auto'], [phase1, '/week', 'manual'], [phase2, '/week', 'manual'], ['full_body_v1', '/customize', 'manual']])(
  'choice %s reaches truthful setup without generating, switching or fabricating a review', async (choice, destination, mode) => {
    setup(choice); await submit();
    await waitFor(() => expect(push).toHaveBeenCalledWith(destination));
    const writes = calls.filter(call => call.method === 'POST');
    expect(writes.map(call => call.url.split('/').at(-1))).toEqual(['register', 'initial-setup']);
    const profile = writes[1].payload;
    expect(profile.selected_program_id).toBe(choice);
    expect(profile.program_selection_mode).toBe(mode);
    for (const key of ['nutrition_phase', 'calories', 'protein', 'fat', 'carbs', 'adherence_score', 'sleep_quality']) expect(profile).not.toHaveProperty(key);
    expect(screen.queryByText(/first plan initialized/i)).not.toBeInTheDocument();
  });
test('explicit nutrition targets are goals only, never a weekly report', async () => {
  setup(phase1);
  fireEvent.click(await screen.findByText('Nutrition targets (optional)'));
  fireEvent.change(screen.getByLabelText('Daily calorie target'), { target: { value: '2400' } });
  fireEvent.change(screen.getByLabelText('Protein target (g)'), { target: { value: '140' } });
  await submit();
  await waitFor(() => expect(push).toHaveBeenCalledWith('/week'));
  const profile = calls.find(call => call.url.endsWith('/profile/initial-setup'))!.payload;
  expect(profile).toMatchObject({ calories: 2400, protein: 140 });
  expect(profile).not.toHaveProperty('fat');
  expect(calls.some(call => call.url.includes('weekly-review'))).toBe(false);
});
test('a failed profile save remains recoverable without another registration or plan', async () => {
  let attempt = 0;
  setup(phase1, async () => ++attempt === 1 ? Response.json({ detail: 'Temporarily unavailable' }, { status: 503 }) : Response.json({}));
  await submit();
  await screen.findByRole('alert');
  expect(push).not.toHaveBeenCalled();
  expect(getToken()).toBe('new-synthetic-account');
  await submit();
  await waitFor(() => expect(push).toHaveBeenCalledWith('/week'));
  expect(calls.filter(call => call.url.endsWith('/auth/register'))).toHaveLength(1);
  expect(calls.filter(call => call.url.endsWith('/profile/initial-setup'))).toHaveLength(2);
  expect(calls.filter(call => call.url.endsWith('/profile/initial-setup')).every(call => call.token === 'Bearer new-synthetic-account')).toBe(true);
});
test('an account switch during profile save prevents late navigation and cross-account retry', async () => {
  const pending = deferred<Response>();
  setup(phase1, () => pending.promise); await submit();
  await waitFor(() => expect(calls.some(call => call.url.endsWith('/profile/initial-setup'))).toBe(true));
  act(() => setAuthToken('different-synthetic-account'));
  await act(async () => pending.resolve(Response.json({})));
  expect(push).not.toHaveBeenCalled();
  expect(getToken()).toBe('different-synthetic-account');
  expect(calls.filter(call => call.url.endsWith('/profile/initial-setup'))).toHaveLength(1);
  expect(await screen.findByText(/account changed/i)).toBeInTheDocument();
});

test('reloading a registered but incomplete account offers explicit setup recovery without registering again', async () => {
  setAuthToken('new-synthetic-account');
  vi.stubGlobal('fetch', vi.fn(async (input, init) => {
    const url = String(input);
    calls.push({ url, method: init?.method ?? 'GET', payload: {}, token: new Headers(init?.headers).get('Authorization') });
    if (url.endsWith('/plan/programs')) return Response.json(programs);
    if (url.endsWith('/profile')) return Response.json({ email: 'synthetic-onboarding@example.com', name: 'Synthetic', initial_setup_available: true });
    return Response.json({});
  }));
  const view = render(<OnboardingPage />); view.unmount(); render(<OnboardingPage />);
  fireEvent.click(await screen.findByRole('button', { name: 'Continue account setup' }));
  await screen.findByText(/Review your answers to finish this account/);
  expect(screen.getByText('Step 1 of 16')).toBeInTheDocument();
  expect(calls.some(call => call.method === 'POST')).toBe(false);
});

test('reload after a committed profile with lost response continues the saved choice without a second write', async () => {
  setAuthToken('new-synthetic-account');
  vi.stubGlobal('fetch', vi.fn(async (input, init) => {
    const url = String(input);
    calls.push({ url, method: init?.method ?? 'GET', payload: {}, token: new Headers(init?.headers).get('Authorization') });
    if (url.endsWith('/plan/programs')) return Response.json(programs);
    return Response.json({ email: 'synthetic-onboarding@example.com', initial_setup_available: false, selected_program_id: 'full_body_v1' });
  }));
  render(<OnboardingPage />);
  fireEvent.click(await screen.findByRole('button', { name: 'Continue account setup' }));
  await waitFor(() => expect(push).toHaveBeenCalledWith('/customize'));
  expect(calls.some(call => call.method === 'POST')).toBe(false);
});

test('a late error body from the prior account cannot replace the account-change recovery message', async () => {
  const body = deferred<{ detail: string }>();
  const response = new Response(null, { status: 503 });
  response.json = () => body.promise;
  setup(phase1, async () => response); await submit();
  await waitFor(() => expect(calls.some(call => call.url.includes('/profile'))).toBe(true));
  await act(async () => {});
  act(() => setAuthToken('different-synthetic-account'));
  await act(async () => body.resolve({ detail: 'Old account failure' }));
  expect(screen.queryByText(/Old account failure/)).not.toBeInTheDocument();
  expect(screen.getByText(/Account changed/)).toBeInTheDocument();
});
