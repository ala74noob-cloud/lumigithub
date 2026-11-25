// ---------- scenes: each draws a full 1920x1080 frame for absolute time t ----------
const SCENES = {};

// ===== shared: top-down city map (low-res pixel art) =====
const ROAD = 128, RW = 30;
function roadC(k) { return k * ROAD + RW / 2; }
function cityMap(o) {
  o = Object.assign({ size: 1152, seed: 3, ground: '#6b8f4e', road: '#4b4b4f', line: '#e8d35a', walk: '#a39f92',
    roofs: ['#b5653e', '#7a8fa0', '#9c8b5e', '#7b6890', '#c9b28a', '#5f7d65', '#a34d4d', '#8a8a8a'], park: '#5c9a45',
    tree: '#2f6e2a', water: '#2f63b8', neon: null, night: false }, o);
  const S = o.size, cv = off(S, S), c = ctxOf(cv), r = rng(o.seed);
  c.imageSmoothingEnabled = false;
  c.fillStyle = o.ground; c.fillRect(0, 0, S, S);
  const n = Math.ceil(S / ROAD);
  for (let bx = 0; bx < n; bx++) for (let by = 0; by < n; by++) {
    const x0 = bx * ROAD + RW, y0 = by * ROAD + RW, bs = ROAD - RW;
    c.fillStyle = o.walk; c.fillRect(x0, y0, bs, bs);
    const kind = r();
    if (bx === n - 1 || (bx >= n - 2 && by < 3 && o.water)) { // water edge
      c.fillStyle = o.water; c.fillRect(x0 - RW, y0 - RW, ROAD + 2, ROAD + 2);
      c.fillStyle = 'rgba(255,255,255,0.25)';
      for (let i = 0; i < 18; i++) c.fillRect(x0 - RW + r() * ROAD, y0 - RW + r() * ROAD, 6, 1);
      continue;
    }
    if (kind < 0.13) { // park
      c.fillStyle = o.park; c.fillRect(x0 + 4, y0 + 4, bs - 8, bs - 8);
      for (let i = 0; i < 9; i++) {
        const tx = x0 + 12 + r() * (bs - 24), ty = y0 + 12 + r() * (bs - 24), tr = 5 + r() * 5;
        c.fillStyle = 'rgba(0,0,0,0.25)'; c.beginPath(); c.arc(tx + 2, ty + 2, tr, 0, 7); c.fill();
        c.fillStyle = o.tree; c.beginPath(); c.arc(tx, ty, tr, 0, 7); c.fill();
        c.fillStyle = 'rgba(255,255,255,0.15)'; c.beginPath(); c.arc(tx - tr * 0.3, ty - tr * 0.3, tr * 0.45, 0, 7); c.fill();
      }
      continue;
    }
    if (kind < 0.22) { // parking lot
      c.fillStyle = '#5d5d60'; c.fillRect(x0 + 4, y0 + 4, bs - 8, bs - 8);
      c.fillStyle = '#d8d8d8';
      for (let i = 0; i < 8; i++) c.fillRect(x0 + 8 + i * 11, y0 + 8, 1, 16);
      for (let i = 0; i < 4; i++) { c.fillStyle = o.roofs[(r() * o.roofs.length) | 0]; c.fillRect(x0 + 10 + i * 22, y0 + 10, 7, 12); }
      continue;
    }
    // buildings: split block into 2x2 or 1x2 lots
    const split = r() < 0.5 ? 2 : 1;
    const cols = split, rows = 2;
    for (let i = 0; i < cols; i++) for (let j = 0; j < rows; j++) {
      const lw = (bs - 8) / cols, lh = (bs - 8) / rows;
      const x = x0 + 4 + i * lw + 2, y = y0 + 4 + j * lh + 2, w = lw - 4, h = lh - 4;
      const col = o.roofs[(r() * o.roofs.length) | 0];
      // drop shadow (fake height)
      c.fillStyle = 'rgba(0,0,0,0.35)'; c.fillRect(x + 4, y + 4, w, h);
      c.fillStyle = col; c.fillRect(x, y, w, h);
      c.fillStyle = 'rgba(255,255,255,0.22)'; c.fillRect(x, y, w, 2); c.fillRect(x, y, 2, h);
      c.fillStyle = 'rgba(0,0,0,0.25)'; c.fillRect(x, y + h - 2, w, 2); c.fillRect(x + w - 2, y, 2, h);
      // roof details
      const k = (r() * 3) | 0;
      for (let q = 0; q < k + 1; q++) {
        c.fillStyle = 'rgba(0,0,0,0.25)';
        const ax = x + 6 + r() * (w - 16), ay = y + 6 + r() * (h - 16);
        c.fillRect(ax, ay, 7, 5);
        c.fillStyle = 'rgba(255,255,255,0.2)'; c.fillRect(ax, ay, 7, 1);
      }
      if (o.neon && r() < 0.55) {
        const nc = o.neon[(r() * o.neon.length) | 0];
        c.save(); c.shadowColor = nc; c.shadowBlur = 8; c.fillStyle = nc;
        if (r() < 0.5) c.fillRect(x + 4, y + h / 2, w - 8, 2); else c.fillRect(x + w / 2, y + 4, 2, h - 8);
        c.restore();
      }
      if (o.night) { // lit windows on roof edges
        c.fillStyle = 'rgba(255,220,120,0.7)';
        for (let q = 0; q < 4; q++) if (r() < 0.6) c.fillRect(x + 3 + r() * (w - 6), y + 2 + r() * (h - 4), 2, 2);
      }
    }
  }
  // roads
  for (let k = 0; k < n; k++) {
    c.fillStyle = o.road; c.fillRect(k * ROAD, 0, RW, S); c.fillRect(0, k * ROAD, S, RW);
  }
  c.fillStyle = o.line;
  for (let k = 0; k < n; k++) {
    for (let y = 0; y < S; y += 16) if ((y % ROAD) > RW + 2 && (y % ROAD) < ROAD - 10) c.fillRect(k * ROAD + RW / 2 - 1, y, 2, 8);
    for (let x = 0; x < S; x += 16) if ((x % ROAD) > RW + 2 && (x % ROAD) < ROAD - 10) c.fillRect(x, k * ROAD + RW / 2 - 1, 8, 2);
  }
  // zebra crossings
  c.fillStyle = 'rgba(255,255,255,0.55)';
  for (let a = 0; a < n; a++) for (let b = 0; b < n; b++) {
    const x = a * ROAD, y = b * ROAD;
    for (let i = 0; i < 5; i++) { c.fillRect(x + RW + 2, y + 3 + i * 5, 5, 3); c.fillRect(x + 3 + i * 5, y + RW + 2, 3, 5); }
  }
  return cv;
}

// path along roads: list of [x,y] waypoints (map px); returns {x,y,ang} at distance d
function pathAt(pts, d) {
  let acc = 0;
  for (let i = 0; i < pts.length - 1; i++) {
    const [x0, y0] = pts[i], [x1, y1] = pts[i + 1];
    const L = Math.hypot(x1 - x0, y1 - y0);
    if (d <= acc + L || i === pts.length - 2) {
      const f = clamp((d - acc) / L, 0, 1.5);
      return { x: x0 + (x1 - x0) * f, y: y0 + (y1 - y0) * f, ang: Math.atan2(y1 - y0, x1 - x0) };
    }
    acc += L;
  }
}
// tiny top-down car (low-res px)
function carTop(c, x, y, ang, col, o = {}) {
  c.save(); c.translate(Math.round(x), Math.round(y)); c.rotate(ang);
  const L = o.L || 18, Wd = o.W || 10;
  c.fillStyle = 'rgba(0,0,0,0.35)'; c.fillRect(-L / 2 + 2, -Wd / 2 + 2, L, Wd);
  c.fillStyle = col; c.fillRect(-L / 2, -Wd / 2, L, Wd);
  c.fillStyle = 'rgba(0,0,0,0.55)'; c.fillRect(-L / 2 + 5, -Wd / 2 + 1, 7, Wd - 2); // windows/roof
  c.fillStyle = o.roof || col; c.fillRect(-L / 2 + 7, -Wd / 2 + 2, 3, Wd - 4);
  c.fillStyle = '#fff8c0'; c.fillRect(L / 2 - 1, -Wd / 2 + 1, 1, 2); c.fillRect(L / 2 - 1, Wd / 2 - 3, 1, 2);
  if (o.police) {
    c.fillStyle = o.flash ? '#ff2b2b' : '#2b5bff'; c.fillRect(-2, -Wd / 2 + 1, 2, Wd / 2 - 1);
    c.fillStyle = o.flash ? '#2b5bff' : '#ff2b2b'; c.fillRect(-2, 0, 2, Wd / 2 - 1);
  }
  c.restore();
  if (o.police && o.glow) {
    c.save(); c.globalCompositeOperation = 'lighter';
    glow(c, x, y, 26, o.flash ? '#ff2020' : '#2050ff', 0.55);
    c.restore();
  }
}

function pixelExplosion(c, x, y, p, seed) {
  if (p <= 0 || p >= 1) return;
  const r = rng(seed);
  const R = 6 + 26 * E.outCubic(p);
  c.save();
  c.globalAlpha = 1 - p * 0.7;
  const cols = ['#fff6b0', '#ffd23f', '#ff8a1f', '#e8421f', '#555'];
  for (let i = 0; i < 16; i++) {
    const a = r() * Math.PI * 2, d = r() * R;
    const ci = Math.min(4, Math.floor(p * 3 + r() * 2));
    c.fillStyle = cols[ci];
    const s = Math.max(2, Math.round((1 - p) * (4 + r() * 6)));
    c.fillRect(Math.round(x + Math.cos(a) * d - s / 2), Math.round(y + Math.sin(a) * d - s / 2), s, s);
  }
  c.restore();
}

function scanlines(c, a = 0.18, gap = 6) {
  c.fillStyle = `rgba(0,0,0,${a})`;
  for (let y = 0; y < H; y += gap) c.fillRect(0, y, W, 2);
}
function rgbGlitch(c, src, amt, t) {
  if (amt <= 0) return;
  const r = rng(Math.floor(t * 30) + 5);
  c.save();
  for (let i = 0; i < 9; i++) {
    const y = r() * H, h = 20 + r() * 120, dx = (r() - 0.5) * 140 * amt;
    c.drawImage(src, 0, y, W, h, dx, y, W, h);
  }
  c.globalCompositeOperation = 'lighter'; c.globalAlpha = 0.35 * amt;
  c.drawImage(src, 14 * amt, 0); c.drawImage(src, -14 * amt, 0);
  c.restore();
}

// =====================================================================
// GTA 1 (1997) — pixel top-down chase
// =====================================================================
SCENES.gta1 = (() => {
  const S = SEG.gta1;
  let map, low, lc, buf;
  const P = [[roadC(1) + 6, roadC(5) + 7], [roadC(4) + 7, roadC(5) + 7], [roadC(4) + 7, roadC(2) + 7], [roadC(8) + 7, roadC(2) + 7]];
  const cop1 = [[roadC(6) - 7, roadC(7)], [roadC(6) - 7, roadC(1)]];
  const cop2 = [[roadC(7), roadC(4) - 7], [roadC(0), roadC(4) - 7]];
  return {
    init() {
      map = cityMap({ seed: 11 });
      low = off(320, 180); lc = ctxOf(low); lc.imageSmoothingEnabled = false;
      buf = off(W, H);
    },
    draw(c, t, opt = {}) {
      const lt = t - S.start;
      const L1b = LINES.g1b, L1c = LINES.g1c;
      // world clock: freezes during "boring" line
      let wt = lt;
      const fz0 = L1b.start - S.start, fz1 = B.g1_bug - S.start;
      if (lt > fz0) wt = fz0 + Math.max(0, lt - fz1) * 1.0 + Math.min(lt - fz0, fz1 - fz0) * 0.0;
      const mad = t >= B.g1_mad;
      const speed = 62 + (mad ? 18 : 0);
      const pl = pathAt(P, wt * speed);
      const camX = pl.x, camY = pl.y;
      lc.fillStyle = '#000'; lc.fillRect(0, 0, 320, 180);
      const vx = camX - 160, vy = camY - 90;
      lc.drawImage(map, Math.round(vx), Math.round(vy), 320, 180, 0, 0, 320, 180);
      const flash = Math.floor(t * 8) % 2 === 0;
      // civilian traffic
      const civ = [[roadC(3) - 7, 'v', '#e0e0e0', 40], [roadC(2) - 7, 'h', '#3f7fd0', 55], [roadC(5) - 7, 'v', '#d04f9a', 30]];
      civ.forEach(([k, dir, col, sp], i) => {
        const d = (wt * sp + i * 300) % 1100;
        const x = dir === 'v' ? k : d, y = dir === 'v' ? 1100 - d : k;
        carTop(lc, x - vx, y - vy, dir === 'v' ? -Math.PI / 2 : 0, col);
      });
      // police
      const ram = [B.g1_ram, B.g1_ram + 0.5, B.g1_ram + 0.95, B.g1_born - 0.3];
      if (!mad) {
        const a = pathAt(cop1, (wt * 45) % 700), b = pathAt(cop2, (wt * 50 + 200) % 900);
        carTop(lc, a.x - vx, a.y - vy, a.ang, '#f2f2f2', { police: true, flash: false, roof: '#2a3c8f' });
        carTop(lc, b.x - vx, b.y - vy, b.ang, '#f2f2f2', { police: true, flash: false, roof: '#2a3c8f' });
      } else {
        const m = t - B.g1_mad;
        for (let i = 0; i < 4; i++) {
          const base = i * Math.PI * 0.5 + m * 1.7 + i;
          let dist = lerp(70, 26, clamp(m / 0.8)) + Math.sin(m * 5 + i * 2) * 6;
          ram.forEach(rt => { const q = t - rt; if (q > -0.12 && q < 0.25) dist = Math.min(dist, lerp(12, 26, Math.abs(q) / 0.2)); });
          const x = pl.x - vx + Math.cos(base) * dist * 1.3, y = pl.y - vy + Math.sin(base) * dist * 0.8;
          const ang = Math.atan2(pl.y - vy - y, pl.x - vx - x);
          carTop(lc, x, y, Math.round(ang / (Math.PI / 4)) * (Math.PI / 4), '#f2f2f2', { police: true, flash: (flash + i) % 2 === 0, glow: true, roof: '#2a3c8f' });
        }
      }
      // player
      carTop(lc, pl.x - vx, pl.y - vy, pl.ang, '#ffd23f', { roof: '#c23b22', L: 19, W: 11 });
      // explosions
      ram.forEach((rt, i) => pixelExplosion(lc, 160 + (i % 2 ? 14 : -12), 90 + (i % 3 - 1) * 9, (t - rt) / 0.6, 50 + i));
      // pixel captions inside the game world
      lc.save(); lc.textAlign = 'center'; lc.font = '14px Bowlby';
      if (!opt.clean && t > S.start + 1.25 && t < L1c.start) {
        const a = clamp((t - S.start - 1.25) * 4);
        lc.globalAlpha = a; lc.fillStyle = '#000'; lc.fillRect(70, 14, 180, 24);
        lc.fillStyle = '#ffd23f'; lc.fillText("RACE'N'CHASE", 160, 32);
        lc.font = '7px Bowlby'; lc.fillStyle = '#fff'; lc.fillText('PROJECT CODENAME  ·  DMA DESIGN', 160, 46);
      }
      if (!opt.clean && t > B.g1_born - 0.2) {
        const a = clamp((t - B.g1_born + 0.2) * 5);
        lc.globalAlpha = a;
        lc.fillStyle = 'rgba(0,0,0,0.75)'; lc.fillRect(40, 8, 240, 52);
        lc.font = '9px Bowlby'; lc.fillStyle = '#999'; lc.fillText("RACE'N'CHASE", 160, 22);
        lc.fillStyle = '#ff3b3b'; lc.fillRect(110, 18, 100 * clamp((t - B.g1_born + 0.2) * 4), 2);
        lc.font = '20px Bowlby'; lc.fillStyle = '#000'; lc.fillText('GRAND THEFT AUTO', 162, 49);
        lc.fillStyle = '#ffd23f'; lc.fillText('GRAND THEFT AUTO', 160, 47);
      }
      lc.restore();
      // upscale
      const bc = ctxOf(buf);
      bc.imageSmoothingEnabled = false;
      let sx = 0, sy = 0;
      ram.forEach(rt => { const q = t - rt; if (q > 0 && q < 0.35) { const k = (1 - q / 0.35) * 22; sx += (hash(Math.floor(t * 60)) - 0.5) * k; sy += (hash(Math.floor(t * 60) + 9) - 0.5) * k; } });
      bc.drawImage(low, sx - 12, sy - 12, W + 24, H + 24);
      // freeze: desaturate + zzz
      const frozen = t >= L1b.start && t < B.g1_bug;
      c.save();
      if (frozen) c.filter = 'grayscale(1) brightness(0.75)';
      c.drawImage(buf, 0, 0);
      c.restore();
      if (frozen && !opt.clean) {
        const q = t - L1b.start;
        c.save(); c.font = '90px Bowlby'; c.fillStyle = '#fff'; c.strokeStyle = '#000'; c.lineWidth = 10; c.lineJoin = 'round';
        for (let i = 0; i < 3; i++) {
          const p = (q * 0.9 + i * 0.33) % 1;
          c.globalAlpha = Math.sin(p * Math.PI);
          const x = 1010 + i * 60 + p * 80, y = 520 - p * 200 - i * 20;
          c.font = `${60 + i * 22}px Bowlby`;
          c.strokeText('Z', x, y); c.fillText('Z', x, y);
        }
        c.restore();
        c.save(); c.translate(W / 2, 330); c.rotate(-0.12);
        stamp(c, 'CANCELLED?', 0, 0, 120, '#ff2d2d', 0, (t - B.g1_cut) / 0.25, { font: FONT_LAT });
        c.restore();
      }
      // the BUG
      if (t > B.g1_bug - 0.05 && t < L1c.end + 0.3 && !opt.clean) {
        const q = t - B.g1_bug;
        const bx = lerp(-120, W + 120, clamp(q / 3.3)), by = 300 + Math.sin(q * 9) * 30;
        drawBug(c, bx, by, q);
      }
      // glitch at bug moment
      const g = t - B.g1_bug;
      if (g > -0.05 && g < 0.45) rgbGlitch(c, buf, 1 - g / 0.45, t);
      scanlines(c, 0.16, 6);
    },
  };
})();

function drawBug(c, x, y, q) {
  c.save(); c.translate(x, y);
  const s = 1.6;
  c.scale(s, s);
  // pixel bug sprite
  const px = (gx, gy, col) => { c.fillStyle = col; c.fillRect(gx * 8, gy * 8, 8, 8); };
  const legs = Math.floor(q * 12) % 2;
  const body = '#33ff66', dark = '#0c7a2c';
  [[-1, -2], [0, -2], [1, -2], [-2, -1], [-1, -1], [0, -1], [1, -1], [2, -1], [-2, 0], [-1, 0], [0, 0], [1, 0], [2, 0], [-2, 1], [-1, 1], [0, 1], [1, 1], [2, 1], [-1, 2], [0, 2], [1, 2]]
    .forEach(([a, b]) => px(a, b, body));
  [[3, -1], [3, 0], [3, 1]].forEach(([a, b]) => px(a, b, dark));
  px(4, -1, '#000'); px(4, 1, '#000');
  for (let i = -1; i <= 1; i++) { px(i, legs ? -3 : -4, dark); px(i, legs ? 3 : 4, dark); }
  px(5, -2, dark); px(5, 2, dark);
  px(-1, -1, '#b6ffca');
  c.restore();
  c.save(); c.font = '64px Bowlby'; c.fillStyle = '#33ff66'; c.strokeStyle = '#000'; c.lineWidth = 10; c.lineJoin = 'round';
  c.strokeText('BUG!', x - 40, y - 70); c.fillText('BUG!', x - 40, y - 70); c.restore();
}

// =====================================================================
// GTA 2 (1999) — neon retro-future top-down + respect
// =====================================================================
SCENES.gta2 = (() => {
  const S = SEG.gta2;
  let map, low, lc, zone;
  const GANG = [{ n: '绿帮', col: '#36e06b' }, { n: '红帮', col: '#ff3b5c' }, { n: '蓝帮', col: '#3bb8ff' }];
  return {
    init() {
      map = cityMap({ seed: 23, ground: '#1d2238', road: '#2a2b38', line: '#5ef3ff', walk: '#3a3f58', park: '#21483a', tree: '#13301f',
        water: '#14204a', roofs: ['#2d3354', '#3c2f55', '#25445a', '#4b3a5e', '#2b2b3d', '#3d4b6b'], neon: ['#ff3ea5', '#39f3ff', '#ffe14d', '#a26bff'], night: true });
      // gang turf tints
      const zc = ctxOf(map);
      [[0, 0, 520, 600, '#36e06b'], [520, 0, 640, 560, '#ff3b5c'], [0, 600, 1152, 560, '#3bb8ff']].forEach(([x, y, w, h, col]) => {
        zc.fillStyle = hexA(col, 0.13); zc.fillRect(x, y, w, h);
        zc.strokeStyle = hexA(col, 0.8); zc.lineWidth = 2; zc.setLineDash([6, 4]); zc.strokeRect(x + 2, y + 2, w - 4, h - 4); zc.setLineDash([]);
      });
      low = off(480, 270); lc = ctxOf(low); lc.imageSmoothingEnabled = false;
    },
    draw(c, t, opt = {}) {
      const lt = t - S.start;
      const camX = 420 + lt * 26, camY = 520 - lt * 16;
      const vx = camX - 240, vy = camY - 135;
      lc.drawImage(map, Math.round(vx), Math.round(vy), 480, 270, 0, 0, 480, 270);
      // cars & pedestrians
      for (let i = 0; i < 7; i++) {
        const k = 1 + (i % 6), sp = 40 + i * 9;
        const d = (lt * sp + i * 170) % 1150;
        const vertical = i % 2 === 0;
        const x = vertical ? roadC(k) + (i % 3 ? 7 : -7) : d, y = vertical ? d : roadC(k) + (i % 3 ? 7 : -7);
        carTop(lc, x - vx, y - vy, vertical ? Math.PI / 2 : 0, ['#ff3ea5', '#39f3ff', '#ffe14d', '#e8e8f0', '#a26bff'][i % 5], { L: 16, W: 9 });
      }
      // gang members (pixel dots)
      const r = rng(5);
      for (let i = 0; i < 40; i++) {
        const gx = r() * 1100, gy = r() * 1100;
        const gi = gy > 600 ? 2 : gx < 520 ? 0 : 1;
        const x = gx + Math.sin(lt * 2 + i) * 6 - vx, y = gy + Math.cos(lt * 1.7 + i) * 6 - vy;
        if (x < -5 || y < -5 || x > 485 || y > 275) continue;
        lc.fillStyle = GANG[gi].col; lc.fillRect(Math.round(x), Math.round(y), 3, 3);
        lc.fillStyle = '#000'; lc.fillRect(Math.round(x) + 1, Math.round(y) - 1, 1, 1);
        if (gi === 1 && t > B.g2_rival && !opt.clean && Math.floor(t * 4 + i) % 2 === 0) { lc.fillStyle = '#ff3b5c'; lc.fillRect(Math.round(x) + 1, Math.round(y) - 6, 1, 3); lc.fillRect(Math.round(x) + 1, Math.round(y) - 2, 1, 1); }
      }
      c.save(); c.imageSmoothingEnabled = false; c.drawImage(low, -8, -8, W + 16, H + 16); c.restore();
      // neon bloom
      c.save(); c.globalCompositeOperation = 'lighter'; c.globalAlpha = 0.18; c.filter = 'blur(14px)'; c.drawImage(low, -8, -8, W + 16, H + 16); c.restore();
      if (!opt.clean) {
        // Rockstar debut badge
        const pr = (t - B.g2_rockstar + 0.25) / 0.45, out = clamp((t - LINES.g2b.start) / 0.3);
        if (pr > 0 && out < 1) {
          c.save(); c.globalAlpha = 1 - out;
          const cx = 1470, cy = 400, s = E.outBack(clamp(pr));
          c.translate(cx, cy); c.scale(s, s); c.rotate((1 - s) * 0.6);
          c.save(); c.rotate(t * 0.4); c.globalCompositeOperation = 'lighter';
          for (let i = 0; i < 12; i++) { c.rotate(Math.PI / 6); c.fillStyle = 'rgba(255,214,60,0.10)'; c.beginPath(); c.moveTo(0, 0); c.lineTo(-40, -420); c.lineTo(40, -420); c.fill(); }
          c.restore();
          starPath(c, 0, 0, 150); c.fillStyle = '#ffd23f'; c.fill(); c.lineWidth = 14; c.strokeStyle = '#111'; c.lineJoin = 'round'; c.stroke();
          starPath(c, -8, -10, 96); c.fillStyle = 'rgba(255,255,255,0.35)'; c.fill();
          outlinedText(c, 'ROCKSTAR GAMES', 0, 250, { font: FONT_LAT, size: 92, fill: '#ffffff', lw: 0.14, track: 0.04 });
          outlinedText(c, '1998年成立 · GTA2 由它发行', 0, 320, { font: FONT_CN2, size: 44, fill: '#ffd23f', lw: 0.2, grad: false });
          c.restore();
        }
        // respect panel
        const pp = clamp((t - LINES.g2b.start + 0.1) / 0.35);
        if (pp > 0) {
          const x0 = lerp(W + 40, 1290, E.outCubic(pp)), y0 = 190;
          c.save();
          c.fillStyle = 'rgba(8,10,24,0.82)'; roundRect(c, x0, y0, 560, 400, 26); c.fill();
          c.strokeStyle = '#39f3ff'; c.lineWidth = 4; c.stroke();
          outlinedText(c, 'RESPECT', x0 + 280, y0 + 70, { font: FONT_LAT, size: 64, fill: '#39f3ff', lw: 0.08, shadow: 0, track: 0.12 });
          GANG.forEach((g, i) => {
            const y = y0 + 140 + i * 95;
            let v = [0.45, 0.6, 0.5][i];
            const up = E.outBack(clamp((t - B.g2_help) / 0.45)), down = E.outCubic(clamp((t - B.g2_rival) / 0.45));
            if (i === 0) v += 0.42 * up;
            if (i === 1) v -= 0.5 * down;
            c.fillStyle = g.col; c.beginPath(); c.arc(x0 + 58, y + 2, 22, 0, 7); c.fill();
            c.lineWidth = 4; c.strokeStyle = '#000'; c.stroke();
            outlinedText(c, g.n, x0 + 140, y + 16, { font: FONT_CN, size: 46, fill: '#fff', lw: 0.14, shadow: 0, grad: false });
            c.fillStyle = '#1b1f33'; roundRect(c, x0 + 205, y - 16, 320, 34, 10); c.fill();
            c.fillStyle = g.col; roundRect(c, x0 + 205, y - 16, Math.max(12, 320 * clamp(v)), 34, 10); c.fill();
            c.strokeStyle = '#000'; c.lineWidth = 3; roundRect(c, x0 + 205, y - 16, 320, 34, 10); c.stroke();
            if (i === 0 && t > B.g2_help) {
              const q = t - B.g2_help; c.globalAlpha = clamp(1.4 - q);
              outlinedText(c, '+ 好感', x0 + 470, y - 30 - q * 30, { font: FONT_CN, size: 44, fill: '#36e06b', lw: 0.16, grad: false });
              c.globalAlpha = 1;
            }
            if (i === 1 && t > B.g2_rival) {
              const q = t - B.g2_rival; c.globalAlpha = clamp(1.4 - q);
              outlinedText(c, '− 结仇', x0 + 470, y - 30 - q * 30, { font: FONT_CN, size: 44, fill: '#ff3b5c', lw: 0.16, grad: false });
              c.globalAlpha = 1;
              if (q < 0.25) { c.fillStyle = `rgba(255,40,70,${0.25 * (1 - q / 0.25)})`; c.fillRect(0, 0, W, H); }
            }
          });
          c.restore();
        }
      }
      scanlines(c, 0.12, 5);
    },
  };
})();

// =====================================================================
// GTA III (2001) — 2D -> 3D tilt, rainy night city, 9/11 delay, police repaint
// =====================================================================
SCENES.gta3 = (() => {
  const S = SEG.gta3;
  let map, far, mid, near, sky, cityBuf;
  return {
    init() {
      map = cityMap({ seed: 31, ground: '#59615a', road: '#3e3f44', line: '#d9cf6a', walk: '#8b8a84', roofs: ['#7d7368', '#6f7d88', '#8f8170', '#5f6670', '#a0876a', '#6c5f58'], park: '#4f7a45', tree: '#2c5228', water: '#2c4a78' });
      sky = off(W, H); const sc = ctxOf(sky);
      sc.fillStyle = vgrad(sc, 0, H, [[0, '#070d26'], [0.45, '#1b2b62'], [0.68, '#4a4f8a'], [0.8, '#8a6a8a'], [1, '#2a2240']]); sc.fillRect(0, 0, W, H);
      // moon + clouds
      glow(sc, 1500, 210, 300, '#b8c8ff', 0.5);
      sc.fillStyle = '#dfe6ff'; sc.beginPath(); sc.arc(1500, 210, 52, 0, 7); sc.fill();
      const rr = rng(4);
      for (let i = 0; i < 26; i++) { sc.fillStyle = `rgba(20,26,58,${0.35 + rr() * 0.4})`; sc.beginPath(); sc.ellipse(rr() * W, 330 + rr() * 160, 160 + rr() * 260, 26 + rr() * 30, 0, 0, 7); sc.fill(); }
      halftone(sc, 0, 0, W, 520, 'rgba(120,140,255,0.10)', 16, 0.9, 0, true);
      far = skyline({ w: 2600, h: 900, seed: 5, baseY: 880, minH: 160, maxH: 520, color: '#1c2550', win: '#7f93d8', winProb: 0.25, winSize: [5, 7], spires: 0.25 });
      mid = skyline({ w: 2600, h: 1000, seed: 9, baseY: 900, minH: 200, maxH: 620, minW: 90, maxW: 200, color: '#121838', win: '#ffd27a', winProb: 0.32, winSize: [7, 10], spires: 0.18, edge: '#2c3a78' });
      near = skyline({ w: 2800, h: 1080, seed: 12, baseY: 1080, minH: 480, maxH: 760, minW: 180, maxW: 300, color: '#090c1c', win: '#ffcf6b', winProb: 0.3, winSize: [10, 14], spires: 0.05, edge: '#2c3a80' });
      cityBuf = off(W, H);
    },
    mode7(c, pitch, camX, camY, h) {
      // pitch: 90deg = top-down, smaller = more perspective
      const f = 900, th = pitch * Math.PI / 180;
      c.fillStyle = vgrad(c, 0, H, [[0, '#0a0f26'], [0.5, '#2a3566'], [1, '#2a3566']]);
      c.fillRect(0, 0, W, H);
      for (let y = 0; y < H; y += 2) {
        const v = (y - H / 2) / f;
        const den = Math.sin(th) + v * Math.cos(th);
        if (den <= 0.02) continue;
        const s = h / den;
        const z = s * (Math.cos(th) - v * Math.sin(th));
        const wpp = s / f; // world px per screen px
        const srcW = W * wpp;
        const mx = camX - srcW / 2, my = camY - z;
        const fog = clamp((s - h) / (h * 6));
        c.drawImage(map, mx, my, srcW, Math.max(1, wpp * 2), 0, y, W, 2);
        if (fog > 0) { c.fillStyle = `rgba(26,34,80,${fog * 0.85})`; c.fillRect(0, y, W, 2); }
      }
    },
    city(c, t, opt) {
      const lt = t - S.start;
      const k = clamp((t - B.g3_3d) / 7);
      const zoom = 1.04 + k * 0.06;
      c.save();
      c.translate(W / 2, H / 2); c.scale(zoom, zoom); c.translate(-W / 2, -H / 2);
      c.drawImage(sky, 0, 0);
      // searchlights
      c.save(); c.globalCompositeOperation = 'lighter';
      [[520, 0.35, 0.9], [1380, -0.3, 1.3]].forEach(([x, a0, sp]) => {
        const a = a0 + Math.sin(t * 0.6 * sp) * 0.35;
        const g = c.createLinearGradient(x, 720, x + Math.sin(a) * 900, 720 - Math.cos(a) * 900);
        g.addColorStop(0, 'rgba(160,190,255,0.22)'); g.addColorStop(1, 'rgba(160,190,255,0)');
        c.fillStyle = g; c.beginPath(); c.moveTo(x - 6, 720);
        c.lineTo(x + Math.sin(a - 0.06) * 1000, 720 - Math.cos(a - 0.06) * 1000);
        c.lineTo(x + Math.sin(a + 0.06) * 1000, 720 - Math.cos(a + 0.06) * 1000); c.lineTo(x + 6, 720); c.fill();
      });
      c.restore();
      c.drawImage(far, -200 - lt * 6, -150);
      c.drawImage(mid, -300 - lt * 12, -170);
      // river with light reflections
      c.fillStyle = vgrad(c, 728, 860, [[0, '#101a3e'], [1, '#070b1c']]); c.fillRect(0, 728, W, 140);
      for (let i = 0; i < 70; i++) { const x = (hash(i) * W * 1.2 - lt * 12) % W; const y = 735 + hash(i + 3) * 120; c.fillStyle = `rgba(255,${190 + hash(i + 9) * 50 | 0},120,${0.12 + 0.3 * hash(i + 7) * (0.6 + 0.4 * Math.sin(t * 3 + i))})`; c.fillRect(x, y, 20 + hash(i + 2) * 70, 2.5); }
      // suspension bridge across the river
      c.save(); c.translate(-lt * 16, 0);
      const deckY = 700;
      c.fillStyle = '#0b1230'; c.fillRect(-200, deckY, W + 600, 18);
      [640, 1560].forEach(x => { c.fillStyle = '#1b2660'; c.fillRect(x - 18, 400, 36, 330); c.fillRect(x - 30, 430, 60, 14); c.fillRect(x - 30, 520, 60, 12); });
      c.strokeStyle = '#4a5cb0'; c.lineWidth = 5;
      c.beginPath(); c.moveTo(-200, 690); c.quadraticCurveTo(220, 520, 640, 404); c.quadraticCurveTo(1100, 700, 1560, 404); c.quadraticCurveTo(1900, 520, 2400, 690); c.stroke();
      c.lineWidth = 2; c.strokeStyle = 'rgba(90,110,200,0.7)';
      for (let x = -180; x < 2400; x += 34) { const yTop = x < 640 ? lerp(690, 404, Math.pow((x + 200) / 840, 2)) : x < 1560 ? 404 + 296 * (1 - Math.pow((x - 1100) / 460, 2)) : lerp(404, 690, Math.pow((x - 1560) / 840, 0.5)); c.beginPath(); c.moveTo(x, deckY); c.lineTo(x, Math.min(deckY, yTop)); c.stroke(); }
      for (let x = -180; x < 2400; x += 40) { c.fillStyle = '#ffe9a0'; c.fillRect(x, deckY - 3, 4, 4); }
      // traffic light streaks on the deck
      for (let i = 0; i < 14; i++) { const x = ((t * 260 + i * 190) % (W + 700)) - 300; c.fillStyle = i % 2 ? '#fff4c8' : '#ff3a3a'; c.fillRect(x, deckY - 7, 26, 4); }
      c.restore();
      // foreground framing buildings (left / right)
      c.drawImage(near, 0, 0, 520, 1080, -60 - lt * 20, 40, 520, 1080);
      c.drawImage(near, 900, 0, 520, 1080, W - 420 + lt * 6, 0, 520, 1080);
      // street + taxi
      c.fillStyle = '#06070d'; c.fillRect(0, 868, W, 220);
      c.fillStyle = 'rgba(255,200,110,0.16)'; c.fillRect(0, 868, W, 5);
      [300, 960, 1620].forEach(x => { c.fillStyle = '#111522'; c.fillRect(x - 5, 690, 10, 180); c.fillRect(x - 5, 690, 60, 8); c.save(); c.globalCompositeOperation = 'lighter'; glow(c, x + 52, 700, 150, '#ffc86b', 0.55); c.restore(); });
      const tx = lerp(-400, W + 400, ((lt * 0.3 + 0.35) % 1.25));
      carSide(c, tx, 960, 0.8, { body: '#f5c518', kind: 'taxi', head: true, tail: true, wheelRot: lt * 12, stripe: '#111', text: 'TAXI' });
      c.restore();
      // rain
      c.save(); c.strokeStyle = 'rgba(170,190,255,0.35)'; c.lineWidth = 2;
      c.beginPath();
      for (let i = 0; i < 260; i++) {
        const x = (hash(i) * (W + 200) + t * 260) % (W + 200) - 100;
        const y = (hash(i + 999) * H + t * 1500 * (0.8 + hash(i + 5) * 0.4)) % H;
        c.moveTo(x, y); c.lineTo(x - 10, y + 38);
      }
      c.stroke(); c.restore();
      // mini radar (open world hint)
      if (!opt.clean) {
        const rp = clamp((t - LINES.g3b.start + 0.1) / 0.35) * (1 - clamp((t - LINES.g3c.start + 0.3) / 0.3));
        if (rp > 0) {
          const rx = 210, ry = 760, R = 150 * E.outBack(rp);
          c.save(); c.globalAlpha = clamp(rp * 2);
          c.beginPath(); c.arc(rx, ry, R, 0, 7); c.fillStyle = 'rgba(10,20,40,0.85)'; c.fill();
          c.save(); c.clip();
          c.globalAlpha = 0.9; c.drawImage(map, 200 + t * 20, 300, 400, 400, rx - R, ry - R, R * 2, R * 2);
          c.fillStyle = 'rgba(0,30,60,0.35)'; c.fillRect(rx - R, ry - R, 2 * R, 2 * R);
          const sweep = t * 2.4;
          c.globalCompositeOperation = 'lighter';
          c.fillStyle = 'rgba(120,255,160,0.25)'; c.beginPath(); c.moveTo(rx, ry); c.arc(rx, ry, R, sweep, sweep + 0.6); c.fill();
          c.restore();
          c.lineWidth = 8; c.strokeStyle = '#000'; c.beginPath(); c.arc(rx, ry, R, 0, 7); c.stroke();
          c.lineWidth = 3; c.strokeStyle = '#f5c518'; c.stroke();
          [[40, -60, '#ff4d4d'], [-70, 20, '#39f3ff'], [60, 70, '#ffd23f'], [-20, -90, '#ff7bd5']].forEach(([dx, dy, col], i) => {
            c.fillStyle = col; c.strokeStyle = '#000'; c.lineWidth = 3;
            const s = 1 + 0.25 * Math.sin(t * 6 + i);
            c.fillRect(rx + dx * R / 150 - 9 * s, ry + dy * R / 150 - 9 * s, 18 * s, 18 * s); c.strokeRect(rx + dx * R / 150 - 9 * s, ry + dy * R / 150 - 9 * s, 18 * s, 18 * s);
          });
          starPath(c, rx, ry, 14); c.fillStyle = '#fff'; c.fill();
          c.restore();
        }
      }
    },
    draw(c, t, opt = {}) {
      const L3c = LINES.g3c, L3d = LINES.g3d;
      const tiltEnd = B.g3_3d;
      if (t < tiltEnd + 0.4 && !opt.city) {
        const p = E.inOutCubic(inv(S.start + 0.6, tiltEnd, t));
        const pitch = lerp(90, 28, p);
        const lt = t - S.start;
        this.mode7(c, pitch, 560 + lt * 20, 640 - lt * 70, lerp(560, 120, p));
        if (t > tiltEnd - 0.05) { // flash into illustrated 3D
          const q = (t - tiltEnd + 0.05) / 0.45;
          const cb = ctxOf(cityBuf); this.city(cb, t, opt);
          c.save(); c.globalAlpha = clamp(q * 1.6); c.drawImage(cityBuf, 0, 0); c.restore();
          c.fillStyle = `rgba(255,255,255,${0.8 * (1 - clamp(q * 2))})`; c.fillRect(0, 0, W, H);
        }
        // big "2D -> 3D" label
        if (!opt.clean) {
          const a = clamp((t - S.start - 1.1) * 3) * (1 - clamp((t - tiltEnd) * 3));
          if (a > 0) {
            c.save(); c.globalAlpha = a;
            const lab = p < 0.55 ? '2D' : '3D';
            outlinedText(c, lab, W - 300, 330, { font: FONT_NUM, size: 220, fill: p < 0.55 ? '#cfcfcf' : '#f5c518', lw: 0.1 });
            c.restore();
          }
        }
        return;
      }
      if (t < L3c.start - 0.15 || opt.city) { this.city(c, t, opt); return; }
      // ---- 9/11: calm, desaturated ----
      const q = t - (L3c.start - 0.15);
      const cb = ctxOf(cityBuf); this.city(cb, t, { clean: true });
      c.save(); c.filter = 'grayscale(1) brightness(0.35)'; c.drawImage(cityBuf, 0, 0); c.restore();
      c.fillStyle = `rgba(0,0,0,${0.35})`; c.fillRect(0, 0, W, H);
      const policeStart = B.g3_delay + 0.75;
      // calendar
      if (t < policeStart + 0.4) {
        const out = clamp((t - policeStart) / 0.4);
        const cx = W / 2, cy = 380, s = lerp(0.92, 1, E.outCubic(clamp(q / 0.6)));
        c.save(); c.globalAlpha = clamp(q * 2.5) * (1 - out); c.translate(cx, cy); c.scale(s, s);
        c.fillStyle = '#e9e6df'; roundRect(c, -230, -240, 460, 480, 18); c.fill();
        c.fillStyle = '#5a5a5a'; roundRect(c, -230, -240, 460, 120, 18); c.fill(); c.fillRect(-230, -150, 460, 30);
        c.fillStyle = '#2a2a2a'; for (let i = 0; i < 2; i++) { c.beginPath(); c.arc(-120 + i * 240, -240, 16, 0, 7); c.fill(); }
        c.fillStyle = '#fff'; c.font = `64px ${FONT_NUM}`; c.textAlign = 'center'; c.fillText('2001', 0, -150);
        c.fillStyle = '#333'; c.font = `260px ${FONT_NUM}`; c.fillText('11', 0, 140);
        c.font = `64px ${FONT_CN}`; c.fillText('9 月', 0, 215);
        c.restore();
        // "delayed" stamp
        if (t > B.g3_delay - 0.05) {
          c.save(); c.globalAlpha = 1 - out;
          stamp(c, '发售延期', W / 2 + 170, 470, 110, '#e02828', -0.18, (t - B.g3_delay + 0.05) / 0.22);
          c.restore();
        }
      }
      // police car repaint
      if (t > policeStart) {
        const pin = E.outCubic(clamp((t - policeStart) / 0.45));
        const x = lerp(-500, W / 2 - 20, pin);
        const wipe = clamp((t - B.g3_bw + 0.35) / 0.55);
        const flash = Math.floor(t * 6) % 2 === 0;
        const drawCar = (blue) => carSide(c, x, 660, 1.5, { kind: 'police', body: blue ? '#f4f6fb' : '#121214', doors: blue ? null : '#f2f2f2', stripe: blue ? '#2a55c9' : null, stripeH: 26,
          win: '#11141c', head: true, wheelRot: -pin * 10, flash, barL: '#e33', barR: blue ? '#36f' : '#e33', text: 'POLICE', textCol: blue ? '#2a55c9' : '#141414' });
        // spotlight + road
        c.save(); c.globalCompositeOperation = 'lighter'; glow(c, W / 2, 560, 700, '#8aa0d0', 0.35); c.restore();
        c.fillStyle = '#16171c'; c.fillRect(0, 680, W, 400);
        c.fillStyle = '#c9b443'; for (let i = 0; i < 12; i++) c.fillRect(i * 200 - ((t * 400) % 200) * (1 - pin), 760, 110, 10);
        c.save(); c.beginPath(); c.rect(lerp(-200, W + 200, wipe), 0, W + 400, H); c.clip(); drawCar(true); c.restore();
        c.save(); c.beginPath(); c.rect(-400, 0, lerp(-200, W + 200, wipe) + 400, H); c.clip(); drawCar(false); c.restore();
        if (wipe > 0 && wipe < 1) { // paint roller band
          const bx = lerp(-200, W + 200, wipe);
          c.fillStyle = 'rgba(0,0,0,0.85)'; c.fillRect(bx - 18, 300, 36, 420);
          c.fillStyle = '#ffd23f'; c.fillRect(bx - 22, 280, 44, 28);
        }
        if (!opt.clean) {
          const lb = clamp((t - policeStart - 0.2) * 4);
          c.save(); c.globalAlpha = lb;
          outlinedText(c, wipe < 0.5 ? '原版：蓝白涂装' : '发售版：黑白涂装', W / 2, 250, { font: FONT_CN, size: 70, fill: wipe < 0.5 ? '#7fb2ff' : '#ffffff', lw: 0.16 });
          c.restore();
        }
      }
    },
  };
})();

// =====================================================================
// VICE CITY (2002) — VHS rewind to 1986, neon sunset, first speaking hero
// =====================================================================
SCENES.vc = (() => {
  const S = SEG.vc;
  let bg, city, buf;
  return {
    init() {
      bg = off(W, H); const c = ctxOf(bg);
      c.fillStyle = vgrad(c, 0, 700, [[0, '#2a0b4f'], [0.35, '#8a1f86'], [0.7, '#ff4f8b'], [1, '#ffb36b']]); c.fillRect(0, 0, W, 700);
      // retro sun with stripes
      c.save();
      const g = c.createLinearGradient(0, 260, 0, 690); g.addColorStop(0, '#fff07a'); g.addColorStop(0.5, '#ffb14a'); g.addColorStop(1, '#ff4f8b');
      c.beginPath(); c.arc(W / 2, 600, 300, Math.PI, 0); c.closePath(); c.fillStyle = g; c.fill();
      c.globalCompositeOperation = 'destination-out';
      for (let i = 0; i < 7; i++) { const y = 470 + i * 26; c.fillRect(0, y, W, 4 + i * 2.2); }
      c.restore();
      glow(c, W / 2, 600, 520, '#ff7ab8', 0.35);
      // sea
      c.fillStyle = vgrad(c, 690, H, [[0, '#ff6aa0'], [0.25, '#7a2a8e'], [1, '#1a0b3a']]); c.fillRect(0, 690, W, H - 690);
      for (let i = 0; i < 46; i++) { const y = 700 + i * i * 0.22; c.fillStyle = `rgba(255,214,140,${0.55 - i * 0.011})`; const w = 600 - i * 9; c.fillRect(W / 2 - w / 2 + Math.sin(i) * 20, y, w, 3); }
      halftone(c, 0, 0, W, 420, 'rgba(255,255,255,0.07)', 18, 1, 0, true);
      city = off(W, 700); const cc = ctxOf(city);
      const sk = skyline({ w: W, h: 700, seed: 41, baseY: 700, minH: 60, maxH: 260, minW: 50, maxW: 140, color: '#3b1050', win: '#ff9ad5', winProb: 0.22, winSize: [5, 7], spires: 0.1 });
      cc.drawImage(sk, 0, 0);
      buf = off(W, H);
    },
    scene(c, t, opt) {
      const lt = t - S.start;
      const z = 1.03 + lt * 0.006;
      c.save(); c.translate(W / 2, H / 2); c.scale(z, z); c.translate(-W / 2, -H / 2);
      c.drawImage(bg, 0, 0);
      c.drawImage(city, -lt * 8, -10);
      // art deco hotel (left)
      c.save(); c.translate(-lt * 18, 0);
      c.fillStyle = '#ffd0e6'; c.fillRect(120, 380, 520, 520);
      c.fillStyle = '#ffb6d6'; c.fillRect(120, 380, 520, 40); c.fillRect(300, 300, 160, 90);
      c.fillStyle = '#78e6e0'; for (let r = 0; r < 6; r++) for (let k = 0; k < 6; k++) c.fillRect(150 + k * 80, 450 + r * 70, 50, 34);
      c.strokeStyle = '#111'; c.lineWidth = 6; c.strokeRect(120, 380, 520, 520); c.strokeRect(300, 300, 160, 90);
      c.save(); c.shadowColor = '#38f2e8'; c.shadowBlur = 30; c.strokeStyle = '#38f2e8'; c.lineWidth = 6;
      c.beginPath(); c.moveTo(130, 430); c.lineTo(630, 430); c.stroke();
      c.font = '80px Bowlby'; c.fillStyle = '#ff5fd2'; c.shadowColor = '#ff5fd2'; c.textAlign = 'center';
      const blink = Math.sin(t * 9) > -0.6 ? 1 : 0.35;
      c.globalAlpha = blink; c.fillText('OCEAN', 380, 370); c.restore();
      c.restore();
      // road + sports car
      c.fillStyle = '#1b0a2c'; c.fillRect(0, 930, W, 160);
      c.fillStyle = '#ff5fd2'; c.fillRect(0, 930, W, 5);
      const cx = lerp(W + 500, -500, ((lt * 0.24 + 0.15) % 1.25));
      carSide(c, cx, 1035, 0.95, { body: '#f6f6f6', kind: 'sports', head: true, tail: true, dir: -1, wheelRot: -lt * 14, stripe: '#ff5fd2', win: '#2a1b3d' });
      // palms foreground
      palm(c, 1720, 1100, 760, -0.25, Math.sin(t * 1.2) * 0.6, '#1a0626', null);
      palm(c, 1520, 1100, 560, -0.12, Math.sin(t * 1.4 + 1) * 0.6, '#24082f', null);
      palm(c, 60, 1100, 640, 0.18, Math.sin(t * 1.1 + 2) * 0.6, '#1a0626', null);
      // hero (speaking) silhouette
      const hp = E.outCubic(clamp((t - LINES.vcb.start + 0.15) / 0.5));
      if (hp > 0 && !opt.clean) {
        c.save(); c.globalAlpha = hp;
        person(c, 1180 + (1 - hp) * 120, 1080, 620, { col: '#14061d', rim: '#38f2e8', shirt: '#1f7f86', floral: '#ff9ad5', rimSide: -1, pose: 'hips' });
        // floral dots on shirt
        c.restore();
      }
      c.restore();
    },
    draw(c, t, opt = {}) {
      const rewindEnd = B.vc_80s;
      const bc = ctxOf(buf);
      this.scene(bc, t, opt);
      if (t < rewindEnd + 0.1 && !opt.clean) {
        const p = inv(S.start, rewindEnd, t);
        c.save(); c.filter = `saturate(${lerp(0.3, 1, p)}) contrast(1.1)`; c.drawImage(buf, 0, 0); c.restore();
        // VHS tracking bands
        const r = rng(Math.floor(t * 24));
        for (let i = 0; i < 6; i++) {
          const y = r() * H, h = 6 + r() * 40;
          c.drawImage(buf, 0, y, W, h, (r() - 0.5) * 80, y, W, h);
          c.fillStyle = `rgba(255,255,255,${0.08 + r() * 0.12})`; c.fillRect(0, y, W, 2);
        }
        const band = (t * 900) % (H + 200) - 100;
        c.fillStyle = 'rgba(255,255,255,0.10)'; c.fillRect(0, band, W, 60);
        // REWIND HUD
        c.save();
        c.font = '86px Bebas'; c.fillStyle = '#fff'; c.shadowColor = '#000'; c.shadowBlur = 0; c.shadowOffsetX = 5; c.shadowOffsetY = 5;
        const y = Math.round(lerp(2002, 1986, E.inOutCubic(clamp(p * 1.05))));
        if (Math.floor(t * 3) % 2 === 0 || p > 0.9) c.fillText(p > 0.97 ? '▶ PLAY' : '◀◀ REWIND', 1430, 190);
        c.font = '150px Bebas'; c.fillText(String(y), 1430, 330);
        c.font = '48px Smiley'; c.fillText('游戏背景年代', 1430, 395);
        c.restore();
      } else {
        c.drawImage(buf, 0, 0);
        if (!opt.clean) {
          // year tag stays small
          const a = clamp((t - rewindEnd - 0.1) * 3) * (1 - clamp((t - LINES.vcb.start) * 3));
          if (a > 0) { c.save(); c.globalAlpha = a; outlinedText(c, '1986', 1560, 330, { font: FONT_LAT, size: 150, fill: '#ff5fd2', lw: 0.08 }); c.restore(); }
        }
      }
      if (!opt.clean && t > LINES.vcb.start) {
        // speech bubble waveform
        const q = t - LINES.vcb.start;
        const bp = E.outBack(clamp(q / 0.35));
        const bx = 860, by = 420;
        c.save(); c.translate(bx, by); c.scale(bp, bp);
        c.fillStyle = '#fff'; c.strokeStyle = '#111'; c.lineWidth = 8;
        roundRect(c, -230, -95, 460, 170, 40); c.fill(); c.stroke();
        c.beginPath(); c.moveTo(140, 70); c.lineTo(230, 170); c.lineTo(60, 74); c.closePath(); c.fill(); c.stroke();
        c.fillStyle = '#fff'; c.fillRect(70, 62, 80, 14);
        c.fillStyle = '#ff2d8a';
        for (let i = 0; i < 17; i++) {
          const a = Math.abs(Math.sin(t * 13 + i * 0.9) * Math.sin(t * 5.3 + i * 0.37));
          const h = 14 + a * 90 * (q < 3.6 ? 1 : 0.2);
          roundRect(c, -200 + i * 24, -10 - h / 2, 14, h, 7); c.fill();
        }
        c.restore();
        if (t > B.vc_liotta - 0.1) {
          const lp = E.outCubic(clamp((t - B.vc_liotta + 0.1) / 0.35));
          c.save(); c.globalAlpha = lp; c.translate(lerp(-80, 0, lp), 0);
          c.fillStyle = '#111'; c.fillRect(250, 595, 660, 108);
          c.fillStyle = '#ff5fd2'; c.fillRect(250, 595, 14, 108);
          outlinedText(c, '配音：雷·利奥塔', 290, 660, { font: FONT_CN, size: 56, fill: '#fff', lw: 0, shadow: 0, align: 'left', grad: false });
          outlinedText(c, 'RAY LIOTTA ·《好家伙》主演', 290, 693, { font: FONT_CN2, size: 28, fill: '#38f2e8', lw: 0, shadow: 0, align: 'left', grad: false });
          c.restore();
        }
      }
    },
  };
})();

// =====================================================================
// SAN ANDREAS (2004) — three cities, CJ gets fat, Hot Coffee, PS2 king
// =====================================================================
SCENES.sa = (() => {
  const S = SEG.sa;
  let pLS, pSF, pLV, buf;
  function panel(kind) {
    const cv = off(700, H), c = ctxOf(cv);
    if (kind === 'LS') {
      c.fillStyle = vgrad(c, 0, H, [[0, '#ff8a3d'], [0.5, '#ffc46b'], [0.75, '#ffe3a1'], [1, '#e7a35a']]); c.fillRect(0, 0, 700, H);
      glow(c, 350, 560, 380, '#fff3c0', 0.6);
      c.fillStyle = '#b4583a'; c.beginPath(); c.moveTo(0, 640); c.quadraticCurveTo(200, 520, 420, 620); c.quadraticCurveTo(560, 560, 700, 640); c.lineTo(700, H); c.lineTo(0, H); c.fill();
      c.drawImage(skyline({ w: 700, h: 760, seed: 51, baseY: 760, minH: 60, maxH: 260, color: '#7a3424', win: '#ffd27a', winProb: 0.15 }), 0, 0);
      c.fillStyle = '#3d1a12'; c.fillRect(0, 860, 700, 220);
      halftone(c, 0, 0, 700, 500, 'rgba(255,255,255,0.10)', 16, 1, 0);
    } else if (kind === 'SF') {
      c.fillStyle = vgrad(c, 0, H, [[0, '#7fa6c7'], [0.6, '#c4d6e2'], [1, '#9db4c4']]); c.fillRect(0, 0, 700, H);
      c.fillStyle = '#6d8aa0'; c.beginPath(); c.moveTo(0, 700); c.quadraticCurveTo(160, 420, 350, 560); c.quadraticCurveTo(520, 380, 700, 600); c.lineTo(700, H); c.lineTo(0, H); c.fill();
      const r = rng(8);
      for (let i = 0; i < 60; i++) { const x = r() * 700, y = 520 + r() * 260; c.fillStyle = ['#e8e1d4', '#d9cbb2', '#f1efe8'][i % 3]; c.fillRect(x, y, 26, 18); c.fillStyle = '#5d6b78'; c.fillRect(x, y - 6, 26, 6); }
      // red bridge
      c.strokeStyle = '#c8452f'; c.fillStyle = '#c8452f';
      c.fillRect(140, 380, 26, 460); c.fillRect(520, 380, 26, 460);
      c.lineWidth = 8; c.beginPath(); c.moveTo(-40, 760); c.quadraticCurveTo(153, 430, 340, 720); c.quadraticCurveTo(533, 430, 740, 760); c.stroke();
      c.fillRect(0, 780, 700, 20);
      c.lineWidth = 3; for (let x = 20; x < 700; x += 30) { c.beginPath(); c.moveTo(x, 780); c.lineTo(x, 780 - 220 * Math.pow(Math.abs(((x % 380) - 190) / 190), 2) - 30); c.stroke(); }
      c.fillStyle = '#4d6b85'; c.fillRect(0, 800, 700, 280);
    } else {
      c.fillStyle = vgrad(c, 0, H, [[0, '#08051a'], [0.6, '#2a0d47'], [1, '#481a5c']]); c.fillRect(0, 0, 700, H);
      const r = rng(9);
      for (let i = 0; i < 90; i++) { c.fillStyle = `rgba(255,255,255,${r()})`; c.fillRect(r() * 700, r() * 500, 2, 2); }
      c.drawImage(skyline({ w: 700, h: 900, seed: 77, baseY: 900, minH: 200, maxH: 540, minW: 80, maxW: 170, color: '#160a2a', win: '#ffcf4d', winProb: 0.45, spires: 0.3 }), 0, 0);
      c.fillStyle = '#0b0614'; c.fillRect(0, 900, 700, 180);
    }
    return cv;
  }
  return {
    init() { pLS = panel('LS'); pSF = panel('SF'); pLV = panel('LV'); buf = off(W, H); },
    panels(c, t, opt) {
      const lt = t - S.start;
      c.fillStyle = '#111'; c.fillRect(0, 0, W, H);
      const P = [[pLS, 'LOS SANTOS', '#ffb020'], [pSF, 'SAN FIERRO', '#c8452f'], [pLV, 'LAS VENTURAS', '#ff5fd2']];
      P.forEach(([img, name, col], i) => {
        const p = E.outCubic(clamp((lt - 0.05 - i * 0.18) / 0.55));
        const x0 = i * 640 - 30;
        c.save();
        c.beginPath(); c.moveTo(x0 + 40, 0); c.lineTo(x0 + 680, 0); c.lineTo(x0 + 640, H); c.lineTo(x0, H); c.closePath();
        c.clip();
        c.translate(0, (1 - p) * (i % 2 ? -H : H));
        c.drawImage(img, x0 - 10 - lt * 6, 0);
        // dynamic bits
        if (i === 0) { // lowrider bounce
          const bounce = Math.abs(Math.sin(t * 7)) * 26;
          carSide(c, x0 + 330, 1000 - bounce, 0.72, { body: '#2fa65a', kind: 'lowrider', stripe: '#ffd23f', rim: '#ffd23f', wheelRot: 0, win: '#1b1b2a' });
          palm(c, x0 + 90, 1090, 520, 0.1, Math.sin(t) * 0.5, '#2a120c', null);
          palm(c, x0 + 600, 1090, 430, -0.1, Math.sin(t + 1) * 0.5, '#2a120c', null);
        } else if (i === 1) { // fog
          for (let k = 0; k < 4; k++) { c.fillStyle = 'rgba(235,242,248,0.35)'; c.beginPath(); c.ellipse(x0 + ((t * 40 + k * 260) % 900) - 100, 560 + k * 70, 260, 40, 0, 0, 7); c.fill(); }
        } else { // neon marquee
          for (let k = 0; k < 22; k++) { const on = (Math.floor(t * 10) + k) % 3 === 0; c.fillStyle = on ? '#ffe14d' : '#5a3a10'; c.beginPath(); c.arc(x0 + 110 + k * 22, 640, 7, 0, 7); c.fill(); }
          c.save(); c.shadowColor = '#ff5fd2'; c.shadowBlur = 30; c.fillStyle = '#ff5fd2'; c.font = '86px Bowlby'; c.textAlign = 'center';
          c.globalAlpha = Math.sin(t * 7) > -0.5 ? 1 : 0.4; c.fillText('CASINO', x0 + 350, 600); c.restore();
        }
        c.restore();
        // outline separators
        c.strokeStyle = '#111'; c.lineWidth = 18; c.beginPath(); c.moveTo(x0, H); c.lineTo(x0 + 40, 0); c.stroke();
        // label
        if (!opt.clean) {
          const lp = E.outBack(clamp((t - B.sa_three - i * 0.2) / 0.35));
          if (lp > 0) {
            c.save(); c.translate(x0 + 340, 360); c.scale(lp, lp); c.rotate(-0.04);
            outlinedText(c, name, 0, 0, { font: FONT_LAT, size: 96, fill: col, lw: 0.12, track: 0.03 });
            c.restore();
          }
        }
      });
    },
    draw(c, t, opt = {}) {
      const Lb = LINES.sab, Lc = LINES.sac, Ld = LINES.sad;
      if (t < Lb.start - 0.15 || opt.panels) { this.panels(c, t, opt); return; }
      if (t < Lc.start - 0.15) {
        // CJ gets fat
        const q = t - (Lb.start - 0.15);
        c.fillStyle = vgrad(c, 0, H, [[0, '#1f6b3a'], [1, '#0d2b18']]); c.fillRect(0, 0, W, H);
        c.save(); c.translate(W / 2, 560); c.rotate(t * 0.15);
        for (let i = 0; i < 16; i++) { c.rotate(Math.PI / 8); c.fillStyle = 'rgba(80,220,120,0.10)'; c.beginPath(); c.moveTo(0, 0); c.lineTo(-90, -1400); c.lineTo(90, -1400); c.fill(); }
        c.restore();
        halftone(c, 0, 0, W, H, 'rgba(0,0,0,0.12)', 22, 0, 1, true, 0.42);
        const fat = 1 + 0.45 * E.outElastic(clamp((t - B.sa_fat + 0.15) / 0.9));
        const enter = E.outCubic(clamp(q / 0.4));
        person(c, W / 2, 1060 + (1 - enter) * 200, 760, { col: '#2a1d17', shirt: '#2fa65a', fat, rim: '#b8ffcb', pose: 'stand' });
        // burgers flying in
        for (let i = 0; i < 5; i++) {
          const bt = (t - (B.sa_fat - 0.9) - i * 0.16) / 0.55;
          if (bt < 0 || bt > 1) continue;
          const sx = i % 2 ? -200 : W + 200, sy = 200 + i * 120;
          const x = lerp(sx, W / 2, E.inCubic(bt)), y = lerp(sy, 520, E.inCubic(bt));
          c.save(); c.translate(x, y); c.rotate(bt * 6);
          c.fillStyle = '#d98a3a'; c.beginPath(); c.ellipse(0, -10, 46, 26, 0, Math.PI, 0); c.fill();
          c.fillStyle = '#5a2e1a'; c.fillRect(-46, -10, 92, 14); c.fillStyle = '#5fbf3a'; c.fillRect(-48, 2, 96, 6);
          c.fillStyle = '#d98a3a'; c.fillRect(-44, 8, 88, 14);
          c.strokeStyle = '#111'; c.lineWidth = 5; c.strokeRect(-46, -36, 92, 58);
          c.restore();
        }
        // fat meter
        c.save();
        const mx = 1380, my = 300;
        outlinedText(c, 'FAT', mx, my - 20, { font: FONT_LAT, size: 70, fill: '#fff', lw: 0.12, align: 'left', track: 0.1 });
        c.fillStyle = '#111'; roundRect(c, mx, my, 380, 48, 14); c.fill();
        c.fillStyle = '#ffb020'; roundRect(c, mx + 6, my + 6, 368 * clamp((fat - 1) / 0.45 * 0.85 + 0.12), 36, 10); c.fill();
        c.restore();
        return;
      }
      if (t < Ld.start + 0.25) {
        // Hot Coffee + AO + pulled from shelves
        const q = t - (Lc.start - 0.15);
        c.fillStyle = vgrad(c, 0, H, [[0, '#2b1610'], [1, '#120806']]); c.fillRect(0, 0, W, H);
        // shelf with game boxes
        const pull = t - B.sa_pull;
        for (let row = 0; row < 3; row++) {
          const y = 300 + row * 250;
          c.fillStyle = '#6b4a33'; c.fillRect(140, y + 180, W - 280, 24);
          for (let k = 0; k < 10; k++) {
            const bx = 200 + k * 155, idx = row * 10 + k;
            const gone = pull > 0 ? clamp((pull - hash(idx) * 0.9) / 0.35) : 0;
            c.save(); c.translate(bx, y + 180 + gone * 900); c.rotate(gone * (hash(idx + 3) - 0.5) * 2);
            c.fillStyle = '#111'; c.fillRect(0, -170, 120, 170);
            c.fillStyle = ['#2fa65a', '#ffb020', '#c8452f'][idx % 3]; c.fillRect(8, -162, 104, 110);
            c.fillStyle = '#fff'; c.font = '34px Bebas'; c.textAlign = 'center'; c.fillText('SAN ANDREAS', 60, -24);
            c.restore();
          }
        }
        c.fillStyle = 'rgba(0,0,0,0.55)'; c.fillRect(0, 0, W, H);
        // coffee cup
        const cp = E.outBack(clamp((t - B.sa_coffee + 0.15) / 0.4));
        if (cp > 0) {
          c.save(); c.translate(W / 2 - 300, 560); c.scale(cp, cp);
          for (let i = 0; i < 3; i++) {
            c.strokeStyle = 'rgba(255,255,255,0.6)'; c.lineWidth = 12; c.lineCap = 'round';
            c.beginPath();
            for (let k = 0; k < 20; k++) { const yy = -170 - k * 9, xx = -50 + i * 50 + Math.sin(t * 4 + k * 0.5 + i) * 14; k ? c.lineTo(xx, yy) : c.moveTo(xx, yy); }
            c.stroke();
          }
          c.fillStyle = '#f4ede2'; c.strokeStyle = '#111'; c.lineWidth = 12;
          c.beginPath(); c.moveTo(-150, -150); c.lineTo(150, -150); c.lineTo(115, 150); c.lineTo(-115, 150); c.closePath(); c.fill(); c.stroke();
          c.beginPath(); c.arc(175, -20, 60, -1.2, 1.2); c.lineWidth = 26; c.stroke(); c.lineWidth = 12; c.strokeStyle = '#f4ede2'; c.stroke();
          c.fillStyle = '#6b3a1e'; c.fillRect(-140, -148, 280, 26);
          c.fillStyle = '#ff3b3b'; c.font = `66px ${FONT_LAT}`; c.textAlign = 'center'; c.fillText('HOT', 0, 0); c.fillText('COFFEE', 0, 70);
          c.restore();
        }
        if (!opt.clean) {
          c.save(); stamp(c, 'AO 成人级', W / 2 + 330, 470, 130, '#ff2d2d', -0.14, (t - B.sa_ao + 0.05) / 0.22); c.restore();
          if (pull > 0) { c.save(); stamp(c, '下架', W / 2 + 420, 720, 120, '#ffd23f', 0.1, pull / 0.22); c.restore(); }
        }
        // shake on stamp
        return;
      }
      // PS2 king
      const q = t - (Ld.start + 0.25);
      c.fillStyle = vgrad(c, 0, H, [[0, '#24104a'], [1, '#0a0518']]); c.fillRect(0, 0, W, H);
      c.save(); c.translate(W / 2, 470); c.rotate(t * 0.25);
      for (let i = 0; i < 20; i++) { c.rotate(Math.PI / 10); c.fillStyle = 'rgba(255,210,63,0.12)'; c.beginPath(); c.moveTo(0, 0); c.lineTo(-80, -1300); c.lineTo(80, -1300); c.fill(); }
      c.restore();
      const kp = E.outBack(clamp((t - Ld.start - 0.25) / 0.45));
      c.save(); c.translate(W / 2, 300); c.scale(kp, kp);
      c.fillStyle = '#ffd23f'; c.strokeStyle = '#111'; c.lineWidth = 12; c.lineJoin = 'round';
      c.beginPath(); c.moveTo(-170, 90); c.lineTo(-200, -80); c.lineTo(-90, 0); c.lineTo(0, -120); c.lineTo(90, 0); c.lineTo(200, -80); c.lineTo(170, 90); c.closePath(); c.fill(); c.stroke();
      c.fillRect(-170, 90, 340, 46); c.strokeRect(-170, 90, 340, 46);
      [[-200, -80], [0, -120], [200, -80]].forEach(([x, y]) => { c.beginPath(); c.arc(x, y, 18, 0, 7); c.fillStyle = '#ff3b5c'; c.fill(); c.stroke(); });
      c.restore();
      const np = E.outBack(clamp((t - B.sa_king + 0.1) / 0.4));
      if (np > 0) {
        c.save(); c.translate(W / 2, 600); c.scale(np, np);
        outlinedText(c, 'No.1', 0, 0, { font: FONT_NUM, size: 190, fill: '#ffd23f', lw: 0.1 });
        c.restore();
        c.save(); c.globalAlpha = clamp((t - B.sa_king - 0.2) * 3);
        outlinedText(c, 'PS2 史上最畅销游戏 · 约1733万份', W / 2, 690, { font: FONT_CN2, size: 46, fill: '#ffffff', lw: 0.16, grad: false });
        c.restore();
      }
    },
  };
})();

// =====================================================================
// GTA IV (2008) — grey realism, rooftop, $500M
// =====================================================================
SCENES.gta4 = (() => {
  const S = SEG.gta4;
  let bg, far, mid, buf;
  return {
    init() {
      bg = off(W, H); const c = ctxOf(bg);
      c.fillStyle = vgrad(c, 0, H, [[0, '#3d4652'], [0.5, '#6c7680'], [0.8, '#9aa3a8'], [1, '#7f8a90']]); c.fillRect(0, 0, W, H);
      const r = rng(3);
      for (let i = 0; i < 40; i++) { c.fillStyle = `rgba(40,46,56,${0.15 + r() * 0.3})`; c.beginPath(); c.ellipse(r() * W, 60 + r() * 380, 220 + r() * 300, 30 + r() * 50, 0, 0, 7); c.fill(); }
      halftone(c, 0, 0, W, 600, 'rgba(0,0,0,0.10)', 14, 0.9, 0, true);
      far = skyline({ w: 2400, h: 1000, seed: 61, baseY: 860, minH: 200, maxH: 640, minW: 50, maxW: 120, color: '#59626e', win: '#cfd6dc', winProb: 0.12, winSize: [4, 6], spires: 0.35, gapX: 2 });
      mid = skyline({ w: 2400, h: 1000, seed: 63, baseY: 980, minH: 260, maxH: 700, minW: 80, maxW: 180, color: '#3a4049', win: '#e8d9a8', winProb: 0.16, winSize: [6, 8], spires: 0.2, edge: '#58606b' });
      buf = off(W, H);
    },
    draw(c, t, opt = {}) {
      const lt = t - S.start;
      const bc = ctxOf(buf);
      const z = 1.02 + lt * 0.012;
      bc.save(); bc.translate(W / 2, H / 2); bc.scale(z, z); bc.translate(-W / 2, -H / 2);
      bc.drawImage(bg, 0, 0);
      // statue in harbour (generic torch statue silhouette)
      bc.save(); bc.translate(330 - lt * 4, 0); bc.fillStyle = '#4c5560';
      bc.fillRect(-40, 700, 80, 160); bc.fillRect(-70, 840, 140, 30);
      bc.beginPath(); bc.moveTo(-28, 700); bc.lineTo(-18, 560); bc.lineTo(18, 560); bc.lineTo(28, 700); bc.fill();
      bc.beginPath(); bc.arc(0, 545, 16, 0, 7); bc.fill();
      bc.fillRect(10, 470, 9, 80); bc.beginPath(); bc.moveTo(6, 470); bc.lineTo(24, 470); bc.lineTo(15, 445); bc.fill();
      for (let i = 0; i < 5; i++) { bc.save(); bc.translate(0, 535); bc.rotate(-1.2 + i * 0.6); bc.fillRect(-2, -34, 4, 14); bc.restore(); }
      bc.restore();
      bc.drawImage(far, -200 - lt * 10, 0);
      bc.fillStyle = '#5d6a74'; bc.fillRect(0, 860, W, 40);
      bc.drawImage(mid, -300 - lt * 22, 40);
      // rooftop foreground
      bc.fillStyle = '#15181d'; bc.fillRect(0, 930, W, 160);
      bc.fillRect(1240, 860, 40, 80); bc.fillRect(1236, 850, 48, 14);
      for (let x = 0; x < W; x += 90) bc.fillRect(x, 905, 10, 30);
      bc.fillRect(0, 900, W, 8);
      // pigeons
      for (let i = 0; i < 7; i++) { const px = (hash(i) * W + lt * 120 * (0.7 + hash(i + 2))) % (W + 100), py = 220 + hash(i + 4) * 200 + Math.sin(t * 3 + i) * 10; const fl = Math.sin(t * 18 + i) * 8; bc.strokeStyle = '#222'; bc.lineWidth = 4; bc.beginPath(); bc.moveTo(px - 14, py - fl); bc.lineTo(px, py); bc.lineTo(px + 14, py - fl); bc.stroke(); }
      // man on ledge (back view)
      person(bc, 760, 932, 470, { col: '#101216', rim: '#aab6c2', rimSide: 1 });
      bc.restore();
      // drizzle
      bc.save(); bc.strokeStyle = 'rgba(220,230,240,0.22)'; bc.lineWidth = 1.6; bc.beginPath();
      for (let i = 0; i < 200; i++) { const x = (hash(i) * W + t * 80) % W, y = (hash(i + 500) * H + t * 1200) % H; bc.moveTo(x, y); bc.lineTo(x - 5, y + 26); }
      bc.stroke(); bc.restore();
      const real = clamp((t - B.g4_real + 0.3) / 0.6);
      c.save(); c.filter = `saturate(${lerp(0.75, 0.35, real)}) contrast(${lerp(1, 1.18, real)})`; c.drawImage(buf, 0, 0); c.restore();
      if (opt.clean) return;
      // money counter
      const mp = clamp((t - B.g4_money + 0.5) / 1.0);
      if (t > LINES.g4b.start - 0.1) {
        const a = E.outCubic(clamp((t - LINES.g4b.start + 0.1) / 0.3));
        c.save(); c.globalAlpha = a;
        c.fillStyle = 'rgba(10,12,16,0.65)'; c.fillRect(0, 170, W, 260);
        outlinedText(c, '$' + fmtInt(500000000 * E.outExpo(mp)), W / 2, 360, { font: FONT_NUM, size: 170, fill: '#8ee07a', lw: 0.08 });
        outlinedText(c, '首周销售额 · 首日卖出360万份', W / 2, 415, { font: FONT_CN2, size: 40, fill: '#ffffff', lw: 0.12, grad: false, shadow: 0 });
        c.restore();
      }
    },
  };
})();

// =====================================================================
// GTA V (2013) — sunny Los Santos, three protagonists, $1B, 235M copies
// =====================================================================
SCENES.gta5 = (() => {
  const S = SEG.gta5;
  let bg, sky2, buf;
  const HERO = [{ col: '#3d8bff', name: 'MICHAEL' }, { col: '#35d07f', name: 'FRANKLIN' }, { col: '#ff9a2e', name: 'TREVOR' }];
  return {
    init() {
      bg = off(W, H); const c = ctxOf(bg);
      c.fillStyle = vgrad(c, 0, H, [[0, '#2f7fd1'], [0.45, '#8cc4ea'], [0.7, '#ffe0a8'], [1, '#ffbf73']]); c.fillRect(0, 0, W, H);
      glow(c, 1500, 640, 420, '#fff3c2', 0.7);
      // hills + sign
      c.fillStyle = '#9b8a5e'; c.beginPath(); c.moveTo(0, 620); c.quadraticCurveTo(300, 380, 700, 520); c.quadraticCurveTo(1000, 420, 1300, 560); c.quadraticCurveTo(1650, 430, W, 600); c.lineTo(W, H); c.lineTo(0, H); c.fill();
      c.fillStyle = '#7d6e48'; c.beginPath(); c.moveTo(0, 700); c.quadraticCurveTo(500, 560, 900, 680); c.quadraticCurveTo(1400, 600, W, 700); c.lineTo(W, H); c.lineTo(0, H); c.fill();
      c.save(); c.translate(380, 470); c.rotate(-0.08); c.fillStyle = '#f7f7f2'; c.font = '62px Anton'; c.textAlign = 'center';
      const sign = 'LOS SANTOS'; c.fillText(sign, 0, 0); c.restore();
      const sk = skyline({ w: W, h: 1000, seed: 91, baseY: 930, minH: 120, maxH: 520, minW: 60, maxW: 150, color: '#40607f', win: '#bfe3ff', winProb: 0.3, winSize: [5, 9], spires: 0.2, edge: '#7aa3c6', profile: x => 0.4 + 0.9 * Math.exp(-Math.pow((x - 0.62) / 0.18, 2)) });
      c.drawImage(sk, 0, 0);
      c.fillStyle = '#2d3640'; c.fillRect(0, 930, W, 150);
      c.fillStyle = '#c9b443'; for (let x = 0; x < W; x += 140) c.fillRect(x, 1000, 80, 8);
      halftone(c, 0, 0, W, 520, 'rgba(255,255,255,0.10)', 16, 1, 0);
      buf = off(W, H);
    },
    draw(c, t, opt = {}) {
      const lt = t - S.start;
      // switch effect: zoom out to "sky" & back around the switch beat
      const sw = t - B.g5_switch;
      let zoom = 1.04 + lt * 0.01, blur = 0;
      if (sw > -0.15 && sw < 0.75) { const k = Math.sin(clamp((sw + 0.15) / 0.9) * Math.PI); zoom *= 1 - 0.35 * k; blur = 10 * k; }
      const bc = ctxOf(buf);
      bc.save(); bc.translate(W / 2, H / 2); bc.scale(zoom, zoom); bc.translate(-W / 2, -H / 2);
      bc.drawImage(bg, 0, 0);
      for (let i = 0; i < 6; i++) palm(bc, 80 + i * 360 + (i % 2) * 60, 1100, 380 + (i % 3) * 90, (i % 2 ? -1 : 1) * 0.12, Math.sin(t + i) * 0.5, '#1e2a22', null);
      // cars on freeway
      for (let i = 0; i < 3; i++) { const x = ((lt * 300 + i * 700) % (W + 600)) - 300; carSide(bc, x, 1060, 0.55, { body: ['#e23b3b', '#f2f2f2', '#2b2b2b'][i], kind: i === 0 ? 'sports' : 'sedan', wheelRot: lt * 20, head: true }); }
      // three heroes
      const heroIn = (i) => E.outBack(clamp((t - B.g5_three - i * 0.17 + 0.1) / 0.4));
      const active = t < B.g5_switch + 0.15 ? 0 : t < B.g5_switch + 0.6 ? 1 : 2;
      HERO.forEach((h, i) => {
        const p = opt.clean ? 1 : heroIn(i);
        if (p <= 0) return;
        const x = 560 + i * 400, base = 1000;
        bc.save(); bc.globalAlpha = clamp(p);
        bc.translate(x, base); bc.scale(1, p); bc.translate(-x, -base);
        bc.fillStyle = hexA(h.col, 0.85); roundRect(bc, x - 150, 330, 300, 600, 26); bc.fill();
        bc.lineWidth = 10; bc.strokeStyle = '#111'; bc.stroke();
        if (i === active && !opt.clean && t > B.g5_three) { bc.lineWidth = 12; bc.strokeStyle = '#fff'; roundRect(bc, x - 162, 318, 324, 624, 32); bc.stroke(); }
        bc.save(); roundRect(bc, x - 150, 330, 300, 600, 26); bc.clip();
        halftone(bc, x - 150, 330, 300, 600, 'rgba(0,0,0,0.25)', 14, 0, 1, true, 0.45);
        person(bc, x, 1000, 560, { col: '#0d0f14', rim: '#fff', fat: i === 2 ? 1.06 : 1, pose: i === 0 ? 'cross' : i === 1 ? 'stand' : 'hips' });
        bc.restore();
        outlinedText(bc, h.name, x, 400, { font: FONT_LAT, size: 64, fill: '#fff', lw: 0.12, track: 0.06 });
        bc.restore();
      });
      bc.restore();
      c.save(); if (blur) c.filter = `blur(${blur}px)`; c.drawImage(buf, 0, 0); c.restore();
      if (blur > 0.5) { c.fillStyle = `rgba(120,180,255,${blur / 40})`; c.fillRect(0, 0, W, H); }
      if (opt.clean) return;
      // $1B counter
      const L5b = LINES.g5b, L5c = LINES.g5c;
      if (t > L5b.start - 0.15) {
        const a = E.outCubic(clamp((t - L5b.start + 0.15) / 0.3));
        c.save(); c.fillStyle = `rgba(6,30,14,${0.78 * a})`; c.fillRect(0, 0, W, H); c.restore();
        // money rain
        c.save();
        for (let i = 0; i < 46; i++) {
          const x = hash(i) * W, y = ((t - L5b.start) * (380 + hash(i + 1) * 300) + hash(i + 2) * H) % (H + 200) - 100;
          c.save(); c.translate(x, y); c.rotate(Math.sin(t * 3 + i) * 0.8); c.globalAlpha = a * 0.85;
          c.fillStyle = '#5fbf6a'; c.fillRect(-46, -22, 92, 44); c.strokeStyle = '#1e5a28'; c.lineWidth = 4; c.strokeRect(-40, -16, 80, 32);
          c.fillStyle = '#1e5a28'; c.font = '28px Anton'; c.textAlign = 'center'; c.fillText('$', 0, 10); c.restore();
        }
        c.restore();
        if (t < L5c.start - 0.1) {
          const mp = clamp((t - B.g5_billion + 0.6) / 1.1);
          c.save(); c.globalAlpha = a;
          outlinedText(c, '$' + fmtInt(1000000000 * E.outExpo(mp)), W / 2, 440, { font: FONT_NUM, size: 190, fill: '#8ee07a', lw: 0.08 });
          outlinedText(c, '发售 3 天 · 全球销售额', W / 2, 520, { font: FONT_CN2, size: 50, fill: '#ffffff', lw: 0.14, grad: false, shadow: 0 });
          c.restore();
          if (t > B.g5_record - 0.1) { c.save(); stamp(c, '刷新纪录', W / 2 + 560, 300, 96, '#ff3b3b', 0.16, (t - B.g5_record + 0.1) / 0.22); c.restore(); }
        } else {
          // 235M copies stack
          const up = clamp((t - L5c.start + 0.1) / 1.4);
          c.save();
          const n = 13;
          for (let i = 0; i < n; i++) {
            const h = 60 + 440 * Math.pow((i + 1) / n, 1.6) * E.outCubic(clamp(up * 1.3 - i * 0.03));
            const x = 300 + i * 100;
            c.fillStyle = i === n - 1 ? '#ffd23f' : '#3fbf65'; c.fillRect(x, 900 - h, 70, h);
            c.strokeStyle = '#111'; c.lineWidth = 6; c.strokeRect(x, 900 - h, 70, h);
          }
          const units = 235000000 * E.outExpo(clamp((t - B.g5_units + 0.4) / 1.0));
          outlinedText(c, fmtInt(units), W / 2, 300, { font: FONT_NUM, size: 170, fill: '#ffd23f', lw: 0.08 });
          outlinedText(c, '份 · 截至2026年11月（Take-Two财报）', W / 2, 365, { font: FONT_CN2, size: 40, fill: '#fff', lw: 0.12, grad: false, shadow: 0 });
          c.restore();
        }
      }
    },
  };
})();

// =====================================================================
// GTA VI (2013 -> 2026) — the wait, the leak, the trailer, the launch
// =====================================================================
SCENES.gta6 = (() => {
  const S = SEG.gta6;
  let hero, heroBuf, buf;
  return {
    init() {
      hero = off(W, H); const c = ctxOf(hero);
      c.fillStyle = vgrad(c, 0, 720, [[0, '#2b0f5c'], [0.35, '#8b2a9e'], [0.62, '#ff4f8b'], [0.85, '#ff9a3d'], [1, '#ffd36b']]); c.fillRect(0, 0, W, 720);
      glow(c, 1320, 650, 520, '#ffd9a0', 0.75);
      c.fillStyle = '#ffe9b0'; c.beginPath(); c.arc(1320, 650, 120, 0, 7); c.fill();
      const r = rng(17);
      for (let i = 0; i < 18; i++) { c.fillStyle = `rgba(120,30,120,${0.25 + r() * 0.3})`; c.beginPath(); c.ellipse(r() * W, 120 + r() * 360, 200 + r() * 260, 20 + r() * 26, 0, 0, 7); c.fill(); }
      const sk = skyline({ w: W, h: 720, seed: 101, baseY: 720, minH: 60, maxH: 300, minW: 50, maxW: 130, color: '#4a1b5e', win: '#ffb3e0', winProb: 0.25, winSize: [4, 6], spires: 0.15, profile: x => 0.3 + 0.9 * Math.exp(-Math.pow((x - 0.3) / 0.16, 2)) });
      c.drawImage(sk, 0, 4);
      c.fillStyle = vgrad(c, 720, H, [[0, '#ff7aa8'], [0.2, '#7a2a8e'], [1, '#170a2c']]); c.fillRect(0, 720, W, H - 720);
      for (let i = 0; i < 40; i++) { const y = 730 + i * i * 0.2; c.fillStyle = `rgba(255,220,150,${0.6 - i * 0.014})`; const w = 420 - i * 8; c.fillRect(1320 - w / 2, y, w, 3); }
      // beach
      c.fillStyle = '#2a0f33'; c.beginPath(); c.moveTo(0, 900); c.quadraticCurveTo(700, 860, W, 940); c.lineTo(W, H); c.lineTo(0, H); c.fill();
      halftone(c, 0, 0, W, 520, 'rgba(255,255,255,0.08)', 16, 1, 0);
      heroBuf = off(W, H); buf = off(W, H);
    },
    heroScene(c, t, opt) {
      const lt = t - LINES.g6d.start;
      const z = 1.12 - 0.08 * E.outCubic(clamp(lt / 2.5)) + Math.max(0, lt - 2.5) * 0.006;
      c.save(); c.translate(W / 2, H / 2); c.scale(z, z); c.translate(-W / 2, -H / 2);
      c.drawImage(hero, 0, 0);
      // flamingos
      for (let i = 0; i < 3; i++) {
        const x = 1580 + i * 70, y = 930 + (i % 2) * 14;
        c.save(); c.translate(x, y); c.scale(i % 2 ? -1 : 1, 1);
        c.fillStyle = '#ff6fae'; c.strokeStyle = '#2a0f33'; c.lineWidth = 3;
        c.fillRect(-2, 0, 3, 46); c.beginPath(); c.ellipse(0, -8, 26, 15, -0.2, 0, 7); c.fill();
        c.lineWidth = 5; c.strokeStyle = '#ff6fae'; c.beginPath(); c.moveTo(16, -14); c.quadraticCurveTo(30, -60, 14, -66); c.stroke();
        c.fillStyle = '#ff6fae'; c.beginPath(); c.arc(14, -68, 7, 0, 7); c.fill();
        c.restore();
      }
      palm(c, 1820, 1120, 820, -0.22, Math.sin(t * 1.1) * 0.7, '#14061d', '#ff9ad0');
      palm(c, 120, 1120, 760, 0.2, Math.sin(t * 1.3 + 1) * 0.7, '#14061d', '#ff9ad0');
      palm(c, 330, 1120, 520, 0.08, Math.sin(t * 1.2 + 2) * 0.7, '#1b0826', null);
      // the duo
      person(c, 880, 1100, 600, { col: '#0f0614', rim: '#ffb3e0', rimSide: -1, pose: 'cross' });
      person(c, 1055, 1100, 565, { col: '#0f0614', rim: '#ffd36b', female: true, rimSide: 1, pose: 'hips' });
      c.restore();
    },
    draw(c, t, opt = {}) {
      const L = LINES;
      const reveal = L.g6d.start - 0.2;
      if (t < reveal && !opt.hero) {
        // ---- dark "waiting" stage ----
        c.fillStyle = '#07060d'; c.fillRect(0, 0, W, H);
        const lt = t - S.start;
        // year counter
        const yearAt = (tt) => {
          if (tt < B.g6_wait + 0.6) return lerp(2013, 2021, E.inOutCubic(inv(S.start + 0.1, B.g6_wait + 0.6, tt)));
          if (tt < L.g6c.start) return 2022;
          return 2023;
        };
        const y = Math.floor(yearAt(t));
        const leak = t > L.g6b.start - 0.1 && t < L.g6c.start - 0.1;
        const trailer = t >= L.g6c.start - 0.1;
        if (!leak && !trailer) {
          c.save();
          c.fillStyle = 'rgba(255,79,139,0.08)';
          for (let i = 0; i < 12; i++) { const x = (i * 180 + lt * 60) % (W + 200) - 100; c.fillRect(x, 0, 2, H); }
          c.restore();
          outlinedText(c, String(y), W / 2, 470, { font: FONT_NUM, size: 300, fill: '#ff7ab8', lw: 0.06 });
          // loading bar
          const lp = clamp(lt / 2.3);
          c.fillStyle = '#222'; roundRect(c, W / 2 - 400, 530, 800, 22, 11); c.fill();
          c.fillStyle = '#ff7ab8'; roundRect(c, W / 2 - 400, 530, 800 * (0.04 + 0.9 * lp), 22, 11); c.fill();
          c.save(); c.font = '52px Bebas'; c.fillStyle = '#ccc'; c.textAlign = 'center';
          c.fillText('LOADING' + '.'.repeat(1 + Math.floor(t * 3) % 3), W / 2, 620); c.restore();
          // spinner
          c.save(); c.translate(W - 150, H - 150); c.rotate(t * 5); c.strokeStyle = '#ff7ab8'; c.lineWidth = 10; c.lineCap = 'round';
          c.beginPath(); c.arc(0, 0, 40, 0, 4.4); c.stroke(); c.restore();
        }
        if (leak) {
          const q = t - (L.g6b.start - 0.1);
          // terminal
          c.save(); c.font = '30px monospace'; c.fillStyle = '#39ff7a';
          const files = [];
          for (let i = 0; i < 26; i++) files.push(`> copying  dev_clip_${String(i * 3 + 7).padStart(3, '0')}.mp4   [${'#'.repeat(1 + (i * 7) % 18)}]`);
          const shift = Math.floor(q * 14);
          for (let i = 0; i < 22; i++) { const s = files[(i + shift) % files.length]; c.globalAlpha = 0.35 + 0.65 * (i / 22); c.fillText(s, 90, 80 + i * 44); }
          c.restore();
          person(c, 1450, 1080, 760, { col: '#050507', rim: '#39ff7a', rimSide: -1, hood: true, jacket: true });
          outlinedText(c, '2022.09', W - 300, 260, { font: FONT_NUM, size: 110, fill: '#39ff7a', lw: 0.08 });
          if (!opt.clean) { c.save(); stamp(c, 'LEAKED', 820, 560, 150, '#ff2d2d', -0.12, (t - B.g6_leak) / 0.22, { font: FONT_LAT }); c.restore(); }
          // glitch
          const gq = t - B.g6_hack;
          if (gq > 0 && gq < 0.4) { c.fillStyle = `rgba(57,255,122,${0.18 * (1 - gq / 0.4)})`; c.fillRect(0, 0, W, H); }
        }
        if (trailer) {
          const q = t - (L.g6c.start - 0.1);
          c.fillStyle = vgrad(c, 0, H, [[0, '#1a0b2e'], [1, '#07060d']]); c.fillRect(0, 0, W, H);
          // screen frame
          const sp = E.outBack(clamp(q / 0.45));
          c.save(); c.translate(700, 520); c.scale(sp * 0.9, sp * 0.9);
          c.fillStyle = '#000'; roundRect(c, -520, -290, 1040, 580, 30); c.fill();
          c.save(); roundRect(c, -510, -280, 1020, 560, 24); c.clip(); c.drawImage(hero, -510, -280, 1020, 560); c.restore();
          c.strokeStyle = '#ff7ab8'; c.lineWidth = 8; roundRect(c, -520, -290, 1040, 580, 30); c.stroke();
          // play button
          c.fillStyle = 'rgba(255,255,255,0.92)'; c.beginPath(); c.arc(0, 0, 90, 0, 7); c.fill();
          c.fillStyle = '#ff4f8b'; c.beginPath(); c.moveTo(-28, -46); c.lineTo(52, 0); c.lineTo(-28, 46); c.closePath(); c.fill();
          c.restore();
          outlinedText(c, '2023.12', 330, 260, { font: FONT_NUM, size: 110, fill: '#ff7ab8', lw: 0.08 });
          const vp = clamp((t - B.g6_views + 0.9) / 1.2);
          const views = 90421491 * E.outExpo(vp);
          c.save(); c.globalAlpha = clamp(q * 3);
          outlinedText(c, fmtInt(views), 1530, 470, { font: FONT_NUM, size: 120, fill: '#ffd36b', lw: 0.08 });
          outlinedText(c, '24小时 YouTube 播放', 1530, 540, { font: FONT_CN2, size: 46, fill: '#fff', lw: 0.14, grad: false, shadow: 0 });
          outlinedText(c, '吉尼斯世界纪录认证', 1530, 595, { font: FONT_CN2, size: 38, fill: '#ffd36b', lw: 0.14, grad: false, shadow: 0 });
          c.restore();
        }
        return;
      }
      // ---- the launch ----
      const q = t - reveal;
      this.heroScene(c, t, opt);
      const fl = 1 - clamp(q / 0.5);
      if (fl > 0) { c.fillStyle = `rgba(255,255,255,${fl})`; c.fillRect(0, 0, W, H); }
      if (opt.clean) return;
      // date stamp + logo
      const dp = E.outBack(clamp((t - B.g6_date - 0.15) / 0.4));
      const logoP = E.outBack(clamp((t - B.g6_release + 0.1) / 0.45));
      const moneyT = L.g6e.start - 0.1;
      const toTop = E.inOutCubic(clamp((t - moneyT) / 0.45));
      if (dp > 0) {
        c.save(); c.translate(W / 2, lerp(175, 150, toTop)); c.scale(dp * lerp(1, 0.75, toTop), dp * lerp(1, 0.75, toTop));
        outlinedText(c, '2026.11.19', 0, 0, { font: FONT_NUM, size: 130, fill: '#ffffff', lw: 0.08 });
        c.restore();
      }
      if (logoP > 0 && toTop < 1) {
        c.save(); c.globalAlpha = 1 - toTop; c.translate(W / 2, 430); c.scale(logoP * 0.9, logoP * 0.9); c.rotate(-0.03);
        const g = c.createLinearGradient(-400, -200, 400, 50); g.addColorStop(0, '#ff4f8b'); g.addColorStop(0.5, '#ff9a3d'); g.addColorStop(1, '#b57bff');
        c.font = `300px ${FONT_NUM}`; c.textAlign = 'center'; c.lineJoin = 'round';
        c.lineWidth = 28; c.strokeStyle = '#000'; c.strokeText('GTA VI', 0, 0);
        c.fillStyle = g; c.fillText('GTA VI', 0, 0);
        c.restore();
        c.save(); c.globalAlpha = clamp((t - B.g6_release - 0.2) * 3) * (1 - toTop);
        outlinedText(c, '重回罪恶都市 · 首次男女双主角', W / 2, 960, { font: FONT_CN2, size: 64, fill: '#ffe3f0', lw: 0.16, grad: false });
        c.restore();
      }
      if (t > moneyT) {
        const mp = E.outBack(clamp((t - B.g6_money + 0.2) / 0.5));
        c.save(); c.fillStyle = `rgba(20,6,30,${0.45 * toTop})`; c.fillRect(0, 0, W, H); c.restore();
        // fireworks
        for (let k = 0; k < 6; k++) {
          const ft = (t - B.g6_money - k * 0.38);
          if (ft < 0 || ft > 1.6) continue;
          const fx = 260 + hash(k) * (W - 520), fy = 160 + hash(k + 9) * 300;
          const cols = ['#ff4f8b', '#ffd36b', '#b57bff', '#39f3ff'];
          c.save(); c.globalCompositeOperation = 'lighter';
          for (let i = 0; i < 28; i++) {
            const a = i / 28 * Math.PI * 2, d = 260 * E.outCubic(clamp(ft / 1.2));
            const x = fx + Math.cos(a) * d, y = fy + Math.sin(a) * d + ft * ft * 80;
            c.globalAlpha = clamp(1.6 - ft);
            c.fillStyle = cols[(k + i) % 4]; c.beginPath(); c.arc(x, y, 6, 0, 7); c.fill();
          }
          c.restore();
        }
        if (mp > 0) {
          c.save(); c.translate(W / 2, 520); c.scale(mp, mp);
          const g = c.createLinearGradient(0, -200, 0, 40); g.addColorStop(0, '#fff3b0'); g.addColorStop(0.5, '#ffd36b'); g.addColorStop(1, '#ff9a3d');
          c.font = `250px ${FONT_NUM}`; c.textAlign = 'center'; c.lineJoin = 'round';
          c.lineWidth = 26; c.strokeStyle = '#000'; c.strokeText('$37.9亿', 0, 0);
          c.fillStyle = g; c.fillText('$37.9亿', 0, 0);
          c.restore();
          c.save(); c.globalAlpha = clamp((t - B.g6_money) * 2);
          outlinedText(c, '*Take-Two 官方估算的首日零售额', W / 2, 600, { font: FONT_CN2, size: 38, fill: '#fff', lw: 0.14, grad: false, shadow: 0 });
          c.restore();
        }
      }
    },
  };
})();

// =====================================================================
// HOOK & OUTRO helpers
// =====================================================================
const MONTAGE = [
  { id: 'gta1', t: 17.85, year: '1997', title: 'GTA' },
  { id: 'gta2', t: 25.6, year: '1999', title: 'GTA 2' },
  { id: 'gta3', t: 33.0, year: '2001', title: 'GTA III', opt: { city: true } },
  { id: 'vc', t: 42.6, year: '2002', title: 'VICE CITY' },
  { id: 'sa', t: 49.2, year: '2004', title: 'SAN ANDREAS', opt: { panels: true } },
  { id: 'gta4', t: 60.3, year: '2008', title: 'GTA IV' },
  { id: 'gta5', t: 65.6, year: '2013', title: 'GTA V' },
  { id: 'gta6', t: 80.6, year: '2026', title: 'GTA VI', opt: { hero: true } },
];
