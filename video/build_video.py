"""
build_video.py – a videó összeállítása: ütemterv, felirat, render, vágás
=========================================================================

Lépések:
  1. Narrációs hangfájlok beolvasása: video/tts/NN.aiff|.wav (Mac "say" / egyéb TTS),
     ha nincs, video/tts/NN_espeak.wav (gépi tartalék). Hosszuk → jelenet-ütemterv
     (jelenetek között GAP szünet).
  2. Felirat: assets/kompozit_erthetoen.vtt – mondatonként, a hang hosszával arányosan.
  3. video/scene_plan.json → render_scenes.py (Blender, venv-bpy) → video/frames/*.png
  4. ffmpeg: hangsáv összefűzése szünetekkel, képsor + címfeliratok (drawtext),
     felirat beégetése, H.264 720p → assets/kompozit_erthetoen.mp4; poszterkép.

    python video/build_video.py            # minden lépés
    python video/build_video.py --no-render   # csak hang+felirat+vágás (ha a frames/ kész)
    python video/build_video.py --no-render --no-annotate   # ha a frames/ már címkézett is
"""

import json
import os
import re
import subprocess
import sys
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
TTS = os.path.join(HERE, "tts")
FRAMES = os.path.join(HERE, "frames")
ASSETS = os.path.join(ROOT, "assets")
PREVIEW = os.environ.get("PREVIEW") == "1"   # PREVIEW=1 → 640×360, 12 fps (gyors ellenőrzés)
ACTION = os.environ.get("ACTION") == "1"     # ACTION=1 → akciófilmes változat: trailer-hang, zene, effektek, szélesvászon
BAR = 48                                      # px (720p): fekete sáv fent/lent az akció-változatban
MUSIC = os.path.join(HERE, "music")
FPS = 12 if PREVIEW else 24
RES = (640, 360) if PREVIEW else (1280, 720)
GAP = 0.8            # s szünet a jelenetek között
LEAD = 1.0           # s csend az elején
TAIL = 1.5           # s a végén
BPY_PY = os.environ.get("BPY_PYTHON", os.path.expanduser("~/venv-bpy/bin/python"))
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

TITLES = [  # (jelenet-index, cím) – a jelenet első 3,5 másodpercében jelenik meg
    (0, "Kompozit érthetően – vákuuminfúzió 3D-ben"),
    (1, "Mi a vákuuminfúzió?"),
    (2, "A rétegrend"),
    (3, "Hol áramlik a gyanta?"),
    (4, "Az eredmény"),
    (5, "Így készült: Fusion 360 + Blender + AI"),
]
if os.environ.get("ACTION") == "1":   # akció-változat: rövid, ütős címek (nagy betűvel jelennek meg)
    TITLES = [(0, "Kompozit érthetően"), (1, "A vákuum dolgozik"), (2, "A rétegrend"),
              (3, "Indul a gyanta"), (4, "Az eredmény"), (5, "Így készült")]


def dur(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                   "-of", "csv=p=0", path], text=True)
    return float(out.strip())


def trim_silence(src, i):
    """Saját felvételnél: az eleji/végi csend levágása (−35 dB alatt), mono 48 kHz WAV."""
    out_dir = os.path.join(TTS, "trimmed")
    os.makedirs(out_dir, exist_ok=True)
    dst = os.path.join(out_dir, f"{i:02d}.wav")
    af = ("silenceremove=start_periods=1:start_threshold=-35dB:start_silence=0.15,"
          "areverse,silenceremove=start_periods=1:start_threshold=-35dB:start_silence=0.25,areverse,"
          "highpass=f=80,aformat=sample_rates=48000:channel_layouts=mono")
    subprocess.check_call(["ffmpeg", "-y", "-v", "error", "-i", src, "-af", af, dst])
    if ACTION:
        return trailer_voice(dst, i)
    return dst


def trailer_voice(src, i):
    """Akció-változat: mélyebb, rekedtesebb „előzetes-hang” – 3 félhanggal lejjebb (rubberband),
    mély-kiemelés, kompresszor, enyhe terem-zengés, limiter. A felvétel maga nem változik."""
    dst = os.path.join(TTS, "trimmed", f"{i:02d}_trailer.wav")
    shift = "" if os.environ.get("VOICE") == "ai" else "rubberband=pitch=0.84:tempo=0.97,"   # az AI-hang már mély
    af = (shift +
          "equalizer=f=110:t=q:w=1.2:g=5,equalizer=f=250:t=q:w=1:g=2,equalizer=f=3000:t=q:w=1:g=-2,"
          "acompressor=threshold=-22dB:ratio=4:attack=5:release=120:makeup=6,"
          "aecho=0.8:0.6:40|75:0.14|0.08,alimiter=limit=0.95")
    subprocess.check_call(["ffmpeg", "-y", "-v", "error", "-i", src, "-af", af, dst])
    return dst


def pick_audio(i):
    # saját felvétel (m4a/wav/caf/mp3) előnyben; az .aiff a "say" TTS tartaléké
    exts = (".m4a", ".wav", ".caf", ".mp3", ".mp4", ".aiff")
    if os.environ.get("VOICE") == "ai":      # VOICE=ai → az AI-hang (ai_hang.py → NN.mp3) az első
        exts = (".mp3",) + exts
    for ext in exts:
        p = os.path.join(TTS, f"{i:02d}{ext}")
        if os.path.exists(p):
            return trim_silence(p, i), "felvetel"
    p = os.path.join(TTS, f"{i:02d}_espeak.wav")
    if os.path.exists(p):
        return p, "espeak"
    raise SystemExit(f"nincs hangfájl a {i:02d}. jelenethez")


def fmt_ts(s):
    h = int(s // 3600); m = int(s % 3600 // 60); sec = s % 60
    return f"{h:02d}:{m:02d}:{sec:06.3f}"


def split_sentences(text):
    parts = re.split(r"(?<=[.!?:])\s+", text.strip())
    return [p for p in parts if p]


def wrap2(s, width=48):
    """Legfeljebb két sorra tördel, szóhatáron."""
    if len(s) <= width:
        return s
    words = s.split()
    line, lines = "", []
    for w in words:
        if len(line) + len(w) + 1 > width and line:
            lines.append(line); line = w
        else:
            line = (line + " " + w).strip()
    lines.append(line)
    if len(lines) > 2:   # ha túl hosszú, egyenletesen két sorba
        mid = len(words) // 2
        lines = [" ".join(words[:mid]), " ".join(words[mid:])]
    return "\n".join(lines)


def main(render=True):
    with open(os.path.join(TTS, "segments.json"), encoding="utf-8") as f:
        segs = json.load(f)
    keys = sorted(segs)
    # ---- 1. ütemterv ---------------------------------------------------------
    t = LEAD
    scenes = []
    audio_inputs = []
    source = set()
    for i, k in enumerate(keys, start=1):
        path, src = pick_audio(i)
        source.add(src)
        d = dur(path)
        scenes.append(dict(index=i - 1, key=k, start=t, audio_len=d, length=d + GAP, audio=path))
        t += d + GAP
    total = t + TAIL - GAP
    for s in scenes:
        s["frames"] = int(round(s["length"] * FPS))
    scenes[-1]["frames"] += int(round((TAIL - GAP) * FPS))
    total_frames = sum(s["frames"] for s in scenes)
    plan = dict(fps=FPS, total_frames=total_frames, total_seconds=total_frames / FPS, scenes=scenes,
                audio_source=sorted(source))
    with open(os.path.join(HERE, "scene_plan.json"), "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    print(f"[plan] {total_frames} képkocka, {total_frames/FPS:.1f} s, hang: {sorted(source)}")

    # ---- 2. felirat (VTT + SRT) ----------------------------------------------
    cues = []
    for s in scenes:
        sents = split_sentences(segs[s["key"]])
        weights = [len(x) for x in sents]
        W = sum(weights)
        t0 = s["start"]
        for sent, w in zip(sents, weights):
            d = s["audio_len"] * w / W
            cues.append((t0, t0 + d - 0.05, wrap2(sent)))
            t0 += d
    os.makedirs(ASSETS, exist_ok=True)
    with open(os.path.join(ASSETS, "kompozit_erthetoen.vtt"), "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n")
        for a, b, txt in cues:
            f.write(f"{fmt_ts(a)} --> {fmt_ts(b)}\n{txt}\n\n")
    srt = os.path.join(HERE, "kompozit_erthetoen.srt")
    with open(srt, "w", encoding="utf-8") as f:
        for n, (a, b, txt) in enumerate(cues, 1):
            f.write(f"{n}\n{fmt_ts(a).replace('.', ',')} --> {fmt_ts(b).replace('.', ',')}\n{txt}\n\n")
    print(f"[felirat] {len(cues)} cue")

    # ---- 3. render -------------------------------------------------------------
    if render:
        if os.path.isdir(FRAMES):
            shutil.rmtree(FRAMES)
        subprocess.check_call([BPY_PY, os.path.join(HERE, "render_scenes.py"), "--plan",
                               os.path.join(HERE, "scene_plan.json"), "--out", FRAMES,
                               "--size", f"{RES[0]}x{RES[1]}"])
    # címkék (buborék + nyíl) a képkockákra (--no-annotate: már címkézett frames/ esetén kihagyjuk)
    if "--no-annotate" not in sys.argv:
        subprocess.check_call(["/usr/local/bin/python3", os.path.join(HERE, "annotate_frames.py"),
                               "--frames", FRAMES, "--labels", os.path.join(HERE, "labels.json")])

    # ---- 4. hangsáv ------------------------------------------------------------
    # ffmpeg filter: minden hang elé/után csend, összefűzés
    inputs, parts = [], []
    for n, s in enumerate(scenes):
        inputs += ["-i", s["audio"]]
    fc = []
    for n, s in enumerate(scenes):
        delay = int(round(s["start"] * 1000))
        fc.append(f"[{n}:a]aformat=sample_rates=48000:channel_layouts=mono,adelay={delay}|{delay}[a{n}]")
    fc.append("".join(f"[a{n}]" for n in range(len(scenes))) + f"amix=inputs={len(scenes)}:normalize=0,"
              f"apad=whole_dur={total_frames/FPS:.3f},loudnorm=I=-16:TP=-1.5:LRA=11[aout]")
    audio_mix = os.path.join(HERE, "narracio_mix.m4a")
    subprocess.check_call(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(fc),
                           "-map", "[aout]", "-c:a", "aac", "-b:a", "128k", audio_mix])
    if ACTION:
        # zene (make_music.py, a jelenetek kezdőidejéhez igazítva) + whoosh a címek előtt;
        # a zene a narráció alatt automatikusan lehalkul (sidechain-kompresszor)
        subprocess.check_call(["/usr/local/bin/python3", os.path.join(HERE, "make_music.py"), "--plan",
                               os.path.join(HERE, "scene_plan.json"), "--out", MUSIC])
        whoosh = os.path.join(MUSIC, "whoosh.wav")
        w_in, w_fc, w_lbl = [], [], []
        for idx, _ in TITLES:
            d = int(round((scenes[idx]["start"] - 1.2) * 1000))
            if d < 0:
                continue
            n = len(w_lbl)
            w_in += ["-i", whoosh]
            w_fc.append(f"[{n + 2}:a]aformat=sample_rates=48000:channel_layouts=stereo,adelay={d}|{d},volume=0.7[w{n}]")
            w_lbl.append(f"[w{n}]")
        fc2 = w_fc + [
            f"[1:a]volume=0.9[mus]",
            f"[0:a]aformat=sample_rates=48000:channel_layouts=stereo,asplit=2[nar][key]",
            f"[mus][key]sidechaincompress=threshold=0.02:ratio=6:attack=40:release=600:makeup=1[duck]",
            "".join(w_lbl) + f"[duck]amix=inputs={len(w_lbl) + 1}:normalize=0[bed]" if w_lbl else "[duck]anull[bed]",
            f"[nar][bed]amix=inputs=2:normalize=0,apad=whole_dur={total_frames/FPS:.3f},"
            f"loudnorm=I=-15:TP=-1.0:LRA=9[aout]"]
        full_mix = os.path.join(HERE, "akcio_mix.m4a")
        subprocess.check_call(["ffmpeg", "-y", "-v", "error", "-i", audio_mix, "-i", os.path.join(MUSIC, "music.wav"),
                               *w_in, "-filter_complex", ";".join(fc2), "-map", "[aout]",
                               "-c:a", "aac", "-b:a", "160k", full_mix])
        audio_mix = full_mix

    # ---- 5. kép + címek + felirat + hang ---------------------------------------
    def esc(s):
        return s.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'").replace(",", "\\,")
    vf = []
    sc_px = RES[0] / 1280.0
    if ACTION:
        # színezés (teal–orange), kontraszt, vignetta, filmszemcse – a címek és a sávok elé
        # hideg, acélos look: a mélyekben kékes, a fények semlegesek (az erős teal–orange sárgított)
        vf += ["colorbalance=rs=-0.05:gs=-0.01:bs=0.07:rm=-0.02:bm=0.02:rh=-0.03:gh=0.0:bh=0.03",
               "eq=contrast=1.16:saturation=1.08:brightness=-0.03",
               "vignette=PI/4.2", "noise=alls=6:allf=t+u"]
    for idx, title in TITLES:
        s = scenes[idx]
        a, b = s["start"] - 0.6, s["start"] + 3.4
        if ACTION:
            # ütésre bevágódó, nagy, középre zárt cím; fehér villanás az ütés pillanatában
            fs = int(54 * sc_px)
            a, b = s["start"] - 0.35, s["start"] + 1.9     # rövid, ütős cím – a címkék előtt eltűnik
            vf.append(f"drawbox=c=white@0.55:t=fill:enable='between(t,{a:.2f},{a + 0.09:.2f})'")
            vf.append(f"drawtext=fontfile={FONT_B}:text='{esc(title.upper())}':fontsize={fs}:fontcolor=white:"
                      f"shadowcolor=black@0.7:shadowx=3:shadowy=3:x=(w-text_w)/2:y=h*0.42-text_h/2:"
                      f"alpha='if(lt(t,{a + 0.12:.2f}),1,if(lt(t,{b - 0.4:.2f}),1,({b:.2f}-t)/0.4))':"
                      f"enable='between(t,{a:.2f},{b:.2f})'")
            continue
        fs, bw, m = (19, 7, 20) if PREVIEW else (38, 14, 40)
        vf.append(f"drawtext=fontfile={FONT_B}:text='{esc(title)}':fontsize={fs}:fontcolor=white:"
                  f"box=1:boxcolor=black@0.45:boxborderw={bw}:x={m}:y={m}:enable='between(t,{a:.2f},{b:.2f})'")
    if ACTION:
        bar = int(BAR * sc_px)
        vf.append(f"drawbox=x=0:y=0:w=iw:h={bar}:c=black:t=fill")
        vf.append(f"drawbox=x=0:y=ih-{bar}:w=iw:h={bar}:c=black:t=fill")
    srt_esc = srt.replace("\\", "/").replace(":", "\\:")
    # felirat: nagyobb, félkövér, sötét áttetsző sávval (BorderStyle=4), csak alul
    # (libass a méreteket 384×288-as virtuális vászonhoz skálázza: FontSize=11 ≈ 27 px 720p-n)
    vf.append(f"subtitles='{srt_esc}':force_style='FontName=DejaVu Sans,Bold=1,FontSize=11,"
              f"BorderStyle=4,Outline=0,Shadow=0,MarginV={9 + (19 if ACTION else 0)},MarginL=14,MarginR=14,"
              f"PrimaryColour=&H00FFFFFF,BackColour=&H73000000'")
    out_mp4 = os.path.join(HERE, "elonezet.mp4") if PREVIEW else os.path.join(ASSETS, "kompozit_erthetoen.mp4")
    if ACTION and not PREVIEW:
        out_mp4 = os.path.join(ASSETS, "kompozit_erthetoen_akcio.mp4")
    subprocess.check_call(["ffmpeg", "-y", "-v", "error", "-framerate", str(FPS),
                           "-i", os.path.join(FRAMES, "%05d.png"), "-i", audio_mix,
                           "-vf", ",".join(vf), "-c:v", "libx264", "-preset", "slow", "-crf", "23",
                           "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-c:a", "copy", "-shortest", out_mp4])
    # poszter: a 4. jelenet közepe
    s4 = scenes[3]
    pf = int(s4["start"] * FPS + s4["frames"] * 0.45)
    subprocess.check_call(["ffmpeg", "-y", "-v", "error", "-i", os.path.join(FRAMES, f"{pf:05d}.png"),
                           "-q:v", "3", os.path.join(ASSETS, "poster.jpg")])
    mb = os.path.getsize(out_mp4) / 1e6
    print(f"[kész] {out_mp4}  {mb:.1f} MB, {total_frames/FPS:.1f} s")


if __name__ == "__main__":
    main(render="--no-render" not in sys.argv)
