import React from 'react';
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import TodayPage from '@/app/today/page';

afterEach(() => { cleanup(); localStorage.clear(); vi.restoreAllMocks(); });

function fixture() {
  const writes: unknown[] = [];
  let finish: (response: Response) => void = () => {};
  globalThis.fetch = vi.fn(async (input, init) => {
    const url = String(input);
    if (url.endsWith('/health')) return Response.json({ status: 'ok' });
    if (url.includes('/plan/scheduling-context?')) return Response.json({ timezone: 'America/New_York', local_today: '2026-10-29', week_start: '2026-10-26', selected_dates: ['2026-10-29'], placement_revision: 1, plan: null });
    if (url.endsWith('/workout/today')) return Response.json({ session_id: 'daily', workout_occurrence_id: 'daily-occurrence', title: 'Daily Workout', date: '2026-10-29', exercises: [{ id: 'press', name: 'Daily Press', sets: 3, rep_range: [8, 12], recommended_working_weight: 20 }] });
    if (url.includes('/soreness?')) return Response.json([]);
    if (url.endsWith('/soreness') && init?.method === 'POST') {
      writes.push(JSON.parse(String(init.body)));
      return new Promise<Response>(resolve => { finish = resolve; });
    }
    return Response.json({});
  });
  return { writes, finish: (response: Response) => finish(response) };
}

test('soreness controls have an accessible dialog name and individual labels', async () => {
  fixture(); render(<TodayPage />);
  const dialog = await screen.findByRole('dialog', { name: /What.s sore today/ });
  expect(within(dialog).getByRole('combobox', { name: 'chest' })).toBeInTheDocument();
  expect(within(dialog).getByRole('textbox', { name: 'Optional soreness notes' })).toBeInTheDocument();
  expect(within(dialog).getByRole('region', { name: 'Soreness inputs' })).toBeInTheDocument();
});

test('pending save prevents duplicate writes or Skip and a failed save retains editable inputs for retry', async () => {
  const request = fixture(); render(<TodayPage />);
  await screen.findByText(/What.s sore today/);
  const notes = screen.getByPlaceholderText('Optional soreness notes');
  fireEvent.change(notes, { target: { value: 'Synthetic soreness note' } });
  const save = screen.getByRole('button', { name: 'Save & Start Workout' });
  fireEvent.click(save); fireEvent.click(save);
  await waitFor(() => expect(request.writes).toHaveLength(1));
  expect(screen.getByRole('button', { name: 'Skip' })).toBeDisabled();
  expect(notes).toBeDisabled();
  await act(async () => request.finish(Response.json({ detail: 'Synthetic failure' }, { status: 503 })));
  expect(await screen.findByRole('alert')).toHaveTextContent('Failed to save soreness');
  expect(notes).toHaveValue('Synthetic soreness note');
  expect(notes).toBeEnabled();
  fireEvent.click(screen.getByRole('button', { name: 'Save & Start Workout' }));
  await waitFor(() => expect(request.writes).toHaveLength(2));
  expect(request.writes[1]).toMatchObject({ entry_date: '2026-10-29', notes: 'Synthetic soreness note', severity_by_muscle: { chest: 'none' } });
  await act(async () => request.finish(Response.json({})));
  await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
});
