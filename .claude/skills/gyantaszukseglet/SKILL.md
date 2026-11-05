---
name: gyantaszukseglet
description: Gyantaszükséglet (resin quantity) becslése vákuuminfúzióhoz, vákuumzsákos és kézi laminálásra – szövet, CSM, Soric-típusú magpaplan, PVC/PET hab (sima, hornyolt, perforált, bevágott), peel ply, infúziós háló, cső. Használd, ha a kalkulátort (assets/calc/resin.js) módosítod, alapértéket cserélsz, vagy valaki megkérdezi, mennyi gyantát keverjen.
---

# Gyantaszükséglet – modell, alapértékek, források

Kód: `assets/calc/resin.js` (`compute`, `rowResin`, `DEF`). Teszt: `node tests/calc/resin_check.mjs`
(18 kézzel számolt eset). Demó: `tests/calc/demo.html`.

## Modell

1. **Szövet és paplan** (rétegenként):
   `gyanta = W × (ρr / ρf) × (1 − Vf) / Vf` [kg/m²], ahol W a felületi tömeg kg/m²-ben.
   Ez azonos a `W × (1 − Wf) / Wf` alakkal, ahol `Wf = Vf·ρf / (Vf·ρf + (1−Vf)·ρr)`.
   A Vf az eljárástól (infúzió / vákuumzsák / kézi) és attól függ, hogy szövet vagy CSM.
   Az eredményben a szövetek együttes Vf és Wf értéke is látszik.
2. **Soric-típusú magpaplan**: a Lantor adatlap kg/m² értéke a névleges vastagságnál,
   közte lineáris interpoláció, a táblán kívül arányos (kg/m²/mm). LRC: 0,35 kg/m²/mm.
3. **Habmag**: `2 × felszíni felvétel/oldal + gyanta a hornyokban, furatokban, vágásokban`.
   - horony (keresztirányú, oldalanként): `2 · w · d / pitch` [mm = dm³/m² ÷ 1000 → m³/m²]
   - furat: `π (D/2)² · t / pitch²`
   - átvágott, hálóra ragasztott (grid/scrim): `2 · kerf · t / pitch`
   - térfogat × ρr. A horonykereszteződéseket kétszer számolja (óvatos, ~1 %).
4. **Segédanyag**: peel ply és infúziós háló: kg/m² × felület × rétegszám; cső: hossz × π(ID/2)² × ρr.
5. **Összesen** = (laminát + mag + segédanyag + cső) × (1 + ráhagyás %) + edényben/tömlőben maradó gyanta.
   Szétosztás tömegarány szerint: edző = összes × B/(A+B). Liter = kg / ρr.
   Laminát tömege = szál + beépült gyanta + mag száraz tömege + mag gyantája (segédanyag nélkül);
   m²-re a legnagyobb sor felületével osztva.

## Alapértékek (óvatos = inkább több gyanta)

| Érték | Alap | Tartomány | Források |
| --- | --- | --- | --- |
| Vf szövet, infúzió | 48 % | 45–55 % | Easy Composites kezdő infúziós útmutató: gyanta = rétegtömeg / 1,5 (Wf 60 % → szénnél Vf ≈ 49 %); Gurit Guide to Composites (vákuumos eljárások 50–60 % körül) |
| Vf szövet, vákuumzsák | 38 % | 35–45 % | Gurit Guide; an-cor.com laminálási glosszárium (vákuumzsák növeli a szálarányt) |
| Vf szövet, kézi | 30 % | 25–40 % | Gurit Guide (kézi laminálás 30–40 %); szakmai jegyzetek 30–50 % – az alsó felet választottuk |
| Vf CSM infúzió / zsák / kézi | 30 / 25 / 17,5 % | 28–35 / 20–30 / 15–20 % | Saertex „SAERcore Resin Consumption” flyer 06/2025 (CSM ref.: kézi 17,5 %, infúzió 33 %); közismert CSM üveg:gyanta 1:2–1:2,5 (Wf 29–33 % ≈ Vf 16–18 %). A vákuumzsák-érték interpoláció (1 forrás). |
| Szálsűrűség üveg / szén / aramid | 2,56 / 1,76 / 1,44 g/cm³ | 2,54–2,60 / 1,75–1,95 / 1,44–1,45 | Gurit Guide; kompozit sűrűségtábla (E-üveg 2,56, szén 1,75–1,95, Kevlar 49 1,45). Szénnél az alsó érték óvatos. |
| Bazalt | 2,65 g/cm³ | 2,6–2,8 | **Csak általános szakirodalmi érték, ebben a körben 2 forrásból nem ellenőrzött.** |
| Gyanta (epoxi) sűrűség | 1,15 g/cm³ | 1,10–1,20 | Gurit Guide; kompozit sűrűségtábla (epoxi 1,1–1,4). Saját termék adatlapja felülírja. |
| Soric XF felvétel | 1,5→1,0; 2→1,0; 3→1,4; 4→1,9; 5→2,4; 6→2,8; 10→5,4 kg/m² | ≈ 0,47–0,67 kg/m²/mm | Lantor Soric XF TDS v2.2 (2020) és régebbi Lantor lap (Composite Envisions „Model 965”), ACP Composites termékoldal. Poliészterrel mérve; epoxinál hasonló sűrűség. |
| Soric TF | 1,5→0,8; 2→1,0; 3→1,4 kg/m² | – | Lantor TDS (keresési kivonat) – 1 forrás |
| Soric LRC | 0,35 kg/m²/mm | – | Lantor (DirectIndustry) – 1 forrás |
| Soric száraz tömeg | ≈ 0,06 kg/m²/mm | XF 2–6: 135–345 g/m² | régebbi Lantor lap; csak a laminát tömegéhez |
| Hab felszíni felvétel / oldal | 0,15 kg/m² | 0–0,15 | Easy Composites EasyCell 75 (sima PVC-n „nem mérhető”); Evonik Rohacell szabadalom (PMI 71A: 0,18 kg/m² összesen); boatdesign.net (H80: ~0,3 kg/m² felület). Óvatosan a felső értéket vettük. PET habnál (nagyobb cella) több is lehet. |
| Horony | 1,2 × 2,5 mm @ 20 mm, keresztben, két oldal | – | Airex GP geometria (Univ. Plymouth, FPCM-10 cikk); kontroll: Easy Composites EasyCell 75G 10 mm: 427 cm³/m² horony+furat (mi egy oldalra ~0,31 dm³/m²-t adunk – azonos nagyságrend) |
| Furat | Ø2 mm @ 50 mm | – | 50 mm-es osztás: Airex GP (Plymouth); **Ø2 mm feltételezés**, állítható |
| Átvágás (grid) | 1 mm @ 30 mm | – | Airex CK 30 mm-es osztás (Plymouth); vágásszélesség feltételezés |
| Diab: hornyolás/vágás csökkentheti a felvételt | – | „akár 30 %” | Diab „How to reduce resin use” – csak minőségi adat |
| Infúziós háló | 0,60 kg/m² | 0,35–0,70 | Diatex FLONET 115: 0,355; OM 70: 0,452; DIANET 135: 0,489 kg/m² (R&G adatlapok); Easy Composites FM100 ~0,70 (háló + peel együtt); boatdesign.net Greenflow 75 ~0,55 |
| Peel ply | 0,10 kg/m² | 0,05–0,15 | boatdesign.net (~80 g/m², egy másik hozzászóló 7 g/m²); Easy Composites 0,7 kg/m² háló+peel együtt. **Gyenge forrásolás (fórum)** – a háló+peel összeg (0,7) egyezik az Easy Composites-szal. |
| Edény + tömlők maradéka | 0,10 kg | – | Easy Composites útmutató (+100 g); Univ. Texas Solar Vehicle wiki (+100 g) |
| Ráhagyás | 10 % | 5–20 % | **Nincs számszerű forrás**; a megrendelő által kért gyakorlati sáv. Az Easy Composites csak a fix 100 g-ot adja hozzá. |
| Keverési arány | 100:30 tömeg | – | Csak példa; mindig a termék adatlapja. |

## Forrás-URL-ek (2026-11 ellenőrizve)

- Lantor Soric XF TDS: https://cdn.shopify.com/s/files/1/0627/0435/3507/files/Wloknina_przekladkowa_Lantor_Soric-XF_TDS.pdf ; https://compositeenvisions.com/wp-content/uploads/2018/03/Model-965-soric-xf-tds.pdf ; https://acpcomposites.com/shop/core-materials/lantor-soric-core/lantor-soric-xf
- Saertex SAERcore resin consumption flyer: https://www.saertex.com/wp-content/uploads/2025/12/Flyer-SAERcore-Resin-Consumption.pdf
- Easy Composites infúziós útmutató: https://www.easycomposites.eu/learning/beginners-guide-to-carbon-fibre-resin-infusion ; FM100: https://www.easycomposites.eu/fm100-resin-infusion-mesh ; EasyCell 75G: https://www.easycomposites.eu/easycell75g-infusion-grooved-closed-cell-pvc-foam
- Diatex hálók (R&G): https://r-g.de/en/art/390183 , https://www.r-g.de/en/art/390184 , https://www.r-g.de/en/art/FMF-39115145
- Airex GP/CK geometria: https://ecm-academics.plymouth.ac.uk/jsummerscales/fpcm/fpcm10/fpcm10_submission_06.pdf
- Diab: https://www.diabgroup.com/how-to-reduce-resin-use-making-your-solution-lighter-than-ever/
- Gurit Guide to Composites (másolat): https://www.scribd.com/doc/200512288/Gurit-Guide-to-Composites ; Gurit Structural Core Processing Guide 2025 (képes PDF, számot nem sikerült kinyerni)
- Univ. Texas: https://cloud.wikis.utexas.edu/wiki/spaces/LHRSOLAR/pages/248512603/Resin+Infusion+Research
- boatdesign.net „Resin intake”: https://www.boatdesign.net/threads/resin-intake.56852/

## Nyitott kérdések

- Hab felszíni felvétel és furatátmérő: nincs gyártói kg/m² tábla (Diab, Gurit, 3A nem közöl a keresett helyeken). Próbalapon mérni: (infúzió utáni tömeg − száraz tömeg − szövet) / felület.
- PET hab (Airex T92) felszíni felvétele valószínűleg nagyobb a PVC-nél; SealX felülettel akár 40–50 % kevesebb (3A sajtóanyag).

## Talált AI-skillek

Webes keresés (SKILL.md / Claude skill / GitHub, kompozit gyantakalkulátor) nem talált ilyen skillt; csak
webes Vf-kalkulátorokat. Semmit nem töltöttünk le és nem telepítettünk.
