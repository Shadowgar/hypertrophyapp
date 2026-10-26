import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import CheckinPage from '@/components/weekly-review';

test('unknown nutrition and adherence stay blank and cannot be submitted as zero or a default score', async () => {
  const writes: string[] = [];
  vi.stubGlobal('fetch', vi.fn(async (input, init) => {
    const url = String(input);
    if (init?.method === 'POST') writes.push(url);
    if (url.endsWith('/profile')) return Response.json({ weight: 80, days_available: 3, calories: null, protein: null, fat: null, carbs: null });
    return Response.json({ week_start: '2026-10-26', today_is_sunday: true, review_required: true });
  }));
  render(<CheckinPage />);
  await screen.findByText('Weekly review available');
  for (const name of ['Daily Calories', 'Protein (g)', 'Fat (g)', 'Carbs (g)']) expect(screen.getByLabelText(name)).toHaveValue(null);
  expect(screen.getByLabelText('Adherence Score (1-5)')).toHaveValue('');
  fireEvent.submit(screen.getByRole('button', { name: /Save Weekly Review/ }).closest('form')!);
  await waitFor(() => expect(screen.getByText(/Enter your chosen nutrition targets and report your actual adherence/)).toBeInTheDocument());
  expect(writes).toEqual([]);
});
