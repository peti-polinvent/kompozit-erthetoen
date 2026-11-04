# Narrációs forgatókönyv – „Kompozit érthetően” (akció-/recept-változat)

Célhossz: 60–90 s. Közönség: laikus + szakmai kollégák. Nyelv: magyar.
Stílus: **recept** – rövid, ütős mondatok, pörgős vágás, zene, ütésre bevágódó címek.
Buborékos címkék nincsenek; az éppen említett alkatrész **fénylő körvonalat** kap.
A képsor a Blender-jelenetből renderelt kameramozgás (`video/render_scenes.py`).

| # | Cím (bevágódik) | Kép | Narráció |
|---|---|---|---|
| 1 | A RECEPT | Messziről becsapódó nyitókép, körbesöprés az asztal körül | Íme a kompozit receptje! |
| 2 | HOZZÁVALÓK | A berendezések sorban kiemelve: szerszám → gyantatartály → szivattyú → puffertartály → gyantacsapda | Kell egy szerszám. Egy gyantatartály. Egy vákuumszivattyú. Egy puffertartály – és egy gyantacsapda. Ha ezek megvannak, jöhet a lényeg. |
| 3 | A RÉTEGREND | Oldalnézet, robbantott rétegrend; a tételek sorban kiemelve (punch-in), a végén gyors összeállás és a fólia ráfeszülése | A rétegrend. Ez határozza meg a termék tulajdonságait. Formaleválasztó a szerszámra. Rá az erősítő rétegek: a megfelelő irányú és anyagú szövetek kombinációjával érjük el a szükséges mechanikai tulajdonságokat. Letépő szövet. Gyantavezető háló. Meglövési és elszívási pont. Tömítőszalag – és a vákuumfólia. |
| 4 | INJEKTÁLÁS | Alacsony, döntött kamera a meglövés felől; a gyantafront átvonul; ráközelítés a kész lapra | Injektálás. A gyanta átjárja a rétegeket. Aztán hagyjuk térhálósodni. |
| 5 | BONTÁS | Elölről-felülről: fólia, háló, letépő szövet lekerül; a termék leemelkedik a szerszámról | Bontás. A letépő szövettel lejönnek a technológiai rétegek – és a termék lekerül a szerszámról. |
| 6 | KÉSZ | Hátráló-emelkedő kisöprés a jelenetből | Kész. Kompozit – érthetően. |

## Hang: AI-narráció

A felhőből a TTS-szolgáltatások nem érhetők el, ezért a hang a saját gépen készül:

    pip install edge-tts
    python video/tts/ai_hang.py        # → video/tts/01.mp3 … 06.mp3 (hu-HU-TamasNeural, lassítva, mélyítve)

A vágószkript `VOICE=ai ACTION=1` módban az mp3-akat használja, trailer-feldolgozással
(mély-kiemelés, kompresszor, enyhe zengés), zenével (`video/make_music.py`, szintetikus,
jogtiszta) és hangeffektekkel. A hangok tényleges hosszához igazítja a képsort és a feliratot.

A korábbi saját hangos felvételek a `video/tts/regi_sajat_hang/` mappában maradtak
(más szöveghez készültek).
