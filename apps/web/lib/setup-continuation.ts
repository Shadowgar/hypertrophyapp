import type { Profile } from './api';
import { safeReturnPath } from './appearance';

/** Navigation only. Profile API owns eligibility and retained-history status. */
export function setupContinuation(profile: Profile, requested: string | null = null): string {
  if (profile.setup_status === 'initial' || profile.initial_setup_available === true) return '/onboarding';
  if (profile.setup_status === 'planning') return profile.selected_program_id === 'full_body_v1' ? '/customize' : '/week';
  const path = safeReturnPath(requested);
  return /^\/(login|onboarding|reset-password)([/?#]|$)/.test(path) ? '/today' : path;
}
