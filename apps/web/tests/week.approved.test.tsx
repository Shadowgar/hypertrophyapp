import React from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, test, vi } from 'vitest';
import WeekPage from '@/app/week/page';
const model = vi.hoisted(() => ({ resolve: null as null | ((value: unknown) => void), delayed: false }));
const fixture = { week_start: '2026-10-26', local_today: '2026-10-26', timezone: 'UTC', placement_revision: 1, selected_dates: ['2026-10-26', '2026-10-28'], plan: null };
beforeEach(() => {
  model.delayed = false; localStorage.setItem('hypertrophy_token', 'week-account-a');
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes('/plan/scheduling-context')) {
      if (model.delayed) return await new Promise<Response>(resolve => { model.resolve = value => resolve(Response.json(value)); });
      return Response.json(fixture);
    }
    if (url.endsWith('/profile')) return Response.json({ selected_program_id: null, program_selection_mode: 'auto' });
    if (url.endsWith('/programs')) return Response.json([]);
    if (url.includes('/history/calendar')) return Response.json({ days: [] });
    return Response.json({}, { status: 404 });
  }));
});
test('Week exposes local weekday slots and keeps preview separate from activation', async () => {
  render(<WeekPage />);
  await screen.findByRole('heading', { name: 'Your training week' });
  const monday = await screen.findByRole('checkbox', { name: 'Mon, Oct 26' });
  expect(monday).toBeChecked();
  expect(screen.getByRole('group', { name: 'Select actual training dates' })).toHaveClass('ux-date-picker');
  expect(screen.queryByRole('button', { name: 'Activate selected dates' })).not.toBeInTheDocument();
  expect(vi.mocked(fetch).mock.calls.every(([, init]) => !init?.method || init.method === 'GET')).toBe(true);
});
test('a delayed retired-account calendar reply cannot install dates', async () => {
  model.delayed = true; render(<WeekPage />);
  await waitFor(() => expect(model.resolve).not.toBeNull());
  localStorage.setItem('hypertrophy_token', 'week-account-b');
  await act(async () => { model.resolve!(fixture); await new Promise(resolve => setTimeout(resolve, 20)); });
  expect(screen.queryByRole('checkbox', { name: 'Mon, Oct 26' })).not.toBeInTheDocument();
});
