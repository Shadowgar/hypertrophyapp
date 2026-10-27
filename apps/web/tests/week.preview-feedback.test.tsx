import React from 'react';
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import WeekPage from '@/app/week/page';

const programId = 'pure_bodybuilding_phase_2_full_body';
const dates = ['2026-10-26', '2026-10-27', '2026-10-28', '2026-10-29', '2026-10-30', '2026-10-31'];
let profile: Record<string, unknown>;
let context: Record<string, unknown>;
let previewResponse: (request: Record<string, unknown>) => Promise<Response>;
let contextResponse: () => Promise<Response>;
let writes: Array<{ path: string; body: Record<string, unknown> }>;

function responsePlan(request: Record<string, unknown>) {
  return { program_template_id: request.template_id ?? programId, week_start: request.week_start, sessions: [], schedule: {
    timezone: request.timezone, selected_dates: request.selected_dates, placement_revision: request.expected_placement_revision,
    preview_digest: 'b'.repeat(64), spacing: { warnings: [], gap_days: [] },
  } };
}
function controls() { return within(screen.getByRole('region', { name: 'Week scheduling' })); }
async function selectDates(count: number) {
  await screen.findByRole('checkbox', { name: 'Mon, Oct 26' });
  await waitFor(() => expect(controls().queryByText(/Loading your profile/)).not.toBeInTheDocument());
  for (const checkbox of screen.getAllByRole('checkbox').slice(0, count)) fireEvent.click(checkbox);
}
function preview() { fireEvent.click(controls().getByRole('button', { name: 'Preview selected dates' })); }

beforeEach(() => {
  localStorage.setItem('hypertrophy_token', 'week-feedback-account-a');
  profile = { selected_program_id: programId, program_selection_mode: 'manual', initial_setup_available: false };
  context = { week_start: dates[0], local_today: dates[0], timezone: 'UTC', placement_revision: 3, selected_dates: [], plan: null };
  writes = [];
  previewResponse = async request => Response.json(responsePlan(request));
  contextResponse = async () => Response.json(context);
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path.endsWith('/profile')) return Response.json(profile);
    if (path.includes('/plan/scheduling-context')) return contextResponse();
    if (path.endsWith('/plan/programs')) return Response.json([{ id: programId, name: 'Full Body Phase 2' }]);
    if (path.includes('/history/calendar')) return Response.json({ days: [] });
    if (init?.method === 'POST') {
      const body = JSON.parse(String(init.body)); writes.push({ path, body });
      return path.endsWith('/plan/selected-dates/preview') ? previewResponse(body) : Response.json({});
    }
    return Response.json({});
  }));
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

test.each([0, 1, 6])('%i dates explain why preview is unavailable beside the control', async count => {
  render(<WeekPage />); await selectDates(count);
  expect(controls().getByRole('button', { name: 'Preview selected dates' })).toBeDisabled();
  expect(controls().getByText(count < 2 ? `Select at least 2 dates to preview (${count} selected).` : 'Select no more than 5 dates to preview (6 selected).')).toBeVisible();
  expect(writes).toHaveLength(0);
});

test.each([2, 3, 5])('%i dates show successful read-only preview beside the controls', async count => {
  render(<WeekPage />); await selectDates(count); preview();
  expect(await controls().findByText(/Preview ready.*not activated/i)).toBeVisible();
  expect(controls().getByRole('button', { name: 'Activate selected dates' })).toBeEnabled();
  expect(writes).toEqual([{ path: expect.stringMatching(/\/selected-dates\/preview$/), body: {
    template_id: programId, week_start: dates[0], timezone: 'UTC', selected_dates: dates.slice(0, count), expected_placement_revision: 3,
  } }]);
});

test('blank account explains the missing saved profile and links Resume Setup', async () => {
  profile = { ...profile, initial_setup_available: true };
  render(<WeekPage />); await selectDates(2);
  expect(controls().getByRole('button', { name: 'Preview selected dates' })).toBeDisabled();
  expect(controls().getByText(/Finish saving your setup profile before previewing/)).toBeVisible();
  expect(controls().getByRole('link', { name: 'Resume Setup' })).toHaveAttribute('href', '/onboarding');
  expect(writes).toHaveLength(0);
});

test('missing manual program explains how to resume program selection', async () => {
  profile = { ...profile, selected_program_id: null };
  render(<WeekPage />); await selectDates(2);
  expect(controls().getByRole('button', { name: 'Preview selected dates' })).toBeDisabled();
  expect(controls().getByText(/Choose a program or Auto before previewing/)).toBeVisible();
  expect(controls().getByRole('link', { name: 'Resume Setup' })).toHaveAttribute('href', '/onboarding');
});

test('Auto remains an explicit null program request', async () => {
  profile = { ...profile, selected_program_id: null, program_selection_mode: 'auto' };
  render(<WeekPage />); await selectDates(2); preview();
  await controls().findByText(/Preview ready/);
  expect(writes[0].body.template_id).toBeNull();
});

test('Customized retains its separate preview and consent path', async () => {
  profile = { ...profile, selected_program_id: 'customized_full_body_v1' };
  render(<WeekPage />); await selectDates(2);
  expect(controls().getByRole('button', { name: 'Preview selected dates' })).toBeDisabled();
  expect(controls().getByText(/Customized dates require their separate preview and consent/)).toBeVisible();
  expect(controls().getByRole('link', { name: 'Open Customized planning' })).toHaveAttribute('href', '/customize');
  expect(writes).toHaveLength(0);
});

test('empty timezone explains its prerequisite beside preview', async () => {
  render(<WeekPage />); await selectDates(2);
  fireEvent.click(screen.getByRole('button', { name: 'Change scheduling timezone' }));
  fireEvent.change(screen.getByLabelText('Scheduling timezone'), { target: { value: '' } });
  expect(controls().getByRole('button', { name: 'Preview selected dates' })).toBeDisabled();
  expect(controls().getByText(/Enter a valid IANA scheduling timezone before previewing/)).toBeVisible();
});

test('missing scheduling context offers an in-place retry', async () => {
  contextResponse = async () => Response.json({ detail: 'Synthetic outage' }, { status: 503 });
  render(<WeekPage />);
  expect(await controls().findByText(/Scheduling context is unavailable.*Retry week loading/)).toBeVisible();
  contextResponse = async () => Response.json(context);
  fireEvent.click(controls().getByRole('button', { name: 'Retry week loading' }));
  await screen.findByRole('checkbox', { name: 'Mon, Oct 26' });
  expect(writes).toHaveLength(0);
});

test('slow preview immediately reports pending and survives harmless focus refresh', async () => {
  let release: (() => void) | undefined;
  previewResponse = request => new Promise(resolve => { release = () => resolve(Response.json(responsePlan(request))); });
  render(<WeekPage />); await selectDates(3); preview();
  expect(controls().getByText(/Checking your selected dates.*No schedule has been activated/)).toBeVisible();
  await waitFor(() => expect(release).toBeDefined());
  fireEvent(window, new Event('focus'));
  await act(async () => { await Promise.resolve(); });
  expect(screen.getAllByRole('checkbox').filter(el => (el as HTMLInputElement).checked)).toHaveLength(3);
  await act(async () => { release!(); });
  expect(await controls().findByText(/Preview ready/)).toBeVisible();
  expect(writes).toHaveLength(1);
});

test('a preview context read superseded by focus is visibly recoverable', async () => {
  render(<WeekPage />); await selectDates(2);
  let release: ((value: Response) => void) | undefined;
  contextResponse = () => new Promise(resolve => { release = resolve; });
  preview(); await waitFor(() => expect(release).toBeDefined());
  const releaseFirst = release!;
  contextResponse = async () => Response.json(context);
  fireEvent(window, new Event('focus'));
  await act(async () => { releaseFirst(Response.json(context)); });
  expect(await controls().findByText(/Scheduling context changed.*preview.*again/i)).toBeVisible();
  expect(controls().getByRole('button', { name: 'Retry preview' })).toBeEnabled();
});

test('API failure shows an actionable error and retry alongside controls', async () => {
  previewResponse = async () => Response.json({ detail: 'Synthetic preview outage' }, { status: 503 });
  render(<WeekPage />); await selectDates(2); preview();
  expect(await controls().findByText(/Failed to preview selected dates.*Synthetic preview outage/)).toBeVisible();
  previewResponse = async request => Response.json(responsePlan(request));
  fireEvent.click(controls().getByRole('button', { name: 'Retry preview' }));
  expect(await controls().findByText(/Preview ready/)).toBeVisible();
  expect(writes).toHaveLength(2);
  expect(writes.every(write => write.path.endsWith('/selected-dates/preview'))).toBe(true);
});

test('late preview cannot overwrite a revised placement and explains invalidation', async () => {
  let release: (() => void) | undefined;
  previewResponse = request => new Promise(resolve => { release = () => resolve(Response.json(responsePlan(request))); });
  render(<WeekPage />); await selectDates(2); preview();
  await waitFor(() => expect(release).toBeDefined());
  context = { ...context, placement_revision: 4, selected_dates: dates.slice(2, 4) };
  fireEvent(window, new Event('focus'));
  await waitFor(() => expect(screen.getByRole('checkbox', { name: 'Wed, Oct 28' })).toBeChecked());
  await act(async () => { release!(); });
  expect(controls().getByText(/local week or placement changed/)).toBeVisible();
  expect(controls().queryByRole('button', { name: 'Activate selected dates' })).not.toBeInTheDocument();
});

test('late retired-account preview discards its program preference and explains account change', async () => {
  let release: (() => void) | undefined;
  previewResponse = request => new Promise(resolve => { release = () => resolve(Response.json(responsePlan(request))); });
  render(<WeekPage />); await selectDates(2); preview();
  await waitFor(() => expect(release).toBeDefined());
  localStorage.setItem('hypertrophy_token', 'week-feedback-account-b');
  await act(async () => { release!(); });
  expect(controls().getByText(/Account changed.*Reload Week/)).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: /Program Override/ }));
  expect(screen.getByRole('combobox', { name: 'Week program override selector' })).toHaveValue('');
  expect(controls().queryByRole('button', { name: 'Activate selected dates' })).not.toBeInTheDocument();
});

test('editing dates clears the success claim and requires a new preview', async () => {
  render(<WeekPage />); await selectDates(2); preview();
  await controls().findByText(/Preview ready/);
  fireEvent.click(screen.getByRole('checkbox', { name: 'Wed, Oct 28' }));
  expect(controls().queryByText(/Preview ready/)).not.toBeInTheDocument();
  expect(controls().getByText(/Your dates changed.*Preview.*again/)).toBeVisible();
  expect(controls().queryByRole('button', { name: 'Activate selected dates' })).not.toBeInTheDocument();
  expect(writes).toHaveLength(1);
});

test('changed saved program discards a delayed preview despite unchanged placement revision', async () => {
  let release: (() => void) | undefined;
  previewResponse = request => new Promise(resolve => { release = () => resolve(Response.json(responsePlan(request))); });
  render(<WeekPage />); await selectDates(2); preview();
  await waitFor(() => expect(release).toBeDefined());
  context = { ...context, plan: { week_start: dates[0], program_template_id: 'pure_bodybuilding_phase_1_full_body', sessions: [] } };
  fireEvent(window, new Event('focus'));
  await waitFor(() => expect(screen.getByRole('checkbox', { name: 'Mon, Oct 26' })).not.toBeChecked());
  await act(async () => { release!(); });
  expect(controls().getByText(/local week or placement changed/)).toBeVisible();
  expect(controls().queryByRole('button', { name: 'Activate selected dates' })).not.toBeInTheDocument();
});
