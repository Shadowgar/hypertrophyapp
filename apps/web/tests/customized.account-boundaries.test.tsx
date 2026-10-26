import React from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, test, vi } from 'vitest';
import CustomizedPage from '@/app/customize/page';
import { CustomizedInventoryEditor } from '@/components/customized-inventory';
import type { InventoryDocument } from '@/lib/customized-inventory';

const dates = ['2026-10-26', '2026-10-28', '2026-10-30'];
const request = { mode: 'customized', bundle_id: 'shorter-current', goal: 'hypertrophy', population: 'broadly_healthy_adult', training_context: 'current', selected_dates: dates, timezone: 'UTC', cap_minutes: 60, cap_kind: 'hard', equipment: ['dumbbell'], skill: 'intermediate', restrictions: [] };
const proposal = { proposal_id: 'old-account-proposal', revision: 1, plan_version: 1, snapshot_hash: 'synthetic-snapshot', state: 'review_required', blocking_reasons: [], snapshot: { request, preview: { candidate_name: 'Private old-account program', sessions: [], missing_actions: [], dose_conflicts: [] }, comparison_reference: null, workload_changes: [] } };
type Call = { path: string; method: string; body: string | undefined; headers: Headers };
const calls: Call[] = [];
function deferred() { let resolve!: (value: Response) => void; return { promise: new Promise<Response>(done => { resolve = done; }), resolve }; }
function install(respond: (call: Call) => Promise<Response> | undefined = () => undefined) {
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const call = { path: String(input), method: init?.method ?? 'GET', body: init?.body ? String(init.body) : undefined, headers: new Headers(init?.headers) };
    calls.push(call);
    const response = respond(call); if (response) return response;
    if (call.path.endsWith('/customized/options')) return Response.json({ equipment: ['dumbbell'], restrictions: [] });
    if (call.path.endsWith('/customized/active')) return Response.json({ plans: [] });
    return Response.json(proposal);
  }));
}
beforeEach(() => { localStorage.clear(); localStorage.setItem('hypertrophy_token', 'synthetic-account-a'); window.history.replaceState(null, '', '/customize'); calls.length = 0; });
async function fillDraft() {
  await screen.findByLabelText('dumbbell');
  fireEvent.change(screen.getByLabelText('Training context'), { target: { value: 'current' } });
  fireEvent.change(screen.getByLabelText('Exercise skill'), { target: { value: 'intermediate' } });
  fireEvent.click(screen.getByLabelText('dumbbell')); fireEvent.click(screen.getByLabelText('No movement restrictions'));
  fireEvent.change(screen.getByLabelText('IANA timezone'), { target: { value: 'UTC' } });
  dates.forEach((date, index) => fireEvent.change(screen.getByLabelText(`Workout date ${index + 1}`), { target: { value: date } }));
  expect(screen.getByRole('button', { name: 'Generate preview' })).toBeEnabled();
}
const posts = () => calls.filter(call => call.method === 'POST');
const inventory: InventoryDocument = { version: 'customized-location-profile-v1', revision: 7, profile: { location_id: 'synthetic-gym', location_name: 'Private old-account gym', equipment: ['dumbbell'], unavailable_variants: [], setups: [], assignments: {}, strength_reports: [] } };

test('a late action after unmount cannot add its proposal to another route URL', async () => {
  const pending = deferred(); install(call => call.method === 'POST' ? pending.promise : undefined);
  const page = render(<CustomizedPage />); await fillDraft();
  fireEvent.click(screen.getByRole('button', { name: 'Generate preview' }));
  await waitFor(() => expect(posts()).toHaveLength(1));
  page.unmount(); window.history.replaceState(null, '', '/week?view=next#schedule');
  await act(async () => pending.resolve(Response.json(proposal)));
  expect(`${window.location.pathname}${window.location.search}${window.location.hash}`).toBe('/week?view=next#schedule');
});

test('a changed localStorage account cannot submit the previous draft before a shell remount', async () => {
  install(); render(<CustomizedPage />); await fillDraft();
  localStorage.setItem('hypertrophy_token', 'synthetic-account-b');
  fireEvent.click(screen.getByRole('button', { name: 'Generate preview' }));
  await act(async () => {});
  expect(posts()).toHaveLength(0);
  expect(screen.getByLabelText('Training context')).toHaveValue('unknown');
});

test('an account change during a pending action cannot restore the old proposal or draft', async () => {
  const pending = deferred(); install(call => call.method === 'POST' ? pending.promise : undefined);
  render(<CustomizedPage />); await fillDraft(); fireEvent.click(screen.getByRole('button', { name: 'Generate preview' }));
  await waitFor(() => expect(posts()).toHaveLength(1));
  localStorage.setItem('hypertrophy_token', 'synthetic-account-b');
  await act(async () => pending.resolve(Response.json(proposal)));
  expect(screen.queryByText('Private old-account program')).not.toBeInTheDocument();
  expect(screen.getByLabelText('Training context')).toHaveValue('unknown');
  expect(window.location.search).toBe(''); expect(posts()).toHaveLength(1);
});

test('late initial proposal hydration is bound to the account that requested it', async () => {
  const pending = deferred(); window.history.replaceState(null, '', '/customize?proposal=old-account-proposal');
  install(call => call.path.endsWith('/proposals/old-account-proposal') ? pending.promise : undefined);
  render(<CustomizedPage />); await screen.findByLabelText('dumbbell');
  localStorage.setItem('hypertrophy_token', 'synthetic-account-b');
  await act(async () => pending.resolve(Response.json(proposal)));
  expect(screen.queryByText('Private old-account program')).not.toBeInTheDocument();
  expect(window.location.search).toBe('');
});

test('a conflict refresh cannot hydrate the prior proposal after an account change', async () => {
  const pending = deferred(); let reads = 0;
  window.history.replaceState(null, '', '/customize?proposal=old-account-proposal');
  install(call => {
    if (call.method === 'POST') return Promise.resolve(Response.json({ detail: 'stale_revision' }, { status: 409 }));
    if (call.path.endsWith('/proposals/old-account-proposal') && ++reads > 1) return pending.promise;
  });
  render(<CustomizedPage />); await screen.findByText('Private old-account program');
  fireEvent.click(screen.getByRole('button', { name: 'Review acceptance' }));
  await waitFor(() => expect(reads).toBe(2));
  localStorage.setItem('hypertrophy_token', 'synthetic-account-b');
  await act(async () => pending.resolve(Response.json({ ...proposal, revision: 2 })));
  expect(screen.queryByText('Private old-account program')).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Accept program' })).not.toBeInTheDocument();
  expect(window.location.search).toBe('');
});

test('a same-account retry after a lost reply keeps the exact content and idempotency key', async () => {
  let attempts = 0;
  install(call => call.method === 'POST' && ++attempts === 1 ? Promise.reject(new TypeError('Synthetic lost reply')) : undefined);
  render(<CustomizedPage />); await fillDraft();
  fireEvent.click(screen.getByRole('button', { name: 'Generate preview' }));
  await screen.findByText('Synthetic lost reply');
  fireEvent.click(screen.getByRole('button', { name: 'Generate preview' }));
  await screen.findByText('Private old-account program');
  const writes = posts(); expect(writes).toHaveLength(2);
  expect(writes[1].body).toBe(writes[0].body);
  expect(writes[1].headers.get('Idempotency-Key')).toBe(writes[0].headers.get('Idempotency-Key'));
  expect(writes.every(call => call.headers.get('Authorization') === 'Bearer synthetic-account-a')).toBe(true);
  expect(screen.queryByRole('button', { name: 'Activate selected dates' })).not.toBeInTheDocument();
});

test('a declined replacement does not read the prior plan after leaving its account', async () => {
  const candidate = { ...proposal, snapshot: { ...proposal.snapshot, replacement: { proposal_id: 'original', kind: 'same_week_unstarted', sessions: [], preserved_work: [] } } };
  const pending = deferred(); window.history.replaceState(null, '', '/customize?proposal=old-account-proposal');
  install(call => call.method === 'POST' ? pending.promise : call.path.endsWith('/proposals/old-account-proposal') ? Promise.resolve(Response.json(candidate)) : undefined);
  const page = render(<CustomizedPage />); await screen.findByText('Private old-account program');
  fireEvent.click(screen.getByRole('button', { name: 'Decline' })); await waitFor(() => expect(posts()).toHaveLength(1));
  page.unmount(); localStorage.setItem('hypertrophy_token', 'synthetic-account-b');
  await act(async () => pending.resolve(Response.json({ ...candidate, state: 'declined' })));
  expect(calls.some(call => call.path.endsWith('/proposals/original'))).toBe(false);
});

test('inventory cannot submit an old document under a new localStorage account', async () => {
  install(); const onSaved = vi.fn();
  render(<CustomizedInventoryEditor document={inventory} equipment={['dumbbell']} variants={[]} onSaved={onSaved} />);
  fireEvent.click(screen.getByText('Equipment inventory and calibration'));
  localStorage.setItem('hypertrophy_token', 'synthetic-account-b');
  fireEvent.click(screen.getByRole('button', { name: 'Save inventory' }));
  await act(async () => {});
  expect(calls.filter(call => call.method === 'PUT')).toHaveLength(0);
  expect(onSaved).not.toHaveBeenCalled();
  expect(screen.getByLabelText('Location name')).toHaveValue('');
  expect(screen.getByRole('button', { name: 'Save inventory' })).toBeDisabled();
});

test('inventory ignores an old account save reply while preserving the original revision request', async () => {
  const pending = deferred(); install(call => call.method === 'PUT' ? pending.promise : undefined);
  const onSaved = vi.fn();
  render(<CustomizedInventoryEditor document={inventory} equipment={['dumbbell']} variants={[]} onSaved={onSaved} />);
  fireEvent.click(screen.getByText('Equipment inventory and calibration'));
  fireEvent.click(screen.getByRole('button', { name: 'Save inventory' }));
  await waitFor(() => expect(calls.filter(call => call.method === 'PUT')).toHaveLength(1));
  localStorage.setItem('hypertrophy_token', 'synthetic-account-b');
  await act(async () => pending.resolve(Response.json({ ...inventory, revision: 8 })));
  expect(onSaved).not.toHaveBeenCalled();
  expect(screen.getByLabelText('Location name')).toHaveValue('');
  const command = calls.find(call => call.method === 'PUT')!;
  expect(JSON.parse(command.body!)).toMatchObject({ expected_revision: 7, profile: inventory.profile });
  expect(command.headers.get('Authorization')).toBe('Bearer synthetic-account-a');
});

test('inventory cannot call its owner after unmount', async () => {
  const pending = deferred(); install(call => call.method === 'PUT' ? pending.promise : undefined);
  const onSaved = vi.fn();
  const page = render(<CustomizedInventoryEditor document={inventory} equipment={['dumbbell']} variants={[]} onSaved={onSaved} />);
  fireEvent.click(screen.getByText('Equipment inventory and calibration'));
  fireEvent.click(screen.getByRole('button', { name: 'Save inventory' }));
  await waitFor(() => expect(calls.filter(call => call.method === 'PUT')).toHaveLength(1));
  page.unmount(); await act(async () => pending.resolve(Response.json({ ...inventory, revision: 8 })));
  expect(onSaved).not.toHaveBeenCalled();
});
