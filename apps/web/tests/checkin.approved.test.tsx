import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, test, vi } from 'vitest';
import CheckinPage from '@/app/checkin/page';

const appearance = vi.hoisted(() => ({ weight_unit: 'lb' as 'lb' | 'kg' }));
vi.mock('@/components/appearance-provider', () => ({ useAppearance: () => ({ preferences: appearance }) }));
vi.mock('@/components/coaching-intelligence-panel', () => ({ default: () => null }));
let entries: Record<string, unknown>[];
let loseReply: boolean;
let failBeforeCommit: boolean;
let posted: Record<string, unknown>[];
beforeEach(() => {
  appearance.weight_unit = 'lb'; entries = []; posted = []; loseReply = false; failBeforeCommit = false;
  localStorage.setItem('hypertrophy_token', 'synthetic-checkin');
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.includes('/plan/scheduling-context')) return Response.json({ local_today: '2026-10-26', week_start: '2026-10-26', timezone: 'UTC' });
    if (url.includes('/history/weekly-checkins')) return Response.json({ entries });
    if (url.endsWith('/weekly-checkin') && init?.method === 'POST') {
      const payload = JSON.parse(String(init.body)); posted.push(payload);
      if (failBeforeCommit) throw new TypeError('Synthetic request lost before commit');
      entries = [{ ...payload, created_at: '2026-10-26T12:00:00' }];
      if (loseReply) throw new TypeError('Synthetic lost response');
      return Response.json({ status: 'logged' });
    }
    return Response.json({}, { status: 404 });
  }));
});

test('a failed request with no matching history keeps recovery visible without resending', async () => {
  failBeforeCommit = true;
  render(<CheckinPage />);
  fireEvent.change(await screen.findByLabelText('Bodyweight (lb)'), { target: { value: '180' } });
  fireEvent.change(screen.getByLabelText('How many planned sessions did you complete?'), { target: { value: '4' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save check-in' }));
  fireEvent.click(await screen.findByRole('button', { name: 'Check saved result' }));
  await screen.findByText(/No matching new check-in is visible yet/);
  expect(screen.getByRole('button', { name: 'Save check-in' })).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Check saved result' })).toBeEnabled();
  expect(posted).toHaveLength(1);
});

test('a retired account form cannot save under the new account', async () => {
  render(<CheckinPage />);
  fireEvent.change(await screen.findByLabelText('Bodyweight (lb)'), { target: { value: '180' } });
  fireEvent.change(screen.getByLabelText('How many planned sessions did you complete?'), { target: { value: '4' } });
  localStorage.setItem('hypertrophy_token', 'different-synthetic-account');
  fireEvent.click(screen.getByRole('button', { name: 'Save check-in' }));
  await new Promise(resolve => setTimeout(resolve, 10));
  expect(posted).toHaveLength(0);
});

test('optional check-in saves actual reports without nutrition or plan generation, using canonical weight', async () => {
  render(<CheckinPage />);
  const input = await screen.findByLabelText('Bodyweight (lb)');
  expect(input).toHaveValue(null);
  fireEvent.change(input, { target: { value: '180' } });
  fireEvent.change(screen.getByLabelText('How many planned sessions did you complete?'), { target: { value: '4' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save check-in' }));
  await screen.findByText('Check-in saved.');
  expect(posted).toEqual([{ week_start: '2026-10-26', body_weight: 81.6466266, adherence_score: 4 }]);
  const writes = vi.mocked(fetch).mock.calls.filter(([, init]) => init?.method === 'POST');
  expect(writes).toHaveLength(1);
  expect(String(writes[0][0])).toMatch(/\/weekly-checkin$/);
});

test('switching unit preserves the draft canonical weight without rounding it on submit', async () => {
  const view = render(<CheckinPage />);
  fireEvent.change(await screen.findByLabelText('Bodyweight (lb)'), { target: { value: '180' } });
  appearance.weight_unit = 'kg'; view.rerender(<CheckinPage />);
  await waitFor(() => expect(screen.getByLabelText('Bodyweight (kg)')).toHaveValue(81.6466266));
  appearance.weight_unit = 'lb'; view.rerender(<CheckinPage />);
  await waitFor(() => expect(screen.getByLabelText('Bodyweight (lb)')).toHaveValue(180));
});

test('lost committed reply is reconciled by reading history, never a second POST', async () => {
  loseReply = true;
  render(<CheckinPage />);
  fireEvent.change(await screen.findByLabelText('Bodyweight (lb)'), { target: { value: '180' } });
  fireEvent.change(screen.getByLabelText('How many planned sessions did you complete?'), { target: { value: '4' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save check-in' }));
  await screen.findByText(/Save result unknown/);
  expect(screen.getByRole('button', { name: 'Save check-in' })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Check saved result' }));
  await screen.findByText('Check-in saved.');
  expect(posted).toHaveLength(1);
});
