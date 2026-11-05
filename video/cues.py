"""
cues.py – a narráció kulcsszavai → kiemelések, címkék, pipák, jelenet-események (egy forrás)
=============================================================================================

A render_scenes.py (3D kiemelés, kamera, bontás-időzítés), az annotate_frames.py (feliratcímkék,
checklista, rétegrend-ábra) és a make_music.py (pipa-/whoosh-/sziszegés-hangok) is innen veszi,
hogy MIKOR hangzik el egy tétel neve (TTS szóhatár-események: video/tts/NN_words.json).
Ha a narráció szövege változik, csak a KULCSSZÓ oszlopot kell átírni.
"""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "..", "blender", "params.json"), encoding="utf-8") as _f:
    P = json.load(_f)
_E, _C, _L = P["equipment"], P["consumables"], {l["type"]: l for l in P["layup"]}

PUMP_KEYS = ["pump_base", "pump_motor", "pump_fan_cover", "pump_feet", "pump_head", "pump_port_in",
             "pump_exhaust", "pump_sight_glass"]
GLASS_KEYS = ["L02_glass", "L03_glass", "L04_glass", "L05_glass"]
TAPE_KEYS = ["tape_xm", "tape_xp", "tape_ym", "tape_yp"]

TITLES = ["A recept", "Hozzávalók", "A rétegrend", "Infúzió", "Bontás", ""]

# jelenet-index → [(kulcsszó-eleje, címke, [szín(ek)], 3D-objektumkulcsok, rétegábra-elem)]
ITEMS = {
    1: [("szerszám", "Szerszám", [P["tool"]["color"]], ["tool"], None),
        ("gyantatartály", "Gyantatartály", [_E["resin_pot"]["resin_color"]], ["resin_pot", "resin_pot_lid"], None),
        ("vákuumszivattyú", "Vákuumszivattyú", [_E["pump"]["color"]], PUMP_KEYS, None),
        ("puffertartály", "Puffertartály", [_E["buffer_tank"]["color"]], ["buffer_tank"], None),
        ("gyantacsapda", "Gyantacsapda", [_E["resin_trap"]["color"]], ["resin_trap", "resin_trap_lid"], None)],
    2: [("formaleválasztó", "Formaleválasztó", [_L["release"]["color"]], ["L01_release"], "release"),
        ("erősítő", "Erősítő szövetek", [_L["glass"]["color"]], GLASS_KEYS, "glass"),
        ("letépő", "Letépő szövet", [_L["peelply"]["color"]], ["L06_peelply"], "peelply"),
        ("gyantavezető", "Gyantavezető háló", [_L["flowmesh"]["color"]], ["L07_flowmesh"], "flowmesh"),
        ("belép", "Meglövési pont", [_C["inlet_spiral"]["color"]], ["spiral_inlet"], "spiral_in"),
        ("elszívjuk", "Elszívási pont", [_C["vacuum_spiral"]["color"]], ["spiral_vacuum"], "spiral_vac"),
        ("tömítőszalag", "Tömítőszalag", [_C["sealant_tape"]["color"]], TAPE_KEYS, "tape"),
        ("vákuumfólia", "Vákuumfólia", [_L["bag"]["color"]], ["L08_bag_film"], "bag")],
    3: [("ráfeszül", "Vákuum: a fólia ráfeszül", ["#15191d"], [], None),
        ("nyílik", "Nyílik a csap – jön a gyanta", [P["resin"]["color"]], [], None),
        ("megkeményedik", "A gyanta megkeményedik", ["#a86a12"], [], None)],
    4: [("egyben", "Fólia + háló + letépő szövet le", [_L["peelply"]["color"]], [], None),
        ("leválik", "A kész lap leválik", [_L["glass"]["color"]], [], None)],
}
EXTRA = {3: {"vakuum": "vákuum"}, 5: {"card": "kompozit"}}   # egyéb események (nincs címkéjük)


def word_time(words, prefix, nth=0):
    hits = [w for w in words if w["text"].lower().strip(".,;:!?–\"„”").startswith(prefix.lower())]
    return hits[nth]["start"] if len(hits) > nth else None


def resolve(scene):
    """scene (scene_plan.json eleme) → [{t0, t1, label, colors, keys, layer}] – másodperc a jelenet
    hangjának elejétől. t1 = a következő tétel kezdete, az utolsónál a hang vége + 0,3 s."""
    words = scene.get("words") or []
    out = []
    for kw, label, cols, keys, layer in ITEMS.get(scene["index"], []):
        t = word_time(words, kw)
        if t is None:
            print(f"[cues] hiányzó kulcsszó: {kw!r} ({scene['key']})")
            continue
        out.append(dict(t0=t, label=label, colors=cols, keys=keys, layer=layer))
    for j, e in enumerate(out):
        e["t1"] = out[j + 1]["t0"] if j + 1 < len(out) else scene["audio_len"] + 0.3
    return out


def extra(scene, name):
    kw = EXTRA.get(scene["index"], {}).get(name)
    return word_time(scene.get("words") or [], kw) if kw else None
