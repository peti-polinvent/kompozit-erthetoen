# Narrációs forgatókönyv – „Kompozit érthetően”

Célhossz: 105–150 s (a végleges felvétel ≈140 s). Közönség: laikus + szakmai kollégák. Nyelv: magyar.
Rövid mondatok, kiírt számok, nincs rövidítés. A táblázat a **felmondott, végleges** szöveget tartalmazza (Peti a felvétel előtt átfogalmazta); a felirat is ebből készül.
A képsor a Blender-jelenetből renderelt kameramozgás (lásd `video/render_scenes.py`).

| # | Idő (s) | Kép | Narráció |
|---|---|---|---|
| 1 | 0–11 | Cím-feliratos nyitókép, lassú körbefordulás az összeállt asztal körül | **Kompozit érthetően.** Hogyan készül egy kompozit lap vákuuminfúzióval? Ezt mutatjuk be egy egyszerű, háromdimenziós modellen, lépésről lépésre. |
| 2 | 12–32 | Felülnézet a szerszámra; a rétegek robbantva lebegnek | A vákuuminfúzió során a száraz erősítőszövetet a szerszámra fektetjük, fóliával légmentesen lezárjuk, és a levegőt kiszivattyúzzuk. A gyantát nem mi nyomjuk be: a külső légnyomás tolja át a rétegeken. Így egyenletes, buborékmentes, jól ismételhető lap készül. |
| 3 | 33–65 | Oldalnézet, közel; a rétegek egyenként ereszkednek a helyükre | Nézzük meg a rétegrendet, alulról felfelé. Az alumínium szerszámon formaleválasztó, majd gelcoat található. Erre négy üvegszövet réteg kerül: nulla kilencven, plusz mínusz negyvenöt, plusz mínusz negyvenöt és nulla kilencven fokos száliránnyal. Felül a tépőszövet, amit a gyanta térhálósodása után eltávolítunk a termékről. Ezen helyezkedik el a gyantavezető háló. Végül a vákuumfólia, tömítőszalaggal lezárva. |
| 4 | 66–107 | Félközeli a bevezetés felől; a gyantafront átvonul; vágás a csapdára és a puffertartályra | Az infúzió során a narancssárga spirálcsőből a gyanta a gyantavezető hálón fut végig, és onnan szivárog le a szövetekbe. A gyantavezető az elszívó oldal előtt véget ér, így a gyanta előbb átitatja a lapot, mint hogy elérné a kékkel feltüntetett elszívó csövet. Ha a gyanta mégis túlfut, a gyantacsapdában gyűlik össze, nem jut a szivattyúba. A csapda és a szivattyú között puffertartály gondoskodik az egyenletesebb vákuumról. A Polinventnél az infúzió mínusz nulla egész hatvanöt bar relatív vákuummal történik, saját fejlesztésű epoxi gyantával. |
| 5 | 107–116 | Kész lap felülnézetben, a tartály szintje lement, csapdában kevés gyanta; műszerek közelről | Mit kapunk eredményül? Egyenletes vastagságú, sima szerszámoldali felületű kompozit lapot, magas száltartalommal. |
| 6 | 117–140 | Osztott kép: Fusion-szkript részlet, params.json, a weboldal | Ezt a modellt négy nap alatt készítettem, mesterséges intelligenciával. A geometriát a Fusion háromszázhatvan szkriptje építette egy paraméterfájlból, az animációt Blenderrel, a weboldalt a model-viewerrel készítettem. A rétegrend bármikor cserélhető: nagyon jó alap a Sewerbot Compact kompozit dob gyártásának bemutatására. Köszönöm a figyelmet. |

## TTS-szegmensek (fájlonként egy jelenet)

A `video/tts/` mappába jelenetenként egy hangfájl kerül: `01.aiff … 06.aiff`
(vagy `.wav`). A vágószkript a hangok tényleges hosszához igazítja a képsort
és a feliratot, tehát a fenti időpontok csak irányadók.

### Felvétel saját hanggal (ez a végleges)

1. **Hol:** csendes szoba, puha felületek (függöny, szőnyeg), ne a laptop
   ventilátora mellett. **Mivel:** iPhone Hangjegyzetek vagy Mac QuickTime Player
   (Fájl → Új hangfelvétel) – a telefon általában jobb. Mikrofon 15–20 cm-re a
   szádtól, kissé oldalt, hogy a „p” és „b” ne puffogjon.
2. **Jelenetenként egy felvétel**, a `video/tts/01.txt … 06.txt` szövegét
   olvasva. Természetesen, beszélgetős tempóban – a számokat úgy mondd, ahogy
   élőben mondanád („mínusz nulla egész hatvanöt bar”). Ha egy mondat elrontva,
   állj meg, és mondd újra az egész szegmenst – a vágás így egyszerűbb.
3. Az elején-végén lehet csend, a szkript automatikusan levágja. A hangerőt is
   kiegyenlíti (loudnorm), így nem kell egyformán hangosnak lenni.
4. Fájlnevek: `01.m4a`, `02.m4a` … `06.m4a` (vagy .wav/.aiff/.caf) a
   `video/tts/` mappában. iPhone-ról AirDrop a Macre, átnevezés, bemásolás.
5. Commit + Push, és szólj – a felhőben készül a végleges 720p videó.

Célhossz: szegmensenként kb. 10 / 20 / 28 / 32 / 12 / 18 s (összesen ~2 perc
a szünetekkel). Ha hosszabb lesz, nem baj, a képsor igazodik; 3 perc felett
viszont rövidítünk a szövegen.

### Tartalék

Ha nincs idő felvételre, a Mac beépített magyar hangja (Tünde) egy paranccsal
előállítja: `say -v "Tünde" -r 165 -f tts/01.txt -o tts/01.aiff` (és így tovább).
