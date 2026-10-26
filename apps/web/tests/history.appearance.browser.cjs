// Run with Playwright installed in the caller's module path; no server or account needed.
// Optional PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH selects an existing local browser.
// Example: node apps/web/tests/history.appearance.browser.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');

const app = path.resolve(__dirname, '../app');
const styles = ['globals.css', 'appearances.css', 'unified.css', 'history/history.css']
  .map(file => fs.readFileSync(path.join(app, file), 'utf8')).join('\n');

(async () => {
  const browser = await chromium.launch({
    headless: true,
    ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH } : {}),
  });
  try {
    const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
    await page.setContent(`<style>${styles}</style><main class="history-page">
      <section class="history-card"><h2>Training calendar</h2><p>Recorded working sets</p>
        <div class="history-switch"><button>Month</button></div><button class="history-date">26</button>
        <label class="history-field">Date range<select><option>Last 4 weeks</option></select></label>
      </section></main>
      <div id="surface-reference" style="background:var(--surface);border:1px solid var(--border-subtle)"></div>
      <div id="input-reference" style="background:var(--input-fill);border:1px solid var(--border-control)"></div>`);
    let appearances = 0;
    for (const family of ['graphite', 'charcoal', 'classic']) {
      for (const appearance of ['light', 'dark']) {
        await page.evaluate(({ family, appearance }) => {
          document.documentElement.dataset.theme = family;
          document.documentElement.dataset.appearance = appearance;
        }, { family, appearance });
        const rendered = await page.evaluate(() => {
          const style = selector => getComputedStyle(document.querySelector(selector));
          const rgb = value => value.match(/[\d.]+/g).slice(0, 3).map(Number);
          const luminance = value => rgb(value).map(n => n / 255).map(n => n <= .04045 ? n / 12.92 : ((n + .055) / 1.055) ** 2.4)
            .reduce((sum, n, i) => sum + n * [.2126, .7152, .0722][i], 0);
          const contrast = (a, b) => (Math.max(luminance(a), luminance(b)) + .05) / (Math.min(luminance(a), luminance(b)) + .05);
          const card = style('.history-card'), select = style('select');
          return {
            card: card.backgroundColor, surface: style('#surface-reference').backgroundColor,
            cardBorder: card.borderTopColor, subtleBorder: style('#surface-reference').borderTopColor,
            input: select.backgroundColor, inputFill: style('#input-reference').backgroundColor,
            controlBorders: ['select', '.history-switch button', '.history-date'].map(selector => style(selector).borderTopColor),
            controlBorder: style('#input-reference').borderTopColor,
            ratios: ['h2', 'p', 'label'].map(selector => contrast(style(selector).color, card.backgroundColor)),
            inputRatio: contrast(select.color, select.backgroundColor),
          };
        });
        const context = `${family}/${appearance}`;
        assert.equal(rendered.card, rendered.surface, `${context}: card bypasses semantic surface`);
        assert.equal(rendered.cardBorder, rendered.subtleBorder, `${context}: card border bypasses semantic border`);
        assert.equal(rendered.input, rendered.inputFill, `${context}: select bypasses semantic input fill`);
        assert.ok(rendered.controlBorders.every(color => color === rendered.controlBorder), `${context}: control bypasses semantic border`);
        assert.ok([...rendered.ratios, rendered.inputRatio].every(ratio => ratio >= 4.5), `${context}: text contrast below 4.5:1`);
        appearances++;
      }
    }
    // A palette update must repaint the consumers, not merely match today's colors.
    const changed = await page.evaluate(() => {
      const root = document.documentElement;
      root.style.setProperty('--surface', 'rgb(12, 34, 56)');
      root.style.setProperty('--input-fill', 'rgb(65, 43, 21)');
      root.style.setProperty('--border-control', 'rgb(23, 45, 67)');
      return { card: getComputedStyle(document.querySelector('.history-card')).backgroundColor,
        input: getComputedStyle(document.querySelector('select')).backgroundColor,
        border: getComputedStyle(document.querySelector('.history-date')).borderTopColor };
    });
    assert.deepEqual(changed, { card: 'rgb(12, 34, 56)', input: 'rgb(65, 43, 21)', border: 'rgb(23, 45, 67)' });
    console.log(JSON.stringify({ passed: true, appearances, dynamicSemanticTokenRepaint: true }));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
