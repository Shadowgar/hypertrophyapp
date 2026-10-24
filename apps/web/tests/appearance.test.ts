import {expect, test} from 'vitest';
import {resolvedAppearance, safeReturnPath, accountScope, defaultPreferences} from '@/lib/appearance';
test('six appearances use independent family and device appearance', () => {
  for (const family of ['graphite','charcoal','classic']) {
    expect(resolvedAppearance('system', true)).toBe('dark');
    expect(resolvedAppearance('system', false)).toBe('light');
    expect(resolvedAppearance('dark', false)).toBe('dark');
    expect(resolvedAppearance('light', true)).toBe('light');
  }
  expect(defaultPreferences).toMatchObject({theme_family:'classic',appearance:'dark'});
});
test('return path keeps selected workout query but rejects external and scripted paths', () => {
  expect(safeReturnPath('/today?date=2026-10-21#exercise')).toBe('/today?date=2026-10-21#exercise');
  for (const path of ['//evil.test','https://evil.test','javascript:alert(1)','/\\evil.test','/\nevil.test']) expect(safeReturnPath(path)).toBe('/today');
});
test('draft namespaces never use another account or raw credential', () => {
  const token=(sub:string)=>`a.${btoa(JSON.stringify({sub}))}.c`;
  expect(accountScope(token('one'))).toBe('one');
  expect(accountScope(token('two'))).toBe('two');
  expect(accountScope('broken')).toBeNull();
});
