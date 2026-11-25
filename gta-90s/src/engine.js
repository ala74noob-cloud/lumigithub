// ---------- core utilities & shared drawing helpers ----------
const W = 1920, H = 1080;
const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const lerp = (a, b, t) => a + (b - a) * t;
const inv = (a, b, x) => clamp((x - a) / (b - a));
const E = {
  lin: t => t,
  outCubic: t => 1 - Math.pow(1 - t, 3),
  inCubic: t => t * t * t,
  inOutCubic: t => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),
  outQuint: t => 1 - Math.pow(1 - t, 5),
  outExpo: t => (t >= 1 ? 1 : 1 - Math.pow(2, -10 * t)),
  outBack: t => { const c1 = 1.9, c3 = c1 + 1; return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2); },
  outElastic: t => (t <= 0 ? 0 : t >= 1 ? 1 : Math.pow(2, -10 * t) * Math.sin((t * 10 - 0.75) * (2 * Math.PI) / 3) + 1),
  inOutSine: t => -(Math.cos(Math.PI * t) - 1) / 2,
};
function rng(seed) {
  let s = seed >>> 0;
  return function () {
    s = (s + 0x6D2B79F5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function hash(n) { const r = rng(n * 9301 + 49297); r(); return r(); }
function off(w, h) { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; }
function ctxOf(c) { return c.getContext('2d'); }

// segment helpers
const SEG = {}; TL.segments.forEach(s => (SEG[s.id] = s));
const B = TL.beats;
const LINES = {}; TL.lines.forEach(l => (LINES[l.id] = l));
function segAt(t) { for (const s of TL.segments) if (t >= s.start && t < s.end) return s; return TL.segments[TL.segments.length - 1]; }

// ---------- color ----------
function normHex(hex) {
  let h = hex.replace('#', '');
  if (h.length === 3) h = h.split('').map(x => x + x).join('');
  return '#' + h;
}
function hexA(hex, a) {
  const h = normHex(hex).replace('#', '');
  const r = parseInt(h.substr(0, 2), 16), g = parseInt(h.substr(2, 2), 16), b = parseInt(h.substr(4, 2), 16);
  return `rgba(${r},${g},${b},${a})`;
}
function mixHex(a, b, t) {
  a = normHex(a); b = normHex(b);
  const pa = [1, 3, 5].map(i => parseInt(a.substr(i, 2), 16));
  const pb = [1, 3, 5].map(i => parseInt(b.substr(i, 2), 16));
  return '#' + pa.map((v, i) => Math.round(lerp(v, pb[i], t)).toString(16).padStart(2, '0')).join('');
}

// ---------- primitive drawing ----------
function vgrad(c, y0, y1, stops) {
  const g = c.createLinearGradient(0, y0, 0, y1);
  stops.forEach(([o, col]) => g.addColorStop(o, col));
  return g;
}
function glow(c, x, y, r, col, a = 1) {
  const g = c.createRadialGradient(x, y, 0, x, y, r);
  g.addColorStop(0, hexA(col, a));
  g.addColorStop(0.35, hexA(col, a * 0.45));
  g.addColorStop(1, hexA(col, 0));
  c.fillStyle = g;
  c.fillRect(x - r, y - r, r * 2, r * 2);
}
function starPath(c, x, y, r, rot = -Math.PI / 2, inner = 0.45) {
  c.beginPath();
  for (let i = 0; i < 10; i++) {
    const rr = i % 2 === 0 ? r : r * inner;
    const a = rot + (i * Math.PI) / 5;
    const px = x + Math.cos(a) * rr, py = y + Math.sin(a) * rr;
    i === 0 ? c.moveTo(px, py) : c.lineTo(px, py);
  }
  c.closePath();
}
function roundRect(c, x, y, w, h, r) {
  c.beginPath();
  c.moveTo(x + r, y); c.lineTo(x + w - r, y); c.quadraticCurveTo(x + w, y, x + w, y + r);
  c.lineTo(x + w, y + h - r); c.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  c.lineTo(x + r, y + h); c.quadraticCurveTo(x, y + h, x, y + h - r);
  c.lineTo(x, y + r); c.quadraticCurveTo(x, y, x + r, y);
  c.closePath();
}

// halftone dots that fade along a direction (pre-render only; slow-ish)
function halftone(c, x, y, w, h, col, spacing, fromA, toA, vertical = true, maxR = 0.5) {
  c.fillStyle = col;
  for (let yy = 0; yy < h; yy += spacing) {
    for (let xx = (yy / spacing) % 2 ? spacing / 2 : 0; xx < w; xx += spacing) {
      const f = vertical ? yy / h : xx / w;
      const a = lerp(fromA, toA, f);
      if (a <= 0.02) continue;
      c.beginPath();
      c.arc(x + xx, y + yy, spacing * maxR * a, 0, Math.PI * 2);
      c.fill();
    }
  }
}

// skyline layer; returns canvas
function skyline(opts) {
  const o = Object.assign({ w: 2400, h: 900, seed: 1, baseY: 900, minH: 120, maxH: 500, minW: 60, maxW: 150,
    color: '#223', edge: null, win: '#ffd877', winProb: 0.35, winSize: [6, 9], gapX: 4, spires: 0.15, outline: null, lw: 0 }, opts);
  const cv = off(o.w, o.h), c = ctxOf(cv), r = rng(o.seed);
  let x = -20;
  while (x < o.w) {
    const bw = lerp(o.minW, o.maxW, r());
    const bh = lerp(o.minH, o.maxH, Math.pow(r(), 1.3)) * (o.profile ? o.profile(x / o.w) : 1);
    const top = o.baseY - bh;
    c.fillStyle = o.color;
    c.fillRect(x, top, bw, bh + 4);
    // stepped top / spire
    const sv = r();
    if (sv < o.spires) {
      const sw = bw * lerp(0.25, 0.5, r()), sh = bh * lerp(0.08, 0.22, r());
      c.fillRect(x + (bw - sw) / 2, top - sh, sw, sh + 2);
      c.fillRect(x + bw / 2 - 2, top - sh - sh * 0.8, 4, sh * 0.8);
    } else if (sv < o.spires + 0.25) {
      const sw = bw * 0.7;
      c.fillRect(x + (bw - sw) / 2, top - 18, sw, 20);
    }
    if (o.edge) { c.fillStyle = o.edge; c.fillRect(x, top, 3, bh); }
    if (o.outline) { c.strokeStyle = o.outline; c.lineWidth = o.lw; c.strokeRect(x, top, bw, bh + 20); }
    // windows
    if (o.winProb > 0) {
      const [ww, wh] = o.winSize;
      for (let wy = top + 12; wy < o.baseY - 10; wy += wh + 7) {
        for (let wx = x + 8; wx < x + bw - ww - 4; wx += ww + 6) {
          if (r() < o.winProb) {
            c.fillStyle = o.win;
            c.globalAlpha = lerp(0.45, 1, r());
            c.fillRect(wx, wy, ww, wh);
            c.globalAlpha = 1;
          }
        }
      }
    }
    x += bw + o.gapX * r();
  }
  return cv;
}

// palm tree
function palm(c, x, y, h, lean, sway, col, rim) {
  const topX = x + lean * h, topY = y - h;
  const cx = x + lean * h * 0.3 + sway * 10, cy = y - h * 0.55;
  c.fillStyle = col;
  c.beginPath();
  const segs = 14;
  const left = [], right = [];
  for (let i = 0; i <= segs; i++) {
    const t = i / segs;
    const px = (1 - t) * (1 - t) * x + 2 * (1 - t) * t * cx + t * t * (topX + sway * 18);
    const py = (1 - t) * (1 - t) * y + 2 * (1 - t) * t * cy + t * t * topY;
    const wdt = lerp(h * 0.045, h * 0.022, t);
    left.push([px - wdt, py]); right.push([px + wdt, py]);
  }
  c.moveTo(left[0][0], left[0][1]);
  left.forEach(p => c.lineTo(p[0], p[1]));
  right.reverse().forEach(p => c.lineTo(p[0], p[1]));
  c.closePath(); c.fill();
  if (rim) { c.strokeStyle = rim; c.lineWidth = 2; c.stroke(); }
  const tx = topX + sway * 18, ty = topY;
  const n = 8;
  for (let i = 0; i < n; i++) {
    const a = -Math.PI + (i / (n - 1)) * Math.PI + Math.sin(sway * 2 + i) * 0.08;
    const len = h * lerp(0.42, 0.55, hash(i + h));
    const droop = h * 0.22;
    const ex = tx + Math.cos(a) * len, ey = ty + Math.sin(a) * len * 0.45 + droop * (1 - Math.abs(Math.sin(a))) + droop * 0.4;
    const mx = tx + Math.cos(a) * len * 0.5, my = ty + Math.sin(a) * len * 0.5 - h * 0.08;
    c.beginPath();
    c.moveTo(tx, ty);
    c.quadraticCurveTo(mx, my - h * 0.05, ex, ey);
    c.quadraticCurveTo(mx, my + h * 0.06, tx, ty + 4);
    c.closePath();
    c.fill();
    if (rim) { c.stroke(); }
  }
}

// side view car. opts: body, roof, win, stripe, kind('sports'|'sedan'|'police'|'lowrider'|'taxi'), lights, wheelRot
function carSide(c, x, y, s, o) {
  o = Object.assign({ body: '#eee', win: '#1b2a3a', outline: '#111', lw: 5, kind: 'sedan', wheelRot: 0, head: false, tail: false, stripe: null, dir: 1 }, o);
  c.save();
  c.translate(x, y); c.scale(s * o.dir, s);
  c.lineJoin = 'round';
  const body = new Path2D();
  if (o.kind === 'sports') {
    body.moveTo(-210, -30); body.lineTo(-200, -62); body.lineTo(-120, -72); body.lineTo(-60, -112); body.lineTo(40, -112);
    body.lineTo(110, -76); body.lineTo(200, -66); body.lineTo(215, -40); body.lineTo(212, -18); body.lineTo(-206, -14); body.closePath();
  } else if (o.kind === 'lowrider') {
    body.moveTo(-230, -30); body.lineTo(-222, -64); body.lineTo(-110, -70); body.lineTo(-70, -116); body.lineTo(60, -116);
    body.lineTo(100, -72); body.lineTo(222, -64); body.lineTo(232, -34); body.lineTo(228, -14); body.lineTo(-226, -14); body.closePath();
  } else {
    body.moveTo(-205, -26); body.lineTo(-198, -70); body.lineTo(-120, -78); body.lineTo(-80, -130); body.lineTo(70, -130);
    body.lineTo(120, -80); body.lineTo(200, -72); body.lineTo(210, -34); body.lineTo(206, -12); body.lineTo(-200, -12); body.closePath();
  }
  c.fillStyle = o.body; c.fill(body);
  if (o.lower) { c.save(); c.clip(body); c.fillStyle = o.lower; c.fillRect(-260, -66, 520, 70); c.restore(); }
  if (o.doors) { c.save(); c.clip(body); c.fillStyle = o.doors; c.fillRect(-112, -80, 222, 70); c.strokeStyle = o.outline; c.lineWidth = 3; c.strokeRect(-112, -80, 222, 70); c.restore(); }
  if (o.stripe) { c.save(); c.clip(body); c.fillStyle = o.stripe; const sh = o.stripeH || 12; c.fillRect(-260, -46 - sh / 2, 520, sh); c.restore(); }
  // windows
  c.fillStyle = o.win;
  c.beginPath();
  if (o.kind === 'sports') { c.moveTo(-108, -74); c.lineTo(-56, -104); c.lineTo(34, -104); c.lineTo(92, -76); }
  else if (o.kind === 'lowrider') { c.moveTo(-98, -72); c.lineTo(-64, -108); c.lineTo(54, -108); c.lineTo(86, -72); }
  else { c.moveTo(-108, -80); c.lineTo(-74, -122); c.lineTo(64, -122); c.lineTo(108, -80); }
  c.closePath(); c.fill();
  c.strokeStyle = o.outline; c.lineWidth = o.lw * 0.6; c.stroke();
  c.beginPath(); c.moveTo(-6, -78); c.lineTo(-6, o.kind === 'sports' ? -104 : -122); c.stroke();
  // window shine
  c.strokeStyle = 'rgba(255,255,255,0.35)'; c.lineWidth = 6;
  c.beginPath(); c.moveTo(-60, -86); c.lineTo(-40, -110); c.stroke();
  // outline body
  c.strokeStyle = o.outline; c.lineWidth = o.lw; c.stroke(body);
  // police light bar
  if (o.kind === 'police') {
    c.fillStyle = o.barL || '#e33'; c.fillRect(-40, -146, 36, 16);
    c.fillStyle = o.barR || '#36f'; c.fillRect(4, -146, 36, 16);
    c.strokeRect(-40, -146, 80, 16);
    if (o.flash !== undefined) {
      glow(c, -22, -138, 90, o.flash ? '#ff3030' : '#3060ff', 0.9);
    }
  }
  if (o.text) {
    c.fillStyle = o.textCol || '#111'; c.font = '700 34px Bebas, Anton'; c.textAlign = 'center';
    c.fillText(o.text, -20, -30);
  }
  // wheels
  const wheel = (wx) => {
    c.fillStyle = '#111'; c.beginPath(); c.arc(wx, -10, 44, 0, Math.PI * 2); c.fill();
    c.fillStyle = o.rim || '#bbb'; c.beginPath(); c.arc(wx, -10, 22, 0, Math.PI * 2); c.fill();
    c.strokeStyle = '#555'; c.lineWidth = 4;
    for (let i = 0; i < 5; i++) {
      const a = o.wheelRot + (i * Math.PI * 2) / 5;
      c.beginPath(); c.moveTo(wx, -10); c.lineTo(wx + Math.cos(a) * 20, -10 + Math.sin(a) * 20); c.stroke();
    }
  };
  wheel(-120); wheel(130);
  if (o.head) { c.fillStyle = '#fff6c8'; c.fillRect(196, -60, 16, 12); glow(c, 214, -54, 120, '#fff2b0', 0.7); }
  if (o.tail) { c.fillStyle = '#ff2a2a'; c.fillRect(-206, -60, 12, 12); glow(c, -206, -54, 70, '#ff2020', 0.6); }
  c.restore();
}

// stylised person silhouette (feet at x,y, height h). o: fat(1..), female, col, rim, rimSide, shirt, pose, jacket, cap
function person(c, x, y, h, o) {
  o = Object.assign({ col: '#0b0b12', rim: null, fat: 1, female: false, shirt: null, pose: 'stand', jacket: false, rimSide: 1, cap: false, hood: false }, o);
  const u = h / 100, f = o.fat, fem = o.female;
  const shW = (fem ? 13.5 : 17.5) * (1 + (f - 1) * 0.55);
  const waW = (fem ? 9 : 12.5) * (1 + (f - 1) * 0.9);
  const hiW = (fem ? 13.5 : 12.5) * (1 + (f - 1) * 0.7);
  const legX = (fem ? 5.2 : 6.2) * (1 + (f - 1) * 0.6);
  const legW = (fem ? 7.2 : 8.6) * (1 + (f - 1) * 0.7);
  const torso = () => {
    const P = new Path2D();
    P.moveTo(-shW, -76.5);
    P.quadraticCurveTo(-shW * 0.5, -80.5, 0, -80.5);
    P.quadraticCurveTo(shW * 0.5, -80.5, shW, -76.5);
    P.bezierCurveTo(shW + 1.5, -70, waW + 1 + (f - 1) * 8, -64, waW, -56);
    P.quadraticCurveTo(hiW + 1, -50, hiW, -44);
    P.lineTo(-hiW, -44);
    P.quadraticCurveTo(-hiW - 1, -50, -waW, -56);
    P.bezierCurveTo(-waW - 1 - (f - 1) * 8, -64, -shW - 1.5, -70, -shW, -76.5);
    P.closePath();
    if (f > 1.05) P.ellipse(0, -58, waW + (f - 1) * 9, 12 + (f - 1) * 3, 0, 0, Math.PI * 2);
    if (o.jacket) { P.moveTo(-shW, -74); P.lineTo(-hiW - 3, -38); P.lineTo(hiW + 3, -38); P.lineTo(shW, -74); P.closePath(); }
    return P;
  };
  const fig = (col, dx) => {
    c.save(); c.translate(dx, 0);
    c.fillStyle = col; c.strokeStyle = col; c.lineCap = 'round'; c.lineJoin = 'round';
    // legs
    [-1, 1].forEach(sd => {
      c.lineWidth = legW; c.beginPath(); c.moveTo(sd * legX, -45); c.lineTo(sd * (legX + 0.6), -24); c.stroke();
      c.lineWidth = legW * 0.78; c.beginPath(); c.moveTo(sd * (legX + 0.6), -25); c.lineTo(sd * (legX + 1.2), -3.5); c.stroke();
      c.beginPath(); c.ellipse(sd * (legX + 2.6), -2.2, 4.6, 2.4, 0, 0, Math.PI * 2); c.fill();
    });
    // arms
    const aw = (fem ? 5.2 : 6.4) * Math.sqrt(f);
    [-1, 1].forEach(sd => {
      c.lineWidth = aw;
      c.beginPath(); c.moveTo(sd * (shW - 2.5), -74.5);
      if (o.pose === 'cross') { c.lineTo(sd * (shW + 1.5), -61); c.lineTo(-sd * 5, -63); }
      else if (o.pose === 'hips') { c.lineTo(sd * (shW + 8), -63); c.lineTo(sd * (waW + 1.5), -53); }
      else { c.lineTo(sd * (shW + 1.6 + (f - 1) * 7), -60); c.lineTo(sd * (shW + 0.6 + (f - 1) * 7), -45); }
      c.stroke();
      if (o.pose === 'stand') { c.beginPath(); c.arc(sd * (shW + 0.6 + (f - 1) * 7), -44, aw * 0.62, 0, Math.PI * 2); c.fill(); }
    });
    c.fill(torso());
    // neck + head
    c.fillRect(-3.4, -87, 6.8, 9);
    c.beginPath(); c.ellipse(0, -92.5, 7.4 * (1 + (f - 1) * 0.22), 9.2, 0, 0, Math.PI * 2); c.fill();
    if (fem) {
      c.beginPath(); c.moveTo(-8.6, -95); c.bezierCurveTo(-12, -86, -11, -76, -7, -71); c.lineTo(7, -71);
      c.bezierCurveTo(11, -76, 12, -86, 8.6, -95); c.quadraticCurveTo(0, -105, -8.6, -95); c.fill();
    }
    if (o.cap) { c.beginPath(); c.ellipse(0, -98.5, 8, 4.2, 0, Math.PI, 0); c.fill(); c.fillRect(-1, -99, 13, 2.6); }
    if (o.hood) { c.beginPath(); c.ellipse(0, -92, 10.5, 12, 0, 0, Math.PI * 2); c.fill(); }
    c.restore();
  };
  c.save(); c.translate(x, y); c.scale(u, u);
  const off = o.rim ? -o.rimSide * 2.0 : 0;
  if (o.rim) fig(o.rim, 0);
  fig(o.col, off);
  if (o.shirt) { c.save(); c.translate(off, 0); c.fillStyle = o.shirt; c.fill(torso());
    if (o.floral) { c.clip(torso()); for (let i = 0; i < 14; i++) { c.fillStyle = o.floral; c.beginPath(); c.arc(-shW + hash(i) * shW * 2, -78 + hash(i + 5) * 34, 1.8, 0, 7); c.fill(); } }
    c.restore(); }
  c.restore();
}

// ---------- text ----------
const FONT_CN = '"ZCOOL QingKe HuangYou", "Noto Sans SC", sans-serif';
const FONT_CN2 = '"Smiley", "ZCOOL QingKe HuangYou", sans-serif';
const FONT_NUM = 'Anton, "Noto Sans SC", sans-serif';
const FONT_LAT = 'Bebas, Anton, sans-serif';

function isNumChar(ch) { return /[0-9.$%亿万]/.test(ch); }

// draw outlined text, optionally with per-char colour runs. returns width
function outlinedText(c, str, x, y, o) {
  o = Object.assign({ font: FONT_CN, size: 120, fill: '#fff', fill2: null, stroke: '#000', lw: 0.15, shadow: 0.07,
    align: 'center', grad: true, numCol: null, track: 0, shadowCol: 'rgba(0,0,0,0.75)' }, o);
  c.save();
  c.font = `${o.size}px ${o.font}`;
  c.textBaseline = 'alphabetic';
  c.lineJoin = 'round'; c.miterLimit = 2;
  // runs
  const runs = [];
  for (const ch of str) {
    const num = o.numCol && isNumChar(ch);
    if (runs.length && runs[runs.length - 1].num === num) runs[runs.length - 1].s += ch;
    else runs.push({ s: ch, num });
  }
  const tr = o.track * o.size;
  runs.forEach(r => (r.w = c.measureText(r.s).width + tr * [...r.s].length));
  const total = runs.reduce((a, r) => a + r.w, 0) - tr;
  let x0 = o.align === 'center' ? x - total / 2 : o.align === 'right' ? x - total : x;
  const lw = o.size * o.lw;
  const drawRuns = (fn) => {
    let xx = x0;
    for (const r of runs) {
      if (tr) { for (const ch of r.s) { fn(r, ch, xx); xx += c.measureText(ch).width + tr; } }
      else { fn(r, r.s, xx); xx += r.w; }
    }
  };
  c.textAlign = 'left';
  // shadow
  if (o.shadow) {
    const d = o.size * o.shadow;
    c.fillStyle = o.shadowCol; c.strokeStyle = o.shadowCol; c.lineWidth = lw;
    drawRuns((r, s, xx) => { c.strokeText(s, xx + d * 0.7, y + d); c.fillText(s, xx + d * 0.7, y + d); });
  }
  c.strokeStyle = o.stroke; c.lineWidth = lw;
  if (lw > 0) drawRuns((r, s, xx) => c.strokeText(s, xx, y));
  const mk = (col) => {
    if (!o.grad) return col;
    const g = c.createLinearGradient(0, y - o.size * 0.85, 0, y + o.size * 0.1);
    g.addColorStop(0, mixHex(col, '#ffffff', 0.35));
    g.addColorStop(0.55, col);
    g.addColorStop(1, mixHex(col, '#000000', 0.18));
    return g;
  };
  const f1 = mk(o.fill), f2 = o.numCol ? mk(o.numCol) : f1;
  drawRuns((r, s, xx) => { c.fillStyle = r.num ? f2 : f1; c.fillText(s, xx, y); });
  c.restore();
  return total;
}
function measure(c, str, font, size) { c.save(); c.font = `${size}px ${font}`; const w = c.measureText(str).width; c.restore(); return w; }

// a "stamp" (rotated rounded box w/ text)
function stamp(c, str, x, y, size, col, rot, p, o = {}) {
  if (p <= 0) return;
  const s = lerp(2.2, 1, E.outCubic(clamp(p * 1.0))) ;
  c.save();
  c.translate(x, y); c.rotate(rot); c.scale(s, s);
  c.globalAlpha = clamp(p * 3) * (o.alpha ?? 1);
  c.font = `${size}px ${o.font || FONT_CN}`;
  const w = c.measureText(str).width + size * 0.7, h = size * 1.25;
  c.lineWidth = size * 0.09; c.strokeStyle = col;
  roundRect(c, -w / 2, -h / 2, w, h, size * 0.18); c.stroke();
  roundRect(c, -w / 2 + size * 0.12, -h / 2 + size * 0.12, w - size * 0.24, h - size * 0.24, size * 0.12);
  c.lineWidth = size * 0.035; c.stroke();
  c.fillStyle = col; c.textAlign = 'center'; c.textBaseline = 'middle';
  c.fillText(str, 0, size * 0.06);
  c.restore();
}

// rolling odometer number formatting
function fmtInt(n) { return Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ','); }

// ---------- noise / grain ----------
const GRAIN = [];
(function () {
  for (let k = 0; k < 4; k++) {
    const cv = off(640, 360), c = ctxOf(cv), id = c.createImageData(640, 360), r = rng(77 + k);
    for (let i = 0; i < id.data.length; i += 4) {
      const v = r() * 255;
      id.data[i] = id.data[i + 1] = id.data[i + 2] = v; id.data[i + 3] = 255;
    }
    c.putImageData(id, 0, 0);
    GRAIN.push(cv);
  }
})();
