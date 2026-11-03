# Narrációs forgatókönyv – „Kompozit érthetően”

Célhossz: 105–120 s. Közönség: laikus + szakmai kollégák. Nyelv: magyar.
TTS-re optimalizálva: rövid mondatok, kiírt számok, nincs rövidítés.
A képsor a Blender-jelenetből renderelt kameramozgás (lásd `video/render_scenes.py`).

| # | Idő (s) | Kép | Narráció |
|---|---|---|---|
| 1 | 0–11 | Cím-feliratos nyitókép, lassú körbefordulás az összeállt asztal körül | **Kompozit érthetően.** Hogyan készül egy kompozit lap vákuuminfúzióval? Ezt mutatjuk be egy egyszerű, háromdimenziós modellen – lépésről lépésre. |
| 2 | 11–30 | Felülnézet a szerszámra; a rétegek robbantva lebegnek | A vákuuminfúzió zárt szerszámos eljárás. A száraz erősítőszövetet a szerszámra fektetjük, fóliával légmentesen lezárjuk, és a levegőt kiszivattyúzzuk. A gyantát nem mi nyomjuk be: a külső légnyomás tolja át a rétegeken. Így egyenletes, buborékmentes, jól ismételhető lap készül. |
| 3 | 30–58 | Oldalnézet, közel; a rétegek egyenként ereszkednek a helyükre | Nézzük a rétegrendet, alulról felfelé. Az alumínium szerszámon formaleválasztó, majd gelcoat. Erre négy üvegszövet réteg kerül: nulla–kilencven, plusz-mínusz negyvenöt, plusz-mínusz negyvenöt, nulla–kilencven fokos száliránnyal. Felül a tépőszövet, amit kikeményedés után lehúzunk. Rá a gyantavezető háló, amely elosztja a gyantát. Végül a vákuumfólia, tömítőszalaggal lezárva. |
| 4 | 58–88 | Félközeli a bevezetés felől; a gyantafront átvonul; vágás a csapdára és a puffertartályra | Indul az infúzió. A narancssárga spirálcsőből a gyanta a gyantavezető hálón fut végig, és onnan szivárog le a szövetekbe. A háló az elszívó oldal előtt véget ér, így a gyanta előbb átitatja a lapot, mint hogy elérné a kék elszívó csövet. Ami mégis túlfut, a gyantacsapdában gyűlik össze – nem jut a szivattyúba. A csapda és a szivattyú között puffertartály simítja a vákuumot. A Polinventnél az infúzió mínusz nulla egész hatvanöt bar relatív vákuummal fut, saját fejlesztésű epoxi gyantával. |
| 5 | 88–101 | Kész lap felülnézetben, a tartály szintje lement, csapdában kevés gyanta; műszerek közelről | Az eredmény: egyenletes vastagságú, sima szerszámoldali felületű kompozit lap, magas száltartalommal, zárt rendszerben – kevés hulladékkal és kevés kibocsátással. |
| 6 | 101–118 | Osztott kép: Fusion-szkript részlet, params.json, a weboldal | Ezt a modellt négy nap alatt készítettem, mesterséges intelligenciával tanulva. A geometriát a Fusion 360 szkriptje építi egy paraméterfájlból, az animációt a Blender, a weboldalt a model-viewer. A rétegrend bármikor cserélhető – ez az alap a sewerbot kompozit dobjának modellezéséhez. Köszönöm a figyelmet. |

## TTS-szegmensek (fájlonként egy jelenet)

A `video/tts/` mappába jelenetenként egy hangfájl kerül: `01.aiff … 06.aiff`
(vagy `.wav`). A vágószkript a hangok tényleges hosszához igazítja a képsort
és a feliratot, tehát a fenti időpontok csak irányadók.

### Hang előállítása a Mac beépített magyar hangjával (ajánlott)

1. Rendszerbeállítások → Kisegítő lehetőségek → Felolvasott tartalom →
   Rendszerhang → „Hangok kezelése…” → Magyar → **Tünde (Enhanced vagy Premium)**
   letöltése (egyszeri, pár száz MB).
2. Terminal, a repó mappájában:
   ```bash
   cd ~/Documents/kompozit-erthetoen/video
   for i in 01 02 03 04 05 06; do say -v "Tünde" -r 165 -f tts/$i.txt -o tts/$i.aiff; done
   ```
   (`-r 165` = szó/perc, nyugodt tempó. Ha a hang neve más, `say -v '?' | grep hu` listázza.)
3. Commit + Push, és szólj – a felhőben összevágom.

### Tartalék

Ha a fenti nem megy, a felhőben gépi (espeak-ng) hanggal készül el a videó; ez
robotikusabb, de a lánc ugyanaz, a hang bármikor cserélhető.
