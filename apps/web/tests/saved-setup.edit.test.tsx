import React from 'react';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { SavedSetup } from '@/components/saved-setup';
import type { Profile } from '@/lib/api';
import { canonicalLoad } from '@/lib/appearance';

const profile = { name: 'Saved Name', age: 32, weight: 80, days_available: 3,
  selected_program_id: 'pure_bodybuilding_phase_2_full_body', onboarding_answers: { primary_goals: ['strength'], generated_onboarding: { consent: 'retained' } },
} as unknown as Profile;
let writes: Array<{ path: string; method?: string; body: Record<string, unknown> }>;
let response: (body: Record<string, unknown>) => Promise<Response>;
beforeEach(() => {
  localStorage.setItem('hypertrophy_token', 'synthetic-basics-a'); writes = [];
  response = async body => Response.json({ ...profile, ...body });
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const body = JSON.parse(String(init?.body)); writes.push({ path: String(input), method: init?.method, body });
    return response(body);
  }));
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
function save() { fireEvent.click(screen.getByRole('button', { name: 'Save basics' })); }

test('review has no writes and explicitly saves only edited basics in canonical kg', async () => {
  render(<SavedSetup profile={profile} unit="lb" />);
  expect(screen.getByText('strength')).toBeVisible(); expect(writes).toHaveLength(0);
  fireEvent.change(screen.getByLabelText('Current name'), { target: { value: '  Updated Name  ' } });
  fireEvent.change(screen.getByLabelText('Current age'), { target: { value: '35' } });
  fireEvent.change(screen.getByLabelText('Current bodyweight (lb)'), { target: { value: '180' } });
  expect(writes).toHaveLength(0); save();
  await screen.findByText(/Basics saved/);
  expect(writes).toEqual([{ path: expect.stringMatching(/\/profile\/setup-basics$/), method: 'PATCH', body: { name: 'Updated Name', age: 35, weight: canonicalLoad(180, 'lb') } }]);
  expect(screen.getByText('strength')).toBeVisible();
});

test('saving an unchanged rounded pound display preserves its exact stored kg', async () => {
  render(<SavedSetup profile={profile} unit="lb" />); save();
  await screen.findByText(/Basics saved/); expect(writes[0].body.weight).toBe(80);
});

test('failure remains editable and supports an explicit retry', async () => {
  response = async () => Response.json({ detail: 'Synthetic outage' }, { status: 503 });
  render(<SavedSetup profile={profile} unit="kg" />); save();
  expect(await screen.findByRole('alert')).toHaveTextContent(/Synthetic outage/);
  expect(screen.getByRole('button', { name: 'Save basics' })).toBeEnabled();
  response = async body => Response.json({ ...profile, ...body }); save();
  await screen.findByText(/Basics saved/); expect(writes).toHaveLength(2);
});

test('slow save shows pending feedback and prevents duplicate submits', async () => {
  let release: (() => void) | undefined;
  response = body => new Promise(resolve => { release = () => resolve(Response.json({ ...profile, ...body })); });
  render(<SavedSetup profile={profile} unit="kg" />); save();
  expect(screen.getByRole('button', { name: 'Saving basics…' })).toBeDisabled();
  fireEvent.submit(screen.getByRole('form', { name: 'Edit current basics' }));
  await waitFor(() => expect(release).toBeDefined()); expect(writes).toHaveLength(1);
  await act(async () => { release!(); }); await screen.findByText(/Basics saved/);
});

test('a retired account cannot submit or adopt a delayed basics response', async () => {
  let release: (() => void) | undefined;
  response = body => new Promise(resolve => { release = () => resolve(Response.json({ ...profile, ...body })); });
  render(<SavedSetup profile={profile} unit="kg" />); save();
  await waitFor(() => expect(release).toBeDefined());
  localStorage.setItem('hypertrophy_token', 'synthetic-basics-b');
  await act(async () => { release!(); });
  expect(screen.queryByText(/Basics saved/)).not.toBeInTheDocument();
  expect(screen.getByRole('alert')).toHaveTextContent(/Account changed.*Reload setup/);
  save(); expect(writes).toHaveLength(1);
});

test('invalid current basics remain local until corrected', async () => {
  render(<SavedSetup profile={profile} unit="kg" />);
  fireEvent.change(screen.getByLabelText('Current name'), { target: { value: '   ' } });
  fireEvent.submit(screen.getByRole('form', { name: 'Edit current basics' }));
  expect(await screen.findByRole('alert')).toHaveTextContent(/name.*age.*bodyweight/i);
  expect(writes).toHaveLength(0);
});
