import { act, fireEvent, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, test, vi } from 'vitest';
import { setAuthToken } from '@/lib/api';
import { Call, chooseProgram, createAccount, fillBasics, initialPreferences, installSetupApi, renderSetup, reviewSetup } from './helpers/onboarding-driver';

const push = vi.hoisted(() => vi.fn());
vi.mock('next/navigation', () => ({ useRouter: () => ({ push, replace: vi.fn() }) }));
const calls: Call[] = [];
beforeEach(() => { localStorage.clear(); calls.length = 0; push.mockReset(); });
const preferenceWrites = () => calls.filter(call => call.url.endsWith('/profile/preferences') && call.method === 'PUT');
const setupWrites = () => calls.filter(call => call.url.endsWith('/profile/initial-setup'));
async function enterSetup() {
  renderSetup(); await createAccount(); await chooseProgram(); fillBasics();
  fireEvent.change(screen.getByLabelText('Weight display'), { target: { value: 'kg' } });
  await reviewSetup();
  fireEvent.click(screen.getByText('Nutrition targets (optional)'));
  fireEvent.change(screen.getByLabelText('Daily calorie target'), { target: { value: '2400' } });
}
function submit() { fireEvent.click(screen.getByRole('button', { name: 'Save setup & choose dates' })); }

test('a preference conflict requires reload and explicit review before replacing the saved unit', async () => {
  let reads = 0;
  installSetupApi(calls, call => {
    if (!call.url.endsWith('/profile/preferences')) return undefined;
    if (call.method === 'GET') return Promise.resolve(Response.json(++reads === 1 ? initialPreferences : { ...initialPreferences, theme_family: 'graphite', revision: 5 }));
    if (preferenceWrites().length === 1) return Promise.resolve(Response.json({ detail: 'Preferences changed elsewhere' }, { status: 409 }));
    return Promise.resolve(Response.json({ ...call.payload, revision: 6 }));
  });
  await enterSetup(); submit();
  const reload = await screen.findByRole('button', { name: 'Reload saved preferences' });
  expect(screen.getByRole('button', { name: 'Save setup & choose dates' })).toBeDisabled();
  fireEvent.submit(screen.getByLabelText('Daily calorie target').closest('form')!);
  expect(preferenceWrites()).toHaveLength(1);
  fireEvent.click(reload);
  const confirm = await screen.findByRole('button', { name: 'Use selected unit and save setup' });
  expect(screen.getByText(/Graphite/)).toBeInTheDocument();
  expect(screen.getByLabelText('Daily calorie target')).toHaveValue(2400);
  expect(screen.getByText(/34 years · 81.6466266 kg/)).toBeInTheDocument();
  expect(setupWrites()).toHaveLength(0);
  fireEvent.click(confirm);
  await waitFor(() => expect(push).toHaveBeenCalledWith('/week'));
  expect(preferenceWrites()[1].payload).toEqual({ theme_family: 'graphite', appearance: 'dark', weight_unit: 'kg', expected_revision: 5 });
  expect(setupWrites()).toHaveLength(1);
  expect(setupWrites()[0].payload).toMatchObject({ weight: 81.6466266, age: 34, calories: 2400 });
});

test('a lost preference acknowledgment is reconciled before setup without replaying the preference write', async () => {
  let reads = 0;
  installSetupApi(calls, call => {
    if (!call.url.endsWith('/profile/preferences')) return undefined;
    if (call.method === 'GET') return Promise.resolve(Response.json(++reads === 1 ? initialPreferences : { ...initialPreferences, weight_unit: 'kg', revision: 1 }));
    return Promise.reject(new TypeError('Synthetic response lost after commit'));
  });
  await enterSetup(); submit();
  fireEvent.click(await screen.findByRole('button', { name: 'Reload saved preferences' }));
  const confirm = await screen.findByRole('button', { name: 'Continue with saved preferences' });
  expect(setupWrites()).toHaveLength(0);
  expect(screen.getByLabelText('Daily calorie target')).toHaveValue(2400);
  fireEvent.click(confirm);
  await waitFor(() => expect(push).toHaveBeenCalledWith('/week'));
  expect(preferenceWrites()).toHaveLength(1);
  expect(setupWrites()).toHaveLength(1);
  expect(setupWrites()[0].payload.weight).toBe(81.6466266);
});

test('a failed preference reload keeps answers and blocks setup until a successful explicit reread', async () => {
  let reads = 0;
  installSetupApi(calls, call => {
    if (!call.url.endsWith('/profile/preferences')) return undefined;
    if (call.method === 'GET') {
      reads += 1;
      return Promise.resolve(reads === 2 ? Response.json({ detail: 'Unavailable' }, { status: 503 }) : Response.json({ ...initialPreferences, weight_unit: reads === 1 ? 'lb' : 'kg', revision: reads === 1 ? 0 : 1 }));
    }
    return Promise.resolve(Response.json({ detail: 'Changed' }, { status: 409 }));
  });
  await enterSetup(); submit();
  fireEvent.click(await screen.findByRole('button', { name: 'Reload saved preferences' }));
  await screen.findByText(/Saved appearance could not be loaded/);
  expect(screen.getByRole('button', { name: 'Save setup & choose dates' })).toBeDisabled();
  expect(screen.queryByRole('button', { name: 'Continue with saved preferences' })).not.toBeInTheDocument();
  expect(setupWrites()).toHaveLength(0);
  expect(screen.getByLabelText('Daily calorie target')).toHaveValue(2400);
  fireEvent.click(screen.getByRole('button', { name: 'Reload saved preferences' }));
  fireEvent.click(await screen.findByRole('button', { name: 'Continue with saved preferences' }));
  await waitFor(() => expect(push).toHaveBeenCalledWith('/week'));
  expect(setupWrites()).toHaveLength(1);
});

test('submitted nutrition targets are frozen while the preference write is pending', async () => {
  let resolve!: (response: Response) => void;
  const pending = new Promise<Response>(done => { resolve = done; });
  installSetupApi(calls, call => call.url.endsWith('/profile/preferences') && call.method === 'PUT' ? pending : undefined);
  await enterSetup(); submit();
  await waitFor(() => expect(preferenceWrites()).toHaveLength(1));
  expect(screen.getByLabelText('Daily calorie target')).toBeDisabled();
  await act(async () => resolve(Response.json({ ...initialPreferences, weight_unit: 'kg', revision: 1 })));
  await waitFor(() => expect(push).toHaveBeenCalledWith('/week'));
  expect(setupWrites()[0].payload.calories).toBe(2400);
});

test('an account change retires a pending preference reread without enabling the old setup', async () => {
  let reads = 0;
  let resolve!: (response: Response) => void;
  const pending = new Promise<Response>(done => { resolve = done; });
  installSetupApi(calls, call => {
    if (!call.url.endsWith('/profile/preferences')) return undefined;
    if (call.method === 'GET') return ++reads === 2 ? pending : Promise.resolve(Response.json(initialPreferences));
    return Promise.resolve(Response.json({ detail: 'Changed' }, { status: 409 }));
  });
  await enterSetup(); submit();
  fireEvent.click(await screen.findByRole('button', { name: 'Reload saved preferences' }));
  await waitFor(() => expect(reads).toBe(2));
  act(() => setAuthToken('different-synthetic-account'));
  await act(async () => resolve(Response.json({ ...initialPreferences, weight_unit: 'kg', revision: 1 })));
  expect(screen.getByText(/Account changed/)).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Continue with saved preferences' })).not.toBeInTheDocument();
  expect(setupWrites()).toHaveLength(0);
  expect(push).not.toHaveBeenCalled();
});
