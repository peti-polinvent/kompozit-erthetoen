"""
render_scenes.py – jelenetenkénti kameramozgás és képkocka-render Blenderben
==============================================================================

Bemenet: build/infusion.blend (a Fusion-exportból animált jelenet, "Infuzio"
NLA-sáv, 1–289 képkocka) + video/scene_plan.json (a build_video.py írja: melyik
jelenet hány kimeneti képkockát kap – a narráció hosszából számolva).

Minden kimeneti képkockára külön beállítjuk a kamerát ÉS az animáció
időpontját (frame_set), majd állóképet renderelünk – így a rétegek
összeállása és a gyantafront vonulása a narráció tempójához igazodik.

    python video/render_scenes.py --plan video/scene_plan.json --out video/frames
    (a venv-bpy környezetben; Workbench motor, 1280×720, ~1,5–2 s/kép CPU-n)
"""

import bpy
import json
import math
import os
import sys
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))

TABLE_TOP = 0.75           # m (params.json: table height 750 mm)
Z0 = TABLE_TOP

# Az animáció kulcs-képkockái (build_info.json): robbantott 1–37, összeállás 37–109,
# tartás 109–133, infúzió 133–253, térhálósodás 253–277, bontás 277–349, vég 373.
F_EXPLODED, F_ASM0, F_ASM1, F_INF0, F_INF1, F_DM0, F_DM1, F_END = 1, 37, 109, 133, 253, 277, 349, 373


def lerp(a, b, t):
    return a + (b - a) * t


def ease(t):
    return t * t * (3 - 2 * t)


def orbit(center, radius, height, angle_deg):
    a = math.radians(angle_deg)
    return (center[0] + radius * math.cos(a), center[1] + radius * math.sin(a), center[2] + height)


# ---- Jelenetek: t ∈ [0,1] → (kamera hely, célpont, animációs képkocka, fókusz mm) --------

def ease_out(t, p=3.0):
    """Gyors indulás, lassú megérkezés (crash-zoom, becsapódás)."""
    return 1 - (1 - min(max(t, 0.0), 1.0)) ** p


def burst(t, t0, amp, decay=18.0):
    """Ütésre rázkódás: t0-tól exponenciálisan lecsengő amplitúdó (m)."""
    return amp * math.exp(-decay * (t - t0)) if t >= t0 else 0.0


# Egy jelenet-függvény visszatérése: (kamera, célpont, animációs képkocka, fókusz mm[, roll°, rázkódás m])
# A roll a kamera nézőtengelye körüli döntés (dutch angle), a rázkódás kézikamera-szerű mozgás amplitúdója.

def scene_1_intro(t):
    # „Hogyan készül egy kompozit termék?” – messziről, magasról becsapódunk az asztalhoz, körbesöprés
    c = (0.1, 0.0, Z0 + 0.05)
    k = ease_out(t / 0.45, 3.5) if t < 0.45 else 1.0
    r, h = lerp(2.9, 1.55, k), lerp(1.5, 0.62, k)
    ang = lerp(-150, -70, ease(t))
    return orbit(c, r, h, ang), c, F_INF0 - 5, lerp(32, 44, k), lerp(-8.0, 0.0, k), 0.004 + burst(t, 0.45, 0.012)


def scene_2_equipment(t):
    # „Kell egy szerszám, gyantatartály, vákuumszivattyú, puffertartály, gyantacsapda” – a berendezések
    # sorban kiemelve (EQUIP_WINDOWS), a kamera lassan a tartály felől a szivattyú felé úszik
    c = (lerp(-0.05, 0.3, ease(t)), 0.0, Z0 + 0.1)
    cam = (lerp(-0.9, -0.2, ease(t)), lerp(-1.5, -1.35, ease(t)), Z0 + lerp(0.7, 0.62, ease(t)))
    return cam, c, F_INF0 - 5, 36, lerp(-2.0, 1.5, t), 0.003


EXTRA_GAP_SCENE = {2: 0.022}   # jelenet-index → plusz hézag rétegenként (m) a robbantott nézetben

TOUR_END = 0.84   # a 3. jelenet első 84%-a a robbantott „túra” (rétegek kiemelve), a maradék az összeállás


def scene_3_layup(t):
    # „A rétegrend” – tiszta oldalnézet, a rétegek sorban kiemelve (punch-in minden tételnél),
    # a végén gyors összeállás és a fólia ráfeszülése
    # a kamera a köteg fölül néz le (~12°), hogy a lapok felső, megvilágított oldala látsszon
    c = (0.0, 0.0, Z0 + 0.2)
    cam = (0.0, lerp(-1.6, -1.45, ease(t)), Z0 + lerp(0.56, 0.5, ease(t)))
    lens = 56.0
    shake = 0.001
    if t < TOUR_END:
        f = F_EXPLODED
        for _, t0, _ in LAYUP_WINDOWS:
            if t >= t0:
                lens += 8.0 * math.exp(-110.0 * (t - t0))   # punch-in, kb. 1 s alatt visszaáll
    else:
        u = (t - TOUR_END) / (1 - TOUR_END)
        f = lerp(F_ASM0 - 8, F_INF0 - 3, u)
        for st in LAYER_SETTLE:
            shake += burst(u, st, 0.012, decay=22.0)
        cam = (lerp(0.0, 0.05, u), lerp(-1.45, -1.3, u), Z0 + lerp(0.5, 0.45, u))
    return cam, c, f, lens, 0.0, shake


def scene_4_infusion(t):
    # „Injektálás” – alacsony, döntött kamera a meglövés felől, a gyantafront átvonul (0–0.7),
    # majd „hagyjuk térhálósodni”: lassú ráközelítés a kész lapra (0.7–1)
    c = (0.05, -0.02, Z0 + 0.04)
    if t < 0.7:
        u = t / 0.7
        cam = (lerp(-1.05, -0.55, u), lerp(-0.7, -0.98, u), Z0 + lerp(0.42, 0.62, u))
        return cam, c, lerp(F_INF0, F_INF1, u), lerp(40, 46, u), lerp(-5.0, -1.5, u), 0.003
    u = (t - 0.7) / 0.3
    cam = (lerp(-0.55, -0.35, u), lerp(-0.98, -0.8, u), Z0 + lerp(0.62, 0.7, u))
    return cam, c, lerp(F_INF1, F_DM0 - 1, u), lerp(46, 52, u), lerp(-1.5, 0.0, u), 0.002


def scene_5_demold(t):
    # „Bontás” – elölről-felülről: a fólia, a háló, a letépő szövet lekerül, a termék leemelkedik
    c = (0.0, 0.05, Z0 + 0.12)
    cam = orbit(c, lerp(1.25, 1.1, ease(t)), lerp(0.85, 0.7, ease(t)), lerp(-105, -75, ease(t)))
    shake = 0.003
    D = F_DM1 - F_DM0
    if DEMOLD_SEC:
        # a narrációhoz kötve: „A letépő szövettel…” → a rétegek indulnak (bontás 4%-a),
        # „…a termék lekerül” → a termék emelése indul (60%), utána ~0,22 jelenetnyi idő alatt felemelkedik
        a, b = DEMOLD_SEC
        if t < a:
            p = lerp(0.0, 0.04, t / a)
        elif t < b:
            p = lerp(0.04, 0.6, (t - a) / (b - a))
        else:
            p = min(1.0, 0.6 + 0.4 * (t - b) / 0.24)
        aframe = F_DM0 + D * p
    else:
        p = t * 1.15 * (F_END - F_DM0) / D
        aframe = lerp(F_DM0, F_END, min(t * 1.15, 1.0))
    for st in (0.04, 0.6):          # a csomag (fólia+háló+letépő) indulása és a termék emelése
        shake += burst(p, st, 0.01, decay=20.0)
    return cam, c, aframe, 44, lerp(-4.0, 0.0, t), shake


def scene_6_outro(t):
    # „Kész.” – hátrálva-emelkedve kisöprünk a jelenetből
    c = (0.1, 0.0, Z0 + 0.08)
    k = ease(t)
    cam = orbit(c, lerp(1.45, 2.8, k), lerp(0.6, 1.45, k), lerp(-30, -115, k))
    return cam, c, F_END, lerp(40, 32, k), lerp(0.0, -7.0, k), 0.003


SCENES = [scene_1_intro, scene_2_equipment, scene_3_layup, scene_4_infusion, scene_5_demold, scene_6_outro]

# =====================================================================================
# LIGHT stílus (alapértelmezett; ACTION=1 → a fenti akció-jelenetek): világos, barátságos,
# a weboldallal harmonizáló kép. Nincs döntés, rázkódás, crash-zoom: lágyan gyorsuló-lassuló
# kameramozgás, 2–4 s-os beállítások, tiszta vágások a tételek / jelenetek határán.
# A jelenet-függvények (t, s) → (kamera, célpont, animációs képkocka, fókusz mm).
# =====================================================================================
STYLE = "action" if os.environ.get("ACTION") == "1" else os.environ.get("STYLE", "light")
LEAD_S = 0.0          # a build_video.py LEAD-je (az 1. jelenet képkockái ennyivel a hang előtt indulnak)
POS = {}              # objektumkulcs-csoport → (középpont, méret) – a main() tölti
EV = {}               # jelenet-index → cues.resolve() (másodperc a jelenet hangjától)
EXTRA_NOW = [0.0]     # a robbantott nézet plusz hézaga az aktuális képkockán


def eio(u):
    """ease-in-out (köbös), [0,1] → [0,1]."""
    u = min(max(u, 0.0), 1.0)
    return 4 * u ** 3 if u < 0.5 else 1 - (-2 * u + 2) ** 3 / 2


def vlerp(a, b, u):
    return tuple(x + (y - x) * u for x, y in zip(a, b))


def run_shots(ts, shots):
    """shots: [(kezdet s, vég s, cam0, cam1, tgt0, tgt1, lens0, lens1)] – az aktuális beállítás
    lágy mozgása (smoothstep); a beállítások között vágás."""
    cur = shots[0]
    for sh in shots:
        if ts >= sh[0]:
            cur = sh
    a, b, c0, c1, g0, g1, l0, l1 = cur
    u = ease((ts - a) / max(b - a, 1e-3)) if b > a else 0.0
    u = min(max(u, 0.0), 1.0)
    return vlerp(c0, c1, u), vlerp(g0, g1, u), l0 + (l1 - l0) * u


def scene_time(t, s):
    return t * s["length"] - (LEAD_S if s["index"] == 0 else 0.0)


def ev_t(idx, j, default):
    e = EV.get(idx, [])
    return e[j]["t0"] if len(e) > j else default


WIDE_A = ((-1.25, -2.65, 1.42), (-0.95, -2.35, 1.34), (0.06, 0.0, 0.46), (0.06, 0.0, 0.5), 30.0, 32.0)


def light_1_intro(t, s):
    # nyitó nagytotál (az asztal alatt a sewerbot Compact dob is látszik), majd lassú körbejárás
    ts, L = scene_time(t, s), s["length"] - LEAD_S
    cut = 0.48 * L
    if ts < cut:
        c0, c1, g0, g1, l0, l1 = WIDE_A
        cam, tgt, lens = run_shots(ts, [(-LEAD_S, cut, c0, c1, g0, g1, l0, l1)])
    else:
        u = (ts - cut) / max(L - cut, 1e-3)
        c = (0.0, 0.0, Z0 + 0.03)
        cam, tgt, lens = orbit(c, 0.98, 0.42, lerp(-128, -72, ease(u))), c, 40.0
    return cam, tgt, lerp(F_INF0 + 40, F_INF0 + 64, min(max(t, 0), 1)), lens


EQUIP_VIEW = [  # (nézési irány a tárgytól a kamera felé, távolság m)
    ((0.0, -1.0, 0.85), 1.25),     # szerszám (a kötegével)
    ((-0.6, -1.0, 0.55), 0.78),    # gyantatartály
    ((0.35, 1.0, 0.65), 0.9),      # vákuumszivattyú – hátulról, a csapda nem takarja
    ((0.75, -1.0, 0.6), 1.0),      # puffertartály
    ((-0.25, -1.0, 0.55), 0.82),   # gyantacsapda
]


def light_2_equipment(t, s):
    ts = scene_time(t, s)
    ev = EV.get(1, [])
    shots = []
    for j, (d, dist) in enumerate(EQUIP_VIEW):
        if j >= len(ev):
            break
        a = -1.0 if j == 0 else ev[j]["t0"] - 0.12
        b = ev[j + 1]["t0"] - 0.12 if j + 1 < len(ev) else s["length"]
        cen = POS.get(tuple(ev[j]["keys"]), (Vector((0, 0, Z0)), 0.3))[0]
        dv = Vector(d).normalized()
        fwd = -dv
        right = fwd.cross(Vector((0, 0, 1))).normalized()
        tgt = cen + right * (0.12 * dist)          # a tárgy kissé balra: jobbra a checklista
        c0, c1 = tgt + dv * dist * 1.06, tgt + dv * dist * 0.93
        shots.append((a, b, tuple(c0), tuple(c1), tuple(tgt), tuple(tgt), 35.0, 36.0))
    if not shots:
        return light_1_intro(1.0, s)
    cam, tgt, lens = run_shots(ts, shots)
    return cam, tgt, F_INF0 - 5, lens


def light_3_layup(t, s):
    ts = scene_time(t, s)
    L = s["length"]
    t_peel, t_tape = ev_t(2, 2, 0.4 * L), ev_t(2, 6, 0.75 * L)   # letépő szövet, tömítőszalag
    tour_end = TOUR_END * L
    if ts < tour_end:
        EXTRA_NOW[0] = EXTRA_GAP_SCENE[2]
        cam, tgt, lens = run_shots(ts, [
            (0.0, t_peel, (-0.12, -1.58, Z0 + 0.5), (0.0, -1.5, Z0 + 0.5), (0.1, 0, Z0 + 0.2), (0.1, 0, Z0 + 0.2), 50, 52),
            (t_peel, t_tape, (0.5, -1.38, Z0 + 0.62), (0.42, -1.34, Z0 + 0.6), (0.12, 0, Z0 + 0.21), (0.12, 0, Z0 + 0.21), 50, 51),
            (t_tape, tour_end, (-0.32, -1.45, Z0 + 0.46), (-0.26, -1.4, Z0 + 0.46), (0.1, 0, Z0 + 0.19), (0.1, 0, Z0 + 0.19), 50, 52)])
        return cam, tgt, F_EXPLODED, lens
    u = (ts - tour_end) / max(L - tour_end, 1e-3)
    EXTRA_NOW[0] = EXTRA_GAP_SCENE[2] * (1 - eio(min(u * 1.4, 1.0)))
    cam, tgt, lens = run_shots(ts, [(tour_end, L, (-0.6, -1.05, Z0 + 0.72), (-0.5, -0.95, Z0 + 0.66),
                                     (0.06, 0, Z0 + 0.06), (0.06, 0, Z0 + 0.03), 40, 42)])
    return cam, tgt, lerp(F_ASM0 - 8, F_ASM1 + 1, eio(u)), lens


F_SUCK0, F_SUCK1 = F_ASM1 + 3, F_INF0 - 3     # a fólia ráfeszülése (build_infusion.py: f_suck0/1)


def light_4_infusion(t, s):
    ts = scene_time(t, s)
    L = s["length"]
    t_suck, t_open, t_cure = ev_t(3, 0, 1.0), ev_t(3, 1, 0.35 * L), ev_t(3, 2, 0.8 * L)
    if ts < t_open - 0.15:
        f = lerp(F_SUCK0 - 1, F_SUCK1 + 1, eio((ts - t_suck + 0.1) / 1.1))
        cam, tgt, lens = run_shots(ts, [(0.0, t_open, (0.55, -0.95, Z0 + 0.5), (0.45, -0.85, Z0 + 0.44),
                                         (0.0, 0.0, Z0 + 0.01), (0.0, 0.0, Z0 + 0.01), 42, 46)])
        return cam, tgt, f, lens
    if ts < t_cure - 0.1:
        u = (ts - t_open) / max(t_cure - t_open, 1e-3)
        cam, tgt, lens = run_shots(ts, [(t_open - 0.15, t_cure, (-1.0, -0.72, Z0 + 0.45), (-0.62, -0.95, Z0 + 0.6),
                                         (0.04, -0.02, Z0 + 0.03), (0.06, -0.02, Z0 + 0.03), 40, 44)])
        return cam, tgt, lerp(F_INF0, F_INF1, min(max(u, 0), 1)), lens
    u = (ts - t_cure) / max(L - t_cure, 1e-3)
    c = (0.0, 0.0, Z0 + 0.02)
    return orbit(c, lerp(0.9, 0.8, ease(u)), 0.5, lerp(-60, -40, ease(u))), c, lerp(F_INF1, F_DM0 - 1, min(u, 1)), 44


def light_5_demold(t, s):
    ts = scene_time(t, s)
    c = (0.0, 0.05, Z0 + 0.12)
    cam = orbit(c, lerp(1.25, 1.08, ease(t)), lerp(0.85, 0.72, ease(t)), lerp(-105, -80, ease(t)))
    D = F_DM1 - F_DM0
    a, b = ev_t(4, 0, 0.3 * s["length"]), ev_t(4, 1, 0.6 * s["length"])
    if ts < a - 0.2:
        p = 0.0
    elif ts < b:
        p = 0.6 * eio((ts - a + 0.2) / max(b - a + 0.2, 1e-3))
    else:
        p = 0.6 + 0.4 * eio((ts - b) / 1.6)
    return cam, c, F_DM0 + D * p, 44


def light_6_outro(t, s):
    # záró nagytotál (a dob újra látszik), lassú hátrálás; a végén a zárókártya (annotate) takarja
    c0, c1, g0, g1, l0, l1 = WIDE_A
    u = eio(t)
    return vlerp(c1, c0, u), vlerp(g1, g0, u), F_END, l1 + (l0 - l1) * u


SCENES_LIGHT = [light_1_intro, light_2_equipment, light_3_layup, light_4_infusion, light_5_demold, light_6_outro]

# ---- Címkék (buborék + nyíl): jelenet → [(objektum-kulcs, szöveg, (dx,dy) px eltolás, t0, t1)] ---
# A kulcs a layout 'key' mezője (obj["key"]). dx,dy: a buborék helye a célponthoz képest
# (720p-s képre; kisebb felbontásnál arányosan skálázódik).
LAYER_KEYS = ["L01_release", "L02_glass", "L03_glass", "L04_glass", "L05_glass",
              "L06_peelply", "L07_flowmesh", "L08_bag_film"]
NL = len(LAYER_KEYS)
# mikor ér a helyére az i. réteg a 3. jelenet összeállás-szakaszában (az összeállás lépcsőzése: 36·i/(n−1) + 36 képkocka)
_ASM_SPAN = (F_INF0 - 3) - (F_ASM0 - 8)
LAYER_SETTLE = [(36 * i / (NL - 1) + 36 + 8) / _ASM_SPAN for i in range(NL)]

# A recept tételei a 3. jelenetben: (objektum-kulcsok, t0, t1) – a narráció sorrendjében
LAYUP_WINDOWS = [
    (["L01_release"], 0.12, 0.20),                                       # formaleválasztó
    (["L02_glass", "L03_glass", "L04_glass", "L05_glass"], 0.20, 0.44),  # erősítő rétegek (kombináció)
    (["L06_peelply"], 0.44, 0.52),                                       # letépő szövet
    (["L07_flowmesh"], 0.52, 0.60),                                      # gyantavezető háló
    (["spiral_inlet", "spiral_vacuum"], 0.60, 0.70),                     # meglövési és elszívási pont
    (["tape_xm", "tape_xp", "tape_ym", "tape_yp"], 0.70, 0.77),          # tömítőszalag
    (["L08_bag_film"], 0.77, 0.84),                                      # vákuumfólia
]
PUMP_KEYS = ["pump_base", "pump_motor", "pump_fan_cover", "pump_feet", "pump_head", "pump_port_in",
             "pump_exhaust", "pump_sight_glass"]
EQUIP_WINDOWS = [
    (["tool"], 0.02, 0.20),
    (["resin_pot", "resin_pot_lid"], 0.20, 0.38),
    (PUMP_KEYS, 0.38, 0.56),
    (["buffer_tank"], 0.56, 0.74),
    (["resin_trap", "resin_trap_lid"], 0.74, 0.92),
]
# Kiemelések: jelenet → [(objektum-kulcsok, szöveg, (dx,dy), t0, t1)] – a szöveg üres: nincs buborék,
# csak a fénylő körvonal (a narráció és a felirat nevezi meg az alkatrészt)
HIGHLIGHTS = {
    1: [(keys, "", (0, 0), t0, t1) for keys, t0, t1 in EQUIP_WINDOWS],
    2: [(keys, "", (0, 0), t0, t1) for keys, t0, t1 in LAYUP_WINDOWS],
}
DEMOLD_SEC = None   # (letépő szövet indul, termék emelése indul) s – a narrációból, ha ismert


def apply_word_timing(plan):
    """A kiemelések kezdete a kimondott szóhoz (TTS szóhatár-események a scene_plan.json-ban):
    minden tétel a kulcsszava előtt 0,15 s-mal kezd fénylani, és a következő tételig tart."""
    global EQUIP_WINDOWS, LAYUP_WINDOWS, TOUR_END, DEMOLD_SEC

    def at(s, word, nth=0):
        hits = [w for w in s["words"] if w["text"].lower().startswith(word.lower())]
        return hits[nth]["start"] if len(hits) > nth else None

    def windows(s, items, end_t):
        L = s["length"]
        ts = [at(s, w) for _, w in items]
        if any(v is None for v in ts):
            print("[időzítés] hiányzó kulcsszó, marad a régi ütemezés:", s["key"]); return None
        out = []
        for j, (keys, _) in enumerate(items):
            t0 = max(0.0, (ts[j] - 0.15) / L)
            t1 = (ts[j + 1] - 0.15) / L if j + 1 < len(items) else end_t
            out.append((keys, t0, t1))
        return out

    if STYLE == "light":
        # a kulcsszavak a cues.py-ból (egy forrás a 3D-nek, a grafikának és a hangeffekteknek)
        global LEAD_S
        sys.path.insert(0, HERE)
        import cues
        LEAD_S = plan.get("lead", 0.0)
        for s in plan["scenes"]:
            EV[s["index"]] = cues.resolve(s) if s.get("words") else []
        for idx in (1, 2):
            s = plan["scenes"][idx]
            L = s["length"]
            HIGHLIGHTS[idx] = [(e["keys"], "", (0, 0), max(0.0, (e["t0"] - 0.1) / L), min(1.0, (e["t1"] - 0.1) / L))
                               for e in EV[idx]]
        if EV[2] and EV[2][-1].get("layer") == "bag":
            TOUR_END = EV[2][-1]["t0"] / plan["scenes"][2]["length"] + 0.04
        print("[időzítés] light:", {k: [round(e["t0"], 2) for e in v] for k, v in EV.items()})
        return
    for s in plan["scenes"]:
        if not s.get("words"):
            continue
        L = s["length"]
        if s["index"] == 1:
            w = windows(s, [(["tool"], "szerszám"), (["resin_pot", "resin_pot_lid"], "gyantatartály"),
                            (PUMP_KEYS, "vákuumszivattyú"), (["buffer_tank"], "puffertartály"),
                            (["resin_trap", "resin_trap_lid"], "gyantacsapda")], None)
            if w:
                last = w[-1]
                ha = at(s, "Ha")
                w[-1] = (last[0], last[1], min(1.0, ((ha or s["audio_len"]) + 0.3) / L))
                EQUIP_WINDOWS = w
        elif s["index"] == 2:
            w = windows(s, [(["L01_release"], "Formaleválasztó"),
                            (["L02_glass", "L03_glass", "L04_glass", "L05_glass"], "erősítő"),
                            (["L06_peelply"], "Letépő"), (["L07_flowmesh"], "Gyantavezető"),
                            (["spiral_inlet", "spiral_vacuum"], "Meglövési"),
                            (["tape_xm", "tape_xp", "tape_ym", "tape_yp"], "Tömítőszalag"),
                            (["L08_bag_film"], "vákuumfólia")], 1.0)
            if w:
                # a robbantott túra a „vákuumfólia” szóig tart; a fólia az összeállás alatt is fénylik
                TOUR_END = w[-1][1] + 0.15 / L
                LAYUP_WINDOWS = w
        elif s["index"] == 4:
            a, b = at(s, "letépő"), at(s, "termék")
            if a is not None and b is not None:
                DEMOLD_SEC = (a / L, b / L)    # jelenet-arányban
    HIGHLIGHTS[1] = [(keys, "", (0, 0), t0, t1) for keys, t0, t1 in EQUIP_WINDOWS]
    HIGHLIGHTS[2] = [(keys, "", (0, 0), t0, t1) for keys, t0, t1 in LAYUP_WINDOWS]
    print("[időzítés] eszközök:", [(round(a, 2), round(b, 2)) for _, a, b in EQUIP_WINDOWS])
    print("[időzítés] rétegrend:", [(round(a, 2), round(b, 2)) for _, a, b in LAYUP_WINDOWS], "túra vége", round(TOUR_END, 2))


LABELS = {}     # buborékos címkék: nincsenek (a felhasználó kérése)
BRACES = {}     # kapcsos jelmagyarázat: nincs


def screen_rect(scene, cam, obj, width, height):
    from bpy_extras.object_utils import world_to_camera_view
    us, vs = [], []
    for c in obj.bound_box:
        cu, cv, cz = world_to_camera_view(scene, cam, obj.matrix_world @ Vector(c))
        if cz > 0:
            us.append(cu * width); vs.append((1 - cv) * height)
    return (min(us), min(vs), max(us), max(vs)) if us else None


def anchor_px(scene, cam, obj, width, height, key=None):
    """Objektum világbeli középpontja → képernyő-pixel (a kamera nézetéből).
    A gyantafrontnál nem a kitöltött tartomány közepe, hanem az ÉLE a célpont
    (ahol a gyanta éppen tart): a +X irányú (elszívás felőli) lap felső közepe."""
    from bpy_extras.object_utils import world_to_camera_view
    bb = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    center = sum(bb, Vector()) / 8
    if key == "resin_front":
        xmax = max(v.x for v in bb); zmax = max(v.z for v in bb)
        center = Vector((xmax - 0.004, center.y, zmax))
    u, v, z = world_to_camera_view(scene, cam, center)
    if z <= 0:
        return None
    # az alkatrész képernyő-téglalapja (a buborékok ne takarják más alkatrészek képét)
    us, vs = [], []
    for c in bb:
        cu, cv, cz = world_to_camera_view(scene, cam, c)
        if cz > 0:
            us.append(cu * width); vs.append((1 - cv) * height)
    rect = (min(us), min(vs), max(us), max(vs)) if us else None
    return (u * width, (1 - v) * height, rect)


def render_mask(scene, objs, path, width, height):
    """A kiemelt objektumok maszkja: minden más elrejtve, átlátszó film, AA nélkül, fél méret."""
    hidden = []
    for o in scene.objects:
        if o.type == "MESH" and o not in objs and not o.hide_render:
            o.hide_render = True; hidden.append(o)
    rx, ry, pct = scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage
    ft, aa, fp = scene.render.film_transparent, scene.display.render_aa, scene.render.filepath
    cm = scene.render.image_settings.color_mode
    scene.render.film_transparent = True
    scene.display.render_aa = "OFF"
    scene.render.resolution_percentage = 50
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    scene.render.film_transparent, scene.display.render_aa = ft, aa
    scene.render.resolution_percentage = pct
    scene.render.image_settings.color_mode = cm
    scene.render.filepath = fp
    for o in hidden:
        o.hide_render = False


def look_at(cam, target, roll_deg=0.0):
    q = (Vector(target) - Vector(cam.location)).to_track_quat("-Z", "Y")
    if roll_deg:
        from mathutils import Quaternion
        q = q @ Quaternion((0.0, 0.0, 1.0), math.radians(roll_deg))   # döntés a nézőtengely körül
    cam.rotation_euler = q.to_euler()


def handheld(time_s, amp):
    """Kézikamera-szerű, sima, determinisztikus remegés (szinuszok összege), amplitúdó m-ben."""
    if amp <= 0:
        return (0.0, 0.0, 0.0)
    x = math.sin(2 * math.pi * 1.3 * time_s) + 0.5 * math.sin(2 * math.pi * 3.1 * time_s + 1.0)
    y = math.sin(2 * math.pi * 1.7 * time_s + 2.0) + 0.5 * math.sin(2 * math.pi * 2.6 * time_s)
    z = math.sin(2 * math.pi * 2.2 * time_s + 0.7) + 0.5 * math.sin(2 * math.pi * 3.7 * time_s + 1.5)
    return (amp * x / 1.5, amp * y / 1.5, amp * z / 1.5)


def main(plan_path, out_dir, width=1280, height=720, start_at=0, only=None):
    with open(plan_path, encoding="utf-8") as f:
        plan = json.load(f)
    apply_word_timing(plan)
    bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, "build", "infusion.blend"))
    sc = bpy.context.scene
    cam = sc.camera
    sc.render.resolution_x, sc.render.resolution_y = width, height
    sc.render.resolution_percentage = 100
    if width / height > 16 / 9 + 0.01:
        # feliratsáv-változat: a 3D a sáv FÖLÖTTI, laposabb területre renderel. A függőleges
        # látószög marad a 16:9-es (VERTICAL illesztés), vízszintesen tágul – semmi nem vágódik le.
        cam.data.sensor_fit = "VERTICAL"
        cam.data.sensor_height = cam.data.sensor_width * 9 / 16
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.compression = 50
    os.makedirs(out_dir, exist_ok=True)

    by_key = {o["key"]: o for o in bpy.data.objects if o.get("key") is not None}
    by_key.setdefault("resin_front", bpy.data.objects.get("Gyantafront"))
    if STYLE == "light":
        # Workbench: stúdiófény, árnyék, cavity (élek), vékony sötét körvonal, anyagszínek;
        # háttér = a weboldal alapszíne (#eceeed), Standard színkezelés → a képkocka beleolvad az oldalba
        sh = sc.display.shading
        sh.light, sh.color_type = "STUDIO", "TEXTURE"      # anyagszín; a dobon a saját textúrája
        sh.show_shadows, sh.shadow_intensity = True, 0.35
        sh.show_cavity, sh.cavity_type = True, "BOTH"
        sh.cavity_ridge_factor, sh.cavity_valley_factor = 1.0, 1.0
        sh.show_object_outline = True
        sh.object_outline_color = (0.008, 0.010, 0.012)       # ~#15191d (lineáris)
        sc.view_settings.view_transform, sc.view_settings.look = "Standard", "None"
        srgb2lin = lambda c: (c / 255) / 12.92 if c / 255 <= 0.04045 else ((c / 255 + 0.055) / 1.055) ** 2.4
        sc.world.color = tuple(srgb2lin(c) for c in (0xEC, 0xEE, 0xED))
        sc.display.render_aa = os.environ.get("RENDER_AA", "16")
        for keys in [tuple(e["keys"]) for v in EV.values() for e in v if e["keys"]]:
            bb = [by_key[k].matrix_world @ Vector(c) for k in keys if by_key.get(k) for c in by_key[k].bound_box]
            if bb:
                lo = Vector((min(v.x for v in bb), min(v.y for v in bb), min(v.z for v in bb)))
                hi = Vector((max(v.x for v in bb), max(v.y for v in bb), max(v.z for v in bb)))
                POS[keys] = ((lo + hi) / 2, (hi - lo).length)
    strip_objs = [o for o in bpy.data.objects if o.get("layer_type") in ("bag", "flowmesh", "peelply")]
    labels_out = {}
    scale = width / 1280.0
    idx = 0
    for s in plan["scenes"]:
        fn = SCENES_LIGHT[s["index"]] if STYLE == "light" else SCENES[s["index"]]
        n = s["frames"]
        for k in range(n):
            if idx >= start_at and (only is None or idx in only):
                t = k / max(n - 1, 1)
                EXTRA_NOW[0] = EXTRA_GAP_SCENE.get(s["index"], 0.0)
                res = fn(t, s) if STYLE == "light" else fn(t)
                loc, target, aframe, lens = res[:4]
                roll = res[4] if len(res) > 4 else 0.0
                amp = res[5] if len(res) > 5 else 0.0
                j = handheld(s["start"] + t * s["length"], amp)
                cam.location = (loc[0] + j[0], loc[1] + j[1], loc[2] + j[2])
                look_at(cam, target, roll)
                cam.data.lens = lens
                sc.frame_set(int(round(aframe)))
                # a lebontott technológiai rétegek a záróképen ne lebegjenek a levegőben
                for o in strip_objs:
                    o.hide_render = s["index"] == 5
                extra = EXTRA_NOW[0]
                for o in by_key.values():      # delta_location: nem animált, a render is tiszteletben tartja
                    if o is not None and o.get("layer_index") is not None:
                        o.delta_location.z = extra * (int(o["layer_index"]) + 1)
                bpy.context.view_layer.update()
                frame_labels = []
                for key, text, (dx, dy), t0, t1 in LABELS.get(s["index"], []):
                    if t0 <= t <= t1 and by_key.get(key) is not None:
                        a = anchor_px(sc, cam, by_key[key], width, height, key)
                        if a:
                            frame_labels.append(dict(text=text, ax=a[0], ay=a[1], dx=dx * scale, dy=dy * scale,
                                                     rect=a[2], age=(t - t0) * s["length"]))
                brace_defs = BRACES.get(s["index"], [])
                for keys, text, t0, t1 in brace_defs:
                    if t0 <= t <= t1:
                        rects = [screen_rect(sc, cam, by_key[k], width, height) for k in keys if by_key.get(k)]
                        rects = [r for r in rects if r]
                        if rects:
                            frame_labels.append(dict(kind="brace", text=text,
                                                     x=min(r[0] for r in rects) - 12 * scale,
                                                     y0=min(r[1] for r in rects), y1=max(r[3] for r in rects),
                                                     age=(t - t0) * s["length"]))
                if frame_labels:
                    labels_out[idx] = frame_labels
                sc.render.filepath = os.path.join(out_dir, f"{idx:05d}.png")
                bpy.ops.render.render(write_still=True)
                # kiemelés-maszk: csak a kiemelt alkatrész(ek), átlátszó háttéren, fél felbontáson
                hl_keys = [k for keys, text, off, t0, t1 in HIGHLIGHTS.get(s["index"], [])
                           if t0 <= t <= t1 for k in keys if by_key.get(k) is not None]
                if hl_keys:
                    render_mask(sc, [by_key[k] for k in hl_keys], os.path.join(out_dir, f"{idx:05d}_mask.png"),
                                width, height)
                if idx % 50 == 0:
                    print(f"[render] {idx}/{plan['total_frames']}", flush=True)
            idx += 1
    with open(os.path.join(HERE, "labels.json"), "w", encoding="utf-8") as f:
        json.dump(labels_out, f, ensure_ascii=False)
    print("[render] kész:", idx, "képkocka;", len(labels_out), "címkézett")


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    plan = argv[argv.index("--plan") + 1] if "--plan" in argv else os.path.join(HERE, "scene_plan.json")
    out = argv[argv.index("--out") + 1] if "--out" in argv else os.path.join(HERE, "frames")
    start = int(argv[argv.index("--start") + 1]) if "--start" in argv else 0
    size = argv[argv.index("--size") + 1] if "--size" in argv else "1280x720"
    w, h = (int(v) for v in size.split("x"))
    only = None
    if "--only" in argv:   # csak a felsorolt képkocka-indexek (ellenőrző állóképekhez)
        only = {int(v) for v in argv[argv.index("--only") + 1].split(",")}
    main(plan, out, width=w, height=h, start_at=start, only=only)
