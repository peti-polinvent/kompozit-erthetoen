"""
mock_fusion_export.py – "ál-Fusion" export teszteléshez
========================================================

A Fusion 360 nem fut a felhőben, ezért a Blender-oldali importáló-animáló
láncot (animate_fusion_export.py) egy Fusion-szerű exporttal teszteljük:
a build_infusion primitívjeit testenként OBJ-be írjuk CENTIMÉTERBEN, Z-fel
tengellyel, és ugyanolyan manifest.json-t készítünk, mint a Fusion-szkript.

    python blender/mock_fusion_export.py --out fusion/export_mock
    python blender/animate_fusion_export.py --export fusion/export_mock --out build_mock
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


def main(out_dir):
    layout = compute_layout(bi.load_params())
    scene, cols = bi.new_scene()
    objs = bi.build_primitives(layout, cols)
    os.makedirs(out_dir, exist_ok=True)
    manifest = {"units": "cm", "up_axis": "Z", "items": [], "notes": ["mock export (Blender primitívek)"],
                "frames": layout["frames"], "geo": layout["geo"], "warnings": []}
    for it in layout["items"]:
        obj = objs[it["key"]]
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        path = os.path.join(out_dir, it["key"] + ".obj")
        bpy.ops.wm.obj_export(filepath=path, export_selected_objects=True, forward_axis="Y", up_axis="Z",
                              global_scale=100.0, export_materials=False, apply_modifiers=True)
        entry = {k: it[k] for k in it if k not in ("size_mm", "center_mm", "p1_mm", "p2_mm", "points_mm")}
        entry["file"] = it["key"] + ".obj"
        manifest["items"].append(entry)
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print("mock export:", out_dir, len(manifest["items"]), "test")


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    main(argv[argv.index("--out") + 1] if "--out" in argv else "fusion/export_mock")
