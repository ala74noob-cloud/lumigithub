// Full render: node src/render.js [workers] [fps]
// Renders all frames in parallel chunks -> build/video/part_XX.mp4, then concat -> build/video/video.mp4
const { chromium } = require('playwright');
const { spawn, execFileSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const ROOT = path.resolve(__dirname, '..');
const TL = JSON.parse(fs.readFileSync(path.join(ROOT, 'build', 'timeline.json'), 'utf8'));
const WORKERS = parseInt(process.argv[2] || '4', 10);
const FPS = parseInt(process.argv[3] || '30', 10);
const NF = Math.round(TL.total * FPS);
const OUT = path.join(ROOT, 'build', 'video');
fs.mkdirSync(OUT, { recursive: true });

async function worker(browser, idx, f0, f1) {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => console.log(`[w${idx} pageerror]`, e.message));
  await page.goto('file://' + path.join(ROOT, 'src', 'index.html'));
  await page.evaluate(() => window.ready);
  const file = path.join(OUT, `part_${String(idx).padStart(2, '0')}.mp4`);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '15', '-pix_fmt', 'yuv420p', '-threads', '2', '-r', String(FPS), file], { stdio: ['pipe', 'inherit', 'inherit'] });
  const t0 = Date.now();
  for (let f = f0; f < f1; f++) {
    const b64 = await page.evaluate((t) => { window.renderFrame(t); return document.getElementById('c').toDataURL('image/jpeg', 0.95).split(',')[1]; }, f / FPS);
    const buf = Buffer.from(b64, 'base64');
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if ((f - f0) % 150 === 0) console.log(`w${idx}: frame ${f - f0}/${f1 - f0}  ${((Date.now() - t0) / Math.max(1, f - f0)).toFixed(0)} ms/frame`);
  }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));
  await page.close();
  return file;
}

(async () => {
  console.log(`frames: ${NF} @ ${FPS}fps, workers: ${WORKERS}`);
  const browser = await chromium.launch({ args: ['--allow-file-access-from-files'] });
  const per = Math.ceil(NF / WORKERS);
  const jobs = [];
  for (let i = 0; i < WORKERS; i++) jobs.push(worker(browser, i, i * per, Math.min(NF, (i + 1) * per)));
  const files = await Promise.all(jobs);
  await browser.close();
  const list = path.join(OUT, 'list.txt');
  fs.writeFileSync(list, files.map(f => `file '${f}'`).join('\n'));
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', path.join(OUT, 'video.mp4')]);
  console.log('done ->', path.join(OUT, 'video.mp4'));
})();
