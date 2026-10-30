import { fireEvent, screen, waitFor } from '@testing-library/react';
import { expect, test, vi } from 'vitest';
import { createAccount, installSetupApi, phase1, renderSetup, reviewSetup, type Call } from './helpers/onboarding-driver';
const {push}=vi.hoisted(()=>({push:vi.fn()}));
vi.mock('next/navigation',()=>({useRouter:()=>({push})}));

test('explicit Flexible intake saves optional expectation without weekday or hidden legacy count',async()=>{
  const calls:Call[]=[];installSetupApi(calls);renderSetup();await createAccount();
  fireEvent.click(screen.getByRole('button',{name:/Follow an Authored program/}));
  fireEvent.click(await screen.findByRole('button',{name:/^Full Body Phase 1/}));
  fireEvent.click(screen.getByRole('radio',{name:/Flexible/}));
  fireEvent.click(screen.getByRole('button',{name:'Use Full Body Phase 1'}));
  fireEvent.change(screen.getByLabelText('Age'),{target:{value:'34'}});
  fireEvent.change(screen.getByLabelText(/Body weight \(/),{target:{value:'180'}});
  expect(screen.queryByLabelText('Training days per week')).not.toBeInTheDocument();
  expect(screen.getByLabelText('Expected sessions per week (optional)')).toHaveValue('');
  await reviewSetup();
  fireEvent.click(screen.getByRole('button',{name:'Save setup & review Flexible'}));
  await waitFor(()=>expect(push).toHaveBeenCalledWith('/training/setup'));
  const saved=calls.find(call=>call.url.endsWith('/profile/initial-setup'));
  expect(saved?.payload).toMatchObject({schedule_mode:'flexible',expected_sessions_per_week:null,days_available:null,selected_program_id:phase1});
  expect(calls.some(call=>call.url.endsWith('/plan/generate-week'))).toBe(false);
});
