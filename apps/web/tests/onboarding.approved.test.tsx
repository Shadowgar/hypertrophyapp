import React from 'react';
import { act, fireEvent, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, test, vi } from 'vitest';
import { Call, chooseProgram, createAccount, fillBasics, initialPreferences, installSetupApi, phase1, renderSetup, reviewSetup } from './helpers/onboarding-driver';
const push = vi.hoisted(() => vi.fn());
vi.mock('next/navigation', () => ({ useRouter: () => ({ push, replace: vi.fn() }) }));
const calls: Call[] = [];
beforeEach(() => { localStorage.clear(); calls.length = 0; push.mockReset(); installSetupApi(calls); });

test('create account is authentication only; program choice precedes questions and explicit review precedes profile save', async () => {
  renderSetup(); await createAccount();
  expect(calls.filter(call => call.method === 'POST').map(call => call.url.split('/').at(-1))).toEqual(['register']);
  expect(screen.queryByLabelText('Age')).not.toBeInTheDocument();
  await chooseProgram();
  expect(screen.getByLabelText('Age')).toHaveValue(null);
  expect(screen.getByLabelText('Body weight (lb)')).toHaveValue(null);
  expect(screen.getByRole('button', { name: 'Continue to equipment' })).toBeDisabled();
  fillBasics(); await reviewSetup();
  expect(calls.some(call => call.url.endsWith('/profile/initial-setup'))).toBe(false);
  expect(screen.getByText('Authored · Full Body Phase 1')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Save setup & choose dates' }));
  await waitFor(() => expect(push).toHaveBeenCalledWith('/week'));
  const payload = calls.find(call => call.url.endsWith('/profile/initial-setup'))!.payload;
  expect(payload).toMatchObject({ age: 34, weight: 81.6466266, days_available: 3, selected_program_id: phase1 });
  expect(payload.training_location).toBeNull();
  expect(payload.equipment_profile).toEqual([]);
  expect(payload.session_time_budget_minutes).toBeNull();
  expect(payload.onboarding_answers).toMatchObject({ birthday: null, training_age_bucket: null, motivation_driver: null, strength_experience_level: null });
  expect(screen.getByRole('button', { name: 'Save setup & choose dates' })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Save setup & choose dates' }));
  expect(calls.filter(call => call.url.endsWith('/profile/initial-setup'))).toHaveLength(1);
  expect(localStorage.getItem('hypertrophy_onboarding_draft_v1')).toBeNull();
});

test('unit change converts entered body weight and saves the preference through its existing revision owner', async () => {
  renderSetup(); await createAccount(); await chooseProgram(); fillBasics();
  fireEvent.change(screen.getByLabelText('Weight display'), { target: { value: 'kg' } });
  expect(screen.getByLabelText('Body weight (kg)')).toHaveValue(81.6466266);
  await reviewSetup();
  fireEvent.click(screen.getByRole('button', { name: 'Save setup & choose dates' }));
  await waitFor(() => expect(push).toHaveBeenCalledWith('/week'));
  expect(calls.find(call => call.method === 'PUT')?.payload).toEqual({ theme_family: 'classic', appearance: 'dark', weight_unit: 'kg', expected_revision: 0 });
  expect(calls.find(call => call.url.endsWith('/profile/initial-setup'))?.payload.weight).toBe(81.6466266);
});

test('equipment selections and optional limitations survive editing and review without invented loads or a plan', async () => {
  renderSetup(); await createAccount(); await chooseProgram(); fillBasics();
  fireEvent.change(screen.getByLabelText('Training location'), { target: { value: 'gym' } });
  fireEvent.click(screen.getByRole('button', { name: 'Continue to equipment' }));
  expect(screen.getByRole('checkbox', { name: 'Dumbbells' })).not.toBeChecked();
  fireEvent.click(screen.getByRole('checkbox', { name: 'Dumbbells' }));
  fireEvent.click(screen.getByText('Movement limitations (optional)'));
  fireEvent.click(screen.getByRole('checkbox', { name: 'Overhead pressing limitations' }));
  fireEvent.click(screen.getByRole('button', { name: 'Review setup' }));
  fireEvent.click(screen.getByRole('button', { name: 'Edit setup' }));
  fireEvent.click(screen.getByRole('button', { name: 'Continue to equipment' }));
  expect(screen.getByRole('checkbox', { name: 'Dumbbells' })).toBeChecked();
  fireEvent.click(screen.getByRole('button', { name: 'Review setup' }));
  fireEvent.click(screen.getByRole('button', { name: 'Save setup & choose dates' }));
  await waitFor(() => expect(push).toHaveBeenCalledWith('/week'));
  const payload = calls.find(call => call.url.endsWith('/profile/initial-setup'))!.payload;
  expect(payload).toMatchObject({ equipment_profile: ['dumbbell'], movement_restrictions: ['overhead_pressing'], training_location: 'gym' });
  expect(calls.some(call => /generate|consent|activate|weekly-review/.test(call.url))).toBe(false);
});

test('a late saved-unit read converts an entered weight instead of reinterpreting its number', async () => {
  let resolve!: (value: Response) => void;
  const preferences = new Promise<Response>(done => { resolve = done; });
  installSetupApi(calls, call => call.url.endsWith('/profile/preferences') ? preferences : undefined);
  renderSetup(); await createAccount(); await chooseProgram(); fillBasics();
  await act(async () => resolve(Response.json({ ...initialPreferences, weight_unit: 'kg' })));
  expect(screen.getByLabelText('Body weight (kg)')).toHaveValue(81.6466266);
});
