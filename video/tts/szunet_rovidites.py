"""szunet_rovidites.py – túl hosszú mondatközi szünetek rövidítése egy narrációs szegmensben.

    python video/tts/szunet_rovidites.py 01 0.5

A NN_words.json alapján minden szóköz-szünetet, ami hosszabb a megadottnál (s), a megadott
hosszra rövidít (a szünet közepéből vág), és a szóidőzítéseket ehhez igazítja.
Ok: az edge-tts vesszőnél ~0,17 s, pontnál ~1 s szünetet tart – a kívánt ~0,5 s a kettő között van.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
key, target = sys.argv[1], float(sys.argv[2])
if len(sys.argv) > 3:            # nyelvi alkönyvtár: python szunet_rovidites.py 01 0.5 en
    HERE = os.path.join(HERE, sys.argv[3])
mp3, wj = os.path.join(HERE, f"{key}.mp3"), os.path.join(HERE, f"{key}_words.json")
words = json.load(open(wj, encoding="utf-8"))

cuts = []   # (vágás kezdete, vége) az eredeti időtengelyen
for a, b in zip(words, words[1:]):
    gap = b["start"] - a["end"]
    if gap > target + 0.05:
        mid = (a["end"] + b["start"]) / 2
        cuts.append((mid - (gap - target) / 2, mid + (gap - target) / 2))
if not cuts:
    sys.exit("nincs rövidítendő szünet")

keep, t = [], 0.0
for c0, c1 in cuts:
    keep.append((t, c0)); t = c1
keep.append((t, None))
parts = "".join(f"[0:a]atrim=start={s:.3f}" + (f":end={e:.3f}" if e else "") + f",asetpts=PTS-STARTPTS[p{i}];"
                for i, (s, e) in enumerate(keep))
fc = parts + "".join(f"[p{i}]" for i in range(len(keep))) + f"concat=n={len(keep)}:v=0:a=1[out]"
tmp = mp3 + ".tmp.mp3"
subprocess.check_call(["ffmpeg", "-y", "-v", "error", "-i", mp3, "-filter_complex", fc, "-map", "[out]",
                       "-c:a", "libmp3lame", "-b:a", "96k", tmp])
os.replace(tmp, mp3)


def shift(x):
    return x - sum(c1 - c0 for c0, c1 in cuts if c1 <= x + 1e-6)


for w in words:
    w["start"], w["end"] = round(shift(w["start"]), 3), round(shift(w["end"]), 3)
json.dump(words, open(wj, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"{key}: {len(cuts)} szünet rövidítve {target} s-ra, összesen {sum(c1 - c0 for c0, c1 in cuts):.2f} s")
