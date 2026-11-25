// usage: node src/still.js out_dir t1 t2 ...   -> renders PNG stills (and a contact sheet via ffmpeg later)
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
(async () => {
  const [outDir, ...times] = process.argv.slice(2);
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch({ args: ['--allow-file-access-from-files'] });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  page.on('console', m => console.log('[page]', m.text()));
  page.on('pageerror', e => console.log('[pageerror]', e.message));
  await page.goto('file://' + path.resolve(__dirname, 'index.html'));
  await page.evaluate(() => window.ready);
  for (const ts of times) {
    const t = parseFloat(ts);
    await page.evaluate(t => window.renderFrame(t), t);
    const el = await page.$('#c');
    await el.screenshot({ path: path.join(outDir, `t${t.toFixed(2).padStart(6, '0')}.jpg`), type: 'jpeg', quality: 85 });
  }
  await browser.close();
})();
