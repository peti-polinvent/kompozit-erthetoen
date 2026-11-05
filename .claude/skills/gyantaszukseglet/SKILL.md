---
name: gyantaszukseglet
description: Gyantaszükséglet (resin quantity) becslése vákuuminfúzióhoz, vákuumzsákos és kézi laminálásra – szövet, CSM, Soric-típusú magpaplan, PVC/PET hab (sima, hornyolt, perforált, bevágott), peel ply, infúziós háló, cső. Használd, ha a kalkulátort (assets/calc/resin.js) módosítod, alapértéket cserélsz, vagy valaki megkérdezi, mennyi gyantát keverjen.
---

# Gyantaszükséglet – modell, alapértékek, források

Kód: `assets/calc/resin.js` (`compute`, `rowResin`, `DEF`). Teszt: `node tests/calc/resin_check.mjs`
(23 kézzel számolt ellenőrzés, köztük Easy Composites-összevetés és egy PET-szendvics). Demó: `tests/calc/demo.html`.

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
| Vf szövet, infúzió | 50 % | 45–55 % | Szövött/varrott üveg infúzióval jellemzően 50–55 %; a gyantabecsléshez az alsó végét vesszük (a `vakuuminfuzio` skill 50–60 %-ával összhangban). JEC Composites Magazine 35 (2007): vákuumos eljárással Gc 0,65 „könnyen” → Vf 0,5; fram.nl: infúzió ≈ ⅔ üveg tömegre (Wf 67 % → Vf ≈ 47–50 %); Easy Composites: gyanta = rétegtömeg / 1,5 (szénre Wf 60 % → Vf ≈ 49 %). |
| Vf szövet, vákuumzsák | 38 % | 35–45 % | Óvatos becslés a kézi (30–40 %, Gurit Guide) felső és az infúzió alsó értéke közt; BRIN (Pustekroket 2021) üveg vákuumzsák Wf 66 % (≈ Vf 47 %) felső korlát. **Közvetlen Vf-forrás nincs – a UI jelöli.** |
| Vf szövet, kézi | 30 % | 25–40 % | JEC Composites Magazine 35 (2007): kézi ≈ 0,3; Gurit Guide (kézi 30–40 %) |
| Vf CSM infúzió / zsák / kézi | 30 / 25 / 17,5 % | 28–35 / 20–30 / 15–20 % | Saertex „SAERcore Resin Consumption” flyer 06/2025 (CSM ref.: kézi 17,5 %, infúzió 33 %); fram.nl (kézi ≈ ⅓ üveg tömegre ≈ Vf 18 %); közismert CSM üveg:gyanta 1:2–1:2,5. A vákuumzsák-érték interpoláció (a UI jelöli). |
| Szálsűrűség üveg / szén / aramid | 2,56 / 1,76 / 1,44 g/cm³ | 2,54–2,60 / 1,75–1,95 / 1,44–1,45 | Gurit Guide; kompozit sűrűségtábla (E-üveg 2,56, szén 1,75–1,95, Kevlar 49 1,45). Szénnél az alsó érték óvatos. |
| Bazalt | 2,65 g/cm³ | 2,63–2,70 | Mafic roving TDS (DIN 65569): 2,63; GBF folytonos bazaltszál: 2,65 ± 0,1; Wikipedia-táblázat 2,67 |
| Gyanta (epoxi) sűrűség | 1,15 g/cm³ | 1,10–1,20 | Gurit Guide; kompozit sűrűségtábla (epoxi 1,1–1,4). Saját termék adatlapja felülírja. |
| Soric XF felvétel | 1,5→1,0; 2→1,0; 3→1,4; 4→1,9; 5→2,4; 6→2,8; 10→5,4 kg/m² | ≈ 0,47–0,67 kg/m²/mm | Lantor Soric XF TDS v2.2 (2020; a PDF szövegéből 2026-11-ben újra kiolvasva, száraz tömeg 100/135/180/250/320/345/625 g/m²) és régebbi Lantor lap (Composite Envisions „Model 965”), ACP Composites termékoldal. Poliészterrel mérve; epoxinál hasonló sűrűség. |
| Soric TF | 1,5→0,8; 2→1,0; 3→1,4 kg/m² | – | Lantor TDS (keresési kivonat) – 1 forrás |
| Soric LRC | 0,35 kg/m²/mm | – | Lantor (DirectIndustry) – 1 forrás |
| Soric száraz tömeg | ≈ 0,06 kg/m²/mm | XF 2–6: 135–345 g/m² | régebbi Lantor lap; csak a laminát tömegéhez |
| Hab felszíni felvétel / oldal | PVC 0,30; PET 0,50 kg/m² (anyagváltáskor vált) | 0–0,5 | **Javítva (korábban 0,15).** Gurit Structural Core Processing Guide rev 7 (2024) Table 4, sima lap infúzióval, két oldal együtt: PVC HT 80 0,62, PVC 100 0,56, Corecell M80 0,71, Kerdyn (PET) 100 1,04 kg/m² → ÷ 2; boatdesign.net (H80 ≈ 0,3 kg/m² felületenként; „PVC-re 0,6 kg/m²”). Ellentmondó: Easy Composites EasyCell 75 („nem mérhető”), Evonik PMI (0,18 összesen, finom cella). Egy gyártói forrás + fórum → a UI „egy forrás” jelölést kap. |
| Horony | 1,2 × 2,5 mm @ 20 mm, keresztben, két oldal | – | Airex GP geometria (Univ. Plymouth, FPCM-10 cikk); Gurit „standard” horony 2 × 2 mm (osztás nélkül) – a keresztmetszet 3 vs 4 mm², ezért egyforrásúként jelölve. Kontroll: Easy Composites EasyCell 75G (egy oldalon hornyolt + perforált): 427 cm³/m²; nálunk g1+p 0,31 dm³/m² (−27 %; az EC horonyméretét nem közli, a geometria a felhasználó által állítható). |
| Furat | Ø2 mm @ 50 mm | – | 50 mm-es osztás: Airex GP (Plymouth); **Ø2 mm feltételezés**, állítható |
| Átvágás (grid) | 1 mm @ 30 mm | – | Airex CK 30 mm-es osztás (Plymouth); vágásszélesség feltételezés |
| Diab: hornyolás/vágás csökkentheti a felvételt | – | „akár 30 %” | Diab „How to reduce resin use” – csak minőségi adat |
| Infúziós háló | 0,60 kg/m² | 0,35–0,70 | Diatex FLONET 115: 0,355; OM 70: 0,452; DIANET 135: 0,489 kg/m² (R&G adatlapok); Easy Composites FM100 ~0,70 (háló + peel együtt); boatdesign.net Greenflow 75 ~0,55 |
| Peel ply | 0,10 kg/m² | 0,03–0,10 | Explore Composites mérés: nejlon peel ply 30–50 g/m²; Directeck WS877 (83 g/m²) adatlap: 83 g epoxi/réteg; boatdesign.net ~80 g/m². Óvatosan a felső értéket vettük; a háló+peel összeg (0,7) egyezik az Easy Composites-szal. |
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

- Hab felszíni felvétel: egyetlen gyártói tábla a Gurit Structural Core Processing Guide 2024 Table 4 (https://www.gurit.com/wp-content/uploads/bsk-pdf-manager/2024/12/Structural-Core-Processing-Guide-rev-7-2024.pdf); Diab/3A nem közöl számot. Furatátmérő: nincs forrás. Próbalapon mérni: (infúzió utáni tömeg − száraz tömeg − szövet) / felület.
- Liter: a kalkulátor egyetlen ρr-t használ a kikeményedett laminátra és a folyékony keverékre is; a folyékony keverék kb. 2–4 %-kal könnyebb (zsugorodás), ez a literben elhanyagolható.
- Ellenőrző források (2026-11): JEC Composites Magazine 35 (2007) nxtbook; fram.nl/about/laminating/about-vacuum-infusion.html; Mafic TDS (knowde.com); explorecomposites.com peel ply teszt.
- PET hab (Airex T92) felszíni felvétele valószínűleg nagyobb a PVC-nél; SealX felülettel akár 40–50 % kevesebb (3A sajtóanyag).

## Talált AI-skillek

Webes keresés (SKILL.md / Claude skill / GitHub, kompozit gyantakalkulátor) nem talált ilyen skillt; csak
webes Vf-kalkulátorokat. Semmit nem töltöttünk le és nem telepítettünk.
