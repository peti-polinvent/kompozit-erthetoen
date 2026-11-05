---
name: szerszamkeszites
description: Kompozit szerszám (mould/tool) készítése mintáról (plug/pattern) – anyagok, rétegrend, gyantarendszer, kompatibilitás, utókikeményítés, Tg, perem infúzióhoz, gyakori hibák (lakk felhólyagosodása), források. Használd, ha szerszámkészítésről, gélgyantáról, leválasztóról, mintaelőkészítésről kérdeznek vagy a szerszam.html oldalt bővíted.
---

# Szerszámkészítés – tudásbázis (Kompozit érthetően)

Oldal: `szerszam.html`. A számok tipikus értékek; konkrét terméknél **a gyártói adatlap (TDS) az irányadó**. Ha források eltérnek, a biztonságosabbat add meg.

## Alapszabályok
- Egy gyártó egy rendszere (alapozó → gélgyanta → csatoló → gyanta → leválasztó). Minden új párosításnál próbafolt.
- Minden réteg a gyártó szerint kikeményedve (nem „tapintásra száraz”), vagy a recoat-ablakon belül, mielőtt a következő ráér.
- Szerszám Tg ≥ termék legmagasabb hőmérséklete + 15–20 °C. Utókikeményítés a termékhőmérséklet fölé (120 °C termék → 130–135 °C).
- Szerszám vastagabb a terméknél, szimmetrikus, egyenletes vastagságú, kerettel.

## Folyamat és számok
- Minta: MDF / tooling board / gipsz / 3D nyomat. Kiemelés ≥ 1–2° (mély/textúra ≥ 3°), belső R ≥ 2–3 mm (szén 3–5), perem 50–100 mm (zsák), 100–150 mm (infúzió), sík (≤ ~0,5 mm/m cél).
- Lezárás: epoxi bevonat vagy 2K alapozó minden oldalon. 3D nyomat: P240 → 2× epoxi bevonat 300–500 g/m², 2. réteg B-állapotban (EC: XCR).
- Felület: vizes csiszolás P400/800 → P1200–P2000, paszta, polír.
- Leválasztó új mintán: félig permanens ≥ 6 réteg, 15 perc köztük, utolsó után ≥ 1 h (EC CR1); vagy karnauba 5–8 réteg + PVA. Szilikon tilos.
- Gélgyanta: 2 × 0,4–0,5 mm, össz. 0,8–1,0 mm; 1 kg/m² ≈ 1 mm (epoxi). <0,5 mm: krokodilbőr; >1,2 mm: repedés. B-állapot: kesztyűs ujj nyomot hagy, nem ragad.
- Csatoló réteg: vékony nedves gélgyanta/gyanta + finom szövet/filc, a B-ablakon belül.
- Tömeg: menetenként max 2–3 mm (2–3 réteg), hőcsúcs kivárása. Vastagság: üveg-epoxi 6–10 mm, szén-epoxi 4–6 mm, PE-CSM 8–12 mm, paszta ~10 mm.
- EC magas hőm. szén szerszám (infúzió, EL160): 1× 210 g twill, 300 g szén filc sarkokba, 8× 450 g twill 0/90, 1× 210 → ~5 mm.
- Kikeményítés a mintán: epoxi 24 h 20–25 °C vagy jobb 12 h 40 °C (csak szobahőn rideg). Utókikeményítés a mintáról levéve, alátámasztva, lépcsőkben (10–20 °C/h, 1–2 h tartás), lassú hűtés.
- Bejáratás: első 3–5 darab előtt mindig friss leválasztó; félig permanensnél később 5–10 levételenként.

## Ellenőrzött termékek (Easy Composites, ships to HU; EU bolt: easycomposites.eu)
- EG60 Epoxy Tooling Gelcoat – https://www.easycomposites.co.uk/epoxy-tooling-gel-coat – keverés 100:10, pot life ~48 min, max üzemi 60 °C (Tg 50–60 °C), háttér: EMP60. Min. 15 °C, inkább 20 °C+.
- EG160 High Temp Epoxy Tooling Gelcoat – https://www.easycomposites.co.uk/eg160-high-temperature-epoxy-tooling-gel-coat – Tg onset 160 °C, kézi laminált szerszám max 125 °C, pot life 30 min, háttér: EMP160 / EL160 (EL160 nedves laminálásnál nem kell csatoló réteg), TDS: 3 h 135 °C tartás az utókikeményítésben; nagy sík szerszámnál a gélgyanta CTE-eltérése vetemíthet.
- Uni-Mould (UG1 gél, UC1 csatoló, UT1 szerszámgyanta, MEKP): vinilészter alapú, epoxi termékekhez/infúzióhoz – https://easycomposites.eu/learning/uni-mould-tooling-system-user-guide
- Csak útmutatókban látott (termékoldal nem ellenőrizve): EMP60, EMP160, EL160, CR1, S120, XCR, MC1.
- Magyar szállítót nem sikerült ellenőrizni.

## Kompatibilitás
- 1K lakk (nitro/akril/spray) poliészter/VE gél alá: NEM (sztirol/oldószer oldja → hólyag, ránc). Epoxi gél alá: inkább ne.
- 2K PU / 2K epoxi / PE töltő, teljesen kikeményedve, csiszolva: igen (PE gélnél próbafolt).
- Nyers PLA, XPS/EPS, MDF: lezárás nélkül nem. XPS/EPS-t a sztirol feloldja.
- CSM: poros/emulziós kötésű CSM epoxival NEM (kötőanyag csak sztirolban oldódik) – csak „epoxi-kompatibilis” CSM vagy szövet.
- Nem kikeményedett epoxira poliészter: nem (amin gátol). Epoxi gél mögé poliészter: nem.
- Szilikonos leválasztó: soha. Prepreg 120 °C: hőálló félig permanens.

## Lakk-hólyagosodás (a felhasználó valós hibája)
Ok: 1K lakk fizikailag szárad, újraoldható; a következő réteg sztirolja/oldószere megduzzasztja; bezárt oldószer hólyagot fúj; 2K-nál a recoat-ablakon kívüli félig kötött réteg ráncosodik. Megelőzés: 2K rendszer, teljes kikeményedés, recoat-ablak, egy gyártó, próbafolt (24 h, karc).

## Egyéb csapdák
Krokodilbőr (vékony gél), előleválás (exoterm, rossz viasz), ráragadás, szálátütés, légzárvány a sarokban, gél túlkeményedése a csatoló előtt, vetemedés (aszimmetria, korai bontás, alátámasztatlan hőkezelés, mintán végzett utókikeményítés CTE-eltéréssel), túl alacsony Tg, vákuumszivárgás (keskeny/porózus perem → vákuummal tömörített szerszám, üres vákuumpróba: néhány mbar/10 perc), csorba élek, halszem (szilikon), puha gél (arány, <15 °C), üveg szerszám szén termékhez hőn (CTE).

## Források
- EC hand-laminating HT mould: https://www.easycomposites.co.uk/learning/hand-laminating-a-high-temperature-epoxy-mould
- EC resin infusion of HT tooling: https://easycomposites.eu/learning/resin-infusion-of-high-temperature-tooling
- EC mould from 3D print: https://easycomposites.co.uk/making-a-composites-mould-from-a-3d-print
- Gurit T-Gel 130-1 (40 °C közbenső kikeményítés bontás előtt): https://pdf.nauticexpo.com/pdf/gurit/t-gel-130-1/27794-106821.html
- EC PDF adatlapok (media.easycomposites.co.uk) WebFetch-csel binárisan jönnek, nem olvashatók; a termékoldal kérdés-válasz része használható.

## AI skill keresés (2026-11)
Szerszámkészítő skill nem található. A claudskills.com „composite” skillje a Composite tervezési mintáról szól (szoftver), nem releváns; nem telepítettük.
