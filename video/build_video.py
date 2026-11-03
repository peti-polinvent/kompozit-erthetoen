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
    return dst


def pick_audio(i):
    # saját felvétel (m4a/wav/caf/mp3) előnyben; az .aiff a "say" TTS tartaléké
    for ext in (".m4a", ".wav", ".caf", ".mp3", ".mp4", ".aiff"):
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

    # ---- 5. kép + címek + felirat + hang ---------------------------------------
    def esc(s):
        return s.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'").replace(",", "\\,")
    vf = []
    for idx, title in TITLES:
        s = scenes[idx]
        a, b = s["start"] - 0.6, s["start"] + 3.4
        fs, bw, m = (19, 7, 20) if PREVIEW else (38, 14, 40)
        vf.append(f"drawtext=fontfile={FONT_B}:text='{esc(title)}':fontsize={fs}:fontcolor=white:"
                  f"box=1:boxcolor=black@0.45:boxborderw={bw}:x={m}:y={m}:enable='between(t,{a:.2f},{b:.2f})'")
    srt_esc = srt.replace("\\", "/").replace(":", "\\:")
    # felirat: nagyobb, félkövér, sötét áttetsző sávval (BorderStyle=4), csak alul
    # (libass a méreteket 384×288-as virtuális vászonhoz skálázza: FontSize=11 ≈ 27 px 720p-n)
    vf.append(f"subtitles='{srt_esc}':force_style='FontName=DejaVu Sans,Bold=1,FontSize=11,"
              f"BorderStyle=4,Outline=0,Shadow=0,MarginV=9,MarginL=14,MarginR=14,"
              f"PrimaryColour=&H00FFFFFF,BackColour=&H73000000'")
    out_mp4 = os.path.join(HERE, "elonezet.mp4") if PREVIEW else os.path.join(ASSETS, "kompozit_erthetoen.mp4")
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
