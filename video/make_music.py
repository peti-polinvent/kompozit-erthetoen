"""
make_music.py – szintetikus, jogtiszta „trailer” zene és hangeffektek a videóhoz
=================================================================================

Nem mintákból, hanem tisztán számolt hullámformákból épül (numpy), ezért nincs
licenc-kérdés. A zene a jelenetek kezdőidejéhez igazodik: minden jelenetváltásra
egy mély ütés („braam” + dobütés) esik, előtte 1,5 s emelkedő „riser”.

    python video/make_music.py --plan video/scene_plan.json --out video/music
      → music/music.wav (sztereó 48 kHz), music/hit.wav, music/whoosh.wav, music/riser.wav

Zenei szerkezet (A-moll, 100 BPM):
  1. recept   – drone + ütés
  2. hozzávalók – belép a pulzáló basszus és a lábdob
  3. rétegrend – pulzus + pergő, akkordmenet Am–F–C–G
  4. injektálás – teljes: dobok, akkordok, magas „tick”
  5. bontás   – majdnem teljes
  6. kész     – visszavétel, záróütés és lecsengés
"""

import argparse
import json
import math
import os

import numpy as np

SR = 48000
BPM = 100
BEAT = 60.0 / BPM
NOTE = {"A1": 55.0, "C2": 65.41, "E2": 82.41, "F2": 87.31, "G2": 98.0, "A2": 110.0,
        "C3": 130.81, "E3": 164.81, "F3": 174.61, "G3": 196.0}
# akkordmenet (gyökér + kvint + terc oktávval feljebb), ütemenként váltva
CHORDS = [("A1", "E2", "C3"), ("F2", "C3", "A2"), ("C2", "G2", "E3"), ("G2", "E3", "G3")]


def env(n, a, d, s_level, r, sustain_n):
    """ADSR-burkoló mintákban."""
    a, d, r = int(a * SR), int(d * SR), int(r * SR)
    e = np.zeros(n)
    i = 0
    seg = min(a, n); e[:seg] = np.linspace(0, 1, seg); i += seg
    seg = min(d, n - i); e[i:i + seg] = np.linspace(1, s_level, seg); i += seg
    seg = min(sustain_n, n - i); e[i:i + seg] = s_level; i += seg
    seg = min(r, n - i); e[i:i + seg] = np.linspace(s_level, 0, seg); i += seg
    return e


def lowpass(x, cutoff):
    """Egyszerű egypólusú aluláteresztő (elég a hangulathoz)."""
    rc = 1.0 / (2 * math.pi * cutoff)
    alpha = (1.0 / SR) / (rc + 1.0 / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):          # numpy-ban vektorizálva nehéz; a hossz miatt elfogadható
        acc += alpha * (x[i] - acc)
        y[i] = acc
    return y


def lowpass_fast(x, cutoff):
    """Aluláteresztő FFT-vel (gyors, a teljes sávra)."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1.0 / (1.0 + (f / cutoff) ** 4)
    return np.fft.irfft(X, n=len(x))


def bandpass_fast(x, lo, hi):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= (1.0 / (1.0 + (lo / np.maximum(f, 1)) ** 4)) * (1.0 / (1.0 + (f / hi) ** 4))
    return np.fft.irfft(X, n=len(x))


def saw(freq, n, detune=0.0):
    t = np.arange(n) / SR
    s = 0
    for k, d in ((1, 0), (1, detune), (1, -detune)):
        ph = (t * freq * (1 + d)) % 1.0
        s = s + (2 * ph - 1)
    return s / 3


def sine(freq, n, phase=0.0):
    return np.sin(2 * math.pi * freq * np.arange(n) / SR + phase)


def reverb_tail(x, seconds=1.2, decay=4.0):
    """Olcsó „terem”: néhány késleltetett, csillapított másolat."""
    n = len(x)
    out = np.copy(x)
    rng = np.random.default_rng(7)
    for k in range(10):
        d = int(SR * (0.03 + 0.09 * k + rng.uniform(0, 0.02)))
        g = math.exp(-decay * (d / SR) / seconds) * 0.35
        out[d:] += g * x[:n - d]
    return out


# ---- effektek ------------------------------------------------------------------

def make_hit(strength=1.0):
    """Mély ütés: lábdob-szerű lecsúszó szinusz + zajcsattanás + lecsengés."""
    n = int(1.8 * SR)
    t = np.arange(n) / SR
    f = 32 + 110 * np.exp(-t * 14)
    body = np.sin(2 * math.pi * np.cumsum(f) / SR) * np.exp(-t * 2.2)
    rng = np.random.default_rng(3)
    noise = rng.standard_normal(n)
    crack = lowpass_fast(noise, 2500) * np.exp(-t * 18) * 0.5
    x = (body * 1.0 + crack) * strength
    x = np.tanh(x * 1.6) * 0.9
    return reverb_tail(x, 1.5, 3.0)


def make_whoosh(seconds=0.7):
    n = int(seconds * SR)
    rng = np.random.default_rng(5)
    noise = rng.standard_normal(n)
    t = np.linspace(0, 1, n)
    x = bandpass_fast(noise, 300, 5000)
    e = np.sin(math.pi * t) ** 2 * (0.3 + 0.7 * t)       # erősödik, a végén csattan
    return x * e * 0.6


def make_riser(seconds=1.5):
    n = int(seconds * SR)
    rng = np.random.default_rng(11)
    noise = rng.standard_normal(n)
    t = np.linspace(0, 1, n)
    x = bandpass_fast(noise, 200, 6000)
    # emelkedő hang is
    f = 110 * 2 ** (t * 2)
    tone = np.sin(2 * math.pi * np.cumsum(f) / SR)
    e = t ** 2.2
    return (x * 0.5 + tone * 0.35) * e * 0.7


def make_braam(seconds=2.6):
    n = int(seconds * SR)
    x = saw(NOTE["A1"], n, 0.006) + 0.6 * saw(NOTE["E2"], n, 0.005) + 0.5 * saw(NOTE["A1"] / 2, n, 0.004)
    x = lowpass_fast(x, 900)
    x = np.tanh(x * 2.2)
    e = env(n, 0.08, 0.5, 0.75, 1.4, int(0.6 * SR))
    return reverb_tail(x * e * 0.7, 1.5, 2.5)


# ---- zene ----------------------------------------------------------------------

def intensity_for(scene_index):
    return [0.5, 0.65, 0.8, 1.0, 0.9, 0.6][scene_index]


def build_music(scenes, total, tail=2.5):
    n = int((total + tail) * SR)
    mix = np.zeros(n)
    t_all = np.arange(n) / SR
    rng = np.random.default_rng(1)

    # intenzitás-görbe idő szerint (jelenetenként, 0.8 s átmenettel)
    inten = np.zeros(n)
    for s in scenes:
        a = int(s["start"] * SR); b = int((s["start"] + s["length"]) * SR)
        inten[a:b] = intensity_for(s["index"])
    inten = lowpass_fast(inten, 1.2)
    inten = np.clip(inten, 0, 1)

    # 1) drone – mindig szól, az intenzitással erősödik
    drone = (sine(NOTE["A1"], n) * 0.5 + 0.35 * saw(NOTE["A1"], n, 0.004) + 0.25 * sine(NOTE["E2"], n))
    drone = lowpass_fast(drone, 400) * (0.18 + 0.12 * inten)
    # lassú lüktetés
    drone *= 0.85 + 0.15 * np.sin(2 * math.pi * t_all / (BEAT * 4))
    mix += drone

    # 2) pulzáló basszus (nyolcadok), akkordgyökéren – csak ha az intenzitás > 0.5
    bass = np.zeros(n)
    half = BEAT / 2
    k = 0
    tt = scenes[0]["start"]
    while tt < total:
        bar = int(tt / (BEAT * 4)) % len(CHORDS)
        root = NOTE[CHORDS[bar][0]]
        i0 = int(tt * SR); ln = int(half * 0.9 * SR)
        if i0 + ln < n:
            seg = saw(root, ln, 0.01) * env(ln, 0.005, 0.12, 0.5, 0.08, ln)
            seg = lowpass_fast(seg, 500 + 500 * ((k % 2) == 0))
            bass[i0:i0 + ln] += seg
        tt += half; k += 1
    gate = np.clip((inten - 0.5) / 0.3, 0, 1)
    mix += bass * 0.32 * gate

    # 3) akkordpad (lassú, széles) – az intenzitással
    pad = np.zeros(n)
    bar_len = int(BEAT * 4 * SR)
    for b in range(int(n / bar_len) + 1):
        ch = CHORDS[b % len(CHORDS)]
        i0 = b * bar_len; ln = min(bar_len + int(0.4 * SR), n - i0)
        if ln <= 0:
            break
        seg = sum(saw(NOTE[nm], ln, 0.008) * (0.6 if j else 1.0) for j, nm in enumerate(ch))
        seg = lowpass_fast(seg, 1200) * env(ln, 0.35, 0.3, 0.8, 0.4, ln)
        pad[i0:i0 + ln] += seg
    mix += pad * 0.09 * (0.3 + 0.7 * inten)

    # 4) dobok: lábdob negyedekre (2. jelenettől), pergő 2-4-re (3. jelenettől), tick nyolcadokra
    kick = make_hit(0.55)[: int(0.5 * SR)]
    snare_n = int(0.22 * SR)
    snare = (bandpass_fast(rng.standard_normal(snare_n), 800, 6000) * np.exp(-np.arange(snare_n) / SR * 22)
             + sine(185, snare_n) * np.exp(-np.arange(snare_n) / SR * 30) * 0.6) * 0.5
    tick_n = int(0.04 * SR)
    tick = bandpass_fast(rng.standard_normal(tick_n), 5000, 12000) * np.exp(-np.arange(tick_n) / SR * 90) * 0.25
    tt = scenes[0]["start"]; beat_i = 0
    while tt < total:
        i0 = int(tt * SR)
        lvl = inten[min(i0, n - 1)]
        if lvl > 0.5 and i0 + len(kick) < n:
            mix[i0:i0 + len(kick)] += kick * (0.5 + 0.5 * lvl) * 0.8
        if lvl > 0.65 and beat_i % 2 == 1 and i0 + snare_n < n:
            mix[i0:i0 + snare_n] += snare * lvl
        for h in (0, 1):
            j0 = i0 + int(h * BEAT / 2 * SR)
            if lvl > 0.55 and j0 + tick_n < n:
                mix[j0:j0 + tick_n] += tick * (0.6 + 0.4 * h) * lvl
        tt += BEAT; beat_i += 1

    # 5) jelenetváltások: riser előtte, braam + ütés rajta
    hit = make_hit(1.0); braam = make_braam(); riser = make_riser(1.5)
    for s in scenes:
        st = s["start"] - 0.35         # kicsit a narráció kezdete előtt
        i0 = int(st * SR)
        r0 = i0 - len(riser)
        if r0 >= 0:
            mix[r0:i0] += riser * (0.5 + 0.5 * intensity_for(s["index"]))
        if i0 >= 0 and i0 + len(hit) < n:
            mix[i0:i0 + len(hit)] += hit * 0.9
            mix[i0:i0 + len(braam)] += braam * (0.6 + 0.4 * intensity_for(s["index"]))
    # záróütés a végén
    i0 = int(total * SR)
    if i0 + len(hit) < n:
        mix[i0:i0 + len(hit)] += hit * 1.0

    # 6) lecsengés a legvégén
    fade = np.ones(n); fo = int(2.0 * SR); fade[-fo:] = np.linspace(1, 0, fo)
    mix *= fade
    mix = np.tanh(mix * 1.1) * 0.9
    # sztereó: kis szélesítés (jobb csatorna 8 ms-mal késik, ellenfázis-mentes)
    d = int(0.008 * SR)
    left = mix
    right = np.concatenate([np.zeros(d), mix[:-d]])
    return np.stack([left, right], axis=1)


# =====================================================================================
# LIGHT stílus: könnyed, meleg, 104 BPM, C-dúr (C–G–Am–F). Marimba/kalimba-szerű pengetett
# arpeggio, lágy szubbasszus, puha lábdob + taps a 2-re és 4-re, shaker tizenhatodok, meleg pad.
# Rövid nyitó „sting”, finom felépülés a 4. jelenetig, feloldó akkord a zárókártya alatt.
# A zene a narráció alatt −10 dB-lel lehalkul (a TTS szóhatár-idők adják az „oldalláncot”).
# =====================================================================================
L_BPM = 104
L_BEAT = 60.0 / L_BPM
L_CHORDS = [  # (basszus MIDI, akkordhangok MIDI) – I–V–vi–IV
    (36, [60, 64, 67, 72]), (43, [59, 62, 67, 71]), (45, [57, 60, 64, 69]), (41, [57, 60, 65, 69])]


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def marimba(f, dur=0.6, bright=1.0):
    n = int(dur * SR); t = np.arange(n) / SR
    x = (np.sin(2 * math.pi * f * t) * np.exp(-t * 7)
         + 0.22 * bright * np.sin(2 * math.pi * 3.98 * f * t) * np.exp(-t * 28)
         + 0.06 * bright * np.sin(2 * math.pi * 9.9 * f * t) * np.exp(-t * 60))
    x[:96] *= np.linspace(0, 1, 96)
    return x


def soft_kick():
    n = int(0.32 * SR); t = np.arange(n) / SR
    f = 48 + 75 * np.exp(-t * 32)
    return np.sin(2 * math.pi * np.cumsum(f) / SR) * np.exp(-t * 11)


def clap(rng):
    n = int(0.25 * SR); t = np.arange(n) / SR
    x = bandpass_fast(rng.standard_normal(n), 900, 3200)
    e = np.zeros(n)
    for k, d in enumerate((0.0, 0.011, 0.022)):
        i = int(d * SR); e[i:] += np.exp(-(t[: n - i]) * (60 if k < 2 else 16))
    return x * e * 0.5


def shaker(rng):
    n = int(0.06 * SR); t = np.arange(n) / SR
    x = bandpass_fast(rng.standard_normal(n), 5000, 11000)
    return x * np.minimum(t / 0.012, 1.0) * np.exp(-t * 45)


def place(buf, x, t, gain=1.0):
    i0 = int(t * SR)
    if i0 < 0 or i0 >= len(buf):
        return
    m = min(len(x), len(buf) - i0)
    buf[i0:i0 + m] += x[:m] * gain


def smooth_steps(n, pts):
    """Lépcsős intenzitás-görbe (idő, érték) pontokból, lágy átmenettel."""
    y = np.zeros(n)
    for (t0, v), nxt in zip(pts, pts[1:] + [(n / SR, None)]):
        y[int(t0 * SR):int(nxt[0] * SR)] = v
    return lowpass_fast(y, 0.6)


def build_music_light(plan, card_t):
    sc = plan["scenes"]
    total = plan["total_frames"] / plan["fps"]
    n = int((total + 0.2) * SR)
    rng = np.random.default_rng(4)
    starts = [s["start"] for s in sc]
    starts[0] = 0.0
    # rétegek be-/kikapcsolása jelenetenként: (arp, pad, bass, kick, clap, shaker, arp-oktáv)
    lv = {0: (1, 1, 0, 0, 0, 0.5, 0), 1: (1, 1, 1, 1, 0, 0.8, 0), 2: (1, 1, 1, 1, 1, 1, 0),
          3: (1, 1, 1, 1, 1, 1, 1), 4: (1, 1, 1, 1, 1, 0.9, 0), 5: (1, 1, 0.6, 0, 0, 0.4, 0)}
    curves = [smooth_steps(n, [(starts[i], lv[i][k]) for i in range(len(sc))]) for k in range(7)]
    end_t = card_t if card_t else total - 3.0
    stop = np.ones(n); stop[int(end_t * SR):] = 0; stop = lowpass_fast(stop, 3.0)   # a ritmus a kártyánál elhal
    arp, pad, bass, drums, shk = (np.zeros(n) for _ in range(5))
    t0 = 1.15                     # a nyitó „sting” után indul a groove
    bar = 4 * L_BEAT
    b = 0
    while t0 + b * bar < end_t + bar:
        tb = t0 + b * bar
        root, ch = L_CHORDS[b % 4]
        i = int(min(tb, total) * SR) % n
        up = 12 if curves[6][i] > 0.5 else 0
        for e, k in enumerate([0, 1, 2, 3, 2, 1, 0, 2]):
            te = tb + e * L_BEAT / 2
            if te < end_t:
                place(arp, marimba(mtof(ch[k] + up), 0.55, 0.8 + 0.4 * (e % 2 == 0)), te, 0.9 - 0.25 * (e % 2))
        # pad: az akkord egy oktávval lejjebb, lassú felfutással
        ln = int((bar + 0.6) * SR)
        tt = np.arange(ln) / SR
        seg = sum(saw(mtof(m - 12), ln, 0.006) for m in ch[:3])
        place(pad, seg * np.minimum(tt / 0.5, 1) * np.minimum((bar + 0.6 - tt) / 0.6, 1), tb)
        for q in range(4):        # szubbasszus negyedekre, lágy
            tq = tb + q * L_BEAT
            if tq < end_t:
                ln2 = int(L_BEAT * 0.9 * SR); t2 = np.arange(ln2) / SR
                place(bass, np.sin(2 * math.pi * mtof(root - 12 + 12) * t2) * np.minimum(t2 / 0.01, 1) * np.exp(-t2 * 3),
                      tq, 0.9 if q % 2 == 0 else 0.6)
                place(drums, soft_kick() * (q % 2 == 0), tq, 1.0)
                if q % 2 == 1:
                    place(drums, clap(rng), tq, 0.0)          # helyfoglaló (a taps külön sávon)
            for s16 in range(4):
                ts = tq + s16 * L_BEAT / 4
                if ts < end_t:
                    place(shk, shaker(rng), ts, (1.0 if s16 == 2 else 0.55))
        b += 1
    claps = np.zeros(n)
    b = 0
    while t0 + b * bar < end_t:
        for q in (1, 3):
            place(claps, clap(rng), t0 + b * bar + q * L_BEAT)
        b += 1
    pad = lowpass_fast(pad, 1400)
    arp = reverb_tail(arp, 0.9, 4.0)
    mix = (arp * 0.30 * curves[0] + pad * 0.05 * curves[1] + bass * 0.30 * curves[2] * stop
           + drums * 0.42 * curves[3] * stop + claps * 0.20 * curves[4] * stop + shk * 0.10 * curves[5] * stop)
    # nyitó sting: felfutó C-dúr arpeggio + csengő
    for k, m in enumerate([60, 64, 67, 72, 76, 79]):
        place(mix, marimba(mtof(m), 1.2), 0.08 + k * 0.07, 0.30)
    place(mix, marimba(mtof(84), 1.6, 1.4), 0.5, 0.18)
    # feloldó akkord a zárókártya alatt (Cadd9), hosszan lecsengő
    if card_t:
        ln = int(max(total - card_t, 1.0) * SR + 0.2 * SR)
        tt = np.arange(ln) / SR
        ch = sum(saw(mtof(m), ln, 0.005) for m in (48, 55, 62, 64, 67))
        ch = lowpass_fast(ch, 1600) * np.minimum(tt / 0.3, 1) * np.exp(-tt * 0.5)
        place(mix, ch, card_t, 0.10)
        for k, m in enumerate([72, 76, 79, 86]):
            place(mix, marimba(mtof(m), 2.0), card_t + k * 0.09, 0.22)
        place(mix, soft_kick(), card_t, 0.4)
    fo = int(1.2 * SR)
    mix[-fo:] *= np.linspace(1, 0, fo)
    return mix


def voice_duck(plan, n, depth_db=-10.0):
    """Oldallánc-lehalkítás a szóhatárokból: beszéd alatt depth_db, 0,12 s támadás, 0,45 s elengedés."""
    g = np.zeros(n)
    for s in plan["scenes"]:
        for w in s.get("words") or []:
            a = int((s["start"] + w["start"] - 0.12) * SR); b = int((s["start"] + w["end"] + 0.25) * SR)
            g[max(a, 0):max(min(b, n), 0)] = 1.0
    g = lowpass_fast(g, 2.0)
    g = np.clip(g / max(g.max(), 1e-6), 0, 1)
    return 10 ** (depth_db * g / 20)


def sfx_light(plan, cue_events, n, card_t):
    """Finom hangeffektek: pipa/pop (checklista, címke), légies whoosh (jelenetváltás), sziszegés (vákuum be)."""
    rng = np.random.default_rng(9)
    out = np.zeros(n)
    def tick():
        m = int(0.07 * SR); t = np.arange(m) / SR
        f = 1500 * np.exp(-t * 8)
        return np.sin(2 * math.pi * np.cumsum(f) / SR) * np.exp(-t * 70) * 0.5
    def pop():
        m = int(0.08 * SR); t = np.arange(m) / SR
        f = 380 + 520 * np.exp(-t * 60)
        return np.sin(2 * math.pi * np.cumsum(f) / SR) * np.exp(-t * 45) * 0.45
    def whoosh(d=0.75):
        m = int(d * SR); u = np.linspace(0, 1, m)
        x = bandpass_fast(rng.standard_normal(m), 700, 7000)
        return x * np.sin(math.pi * u) ** 3 * 0.22
    def hiss(d=1.4):
        m = int(d * SR); t = np.arange(m) / SR
        x = bandpass_fast(rng.standard_normal(m), 2500, 10000)
        return x * np.minimum(t / 0.06, 1) * np.exp(-t * 2.2) * 0.16
    for kind, t in cue_events:
        if kind == "tick":
            place(out, tick(), t)
        elif kind == "pop":
            place(out, pop(), t)
        elif kind == "whoosh":
            place(out, whoosh(), t - 0.45)
        elif kind == "hiss":
            place(out, hiss(), t)
    return out


def main_light(plan_path, out_dir):
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import cues
    with open(plan_path, encoding="utf-8") as f:
        plan = json.load(f)
    total = plan["total_frames"] / plan["fps"]
    n = int((total + 0.2) * SR)
    last = plan["scenes"][-1]
    kc = cues.extra(last, "card")
    card_t = last["start"] + kc - 0.25 if kc is not None else None
    ev = []
    for s in plan["scenes"]:
        if s["index"] > 0:
            ev.append(("whoosh", s["start"]))
        for e in (cues.resolve(s) if s.get("words") else []):
            ev.append(("tick" if s["index"] == 1 else "pop", s["start"] + e["t0"] - 0.08))
        vt = cues.extra(s, "vakuum")
        if vt is not None:
            ev.append(("hiss", s["start"] + vt + 0.25))
    if card_t:
        ev.append(("whoosh", card_t + 0.1))
    music = build_music_light(plan, card_t)[:n]
    music = music / (np.sqrt(np.mean(music ** 2)) + 1e-9) * 10 ** (-18 / 20)   # ~ −18 dBFS RMS a duck előtt
    music *= voice_duck(plan, len(music))
    sfx = sfx_light(plan, ev, len(music), card_t)
    d = int(0.006 * SR)
    st = np.stack([music, np.concatenate([np.zeros(d), music[:-d]])], axis=1)
    os.makedirs(out_dir, exist_ok=True)
    write_wav(os.path.join(out_dir, "music.wav"), np.tanh(st * 1.2) / 1.2)
    write_wav(os.path.join(out_dir, "sfx.wav"), np.stack([sfx, sfx], axis=1) * 0.6)
    print(f"[zene] light: {total:.1f} s, {len(ev)} effekt → {out_dir}/music.wav, sfx.wav")


def write_wav(path, x):
    import wave
    x = np.clip(x, -1, 1)
    if x.ndim == 1:
        x = x[:, None]
    pcm = (x * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(x.shape[1]); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def main(plan_path, out_dir):
    with open(plan_path, encoding="utf-8") as f:
        plan = json.load(f)
    scenes = plan["scenes"]
    total = plan["total_seconds"] if "total_seconds" in plan else plan["total_frames"] / plan["fps"]
    os.makedirs(out_dir, exist_ok=True)
    write_wav(os.path.join(out_dir, "music.wav"), build_music(scenes, total))
    write_wav(os.path.join(out_dir, "hit.wav"), make_hit())
    write_wav(os.path.join(out_dir, "whoosh.wav"), make_whoosh())
    write_wav(os.path.join(out_dir, "riser.wav"), make_riser())
    print(f"[zene] {total:.1f} s + lecsengés → {out_dir}/music.wav; effektek: hit, whoosh, riser")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", default=os.path.join(os.path.dirname(__file__), "scene_plan.json"))
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "music"))
    ap.add_argument("--style", default="light")
    a = ap.parse_args()
    (main_light if a.style == "light" else main)(a.plan, a.out)
