import React from 'react';
import { render, screen } from '@testing-library/react';
import { beforeEach, expect, test, vi } from 'vitest';
import HomePage from '@/app/page';
import SettingsPage from '@/app/settings/page';
vi.mock('next/navigation', () => ({ useRouter: () => ({ push: vi.fn(), replace: vi.fn() }) }));
beforeEach(() => { localStorage.clear(); localStorage.setItem('hypertrophy_token', 'owned-account'); });
for (const [state, label] of [['initial', 'Resume Setup'], ['planning', 'Resume Setup'], ['established', 'Review/Edit Setup']] as const) {
 for (const [name, Component] of [['Home', HomePage], ['Settings', SettingsPage]] as const) {
  test(`${name} exposes ${label} for server setup status ${state} without writes`, async () => {
   const writes: string[] = [];
   vi.stubGlobal('fetch', vi.fn(async (input, init) => {
    const url = String(input); if (init?.method && init.method !== 'GET') writes.push(url);
    if (url.endsWith('/profile')) return Response.json({ setup_status: state, initial_setup_available: state === 'initial', email: 'synthetic@example.com', name: 'Synthetic', selected_program_id: 'pure_bodybuilding_phase_1_full_body', age: 30, weight: 80, days_available: 3, equipment_profile: [] });
    if (url.includes('/plan/scheduling-context')) return Response.json({ timezone: 'UTC', local_today: '2026-10-27', week_start: '2026-10-26', selected_dates: [], placement_revision: 0, plan: null });
    if (url.includes('/history/analytics')) return Response.json({});
    return Response.json({ detail: 'Unavailable in synthetic fixture' }, { status: 404 });
   }));
   render(<Component />);
   expect(await screen.findByRole('link', { name: label })).toHaveAttribute('href', '/onboarding');
   expect(writes).toHaveLength(0);
  });
 }
}
