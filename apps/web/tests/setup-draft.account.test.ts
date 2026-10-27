import { beforeEach, expect, test } from 'vitest';
import { setAuthToken } from '@/lib/api';
import { DRAFT_KEY, emptyAnswers, readCachedDraft, writeCachedDraft } from '@/app/onboarding/setup-draft';
const token = (sub: string) => `header.${btoa(JSON.stringify({ sub }))}.signature`;
beforeEach(() => localStorage.clear());
test('draft reload is bound to account identity across login tokens and private data is absent', () => {
 setAuthToken(token('account-a')); expect(writeCachedDraft({ ...emptyAnswers, selectedProgramId: 'phase1', age: '32', weightValue: '180', birthday: '1994-01-01', equipmentTags: ['cable'] })).toBe(true);
 const draft = readCachedDraft(); expect(draft).toContain('cable');
 for (const field of ['age', 'weightValue', 'birthday', 'password', 'email']) expect(JSON.parse(draft!)).not.toHaveProperty(field);
 setAuthToken(`${token('account-a')}another-signature`); expect(readCachedDraft()).toBe(draft);
 setAuthToken(token('account-b')); expect(readCachedDraft()).toBeNull();
});
test('legacy unowned or expired guest choices cannot become a signed-in accounts answers', () => {
 localStorage.setItem(DRAFT_KEY, JSON.stringify({ equipmentTags: ['cable'] })); expect(readCachedDraft()).toContain('cable');
 setAuthToken(token('account-a')); expect(readCachedDraft()).toBeNull();
});
