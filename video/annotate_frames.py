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
FONT_B = next((p for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                            "C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf",
                            "/System/Library/Fonts/Supplemental/Arial Bold.ttf")
               if os.path.exists(p)), "DejaVuSans-Bold.ttf")
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


# =====================================================================================
# LIGHT stílus: mozgógrafika képkockánként (Pillow) – jelenetcím, alsó harmad címke,
# „Hozzávalók” checklista, élő rétegrend-ábra, finom borostyán kiemelés, felirat, zárókártya.
# Minden animáció ease-out-cubic, 0,2–0,35 s; biztonsági margó ≥ 5 %.
# =====================================================================================
PAGE = (0xEC, 0xEE, 0xED)
INK = (0x15, 0x19, 0x1D)
MUTED = (0x5D, 0x64, 0x6B)
AMBER = (0xE0, 0x9A, 0x1F)
ARCHIVO = os.path.join(HERE, "fonts", "Archivo-VF.ttf")
_FONTS = {}


BAND_COL = (0xF7, 0xF8, 0xF7)          # feliratsáv: az oldal „raised” tónusa
CJK = os.environ.get("VLANG") == "zh"   # kínai: Microsoft YaHei (az Archivóban nincs CJK)


def font(size, wght=700, wdth=100):
    key = (int(size), wght, wdth)
    if key not in _FONTS:
        if CJK:
            _FONTS[key] = ImageFont.truetype("C:/Windows/Fonts/msyhbd.ttc" if wght >= 600 else
                                             "C:/Windows/Fonts/msyh.ttc", int(size))
            return _FONTS[key]
        try:
            f = ImageFont.truetype(ARCHIVO, int(size))
            f.set_variation_by_axes([wght, wdth])          # tengelysorrend: Weight, Width
        except Exception:
            f = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf" if os.path.exists("C:/Windows/Fonts/segoeuib.ttf")
                                   else FONT_B, int(size))
        _FONTS[key] = f
    return _FONTS[key]


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def eo(u):
    """ease-out-cubic, [0,1]-re vágva."""
    u = min(max(u, 0.0), 1.0)
    return 1 - (1 - u) ** 3


def spring(u):
    """lágy rugó (kis túllendülés), u ∈ [0,1] → ~[0,1.06]."""
    u = min(max(u, 0.0), 1.0)
    return 1 - math.exp(-6 * u) * math.cos(7 * u)


def inout(t, a, b, d_in=0.3, d_out=0.25):
    """Be-/kiúszás súlya: a-nál indul (d_in alatt be), b előtt d_out-tal kiúszik."""
    return eo((t - a) / d_in) * (1 - eo((t - (b - d_out)) / d_out))


def draw_highlight_light(img, mask_path, sc):
    """Vékony, lágy borostyán körvonal a kiemelt alkatrészen (a maszk alfájából)."""
    m = Image.open(mask_path).convert("RGBA").split()[3].resize(img.size, Image.BILINEAR)
    m = m.point(lambda v: 255 if v > 90 else 0)
    r = max(1, int(round(2.5 * sc)))
    dil = m.filter(ImageFilter.MaxFilter(2 * r + 1))
    ring = ImageChops.subtract(dil, m).filter(ImageFilter.GaussianBlur(0.8 * sc))
    glow = ImageChops.subtract(dil.filter(ImageFilter.GaussianBlur(7 * sc)), m)
    for mask, a in ((glow, 0.35), (ring, 1.0)):
        lay = Image.new("RGBA", img.size, AMBER + (0,))
        lay.putalpha(mask.point(lambda v, a=a: int(v * a)))
        img.alpha_composite(lay)


def panel(d, box, alpha=1.0):
    d.rectangle(box, fill=(255, 255, 255, int(235 * alpha)))


def draw_title(d, text, t, a, b, W, H, sc):
    if not text:
        return
    k = inout(t, a + 0.15, b, 0.35, 0.3)
    if k <= 0.01:
        return
    f = font(58 * sc, 800, 62)
    x = 0.055 * W - (1 - k) * 40 * sc
    y = 0.07 * H
    asc = f.getbbox("ÁH")[3]
    top = f.getbbox("H")[1]
    d.rectangle([x, y + top, x + 9 * sc, y + asc], fill=AMBER + (int(255 * k),))
    d.text((x + 24 * sc, y), text, font=f, fill=INK + (int(255 * k),))


def chip(d, x, y, s, colors, alpha):
    cs = [hexrgb(c) for c in colors]
    if len(cs) == 1:
        d.rectangle([x, y, x + s, y + s], fill=cs[0] + (int(255 * alpha),))
    else:
        d.rectangle([x, y, x + s / 2, y + s], fill=cs[0] + (int(255 * alpha),))
        d.rectangle([x + s / 2, y, x + s, y + s], fill=cs[1] + (int(255 * alpha),))
    d.rectangle([x, y, x + s, y + s], outline=INK + (int(70 * alpha),), width=max(1, int(1.5 * (s / 34))))


def draw_lower_third(d, ev, t, W, H, sc):
    k = inout(t, ev["a0"], ev["a1"], 0.3, 0.22)
    if k <= 0.01:
        return
    f = font(40 * sc, 700, 88)
    tw = d.textbbox((0, 0), ev["label"], font=f)[2]
    s = 34 * sc
    pad = 18 * sc
    w = pad + s + 16 * sc + tw + pad * 1.3
    h = 70 * sc
    x = 0.055 * W - (1 - k) * 48 * sc
    y = 0.705 * H
    panel(d, [x, y, x + w, y + h], k)
    d.rectangle([x, y, x + 5 * sc, y + h], fill=AMBER + (int(255 * k),))
    chip(d, x + pad, y + (h - s) / 2, s, ev["colors"], k)
    cap = f.getbbox("H")
    d.text((x + pad + s + 16 * sc, y + h / 2 - (cap[1] + cap[3]) / 2), ev["label"], font=f, fill=INK + (int(255 * k),))


def draw_tick(d, x, y, s, k, alpha):
    """✓ borostyánban, rugós „pop”-pal (k: 0→1 animáció)."""
    if k <= 0:
        return
    g = spring(k)
    cx, cy = x + s / 2, y + s / 2
    pts = [(-0.32, 0.02), (-0.08, 0.27), (0.38, -0.3)]
    pts = [(cx + px * s * g, cy + py * s * g) for px, py in pts]
    d.line(pts, fill=AMBER + (int(255 * alpha),), width=max(2, int(s * 0.17)), joint="curve")


def draw_checklist(d, evs, t, a, b, W, H, sc, ticks):
    k = inout(t, a + 0.3, b, 0.35, 0.3)
    if k <= 0.01:
        return
    pw, x1 = 0.205 * W, 0.945 * W
    x0 = x1 - pw + (1 - k) * 50 * sc
    y0 = 0.17 * H
    row = 56 * sc
    ph = 92 * sc + row * len(evs) + 14 * sc
    panel(d, [x0, y0, x0 + pw, y0 + ph], k)
    d.text((x0 + 26 * sc, y0 + 22 * sc), __import__("cues").TXT["checklist"], font=font(40 * sc, 800, 62),
           fill=INK + (int(255 * k),))
    d.rectangle([x0 + 26 * sc, y0 + 74 * sc, x0 + 70 * sc, y0 + 78 * sc], fill=AMBER + (int(255 * k),))
    fi = font(30 * sc, 600, 92)
    for j, e in enumerate(evs):
        yy = y0 + 92 * sc + j * row
        done = t >= e["abs0"]
        bs = 26 * sc
        bx, by = x0 + 26 * sc, yy + (row - bs) / 2
        d.rectangle([bx, by, bx + bs, by + bs], outline=(INK if done else MUTED) + (int(160 * k),), width=max(1, int(2 * sc)))
        draw_tick(d, bx - 2 * sc, by - 4 * sc, bs + 8 * sc, (t - e["abs0"]) / 0.3, k)
        col = INK if done else MUTED
        cap = fi.getbbox("H")
        d.text((bx + bs + 16 * sc, yy + row / 2 - (cap[1] + cap[3]) / 2), e["label"], font=fi,
               fill=col + (int((255 if done else 150) * k),))


def draw_layer_stack(d, evs, t, a, b, W, H, sc):
    """Élő rétegrend-ábra (mint a weboldal rajza): alulról felfelé épül, ahogy a narráció megnevezi."""
    k = inout(t, a + 0.3, b, 0.35, 0.3)
    if k <= 0.01:
        return
    pw, x1 = 0.215 * W, 0.945 * W
    x0 = x1 - pw + (1 - k) * 50 * sc
    y0 = 0.17 * H
    ph = 300 * sc
    panel(d, [x0, y0, x0 + pw, y0 + ph], k)
    d.text((x0 + 26 * sc, y0 + 22 * sc), __import__("cues").TXT["stack"], font=font(40 * sc, 800, 62),
           fill=INK + (int(255 * k),))
    d.rectangle([x0 + 26 * sc, y0 + 74 * sc, x0 + 70 * sc, y0 + 78 * sc], fill=AMBER + (int(255 * k),))
    cx = x0 + pw / 2
    base = y0 + ph - 54 * sc
    tw, lw = 330 * sc / 2, 250 * sc / 2
    # szerszám (mindig látszik)
    d.rectangle([cx - tw, base, cx + tw, base + 26 * sc], fill=(0x9A, 0xA0, 0xA6, int(255 * k)), outline=INK + (int(90 * k),))
    d.text((cx - tw, base + 29 * sc), __import__("cues").TXT["tool"], font=font(18 * sc, 600, 90), fill=MUTED + (int(220 * k),))
    when = {e["layer"]: e["abs0"] for e in evs if e.get("layer")}
    y = base

    def appear(name):
        t0 = when.get(name)
        return 0.0 if t0 is None else eo((t - t0) / 0.35)

    def slab(name, h, half, color, dx=0.0, hatch=None, sub=0.0):
        nonlocal y
        g = appear(name)
        if g <= 0:
            return False
        top = y - h
        off = (1 - g) * 26 * sc
        al = int(255 * k * g)
        d.rectangle([cx - half + dx, top - off, cx + half + dx, y - off], fill=hexrgb(color) + (al,),
                    outline=INK + (int(80 * k * g),))
        if hatch:
            for xx in range(int(cx - half + dx), int(cx + half + dx), int(9 * sc)):
                d.line([(xx, y - off), (min(xx + h, cx + half + dx), top - off)], fill=hexrgb(hatch) + (al,), width=1)
        y = top - sub
        return True

    L = {l["type"]: l["color"] for l in __import__("cues").P["layup"]}
    gl = [l["color"] for l in __import__("cues").P["layup"] if l["type"] == "glass"]
    slab("release", 9 * sc, lw + 14 * sc, L["release"])
    for c in gl:
        slab("glass", 14 * sc, lw, c)
    slab("peelply", 11 * sc, lw + 8 * sc, L["peelply"])
    mesh_top = y
    if slab("flowmesh", 15 * sc, lw - 8 * sc, L["flowmesh"], dx=-12 * sc, hatch="#2e7d50"):
        mesh_top = y
    C = __import__("cues").P["consumables"]
    for name, xx, col in (("spiral_in", cx - lw - 2 * sc, C["inlet_spiral"]["color"]),
                          ("spiral_vac", cx + lw + 2 * sc, C["vacuum_spiral"]["color"])):
        g = appear(name)
        if g <= 0:
            continue
        r = 12 * sc * eo(g)
        if True:
            d.ellipse([xx - r, mesh_top - 2 * r, xx + r, mesh_top], fill=hexrgb(col) + (int(255 * k * g),),
                      outline=INK + (int(90 * k * g),))
    g = appear("tape")
    if g > 0:
        th = 14 * sc
        for xx in (cx - tw + 6 * sc, cx + tw - 22 * sc):
            d.rectangle([xx, base - th * eo(g), xx + 16 * sc, base], fill=hexrgb(C["sealant_tape"]["color"]) + (int(255 * k * g),),
                        outline=INK + (int(90 * k * g),))
    g = appear("bag")
    if g > 0:
        lift = (1 - eo(g)) * 30 * sc
        top = mesh_top - 30 * sc - lift
        pts = [(cx - tw + 14 * sc, base - 10 * sc), (cx - lw - 20 * sc, top + 8 * sc), (cx - lw, top),
               (cx + lw, top), (cx + lw + 20 * sc, top + 8 * sc), (cx + tw - 14 * sc, base - 10 * sc)]
        d.line(pts, fill=(0xC9, 0xB0, 0x10, int(255 * k * g)), width=max(2, int(3 * sc)), joint="curve")


def wrap_px(d, text, f, maxw):
    """Egy vagy két kiegyensúlyozott sor, pixelszélesség szerint (kínaiban karakterenként,
    írásjel nem kerül sor elejére)."""
    text = text.replace("\n", "" if CJK else " ").strip()
    if d.textlength(text, font=f) <= maxw:
        return [text]
    units = list(text) if CJK else text.split(" ")
    sep = "" if CJK else " "
    best = None
    for i in range(1, len(units)):
        if CJK and units[i] in "，。、；：！？）」”":
            continue
        a, b = sep.join(units[:i]), sep.join(units[i:])
        w = max(d.textlength(a, font=f), d.textlength(b, font=f))
        if best is None or w < best[0]:
            best = (w, [a, b])
    return best[1] if best else [text]


def band_h(H):
    return int(round(0.13 * H / 2)) * 2


def draw_caption_bar(d, text, t, a, b, W, H, sc):
    """Rögzített feliratsáv a kép alján (a 3D-kép a sáv fölött van); max. 2 sor, középre zárva."""
    bh = band_h(H)
    k = eo((t - a) / 0.15) * (1 - eo((t - b + 0.12) / 0.12))
    if k <= 0.01 or not text:
        return
    maxw = W - 2 * 0.06 * W
    size = 41.5 * sc
    while True:
        f = font(size, 600, 100)
        lines = wrap_px(d, text, f, maxw)
        lh = size * 1.22
        if (all(d.textlength(ln, font=f) <= maxw for ln in lines) and lh * len(lines) <= bh - 10 * sc) \
                or size < 28 * sc:
            break
        size -= 1.5 * sc
    cap = f.getbbox("Hg") if not CJK else f.getbbox("中")
    y0 = H - bh + (bh - lh * len(lines)) / 2
    for j, ln in enumerate(lines):
        w = d.textlength(ln, font=f)
        d.text(((W - w) / 2, y0 + j * lh + (lh - (cap[3] - cap[1])) / 2 - cap[1]), ln,
               font=f, fill=INK + (int(255 * k),))


def draw_end_card(img, t, t0, W, H, sc):
    k = eo((t - t0) / 0.6)
    if k <= 0:
        return 0.0
    ov = Image.new("RGBA", img.size, PAGE + (int(255 * k),))
    d = ImageDraw.Draw(ov)
    kt = eo((t - t0 - 0.35) / 0.5)
    if kt > 0:
        txt = __import__("cues").TXT["card"]
        fs = 132 * sc
        while True:
            f = font(fs, 800, 62)
            tw = d.textbbox((0, 0), txt, font=f)[2]
            if tw <= 0.88 * W or fs < 60 * sc:
                break
            fs -= 4 * sc
        y = 0.40 * H + (1 - kt) * 30 * sc
        d.text(((W - tw) / 2, y), txt, font=f, fill=INK + (int(255 * kt),))
        bw = 120 * sc * eo((t - t0 - 0.6) / 0.4)
        d.rectangle([(W - bw) / 2, y - 34 * sc, (W + bw) / 2, y - 24 * sc], fill=AMBER + (int(255 * kt),))
        ku = eo((t - t0 - 0.7) / 0.5)
        fu = font(36 * sc, 500, 100)
        url = "peti-polinvent.github.io/kompozit-erthetoen"
        uw = d.textbbox((0, 0), url, font=fu)[2]
        d.text(((W - uw) / 2, y + 170 * sc + (1 - ku) * 16 * sc), url, font=fu, fill=MUTED + (int(255 * ku),))
    img.alpha_composite(ov)
    return k


_CTX = {}


def _light_frame(idx):
    c = _CTX
    path = os.path.join(c["dir"], f"{idx:05d}.png")
    if not os.path.exists(path):
        return
    img = Image.open(path).convert("RGBA")
    W, H = img.size
    sc = W / 1920.0
    t = idx / c["fps"]
    mask = os.path.join(c["dir"], f"{idx:05d}_mask.png")
    if os.path.exists(mask):
        draw_highlight_light(img, mask, sc)
        os.remove(mask)
    cv = c.get("canvas")
    if cv and (W, H) != tuple(cv):
        # a 3D-kép a sáv fölé kerül; alul a rögzített feliratsáv (oldalszínű, „raised” tónus)
        full = Image.new("RGBA", tuple(cv), BAND_COL + (255,))
        full.paste(img, (0, 0))
        img, (W, H) = full, tuple(cv)
    elif cv:
        ImageDraw.Draw(img).rectangle([0, H - band_h(H), W, H], fill=BAND_COL + (255,))
    if t < 0.45:                                        # nyitás: az oldal színéből
        img.alpha_composite(Image.new("RGBA", img.size, PAGE + (int(255 * (1 - eo(t / 0.45))),)))
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    si = max(j for j, s in enumerate(c["scenes"]) if s["f0"] <= idx)
    s = c["scenes"][si]
    a, b = s["f0"] / c["fps"], s["f1"] / c["fps"]
    import cues
    draw_title(d, cues.TITLES[si], t, a, b, W, H, sc)
    evs = s["ev"]
    if si == 1:
        draw_checklist(d, evs, t, a, b, W, H, sc, None)
    if si == 2:
        draw_layer_stack(d, evs, t, a, b, W, H, sc)
    for e in evs:
        if e["a0"] - 0.05 <= t <= e["a1"] + 0.05:
            draw_lower_third(d, e, t, W, H, sc)
    card_t0 = c["card_t0"]
    if card_t0 is None or t < card_t0 + 0.3:
        for (sa, sb, txt) in c["subs"]:
            if sa - 0.05 <= t <= sb + 0.05:
                draw_caption_bar(d, txt, t, sa, sb, W, H, sc)
    img.alpha_composite(ov)
    if card_t0 is not None:
        draw_end_card(img, t, card_t0, W, H, sc)
    img.convert("RGB").save(path, compress_level=1)


def _init_light(ctx):
    _CTX.update(ctx)
    sys.path.insert(0, HERE)


def main_light(frames_dir, plan_path, subs_path, canvas=None):
    sys.path.insert(0, HERE)
    import cues
    with open(plan_path, encoding="utf-8") as f:
        plan = json.load(f)
    with open(subs_path, encoding="utf-8") as f:
        subs = json.load(f)
    fps = plan["fps"]
    f0, scenes = 0, []
    for s in plan["scenes"]:
        evs = cues.resolve(s) if s.get("words") else []
        for e in evs:
            e["abs0"] = s["start"] + e["t0"]
            e["a0"] = e["abs0"] - 0.08
            e["a1"] = s["start"] + e["t1"]
        scenes.append(dict(f0=f0, f1=f0 + s["frames"], ev=evs))
        f0 += s["frames"]
    last = plan["scenes"][-1]
    kc = cues.extra(last, "card")
    card_t0 = last["start"] + kc - 0.25 if kc is not None else None
    ctx = dict(dir=frames_dir, fps=fps, scenes=scenes, subs=subs, card_t0=card_t0, canvas=canvas)
    idxs = list(range(plan["total_frames"]))
    from multiprocessing import Pool
    with Pool(max(1, (os.cpu_count() or 2) - 1), initializer=_init_light, initargs=(ctx,)) as pool:
        for n, _ in enumerate(pool.imap_unordered(_light_frame, idxs, chunksize=8)):
            if n % 200 == 0:
                print(f"[grafika] {n}/{len(idxs)}", flush=True)
    print(f"[grafika] {len(idxs)} képkocka kész")


if __name__ == "__main__":
    argv = sys.argv[1:]
    if "--plan" in argv:     # LIGHT stílus
        frames = argv[argv.index("--frames") + 1] if "--frames" in argv else os.path.join(HERE, "frames")
        cv = tuple(int(v) for v in argv[argv.index("--canvas") + 1].split("x")) if "--canvas" in argv else None
        main_light(frames, argv[argv.index("--plan") + 1], argv[argv.index("--subs") + 1], cv)
        sys.exit(0)
    frames = argv[argv.index("--frames") + 1] if "--frames" in argv else os.path.join(HERE, "frames")
    labels = argv[argv.index("--labels") + 1] if "--labels" in argv else os.path.join(HERE, "labels.json")
    main(frames, labels)
