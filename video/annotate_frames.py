"""
annotate_frames.py – buborékos címkék nyíllal a renderelt képkockákra, ütközésmentesen
========================================================================================

Bemenet: video/frames/NNNNN.png + video/labels.json (a render_scenes.py írja:
képkockánként a címkék szövege, a célpont képernyő-pozíciója és a buborék
kívánt eltolása). Kimenet: ugyanazok a képek felülírva, rajtuk a címkék.

Elrendezés: minden buboréknak több jelölt helye van (a kívánt eltolás, majd
körben 8 irány × 3 távolság). Azt választjuk, amelyik
  * a képen belül van és nem lóg a felirat sávjába (alsó ~70 px),
  * nem fedi a már elhelyezett buborékokat,
  * a vonala nem metsz át másik buborékot, és nem halad át másik célponton,
  * nem takarja másik címkézett alkatrész képét (a render adja a téglalapokat),
  * és (ha lehet) ugyanaz, mint az előző képkockán – így nem ugrál.
Ha egyetlen jelölt sem jó, a legkisebb büntetésű kerül kiválasztásra.

    python video/annotate_frames.py --frames video/frames --labels video/labels.json
"""

import json
import math
import os
import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SUB_BAND = 72          # px (720p) alul, ahol a felirat van – ide nem kerül buborék
BAR = 48 if os.environ.get("ACTION") == "1" else 0   # akció-változat: fekete szélesvásznú sávok fent/lent
PAD = 9


def rect_overlap(a, b, margin=6):
    return not (a[2] + margin < b[0] or b[2] + margin < a[0] or a[3] + margin < b[1] or b[3] + margin < a[1])


def seg_hits_rect(p, q, r, samples=24):
    for i in range(samples + 1):
        t = i / samples
        x = p[0] + (q[0] - p[0]) * t
        y = p[1] + (q[1] - p[1]) * t
        if r[0] <= x <= r[2] and r[1] <= y <= r[3]:
            return True
    return False


def seg_near_point(p, q, c, rad):
    px, py = p; qx, qy = q; cx, cy = c
    dx, dy = qx - px, qy - py
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return math.hypot(cx - px, cy - py) < rad
    t = max(0.0, min(1.0, ((cx - px) * dx + (cy - py) * dy) / L2))
    return math.hypot(cx - (px + t * dx), cy - (py + t * dy)) < rad


def attach_point(ax, ay, box):
    """A buborék széléhez legközelebbi pont a célpont felől (ide fut a vonal)."""
    return (min(max(ax, box[0]), box[2]), min(max(ay, box[1]), box[3]))


def layout(labels, W, H, font, scale, prev):
    """labels: [{text, ax, ay, dx, dy, age}] → ugyanezek kiegészítve 'box' mezővel."""
    d = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    pad = PAD * scale
    sizes = []
    for lab in labels:
        tw, th = d.textbbox((0, 0), lab["text"], font=font)[2:]
        sizes.append((tw, th))
    anchors = [(l["ax"], l["ay"]) for l in labels]
    placed = []            # (box)
    lines = []             # (p, q)
    result = []
    # stabil sorrend: amelyik már volt az előző képen, azt előbb helyezzük
    order = sorted(range(len(labels)), key=lambda i: (labels[i]["text"] not in prev, labels[i]["text"]))
    boxes = [None] * len(labels)
    for i in order:
        lab = labels[i]; tw, th = sizes[i]
        ax, ay = lab["ax"], lab["ay"]
        cands = []
        if lab["text"] in prev:
            cands.append(prev[lab["text"]])
        cands.append((lab["dx"], lab["dy"]))
        for rad in (130 * scale, 190 * scale, 260 * scale):
            for ang in range(0, 360, 45):
                a = math.radians(ang)
                cands.append((rad * math.cos(a), -rad * math.sin(a)))
        best, best_cost = None, 1e9
        for k, (dx, dy) in enumerate(cands):
            bx, by = ax + dx, ay + dy
            box = (bx - tw / 2 - pad, by - th / 2 - pad, bx + tw / 2 + pad, by + th / 2 + pad)
            cost = 0.0
            # képen belül, felirat-sáv felett
            if box[0] < 8 or box[2] > W - 8 or box[1] < (8 + BAR) * scale or box[3] > H - (SUB_BAND + BAR) * scale:
                cost += 1000
            # ne fedje a célpontját és más célpontokat
            for j, (ox, oy) in enumerate(anchors):
                if box[0] - 10 <= ox <= box[2] + 10 and box[1] - 10 <= oy <= box[3] + 10:
                    cost += 400
            # ne fedje a már elhelyezett buborékokat
            for pb in placed:
                if rect_overlap(box, pb):
                    cost += 500
            # ne takarja MÁS címkézett alkatrész képét (pl. a szivattyú buborékja a csapdát)
            for j, other in enumerate(labels):
                r = other.get("rect")
                if j != i and r and rect_overlap(box, r, margin=0):
                    # átfedés mértéke arányosan (kis érintés kevésbé büntetett)
                    ix = max(0, min(box[2], r[2]) - max(box[0], r[0]))
                    iy = max(0, min(box[3], r[3]) - max(box[1], r[1]))
                    area = (box[2] - box[0]) * (box[3] - box[1])
                    cost += 350 * (ix * iy) / max(area, 1)
            # a vonala ne messen más buborékot / célpontot, és más vonal ne messe ezt a buborékot
            p = attach_point(ax, ay, box)
            for pb in placed:
                if seg_hits_rect(p, (ax, ay), pb):
                    cost += 300
            for (lp, lq) in lines:
                if seg_hits_rect(lp, lq, box):
                    cost += 300
            for j, (ox, oy) in enumerate(anchors):
                if j != i and seg_near_point(p, (ax, ay), (ox, oy), 14 * scale):
                    cost += 150
            # preferencia: előző hely (k==0 ha volt), majd a tervezett eltolás, majd a közelebbi jelöltek
            cost += k * 1.5 + math.hypot(dx, dy) / (40 * scale)
            if cost < best_cost:
                best, best_cost = (dx, dy, box), cost
        dx, dy, box = best
        boxes[i] = box
        placed.append(box)
        lines.append((attach_point(ax, ay, box), (ax, ay)))
        prev[lab["text"]] = (dx, dy)
    for i, lab in enumerate(labels):
        r = dict(lab); r["box"] = boxes[i]; result.append(r)
    # amelyik címke eltűnt, azt felejtsük el, hogy visszatéréskor újra tervezzen
    for k in list(prev):
        if k not in {l["text"] for l in labels}:
            del prev[k]
    return result


def draw_label(img, lab, font, scale):
    alpha = max(0.0, min(1.0, lab.get("age", 1.0) / 0.35))
    if alpha <= 0:
        return
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    ax, ay = lab["ax"], lab["ay"]
    box = lab["box"]
    a = int(255 * alpha)
    ex, ey = attach_point(ax, ay, box)
    d.line([(ex, ey), (ax, ay)], fill=(255, 255, 255, int(220 * alpha)), width=max(2, int(2 * scale)))
    r = 5 * scale
    d.ellipse([ax - r, ay - r, ax + r, ay + r], fill=(255, 196, 0, a), outline=(20, 20, 20, a), width=max(1, int(1.5 * scale)))
    d.rounded_rectangle(box, radius=int(8 * scale), fill=(18, 24, 32, int(205 * alpha)),
                        outline=(255, 255, 255, int(150 * alpha)), width=max(1, int(1.2 * scale)))
    tw, th = d.textbbox((0, 0), lab["text"], font=font)[2:]
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    d.text((cx - tw / 2, cy - th / 2 - 1), lab["text"], font=font, fill=(255, 255, 255, a))
    img.alpha_composite(ov)


def draw_highlight(img, mask_path, scale):
    """Fénylő körvonal a kiemelt alkatrész körül (a maszk alfájából): kitágított él,
    lágy narancs-sárga derengéssel, és enyhe világosítás az alkatrészen."""
    m = Image.open(mask_path).convert("RGBA").split()[3].resize(img.size, Image.BILINEAR)
    m = m.point(lambda v: 255 if v > 90 else 0)
    r = max(3, int(5 * scale))
    dil = m.filter(ImageFilter.MaxFilter(2 * r + 1))
    ring = ImageChops.subtract(dil, m)                          # vékony gyűrű
    glow = dil.filter(ImageFilter.GaussianBlur(10 * scale))     # derengés
    glow = ImageChops.subtract(glow, m.filter(ImageFilter.GaussianBlur(1)))
    col_glow = Image.new("RGBA", img.size, (255, 170, 0, 0)); col_glow.putalpha(glow.point(lambda v: int(v * 0.9)))
    col_ring = Image.new("RGBA", img.size, (255, 220, 60, 0)); col_ring.putalpha(ring.point(lambda v: int(v * 0.95)))
    tint = Image.new("RGBA", img.size, (255, 230, 150, 0)); tint.putalpha(m.point(lambda v: int(v * 0.14)))
    img.alpha_composite(col_glow); img.alpha_composite(tint); img.alpha_composite(col_ring)


def draw_braces(img, braces, font, scale):
    """Kapcsos zárójelek: a csoport felső és alsó éle között, a szöveg balra tőle.
    A szövegdobozokat függőlegesen széttoljuk, ha összeérnének."""
    if not braces:
        return
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    pad = PAD * scale
    items = []
    for b in sorted(braces, key=lambda b: b["y0"]):
        tw, th = d.textbbox((0, 0), b["text"], font=font)[2:]
        items.append(dict(b, tw=tw, th=th, cy=(b["y0"] + b["y1"]) / 2))
    # dobozok széttolása (fentről lefelé), hogy ne fedjék egymást
    for k in range(1, len(items)):
        prev_b = items[k - 1]; cur = items[k]
        min_cy = prev_b["cy"] + prev_b["th"] / 2 + cur["th"] / 2 + 2 * pad + 4 * scale
        if cur["cy"] < min_cy:
            cur["cy"] = min_cy
    # a feliratsáv fölött maradjanak: a legalsót felhúzzuk, és ha kell, a többit is (alulról felfelé)
    H = img.size[1]
    for k in range(len(items) - 1, -1, -1):
        cur = items[k]
        limit = (H - (SUB_BAND + BAR + 18) * scale) - cur["th"] / 2 - pad   # kétsoros felirat fölött
        if k < len(items) - 1:
            nxt = items[k + 1]
            limit = min(limit, nxt["cy"] - nxt["th"] / 2 - cur["th"] / 2 - 2 * pad - 4 * scale)
        if cur["cy"] > limit:
            cur["cy"] = limit
    # közös felirat-oszlop: a legbalra eső zárójeltől balra
    x_col = min(b["x"] for b in items) - 26 * scale
    for b in items:
        alpha = max(0.0, min(1.0, b.get("age", 1.0) / 0.35))
        a = int(255 * alpha)
        x, y0, y1 = b["x"], b["y0"] + 2, b["y1"] - 2
        w = 10 * scale
        col = (255, 215, 60, int(240 * alpha))        # sárga, hogy elváljon a szürke modelltől
        lw = max(2, int(2.5 * scale))
        # zárójel: két ív helyett egyszerű, jól olvasható forma: ]-szerű, középen csúccsal
        ym = (y0 + y1) / 2
        d.line([(x, y0), (x - w * 0.6, y0 + w * 0.5), (x - w * 0.6, ym - w * 0.5), (x - w * 1.3, ym),
                (x - w * 0.6, ym + w * 0.5), (x - w * 0.6, y1 - w * 0.5), (x, y1)], fill=col, width=lw, joint="curve")
        # vezető vonal a csúcstól a dobozig
        bx1 = x_col
        tw, th = b["tw"], b["th"]
        box = (bx1 - tw - 2 * pad, b["cy"] - th / 2 - pad, bx1, b["cy"] + th / 2 + pad)
        d.line([(x - w * 1.3, ym), (bx1, b["cy"])], fill=col, width=lw)
        d.rounded_rectangle(box, radius=int(8 * scale), fill=(18, 24, 32, int(205 * alpha)),
                            outline=(255, 255, 255, int(150 * alpha)), width=max(1, int(1.2 * scale)))
        d.text((box[0] + pad, b["cy"] - th / 2 - 1), b["text"], font=font, fill=(255, 255, 255, a))
    img.alpha_composite(ov)


def main(frames_dir, labels_path):
    with open(labels_path, encoding="utf-8") as f:
        labels = json.load(f)
    # kiemelés-maszkos képkockák címke nélkül is feldolgozandók (fénylő körvonal szöveg nélkül)
    for f in os.listdir(frames_dir):
        if f.endswith("_mask.png"):
            labels.setdefault(str(int(f[:5])), [])
    if not labels:
        print("[címkék] nincs címke")
        return
    first = sorted(f for f in os.listdir(frames_dir) if f.endswith(".png"))[0]
    sample = Image.open(os.path.join(frames_dir, first))
    W, H = sample.size
    scale = W / 1280.0
    font = ImageFont.truetype(FONT_B, max(11, int(21 * scale)))
    prev = {}
    n = 0
    last_idx = None
    for idx in sorted(labels, key=int):
        path = os.path.join(frames_dir, f"{int(idx):05d}.png")
        if not os.path.exists(path):
            continue
        if last_idx is not None and int(idx) - last_idx > 1:
            prev = {}            # jelenetváltás / ugrás: új elrendezés
        last_idx = int(idx)
        braces = [l for l in labels[idx] if l.get("kind") == "brace"]
        points = [l for l in labels[idx] if l.get("kind") != "brace"]
        img = Image.open(path).convert("RGBA")
        mask_path = os.path.join(frames_dir, f"{int(idx):05d}_mask.png")
        if os.path.exists(mask_path):
            draw_highlight(img, mask_path, scale)
            os.remove(mask_path)
        if points:
            placed = layout(points, W, H, font, scale, prev)
            for lab in placed:
                draw_label(img, lab, font, scale)
        draw_braces(img, braces, font, scale)
        img.convert("RGB").save(path)
        n += 1
    print(f"[címkék] {n} képkocka címkézve")


if __name__ == "__main__":
    argv = sys.argv[1:]
    frames = argv[argv.index("--frames") + 1] if "--frames" in argv else os.path.join(HERE, "frames")
    labels = argv[argv.index("--labels") + 1] if "--labels" in argv else os.path.join(HERE, "labels.json")
    main(frames, labels)
