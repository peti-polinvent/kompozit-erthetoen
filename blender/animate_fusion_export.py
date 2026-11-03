"""
animate_fusion_export.py – a Fusion 360-ból exportált testek animálása Blenderben
===================================================================================

Bemenet:  fusion/export/manifest.json + <key>.obj (vagy .stl) fájlok
          (a fusion/KompozitInfuzio szkript állítja elő)
Kimenet:  ugyanaz, mint a build_infusion.py-é: infusion.glb, infusion.blend,
          build_info.json, preview_*.png

    python blender/animate_fusion_export.py --export fusion/export --out build
    (ha a modell az oldalára dőlve jelenik meg: --yup kapcsolóval)

A geometria a Fusionból jön (CAD), az animáció – rétegek robbantása/összeállása,
gyantafront, gyantaszintek –, a kamera, a fény és az export a Blenderé
(build_infusion.animate_and_export). A mértékegységet a manifest adja (cm),
de biztonságból az asztal méretéből is ellenőrizzük.
"""

import bpy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import build_infusion as bi  # noqa: E402
from infusion_layout import compute_layout  # noqa: E402

UNIT_SCALE = {"mm": 0.001, "cm": 0.01, "m": 1.0, "in": 0.0254}


AXES = {"Z": dict(forward_axis="Y", up_axis="Z"),          # Fusion API-koordináták változatlanul
        "Y": dict(forward_axis="NEGATIVE_Z", up_axis="Y")}  # ha az export Y-fel tengelyű (--yup)


def import_mesh(path, up="Z"):
    """OBJ/STL import; visszaadja az új objektumo(ka)t."""
    before = set(bpy.data.objects)
    if path.lower().endswith(".obj"):
        bpy.ops.wm.obj_import(filepath=path, **AXES[up])
    else:
        bpy.ops.wm.stl_import(filepath=path, **AXES[up])
    return [o for o in bpy.data.objects if o not in before and o.type == "MESH"]


def join_objects(objs, name):
    if len(objs) == 1:
        objs[0].name = name
        return objs[0]
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    objs[0].name = name
    return objs[0]


def detect_scale(objs_by_key, layout, declared):
    """A Fusion cm-ben exportál; ha mégsem, az asztallap hosszából kiderül."""
    scale = UNIT_SCALE.get(declared, 0.01)
    tbl = objs_by_key.get("table_top")
    if tbl:
        raw_len = max(v.co.x for v in tbl.data.vertices) - min(v.co.x for v in tbl.data.vertices)
        want_mm = next(it["size_mm"][0] for it in layout["items"] if it["key"] == "table_top")
        for unit, s in UNIT_SCALE.items():
            if abs(raw_len * s / (want_mm * 0.001) - 1.0) < 0.05:
                if unit != declared:
                    print(f"[figyelem] a manifest {declared}-t mond, a geometria {unit}-ben van – {unit}-t használok")
                return s
    return scale


def main(export_dir, out_dir, previews, up="Z"):
    with open(os.path.join(export_dir, "manifest.json"), encoding="utf-8") as f:
        manifest = json.load(f)
    layout = compute_layout(bi.load_params())
    scene, cols = bi.new_scene()
    scene["source"] = "fusion360"

    objs = {}
    for entry in manifest["items"]:
        path = os.path.join(export_dir, entry["file"])
        if not os.path.exists(path):
            print("[hiányzik]", path)
            continue
        parts = import_mesh(path, up)
        if not parts:
            print("[üres]", path)
            continue
        obj = join_objects(parts, entry["name"])
        # gyűjteménybe sorolás
        for c in list(obj.users_collection):
            c.objects.unlink(obj)
        cols[entry["collection"]].objects.link(obj)
        # anyag a layout színeiből (a Fusion OBJ nem hoz megbízható anyagot)
        obj.data.materials.clear()
        obj.data.materials.append(bi.material_for(entry))
        obj["key"] = entry["key"]
        for k in ("layer_index", "layer_type", "thickness_mm"):
            if k in entry:
                obj[k] = entry[k]
        objs[entry["key"]] = obj

    # mértékegység: Fusion → méter
    s = detect_scale(objs, layout, manifest.get("units", "cm"))
    for obj in objs.values():
        for v in obj.data.vertices:
            v.co *= s
        obj.data.update()
        # az origó legyen a test közepén, hogy a robbantás a location-nel menjen
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
        obj.select_set(False)
        bpy.ops.object.shade_smooth() if obj.get("key", "").startswith(("spiral", "resin", "hose", "pump_", "buffer")) else None

    # a sweep-elt csövek Fusion-hálója nagyon sűrű (~1 MB/cső OBJ-ben) → ritkítás a webhez
    for key, obj in objs.items():
        if key.startswith("hose") and len(obj.data.polygons) > 4000:
            mod = obj.modifiers.new("Ritkitas", "DECIMATE")
            mod.ratio = 0.25
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.modifier_apply(modifier=mod.name)

    missing = [it["key"] for it in layout["items"] if it["key"] not in objs]
    if missing:
        print("[figyelem] a Fusion-exportból hiányzó testek:", ", ".join(missing))

    info = bi.animate_and_export(layout, objs, cols, out_dir)
    info["missing_from_fusion"] = missing
    with open(os.path.join(out_dir, "build_info.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
    if previews:
        bi.render_previews(out_dir, info)
    return info


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    export_dir = argv[argv.index("--export") + 1] if "--export" in argv else os.path.join(HERE, "..", "fusion", "export")
    out_dir = argv[argv.index("--out") + 1] if "--out" in argv else "build"
    # --yup: ha a Fusion-export Y-fel tengelyű (a modell "fekve" jelenne meg)
    main(export_dir, out_dir, "--no-preview" not in argv, up="Y" if "--yup" in argv else "Z")
