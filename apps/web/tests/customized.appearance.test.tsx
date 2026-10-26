import React from 'react';
import { render, screen } from '@testing-library/react';
import { beforeEach, expect, test, vi } from 'vitest';
import CustomizedPage from '@/app/customize/page';
const appearance = vi.hoisted(() => ({ weight_unit: 'lb' as 'lb' | 'kg' }));
vi.mock('@/components/appearance-provider', () => ({ useAppearance: () => ({ preferences: appearance }) }));
const dates = ['2026-10-26', '2026-10-28', '2026-10-30'];
const request = { mode: 'customized', training_context: 'current', skill: 'basic', restrictions: [], selected_dates: dates, equipment: ['dumbbell'], timezone: 'UTC', cap_minutes: 60 };
const plan = { proposal_id: 'synthetic-preview', revision: 1, plan_version: 1, state: 'active', snapshot: { request, preview: { candidate_name: 'Synthetic program', sessions: [{ local_date: dates[0], minimum_minutes: 30, maximum_minutes: 40, cap_status: 'within_estimated_cap', exercises: [{ variant_id: 'row', name: 'Synthetic row', sets: 3, reps_min: 8, reps_max: 12, target_min: 2, target_max: 3, target_scale: 'rir', load_basis: 'per_hand', working_load: 45.359237, load_unit: 'kg' }] }], missing_actions: [], dose_conflicts: [] } }, blocking_reasons: [], active_placement: { dates, timezone: 'UTC', placement_revision: 1, frozen_dates: [], sessions: [{ session_id: 'synthetic-session', date: dates[0], title: 'Synthetic session', exercises: [{ id: 'row', name: 'Synthetic row', sets: 3, rep_range: [8, 12], recommended_working_weight: 45.359237, customized: { target_kind: 'rir', target_min: 2, target_max: 3, rest_seconds: { low: 90, high: 120 }, identity: { unit: 'kg', basis: 'per_hand' } } }] }] } };
beforeEach(() => {
  window.history.replaceState(null, '', '/customize'); appearance.weight_unit = 'lb';
  vi.stubGlobal('fetch', vi.fn(async input => String(input).endsWith('/customized/options') ? Response.json({ equipment: [], restrictions: [] }) : Response.json({ plans: [plan] })));
});
test('active prescriptions and original preview follow units without modifying stored snapshots', async () => {
  const view = render(<CustomizedPage />);
  await screen.findByText(/Working load: 100 lb/);
  expect(screen.getByText(/Qualified recorded baseline: 100 lb/)).toBeInTheDocument();
  appearance.weight_unit = 'kg'; view.rerender(<CustomizedPage />);
  expect(screen.getByText(/Working load: 45.359237 kg/)).toBeInTheDocument();
  expect(screen.getByText(/Qualified recorded baseline: 45.359237 kg/)).toBeInTheDocument();
  expect(vi.mocked(fetch).mock.calls.every(([, init]) => !(init as RequestInit | undefined)?.method || (init as RequestInit).method === 'GET')).toBe(true);
});
