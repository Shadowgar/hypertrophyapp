// Requires caller-provided Playwright, a disposable API/PostgreSQL and loopback web.
// Example: NODE_PATH=/path/to/playwright/node_modules node ...browser.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { chromium, webkit, devices } = require('playwright');
const base = new URL(process.env.WORKOUTAPP_TEST_BASE || 'http://127.0.0.1:55431');
assert.equal(base.hostname, '127.0.0.1');
assert.equal(base.port, '55431', 'This runner only mutates dedicated disposable port 55431');
const out = process.env.WORKOUTAPP_TEST_ARTIFACTS;
if (out) fs.mkdirSync(out, { recursive: true });
(async () => {
 const summaries = [];
 for (const engine of (process.env.WORKOUTAPP_TEST_ENGINES || 'chromium,webkit').split(',')) {
  const browser = await ({ chromium, webkit })[engine].launch({ headless: true, ...(engine === 'webkit' && process.env.WEBKIT_TEST_EXECUTABLE ? { executablePath: process.env.WEBKIT_TEST_EXECUTABLE } : {}) });
  const context = await browser.newContext({ ...(engine === 'webkit' ? devices['iPhone 13'] : { viewport: { width: 1440, height: 900 } }), timezoneId: 'America/New_York' });
  await context.route('**/*', route => new URL(route.request().url()).origin === base.origin ? route.continue() : route.abort());
  const page = await context.newPage(); page.setDefaultTimeout(60000);
  const errors = [], writes = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', req => { if (['POST', 'PATCH', 'PUT'].includes(req.method())) writes.push({ method: req.method(), path: new URL(req.url()).pathname }); });
  const tap = locator => engine === 'webkit' ? locator.tap() : locator.click();
  try {
   const email = `iphone-${engine}-${Date.now()}@example.com`, password = 'Synthetic-only-browser-Q98!';
   await page.goto(`${base}onboarding`, { waitUntil: 'networkidle' });
   await tap(page.getByRole('button', { name: 'Create an account', exact: true }));
   await page.getByLabel('Name', { exact: true }).fill('Synthetic browser');
   await page.getByLabel('Email', { exact: true }).fill(email);
   await page.getByLabel('Password', { exact: true }).fill(password);
   await tap(page.getByRole('button', { name: 'Show password', exact: true }));
   assert.equal(await page.getByLabel('Password', { exact: true }).getAttribute('type'), 'text');
   assert.equal(await page.getByLabel('Password', { exact: true }).inputValue(), password);
   await tap(page.getByRole('button', { name: 'Hide password', exact: true }));
   await tap(page.getByRole('button', { name: 'Create account', exact: true }));
   await page.getByRole('heading', { name: 'How would you like to train?' }).waitFor();
   await tap(page.getByRole('button', { name: /Follow an Authored program/ }));
   await page.getByRole('heading', { name: 'Follow an Authored program' }).waitFor();
   await page.goBack(); await page.getByRole('heading', { name: 'How would you like to train?' }).waitFor();
   assert.equal(await page.getByRole('button', { name: 'Create account', exact: true }).count(), 0);
   await page.goForward(); await page.getByRole('heading', { name: 'Follow an Authored program' }).waitFor();
   await page.reload(); await page.getByRole('heading', { name: 'Follow an Authored program' }).waitFor();
   // Leave/close the page, sign out locally, then sign back into the same account.
   await page.close();
   const resumed = await context.newPage();
   await resumed.goto(`${base}onboarding`);
   await resumed.evaluate(() => { localStorage.removeItem('hypertrophy_token'); window.dispatchEvent(new Event('hypertrophy:auth-token-changed')); });
   await resumed.close();
   const next = await context.newPage();
   // Continue with a fresh page while keeping only the account-owned non-private draft.
   await runAfterLogin(next, email, password, engine, out, writes, errors);
   summaries.push({ engine, viewport: engine === 'webkit' ? '390x844 iPhone 13 emulation' : '1440x900 desktop', writes, pageErrors: errors });
   assert.equal(writes.filter(call => call.path === '/api/auth/register').length, 1);
   assert.equal(writes.filter(call => call.path === '/api/profile/initial-setup').length, 1);
   assert.equal(writes.filter(call => call.path === '/api/plan/generate-week').length, 0);
   assert.deepEqual(errors, []);
  } finally { await browser.close(); }
 }
 if (out) fs.writeFileSync(`${out}/summary.json`, JSON.stringify(summaries, null, 2));
 console.log(JSON.stringify(summaries, null, 2));
})().catch(error => { console.error(error); process.exitCode = 1; });

async function runAfterLogin(page, email, password, engine, out, writes, errors) {
 page.setDefaultTimeout(60000);
 page.on('pageerror', error => errors.push(error.message));
 page.on('request', req => { if (['POST', 'PATCH', 'PUT'].includes(req.method())) writes.push({ method: req.method(), path: new URL(req.url()).pathname }); });
 const tap = locator => engine === 'webkit' ? locator.tap() : locator.click();
 await page.goto(`${base}login`);
 await page.getByLabel('Email', { exact: true }).fill(email);
 await page.getByLabel('Password', { exact: true }).fill(password);
 await tap(page.getByRole('button', { name: 'Show password', exact: true }));
 assert.equal(await page.getByLabel('Password', { exact: true }).getAttribute('type'), 'text');
 await tap(page.getByRole('button', { name: 'Hide password', exact: true }));
 await tap(page.getByRole('button', { name: 'Sign in', exact: true }));
 await page.waitForURL('**/onboarding');
 await page.getByRole('heading', { name: 'Follow an Authored program' }).waitFor();
 await tap(page.getByRole('button', { name: /^Full Body Phase 1/ }));
 await tap(page.getByRole('button', { name: 'Use Full Body Phase 1' }));
 await page.getByLabel('Age', { exact: true }).fill('34');
 await page.getByLabel('Body weight (lb)', { exact: true }).fill('180');
 await page.getByLabel('Training days per week').selectOption('3');
 await tap(page.getByRole('button', { name: 'Continue to equipment' }));
 await tap(page.getByRole('button', { name: 'Review setup' }));
 await tap(page.getByRole('button', { name: 'Save setup & choose dates' }));
 await page.waitForURL('**/week');
 const controls = page.getByRole('region', { name: 'Week scheduling' });
 await controls.getByText('Select at least 2 dates to preview (0 selected).').waitFor();
 const dates = controls.getByRole('checkbox');
 await tap(dates.nth(0));
 await controls.getByText('Select at least 2 dates to preview (1 selected).').waitFor();
 await tap(dates.nth(2));
 await tap(controls.getByRole('button', { name: 'Preview selected dates', exact: true }));
 await controls.getByText(/Preview ready.*not activated/).waitFor();
 await controls.getByRole('button', { name: 'Activate selected dates' }).waitFor();
 assert.equal(writes.filter(call => call.path === '/api/plan/generate-week').length, 0);
 if (out) await page.screenshot({ path: `${out}/${engine}-preview.png`, fullPage: true });
 // Saved profile has no activated plan: re-login must return to date planning.
 await page.evaluate(() => { localStorage.removeItem('hypertrophy_token'); window.dispatchEvent(new Event('hypertrophy:auth-token-changed')); });
 await page.goto(`${base}login`);
 await page.getByLabel('Email', { exact: true }).fill(email); await page.getByLabel('Password', { exact: true }).fill(password);
 await tap(page.getByRole('button', { name: 'Sign in', exact: true })); await page.waitForURL('**/week');
 await page.goto(`${base}onboarding`); await page.getByRole('heading', { name: 'Your saved setup' }).waitFor();
 assert.equal(await page.getByRole('button', { name: 'Create account', exact: true }).count(), 0);
 if (out) await page.screenshot({ path: `${out}/${engine}-saved-setup.png`, fullPage: true });
}
