# -*- coding: utf-8 -*-
"""Procedural sound design + voice placement + mix.

Outputs (build/audio):  voice.wav  sfx.wav  mix.wav   (48 kHz stereo, 24-bit)
"""
import json, os
import numpy as np
import soundfile as sf
from scipy import signal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TL = json.load(open(os.path.join(ROOT, "build", "timeline.json"), encoding="utf-8"))
SR = 48000
RNG = np.random.default_rng(7)
TOTAL = TL["total"]
N = int(TOTAL * SR) + SR
LINES = {l["id"]: l for l in TL["lines"]}
SEG = {s["id"]: s for s in TL["segments"]}
B = TL["beats"]


# ------------------------------------------------------------------ dsp helpers
def tt(d):
    return np.arange(int(d * SR)) / SR


def noise(d):
    return RNG.standard_normal(int(d * SR))


def pink(d):
    n = int(d * SR)
    w = RNG.standard_normal(n)
    b = [0.049922035, -0.095993537, 0.050612699, -0.004408786]
    a = [1, -2.494956002, 2.017265875, -0.522189400]
    return signal.lfilter(b, a, w) * 3.5


def bp(x, lo, hi, order=2):
    hi = min(hi, SR / 2 * 0.95)
    sos = signal.butter(order, [lo, hi], btype="band", fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def lp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, min(f, SR / 2 * 0.95), btype="low", fs=SR, output="sos"), x)


def hp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, btype="high", fs=SR, output="sos"), x)


def expdec(d, tau):
    return np.exp(-tt(d) / tau)


def fade(x, a=0.005, b=0.02):
    x = x.copy()
    na, nb = int(a * SR), int(b * SR)
    if na:
        x[:na] *= np.linspace(0, 1, na)
    if nb:
        x[-nb:] *= np.linspace(1, 0, nb)
    return x


def norm(x, peak=1.0):
    m = np.max(np.abs(x)) + 1e-9
    return x / m * peak


def sine_sweep(d, f0, f1, curve="exp"):
    t = tt(d)
    if curve == "exp":
        f = f0 * (f1 / f0) ** (t / d)
    else:
        f = f0 + (f1 - f0) * t / d
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph), f


def osc(freq, d, kind="sine"):
    t = tt(d)
    if np.isscalar(freq):
        ph = 2 * np.pi * freq * t
    else:
        ph = 2 * np.pi * np.cumsum(freq) / SR
    if kind == "sine":
        return np.sin(ph)
    if kind == "square":
        return np.sign(np.sin(ph))
    if kind == "saw":
        return 2 * ((ph / (2 * np.pi)) % 1) - 1
    if kind == "tri":
        return 2 * np.abs(2 * ((ph / (2 * np.pi)) % 1) - 1) - 1


def swept_noise(d, f0, f1, shape=None, bands=12, width=0.45):
    n = int(d * SR)
    x = noise(d)
    t = np.linspace(0, 1, n)
    prog = shape(t) if shape else t
    lc = np.log(f0) + (np.log(f1) - np.log(f0)) * prog
    centers = np.geomspace(min(f0, f1) * 0.8, max(f0, f1) * 1.2, bands)
    out = np.zeros(n)
    wsum = np.zeros(n) + 1e-6
    for fc in centers:
        y = bp(x, fc * 0.7, fc * 1.4)
        w = np.exp(-((np.log(fc) - lc) / width) ** 2)
        out += y * w
        wsum += w
    return out / np.sqrt(wsum)


def reverb(x, wet=0.25, size=1.0, damp=3500):
    dl = [int(d * size * SR / 44100) for d in (1557, 1617, 1491, 1422, 1277, 1356)]
    y = np.zeros(len(x) + int(SR * 1.2 * size))
    xp = np.concatenate([x, np.zeros(len(y) - len(x))])
    for d in dl:
        a = np.zeros(d + 1); a[0] = 1; a[-1] = -0.8
        y += signal.lfilter([1], a, lp(xp, damp, 1))
    for d in (225, 556, 441):
        d = int(d * SR / 44100)
        b = np.zeros(d + 1); b[0] = -0.5; b[-1] = 1
        a = np.zeros(d + 1); a[0] = 1; a[-1] = -0.5
        y = signal.lfilter(b, a, y)
    y = y / len(dl) * 0.6
    out = y * wet
    out[: len(x)] += x * (1 - wet * 0.5)
    return out


def stereo(x, pan=0.0):
    pan = np.clip(pan, -1, 1)
    if np.isscalar(pan):
        l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    else:
        l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    return np.stack([x * l, x * r], axis=1) * 1.4142


def widen(x, ms=12):
    d = int(ms / 1000 * SR)
    l = x
    r = np.concatenate([np.zeros(d), x[:-d]]) if d else x
    return np.stack([l, r], axis=1)


# ------------------------------------------------------------------ sound recipes
def impact(big=1.0):
    d = 1.6 if big >= 1 else 0.9
    s, _ = sine_sweep(d, 95 * (1.1 if big < 1 else 1), 34)
    sub = s * expdec(d, 0.28 * big + 0.08)
    body = lp(noise(d), 900) * expdec(d, 0.06)
    crack = hp(noise(d), 2500) * expdec(d, 0.018)
    x = sub * 1.0 + body * 0.55 + crack * 0.35
    x = reverb(fade(x, 0.001, 0.2), wet=0.22, size=1.2)
    return widen(norm(x, 0.95), 9)


def whoosh(d=0.5, up=True, pan=(-0.7, 0.7)):
    shape = (lambda t: t) if up else (lambda t: 1 - t)
    x = swept_noise(d, 250, 4200, shape)
    t = np.linspace(0, 1, len(x))
    env = np.sin(np.pi * np.clip(t, 0, 1) ** 0.8) ** 1.6
    x = norm(x * env, 0.8)
    p = np.linspace(pan[0], pan[1], len(x))
    return stereo(x, p)


def radio_tune(d=0.55):
    t = tt(d)
    st = bp(noise(d), 900, 6500) * (0.6 + 0.4 * np.sin(2 * np.pi * 37 * t))
    wh, _ = sine_sweep(d, 2600, 700)
    wh2, _ = sine_sweep(d, 1200, 3100)
    blips = np.zeros(len(t))
    for k in range(3):
        a = int((0.08 + k * 0.14) * SR)
        b = a + int(0.05 * SR)
        blips[a:b] = osc(400 + 300 * k, 0.05, "square") * 0.25
    env = np.minimum(1, t / 0.04) * np.minimum(1, (d - t) / 0.08)
    x = (st * 0.6 + wh * 0.18 + wh2 * 0.1 + bp(blips, 300, 3000)) * env
    click = np.zeros(len(t)); click[-int(0.01 * SR):] = hp(noise(0.01), 1500) * 0.7
    return widen(norm(x + click, 0.7), 4)


def ding(freq=1320, d=1.2, wet=0.3):
    t = tt(d)
    x = sum(a * np.sin(2 * np.pi * freq * m * t) * np.exp(-t / (0.45 / m ** 0.5))
            for m, a in ((1, 1), (2.76, 0.35), (5.4, 0.18), (8.9, 0.06)))
    x = fade(x, 0.002, 0.1)
    return widen(norm(reverb(x, wet), 0.6), 7)


def cash_register():
    d = 1.4
    t = tt(d)
    ka = hp(noise(0.06), 1800) * expdec(0.06, 0.012)
    clank = sum(np.sin(2 * np.pi * f * tt(0.18)) * np.exp(-tt(0.18) / 0.04) for f in (520, 1370, 2210)) * 0.3
    ching = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t / dec) for f, a, dec in
                ((2093, 1, 0.5), (3136, 0.6, 0.4), (4186, 0.35, 0.3), (2637, 0.5, 0.45)))
    drawer = lp(noise(0.35), 1500) * np.hanning(int(0.35 * SR)) * 0.3
    x = np.zeros(int(1.8 * SR))
    x[:len(ka)] += ka
    x[int(0.02 * SR):int(0.02 * SR) + len(clank)] += clank
    o = int(0.09 * SR); x[o:o + len(ching)] += ching * 0.55
    o = int(0.12 * SR); x[o:o + len(drawer)] += drawer
    return widen(norm(reverb(fade(x, 0.001, 0.2), 0.18), 0.7), 6)


def stamp_snd():
    d = 0.5
    s, _ = sine_sweep(d, 140, 55)
    th = s * expdec(d, 0.07)
    slap = bp(noise(d), 300, 3000) * expdec(d, 0.025)
    x = reverb(fade(th * 1.0 + slap * 0.7, 0.001, 0.1), 0.15, 0.6)
    return widen(norm(x, 0.85), 5)


def pop(f=520):
    d = 0.12
    s, _ = sine_sweep(d, f * 1.6, f * 0.7)
    x = s * expdec(d, 0.03) + hp(noise(d), 3000) * expdec(d, 0.004) * 0.3
    return stereo(norm(fade(x, 0.0005, 0.02), 0.5))


def tick(f=3500, d=0.012):
    x = bp(noise(0.03), f * 0.7, f * 1.4) * expdec(0.03, d / 3)
    return stereo(norm(x, 0.5))


def glitch(d=0.45):
    t = tt(d)
    x = np.zeros(len(t))
    pos = 0
    while pos < len(t):
        L = int(RNG.uniform(0.015, 0.06) * SR)
        kind = RNG.integers(0, 3)
        if kind == 0:
            seg = osc(RNG.uniform(200, 2400), L / SR, "square") * 0.5
        elif kind == 1:
            seg = np.round(noise(L / SR) * 3) / 3 * 0.5
        else:
            seg = np.zeros(L)
        x[pos:pos + L] += seg[: len(x) - pos]
        pos += L
    x = lp(x, 7000)
    return widen(norm(fade(x, 0.002, 0.05), 0.6), 3)


def siren8(d):
    t = tt(d)
    f = np.where((t * 2.2) % 1 < 0.5, 700, 930) * (1 + 0.01 * np.sin(2 * np.pi * 6 * t))
    x = lp(osc(f, d, "square"), 2800) * 0.5
    return widen(norm(fade(x, 0.05, 0.3), 0.5), 2)


def crash():
    d = 1.0
    t = tt(d)
    burst = noise(d) * expdec(d, 0.09)
    clank = sum(np.sin(2 * np.pi * f * t + RNG.uniform(0, 6)) * np.exp(-t / dec) for f, dec in
                ((410, 0.2), (1130, 0.15), (2350, 0.1), (3170, 0.08), (780, 0.18)))
    s, _ = sine_sweep(d, 110, 45)
    x = burst * 0.7 + clank * 0.25 + s * expdec(d, 0.12)
    x = np.round(x * 12) / 12  # a bit crunchy / retro
    return widen(norm(reverb(fade(x, 0.001, 0.2), 0.15, 0.7), 0.85), 8)


def arp8(notes, step=0.055, kind="square", d_last=0.2):
    out = []
    for i, f in enumerate(notes):
        d = d_last if i == len(notes) - 1 else step
        out.append(osc(f, d, kind) * expdec(d, d * 0.8 + 0.02))
    x = lp(np.concatenate(out), 5000)
    return stereo(norm(fade(x, 0.002, 0.03), 0.45))


def sad_trombone():
    notes = [(392, 0.32), (370, 0.32), (349, 0.32), (330, 1.1)]
    out = []
    for i, (f, d) in enumerate(notes):
        t = tt(d)
        vib = 1 + (0.025 * np.sin(2 * np.pi * 5.5 * t) * np.clip(t / 0.3, 0, 1) if i == 3 else 0)
        s = osc(f * vib * 0.5, d, "saw")
        env = np.minimum(1, t / 0.04) * np.minimum(1, (d - t) / 0.06)
        wah = np.minimum(1, t / 0.12)
        y = lp(s, 600) * (1 - wah) + lp(s, 1800) * wah
        out.append(y * env)
    x = np.concatenate(out)
    return widen(norm(reverb(x, 0.18), 0.55), 6)


def tape_stop(d=0.6):
    s, _ = sine_sweep(d, 520, 30)
    x = (s + 0.3 * lp(noise(d), 800)) * np.linspace(1, 0, int(d * SR)) ** 0.7
    return stereo(norm(x, 0.5))


def rain(d):
    x = hp(pink(d), 900) * 0.6 + hp(noise(d), 4000) * 0.15
    drops = np.zeros(int(d * SR))
    idx = RNG.integers(0, len(drops) - 400, int(d * 40))
    for i in idx:
        drops[i:i + 300] += bp(noise(300 / SR), 1500, 6000) * np.exp(-np.arange(300) / 40) * RNG.uniform(0.2, 1)
    x = x + drops * 0.6
    return widen(norm(fade(x, 0.4, 0.6), 0.35), 17)


def thunder(d=2.5):
    x = lp(pink(d), 220) * (np.minimum(1, tt(d) / 0.15) * expdec(d, 0.8))
    x += lp(noise(d), 1200) * expdec(d, 0.12) * 0.2
    return widen(norm(x, 0.6), 23)


def engine_pass(d=2.2, base=85):
    t = tt(d)
    c = d / 2
    dop = 1 + 0.12 * np.tanh((c - t) * 3)
    f = base * dop
    x = osc(f, d, "saw") * 0.6 + osc(f * 2, d, "square") * 0.2
    x = lp(x, 900) + lp(noise(d), 500) * 0.3
    env = np.exp(-((t - c) / (d / 4)) ** 2)
    pan = np.tanh((t - c) * 2.5)
    return stereo(norm(x * env, 0.5), pan)


def sonar():
    d = 1.4
    x = np.sin(2 * np.pi * 1250 * tt(d)) * expdec(d, 0.18)
    return widen(norm(reverb(x, 0.45, 1.3), 0.45), 11)


def page_flip():
    d = 0.22
    x = bp(noise(d), 800, 7000) * np.hanning(int(d * SR)) ** 0.7
    return stereo(norm(x, 0.45), 0.2)


def spray(d=0.6):
    x = hp(noise(d), 2500) * (np.minimum(1, tt(d) / 0.03) * np.minimum(1, (d - tt(d)) / 0.08))
    x *= 1 + 0.15 * np.sin(2 * np.pi * 11 * tt(d))
    return stereo(norm(x, 0.45), np.linspace(-0.6, 0.6, int(d * SR)))


def vhs_rewind(d):
    t = tt(d)
    wh = osc(1800 + 600 * np.sin(2 * np.pi * 0.7 * t) + 400 * t / d, d, "sine")
    chatter = (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 42 * t)))
    x = wh * 0.25 * chatter + bp(noise(d), 2000, 8000) * 0.25 * chatter + lp(noise(d), 300) * 0.25
    return widen(norm(fade(x, 0.05, 0.08), 0.45), 4)


def vhs_clunk():
    d = 0.35
    x = lp(noise(d), 1500) * expdec(d, 0.02) + np.sin(2 * np.pi * 90 * tt(d)) * expdec(d, 0.05)
    return stereo(norm(x, 0.7))


def synth_stab(chord=(261.6, 311.1, 392.0, 466.2), d=1.4):
    t = tt(d)
    x = np.zeros(len(t))
    for f in chord:
        for det in (-0.006, 0, 0.007):
            x += osc(f * (1 + det), d, "saw")
    cut = 600 + 3800 * np.exp(-t / 0.12)
    # time-varying LP approximated by crossfading two filters
    a = lp(x, 4400); b = lp(x, 700)
    w = (cut - 600) / 3800
    y = a * w + b * (1 - w)
    y *= np.minimum(1, t / 0.008) * np.exp(-t / 0.5)
    return widen(norm(reverb(y, 0.3, 1.1), 0.55), 14)


def waves(d):
    t = tt(d)
    x = lp(pink(d), 1100) * (0.55 + 0.45 * np.sin(2 * np.pi * 0.16 * t) ** 2)
    return widen(norm(fade(x, 0.5, 0.6), 0.35), 21)


def boing():
    d = 0.7
    t = tt(d)
    f = 240 + 140 * np.sin(2 * np.pi * 13 * t) * np.exp(-t / 0.25) + 60 * t
    x = osc(f, d, "sine") * expdec(d, 0.25)
    return stereo(norm(x, 0.55))


def beep(f=1000, d=0.35):
    x = np.sin(2 * np.pi * f * tt(d)) * (np.minimum(1, tt(d) / 0.005) * np.minimum(1, (d - tt(d)) / 0.01))
    return stereo(norm(x, 0.35))


def thud(f=90):
    d = 0.35
    s, _ = sine_sweep(d, f * 1.6, f * 0.6)
    x = s * expdec(d, 0.05) + lp(noise(d), 1200) * expdec(d, 0.015) * 0.5
    return stereo(norm(x, 0.6), RNG.uniform(-0.5, 0.5))


def fanfare():
    notes = [523.3, 659.3, 784.0, 1046.5]
    x = np.zeros(int(2.2 * SR))
    for i, f in enumerate(notes):
        d = ding(f, 1.6 if i == 3 else 1.0, 0.25)[:, 0]
        o = int(i * 0.09 * SR)
        x[o:o + len(d)] += d[: len(x) - o]
    return widen(norm(x, 0.6), 8)


def counter_ticks(d, rate0=30, rate1=6):
    out = np.zeros(int(d * SR) + SR // 10)
    tk = tick(4200)[:, 0]
    tpos = 0.0
    while tpos < d:
        rate = rate0 + (rate1 - rate0) * (tpos / d) ** 1.5
        o = int(tpos * SR)
        out[o:o + len(tk)] += tk * 0.8
        tpos += 1 / rate
    return stereo(out)


def keyboard(d):
    out = np.zeros(int(d * SR) + 2000)
    tpos = 0.0
    while tpos < d:
        o = int(tpos * SR)
        k = bp(noise(0.02), 1500, 6000) * expdec(0.02, 0.004) * RNG.uniform(0.4, 1)
        out[o:o + len(k)] += k
        tpos += RNG.uniform(0.045, 0.11)
    return widen(norm(out, 0.4), 3)


def alarm(n=3):
    x = np.concatenate([np.concatenate([osc(880, 0.12, "square") * 0.5, np.zeros(int(0.08 * SR))]) for _ in range(n)])
    return stereo(norm(lp(x, 4000), 0.4))


def firework(pan=0.0):
    wd = 0.45
    wh, _ = sine_sweep(wd, 900, 2600)
    wh *= np.linspace(0.2, 1, len(wh)) * 0.25
    bd = 1.6
    t = tt(bd)
    burst = lp(noise(bd), 2500) * expdec(bd, 0.12)
    crack = np.zeros(len(t))
    for i in RNG.integers(int(0.15 * SR), int(1.4 * SR), 60):
        L = 200
        crack[i:i + L] += hp(noise(L / SR), 3000) * np.exp(-np.arange(L) / 30) * RNG.uniform(0.2, 1)
    x = np.concatenate([wh, burst + crack * 0.5])
    return stereo(norm(reverb(x, 0.25, 1.2), 0.55), pan)


def riser(d=1.4):
    x = swept_noise(d, 300, 6000, lambda t: t ** 1.5) * np.linspace(0, 1, int(d * SR)) ** 2
    s, _ = sine_sweep(d, 180, 1400)
    x = x + s * 0.18 * np.linspace(0, 1, len(s)) ** 2
    return widen(norm(x, 0.6), 9)


def hum(d, base=60):
    t = tt(d)
    x = sum(np.sin(2 * np.pi * base * k * t) / k for k in (1, 2, 3, 5, 7))
    x *= 1 + 0.3 * (RNG.standard_normal(len(t)) > 2.6)
    return stereo(norm(lp(x, 1800) * 0.4, 0.25))


def engine8(d):
    t = tt(d)
    f = 72 + 6 * np.sin(2 * np.pi * 0.7 * t)
    x = lp(osc(f, d, "square"), 600) * (0.8 + 0.2 * np.sin(2 * np.pi * 9 * t))
    return stereo(norm(fade(x, 0.2, 0.3), 0.3))


def city_amb(d):
    x = lp(pink(d), 400) * 0.8 + bp(pink(d), 400, 2500) * 0.15
    out = norm(x, 0.3)
    for k in range(3):  # distant horns
        o = int(RNG.uniform(0.5, d - 1.0) * SR)
        h = (osc(392 if k % 2 else 349, 0.35, "saw") * 0.5 + osc(494, 0.35, "saw") * 0.3)
        h = lp(h, 1600) * np.hanning(len(h)) * 0.08
        out[o:o + len(h)] += h
    return widen(fade(out, 0.3, 0.5), 19)


def shutter():
    d = 0.1
    x = np.zeros(int(d * SR))
    for o in (0, int(0.045 * SR)):
        c = bp(noise(0.03), 1500, 7000) * expdec(0.03, 0.005)
        x[o:o + len(c)] += c
    return stereo(norm(x, 0.45))


def hiss(d=0.25):
    x = hp(noise(d), 1800) * np.minimum(1, tt(d) / 0.01) * expdec(d, 0.08)
    return stereo(norm(x, 0.4))


def clock_tick(hi=True):
    f = 3000 if hi else 2200
    x = bp(noise(0.04), f * 0.8, f * 1.3) * expdec(0.04, 0.004) + np.sin(2 * np.pi * f / 2 * tt(0.04)) * expdec(0.04, 0.006) * 0.3
    return stereo(norm(x, 0.5))


# ------------------------------------------------------------------ placement
sfx = np.zeros((N, 2))
beds = np.zeros((N, 2))   # ambience, ducked under voice


def put(snd, t, gain_db=0.0, bed=False):
    o = int(t * SR)
    if o < 0:
        snd = snd[-o:]; o = 0
    e = min(N, o + len(snd))
    (beds if bed else sfx)[o:e] += snd[: e - o] * 10 ** (gain_db / 20)


L = LINES
S = SEG

# ---- hook
put(impact(0.7), 0.02, -4)
put(glitch(0.3), 0.0, -12)
HOOK_END = L["h3"]["start"] - 0.12
SHOT = HOOK_END / 8
for i in range(1, 8):
    put(whoosh(0.32, True, (0.8, -0.8)), i * SHOT - 0.24, -13)
    put(shutter(), i * SHOT - 0.02, -14)
put(cash_register(), B["h2_money"] + 0.05, -9)
put(riser(1.2), HOOK_END - 1.1, -18)
put(impact(1.0), HOOK_END, -3)
wG = next(w for w in L["h3"]["words"] if w[2] == "GTA")
for i in range(6):
    tt_ = wG[0] + (L["h3"]["end"] - wG[0]) * i / 6
    put(ding(880 * 2 ** (i / 12 * 2), 0.9, 0.25), tt_, -15)
put(pop(380), wG[0] - 0.15, -10)

# ---- era transitions (radio switch = music cue)
ERA = ["gta1", "gta2", "gta3", "vc", "sa", "gta4", "gta5", "gta6", "outro"]
STARS = {"gta1": 1, "gta2": 2, "gta3": 3, "vc": 3, "sa": 3, "gta4": 4, "gta5": 5, "gta6": 6, "outro": 6}
prev = 0
for sid in ERA:
    T = S[sid]["start"]
    put(whoosh(0.6, True, (0.9, -0.9)), T - 0.33, -8)
    put(radio_tune(0.5), T - 0.3, -15)
    if sid not in ("gta6", "outro"):
        put(impact(0.6), T + 0.04, -9)
    if STARS[sid] > prev and sid != "gta6":
        put(ding(1568, 0.8, 0.2), T + 0.55, -17)
    prev = STARS[sid]

# ---- card pops (subtle)
for l in TL["lines"]:
    if l["card"]:
        st = l["start"]
        seg = S[l["seg"]]
        first = next(x for x in TL["lines"] if x["seg"] == l["seg"])["id"] == l["id"]
        if first and l["seg"] in ERA[:-2]:
            st = max(st, seg["start"] + 1.08)
        put(pop(420), st + 0.05, -20)

# ---- GTA 1
s1 = S["gta1"]
put(engine8(L["g1b"]["start"] - s1["start"]), s1["start"], -16, bed=True)
put(arp8([523, 659, 784, 1047], 0.06), s1["start"] + 1.25, -15)
put(tape_stop(0.55), L["g1b"]["start"] - 0.05, -14)
put(sad_trombone(), B["g1_boring"] - 0.15, -11)
put(stamp_snd(), B["g1_cut"], -7)
put(glitch(0.45), B["g1_bug"] - 0.05, -9)
put(arp8([1500, 1200, 1800, 900, 2000], 0.03, "square", 0.05), B["g1_bug"] + 0.2, -18)
put(siren8(L["g1d"]["end"] - B["g1_mad"] + 0.2), B["g1_mad"] - 0.1, -17)
put(engine8(s1["end"] - B["g1_bug"]), B["g1_bug"], -17, bed=True)
for i, rt in enumerate([B["g1_ram"], B["g1_ram"] + 0.5, B["g1_ram"] + 0.95, B["g1_born"] - 0.3]):
    put(crash(), rt - 0.02, -9 - i)
put(arp8([392, 523, 659, 784, 1047, 1319], 0.05, "square", 0.35), B["g1_born"] - 0.2, -12)

# ---- GTA 2
s2 = S["gta2"]
put(hum(s2["end"] - s2["start"], 60), s2["start"], -20, bed=True)
put(riser(0.5), B["g2_rockstar"] - 0.7, -18)
put(impact(0.8), B["g2_rockstar"] - 0.25, -8)
put(ding(2093, 1.4, 0.35), B["g2_rockstar"] - 0.2, -15)
put(whoosh(0.35, True, (0.9, 0.2)), L["g2b"]["start"] - 0.15, -14)
put(arp8([660, 990], 0.07, "square", 0.12), B["g2_help"] + 0.05, -15)
put(arp8([300, 200], 0.08, "saw", 0.2), B["g2_rival"] + 0.05, -14)

# ---- GTA III
s3 = S["gta3"]
put(riser(B["g3_3d"] - s3["start"] - 0.4), s3["start"] + 0.5, -15)
put(impact(1.0), B["g3_3d"], -6)
put(rain(L["g3c"]["start"] - B["g3_3d"]), B["g3_3d"] - 0.1, -16, bed=True)
put(thunder(), B["g3_3d"] + 0.3, -16)
put(engine_pass(2.4, 95), B["g3_3d"] + 0.5, -17)
put(sonar(), L["g3b"]["start"] - 0.05, -15)
put(rain(s3["end"] - L["g3c"]["start"] + 0.2), L["g3c"]["start"] - 0.15, -24, bed=True)
put(page_flip(), L["g3c"]["start"] - 0.1, -12)
put(stamp_snd(), B["g3_delay"] + 0.02, -8)
put(whoosh(0.4, True, (-0.9, 0.0)), B["g3_delay"] + 0.6, -14)
put(siren8(0.6), B["g3_delay"] + 0.8, -20)
put(spray(0.6), B["g3_bw"] - 0.35, -11)

# ---- Vice City
sv = S["vc"]
put(vhs_rewind(B["vc_80s"] - sv["start"]), sv["start"] + 0.02, -12)
put(vhs_clunk(), B["vc_80s"] + 0.02, -8)
put(synth_stab(), B["vc_80s"] + 0.06, -9)
put(waves(sv["end"] - B["vc_80s"] + 0.3), B["vc_80s"], -19, bed=True)
put(pop(700), L["vcb"]["start"], -12)
put(whoosh(0.3, True, (-0.8, -0.2)), B["vc_liotta"] - 0.1, -16)
put(engine_pass(2.6, 120), sv["start"] + 1.2, -21)

# ---- San Andreas
ss = S["sa"]
for i in range(3):
    put(whoosh(0.35, i % 2 == 0, (-0.6 + i * 0.6, -0.6 + i * 0.6)), ss["start"] + i * 0.18, -15)
    put(stamp_snd(), B["sa_three"] + i * 0.2 + 0.08, -12 - i)
put(hiss(0.22), ss["start"] + 0.9, -20)
put(hiss(0.22), ss["start"] + 1.35, -21)
for i in range(5):
    put(whoosh(0.3, True, ((-0.8, 0) if i % 2 == 0 else (0.8, 0))), B["sa_fat"] - 0.9 + i * 0.16, -19)
put(boing(), B["sa_fat"] - 0.1, -9)
put(pop(500), B["sa_coffee"] - 0.12, -10)
put(hiss(0.4), B["sa_coffee"], -20)
put(stamp_snd(), B["sa_ao"] - 0.02, -6)
put(beep(1000, 0.4), B["sa_ao"] + 0.05, -15)
for i in range(8):
    put(thud(70 + i * 9), B["sa_pull"] + 0.08 + i * 0.09, -15)
put(stamp_snd(), B["sa_pull"] + 0.02, -10)
put(fanfare(), L["sad"]["start"] + 0.27, -11)
put(impact(0.6), B["sa_king"] - 0.08, -10)

# ---- GTA IV
s4 = S["gta4"]
put(city_amb(s4["end"] - s4["start"] + 0.4), s4["start"] - 0.2, -14, bed=True)
put(rain(s4["end"] - s4["start"]), s4["start"], -27, bed=True)
put(whoosh(0.7, False, (0.3, -0.3)), B["g4_real"] - 0.3, -15)
put(counter_ticks(1.0), B["g4_money"] - 0.5, -16)
put(cash_register(), B["g4_money"] + 0.45, -9)

# ---- GTA V
s5 = S["gta5"]
for i in range(3):
    put(pop(300 + i * 90), B["g5_three"] + i * 0.17 - 0.05, -9)
put(whoosh(0.45, True, (0, 0)), B["g5_switch"] - 0.2, -8)
put(impact(0.6), B["g5_switch"] + 0.25, -11)
put(whoosh(0.45, False, (0, 0)), B["g5_switch"] + 0.3, -11)
put(impact(0.8), B["g5_switch"] + 0.72, -10)
put(cash_register(), L["g5b"]["start"] - 0.12, -9)
put(counter_ticks(1.1), B["g5_billion"] - 0.6, -16)
put(stamp_snd(), B["g5_record"] - 0.05, -8)
put(riser(1.2), L["g5c"]["start"] - 0.1, -17)
put(counter_ticks(1.0), B["g5_units"] - 0.4, -17)
put(ding(1760, 1.0, 0.25), B["g5_units"] + 0.62, -14)

# ---- GTA VI
s6 = S["gta6"]
t0 = s6["start"] + 0.1
k = 0
while t0 + k * 0.5 < L["g6b"]["start"] - 0.1:
    put(clock_tick(k % 2 == 0), t0 + k * 0.5, -14)
    k += 1
# year flips 2013 -> 2021
for i in range(8):
    p = i / 8
    put(tick(2600), s6["start"] + 0.1 + (B["g6_wait"] + 0.6 - s6["start"] - 0.1) * (0.5 - 0.5 * np.cos(np.pi * p)), -18)
put(glitch(0.5), L["g6b"]["start"] - 0.12, -9)
put(keyboard(L["g6c"]["start"] - L["g6b"]["start"]), L["g6b"]["start"], -16)
put(stamp_snd(), B["g6_leak"] + 0.02, -8)
put(alarm(3), B["g6_leak"] + 0.1, -18)
put(pop(600), L["g6c"]["start"] - 0.1, -10)
put(tick(5000), L["g6c"]["start"] + 0.3, -12)
put(counter_ticks(1.2), B["g6_views"] - 0.9, -17)
put(ding(2093, 1.2, 0.3), B["g6_views"] + 0.32, -13)
put(riser(1.0), L["g6d"]["start"] - 1.15, -12)
put(impact(1.2), L["g6d"]["start"] - 0.2, -3)
put(waves(s6["end"] - L["g6d"]["start"] + 0.5), L["g6d"]["start"] - 0.2, -18, bed=True)
put(stamp_snd(), B["g6_date"] + 0.15, -9)
put(impact(1.0), B["g6_release"] - 0.1, -5)
put(fanfare(), B["g6_release"] - 0.05, -13)
put(ding(1568, 0.9, 0.2), B["g6_release"], -14)
put(cash_register(), B["g6_money"] - 0.18, -8)
for kk in range(6):
    put(firework([-0.6, 0.5, -0.2, 0.7, -0.7, 0.2][kk]), B["g6_money"] + kk * 0.38 - 0.45, -13)
put(impact(0.7), B["g6_biggest"], -12)

# ---- outro
so = S["outro"]
for i in range(8):
    put(pop(350 + i * 40), so["start"] + i * 0.06, -22)
put(ding(1046, 1.2, 0.35), L["o2"]["start"] - 0.02, -13)
put(impact(1.0), TOTAL - 1.1, -12)

# ------------------------------------------------------------------ voice track
voice = np.zeros(N)
for l in TL["lines"]:
    v, sr = sf.read(os.path.join(ROOT, "build", "tts", l["id"] + ".wav"))
    o = int(l["start"] * SR)
    voice[o:o + len(v)] += v

# gentle voice chain: HP, light compression, presence
voice = hp(voice, 75)
env = np.sqrt(lp(voice ** 2, 12, 1).clip(0)) + 1e-6
thr = 10 ** (-20 / 20)
gain = np.where(env > thr, (env / thr) ** (1 / 2.5 - 1), 1.0)
voice = voice * lp(gain, 30, 1)
pres = bp(voice, 2500, 6000)
voice = voice + pres * 0.25
voice = norm(voice, 0.89)
voice_st = np.stack([voice, voice], axis=1)

# sidechain: everything ducks while the narrator talks (fast attack, slow release)
act = (np.abs(voice) > 0.015).astype(float)
k = int(0.12 * SR)
act = np.convolve(act, np.ones(k) / k, mode="same") > 0.05     # speech regions incl. tiny gaps
env = act.astype(float)
a_att, a_rel = np.exp(-1 / (0.03 * SR)), np.exp(-1 / (0.28 * SR))
env = signal.lfilter([1 - a_rel], [1, -a_rel], env)            # release smoothing
env = np.maximum(env, signal.lfilter([1 - a_att], [1, -a_att], act.astype(float)))
env = np.clip(env * 1.4, 0, 1)
beds *= (1 - 0.72 * env)[:, None]        # ambience: about -11 dB under speech
sfx *= (1 - 0.55 * env)[:, None]         # hits/effects: about -7 dB under speech
fx = sfx + beds

# levels: keep SFX clearly under the voice
fx = fx / (np.max(np.abs(fx)) + 1e-9) * 0.62
mix = voice_st * 0.82 + fx * 0.75
pk = np.max(np.abs(mix))
if pk > 0.98:
    mix = np.tanh(mix / pk * 1.2) * 0.98 / np.tanh(1.2)

out = os.path.join(ROOT, "build", "audio")
os.makedirs(out, exist_ok=True)
n_total = int(TOTAL * SR)
sf.write(os.path.join(out, "voice.wav"), (voice_st * 0.82)[:n_total], SR, subtype="PCM_24")
sf.write(os.path.join(out, "sfx.wav"), (fx * 0.75)[:n_total], SR, subtype="PCM_24")
sf.write(os.path.join(out, "mix.wav"), mix[:n_total], SR, subtype="PCM_24")
print("audio written", TOTAL)
