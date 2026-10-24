import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { beforeEach, test, expect, vi } from 'vitest';
import OnboardingPage from '@/app/onboarding/page';
const push = vi.hoisted(() => vi.fn());
vi.mock('next/navigation', () => ({useRouter: () => ({push, replace: vi.fn()})}));
beforeEach(() => { localStorage.clear(); push.mockReset(); });
test('existing-account login never writes profile, program, plan or check-in', async () => {
  const calls: string[] = [];
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    calls.push(`${init?.method ?? 'GET'} ${url}`);
    return new Response(JSON.stringify(url.endsWith('/auth/login') ? {access_token:'synthetic-token'} : url.endsWith('/plan/programs') ? [] : {}), {status:200});
  }));
  render(<OnboardingPage/>);
  fireEvent.click(await screen.findByRole('button', {name:/already have an account/i}));
  fireEvent.click(screen.getByRole('button',{name:/log in and continue/i}));
  await waitFor(() => expect(push).toHaveBeenCalledWith('/today'));
  expect(calls.filter(c => c.startsWith('POST'))).toEqual([expect.stringMatching(/POST .*\/auth\/login$/)]);
});
