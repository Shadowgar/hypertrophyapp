// Isolated browser regression: every API call is intercepted with synthetic data.
// Run with caller-provided Playwright, a loopback web server, and no live API.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { chromium, webkit, devices } = require('playwright');
const base = new URL(process.env.FERRAVIS_TEST_BASE || 'http://127.0.0.1:3301');
assert.equal(base.hostname, '127.0.0.1');
assert.ok(['3301', '55431'].includes(base.port), 'Only dedicated disposable web ports are allowed');
const out = process.env.FERRAVIS_TEST_ARTIFACTS;
assert.ok(out, 'Artifact directory is required'); fs.mkdirSync(out, { recursive: true });
const baseline = process.env.FERRAVIS_CAPTURE_BASELINE === '1';
const token = `synthetic.${Buffer.from(JSON.stringify({ sub: 'ferravis-browser-fixture' })).toString('base64url')}.synthetic`;
const viewports = [ ['desktop', 1440, 900], ['mobile', 390, 844], ['short-desktop', 1440, 600], ['landscape', 844, 390] ];
(async () => {
 const results = [];
 for (const engine of (process.env.FERRAVIS_TEST_ENGINES || 'chromium,webkit').split(',')) {
  const browser = await ({ chromium, webkit })[engine].launch({ headless: true, ...(engine === 'webkit' && process.env.WEBKIT_TEST_EXECUTABLE ? { executablePath: process.env.WEBKIT_TEST_EXECUTABLE } : {}) });
  try { for (const [name, width, height] of viewports) {
   const handheld = name === 'mobile' || name === 'landscape';
   const context = await browser.newContext({ ...(handheld ? devices['iPhone 13'] : {}), viewport: { width, height }, reducedMotion: 'reduce' });
   const requests = [], errors = [], draftIsolation = []; let failSave = true, saveCount = 0, setupProfile = null;
   await context.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (url.origin !== base.origin) return route.abort();
    if (!url.pathname.startsWith('/api/')) return route.continue();
    const path = url.pathname.slice(4); requests.push({ method: route.request().method(), path });
    let data = {}, status = 200;
    if (path === '/health') data = { status: 'ok' };
    else if (path === '/profile/preferences') data = { theme_family: 'classic', appearance: 'dark', weight_unit: 'lb', revision: 0 };
    else if (path === '/profile') data = setupProfile || { name: 'Synthetic athlete', age: 34, weight_kg: 80, days_available: 3, split_preference: 'full_body', equipment: ['barbell'], program_id: 'full_body_phase1', training_mode: 'authored' };
    else if (path === '/plan/programs') data = [
     { id: 'pure_bodybuilding_phase_1_full_body', name: 'Full Body Phase 1', days_supported: [2, 3, 4, 5] },
     { id: 'pure_bodybuilding_phase_2_full_body', name: 'Full Body Phase 2', days_supported: [2, 3, 4, 5] },
    ];
    else if (path === '/plan/scheduling-context') data = { timezone: 'America/New_York', local_today: '2026-10-29', week_start: '2026-10-26', selected_dates: ['2026-10-29'], placement_revision: 1, plan: null };
    else if (path === '/weekly-review/status') data = { today_is_sunday: false, review_required: false };
    else if (path === '/workout/today') data = { session_id: 'fixture-session', workout_occurrence_id: 'fixture-occurrence', title: 'Full Body Workout', date: '2026-10-29', exercises: [{ id: 'press', name: 'Bench Press', sets: 3, rep_range: [8, 12], recommended_working_weight: 40 }] };
    else if (path.endsWith('/progress')) data = { completed_total: 0, planned_total: 3, percent_complete: 0, exercises: [] };
    else if (path === '/soreness') {
     if (route.request().method() === 'POST') { saveCount++; await new Promise(resolve => setTimeout(resolve, 350)); data = failSave ? { detail: 'Synthetic save failure' } : {}; status = failSave ? 503 : 200; }
     else data = [];
    }
    return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(data) });
   });
   const page = await context.newPage(); page.setDefaultTimeout(45000); page.on('pageerror', e => errors.push(e.message));
   const activate = locator => handheld ? locator.tap() : locator.click();
   page.on('console', message => {
    if (message.type() === 'error' && !/\b503\b/.test(message.text())) errors.push(message.text());
   });
   await page.goto(`${base}login`, { waitUntil: 'networkidle' });
   await page.getByRole('heading', { name: 'Welcome back' }).waitFor();
   const recovery = await page.getByRole('link', { name: 'Forgot password?' }).boundingBox();
   const submit = await page.getByRole('button', { name: 'Sign in', exact: true }).boundingBox();
   const login = { gap: submit.y - (recovery.y + recovery.height), buttonBottom: submit.y + submit.height };
   await page.screenshot({ path: `${out}/${engine}-${name}-login.png`, fullPage: true });
   if (!baseline) {
    assert.equal(await page.title(), 'FERRAVIS — Strength, Engineered.');
    assert.ok(await page.getByRole('link', { name: 'FERRAVIS', exact: true }).count());
    const assets = await page.evaluate(async () => {
     const manifest = await (await fetch('/manifest.json')).json();
     const icons = await Promise.all([...manifest.icons.map(icon => icon.src), '/apple-touch-icon.png', '/favicon-32.png'].map(async src => {
      const image = new Image(); image.src = src; await image.decode(); return { src, width: image.naturalWidth, height: image.naturalHeight };
     }));
     return { name: manifest.name, shortName: manifest.short_name, icons };
    });
    assert.equal(assets.name, 'FERRAVIS — Strength, Engineered.');
    assert.equal(assets.shortName, 'FERRAVIS');
    assert.ok(assets.icons.every(icon => icon.width > 0 && icon.width === icon.height));
    assert.ok(login.gap >= 0 && login.gap <= 40, `${engine}/${name}: recovery-to-login gap ${login.gap}`);
    assert.ok(submit.x >= 0 && submit.x + submit.width <= width);
    await page.getByLabel('Password', { exact: true }).fill('Synthetic-only-password');
    await activate(page.getByRole('button', { name: 'Show password' }));
    assert.equal(await page.getByLabel('Password', { exact: true }).getAttribute('type'), 'text');
    await activate(page.getByRole('button', { name: 'Hide password' }));
    assert.equal(await page.getByLabel('Password', { exact: true }).getAttribute('type'), 'password');
    await activate(page.getByRole('link', { name: 'Create an account' }));
    await page.waitForURL('**/onboarding');
    await page.screenshot({ path: `${out}/${engine}-${name}-onboarding.png`, fullPage: true });
    if (name === 'desktop') {
     const oldId = '11111111-1111-4111-8111-111111111111', newId = '22222222-2222-4222-8222-222222222222';
     const email = 'synthetic-reset@example.com';
     const session = sub => `synthetic.${Buffer.from(JSON.stringify({ sub, email })).toString('base64url')}.synthetic`;
     const oldAnswers = { selectedProgramId: 'pure_bodybuilding_phase_2_full_body', daysAvailable: '5', trainingLocation: 'home', equipmentTags: ['cable'], chooseForMeFamily: 'upper_lower' };
     const beforeWrites = requests.filter(request => request.method !== 'GET').length;
     for (const kind of ['old-owner', 'legacy-unowned']) {
      const accountId = kind === 'old-owner' ? oldId : newId;
      setupProfile = { id: accountId, email, name: 'Synthetic reset fixture', initial_setup_available: true };
      await page.evaluate(({ kind, oldId, accountId, token, oldAnswers }) => {
       localStorage.clear(); sessionStorage.clear();
       localStorage.setItem('hypertrophy_token', token);
       localStorage.setItem('hypertrophy_onboarding_draft_v1', JSON.stringify(kind === 'old-owner'
        ? { version: 2, owner: `account:${oldId}`, answers: oldAnswers } : oldAnswers));
       if (kind === 'old-owner') localStorage.setItem(`hypertrophy_setup_position_${accountId}`, 'basics');
      }, { kind, oldId, accountId, token: session(accountId), oldAnswers });
      await page.goto(`${base}onboarding`, { waitUntil: 'networkidle' });
      if (kind === 'old-owner') {
       // Positive control: this is a valid old-account draft, not malformed test data.
       await page.getByRole('heading', { name: 'A few essentials' }).waitFor();
       assert.equal(await page.getByLabel('Training days per week').inputValue(), '5');
       assert.equal(await page.getByLabel('Training location', { exact: true }).inputValue(), 'home');
       setupProfile = { id: newId, email, name: 'Synthetic reset fixture', initial_setup_available: true };
       await page.evaluate(token => localStorage.setItem('hypertrophy_token', token), session(newId));
       await page.reload({ waitUntil: 'networkidle' });
      }
      await page.getByRole('heading', { name: 'How would you like to train?' }).waitFor();
      await activate(page.getByRole('button', { name: /Help me choose/ }));
      assert.equal(await page.getByLabel('Choose-for-me family').inputValue(), 'full_body');
      await activate(page.getByRole('button', { name: 'Keep Auto preference' }));
      await page.getByRole('heading', { name: 'A few essentials' }).waitFor();
      for (const label of ['Age', 'Body weight (lb)', 'Training days per week', 'Training location']) {
       assert.equal(await page.getByLabel(label, { exact: true }).inputValue(), '', `${kind} leaked ${label}`);
      }
      await page.screenshot({ path: `${out}/${engine}-${name}-${kind}-defaults.png`, fullPage: true });
      await page.getByLabel('Age', { exact: true }).fill('34');
      await page.getByLabel('Body weight (lb)', { exact: true }).fill('180');
      await page.getByLabel('Training days per week').selectOption('3');
      await activate(page.getByRole('button', { name: 'Continue to equipment' }));
      await page.getByRole('heading', { name: 'Your equipment' }).waitFor();
      assert.equal(await page.getByLabel('Cable station').isChecked(), false, `${kind} leaked equipment`);
      assert.equal(await page.locator('input[type="checkbox"]:checked').count(), 0);
      draftIsolation.push({ kind, sameEmail: true, distinctAccountIds: kind === 'old-owner', defaultsClean: true });
     }
     assert.equal(requests.filter(request => request.method !== 'GET').length, beforeWrites, 'Draft checks wrote server data');
     setupProfile = null;
     await page.evaluate(() => { localStorage.clear(); sessionStorage.clear(); });
    }
   }
   await page.evaluate(token => localStorage.setItem('hypertrophy_token', token), token);
   await page.goto(`${base}today`, { waitUntil: 'networkidle' });
   await page.getByText(/What.s sore today\?/).waitFor();
   const save = page.getByRole('button', { name: 'Save & Start Workout' });
   const skip = page.getByRole('button', { name: 'Skip', exact: true });
   const initialSave = await save.boundingBox(), initialSkip = await skip.boundingBox();
   const modal = { save: initialSave, skip: initialSkip, viewport: { width, height } };
   await page.screenshot({ path: `${out}/${engine}-${name}-soreness.png`, fullPage: true });
   if (!baseline) {
    const dialog = page.getByRole('dialog', { name: /What.s sore today/ });
    const bounds = await dialog.boundingBox();
    assert.ok(bounds.y >= 0 && bounds.y + bounds.height <= height, `Dialog exceeds viewport: ${JSON.stringify(bounds)}`);
    assert.ok(initialSave.y >= 0 && initialSave.y + initialSave.height <= height);
    assert.ok(initialSkip.y >= 0 && initialSkip.y + initialSkip.height <= height);
    assert.equal(await dialog.evaluate(el => el.contains(document.activeElement)), true);
    await skip.focus(); await page.keyboard.press('Tab');
    assert.equal(await dialog.evaluate(el => el.contains(document.activeElement)), true, 'Tab escaped modal');
    const body = dialog.getByRole('region', { name: 'Soreness inputs' });
    const scrollable = await body.evaluate(el => el.scrollHeight > el.clientHeight);
    modal.inputsScrollable = scrollable;
    if (height <= 600) assert.equal(scrollable, true, 'Short viewport should scroll inputs');
    await body.focus(); await page.keyboard.press('Shift+Tab');
    assert.equal(await skip.evaluate(el => el === document.activeElement), true, 'Backward Tab did not wrap');
    await body.focus(); await page.keyboard.press('PageDown'); await page.waitForTimeout(200);
    if (scrollable) assert.ok(await body.evaluate(el => el.scrollTop > 0), 'Keyboard cannot scroll inputs');
    await body.evaluate(el => { el.scrollTop = 0; });
    const oldScroll = await page.evaluate(() => window.scrollY);
    const bodyBox = await body.boundingBox(); await page.mouse.move(bodyBox.x + bodyBox.width / 2, bodyBox.y + bodyBox.height / 2); await page.mouse.wheel(0, 1000);
    await page.waitForTimeout(200);
    if (scrollable) assert.ok(await body.evaluate(el => el.scrollTop > 0), 'Inputs do not scroll');
    assert.equal(await page.evaluate(() => window.scrollY), oldScroll, 'Background scrolled');
    const afterScroll = await save.boundingBox(); assert.ok(Math.abs(afterScroll.y - initialSave.y) < 1, 'Footer moved while scrolling');
    if (engine === 'chromium' && handheld && scrollable) {
     await body.evaluate(el => { el.scrollTop = 0; });
     const cdp = await context.newCDPSession(page);
     // Browser-native touch scroll; WebKit is checked with touch controls and wheel/keyboard separately.
     await cdp.send('Input.synthesizeScrollGesture', {
      x: bodyBox.x + bodyBox.width / 2, y: bodyBox.y + bodyBox.height * .8,
      yDistance: -Math.min(180, bodyBox.height * .6), gestureSourceType: 'touch', speed: 300,
     });
     await cdp.detach();
     assert.ok(await body.evaluate(el => el.scrollTop > 0), 'Touch gesture cannot scroll inputs');
    }
    await page.mouse.move(5, 5); await page.mouse.wheel(0, 1000); await page.waitForTimeout(200);
    assert.equal(await page.evaluate(() => window.scrollY), oldScroll, 'Backdrop wheel scrolled background');
    await dialog.getByLabel('Optional soreness notes').fill('Synthetic check only');
    if (name === 'mobile') {
     // Exercise the VisualViewport handler with a keyboard-sized visible region.
     // Headless browsers do not display a real iPhone keyboard; physical acceptance stays open.
     await page.evaluate(() => {
      Object.defineProperty(window.visualViewport, 'height', { configurable: true, value: 340 });
      Object.defineProperty(window.visualViewport, 'offsetTop', { configurable: true, value: 40 });
      window.visualViewport.dispatchEvent(new Event('resize'));
     });
     const keyboardBounds = await dialog.boundingBox(), keyboardSave = await save.boundingBox();
     assert.ok(keyboardBounds.y >= 40 && keyboardBounds.y + keyboardBounds.height <= 380);
     assert.ok(keyboardSave.y >= 40 && keyboardSave.y + keyboardSave.height <= 380);
     await page.screenshot({ path: `${out}/${engine}-${name}-keyboard-viewport.png`, fullPage: true });
     await page.evaluate(() => {
      delete window.visualViewport.height; delete window.visualViewport.offsetTop;
      window.visualViewport.dispatchEvent(new Event('resize'));
     });
    }
    await activate(save); await save.evaluate(el => el.click());
    assert.equal(await save.isDisabled(), true); assert.equal(await skip.isDisabled(), true);
    assert.equal(await dialog.getByRole('status').textContent(), 'Saving soreness…');
    await page.getByRole('alert').filter({ hasText: 'Failed to save soreness' }).waitFor();
    assert.equal(saveCount, 1);
    const alert = await page.getByRole('alert').filter({ hasText: 'Failed to save soreness' }).boundingBox(); assert.ok(alert.y + alert.height <= height);
    await page.screenshot({ path: `${out}/${engine}-${name}-soreness-error.png`, fullPage: true });
    failSave = false; await activate(save); await dialog.waitFor({ state: 'hidden' }); assert.equal(saveCount, 2);
    assert.equal(await page.evaluate(() => document.body.style.position), '', 'Body scroll lock leaked');
    assert.equal(await page.getByRole('heading', { name: 'Today', exact: true }).evaluate(el => el === document.activeElement), true, 'Focus did not return to Today');
    await page.reload(); await page.getByRole('dialog').waitFor();
    await page.keyboard.press('Escape'); await page.getByRole('dialog').waitFor({ state: 'hidden' });
    assert.equal(await page.evaluate(() => localStorage.getItem('hypertrophy_soreness_skip:2026-10-29')), '1');
    assert.equal(saveCount, 2, 'Skip wrote a soreness report');
    assert.equal(await page.getByRole('heading', { name: 'Today', exact: true }).evaluate(el => el === document.activeElement), true, 'Skip did not restore focus');
    await page.screenshot({ path: `${out}/${engine}-${name}-today.png`, fullPage: true });
    assert.deepEqual(errors, []);
   }
   results.push({ engine, name, login, modal, draftIsolation, pageErrors: errors, interceptedApiRequests: requests.length });
   await context.close();
  } } finally { await browser.close(); }
 }
 fs.writeFileSync(`${out}/summary.json`, JSON.stringify({ baseline, results }, null, 2)); console.log(JSON.stringify({ baseline, results }, null, 2));
})().catch(error => { console.error(error); process.exitCode = 1; });
