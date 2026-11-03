"""
build_infusion.py – vákuuminfúziós összeállítás Blenderben, params.json-ból
=============================================================================

Két üzemmód, ugyanaz az animáció és export:

  1) Primitívekből (Fusion nélkül):
        python blender/build_infusion.py --out build
     A geometriát az infusion_layout.py számolja, itt hasábok/hengerek/csövek
     lesznek belőle.

  2) Fusion 360-ból exportált testekből:
        python blender/animate_fusion_export.py --out build
     (az a szkript ezt a modult importálja: anyagok, animáció, export közös)

Animáció:  robbantott rétegrend → rétegek sorban összeállnak a szerszámon →
           a gyanta a bevezetéstől az elszívásig átitatja a laminátumot,
           közben a tartály szintje csökken, a csapdában kevés gyanta jelenik meg.

Kimenetek: <out>/infusion.glb (web, model-viewer), <out>/infusion.blend,
           <out>/build_info.json, <out>/preview_*.png (Workbench render)
"""

import bpy
import json
import math
import os
import sys
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from infusion_layout import compute_layout  # noqa: E402

MM = 0.001  # 1 mm Blender-méterben


# ---------------------------------------------------------------------------
# Anyagok
# ---------------------------------------------------------------------------

def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def make_material(name, color_hex, alpha=1.0, roughness=0.6, metallic=0.0):
    """Principled BSDF anyag; átlátszó, ha alpha < 1 (glTF-be is átmegy)."""
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    r, g, b = hex_to_rgb(color_hex)
    bsdf.inputs["Base Color"].default_value = (r, g, b, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Alpha"].default_value = alpha
    mat.diffuse_color = (r, g, b, alpha)  # Workbench/Solid nézethez
    if alpha < 1.0:
        mat.surface_render_method = "BLENDED"
        mat.use_backface_culling = False
    return mat


def material_for(item):
    return make_material(f"M_{item['key']}", item["color"], alpha=item.get("alpha", 1.0),
                         roughness=item.get("roughness", 0.6), metallic=item.get("metallic", 0.0))


# ---------------------------------------------------------------------------
# Primitívek
# ---------------------------------------------------------------------------

def _box_mesh(name, sx, sy, sz, x0=None):
    """Hasáb-mesh. Ha x0 adott, az origó a -X oldali lapon van (skálázható)."""
    mesh = bpy.data.meshes.new(name)
    if x0 is None:
        hx, hy, hz = sx / 2, sy / 2, sz / 2
        xs = (-hx, hx)
    else:
        hy, hz = sy / 2, sz / 2
        xs = (0.0, sx)
    verts = [(xs[0], -hy, -hz), (xs[1], -hy, -hz), (xs[1], hy, -hz), (xs[0], hy, -hz),
             (xs[0], -hy, hz), (xs[1], -hy, hz), (xs[1], hy, hz), (xs[0], hy, hz)]
    faces = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    return mesh


def add_box(name, size, location, material, collection):
    obj = bpy.data.objects.new(name, _box_mesh(name, *size))
    collection.objects.link(obj)
    obj.location = location
    obj.data.materials.append(material)
    return obj


def add_box_origin_minx(name, size, min_corner_x, center_y, center_z, material, collection):
    """Hasáb, origója a -X lapon: X-skálázással 'növeszthető' (gyantafront)."""
    obj = bpy.data.objects.new(name, _box_mesh(name, *size, x0=0.0))
    collection.objects.link(obj)
    obj.location = (min_corner_x, center_y, center_z)
    obj.data.materials.append(material)
    return obj


def add_cylinder_between(name, radius, p1, p2, material, collection, segments=32):
    """Henger a p1→p2 tengely mentén."""
    p1, p2 = Vector(p1), Vector(p2)
    d = p2 - p1
    bpy.ops.mesh.primitive_cylinder_add(vertices=segments, radius=radius, depth=d.length,
                                        location=(p1 + p2) / 2)
    obj = bpy.context.active_object
    obj.name = name
    obj.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    for c in obj.users_collection:
        c.objects.unlink(obj)
    collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj


def add_cylinder_bottom_origin(name, radius, height, base_location, material, collection):
    """Henger, origója az ALJÁN (Z-skálázással folyadékszint animálható)."""
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=radius, depth=height,
                                        location=(0, 0, height / 2))
    obj = bpy.context.active_object
    obj.name = name
    for c in obj.users_collection:
        c.objects.unlink(obj)
    collection.objects.link(obj)
    obj.location = base_location
    obj.data.materials.append(material)
    return obj


def add_tube(name, points, radius, material, collection):
    """Bezier-görbe mentén futó cső, mesh-sé alakítva (glTF-hez)."""
    curve = bpy.data.curves.new(name, type="CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = radius
    curve.bevel_resolution = 4
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for bp, p in zip(spline.bezier_points, points):
        bp.co = Vector(p)
        bp.handle_left_type = bp.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(name, curve)
    collection.objects.link(obj)
    obj.data.materials.append(material)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.convert(target="MESH")
    obj.select_set(False)
    return obj


# ---------------------------------------------------------------------------
# Animációs segédek
# ---------------------------------------------------------------------------

def key_loc(obj, frame, loc):
    obj.location = loc
    obj.keyframe_insert(data_path="location", frame=frame)


def key_scale(obj, frame, scale):
    obj.scale = scale
    obj.keyframe_insert(data_path="scale", frame=frame)


def smooth_keys(obj):
    if obj.animation_data and obj.animation_data.action:
        for fc in obj.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.easing = "EASE_IN_OUT"


# ---------------------------------------------------------------------------
# Jelenet
# ---------------------------------------------------------------------------

COLLECTIONS = ["00_Asztal", "01_Szerszam", "02_Retegrend", "03_Segedanyagok",
               "04_Berendezesek", "05_Gyanta", "99_Kamera_Feny"]


def new_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "MILLIMETERS"
    cols = {}
    for n in COLLECTIONS:
        c = bpy.data.collections.new(n)
        scene.collection.children.link(c)
        cols[n] = c
    return scene, cols


def build_primitives(layout, cols):
    """Layout-itemek → Blender-objektumok. Visszaad: {key: obj}"""
    objs = {}
    for it in layout["items"]:
        mat = material_for(it)
        col = cols[it["collection"]]
        if it["kind"] == "box":
            size = [v * MM for v in it["size_mm"]]
            center = [v * MM for v in it["center_mm"]]
            obj = add_box(it["name"], size, center, mat, col)
            dl, dw = Vector(it.get("dir_len", (1, 0, 0))), Vector(it.get("dir_wid", (0, 1, 0)))
            if (dl - Vector((1, 0, 0))).length > 1e-6 or (dw - Vector((0, 1, 0))).length > 1e-6:
                from mathutils import Matrix
                obj.rotation_euler = Matrix((dl, dw, dl.cross(dw))).transposed().to_euler()
        elif it["kind"] == "cyl":
            obj = add_cylinder_between(it["name"], it["radius_mm"] * MM,
                                       [v * MM for v in it["p1_mm"]], [v * MM for v in it["p2_mm"]],
                                       mat, col)
        else:
            obj = add_tube(it["name"], [[v * MM for v in p] for p in it["points_mm"]],
                           it["radius_mm"] * MM, mat, col)
        obj["key"] = it["key"]
        if it["kind"] != "box":
            for poly in obj.data.polygons:
                poly.use_smooth = True
        if "layer_index" in it:
            obj["layer_index"] = it["layer_index"]
            obj["layer_type"] = it["layer_type"]
            obj["thickness_mm"] = it["thickness_mm"]
        objs[it["key"]] = obj
    return objs


def animate_and_export(layout, objs, cols, out_dir):
    """Közös rész: rétegek robbantás/összeállás, gyanta, kamera, fény, export.
    objs: {key: Blender-objektum} – a rétegek a layout 'layer_index' mezője
    alapján mozognak, a jelenlegi location-jük a nyugalmi helyzet."""
    scene = bpy.context.scene
    G, F = layout["geo"], layout["frames"]
    gap = F["explode_gap_mm"] * MM
    n = G["n_layers"]
    f_as0, f_as1 = F["assemble"]
    f_in0, f_in1 = F["infuse"]
    f_end = F["end"]

    # --- rétegek: robbantott → összeállt, lentről felfelé lépcsőzve
    for it in layout["items"]:
        if "layer_index" not in it or it["key"] not in objs:
            continue
        i = it["layer_index"]
        obj = objs[it["key"]]
        rest = Vector(obj.location)
        exploded = rest + Vector((0, 0, (i + 1) * gap))
        stagger = F["assemble_frames"] * 0.5 * i / max(n - 1, 1)
        dur = F["assemble_frames"] * 0.5
        key_loc(obj, 1, exploded)
        key_loc(obj, int(f_as0 + stagger), exploded)
        key_loc(obj, int(f_as0 + stagger + dur), rest)
        smooth_keys(obj)

    # --- gyanta (csak Blenderben épül: animált, nem CAD-geometria)
    mat_resin = make_material("M_resin", G["resin_color"], alpha=G["resin_alpha"], roughness=0.15)
    pot_pos = [v * MM for v in G["pot_pos"]]
    trap_pos = [v * MM for v in G["trap_pos"]]
    resin_pot = add_cylinder_bottom_origin("Gyanta a tartályban", G["pot_r"] * MM * 0.97, G["pot_h"] * MM,
                                           (pot_pos[0], pot_pos[1], pot_pos[2] + 1 * MM), mat_resin, cols["05_Gyanta"])
    lvl0 = G["pot_level"]
    key_scale(resin_pot, 1, (1, 1, lvl0))
    key_scale(resin_pot, f_in0, (1, 1, lvl0))
    key_scale(resin_pot, f_in1, (1, 1, lvl0 * 0.35))
    key_scale(resin_pot, f_end, (1, 1, lvl0 * 0.35))

    resin_trap = add_cylinder_bottom_origin("Gyanta a csapdában", G["trap_r"] * MM * 0.96, G["trap_h"] * MM,
                                            (trap_pos[0], trap_pos[1], trap_pos[2] + 1 * MM), mat_resin, cols["05_Gyanta"])
    key_scale(resin_trap, 1, (1, 1, 0.001))
    key_scale(resin_trap, int(f_in0 + F["infuse_frames"] * 0.85), (1, 1, 0.001))
    key_scale(resin_trap, f_in1, (1, 1, 0.12))
    key_scale(resin_trap, f_end, (1, 1, 0.12))

    R = G["resin_front"]
    resin_front = add_box_origin_minx("Gyantafront", (R["length"] * MM, R["width"] * MM, R["height"] * MM),
                                      R["x0"] * MM, 0, R["z_center"] * MM, mat_resin, cols["05_Gyanta"])
    key_scale(resin_front, 1, (0.001, 1, 1))
    key_scale(resin_front, f_in0, (0.001, 1, 1))
    key_scale(resin_front, f_in1, (1.0, 1, 1))
    key_scale(resin_front, f_end, (1.0, 1, 1))
    for o in (resin_front, resin_pot, resin_trap):
        smooth_keys(o)

    # --- kamera, fény, világ
    scene.frame_start, scene.frame_end = 1, f_end
    scene.render.fps = F["fps"]
    table_top = G["table_top"] * MM
    cam_data = bpy.data.cameras.new("Kamera")
    cam_data.lens = 45
    cam = bpy.data.objects.new("Kamera", cam_data)
    cols["99_Kamera_Feny"].objects.link(cam)
    cam.location = (-0.75, -1.65, table_top + 1.05)
    target = Vector((0.15, 0.05, table_top + 0.06))
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    sun_data = bpy.data.lights.new("Nap", "SUN")
    sun_data.energy = 3.0
    sun = bpy.data.objects.new("Nap", sun_data)
    cols["99_Kamera_Feny"].objects.link(sun)
    sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(-40))
    world = bpy.data.worlds.new("Vilag")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.95, 0.96, 0.97, 1)
    world.color = (0.93, 0.94, 0.95)  # Workbench háttér

    # Workbench: gyors, műszaki-illusztráció jellegű render
    scene.render.engine = "BLENDER_WORKBENCH"
    sh = scene.display.shading
    sh.light, sh.color_type = "STUDIO", "MATERIAL"
    sh.show_shadows = sh.show_cavity = sh.show_object_outline = True
    sh.cavity_type = "BOTH"
    scene.display.render_aa = "8"
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080

    # --- export: minden akció egy közös "Infuzio" NLA-sávba → egyetlen glTF-animáció
    for obj in bpy.data.objects:
        ad = obj.animation_data
        if ad and ad.action:
            track = ad.nla_tracks.new()
            track.name = "Infuzio"
            track.strips.new("Infuzio", 1, ad.action)
            ad.action = None
    os.makedirs(out_dir, exist_ok=True)
    glb = os.path.join(out_dir, "infusion.glb")
    bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", export_animations=True,
                              export_animation_mode="NLA_TRACKS", export_apply=True,
                              export_cameras=False, export_lights=False, export_yup=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out_dir, "infusion.blend"))

    info = {"frames": {k: F[k] for k in ("exploded_hold", "assemble", "assembled_hold", "infuse", "end")},
            "fps": F["fps"],
            "stack_total_display_mm": round(G["stack_top"] - G["tool_top"], 2),
            "stack_total_real_mm": round(sum(it["thickness_mm"] for it in layout["items"] if "thickness_mm" in it), 3),
            "layers": [it["name"] for it in layout["items"] if "layer_index" in it],
            "source": scene.get("source", "blender_primitives")}
    with open(os.path.join(out_dir, "build_info.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
    print("GLB:", glb)
    return info


def render_previews(out_dir, info):
    scene = bpy.context.scene
    scene.render.resolution_x, scene.render.resolution_y = 1280, 720
    fr = info["frames"]
    for label, f in {"1_robbantott": 1, "2_osszeallt": fr["assembled_hold"][0] + 2,
                     "3_infuzio_kozben": (fr["infuse"][0] + fr["infuse"][1]) // 2, "4_vege": fr["end"]}.items():
        scene.frame_set(f)
        scene.render.filepath = os.path.join(out_dir, f"preview_{label}.png")
        bpy.ops.render.render(write_still=True)


def load_params():
    with open(os.path.join(HERE, "params.json"), encoding="utf-8") as f:
        return json.load(f)


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    out = argv[argv.index("--out") + 1] if "--out" in argv else "build"
    return out, "--no-preview" not in argv


if __name__ == "__main__":
    out, previews = parse_args()
    layout = compute_layout(load_params())
    scene, cols = new_scene()
    objs = build_primitives(layout, cols)
    info = animate_and_export(layout, objs, cols, out)
    if previews:
        render_previews(out, info)
