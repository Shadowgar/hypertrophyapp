// Mutates only synthetic accounts on the explicitly version-checked disposable service.
// Run disabled first, then enabled with the same private tmpfs session directory.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium, webkit, devices } = require('playwright');
const base = 'http://127.0.0.1:55431';
const expectedVersion = process.env.FERRAVIS_EXPECTED_VERSION;
const phase = process.env.FERRAVIS_CONSENT_PHASE;
const out = process.env.FERRAVIS_TEST_ARTIFACTS;
const sessions = process.env.FERRAVIS_PRIVATE_SESSIONS;
assert.match(expectedVersion || '', /^[a-f0-9]{40}$/);
assert.ok(['disabled', 'enabled'].includes(phase));
assert.ok(out);
assert.ok(sessions?.startsWith('/dev/shm/ferravis-'));
fs.mkdirSync(out, { recursive: true }); fs.mkdirSync(sessions, { recursive: true, mode: 0o700 });
async function request(page, endpoint, method = 'GET', body) {
 return page.evaluate(async ({ endpoint, method, body }) => {
  const response = await fetch(`/api${endpoint}`, { method, headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.getItem('hypertrophy_token')}`, ...(method === 'POST' ? { 'Idempotency-Key': crypto.randomUUID() } : {}) }, ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
  return { status: response.status, data: await response.json() };
 }, { endpoint, method, body });
}
(async () => {
 const versions = await Promise.all(['/version', '/api/health'].map(async endpoint => (await fetch(`${base}${endpoint}`)).json()));
 for (const result of versions) assert.equal(result.version, expectedVersion);
 const results = [];
 for (const engine of (process.env.FERRAVIS_TEST_ENGINES || 'chromium,webkit').split(',')) {
  const browser = await ({ chromium, webkit })[engine].launch({ headless: true, ...(engine === 'webkit' && process.env.WEBKIT_TEST_EXECUTABLE ? { executablePath: process.env.WEBKIT_TEST_EXECUTABLE } : {}) });
  const sessionPath = path.join(sessions, `${engine}.json`);
  const context = await browser.newContext({ ...(engine === 'webkit' ? devices['iPhone 13'] : { viewport: { width: 1440, height: 900 } }), timezoneId: 'America/New_York', ...(phase === 'enabled' ? { storageState: sessionPath } : {}) });
  await context.route('**/*', route => new URL(route.request().url()).origin === base ? route.continue() : route.abort());
  const page = await context.newPage(); page.setDefaultTimeout(60000);
  const errors = [], writes = [], responses = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', req => { if (['POST', 'PATCH', 'PUT'].includes(req.method())) writes.push({ method: req.method(), path: new URL(req.url()).pathname }); });
  page.on('response', res => { if (new URL(res.url()).pathname.startsWith('/api/')) responses.push({ path: new URL(res.url()).pathname, status: res.status() }); });
  const activate = locator => engine === 'webkit' ? locator.tap() : locator.click();
  try {
   if (phase === 'disabled') {
    await page.goto(`${base}/onboarding`, { waitUntil: 'networkidle' });
    await activate(page.getByRole('button', { name: 'Create an account', exact: true }));
    await page.getByLabel('Name', { exact: true }).fill('Synthetic consent review');
    await page.getByLabel('Email', { exact: true }).fill(`ferravis-consent-${engine}-${Date.now()}@example.com`);
    await page.getByLabel('Password', { exact: true }).fill('Synthetic-only-browser-Q98!');
    await activate(page.getByRole('button', { name: 'Create account', exact: true }));
    await page.getByRole('heading', { name: 'How would you like to train?' }).waitFor();
    await activate(page.getByRole('button', { name: /Create a Customized program/ }));
    await page.getByLabel('Age', { exact: true }).fill('34');
    await page.getByLabel('Body weight (lb)', { exact: true }).fill('180');
    await page.getByLabel('Training days per week').selectOption('3');
    await activate(page.getByRole('button', { name: 'Continue to equipment' }));
    await page.getByLabel('Dumbbells', { exact: true }).check();
    await activate(page.getByRole('button', { name: 'Review setup' }));
    await page.screenshot({ path: `${out}/${engine}-customized-setup-review.png`, fullPage: true });
    await activate(page.getByRole('button', { name: 'Save setup & review Customized' }));
    await page.waitForURL('**/customize');
    await page.getByRole('status').filter({ hasText: 'Customized is not enabled in this deployment' }).waitFor();
    assert.equal(await page.getByRole('button', { name: 'Generate preview', exact: true }).isDisabled(), true);
    assert.equal(await page.getByRole('button', { name: 'Accept program', exact: true }).count(), 0);
    assert.equal(await page.getByRole('button', { name: 'Activate selected dates', exact: true }).count(), 0);
    assert.equal(writes.filter(call => call.path.startsWith('/api/customized/')).length, 0);
    assert.equal(writes.filter(call => call.path === '/api/profile/initial-setup').length, 1);
    await context.storageState({ path: sessionPath }); fs.chmodSync(sessionPath, 0o600);
    await page.screenshot({ path: `${out}/${engine}-customized-disabled.png`, fullPage: true });
   } else {
    await page.goto(`${base}/customize`, { waitUntil: 'networkidle' });
    const options = await request(page, '/customized/options'); assert.equal(options.status, 200);
    // Fixture setup only: explicit synthetic rack/stations, no strength history or invented personal loads.
    const equipment = ['machine', 'floor', 'dumbbell', 'bench', 'bodyweight', 'leg_press_station', 'chest_press_station', 'row_station', 'leg_curl_station', 'pulldown_station', 'calf_station'];
    const setups = [], assignments = {};
    for (const variant of options.data.variants) {
     if (!['dumbbell', 'machine'].includes(variant.implement)) continue;
     const key = variant.implement === 'dumbbell' ? 'synthetic-rack' : `synthetic-${variant.id}`;
     if (!setups.some(setup => setup.key === key)) setups.push({ key, label: `Synthetic ${key}`, kind: variant.implement === 'dumbbell' ? 'dumbbell' : 'machine_stack', unit: 'kg', weights: [10, 11, 12].map(weight => ({ weight, count: 2 })), plates: [], bar_weight: null, stack: null, min_load: null, max_load: null, setup_note: 'Synthetic disposable qualification fixture; exact setup identity only' });
     assignments[variant.id] = key;
    }
    const profile = { location_id: 'synthetic-qualification-gym', location_name: 'Synthetic qualification gym', equipment, setups, assignments, unavailable_variants: [], strength_reports: [] };
    const saved = await request(page, '/customized/profile', 'PUT', { expected_revision: options.data.inventory.revision, profile }); assert.equal(saved.status, 200);
    await page.reload({ waitUntil: 'networkidle' });
    await page.getByLabel('Training context').selectOption('current');
    await page.getByLabel('Exercise skill').selectOption('intermediate');
    await page.getByLabel('No movement restrictions', { exact: true }).check();
    await page.getByLabel('IANA timezone', { exact: true }).fill('America/New_York');
    const schedule = await request(page, '/plan/scheduling-context?timezone=America%2FNew_York'); assert.equal(schedule.status, 200);
    const dates = [7, 9, 11].map(offset => { const day = new Date(`${schedule.data.week_start}T12:00:00Z`); day.setUTCDate(day.getUTCDate() + offset); return day.toISOString().slice(0, 10); });
    for (let i = 0; i < dates.length; i++) await page.getByLabel(`Workout date ${i + 1}`, { exact: true }).fill(dates[i]);
    const previewResponse = page.waitForResponse(res => new URL(res.url()).pathname === '/api/customized/proposals' && res.request().method() === 'POST');
    await activate(page.getByRole('button', { name: 'Generate preview', exact: true }));
    const preview = await previewResponse; assert.equal(preview.status(), 200); const proposal = await preview.json();
    assert.equal(await page.getByRole('button', { name: 'Activate selected dates', exact: true }).count(), 0);
    const review = page.getByRole('button', { name: 'Review acceptance', exact: true }); await review.waitFor(); assert.equal(await review.isDisabled(), false);
    await activate(review);
    const consent = page.getByRole('checkbox', { name: 'I accept this exact program version', exact: true }); await consent.waitFor();
    const accept = page.getByRole('button', { name: 'Accept program', exact: true });
    assert.equal(await consent.isChecked(), false); assert.equal(await accept.isDisabled(), true);
    await accept.evaluate(el => el.click());
    assert.equal(writes.filter(call => call.path.endsWith('/accept')).length, 0);
    await consent.check(); assert.equal(await accept.isDisabled(), false);
    await consent.uncheck(); assert.equal(await accept.isDisabled(), true);
    assert.equal(await page.getByRole('button', { name: 'Activate selected dates', exact: true }).count(), 0);
    await consent.scrollIntoViewIfNeeded();
    await page.screenshot({ path: `${out}/${engine}-customized-consent-unchecked.png`, fullPage: true });
    const current = await request(page, `/customized/proposals/${proposal.proposal_id}`); assert.equal(current.status, 200);
    const denied = await request(page, `/customized/proposals/${proposal.proposal_id}/activate`, 'POST', { expected_revision: current.data.revision, snapshot_hash: current.data.snapshot_hash });
    assert.equal(denied.status, 409, JSON.stringify(denied.data));
    const active = await request(page, '/customized/active'); assert.equal(active.status, 200); assert.deepEqual(active.data.plans, []);
    const after = await request(page, `/customized/proposals/${proposal.proposal_id}`); assert.notEqual(after.data.state, 'accepted_candidate'); assert.notEqual(after.data.state, 'active');
    results.push({ engine, phase, dates, proposalState: after.data.state, rejectedActivation: denied, activePlans: active.data.plans.length });
   }
   assert.deepEqual(errors, []);
   results.push({ engine, phase, versions, pageErrors: errors, writes, apiResponses: responses });
  } catch (error) {
   console.error('Failed browser URL:', page.url()); console.error((await page.locator('body').innerText()).slice(-3500));
   await page.screenshot({ path: `${out}/${engine}-${phase}-failure.png`, fullPage: true }); throw error;
  } finally { await browser.close(); }
 }
 fs.writeFileSync(`${out}/summary.json`, JSON.stringify(results, null, 2)); console.log(JSON.stringify(results, null, 2));
})().catch(error => { console.error(error); process.exitCode = 1; });
