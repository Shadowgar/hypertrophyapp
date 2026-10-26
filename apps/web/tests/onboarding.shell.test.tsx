import React from 'react';
import { act, fireEvent, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, test, vi } from 'vitest';
import OnboardingPage from '@/app/onboarding/page';
import { AppShell } from '@/components/app-shell';
import { clearAuthToken, setAuthToken } from '@/lib/api';
import { Call, chooseProgram, createAccount, fillBasics, installSetupApi, renderSetup, reviewSetup } from './helpers/onboarding-driver';
const push = vi.hoisted(() => vi.fn());
vi.mock('next/navigation', () => ({ usePathname: () => '/onboarding', useRouter: () => ({ push, replace: vi.fn() }) }));
const token = (sub: string) => `synthetic.${btoa(JSON.stringify({sub}))}.signature`;
function deferred<T>() { let resolve!: (value: T) => void; return { promise: new Promise<T>(done => { resolve = done; }), resolve }; }
const calls: Call[] = [];
beforeEach(() => { localStorage.clear(); push.mockReset(); calls.length = 0; });
async function setup(profile: Promise<Response>) {
  installSetupApi(calls, call => call.url.endsWith('/auth/register') ? Promise.resolve(Response.json({ access_token: token('registered-account') })) : call.url.endsWith('/profile/initial-setup') ? profile : undefined);
  renderSetup(<AppShell><OnboardingPage /></AppShell>);
  await createAccount(); await chooseProgram(); fillBasics(); await reviewSetup();
  fireEvent.click(screen.getByRole('button', { name: 'Save setup & choose dates' }));
  await waitFor(() => expect(calls.some(call => call.url.endsWith('/profile/initial-setup'))).toBe(true));
}
test.each(['saved', 'failed'])("the real shell retains the registering account's %s profile result", async outcome => {
  const profile = deferred<Response>(); await setup(profile.promise);
  expect(screen.getByRole('button', { name: 'Sign out' })).toBeInTheDocument();
  await act(async () => profile.resolve(outcome === 'saved' ? Response.json({}) : Response.json({ detail: 'Synthetic failure' }, { status: 503 })));
  if (outcome === 'saved') await waitFor(() => expect(push).toHaveBeenCalledWith('/week'));
  else { expect(push).not.toHaveBeenCalled(); expect(await screen.findByRole('alert')).toHaveTextContent('Profile save failed: Synthetic failure'); }
});
test('a different account resets private setup inputs and the old draft inside the stable shell', async () => {
  installSetupApi(calls);
  renderSetup(<AppShell><OnboardingPage /></AppShell>); await createAccount(); await chooseProgram(); fillBasics();
  expect(screen.getByLabelText('Body weight (lb)')).toHaveValue(180);
  act(() => setAuthToken(token('other-account'))); await screen.findByText(/Account changed/);
  expect(screen.queryByDisplayValue('180')).not.toBeInTheDocument(); expect(localStorage.getItem('hypertrophy_onboarding_draft_v1')).toBeNull();
  expect(push).not.toHaveBeenCalled();
});
test.each(['logout', 'storage-switch'])('%s during profile save retires the old save without retaining private form state', async action => {
  const profile = deferred<Response>(); await setup(profile.promise);
  act(() => {
    if (action === 'logout') clearAuthToken();
    else { localStorage.setItem('hypertrophy_token', token('other-account')); window.dispatchEvent(new StorageEvent('storage', { key: 'hypertrophy_token', newValue: token('other-account') })); }
  });
  await act(async () => profile.resolve(Response.json({})));
  expect(push).not.toHaveBeenCalled();
  expect(calls.filter(call => call.url.endsWith('/profile/initial-setup')).map(call => call.token)).toEqual([`Bearer ${token('registered-account')}`]);
  expect(localStorage.getItem('hypertrophy_onboarding_draft_v1')).toBeNull();
  expect(screen.queryByDisplayValue('180')).not.toBeInTheDocument(); expect(screen.getByText(/Account changed/)).toBeInTheDocument();
});
