import { act, fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { setAuthToken } from '@/lib/api';
import { DRAFT_KEY } from '@/app/onboarding/setup-draft';
import { Call, chooseProgram, createAccount, fillBasics, installSetupApi, renderSetup, reviewSetup } from './helpers/onboarding-driver';

const push = vi.hoisted(() => vi.fn());
vi.mock('next/navigation', () => ({ useRouter: () => ({ push, replace: vi.fn() }) }));
const calls: Call[] = [];
beforeEach(() => { localStorage.clear(); calls.length = 0; push.mockReset(); installSetupApi(calls); });
afterEach(() => { vi.restoreAllMocks(); });
const deny = () => { throw new DOMException('Synthetic draft cache unavailable', 'SecurityError'); };

test('denied optional draft reads allow setup without a browser cache', async () => {
  const get = Storage.prototype.getItem;
  vi.spyOn(Storage.prototype, 'getItem').mockImplementation(function (this: Storage, key) { return key === DRAFT_KEY ? deny() : get.call(this, key); });
  renderSetup();
  expect(await screen.findByText(/Browser draft storage is unavailable/)).toBeInTheDocument();
  await createAccount(); await chooseProgram(); fillBasics(); await reviewSetup();
  fireEvent.click(screen.getByRole('button', { name: 'Save setup & choose dates' }));
  await waitFor(() => expect(push).toHaveBeenCalledWith('/week'));
  expect(calls.filter(call => call.url.endsWith('/profile/initial-setup'))).toHaveLength(1);
});

test('quota failure in an optional draft write keeps the active answers and setup usable', async () => {
  const set = Storage.prototype.setItem;
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(function (this: Storage, key, value) {
    if (key === DRAFT_KEY) throw new DOMException('Synthetic quota exceeded', 'QuotaExceededError');
    set.call(this, key, value);
  });
  renderSetup(); await createAccount(); await chooseProgram(); fillBasics();
  expect(screen.getByLabelText('Body weight (lb)')).toHaveValue(180);
  expect(screen.getByText(/Browser draft storage is unavailable/)).toBeInTheDocument();
  await reviewSetup(); fireEvent.click(screen.getByRole('button', { name: 'Save setup & choose dates' }));
  await waitFor(() => expect(push).toHaveBeenCalledWith('/week'));
});

test('failed cache cleanup after acknowledged profile save remains confirmed and cannot submit again', async () => {
  renderSetup(); await createAccount(); await chooseProgram(); fillBasics(); await reviewSetup();
  const remove = Storage.prototype.removeItem;
  vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(function (this: Storage, key) { if (key === DRAFT_KEY) deny(); else remove.call(this, key); });
  fireEvent.click(screen.getByRole('button', { name: 'Save setup & choose dates' }));
  await waitFor(() => expect(push).toHaveBeenCalledWith('/week'));
  expect(screen.getByText(/Profile saved/)).toBeInTheDocument();
  expect(screen.queryByText(/Profile save failed/)).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Save setup & choose dates' })).toBeDisabled();
  expect(calls.filter(call => call.url.endsWith('/profile/initial-setup'))).toHaveLength(1);
});

test('failed cache cleanup cannot retain an old account form or apply its pending save reply', async () => {
  let resolve!: (response: Response) => void;
  const pending = new Promise<Response>(done => { resolve = done; });
  installSetupApi(calls, call => call.url.endsWith('/profile/initial-setup') ? pending : undefined);
  renderSetup(); await createAccount(); await chooseProgram(); fillBasics(); await reviewSetup();
  fireEvent.click(screen.getByRole('button', { name: 'Save setup & choose dates' }));
  await waitFor(() => expect(calls.some(call => call.url.endsWith('/profile/initial-setup'))).toBe(true));
  const remove = Storage.prototype.removeItem;
  vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(function (this: Storage, key) { if (key === DRAFT_KEY) deny(); else remove.call(this, key); });
  act(() => setAuthToken('other-synthetic-account'));
  await act(async () => resolve(Response.json({})));
  expect(screen.getByText(/Account changed/)).toBeInTheDocument();
  expect(screen.queryByText(/Recovered saved onboarding draft/)).not.toBeInTheDocument();
  expect(screen.queryByRole('heading', { name: 'Review your setup' })).not.toBeInTheDocument();
  expect(push).not.toHaveBeenCalled();
  expect(calls.filter(call => call.url.endsWith('/profile/initial-setup'))).toHaveLength(1);
});
