"""
annotate_frames.py – buborékos címkék nyíllal a renderelt képkockákra
======================================================================

Bemenet: video/frames/NNNNN.png + video/labels.json (a render_scenes.py írja:
képkockánként a címkék szövege, a célpont képernyő-pozíciója és a buborék
eltolása). Kimenet: ugyanazok a képek felülírva, rajtuk a címkék.

Stílus: lekerekített, félig átlátszó sötét buborék, fehér félkövér szöveg,
vékony vonal a célpontig, kis pont a célponton; 0,35 s alatt úszik be.

    python video/annotate_frames.py --frames video/frames --labels video/labels.json
"""

import json
import os
import sys
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def draw_label(img, lab, font, scale):
    alpha = max(0.0, min(1.0, lab.get("age", 1.0) / 0.35))
    if alpha <= 0:
        return
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    ax, ay = lab["ax"], lab["ay"]
    bx, by = ax + lab["dx"], ay + lab["dy"]
    text = lab["text"]
    tw, th = d.textbbox((0, 0), text, font=font)[2:]
    pad = int(9 * scale)
    W, H = img.size
    # a buborék maradjon a képen belül
    bx = min(max(bx, pad + tw / 2), W - pad - tw / 2)
    by = min(max(by, pad + th / 2), H - 70 * scale - th / 2)   # alul hely a feliratnak
    box = (bx - tw / 2 - pad, by - th / 2 - pad, bx + tw / 2 + pad, by + th / 2 + pad)
    a = int(255 * alpha)
    # vonal: a buborék széléhez legközelebbi pontból a célpontig
    ex = min(max(ax, box[0]), box[2]); ey = min(max(ay, box[1]), box[3])
    d.line([(ex, ey), (ax, ay)], fill=(255, 255, 255, int(220 * alpha)), width=max(2, int(2 * scale)))
    r = 5 * scale
    d.ellipse([ax - r, ay - r, ax + r, ay + r], fill=(255, 196, 0, a), outline=(20, 20, 20, a), width=max(1, int(1.5 * scale)))
    d.rounded_rectangle(box, radius=int(8 * scale), fill=(18, 24, 32, int(200 * alpha)),
                        outline=(255, 255, 255, int(150 * alpha)), width=max(1, int(1.2 * scale)))
    d.text((bx - tw / 2, by - th / 2 - 1), text, font=font, fill=(255, 255, 255, a))
    img.alpha_composite(ov)


def main(frames_dir, labels_path):
    with open(labels_path, encoding="utf-8") as f:
        labels = json.load(f)
    if not labels:
        print("[címkék] nincs címke")
        return
    sample = Image.open(os.path.join(frames_dir, "00000.png"))
    scale = sample.size[0] / 1280.0
    font = ImageFont.truetype(FONT_B, max(11, int(21 * scale)))
    n = 0
    for idx, labs in labels.items():
        path = os.path.join(frames_dir, f"{int(idx):05d}.png")
        if not os.path.exists(path):
            continue
        img = Image.open(path).convert("RGBA")
        for lab in labs:
            draw_label(img, lab, font, scale)
        img.convert("RGB").save(path)
        n += 1
    print(f"[címkék] {n} képkocka címkézve")


if __name__ == "__main__":
    argv = sys.argv[1:]
    frames = argv[argv.index("--frames") + 1] if "--frames" in argv else os.path.join(HERE, "frames")
    labels = argv[argv.index("--labels") + 1] if "--labels" in argv else os.path.join(HERE, "labels.json")
    main(frames, labels)
