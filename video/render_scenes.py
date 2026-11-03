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
    # robbantott rétegrend OLDALNÉZETBEN (a -Y oldalról, enyhe rálátás), lassú közeledés;
    # a rétegcsoportokat kapcsos zárójelek jelölik (BRACES)
    # majdnem tiszta oldalnézet (kb. 12° rálátás), a köteg a kép jobb felén; a rétegeket a
    # render EXTRA_GAP-pel jobban széthúzza (csak ebben a jelenetben, a GLB-t nem érinti)
    c = (-0.22, 0.0, Z0 + 0.25)
    cam = (lerp(-0.2, -0.22, ease(t)), lerp(-1.85, -1.75, ease(t)), Z0 + lerp(0.64, 0.6, ease(t)))
    return cam, c, F_EXPLODED, 60


EXTRA_GAP_SCENE = {1: 0.022}   # jelenet-index → plusz hézag rétegenként (m) a robbantott nézetben


TOUR_END = 0.66   # a 3. jelenet első 66%-a a robbantott "túra", a maradék az összeállás


def scene_3_layup(t):
    # TISZTA oldalnézet (a -Y oldalról, a rétegek magasságából): a rétegek vékony
    # csíkokként látszanak, és sorban ereszkednek a helyükre; lassú közelítés
    # 0–TOUR_END: robbantott állapot, a rétegek egyenként kiemelve (alulról felfelé);
    # TOUR_END–1: a rétegek sorban a helyükre ereszkednek
    c = (0.0, 0.0, Z0 + 0.14)
    cam = (0.0, lerp(-1.55, -1.42, ease(t)), Z0 + lerp(0.2, 0.17, ease(t)))
    if t < TOUR_END:
        f = F_EXPLODED
    else:
        f = lerp(F_ASM0 - 8, F_ASM1 + 6, (t - TOUR_END) / (1 - TOUR_END))
    return cam, c, f, 60



def scene_4_infusion(t):
    # 0–0.56: a gyantafront vonul (a bevezetés felől, kissé magasról)
    # 0.56–1: vágás a berendezésekre (csapda, puffertartály, műszerek)
    if t < 0.56:
        u = t / 0.56
        c = (0.05, -0.02, Z0 + 0.04)
        cam = (lerp(-0.95, -0.55, u), lerp(-0.85, -1.0, u), Z0 + lerp(0.75, 0.65, u))
        f = lerp(F_INF0, F_INF1, u)
        return cam, c, f, 45
    u = (t - 0.56) / 0.44
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
    c = (0.5, 0.0, Z0 + 0.22)
    cam = (lerp(0.0, 0.08, u), -0.85, Z0 + 0.62)
    return cam, c, F_END, 55


def scene_6_outro(t):
    c = (0.1, 0.0, Z0 + 0.05)
    return orbit(c, 1.75, 0.82, lerp(-70, -20, t)), c, F_END, 38


SCENES = [scene_1_intro, scene_2_overview, scene_3_layup, scene_4_infusion, scene_5_result, scene_6_outro]

# ---- Címkék (buborék + nyíl): jelenet → [(objektum-kulcs, szöveg, (dx,dy) px eltolás, t0, t1)] ---
# A kulcs a layout 'key' mezője (obj["key"]). dx,dy: a buborék helye a célponthoz képest
# (720p-s képre; kisebb felbontásnál arányosan skálázódik).
LAYER_KEYS = ["L01_gelcoat", "L02_glass", "L03_glass", "L04_glass", "L05_glass",
              "L06_peelply", "L07_flowmesh", "L08_bag_film"]
LAYER_TEXT = ["Gelcoat", "Üvegszövet 0/90°", "Üvegszövet ±45°", "Üvegszövet ±45°",
              "Üvegszövet 0/90°", "Tépőszövet (peel ply)", "Gyantavezető háló", "Vákuumfólia"]
NL = len(LAYER_KEYS)
# mikor ér a helyére az i. réteg a 3. jelenet idejében (az összeállás lépcsőzése: 36·i/(n−1) + 36 képkocka)
LAYER_SETTLE = [(36 * i / (NL - 1) + 36 + 8) / (F_ASM1 + 6 - (F_ASM0 - 8)) for i in range(NL)]
# Kiemelések: jelenet → [(objektum-kulcsok, szöveg, (dx,dy) címke-eltolás, t0, t1)].
# Az adott időablakban a felsorolt alkatrész(ek) fénylő körvonalat kapnak, és EGY névcímkét.
# Az időablakok a narráció mondataihoz igazodnak (arányosan a jelenet hosszához).
HIGHLIGHTS = {
    # robbantott túra: minden réteg egyforma ideig, alulról felfelé; az összeállás alatt nincs címke
    2: [([LAYER_KEYS[i]], LAYER_TEXT[i], (-420, 0), 0.02 + (TOUR_END - 0.04) * i / NL,
         0.02 + (TOUR_END - 0.04) * (i + 1) / NL - 0.004) for i in range(NL)],
    3: [(["spiral_inlet"], "Gyantabevezető spirálcső", (-150, -200), 0.04, 0.17),
        (["L08_flowmesh"], "Gyantavezető háló", (260, -170), 0.17, 0.30),
        (["resin_front"], "Gyantafront", (60, 140), 0.30, 0.45),
        (["spiral_vacuum"], "Vákuumelszívó spirálcső", (220, -60), 0.45, 0.56),
        (["resin_trap"], "Gyantacsapda", (-230, -40), 0.56, 0.72),
        (["buffer_tank"], "Puffertartály", (160, 150), 0.72, 0.84),
        (["gauge_trap_case", "gauge_trap_face"], "Vákuummérő: –0,65 bar", (240, -200), 0.84, 1.0)],
    4: [(["gauge_trap_case", "gauge_trap_face", "gauge_buffer_case", "gauge_buffer_face"],
         "Vákuummérők", (-260, -120), 0.62, 1.0)],
}
LABELS = {k: [(keys[0], text, off, t0, t1) for keys, text, off, t0, t1 in v] for k, v in HIGHLIGHTS.items()}

# Kapcsos zárójelek a 2. jelenethez: (objektum-kulcsok, szöveg, t0, t1) – a zárójel a csoport
# legfelső és legalsó elemének képernyő-magassága között fut, a köteg BAL széle mellett.
BRACES = {
    1: [(["L08_bag_film"], "Vákuumfólia", 0.12, 1.0),
        (["L06_peelply", "L07_flowmesh"], "Tépőszövet + gyantavezető háló", 0.12, 1.0),
        (["L02_glass", "L03_glass", "L04_glass", "L05_glass"], "Száraz erősítőrétegek (4× üvegszövet)", 0.12, 1.0),
        (["L01_gelcoat"], "Gelcoat", 0.12, 1.0),
        (["tool"], "Formaleválasztóval előkészített szerszám", 0.12, 1.0)],
}


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


def look_at(cam, target):
    cam.rotation_euler = (Vector(target) - Vector(cam.location)).to_track_quat("-Z", "Y").to_euler()


def main(plan_path, out_dir, width=1280, height=720, start_at=0, only=None):
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
            if idx >= start_at and (only is None or idx in only):
                t = k / max(n - 1, 1)
                loc, target, aframe, lens = fn(t)
                cam.location = loc
                look_at(cam, target)
                cam.data.lens = lens
                sc.frame_set(int(round(aframe)))
                extra = EXTRA_GAP_SCENE.get(s["index"], 0.0)
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
