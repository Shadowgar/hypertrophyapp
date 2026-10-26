import React from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import OnboardingPage from '@/app/onboarding/page';
import { AppShell } from '@/components/app-shell';
import { clearAuthToken, setAuthToken } from '@/lib/api';
const push = vi.hoisted(() => vi.fn());
vi.mock('next/navigation', () => ({ usePathname: () => '/onboarding', useRouter: () => ({ push, replace: vi.fn() }) }));
const token = (sub: string) => `synthetic.${btoa(JSON.stringify({sub}))}.signature`;
function deferred<T>() { let resolve!: (value: T) => void; return { promise: new Promise<T>(done => { resolve = done; }), resolve }; }
beforeEach(() => { localStorage.clear(); push.mockReset(); });

test.each(['saved', 'failed'])("the real shell retains the registering account's %s profile result", async outcome => {
  const profile = deferred<Response>();
  localStorage.setItem('hypertrophy_onboarding_draft_v1', JSON.stringify({ phase: 'account', authMode: 'register', email: 'synthetic-shell@example.com', firstName: 'Synthetic' }));
  vi.stubGlobal('fetch', vi.fn(async input => {
    const url = String(input);
    if (url.endsWith('/plan/programs')) return Response.json([]);
    if (url.endsWith('/auth/register')) return Response.json({ access_token: token('registered-account') });
    if (url.endsWith('/profile/initial-setup')) return profile.promise;
    return Response.json({});
  }));
  render(<AppShell><OnboardingPage /></AppShell>);
  fireEvent.change(await screen.findByLabelText('Password'), { target: { value: 'Synthetic-only-Q98z!' } });
  fireEvent.click(screen.getByRole('button', { name: 'Continue' }));
  await screen.findByRole('button', { name: 'Sign out' });
  await act(async () => profile.resolve(outcome === 'saved' ? Response.json({}) : Response.json({ detail: 'Synthetic failure' }, { status: 503 })));
  if (outcome === 'saved') await waitFor(() => expect(push).toHaveBeenCalledWith('/week'));
  else {
    expect(push).not.toHaveBeenCalled();
    expect(await screen.findByRole('alert')).toHaveTextContent('Profile save failed: Synthetic failure');
  }
});

test('a different account resets private setup inputs and the old draft inside the stable shell', async () => {
  setAuthToken(token('first-account'));
  localStorage.setItem('hypertrophy_onboarding_draft_v1', JSON.stringify({ phase: 'account', authMode: 'register', email: 'first-synthetic@example.com', firstName: 'Private previous name' }));
  vi.stubGlobal('fetch', vi.fn(async () => Response.json([])));
  render(<AppShell><OnboardingPage /></AppShell>);
  expect(await screen.findByLabelText('Email address')).toHaveValue('first-synthetic@example.com');
  act(() => setAuthToken(token('other-account')));
  await screen.findByText(/Account changed/);
  expect(screen.queryByDisplayValue('first-synthetic@example.com')).not.toBeInTheDocument();
  expect(localStorage.getItem('hypertrophy_onboarding_draft_v1')).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: /already have an account/i }));
  expect(screen.getByLabelText('Email address')).toHaveValue('');
  expect(push).not.toHaveBeenCalled();
});


test.each(['logout', 'storage-switch'])("%s during registration retires the old save without retaining private form state", async action => {
  const profile = deferred<Response>();
  const writes: string[] = [];
  localStorage.setItem('hypertrophy_onboarding_draft_v1', JSON.stringify({ phase: 'account', authMode: 'register', email: 'pending-synthetic@example.com', firstName: 'Synthetic' }));
  vi.stubGlobal('fetch', vi.fn(async (input, init) => {
    const url = String(input);
    if (url.endsWith('/plan/programs')) return Response.json([]);
    if (url.endsWith('/auth/register')) return Response.json({ access_token: token('registering-account') });
    if (url.endsWith('/profile/initial-setup')) {
      writes.push(new Headers(init?.headers).get('Authorization') || '');
      return profile.promise;
    }
    return Response.json({});
  }));
  render(<AppShell><OnboardingPage /></AppShell>);
  fireEvent.change(await screen.findByLabelText('Password'), { target: { value: 'Synthetic-only-Q98z!' } });
  fireEvent.click(screen.getByRole('button', { name: 'Continue' }));
  await screen.findByRole('button', { name: 'Sign out' });
  act(() => {
    if (action === 'logout') clearAuthToken();
    else {
      localStorage.setItem('hypertrophy_token', token('other-account'));
      window.dispatchEvent(new StorageEvent('storage', { key: 'hypertrophy_token', newValue: token('other-account') }));
    }
  });
  await act(async () => profile.resolve(Response.json({})));
  expect(push).not.toHaveBeenCalled();
  expect(writes).toEqual([`Bearer ${token('registering-account')}`]);
  expect(localStorage.getItem('hypertrophy_onboarding_draft_v1')).toBeNull();
  expect(screen.queryByDisplayValue('pending-synthetic@example.com')).not.toBeInTheDocument();
  expect(screen.queryByDisplayValue('Synthetic-only-Q98z!')).not.toBeInTheDocument();
  expect(screen.getByText(/Account changed/)).toBeInTheDocument();
});
