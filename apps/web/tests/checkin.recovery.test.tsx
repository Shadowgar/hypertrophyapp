import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, test, vi } from 'vitest';
import WeeklyReview from '@/components/weekly-review';
import CheckinPage from '@/app/checkin/page';
vi.mock('@/components/coaching-intelligence-panel', () => ({ default: () => null }));
let committed: boolean, lost: boolean, posts: number;
beforeEach(() => {
  committed = false; lost = false; posts = 0;
  localStorage.setItem('hypertrophy_token', 'synthetic-review-account');
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.includes('/weekly-review/status')) return Response.json({ week_start: '2026-10-26', existing_review_submitted: committed, review_required: true });
    if (url.endsWith('/profile')) return Response.json({ weight: 80, calories: 2200, protein: 150, fat: 70, carbs: 240, days_available: 3, scheduling_timezone: 'UTC' });
    if (url.endsWith('/weekly-review') && init?.method === 'POST') {
      posts++; committed = true;
      if (lost) throw new TypeError('Synthetic lost acknowledgement');
      return Response.json({ summary: null, adjustments: { global_set_delta: 0, global_weight_scale: 1, weak_point_exercises: [], exercise_overrides: [] } });
    }
    if (url.includes('/history/weekly-checkins')) return Response.json({ entries: [] });
    if (url.includes('/plan/scheduling-context')) return Response.json({ week_start: '2026-10-26' });
    return Response.json({}, { status: 404 });
  }));
});
async function save() {
  await screen.findByText('Weekly review available');
  fireEvent.change(screen.getByLabelText('Adherence Score (1-5)'), { target: { value: '4' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save Weekly Review' }));
}
test('an acknowledged detailed review cannot be submitted twice', async () => {
  render(<WeeklyReview />); await save(); await screen.findByText('Weekly review saved');
  expect(screen.getByRole('button', { name: 'Save Weekly Review' })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Save Weekly Review' })); expect(posts).toBe(1);
});
test('lost detailed-review reply is checked without another write', async () => {
  lost = true; render(<WeeklyReview />); await save();
  fireEvent.click(await screen.findByRole('button', { name: 'Check saved review' }));
  await screen.findByText(/A weekly review is now recorded.*nothing was resent/);
  expect(screen.getByRole('button', { name: 'Save Weekly Review' })).toBeDisabled(); expect(posts).toBe(1);
});
test('closing and reopening detailed review preserves the unknown transaction', async () => {
  lost = true; render(<CheckinPage />);
  const summary = screen.getByText('Detailed weekly review and nutrition targets');
  fireEvent.click(summary); await save();
  await screen.findByRole('button', { name: 'Check saved review' });
  fireEvent.click(summary); fireEvent.click(summary);
  await waitFor(() => expect(screen.getByRole('button', { name: 'Save Weekly Review' })).toBeDisabled());
  expect(screen.getByRole('button', { name: 'Check saved review' })).toBeVisible(); expect(posts).toBe(1);
});
