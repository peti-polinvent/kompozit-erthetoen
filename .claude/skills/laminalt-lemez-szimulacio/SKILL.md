---
name: laminalt-lemez-szimulacio
description: A weboldal rétegrend-építő és lemez-szimulátora (assets/sim/) – anyagadatbázis, lemezelmélet (CLT + FSDT Navier), tönkremenetel (Tsai-Wu), a számítómotor API-ja és a magyarázatok szabályai. Használd, ha a szimulátor kódjához, adataihoz vagy szövegeihez nyúlsz.
---

# Rétegrend-építő és lemez-szimulátor

Cél: laikus látogató max. **20 rétegből** rétegrendet épít egy 400 × 300 mm-es, vákuuminfúzióval
készült síklaphoz, terhelést ad rá, és látja (1) a lehajlást animálva, (2) mikor reped meg az első
réteg (first-ply failure), (3) mekkora terhelés kell adott lehajláshoz, (4) közérthető magyarázatot,
mi miért változott. Mérnöki becslés, nem méretezés – ezt az oldal mindig kiírja.

Szakmai háttér a telepített (átvizsgált, Apache 2.0) skillekben: `aero-laminate-bending-stiffness`
(ABD), `aero-laminate-first-ply-failure`, `aero-failure-criteria`, `aero-sandwich-panels`,
`aero-unidirectional-lamina-micromechanics`. A Python-szkriptjeiket NEM futtatjuk (külső kód);
csak a leírásaikat használjuk tudásanyagként.

## Modell

- **Rétegek** alulról felfelé (z = −h/2 … +h/2), szög a lap x tengelyéhez (x = 400 mm-es oldal).
- **CLT**: Q (redukált merevség) → Q̄(θ) → A, B, D (N/mm, N, N·mm). Transzverzális nyírás:
  A44, A55 = (5/6)·Σ G23/G13 · t (forgatva).
- **Lemez**: négy élén csuklósan megtámasztott, Navier-sor, **FSDT (Mindlin–Reissner)**
  speciálisan ortotrop alakban (D11, D22, D12, D66, A44, A55; tagonként 3×3 egyenletrendszer).
  D16/D26-ot a megoldás elhanyagolja – ha |D16|/D11 vagy |D26|/D22 > 0,1, figyelmeztetés.
  Aszimmetrikus rétegrendnél (B ≠ 0) redukált hajlítómerevség D* = D − B·A⁻¹·B, és figyelmeztetés
  („a lap vetemedni fog kikeményedéskor”). Páratlan m, n tagok; alapértelmezés 31×31 tag.
- **Terhelés**: (a) egyenletes nyomás q [kPa]; (b) középen folt-teher P [N] c×d = 60×60 mm-es
  felületen (pl. ráálló ember: m·9,81). Foltteher-együttható:
  Q_mn = 16P/(π² m n c d) · sin(mπ/2) sin(nπ/2) sin(mπc/2a) sin(nπd/2b).
- **Feszültség**: M, (Q) a lap 21×21 pontos rácsán a sorból → κ = D*⁻¹·M (teljes D, 16/26-tal) →
  rétegenként alsó/felső szálban ε = z·κ → anyagi koordináták σ1, σ2, τ12.
- **Tönkremenetel**: Tsai-Wu, F12 = −0,5/√(Xt·Xc·Yt·Yc). Lineáris → terhelési szorzó λ a
  F_i(λσ)_i + F_ij(λσ)_i(λσ)_j = 1 pozitív gyökéből; az első réteg tönkremeneteli terhelése = λ·P.
  Mód (a legnagyobb arányú tag alapján): „szálszakadás (húzás)”, „szálnyomás”,
  „mátrixrepedés (keresztirány)”, „nyírás”. Maganyagnál: a mag nyírófeszültsége
  τ ≈ Q/(h_mag + (h_felső + h_alsó)/2) a Q-maximum helyén, határ S_mag; a kisebbik λ dönt.
- **Nagy lehajlás**: ha w_max > 0,5·h, figyelmeztetés: a valóságban a membránhatás merevít,
  a lineáris modell túlbecsüli a lehajlást (biztonságos irány).
- **Ellenőrzés**: izotróp egyrétegű négyzetlapnál w_max = 0,00406·q·a⁴/D (vékony lemez);
  független Python-referenciával (numpy) egyezés ≤ 0,5 %.

## Anyagok (infúziós epoxival, tipikus értékek; GPa, MPa, mm)

| id | név | fajta | E1 | E2 | G12 | ν12 | G13 | G23 | Xt | Xc | Yt | Yc | S | t/réteg | g/m² (szál) | ρ g/cm³ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gl-woven | Üvegszövet 300 (vászon/köper) | szövet | 21 | 21 | 3.8 | 0.13 | 3.0 | 3.0 | 350 | 300 | 350 | 300 | 55 | 0.23 | 300 | 1.90 |
| gl-ud | UD üveg 300 | UD | 40 | 10 | 3.8 | 0.28 | 3.8 | 3.4 | 900 | 600 | 35 | 120 | 55 | 0.23 | 300 | 1.90 |
| gl-biax | Üveg biax ±45° 600 (varrott) | biax → 2 UD altréteg (+45/−45 a lerakási szöghöz képest), mindkettő gl-ud, t = 0.23 | | | | | | | | | | | | 0.46 | 600 | 1.90 |
| gl-csm | Üvegpaplan (CSM) 450 | izotróp | 7.5 | 7.5 | 2.8 | 0.32 | 2.8 | 2.8 | 95 | 140 | 95 | 140 | 65 | 0.60 | 450 | 1.50 |
| cf-woven | Szénszövet 200 (köper) | szövet | 55 | 55 | 4.0 | 0.05 | 3.5 | 3.5 | 600 | 500 | 600 | 500 | 80 | 0.22 | 200 | 1.50 |
| cf-ud | UD szén 300 | UD | 120 | 8 | 4.2 | 0.30 | 4.2 | 3.0 | 1800 | 1100 | 45 | 180 | 70 | 0.30 | 300 | 1.55 |
| ar-woven | Aramid (kevlár) szövet 170 | szövet | 25 | 25 | 2.2 | 0.10 | 2.0 | 2.0 | 450 | 130 | 450 | 130 | 45 | 0.25 | 170 | 1.35 |
| core-pet | PET hab maganyag (5/10/20 mm) | izotróp mag | 0.08 | 0.08 | 0.025 | 0.30 | 0.025 | 0.025 | 1.8 | 1.3 | 1.8 | 1.3 | 0.9 | 5/10/20 | – | 0.10 |

Megjegyzések a magyarázatokhoz: az aramid húzásra kiváló, **nyomásra gyenge** (Xc ≪ Xt);
a paplan minden irányban egyforma, de gyengébb, és epoxihoz porkötésű változat kell (az emulziós
kötőanyagot csak a sztirol oldja); UD csak szálirányban erős; ±45° a nyírást és a csavarást viszi;
a mag a hajlítómerevséget a két héj távolságának nagyjából **négyzetével** növeli (szendvicshatás,
D ≈ E_f·t_f·d²/2) kis tömegnövekedéssel – a köbös szabály csak tömör laminátra igaz.
Konzisztencia: t ≈ g/m² / (ρ_szál·V_f), pl. üveg 300 g/m² / (2,55 g/cm³ · 0,51) ≈ 0,23 mm.

## API – `assets/sim/clt.js` (ES-modul, DOM nélkül, böngészőben és Node-ban is fut)

```js
export const MATERIALS;            // { [id]: {id, name, kind:'woven'|'ud'|'biax'|'mat'|'core', E1,E2,G12,nu12,G13,G23 (GPa),
                                    //   Xt,Xc,Yt,Yc,S (MPa), t (mm), thicknessOptions?:[5,10,20], areal (g/m²), rho (g/cm³), color, note } }
export const DEFAULT_PANEL = { a: 400, b: 300 };      // mm
export function analyze(plies, opts) // plies: [{ mat:'gl-woven', angle:0, t?:10 }] alulról felfelé (t csak magnál)
// opts: { a, b, load: {type:'pressure', q /*kPa*/} | {type:'patch', P /*N*/, c:60, d:60}, terms:31, grid:21 }
// visszaad: {
//   h /*mm*/, massPerArea /*kg/m²*/, panelMass /*kg*/, A, B, D /*3×3*/, symmetric, warnings: [string – magyarul],
//   inPlane: { Ex, Ey, Gxy, nuxy } /*GPa*/, flexural: { Efx, Efy } /*GPa*/,
//   wMax /*mm, pozitív lefelé*/, w: { nx, ny, values: Float64Array /*mm, sor-folytonos, x gyors*/ },
//   fpf: { factor /*λ*/, load /*a bemenettel azonos egységben*/, plyIndex, mode, x, y /*mm*/, criterion:'Tsai-Wu' },
//   plyResults: [{ index, mat, angle, zBot, zTop, maxFailureIndex }] }
export function loadForDeflection(plies, opts, wTarget /*mm*/) // → terhelés (az opts.load egységében)
```

## Magyarázat-szabályok (felület)

- Egy mondat = egy hatás, mindig összehasonlítva valamivel („kétszer olyan merev, mint…”).
  Referencia: a projekt saját lapja, 4 × gl-woven [0/45/45/0] (a videó és a 3D modell rétegrendje).
- Számok kerekítve, mértékegységgel; terhelés kg-ban is („kb. 85 kg-os ember ráállva”).
- Az első rétegtörés ≠ teljes törés: „itt jelenik meg az első repedés; a lap ennél
  általában többet bír, de ez már károsodás”.
- Mindig látszik: „Egyszerűsített mérnöki becslés (klasszikus rétegelmélet), nem méretezés.”
