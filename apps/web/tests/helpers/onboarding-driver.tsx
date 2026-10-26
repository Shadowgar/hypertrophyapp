import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { vi } from 'vitest';
import OnboardingPage from '@/app/onboarding/page';
import { AppearanceProvider } from '@/components/appearance-provider';

export const phase1 = 'pure_bodybuilding_phase_1_full_body';
export const phase2 = 'pure_bodybuilding_phase_2_full_body';
export const programs = [
  { id: phase1, name: 'Full Body Phase 1', split: 'full_body', version: '1', days_supported: [2, 3, 4, 5] },
  { id: phase2, name: 'Full Body Phase 2', split: 'full_body', version: '2', days_supported: [2, 3, 4, 5] },
  { id: 'full_body_v1', name: 'Customize My Workout', split: 'full_body', version: '1', days_supported: [3] },
];
export const initialPreferences = { theme_family: 'classic', appearance: 'dark', weight_unit: 'lb', revision: 0 };
export type Call = { url: string; method: string; payload: Record<string, unknown>; token: string | null };
export function installSetupApi(calls: Call[], respond?: (call: Call) => Promise<Response> | undefined) {
  vi.stubGlobal('fetch', vi.fn(async (input, init) => {
    const call = { url: String(input), method: init?.method ?? 'GET', payload: init?.body ? JSON.parse(String(init.body)) : {}, token: new Headers(init?.headers).get('Authorization') };
    calls.push(call);
    const custom = respond?.(call);
    if (custom) return custom;
    if (call.url.endsWith('/plan/programs')) return Response.json(programs);
    if (call.url.endsWith('/auth/register')) return Response.json({ access_token: 'new-synthetic-account' });
    if (call.url.endsWith('/profile/preferences')) return Response.json(call.method === 'PUT' ? { ...initialPreferences, ...call.payload, revision: 1 } : initialPreferences);
    if (call.url.endsWith('/profile/initial-setup')) return Response.json({});
    return Response.json({ detail: 'Unexpected endpoint' }, { status: 503 });
  }));
}
export function renderSetup(children: React.ReactNode = <OnboardingPage />) {
  vi.stubGlobal('matchMedia', vi.fn(() => ({ matches: true, addEventListener: vi.fn(), removeEventListener: vi.fn() })));
  return render(<AppearanceProvider>{children}</AppearanceProvider>);
}
export async function createAccount(email = 'synthetic-onboarding@example.com') {
  await fillAccount(email);
  fireEvent.click(screen.getByRole('button', { name: 'Create account' }));
  await screen.findByRole('heading', { name: 'How would you like to train?' });
}
export async function fillAccount(email = 'synthetic-onboarding@example.com') {
  fireEvent.click(await screen.findByRole('button', { name: 'Create an account' }));
  fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Synthetic' } });
  fireEvent.change(screen.getByLabelText('Email'), { target: { value: email } });
  fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'Synthetic-only-Q98z!' } });
}
export async function chooseProgram(choice: string | null = phase1) {
  if (choice === 'full_body_v1') {
    fireEvent.click(screen.getByRole('button', { name: /Create a Customized program/ }));
  } else if (choice === null) {
    fireEvent.click(screen.getByRole('button', { name: /Help me choose/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Keep Auto preference' }));
  } else {
    fireEvent.click(screen.getByRole('button', { name: /Follow an Authored program/ }));
    const label = choice === phase1 ? 'Full Body Phase 1' : 'Full Body Phase 2';
    fireEvent.click(await screen.findByRole('button', { name: new RegExp(`^${label}`) }));
    fireEvent.click(screen.getByRole('button', { name: `Use ${label}` }));
  }
  await screen.findByRole('heading', { name: 'A few essentials' });
}
export function fillBasics() {
  fireEvent.change(screen.getByLabelText('Age'), { target: { value: '34' } });
  fireEvent.change(screen.getByLabelText(/Body weight \(/), { target: { value: '180' } });
  fireEvent.change(screen.getByLabelText('Training days per week'), { target: { value: '3' } });
}
export async function reviewSetup() {
  fireEvent.click(screen.getByRole('button', { name: 'Continue to equipment' }));
  await screen.findByRole('heading', { name: 'Your equipment' });
  fireEvent.click(screen.getByRole('button', { name: 'Review setup' }));
  await screen.findByRole('heading', { name: 'Review your setup' });
}
