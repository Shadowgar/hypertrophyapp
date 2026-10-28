import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { setAuthToken } from '@/lib/api';
import { DRAFT_KEY, emptyAnswers, readCachedDraft, writeCachedDraft } from '@/app/onboarding/setup-draft';
const token = (sub: string) => `header.${btoa(JSON.stringify({ sub }))}.signature`;
beforeEach(() => localStorage.clear());
afterEach(() => vi.restoreAllMocks());
test('draft reload is bound to account identity across login tokens and private data is absent', () => {
 setAuthToken(token('account-a')); expect(writeCachedDraft({ ...emptyAnswers, selectedProgramId: 'phase1', age: '32', weightValue: '180', birthday: '1994-01-01', equipmentTags: ['cable'] })).toBe(true);
 const draft = readCachedDraft(); expect(draft).toContain('cable');
 for (const field of ['age', 'weightValue', 'birthday', 'password', 'email']) expect(JSON.parse(draft!)).not.toHaveProperty(field);
 setAuthToken(`${token('account-a')}another-signature`); expect(readCachedDraft()).toBe(draft);
 setAuthToken(token('account-b')); expect(readCachedDraft()).toBeNull();
});
test('legacy unowned or expired guest choices cannot become a signed-in accounts answers', () => {
 localStorage.setItem(DRAFT_KEY, JSON.stringify({ equipmentTags: ['cable'] })); expect(readCachedDraft()).toBeNull();
 setAuthToken(token('account-a')); expect(readCachedDraft()).toBeNull();
});

test('failed replacement never relabels another account draft', () => {
 const a = token('account-a'), b = token('account-b');
 setAuthToken(a); writeCachedDraft({ ...emptyAnswers, equipmentTags: ['cable'] });
 setAuthToken(b);
 const set = Storage.prototype.setItem;
 vi.spyOn(Storage.prototype, 'setItem').mockImplementation(function (this: Storage, key, value) {
  if (key === DRAFT_KEY) throw new DOMException('Full storage', 'QuotaExceededError');
  return set.call(this, key, value);
 });
 expect(writeCachedDraft({ ...emptyAnswers, equipmentTags: ['dumbbell'] })).toBe(false);
 expect(readCachedDraft()).toBeNull();
 setAuthToken(a); expect(readCachedDraft()).toContain('cable');
});
test('a concurrent writer cannot tear owner and answers during recovery', () => {
 const a = token('account-a'), b = token('account-b');
 setAuthToken(a); writeCachedDraft({ ...emptyAnswers, equipmentTags: ['cable'] });
 const get = Storage.prototype.getItem;
 vi.spyOn(Storage.prototype, 'getItem').mockImplementation(function (this: Storage, key) {
  const value = get.call(this, key);
  if (key === `${DRAFT_KEY}.owner`) {
   setAuthToken(b); writeCachedDraft({ ...emptyAnswers, equipmentTags: ['dumbbell'] }); setAuthToken(a);
  }
  return value;
 });
 expect(readCachedDraft()).not.toContain('dumbbell');
});
test('ambiguous legacy split-owner entries are not accepted as saved account answers', () => {
 setAuthToken(token('account-b'));
 localStorage.setItem(DRAFT_KEY, JSON.stringify({ equipmentTags: ['cable'] }));
 localStorage.setItem(`${DRAFT_KEY}.owner`, 'account-b');
 expect(readCachedDraft()).toBeNull();
});
test('a form cannot write its old answers after a cross-tab token change before notification', () => {
 const a = token('account-a'), b = token('account-b');
 setAuthToken(a);
 localStorage.setItem('hypertrophy_token', b);
 expect(writeCachedDraft({ ...emptyAnswers, equipmentTags: ['cable'] }, a)).toBe(false);
 expect(readCachedDraft()).toBeNull();
});
test('unidentifiable signed-in sessions cannot claim draft ownership', () => {
 localStorage.setItem('hypertrophy_token', 'invalid-token');
 expect(writeCachedDraft({ ...emptyAnswers, equipmentTags: ['cable'] })).toBe(false);
 expect(readCachedDraft()).toBeNull();
});

test('legacy owner deletion cannot turn authenticated answers into a guest draft', () => {
 localStorage.setItem(DRAFT_KEY, JSON.stringify({ equipmentTags: ['cable'] }));
 localStorage.setItem(`${DRAFT_KEY}.owner`, 'account-a');
 const get = Storage.prototype.getItem;
 vi.spyOn(Storage.prototype, 'getItem').mockImplementation(function (this: Storage, key) {
  const value = get.call(this, key);
  if (key === DRAFT_KEY) { localStorage.removeItem(DRAFT_KEY); localStorage.removeItem(`${DRAFT_KEY}.owner`); }
  return value;
 });
 expect(readCachedDraft()).toBeNull();
});

test('an atomic read retains its original owner when another tab replaces the whole draft', () => {
 const a = token('account-a'), b = token('account-b');
 setAuthToken(a); writeCachedDraft({ ...emptyAnswers, equipmentTags: ['cable'] });
 const get = Storage.prototype.getItem;
 vi.spyOn(Storage.prototype, 'getItem').mockImplementation(function (this: Storage, key) {
  const value = get.call(this, key);
  if (key === DRAFT_KEY) {
   setAuthToken(b); writeCachedDraft({ ...emptyAnswers, equipmentTags: ['dumbbell'] }); setAuthToken(a);
  }
  return value;
 });
 expect(readCachedDraft()).toContain('cable');
});
test('guest and an account named guest remain separate owners', () => {
 expect(writeCachedDraft({ ...emptyAnswers, equipmentTags: ['cable'] })).toBe(true);
 expect(readCachedDraft()).toContain('cable');
 setAuthToken(token('guest')); expect(readCachedDraft()).toBeNull();
});
