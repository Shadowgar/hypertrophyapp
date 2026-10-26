import { act, fireEvent, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, test, vi } from 'vitest';
import { getToken, setAuthToken } from '@/lib/api';
import { Call, chooseProgram, createAccount, fillBasics, installSetupApi, phase1, phase2, renderSetup, reviewSetup } from './helpers/onboarding-driver';
const push = vi.hoisted(() => vi.fn());
vi.mock('next/navigation', () => ({ useRouter: () => ({ push, replace: vi.fn() }) }));
const calls: Call[] = [];
function deferred<T>() { let resolve!: (value: T) => void; return { promise: new Promise<T>(done => { resolve = done; }), resolve }; }
beforeEach(() => { localStorage.clear(); push.mockReset(); calls.length = 0; });
async function setup(choice: string | null, profile?: () => Promise<Response>) {
  installSetupApi(calls, call => call.url.endsWith('/profile/initial-setup') ? profile?.() : undefined);
  renderSetup(); await createAccount(); await chooseProgram(choice); fillBasics(); await reviewSetup();
}
function submit() { fireEvent.click(screen.getByRole('button', { name: /Save setup &/ })); }

test.each([[null, '/week', 'auto'], [phase1, '/week', 'manual'], [phase2, '/week', 'manual'], ['full_body_v1', '/customize', 'manual']])(
  'choice %s reaches truthful setup without generating, switching or fabricating a review', async (choice, destination, mode) => {
    await setup(choice); submit(); await waitFor(() => expect(push).toHaveBeenCalledWith(destination));
    const writes = calls.filter(call => call.method === 'POST');
    expect(writes.map(call => call.url.split('/').at(-1))).toEqual(['register', 'initial-setup']);
    expect(writes[1].payload).toMatchObject({ selected_program_id: choice, program_selection_mode: mode });
    for (const key of ['nutrition_phase', 'calories', 'protein', 'fat', 'carbs', 'adherence_score', 'sleep_quality']) expect(writes[1].payload).not.toHaveProperty(key);
    expect(calls.some(call => /generate|consent|activate|weekly-review|program-switch/.test(call.url))).toBe(false);
  });
test('explicit nutrition targets are goals only, never a weekly report', async () => {
  await setup(phase1); fireEvent.click(screen.getByText('Nutrition targets (optional)'));
  fireEvent.change(screen.getByLabelText('Daily calorie target'), { target: { value: '2400' } });
  fireEvent.change(screen.getByLabelText('Protein target (g)'), { target: { value: '140' } });
  submit(); await waitFor(() => expect(push).toHaveBeenCalledWith('/week'));
  const profile = calls.find(call => call.url.endsWith('/profile/initial-setup'))!.payload;
  expect(profile).toMatchObject({ calories: 2400, protein: 140 }); expect(profile).not.toHaveProperty('fat');
  expect(calls.some(call => call.url.includes('weekly-review'))).toBe(false);
});
test('a failed profile save remains recoverable without another registration or plan', async () => {
  let attempt = 0;
  await setup(phase1, async () => ++attempt === 1 ? Response.json({ detail: 'Temporarily unavailable' }, { status: 503 }) : Response.json({}));
  submit(); await screen.findByRole('alert'); expect(push).not.toHaveBeenCalled(); expect(getToken()).toBe('new-synthetic-account');
  submit(); await waitFor(() => expect(push).toHaveBeenCalledWith('/week'));
  expect(calls.filter(call => call.url.endsWith('/auth/register'))).toHaveLength(1);
  const writes = calls.filter(call => call.url.endsWith('/profile/initial-setup'));
  expect(writes).toHaveLength(2); expect(writes.every(call => call.token === 'Bearer new-synthetic-account')).toBe(true);
});
test('an account switch during profile save prevents late navigation and cross-account retry', async () => {
  const pending = deferred<Response>(); await setup(phase1, () => pending.promise); submit();
  await waitFor(() => expect(calls.some(call => call.url.endsWith('/profile/initial-setup'))).toBe(true));
  act(() => setAuthToken('different-synthetic-account')); await act(async () => pending.resolve(Response.json({})));
  expect(push).not.toHaveBeenCalled(); expect(getToken()).toBe('different-synthetic-account');
  expect(calls.filter(call => call.url.endsWith('/profile/initial-setup'))).toHaveLength(1);
  expect(screen.getByText(/Account changed/)).toBeInTheDocument();
});
test('reloading a registered but incomplete account offers explicit setup recovery without registering again', async () => {
  setAuthToken('new-synthetic-account');
  installSetupApi(calls, call => call.url.endsWith('/profile') ? Promise.resolve(Response.json({ email: 'synthetic@example.com', name: 'Synthetic', initial_setup_available: true })) : undefined);
  const first = renderSetup(); first.unmount(); renderSetup();
  fireEvent.click(await screen.findByRole('button', { name: 'Continue account setup' }));
  await screen.findByText(/Review your answers to finish this account/);
  await chooseProgram();
  expect(screen.getByLabelText('Age')).toHaveValue(null); expect(screen.getByLabelText('Body weight (lb)')).toHaveValue(null);
  expect(calls.some(call => call.method === 'POST')).toBe(false);
});
test('reload after a committed profile with lost response continues the saved choice without a second write', async () => {
  setAuthToken('new-synthetic-account');
  installSetupApi(calls, call => call.url.endsWith('/profile') ? Promise.resolve(Response.json({ email: 'synthetic@example.com', initial_setup_available: false, selected_program_id: 'full_body_v1' })) : undefined);
  renderSetup(); fireEvent.click(await screen.findByRole('button', { name: 'Continue account setup' }));
  await waitFor(() => expect(push).toHaveBeenCalledWith('/customize')); expect(calls.some(call => call.method === 'POST')).toBe(false);
});
test('a late error body from the prior account cannot replace the account-change recovery message', async () => {
  const body = deferred<{ detail: string }>(); const response = new Response(null, { status: 503 }); response.json = () => body.promise;
  await setup(phase1, async () => response); submit();
  await waitFor(() => expect(calls.some(call => call.url.endsWith('/profile/initial-setup'))).toBe(true));
  await act(async () => {}); act(() => setAuthToken('different-synthetic-account'));
  await act(async () => body.resolve({ detail: 'Old account failure' }));
  expect(screen.queryByText(/Old account failure/)).not.toBeInTheDocument(); expect(screen.getByText(/Account changed/)).toBeInTheDocument();
});
