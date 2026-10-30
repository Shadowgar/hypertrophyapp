import React from 'react';
import { render, screen } from '@testing-library/react';
import HomePage from '@/app/page';

test('Home prioritizes the confirmed next source action without requesting an inactive runner or calendar review', async () => {
  localStorage.setItem('hypertrophy_token', 'synthetic-flexible-home');
  const requests: string[] = [];
  vi.stubGlobal('fetch', vi.fn(async input => {
    const url = String(input); requests.push(url);
    if (url.endsWith('/training/next')) return Response.json({ mode: 'flexible', action: 'start',
      sequence_id: 'seq', state: 'active', occurrence_id: 'occ', source_position: 0,
      session: { title: 'Original source workout', exercises: [] } });
    if (url.endsWith('/profile')) return Response.json({ schedule_mode: 'flexible', name: 'Synthetic', setup_status: 'established' });
    if (url.endsWith('/workout/today')) return Response.json({ detail: 'Explicit Start required' }, { status: 409 });
    return Response.json({});
  }));
  render(<HomePage />);
  await screen.findByRole('button', { name: 'Start next workout' });
  expect(requests.some(url => url.endsWith('/workout/today'))).toBe(false);
  expect(requests.some(url => url.endsWith('/weekly-review/status'))).toBe(false);
  expect(screen.queryByRole('link', { name: 'Choose dates' })).not.toBeInTheDocument();
});
