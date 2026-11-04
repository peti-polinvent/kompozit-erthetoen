"""
make_music.py – szintetikus, jogtiszta „trailer” zene és hangeffektek a videóhoz
=================================================================================

Nem mintákból, hanem tisztán számolt hullámformákból épül (numpy), ezért nincs
licenc-kérdés. A zene a jelenetek kezdőidejéhez igazodik: minden jelenetváltásra
egy mély ütés („braam” + dobütés) esik, előtte 1,5 s emelkedő „riser”.

    python video/make_music.py --plan video/scene_plan.json --out video/music
      → music/music.wav (sztereó 48 kHz), music/hit.wav, music/whoosh.wav, music/riser.wav

Zenei szerkezet (A-moll, 100 BPM):
  1. jelenet  – mély zúgás (drone), ritka ütések
  2. jelenet  – belép a pulzáló basszus és a lábdob
  3. jelenet  – pulzus + pergő, akkordmenet Am–F–C–G
  4. jelenet  – teljes: dobok, akkordok, magas „tick”
  5. jelenet  – visszavétel: drone + akkord, nyugodtabb
  6. jelenet  – teljes, a végén záróütés és lecsengés
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
    return [0.35, 0.6, 0.75, 1.0, 0.45, 1.0][scene_index]


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
    a = ap.parse_args()
    main(a.plan, a.out)
