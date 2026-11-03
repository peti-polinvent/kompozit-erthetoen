# Kompozit érthetően – vákuuminfúzió 3D-ben

Egyetlen történet: hogyan készül egy egyszerű kompozit panel vákuuminfúzióval?
Paraméterezhető CAD-modell (Fusion 360) + animáció/render (Blender) + narrált
videó + weboldal. Készült a Polinvent belső „AI Kihívás” keretében
(2026. november 2–6.).

**Élő oldal:** https://peti-polinvent.github.io/kompozit-erthetoen/ · **Repó:** https://github.com/peti-polinvent/kompozit-erthetoen

## Hogyan áll össze? (hibrid munkafolyamat)

```
blender/params.json ──► blender/infusion_layout.py  (geometria mm-ben, eszközfüggetlen)
                                 │
                 ┌───────────────┴────────────────┐
                 ▼                                ▼
   fusion/KompozitInfuzio/            blender/build_infusion.py
   KompozitInfuzio.py (Fusion 360)    (Blender, primitívekből – Fusion nélkül is fut)
   → fusion/export/*.obj, .f3d, .step            │
                 │                                │
                 ▼                                │
   blender/animate_fusion_export.py ◄─────────────┘  (közös: animáció, kamera, export)
   → build/infusion.glb  → assets/infusion.glb → index.html (model-viewer)
   → build/infusion.blend, preview_*.png → videó
```

- **Fusion 360** a tervezőeszköz: a szkript komponensekbe rendezett, elnevezett,
  színezett testeket épít a paraméterfájlból, és testenként exportál.
- **Blender** az animációs/render-eszköz: robbantott rétegrend, összeállás,
  gyantafront, gyantaszintek; GLB a webre, képsor a videóhoz.
- A két eszköz **ugyanazt a geometriát** használja (`infusion_layout.py`), így a
  Fusion-export és a Blender-primitív verzió felcserélhető.

## Mappaszerkezet

| Mappa / fájl | Mi ez? |
|---|---|
| `index.html` | A weboldal (mobilbarát, `model-viewer` 3D nézővel, videóval, naplóval) |
| `assets/` | Weboldal eszközei: `infusion.glb`, videó, képek, helyben tárolt JS-könyvtárak |
| `blender/params.json` | **A rétegrend és a geometria paraméterei** – ezt szerkeszd |
| `blender/infusion_layout.py` | Eszközfüggetlen geometria: params → testek listája (mm) |
| `blender/build_infusion.py` | Blender: primitív-építő + közös animáció/export |
| `blender/animate_fusion_export.py` | Blender: Fusion-export (OBJ) beolvasása + animáció/export |
| `blender/mock_fusion_export.py` | Teszt: Fusion-szerű export Blenderből (a lánc próbájához) |
| `fusion/KompozitInfuzio/` | Fusion 360 szkript (+ manifest) |
| `fusion/export/` | A Fusion-szkript kimenete: OBJ-k, manifest.json, f3d, step |
| `build/` | Generált kimenetek: `infusion.blend`, `infusion.glb`, előnézeti képek |
| `video/` | Narrációs szkript, feliratok, render- és vágószkriptek |
| `NAPLO.md` | Tanulási napló: eszközök, promptok, elakadások, megoldások |

## Futtatás

**Fusion 360** (Personal is jó): Utilities → Add-Ins → Scripts and Add-Ins →
Scripts → „+” → válaszd a `fusion/KompozitInfuzio` mappát → Run. Új dokumentum
nyílik, az export a `fusion/export/` mappába kerül.

**Blender** (4.2+; a Fusion-export animálása):

```bash
pip install bpy==4.5.15          # Python 3.11 kell hozzá (vagy Blender saját Pythonja)
python blender/animate_fusion_export.py --export fusion/export --out build
#   ha az oldalára dőlve jön be a modell:  --yup
# Fusion nélkül, csak primitívekből:
python blender/build_infusion.py --out build
```

A `params.json`-ban cserélhető a panel mérete, a rétegek (név, típus, valós és
megjelenített vastagság, szín), a segédanyagok, a berendezések és az animáció
időzítése. Rétegtípusok: `release`, `gelcoat`, `glass`, `carbon`, `peelply`,
`flowmesh`, `bag`.

## Következő lépések (a kihíváson túl)

- A sewerbot Compact kompozit dobjának geometriája és rétegrendje ugyanebből a
  paraméterfájl-logikából (hengeres szerszám, rétegek körbetekerve).
- Gyantaáramlás-szimuláció (Darcy-törvény alapú kitöltésiidő-becslés) a
  paraméterekből.
