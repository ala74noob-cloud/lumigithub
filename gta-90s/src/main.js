// ---------- orchestration: hook montage, transitions, HUD, cards ----------
const cv = document.getElementById('c');
const ctx = cv.getContext('2d');
const ERA = {
  hook: { accent: '#FFD23F', accent2: '#FF4D4D', stars: 0 },
  gta1: { accent: '#FFD23F', accent2: '#FF5A4D', stars: 1 },
  gta2: { accent: '#39F3FF', accent2: '#FF3EA5', stars: 2 },
  gta3: { accent: '#F5C518', accent2: '#7FB2FF', stars: 3 },
  vc: { accent: '#FF5FD2', accent2: '#38F2E8', stars: 3 },
  sa: { accent: '#3BD16F', accent2: '#FFB020', stars: 3 },
  gta4: { accent: '#E9EEF2', accent2: '#FFB347', stars: 4 },
  gta5: { accent: '#58E07A', accent2: '#FFD23F', stars: 5 },
  gta6: { accent: '#FF6FAE', accent2: '#FFD36B', stars: 6 },
  outro: { accent: '#FFD23F', accent2: '#FF6FAE', stars: 6 },
};
const ORDER = TL.segments.map(s => s.id);
const ERA_IDS = ['gta1', 'gta2', 'gta3', 'vc', 'sa', 'gta4', 'gta5', 'gta6'];
const bufA = off(W, H), bufB = off(W, H), bufC = off(W, H);
let VIGNETTE, THUMBS = {};

function drawScene(c, id, t, opt) {
  c.save();
  c.globalAlpha = 1; c.globalCompositeOperation = 'source-over'; c.filter = 'none';
  c.setTransform(1, 0, 0, 1, 0, 0);
  if (id === 'hook') drawHook(c, t);
  else if (id === 'outro') drawOutro(c, t);
  else SCENES[id].draw(c, t, opt || {});
  c.restore();
}

// ---------------- hook ----------------
const HOOK_END = LINES.h3.start - 0.12;
const SHOT = HOOK_END / MONTAGE.length;
const SLIDE = 0.2;
function drawHook(c, t) {
  if (t < HOOK_END) {
    const i = Math.min(MONTAGE.length - 1, Math.floor(t / SHOT));
    const m = MONTAGE[i];
    const lt = t - i * SHOT;
    const ca = ctxOf(bufC);
    drawShot(ca, m, lt);
    c.drawImage(bufC, 0, 0);
    // slide-in of next shot
    const rem = (i + 1) * SHOT - t;
    if (i < MONTAGE.length - 1 && rem < SLIDE) {
      const p = E.inOutCubic(1 - rem / SLIDE);
      const n = MONTAGE[i + 1];
      const cb = ctxOf(bufB);
      drawShot(cb, n, -rem);
      const ex = lerp(W + 260, -260, p);
      c.save(); c.beginPath(); c.moveTo(ex + 200, 0); c.lineTo(W + 400, 0); c.lineTo(W + 400, H); c.lineTo(ex - 200, H); c.closePath(); c.clip();
      c.drawImage(bufB, 0, 0); c.restore();
      c.save(); c.strokeStyle = ERA[n.id].accent; c.lineWidth = 34; c.beginPath(); c.moveTo(ex + 200, 0); c.lineTo(ex - 200, H); c.stroke();
      c.strokeStyle = '#fff'; c.lineWidth = 8; c.beginPath(); c.moveTo(ex + 224, 0); c.lineTo(ex - 176, H); c.stroke(); c.restore();
    }
    // year + title (top-left); switches half-way through the slide
    let li = i, k = clamp((t - i * SHOT) / 0.25);
    if (i < MONTAGE.length - 1 && rem < SLIDE / 2) { li = i + 1; k = clamp((SLIDE / 2 - rem) / 0.12); }
    const lm = MONTAGE[li];
    c.save();
    c.globalAlpha = 1;
    const yy = 210;
    outlinedText(c, lm.year, 80, yy, { font: FONT_NUM, size: 170, fill: ERA[lm.id].accent, lw: 0.08, align: 'left' });
    c.globalAlpha = k;
    outlinedText(c, lm.title, 86, yy + 74, { font: FONT_LAT, size: 70, fill: '#fff', lw: 0.12, align: 'left', track: 0.05 });
    c.restore();
    return;
  }
  // title card
  const q = t - HOOK_END;
  c.fillStyle = '#0b0b10'; c.fillRect(0, 0, W, H);
  c.save(); c.translate(W / 2, 520); c.rotate(t * 0.12);
  for (let i = 0; i < 18; i++) { c.rotate(Math.PI / 9); c.fillStyle = i % 2 ? 'rgba(255,210,63,0.10)' : 'rgba(255,111,174,0.07)'; c.beginPath(); c.moveTo(0, 0); c.lineTo(-150, -1500); c.lineTo(150, -1500); c.fill(); }
  c.restore();
  halftone(c, 0, 600, W, 480, 'rgba(255,210,63,0.10)', 20, 0, 1, true, 0.4);
  // faint montage strip
  c.save(); c.globalAlpha = 0.22;
  ERA_IDS.forEach((id, i) => { const th = THUMBS[id]; if (th) c.drawImage(th, ((i * 250 - q * 120) % (8 * 250)) - 40, 890, 240, 135); });
  c.restore();
  const p1 = E.outBack(clamp(q / 0.35));
  c.save(); c.translate(W / 2, 470); c.scale(p1, p1); c.rotate(-0.04);
  outlinedText(c, '90秒', 0, 0, { font: FONT_CN, size: 330, fill: '#FFD23F', lw: 0.12, shadow: 0.06, numCol: '#FFD23F' });
  c.restore();
  const wG = LINES.h3.words.find(w => w[2] === 'GTA');
  const tG = wG ? wG[0] : LINES.h3.start + 0.8;
  const p2 = E.outBack(clamp((t - tG + 0.15) / 0.35));
  if (p2 > 0) {
    c.save(); c.translate(W / 2, 660); c.scale(p2, p2);
    outlinedText(c, '带你看完 GTA 1→6 代', 0, 0, { font: FONT_CN, size: 120, fill: '#ffffff', lw: 0.15, numCol: '#FF6FAE' });
    c.restore();
  }
  // stars light up across the end of the line
  const s0 = tG, s1 = LINES.h3.end;
  for (let i = 0; i < 6; i++) {
    const on = t > lerp(s0, s1, i / 6);
    const pop = clamp((t - lerp(s0, s1, i / 6)) / 0.2);
    const x = W / 2 + (i - 2.5) * 130, y = 800;
    const r = 46 * (on ? 1 + 0.25 * Math.sin(pop * Math.PI) : 0.85);
    starPath(c, x, y, r); c.lineJoin = 'round';
    c.fillStyle = on ? '#fff' : 'rgba(255,255,255,0.12)'; c.fill();
    c.lineWidth = 8; c.strokeStyle = '#000'; c.stroke();
  }
}
function drawShot(c, m, lt) {
  c.save();
  const z = 1.08 - 0.05 * clamp((lt + SLIDE) / (SHOT + SLIDE));
  c.translate(W / 2, H / 2); c.scale(z, z); c.translate(-W / 2, -H / 2);
  SCENES[m.id].draw(c, m.t + lt * 0.8, Object.assign({ clean: true }, m.opt || {}));
  c.restore();
}

// ---------------- outro ----------------
function drawOutro(c, t) {
  const S = SEG.outro, q = t - S.start;
  c.fillStyle = '#0b0b10'; c.fillRect(0, 0, W, H);
  const z = lerp(1.15, 1.0, E.outCubic(clamp(q / 1.6)));
  c.save(); c.translate(W / 2, 400); c.scale(z, z); c.rotate(-0.03);
  const tw = 380, th = 214, gap = 24;
  ERA_IDS.forEach((id, i) => {
    const col = i % 4, row = Math.floor(i / 4);
    const x = (col - 2) * (tw + gap) + gap / 2, y = (row - 1) * (th + gap + 50) + 10;
    const p = E.outCubic(clamp((q - i * 0.06) / 0.4));
    c.save(); c.globalAlpha = p; c.translate(x + tw / 2, y + th / 2); c.scale(lerp(0.8, 1, p), lerp(0.8, 1, p));
    c.drawImage(THUMBS[id], -tw / 2, -th / 2, tw, th);
    c.lineWidth = 8; c.strokeStyle = ERA[id].accent; c.strokeRect(-tw / 2, -th / 2, tw, th);
    outlinedText(c, MONTAGE[i].year, -tw / 2 + 12, th / 2 + 40, { font: FONT_NUM, size: 48, fill: ERA[id].accent, lw: 0.12, align: 'left', shadow: 0 });
    outlinedText(c, MONTAGE[i].title, tw / 2 - 10, th / 2 + 40, { font: FONT_LAT, size: 40, fill: '#fff', lw: 0.12, align: 'right', shadow: 0 });
    c.restore();
  });
  c.restore();
  c.fillStyle = 'rgba(0,0,0,0.35)'; c.fillRect(0, 0, W, H);
}

// ---------------- transitions ----------------
const TRANS = 0.26;
function drawWithTransitions(c, t) {
  const segs = TL.segments;
  for (let i = 1; i < segs.length; i++) {
    const T = segs[i].start;
    if (t > T - TRANS && t < T + TRANS) {
      const p = E.inOutCubic((t - (T - TRANS)) / (2 * TRANS));
      drawScene(ctxOf(bufA), segs[i - 1].id, t);
      drawScene(ctxOf(bufB), segs[i].id, t);
      c.drawImage(bufA, 0, 0);
      const ex = lerp(W + 300, -300, p);
      c.save(); c.beginPath(); c.moveTo(ex + 260, 0); c.lineTo(W + 400, 0); c.lineTo(W + 400, H); c.lineTo(ex - 260, H); c.closePath(); c.clip();
      c.drawImage(bufB, 0, 0); c.restore();
      const col = ERA[segs[i].id].accent;
      c.save();
      c.strokeStyle = '#000'; c.lineWidth = 120; c.beginPath(); c.moveTo(ex + 300, 0); c.lineTo(ex - 220, H); c.stroke();
      c.strokeStyle = col; c.lineWidth = 80; c.beginPath(); c.moveTo(ex + 300, 0); c.lineTo(ex - 220, H); c.stroke();
      c.strokeStyle = '#fff'; c.lineWidth = 10; c.beginPath(); c.moveTo(ex + 350, 0); c.lineTo(ex - 170, H); c.stroke();
      c.restore();
      return segs[i];
    }
  }
  const s = segAt(t);
  drawScene(c, s.id, t);
  return s;
}

// ---------------- HUD: era intro + badge ----------------
function drawEraTitle(c, t) {
  for (const s of TL.segments) {
    if (!ERA_IDS.includes(s.id)) continue;
    if (t < s.start || t > s.end) continue;
    const e = ERA[s.id];
    let k, a = 1, start = s.start;
    if (s.id === 'gta6') { start = LINES.g6e.start - 1.05; if (t < start + 0.7) continue; }
    const lt = t - start;
    const sIn = E.outBack(clamp(lt / 0.32));
    k = E.inOutCubic(clamp((lt - 0.72) / 0.4));
    a *= 1 - clamp((t - (s.end - 0.25)) / 0.2);
    if (a <= 0) continue;
    const yearSize = 280, titleSize = 96;
    c.save();
    c.font = `${yearSize}px ${FONT_NUM}`; const wy = c.measureText(s.year).width;
    c.font = `${titleSize}px ${FONT_LAT}`; const wt = c.measureText(s.title).width * 1.08;
    const wmax = Math.max(wy, wt);
    const sc = lerp(1, 0.4, k);
    const cx = lerp(W / 2, 70 + (wmax * 0.4) / 2, k), cy = lerp(450, 132, k);
    c.globalAlpha = a;
    c.translate(cx, cy); c.scale(sc * sIn, sc * sIn); c.rotate(lerp(-0.05, 0, k));
    if (k < 1) { // backing flash
      c.save(); c.globalAlpha = a * (1 - k) * 0.55; c.fillStyle = '#000'; c.fillRect(-W, -260, W * 2, 420); c.restore();
    }
    outlinedText(c, s.year, 0, 0, { font: FONT_NUM, size: yearSize, fill: e.accent, lw: 0.07, shadow: 0.05 });
    outlinedText(c, s.title, 0, titleSize * 1.15, { font: FONT_LAT, size: titleSize, fill: '#ffffff', lw: 0.13, track: 0.08 });
    c.restore();
  }
}

// wanted stars (top-right)
function drawStars(c, t, seg) {
  if (seg.id === 'hook') return;
  const e = ERA[seg.id];
  const prevStars = (() => { const i = ORDER.indexOf(seg.id); return i > 0 ? ERA[ORDER[i - 1]].stars : 0; })();
  const lightAt = seg.id === 'gta6' ? B.g6_release : seg.start + 0.55;
  const blink = (seg.id === 'gta1' && t > B.g1_mad && t < LINES.g1d.end) || seg.id === 'outro';
  for (let i = 0; i < 6; i++) {
    const x = W - 90 - (5 - i) * 74, y = 92;
    let on = i < e.stars;
    let pop = 0;
    if (i >= prevStars && i < e.stars) { on = t > lightAt; pop = clamp((t - lightAt) / 0.25); }
    let fill = on ? '#ffffff' : 'rgba(255,255,255,0.18)';
    if (on && blink && Math.floor(t * 4) % 2 === 0) fill = '#ffd23f';
    const r = 30 * (1 + 0.45 * Math.sin(pop * Math.PI));
    c.save();
    if (pop > 0 && pop < 1) { c.globalCompositeOperation = 'lighter'; glow(c, x, y, 120, '#ffffff', 0.6 * (1 - pop)); c.globalCompositeOperation = 'source-over'; }
    starPath(c, x, y, r); c.lineJoin = 'round';
    c.fillStyle = fill; c.fill(); c.lineWidth = 7; c.strokeStyle = '#000'; c.stroke();
    c.restore();
  }
}

// timeline (bottom)
function drawTimeline(c, t, seg) {
  const idx = ERA_IDS.indexOf(seg.id);
  if (idx < 0) return;
  const x0 = 420, x1 = W - 420, y = 1040;
  const a = clamp((t - SEG.gta1.start) * 2) * (1 - clamp((t - (SEG.gta6.end - 0.3)) / 0.3));
  c.save(); c.globalAlpha = a * 0.92;
  c.fillStyle = 'rgba(0,0,0,0.55)'; roundRect(c, x0 - 40, y - 34, x1 - x0 + 80, 62, 31); c.fill();
  c.strokeStyle = 'rgba(255,255,255,0.25)'; c.lineWidth = 4; c.beginPath(); c.moveTo(x0, y); c.lineTo(x1, y); c.stroke();
  const segP = clamp((t - seg.start) / (seg.end - seg.start));
  const px = lerp(x0, x1, (idx + segP) / (ERA_IDS.length - 1) * ((ERA_IDS.length - 1) / ERA_IDS.length) + 0.5 / ERA_IDS.length);
  c.strokeStyle = ERA[seg.id].accent; c.lineWidth = 6; c.beginPath(); c.moveTo(x0, y); c.lineTo(Math.min(px, x1), y); c.stroke();
  ERA_IDS.forEach((id, i) => {
    const nx = lerp(x0, x1, (i + 0.5) / ERA_IDS.length);
    const cur = i === idx, past = i < idx;
    c.beginPath(); c.arc(nx, y, cur ? 11 : 7, 0, 7);
    c.fillStyle = cur ? ERA[id].accent : past ? '#ddd' : '#555'; c.fill();
    c.font = `${cur ? 34 : 26}px ${FONT_LAT}`; c.textAlign = 'center';
    c.fillStyle = cur ? '#fff' : past ? '#bbb' : '#777';
    c.fillText(MONTAGE[i].year, nx, y - 14 - (cur ? 4 : 0));
  });
  c.restore();
}

// ---------------- cards ----------------
const CARDS = [];
(function buildCards() {
  const lines = TL.lines;
  for (let i = 0; i < lines.length; i++) {
    const l = lines[i];
    if (!l.card) continue;
    const seg = SEG[l.seg];
    const first = lines.findIndex(x => x.seg === l.seg) === i;
    let st = l.start - 0.04;
    if (first && ERA_IDS.includes(l.seg) && l.seg !== 'gta6') st = Math.max(st, seg.start + 1.08);
    const nxt = lines[i + 1];
    let en = l.end + 0.85;
    if (nxt) {
      let ns = nxt.start - 0.04;
      const nFirst = nxt.seg !== l.seg;
      if (nFirst) ns = Math.min(ns, SEG[nxt.seg].start - 0.18);
      en = Math.min(en, ns);
    }
    en = Math.min(en, seg.end - 0.12);
    CARDS.push({ line: l, st, en, seg: l.seg });
  }
})();
function drawCards(c, t) {
  for (const cd of CARDS) {
    if (t < cd.st || t > cd.en) continue;
    const e = ERA[cd.seg] || ERA.hook;
    const [A, Bt] = cd.line.card;
    const big = cd.line.big;
    const pin = clamp((t - cd.st) / 0.28), pout = clamp((t - (cd.en - 0.16)) / 0.16);
    // scrim
    c.save();
    c.globalAlpha = Math.min(E.outCubic(pin), 1 - pout);
    c.fillStyle = vgrad(c, 560, H, [[0, 'rgba(0,0,0,0)'], [0.55, 'rgba(0,0,0,0.45)'], [1, 'rgba(0,0,0,0.7)']]);
    c.fillRect(0, 560, W, H - 560);
    c.restore();
    const sizeB0 = big ? 200 : 150;
    const sizeB = Math.min(sizeB0, sizeB0 * 1620 / measure(c, Bt, FONT_CN, sizeB0));
    const sizeA = Math.min(92, 92 * 1500 / measure(c, A, FONT_CN2, 92));
    const yB = 955, yA = yB - sizeB * 0.98 - 6;
    // line A
    const pa = E.outCubic(clamp((t - cd.st) / 0.24));
    c.save();
    c.globalAlpha = pa * (1 - pout);
    c.translate(W / 2 + lerp(-90, 0, pa), yA);
    outlinedText(c, A, 0, 0, { font: FONT_CN2, size: sizeA, fill: '#ffffff', lw: 0.2, shadow: 0.07, numCol: e.accent2 });
    c.restore();
    // line B
    const pb = clamp((t - cd.st - 0.07) / 0.32);
    if (pb > 0) {
      const s = lerp(1.4, 1, E.outBack(pb)) * lerp(1, 0.96, pout);
      c.save();
      c.globalAlpha = clamp(pb * 3) * (1 - pout);
      c.translate(W / 2, yB - sizeB * 0.35); c.rotate(-0.025); c.scale(s, s); c.translate(0, sizeB * 0.35);
      outlinedText(c, Bt, 0, 0, { font: FONT_CN, size: sizeB, fill: e.accent, lw: 0.16, shadow: 0.075, numCol: big ? null : e.accent2 });
      c.restore();
    }
  }
}

// ---------------- master render ----------------
function render(t) {
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.globalAlpha = 1; ctx.filter = 'none'; ctx.globalCompositeOperation = 'source-over';
  ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H);
  const seg = drawWithTransitions(ctx, t);
  drawEraTitle(ctx, t);
  drawStars(ctx, t, seg);
  drawTimeline(ctx, t, seg);
  drawCards(ctx, t);
  // grain + vignette
  ctx.save(); ctx.globalCompositeOperation = 'overlay'; ctx.globalAlpha = 0.10;
  ctx.drawImage(GRAIN[Math.floor(t * 30) % 4], 0, 0, W, H); ctx.restore();
  ctx.drawImage(VIGNETTE, 0, 0);
  // fades
  const fi = 1 - clamp(t / 0.25), fo = clamp((t - (TL.total - 0.7)) / 0.6);
  const f = Math.max(fi, fo);
  if (f > 0) { ctx.fillStyle = `rgba(0,0,0,${f})`; ctx.fillRect(0, 0, W, H); }
}

async function init() {
  const texts = [];
  TL.lines.forEach(l => l.card && texts.push(...l.card));
  texts.push('90秒带你看完GTA 1→6代', '原版：蓝白涂装发售版：黑白涂装发售延期', '配音：雷·利奥塔', '游戏背景年代', 'PS2 史上最畅销游戏 · 约1733万份', '首周销售额 · 首日卖出360万份',
    '份 · 截至2026年11月（Take-Two财报）', '24小时 YouTube 播放量 · 吉尼斯纪录', '重回罪恶都市 · 首次男女双主角', '*Take-Two 官方估算的首日零售额', '$37.9亿', 'AO 成人级下架刷新纪录3天',
    '绿帮红帮蓝帮+ 好感− 结仇', '1998年成立 · GTA2 由它发行', '9 月', 'RAY LIOTTA ·《好家伙》主演');
  const all = texts.join('');
  await Promise.all([
    document.fonts.load(`100px "ZCOOL QingKe HuangYou"`, all),
    document.fonts.load(`100px "Noto Sans SC"`, all),
    document.fonts.load(`100px Smiley`, all),
    document.fonts.load(`100px Anton`, '0123456789$,.亿'),
    document.fonts.load(`100px Bebas`, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'),
    document.fonts.load(`100px Bowlby`, "ABCDEFGHIJKLMNOPQRSTUVWXYZ'!?"),
  ]);
  await document.fonts.ready;
  Object.values(SCENES).forEach(s => s.init && s.init());
  VIGNETTE = off(W, H);
  const vc = ctxOf(VIGNETTE), g = vc.createRadialGradient(W / 2, H / 2, H * 0.35, W / 2, H / 2, H * 1.05);
  g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, 'rgba(0,0,0,0.5)');
  vc.fillStyle = g; vc.fillRect(0, 0, W, H);
  // thumbnails for title strip & outro
  MONTAGE.forEach(m => {
    const tc = ctxOf(bufA);
    tc.clearRect(0, 0, W, H);
    SCENES[m.id].draw(tc, m.t, Object.assign({ clean: true }, m.opt || {}));
    const th = off(480, 270); ctxOf(th).drawImage(bufA, 0, 0, 480, 270);
    THUMBS[m.id] = th;
  });
  return true;
}
window.ready = init();
window.renderFrame = (t) => { render(t); return true; };
window.TOTAL = TL.total;
