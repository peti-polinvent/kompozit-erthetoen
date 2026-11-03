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

# Az animáció kulcs-képkockái (build_info.json): robbantott 1–37, összeállás
# 37–109, tartás 109–133, infúzió 133–253, vég 253–289.
F_EXPLODED, F_ASM0, F_ASM1, F_INF0, F_INF1, F_END = 1, 37, 109, 133, 253, 289


def lerp(a, b, t):
    return a + (b - a) * t


def ease(t):
    return t * t * (3 - 2 * t)


def orbit(center, radius, height, angle_deg):
    a = math.radians(angle_deg)
    return (center[0] + radius * math.cos(a), center[1] + radius * math.sin(a), center[2] + height)


# ---- Jelenetek: t ∈ [0,1] → (kamera hely, célpont, animációs képkocka, fókusz mm) --------

def scene_1_intro(t):
    # lassú körbefordulás az összeállt asztal körül (infúzió előtt)
    c = (0.1, 0.0, Z0 + 0.05)
    return orbit(c, 1.65, 0.78, lerp(-125, -70, t)), c, F_INF0 - 5, 40


def scene_2_overview(t):
    # robbantott rétegrend, magasról, lassú közeledés
    c = (0.0, 0.0, Z0 + 0.12)
    cam = (lerp(-0.9, -0.7, ease(t)), lerp(-1.3, -1.0, ease(t)), Z0 + lerp(1.25, 1.05, ease(t)))
    return cam, c, F_EXPLODED, 42


def scene_3_layup(t):
    # oldalnézet közelről, a rétegek sorban a helyükre ereszkednek
    c = (0.0, 0.0, Z0 + 0.08)
    cam = (lerp(-0.55, -0.35, t), -1.05, Z0 + 0.42)
    f = lerp(F_ASM0 - 8, F_ASM1 + 6, t)
    return cam, c, f, 50


def scene_4_infusion(t):
    # 0–0.62: a gyantafront vonul (a bevezetés felől, kissé magasról)
    # 0.62–1: vágás a berendezésekre (csapda, puffertartály, műszerek)
    if t < 0.62:
        u = t / 0.62
        c = (0.05, -0.02, Z0 + 0.04)
        cam = (lerp(-0.95, -0.55, u), lerp(-0.85, -1.0, u), Z0 + lerp(0.75, 0.65, u))
        f = lerp(F_INF0, F_INF1, u)
        return cam, c, f, 45
    u = (t - 0.62) / 0.38
    c = (0.56, 0.0, Z0 + 0.12)
    cam = (lerp(0.2, 0.3, u), -0.95, Z0 + 0.55)
    return cam, c, F_INF1 - 2, 50


def scene_5_result(t):
    # kész lap felülről, majd a műszerekre közelítünk
    if t < 0.6:
        u = t / 0.6
        c = (0.0, 0.0, Z0 + 0.03)
        cam = (lerp(-0.1, 0.05, u), lerp(-0.75, -0.6, u), Z0 + lerp(0.95, 0.85, u))
        return cam, c, F_END, 42
    u = (t - 0.6) / 0.4
    c = (0.47, -0.1, Z0 + 0.27)
    cam = (lerp(0.1, 0.15, u), -0.5, Z0 + 0.45)
    return cam, c, F_END, 60


def scene_6_outro(t):
    c = (0.1, 0.0, Z0 + 0.05)
    return orbit(c, 1.75, 0.82, lerp(-70, -20, t)), c, F_END, 38


SCENES = [scene_1_intro, scene_2_overview, scene_3_layup, scene_4_infusion, scene_5_result, scene_6_outro]

# ---- Címkék (buborék + nyíl): jelenet → [(objektum-kulcs, szöveg, (dx,dy) px eltolás, t0, t1)] ---
# A kulcs a layout 'key' mezője (obj["key"]). dx,dy: a buborék helye a célponthoz képest
# (720p-s képre; kisebb felbontásnál arányosan skálázódik).
LAYER_SETTLE = [(36 * i / 8 + 36 + 8) / (F_ASM1 + 6 - (F_ASM0 - 8)) for i in range(9)]   # t a 3. jelenetben
LAYER_KEYS = ["L01_release", "L02_gelcoat", "L03_glass", "L04_glass", "L05_glass", "L06_glass",
              "L07_peelply", "L08_flowmesh", "L09_bag_film"]
LAYER_TEXT = ["Formaleválasztó fólia", "Gelcoat", "Üvegszövet 0/90°", "Üvegszövet ±45°", "Üvegszövet ±45°",
              "Üvegszövet 0/90°", "Tépőszövet (peel ply)", "Gyantavezető háló", "Vákuumfólia"]
LABELS = {
    1: [("tool", "Szerszám (alumínium lap)", (-250, 110), 0.15, 1.0),
        ("L04_glass", "Száraz erősítőrétegek", (-300, -30), 0.15, 1.0),
        ("L09_bag_film", "Vákuumfólia", (-230, -150), 0.15, 1.0),
        ("resin_pot", "Gyantatartály", (-40, -170), 0.15, 1.0),
        ("resin_trap", "Gyantacsapda", (-60, -230), 0.15, 1.0),
        ("buffer_tank", "Puffertartály", (210, -40), 0.15, 1.0),
        ("pump_motor", "Vákuumszivattyú", (150, -200), 0.15, 1.0)],
    # rétegek: egyszerre csak az épp helyére ereszkedő réteg címkéje, fix helyen bal oldalt
    2: [(LAYER_KEYS[i], LAYER_TEXT[i], (-340, -30), LAYER_SETTLE[i] - 0.015,
         (LAYER_SETTLE[i + 1] - 0.016) if i < 8 else 1.0) for i in range(9)],
    3: [("spiral_inlet", "Gyantabevezető spirálcső", (-150, -200), 0.02, 0.60),
        ("L08_flowmesh", "Gyantavezető háló", (260, -170), 0.10, 0.60),
        ("resin_front", "Gyantafront", (-40, 150), 0.22, 0.60),
        ("spiral_vacuum", "Vákuumelszívó spirálcső", (220, -60), 0.02, 0.60),
        ("resin_trap", "Gyantacsapda", (-230, -40), 0.64, 1.0),
        ("buffer_tank", "Puffertartály", (160, 150), 0.64, 1.0),
        ("pump_motor", "Vákuumszivattyú", (-120, -200), 0.64, 1.0),
        ("gauge_trap_case", "Vákuummérő: –0,65 bar", (240, -200), 0.64, 1.0)],
    4: [("gauge_trap_case", "Vákuummérő (zsákoldal)", (-260, -120), 0.62, 1.0),
        ("gauge_buffer_case", "Vákuummérő (puffertartály)", (160, -140), 0.62, 1.0)],
}


def anchor_px(scene, cam, obj, width, height):
    """Objektum világbeli középpontja → képernyő-pixel (a kamera nézetéből)."""
    from bpy_extras.object_utils import world_to_camera_view
    bb = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    center = sum(bb, Vector()) / 8
    u, v, z = world_to_camera_view(scene, cam, center)
    if z <= 0:
        return None
    return (u * width, (1 - v) * height)


def look_at(cam, target):
    cam.rotation_euler = (Vector(target) - Vector(cam.location)).to_track_quat("-Z", "Y").to_euler()


def main(plan_path, out_dir, width=1280, height=720, start_at=0):
    with open(plan_path, encoding="utf-8") as f:
        plan = json.load(f)
    bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, "build", "infusion.blend"))
    sc = bpy.context.scene
    cam = sc.camera
    sc.render.resolution_x, sc.render.resolution_y = width, height
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.compression = 50
    os.makedirs(out_dir, exist_ok=True)

    by_key = {o["key"]: o for o in bpy.data.objects if o.get("key") is not None}
    by_key.setdefault("resin_front", bpy.data.objects.get("Gyantafront"))
    labels_out = {}
    scale = width / 1280.0
    idx = 0
    for s in plan["scenes"]:
        fn = SCENES[s["index"]]
        n = s["frames"]
        for k in range(n):
            if idx >= start_at:
                t = k / max(n - 1, 1)
                loc, target, aframe, lens = fn(t)
                cam.location = loc
                look_at(cam, target)
                cam.data.lens = lens
                sc.frame_set(int(round(aframe)))
                bpy.context.view_layer.update()
                frame_labels = []
                for key, text, (dx, dy), t0, t1 in LABELS.get(s["index"], []):
                    if t0 <= t <= t1 and by_key.get(key) is not None:
                        a = anchor_px(sc, cam, by_key[key], width, height)
                        if a:
                            frame_labels.append(dict(text=text, ax=a[0], ay=a[1], dx=dx * scale, dy=dy * scale,
                                                     age=(t - t0) * s["length"]))
                if frame_labels:
                    labels_out[idx] = frame_labels
                sc.render.filepath = os.path.join(out_dir, f"{idx:05d}.png")
                bpy.ops.render.render(write_still=True)
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
    main(plan, out, width=w, height=h, start_at=start)
