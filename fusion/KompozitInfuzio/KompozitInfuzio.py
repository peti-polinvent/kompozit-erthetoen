# -*- coding: utf-8 -*-
"""
KompozitInfuzio – Fusion 360 szkript
=====================================

A blender/params.json + blender/infusion_layout.py alapján felépíti a
vákuuminfúziós összeállítást Fusion 360-ban (asztal, szerszám, rétegrend,
tömítőszalag, spirálcsövek, gyantatartály, gyantacsapda, szivattyú, csövek),
komponensekbe rendezve, elnevezett testekkel és színekkel, majd exportál:

    fusion/export/<key>.obj      – minden test külön (Blender animációhoz)
    fusion/export/manifest.json  – testek listája (kulcs, név, típus, szín…)
    fusion/export/infusion.f3d   – Fusion archívum
    fusion/export/infusion.step  – STEP (ha a licenc engedi; Personal: lehet, hogy nem)

Telepítés / futtatás Fusionban:
  1. Utilities (Segédprogramok) fül → Add-Ins → Scripts and Add-Ins (Shift+S)
  2. Scripts fül → zöld "+" a "My Scripts" mellett → válaszd ki ezt a mappát:
         <projekt>/fusion/KompozitInfuzio
  3. Jelöld ki a "KompozitInfuzio" szkriptet → Run
  4. Új dokumentum nyílik a modellel; a végén üzenetablak mutatja, mi exportálódott.

A szkript DIRECT (nem parametrikus) tervezési módban dolgozik és ideiglenes
B-Rep testeket (TemporaryBRepManager) tesz a komponensekbe: ez a legrobusztusabb
út, ha a kódot nem interaktívan fejlesztjük. A paraméterezés a params.json-ban
van – módosítás után egyszerűen újra kell futtatni a szkriptet.

Fusion API jegyzet: a belső hosszegység CENTIMÉTER, ezért minden mm-es érték
0,1-del szorzódik.
"""

import adsk.core
import adsk.fusion
import traceback
import json
import os
import sys
import math

MM = 0.1  # mm → cm (a Fusion API belső egysége a cm)


def _paths():
    here = os.path.dirname(os.path.abspath(__file__))
    project = os.path.normpath(os.path.join(here, "..", ".."))
    return dict(
        here=here,
        blender_dir=os.path.join(project, "blender"),
        params=os.path.join(project, "blender", "params.json"),
        export=os.path.join(project, "fusion", "export"),
    )


def _hex_to_color(h, alpha=1.0):
    h = h.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return adsk.core.Color.create(r, g, b, int(round(alpha * 255)))


def _p(v):
    """mm-es [x,y,z] → Point3D (cm)"""
    return adsk.core.Point3D.create(v[0] * MM, v[1] * MM, v[2] * MM)


class Builder:
    def __init__(self, app, design):
        self.app = app
        self.ui = app.userInterface
        self.design = design
        self.root = design.rootComponent
        self.tbm = adsk.fusion.TemporaryBRepManager.get()
        self.components = {}
        self.warnings = []
        self._appearance_cache = {}
        self._base_appearance = self._find_base_appearance()

    # ---- komponensek -------------------------------------------------------
    def component(self, name):
        if name in self.components:
            return self.components[name]
        occ = self.root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        occ.component.name = name
        self.components[name] = occ.component
        return occ.component

    # ---- megjelenés ----------------------------------------------------------
    def _find_base_appearance(self):
        """Egy egyszínű műanyag-megjelenés a könyvtárból, amit lemásolunk és átszínezünk."""
        try:
            for lib in self.app.materialLibraries:
                if "Appearance" not in lib.name:
                    continue
                for cand in ("Plastic - Matte (Yellow)", "Plastic - Matte (White)",
                             "Paint - Enamel Glossy (Yellow)", "Plastic - Glossy (Yellow)"):
                    ap = lib.appearances.itemByName(cand)
                    if ap:
                        return ap
                # bármi, aminek a nevében "Plastic" van
                for i in range(lib.appearances.count):
                    ap = lib.appearances.item(i)
                    if "Plastic" in ap.name:
                        return ap
        except Exception:
            self.warnings.append("Megjelenés-könyvtár nem érhető el: " + traceback.format_exc(limit=1))
        return None

    def appearance(self, key, color_hex, alpha):
        if key in self._appearance_cache:
            return self._appearance_cache[key]
        ap = None
        if self._base_appearance:
            try:
                ap = self.design.appearances.addByCopy(self._base_appearance, "KI_" + key)
                for i in range(ap.appearanceProperties.count):
                    prop = ap.appearanceProperties.item(i)
                    if prop.objectType == adsk.core.ColorProperty.classType():
                        cp = adsk.core.ColorProperty.cast(prop)
                        if cp.hasConnectedTexture:
                            continue
                        cp.value = _hex_to_color(color_hex)
                        break
            except Exception:
                self.warnings.append("Szín nem állítható (%s): %s" % (key, traceback.format_exc(limit=1)))
                ap = None
        self._appearance_cache[key] = ap
        return ap

    # ---- testek ----------------------------------------------------------------
    def add_body(self, comp, tmp_body, item):
        """tmp_body: TemporaryBRep (bekerül a komponensbe) VAGY már a komponensben
        lévő BRepBody (pl. sweep eredménye) – mindkettőt elnevezi és színezi."""
        if isinstance(tmp_body, adsk.fusion.BRepBody) and tmp_body.parentComponent is not None:
            body = tmp_body
        else:
            body = comp.bRepBodies.add(tmp_body)
        body.name = item["name"]
        ap = self.appearance(item["key"], item["color"], item.get("alpha", 1.0))
        if ap:
            try:
                body.appearance = ap
                if item.get("alpha", 1.0) < 1.0:
                    body.opacity = max(0.15, float(item["alpha"]))
            except Exception:
                self.warnings.append("Megjelenés nem alkalmazható: " + item["key"])
        return body

    def box(self, item):
        s, c = item["size_mm"], item["center_mm"]
        dl = item.get("dir_len", [1, 0, 0])
        dw = item.get("dir_wid", [0, 1, 0])
        obb = adsk.core.OrientedBoundingBox3D.create(
            _p(c), adsk.core.Vector3D.create(*dl), adsk.core.Vector3D.create(*dw),
            s[0] * MM, s[1] * MM, s[2] * MM)
        return self.tbm.createBox(obb)

    def cylinder(self, p1, p2, radius_mm):
        return self.tbm.createCylinderOrCone(_p(p1), radius_mm * MM, _p(p2), radius_mm * MM)

    def tube_sweep(self, comp, item):
        """Ívelt cső: 3D illesztett spline a pontokon át + kör profil + SWEEP.
        Ez a "valódi" CAD-megoldás; a szögletes henger+gömb lánc csak tartalék."""
        pts = item["points_mm"]
        r = item["radius_mm"] * MM
        # 1) pálya: 3D-s vázlat az XY síkon, illesztett spline a modell-koordinátákon át
        sk_path = comp.sketches.add(self.root.xYConstructionPlane)
        sk_path.name = "Palya_" + item["key"]
        coll = adsk.core.ObjectCollection.create()
        for p in pts:
            coll.add(sk_path.modelToSketchSpace(_p(p)))
        spline = sk_path.sketchCurves.sketchFittedSplines.add(coll)
        path = comp.features.createPath(spline, False)
        # 2) profil: kör a pálya kezdőpontjára merőleges síkon
        pin = comp.constructionPlanes.createInput()
        pin.setByDistanceOnPath(path, adsk.core.ValueInput.createByReal(0.0))
        plane = comp.constructionPlanes.add(pin)
        plane.name = "Profil_" + item["key"]
        sk_prof = comp.sketches.add(plane)
        sk_prof.name = "Profil_" + item["key"]
        center = sk_prof.modelToSketchSpace(_p(pts[0]))
        sk_prof.sketchCurves.sketchCircles.addByCenterRadius(center, r)
        prof = sk_prof.profiles.item(0)
        # 3) sweep
        sin = comp.features.sweepFeatures.createInput(
            prof, path, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        sin.orientation = adsk.fusion.SweepOrientationTypes.PerpendicularOrientationType
        sweep = comp.features.sweepFeatures.add(sin)
        body = sweep.bodies.item(0)
        sk_path.isVisible = False
        sk_prof.isVisible = False
        plane.isLightBulbOn = False
        return body

    def tube(self, item):
        """Tartalék: töröttvonal mentén hengerszakaszok + gömbök a töréspontokban."""
        pts = item["points_mm"]
        r = item["radius_mm"]
        result = None
        for a, b in zip(pts[:-1], pts[1:]):
            seg = self.cylinder(a, b, r)
            result = seg if result is None else self._union(result, seg)
        for p in pts[1:-1]:
            sph = self.tbm.createSphere(_p(p), r * MM)
            result = self._union(result, sph)
        return result

    def _union(self, a, b):
        ok = self.tbm.booleanOperation(a, b, adsk.fusion.BooleanTypes.UnionBooleanType)
        if not ok:
            self.warnings.append("Boolean unió sikertelen egy csőszakasznál")
        return a

    def build(self, layout):
        bodies = []
        for it in layout["items"]:
            comp = self.component(it["collection"])
            if it["kind"] == "box":
                tmp = self.box(it)
            elif it["kind"] == "cyl":
                tmp = self.cylinder(it["p1_mm"], it["p2_mm"], it["radius_mm"])
            else:
                try:
                    tmp = self.tube_sweep(comp, it)
                except Exception:
                    self.warnings.append("Sweep sikertelen (%s), szögletes tartalék: %s"
                                         % (it["key"], traceback.format_exc(limit=1).strip().splitlines()[-1]))
                    tmp = self.tube(it)
            body = self.add_body(comp, tmp, it)
            bodies.append((it, body))
        return bodies


def export_all(design, bodies, layout, export_dir, warnings):
    os.makedirs(export_dir, exist_ok=True)
    em = design.exportManager
    manifest = {"units": "cm", "up_axis": "Z", "items": [], "notes": []}
    for it, body in bodies:
        entry = {k: it[k] for k in it if k not in ("size_mm", "center_mm", "p1_mm", "p2_mm", "points_mm")}
        path_obj = os.path.join(export_dir, it["key"] + ".obj")
        try:
            opts = em.createOBJExportOptions(body, path_obj)
            em.execute(opts)
            entry["file"] = it["key"] + ".obj"
        except Exception:
            # régebbi Fusion: nincs OBJ export → STL
            path_stl = os.path.join(export_dir, it["key"] + ".stl")
            opts = em.createSTLExportOptions(body, path_stl)
            opts.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
            opts.isBinaryFormat = True
            em.execute(opts)
            entry["file"] = it["key"] + ".stl"
        manifest["items"].append(entry)

    try:
        em.execute(em.createFusionArchiveExportOptions(os.path.join(export_dir, "infusion.f3d")))
        manifest["notes"].append("f3d exportálva")
    except Exception:
        warnings.append("F3D export sikertelen")
    try:
        em.execute(em.createSTEPExportOptions(os.path.join(export_dir, "infusion.step")))
        manifest["notes"].append("STEP exportálva")
    except Exception:
        warnings.append("STEP export nem sikerült (Personal licenc alatt ez várható) – az OBJ/F3D elég a továbbiakhoz")

    manifest["frames"] = layout["frames"]
    manifest["geo"] = layout["geo"]
    manifest["warnings"] = warnings
    with open(os.path.join(export_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    return manifest


def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        paths = _paths()

        if paths["blender_dir"] not in sys.path:
            sys.path.insert(0, paths["blender_dir"])
        import importlib
        import infusion_layout
        importlib.reload(infusion_layout)   # újrafuttatásnál a friss modult lássuk

        with open(paths["params"], encoding="utf-8") as f:
            params = json.load(f)
        layout = infusion_layout.compute_layout(params)

        doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        design.designType = adsk.fusion.DesignTypes.DirectDesignType
        try:
            design.fusionUnitsManager.distanceDisplayUnits = adsk.fusion.DistanceUnits.MillimeterDistanceUnits
        except Exception:
            pass

        b = Builder(app, design)
        bodies = b.build(layout)
        app.activeViewport.fit()
        manifest = export_all(design, bodies, layout, paths["export"], b.warnings)

        msg = ("Kész: %d test, %d komponens.\nExport: %s\n%s" % (
            len(bodies), len(b.components), paths["export"], "\n".join(manifest["notes"])))
        if b.warnings:
            msg += "\n\nFigyelmeztetések:\n- " + "\n- ".join(b.warnings)
        ui.messageBox(msg, "KompozitInfuzio")
    except Exception:
        if ui:
            ui.messageBox("Hiba:\n{}".format(traceback.format_exc()), "KompozitInfuzio")
