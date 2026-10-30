import React from 'react';
import { render, screen } from '@testing-library/react';
import WeeklyReview from '@/components/weekly-review';

test('Flexible review does not invent calendar frequency, completion percentages or adaptation', async () => {
  const requests: string[] = [];
  vi.stubGlobal('fetch', vi.fn(async input => {
    const url = String(input); requests.push(url);
    return Response.json({ schedule_mode: 'flexible', days_available: null, expected_sessions_per_week: null });
  }));
  render(<WeeklyReview />);
  await screen.findByText(/Calendar-based weekly review is unavailable for Flexible training/);
  expect(requests.every(url => url.endsWith('/profile'))).toBe(true);
  expect(screen.queryByText('Sessions next week (2-5)')).not.toBeInTheDocument();
  expect(screen.queryByText('Coaching Preview')).not.toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Continue Flexible training' })).toHaveAttribute('href', '/today');
});
