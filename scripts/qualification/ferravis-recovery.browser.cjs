// Uses only the version-checked disposable service; SMTP must be disabled there.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { chromium, webkit, devices } = require('playwright');
const base = 'http://127.0.0.1:55431';
const version = process.env.FERRAVIS_EXPECTED_VERSION;
const out = process.env.FERRAVIS_TEST_ARTIFACTS;
assert.match(version || '', /^[a-f0-9]{40}$/);
assert.ok(out);
fs.mkdirSync(out, { recursive: true });
(async () => {
 for (const endpoint of ['/version', '/api/health']) assert.equal((await (await fetch(`${base}${endpoint}`)).json()).version, version);
 const results = [];
 for (const engine of ['chromium', 'webkit']) {
  const browser = await ({ chromium, webkit })[engine].launch({ headless: true, ...(engine === 'webkit' && process.env.WEBKIT_TEST_EXECUTABLE ? { executablePath: process.env.WEBKIT_TEST_EXECUTABLE } : {}) });
  try {
   const context = await browser.newContext(engine === 'webkit' ? devices['iPhone 13'] : { viewport: { width: 1440, height: 900 } });
   await context.route('**/*', route => new URL(route.request().url()).origin === base ? route.continue() : route.abort());
   const page = await context.newPage(); page.setDefaultTimeout(30000);
   const errors = []; page.on('pageerror', error => errors.push(error.message));
   const activate = locator => engine === 'webkit' ? locator.tap() : locator.click();
   await page.goto(`${base}/login`);
   await activate(page.getByRole('link', { name: 'Forgot password?' }));
   assert.equal(await page.getByLabel('Email', { exact: true }).count(), 0);
   await page.getByLabel('Recovery code', { exact: true }).fill('synthetic-invalid-reset-token');
   await page.getByLabel('New password', { exact: true }).fill('Synthetic-only-browser-Q98!');
   await activate(page.getByRole('button', { name: 'Show password', exact: true }));
   assert.equal(await page.getByLabel('New password', { exact: true }).getAttribute('type'), 'text');
   await activate(page.getByRole('button', { name: 'Hide password', exact: true }));
   assert.equal(await page.getByLabel('New password', { exact: true }).getAttribute('type'), 'password');
   const denied = page.waitForResponse(res => res.url().endsWith('/auth/password-reset/confirm'));
   await activate(page.getByRole('button', { name: 'Save new password', exact: true }));
   assert.equal((await denied).status(), 400);
   await page.getByRole('alert').filter({ hasText: 'This code is invalid or no longer available.' }).waitFor();
   await page.screenshot({ path: `${out}/${engine}-recovery-invalid.png`, fullPage: true });
   await activate(page.getByRole('button', { name: 'Try another code', exact: true }));
   assert.equal(await page.getByLabel('Recovery code', { exact: true }).inputValue(), '');
   await activate(page.getByRole('link', { name: 'Back to sign in', exact: true }));
   await page.waitForURL('**/login');
   assert.deepEqual(errors, []);
   results.push({ engine, version, invalidTokenStatus: 400, pageErrors: errors, externalMailSent: false });
  } finally { await browser.close(); }
 }
 fs.writeFileSync(`${out}/summary.json`, JSON.stringify(results, null, 2));
 console.log(JSON.stringify(results, null, 2));
})().catch(error => { console.error(error); process.exitCode = 1; });
