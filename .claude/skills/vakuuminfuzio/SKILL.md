---
name: vakuuminfuzio
description: Kompozitgyártás vákuuminfúzióval (VARTM / resin infusion) – szakmai tudás, magyar terminológia, tipikus értékek, gyakori hibák és a laikus magyarázat szabályai. Használd, ha a kompozit panel / dob infúziójáról, rétegrendről, segédanyagokról, berendezésekről szöveget, narrációt, weboldalt, 3D-modellt vagy animációt készítesz ebben a projektben.
---

# Vákuuminfúzió – szakmai alap a „Kompozit érthetően” projekthez

## Terminológia (kötelező magyar szakszavak)

| Angol | Magyar (ezt használd) | Kerülendő |
|---|---|---|
| mould / tool | szerszám | forma (laikus szövegben elmegy) |
| release agent | formaleválasztó | leválasztó viasz |
| reinforcement / dry fabric | erősítő réteg, száraz szövet | |
| peel ply | letépő szövet | tépőszövet (régi szövegekben előfordul) |
| flow mesh / infusion mesh | **gyantavezető háló** | áramlási háló (tükörfordítás, HIBÁS) |
| spiral tube / omega profile | spirálcső | |
| inlet | meglövési pont, gyantabevezetés | |
| vacuum line / outlet | elszívási pont, vákuumelszívás | |
| sealant tape / tacky tape | tömítőszalag | |
| vacuum bag | vákuumfólia (vákuumzsák) | |
| catch pot / resin trap | gyantacsapda | |
| vacuum reservoir | puffertartály (vákuumtartály) | |
| cure | térhálósodás, kikeményedés | száradás (HIBÁS: a gyanta nem szárad) |
| demould | bontás, kiszerelés | |

A rétegrend alulról felfelé: szerszám → formaleválasztó → erősítő rétegek (irány és anyag
szerint kombinált szövetek) → letépő szövet → gyantavezető háló → spirálcsövek (meglövés, elszívás)
→ tömítőszalag a szerszám szélén → vákuumfólia. Gelcoat ebben a projektben NINCS.

## Folyamat (a sorrend fontos)

1. Szerszám tisztítása, formaleválasztó felvitele.
2. Száraz rétegrend lerakása (irányok pl. 0/90°, ±45°), ragasztóspray rögzíti.
3. Letépő szövet, gyantavezető háló, spirálcsövek. A háló az elszívó oldal **előtt** 2–5 cm-rel
   véget ér, hogy a gyanta ne „rövidre zárjon” a vákuumcső felé.
4. Tömítőszalag, vákuumfólia, csövek bekötése: gyantatartály → (csap) → meglövés … elszívás →
   gyantacsapda → puffertartály → vákuumszivattyú.
5. Vákuum + **tömörségpróba**: zárt szivattyú-ággal a vákuum percek alatt is alig eshet
   (néhány mbar). Szivárgó zsák = porózus, gyenge termék.
6. Gyanta bekeverése (keverési arány tömegre!), szükség esetén gáztalanítás.
7. Infúzió: a csap nyit, a **légköri nyomás** tolja be a gyantát (nem pumpáljuk!).
   A front a háló tetején siet, alatta lefelé szivárog a szövetbe.
8. Kitöltés után a bevezetés lezárva, vákuum tartva a gélesedésig, majd térhálósodás.
9. Bontás: fólia, háló, letépő szövet le; a termék leválik a szerszámról.

## Tipikus értékek (laikus szövegben kerekítve)

- Infúziós gyanta viszkozitása: ~100–300 mPa·s (kb. olajszerű). Fazékidő ≥ kitöltési idő.
- Száltartalom: ~50–60 térfogat%. Kézi laminálásnál jellemzően ~25–35 térfogat%.
- Áteresztőképesség (Darcy): üvegszövet-köteg ~2–4·10⁻¹¹ m², gyantavezető hálóval a hatásos érték ~10⁻⁹ m².
- Kitöltési idő (Darcy-becslés): t ≈ μ·φ·L² / (2·K·Δp) – L a folyási hossz; a hossz
  **négyzetével** nő, ezért nagy darabnál több meglövési pont kell.
- A vákuum a légköri nyomásnál jóval kisebb, és **végig tartani kell** (ezért a puffertartály).

## Gyakori hibák (amire a modellben/szövegben figyelni kell)

- Szivárgás → légzárvány, száraz foltok. Tömörségpróba nélkül nincs infúzió.
- Gyanta a szivattyúban → ezért van gyantacsapda; a csapdában a bemenet merülőcsöve a térbe lóg.
- „Race-tracking”: a gyanta a szélek mentén előresiet – a háló és a csövek elhelyezése számít.
- Fizikai realitás a 3D-ben: csövek csonkhoz tengelyirányban csatlakoznak; a fólia ráfeszül a
  kötegre, nem lebeg; a tömítőszalag a szerszámon van, nem az asztalon; a kész **termék vékony lap**
  (valós vastagság ~2 mm), nem tégla.

## Laikus magyarázat szabályai

- Egy gondolat = egy mondat. Hasonlat jó: „a háló a gyanta autópályája”, „a légnyomás tolja be,
  mint a szívószálban az üdítőt”.
- Mindig mondd meg, MIÉRT kell egy eszköz (a csapda védi a szivattyút; a puffer egyenletesen tartja
  a vákuumot; a letépő szövet érdes, ragasztható felületet hagy és leviszi a segédanyagokat).
- Cégnév a nyilvános anyagokban nem szerepel.
