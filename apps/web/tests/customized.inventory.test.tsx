import React from 'react';
import {act, fireEvent, render, screen, waitFor, within} from '@testing-library/react';
import {beforeEach, expect, test, vi} from 'vitest';
import {CustomizedInventoryEditor} from '@/components/customized-inventory';
import {customizedApi} from '@/lib/api';
import type {InventoryDocument} from '@/lib/customized-inventory';

vi.mock('@/lib/api', () => ({customizedApi: {saveProfile: vi.fn()}, getToken: () => null}));
const variants = [
  {id: 'db_press', name: 'Dumbbell press', implement: 'dumbbell', basis: 'per_hand'},
  {id: 'machine_press', name: 'Machine press', implement: 'machine', basis: 'machine_stack'},
];
const empty: InventoryDocument = {version: 'inventory-v1', revision: 0, profile: null};
const stored: InventoryDocument = {version: 'inventory-v1', revision: 4, profile: {
  location_id: 'location-stable', location_name: 'Home gym', equipment: ['dumbbell'], unavailable_variants: [],
  setups: [{key: 'pair-stable', label: 'Adjustable pair', kind: 'dumbbell', unit: 'kg', weights: [{weight: 12.5, count: 2}], plates: [], bar_weight: null, stack: null, min_load: null, max_load: null, setup_note: 'Blue handles; full bench range'}],
  assignments: {db_press: 'pair-stable'}, strength_reports: [],
}};

beforeEach(() => vi.resetAllMocks());
function openEditor(document: InventoryDocument | null = empty, onSaved = vi.fn()) {
  const view = render(<CustomizedInventoryEditor document={document} equipment={['dumbbell', 'bench']} variants={variants} onSaved={onSaved}/>);
  fireEvent.click(screen.getByText('Equipment inventory and calibration'));
  return {...view, onSaved};
}
function change(label: string, value: string) {fireEvent.change(screen.getByLabelText(label), {target: {value}});}
function addDumbbells() {
  fireEvent.click(screen.getByRole('button', {name: 'Add equipment setup'}));
  change('Setup 1 name', 'Adjustable pair');
  change('Setup 1 kind', 'dumbbell');
  change('Setup 1 unit', 'kg');
  change('Setup 1 identity and range notes', 'Blue handles; full bench range');
  fireEvent.click(screen.getByRole('button', {name: 'Add weight to setup 1'}));
  change('Setup 1 weight 1', '12.5');
  change('Setup 1 count 1', '2');
}

test('does not seed equipment weights or allow saving before the account document loads', () => {
  openEditor(null);
  expect(screen.queryByRole('spinbutton')).not.toBeInTheDocument();
  expect(screen.getByRole('button', {name: 'Save inventory'})).toBeDisabled();
});

test('saves only actual declared inventory and explicit compatible assignments', async () => {
  const saved = {...stored, revision: 5};
  vi.mocked(customizedApi.saveProfile).mockResolvedValue(saved);
  const {onSaved} = openEditor();
  change('Location name', 'Home gym');
  addDumbbells();
  expect(screen.getByLabelText('Setup 1 minimum usable load')).toHaveValue(null);
  expect(screen.getByLabelText('Setup 1 maximum usable load')).toHaveValue(null);
  const assignment = screen.getByLabelText('Equipment setup for Dumbbell press');
  fireEvent.change(assignment, {target: {value: within(assignment).getByRole('option', {name: 'Adjustable pair'}).getAttribute('value')}});
  expect(within(screen.getByLabelText('Equipment setup for Machine press')).queryByRole('option', {name: 'Adjustable pair'})).not.toBeInTheDocument();
  fireEvent.click(screen.getByLabelText('Unavailable: Machine press'));
  fireEvent.click(screen.getByRole('button', {name: 'Save inventory'}));
  await waitFor(() => expect(onSaved).toHaveBeenCalledWith(saved));
  const [revision, profile] = vi.mocked(customizedApi.saveProfile).mock.calls[0];
  expect(revision).toBe(0);
  expect(profile).toMatchObject({location_name: 'Home gym', equipment: ['dumbbell', 'bench'], unavailable_variants: ['machine_press'], strength_reports: []});
  expect(profile.location_id).toBeTruthy();
  expect(profile.setups).toEqual([{key: expect.any(String), label: 'Adjustable pair', kind: 'dumbbell', unit: 'kg', weights: [{weight: 12.5, count: 2}], plates: [], bar_weight: null, stack: null, min_load: null, max_load: null, setup_note: 'Blue handles; full bench range'}]);
  expect(profile.assignments).toEqual({db_press: profile.setups[0].key});
});

test('optional historical reports require date, confirmation and an e1RM method without prescribing a load', async () => {
  vi.mocked(customizedApi.saveProfile).mockResolvedValue({...stored, revision: 5});
  openEditor(stored);
  fireEvent.click(screen.getByRole('button', {name: 'Add historical strength report'}));
  change('Report 1 exercise', 'db_press');
  change('Report 1 kind', 'e1rm');
  change('Report 1 load', '25');
  change('Report 1 observed date', '2026-10-01');
  fireEvent.click(screen.getByLabelText('Report 1 confirmed historical observation'));
  fireEvent.click(screen.getByRole('button', {name: 'Save inventory'}));
  expect(customizedApi.saveProfile).not.toHaveBeenCalled();
  expect(screen.getByRole('alert')).toHaveTextContent(/method/i);
  change('Report 1 estimation method or reference', 'Recorded estimate from prior training log');
  fireEvent.click(screen.getByRole('button', {name: 'Save inventory'}));
  await waitFor(() => expect(customizedApi.saveProfile).toHaveBeenCalledOnce());
  const profile = vi.mocked(customizedApi.saveProfile).mock.calls[0][1];
  expect(profile.strength_reports).toEqual([{report_id: expect.any(String), variant_id: 'db_press', setup_key: 'pair-stable', kind: 'e1rm', load: 25, unit: 'kg', observed_on: '2026-10-01', confirmed: true, method_reference: 'Recorded estimate from prior training log'}]);
  expect(screen.getByText(/Historical information only/i)).toBeInTheDocument();
  expect(screen.queryByText(/recommended working load/i)).not.toBeInTheDocument();
});

test('refreshes loaded inventory identities and surfaces stale revisions without replacing the draft', async () => {
  vi.mocked(customizedApi.saveProfile).mockRejectedValue(new Error('Inventory revision changed; reload before saving.'));
  const {rerender, onSaved} = openEditor();
  rerender(<CustomizedInventoryEditor document={stored} equipment={['dumbbell']} variants={variants} onSaved={onSaved}/>);
  expect(screen.getByLabelText('Location name')).toHaveValue('Home gym');
  change('Location name', 'Updated home gym');
  fireEvent.click(screen.getByRole('button', {name: 'Save inventory'}));
  expect(await screen.findByRole('alert')).toHaveTextContent('Inventory revision changed');
  expect(screen.getByLabelText('Location name')).toHaveValue('Updated home gym');
  expect(vi.mocked(customizedApi.saveProfile).mock.calls[0][1]).toMatchObject({location_id: 'location-stable', assignments: {db_press: 'pair-stable'}});
  expect(onSaved).not.toHaveBeenCalled();
});

test('account change erases private inputs and rejects a delayed save response', async () => {
  let resolveSave!: (value: InventoryDocument) => void;
  vi.mocked(customizedApi.saveProfile).mockImplementation(() => new Promise(resolve => {resolveSave = resolve;}));
  const {onSaved} = openEditor(stored);
  fireEvent.click(screen.getByRole('button', {name: 'Save inventory'}));
  await waitFor(() => expect(customizedApi.saveProfile).toHaveBeenCalledOnce());
  await act(async () => {
    window.dispatchEvent(new Event('hypertrophy:auth-token-changed'));
    resolveSave({...stored, revision: 5});
  });
  expect(screen.getByLabelText('Location name')).toHaveValue('');
  expect(screen.queryByDisplayValue('Blue handles; full bench range')).not.toBeInTheDocument();
  expect(screen.getByRole('button', {name: 'Save inventory'})).toBeDisabled();
  expect(onSaved).not.toHaveBeenCalled();
});

test('setup edits cannot silently reinterpret a confirmed historical report', async () => {
  const withReport: InventoryDocument = {...stored, profile: {...stored.profile!, strength_reports: [{report_id: 'historical-stable', variant_id: 'db_press', setup_key: 'pair-stable', kind: '1rm', load: 25, unit: 'kg', observed_on: '2026-10-01', confirmed: true, method_reference: null, setup_fingerprint: 'server-bound-setup'}]}};
  openEditor(withReport);
  change('Setup 1 unit', 'lb');
  fireEvent.click(screen.getByRole('button', {name: 'Save inventory'}));
  expect(customizedApi.saveProfile).not.toHaveBeenCalled();
  expect(screen.getByRole('alert')).toHaveTextContent(/report/i);
});

test('new weight rows stay blank and reject fractional counts before saving', () => {
  openEditor();
  change('Location name', 'Home gym');
  fireEvent.click(screen.getByRole('button', {name: 'Add equipment setup'}));
  change('Setup 1 name', 'Pair'); change('Setup 1 kind', 'dumbbell'); change('Setup 1 unit', 'kg');
  change('Setup 1 identity and range notes', 'Exact setup');
  fireEvent.click(screen.getByRole('button', {name: 'Add weight to setup 1'}));
  expect(screen.getByLabelText('Setup 1 weight 1')).toHaveValue(null);
  expect(screen.getByLabelText('Setup 1 count 1')).toHaveValue(null);
  change('Setup 1 weight 1', '10'); change('Setup 1 count 1', '1.5');
  fireEvent.click(screen.getByRole('button', {name: 'Save inventory'}));
  expect(screen.getByRole('alert')).toHaveTextContent(/whole numbers/i);
  expect(customizedApi.saveProfile).not.toHaveBeenCalled();
});

test('a declared machine range replaces enumerated labels without inventing its bounds', async () => {
  vi.mocked(customizedApi.saveProfile).mockResolvedValue({...stored, revision: 5});
  openEditor(); change('Location name', 'Gym');
  fireEvent.click(screen.getByRole('button', {name: 'Add equipment setup'}));
  change('Setup 1 name', 'Chest machine'); change('Setup 1 kind', 'machine_stack'); change('Setup 1 unit', 'lb');
  change('Setup 1 identity and range notes', 'Machine A; handle 3; full range');
  fireEvent.click(screen.getByRole('button', {name: 'Add weight to setup 1'}));
  change('Setup 1 weight 1', '30'); change('Setup 1 count 1', '1');
  fireEvent.click(screen.getByLabelText('Setup 1 has a confirmed uniform stack range instead of individual labels'));
  expect(screen.queryByLabelText('Setup 1 weight 1')).not.toBeInTheDocument();
  for (const field of ['minimum', 'maximum', 'increment']) expect(screen.getByLabelText(`Setup 1 stack ${field}`)).toHaveValue(null);
  change('Setup 1 stack minimum', '30'); change('Setup 1 stack maximum', '150'); change('Setup 1 stack increment', '15');
  fireEvent.click(screen.getByRole('button', {name: 'Save inventory'}));
  await waitFor(() => expect(customizedApi.saveProfile).toHaveBeenCalledOnce());
  expect(vi.mocked(customizedApi.saveProfile).mock.calls[0][1].setups[0]).toMatchObject({kind: 'machine_stack', unit: 'lb', weights: [], stack: {minimum: 30, maximum: 150, increment: 15}});
});

test('barbell payload preserves the entered bar and total plate counts without assigning it to dumbbell exercises', async () => {
  vi.mocked(customizedApi.saveProfile).mockResolvedValue({...stored, revision: 5});
  openEditor(); change('Location name', 'Gym');
  fireEvent.click(screen.getByRole('button', {name: 'Add equipment setup'}));
  change('Setup 1 name', 'Rack A'); change('Setup 1 kind', 'barbell'); change('Setup 1 unit', 'kg');
  change('Setup 1 identity and range notes', 'Bar A; rack position 3');
  expect(screen.getByLabelText('Setup 1 bar weight')).toHaveValue(null);
  change('Setup 1 bar weight', '15');
  fireEvent.click(screen.getByRole('button', {name: 'Add plate to setup 1'}));
  change('Setup 1 plate 1', '2.5'); change('Setup 1 count 1', '4');
  expect(within(screen.getByLabelText('Equipment setup for Dumbbell press')).queryByRole('option', {name: 'Rack A'})).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', {name: 'Save inventory'}));
  await waitFor(() => expect(customizedApi.saveProfile).toHaveBeenCalledOnce());
  expect(vi.mocked(customizedApi.saveProfile).mock.calls[0][1].setups[0]).toMatchObject({kind: 'barbell', bar_weight: 15, plates: [{weight: 2.5, count: 4}], weights: [], stack: null});
});

test('editing a saved report keeps its server-owned setup fingerprint and stable identifiers', async () => {
  const withReport: InventoryDocument = {...stored, profile: {...stored.profile!, strength_reports: [{report_id: 'report-stable', variant_id: 'db_press', setup_key: 'pair-stable', kind: '1rm', load: 25, unit: 'kg', observed_on: '2026-10-01', confirmed: true, method_reference: null, setup_fingerprint: 'server-bound-setup'}]}};
  vi.mocked(customizedApi.saveProfile).mockResolvedValue({...withReport, revision: 5});
  openEditor(withReport);
  change('Setup 1 weight 1', '15'); // Inventory availability is distinct from setup identity.
  fireEvent.click(screen.getByRole('button', {name: 'Save inventory'}));
  await waitFor(() => expect(customizedApi.saveProfile).toHaveBeenCalledOnce());
  expect(vi.mocked(customizedApi.saveProfile).mock.calls[0][1].strength_reports[0]).toEqual({report_id: 'report-stable', variant_id: 'db_press', setup_key: 'pair-stable', kind: '1rm', load: 25, unit: 'kg', observed_on: '2026-10-01', confirmed: true, method_reference: null, setup_fingerprint: 'server-bound-setup'});
});

test('zero maximum usable load is rejected while an explicit zero minimum remains valid', () => {
  openEditor(stored);
  change('Setup 1 minimum usable load', '0'); change('Setup 1 maximum usable load', '0');
  fireEvent.click(screen.getByRole('button', {name: 'Save inventory'}));
  expect(customizedApi.saveProfile).not.toHaveBeenCalled();
  expect(screen.getByRole('alert')).toHaveTextContent(/maximum usable load/i);
});


test('historical report units remain explicit and independent of the setup labels', async () => {
  const withReport: InventoryDocument = {...stored, profile: {...stored.profile!, strength_reports: [{report_id: 'historical-lb', variant_id: 'db_press', setup_key: 'pair-stable', kind: '1rm', load: 55, unit: 'lb', observed_on: '2026-10-01', confirmed: true, method_reference: null, setup_fingerprint: 'server-owned'}]}};
  vi.mocked(customizedApi.saveProfile).mockResolvedValue({...withReport, revision: 5});
  openEditor(withReport);
  expect(screen.getByLabelText('Report 1 unit')).toHaveValue('lb');
  fireEvent.click(screen.getByRole('button', {name: 'Save inventory'}));
  await waitFor(() => expect(customizedApi.saveProfile).toHaveBeenCalledOnce());
  const profile = vi.mocked(customizedApi.saveProfile).mock.calls[0][1];
  expect(profile.setups[0].unit).toBe('kg');
  expect(profile.strength_reports[0]).toMatchObject({unit: 'lb', load: 55, setup_fingerprint: 'server-owned'});
});
