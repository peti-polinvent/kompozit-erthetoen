# Tanulási napló – „Kompozit érthetően”

AI Kihívás, 2026. november 2–6. · Mészáros Péter

A napló célja: lépésről lépésre rögzíteni, milyen eszközöket használtam, hogyan
dolgoztam az AI-jal (példa promptokkal), hol akadtam el, és hogyan jutottam túl
rajta. Az AI itt nem „megcsinálja helyettem”, hanem a tanulás gyorsítója: ő írja
az első verziót, én futtatom, ellenőrzöm, javítom – és közben megértem.

---

## 0. nap – hétfő este: tervezés és keretek

**Eszközök:** Claude (Cowork mód, a projektmappához kötve), Blender 4.5
LTS `bpy` Python-csomagként a felhőben, ffmpeg, GitHub Pages (tervezett).

**Döntések:**

- Téma: egy sík kompozit panel vákuuminfúziója. Egyszerű geometria, de az
  összes szereplő (szerszám, rétegrend, segédanyagok, zsák, gyantatartály,
  gyantacsapda, szivattyú) benne van. A sewerbot Compact dob később ugyanebből
  a logikából építhető.
- A rétegrend **paraméterfájlból** (`blender/params.json`) épül, nem kézzel
  modellezve: így később cserélhető, bővíthető, és szimulációhoz is jó alap.
- Munkamegosztás: az AI a felhőben futtatja a Blender-szkriptet és generálja a
  `.blend`/`.glb` fájlokat; én Blenderben megnyitom, ellenőrzöm, visszajelzek.
- Narráció: AI-hang (TTS) **és** felirat. GitHub-fiók: még nincs, a hét során
  létrehozom.

**Első prompt (a kihívás szövege + a saját projektjavaslatom):**

> „Az általam javasolt projekt: »Kompozit érthetően«. Egyetlen történetet
> mutatunk be: hogyan készül egy egyszerű kompozit panel vákuuminfúzióval? …
> A geometria és rétegrend változtatható legyen és ezek alapján szimulációt is
> tudjunk majd futtatni.”

Az AI visszakérdezett (hatókör, hol fusson a Blender, narráció, hosting), és
csak utána kezdett dolgozni. Tanulság: a jó visszakérdezés fél siker – a
válaszaim alapján a hét beosztása is kialakult.

**Elakadás #1 – Blender letöltés a felhőben.** A `download.blender.org`
nem volt elérhető a felhőből (hálózati korlát). Megoldás: a Blender
Python-csomagként (`pip install bpy==4.5.15`) a PyPI-ról telepíthető, így
headless módon fut – render és GLB-export is működik.

**Elakadás #2 – render sebesség.** EEVEE GPU nélkül 56 s/kép volt (640×360!),
ami egy 2 perces videóhoz vállalhatatlan. Megoldás: Workbench motor
(műszaki-illusztráció stílus): 1,5 s/kép 720p-ben. A stílus illik is a
tananyag jellegéhez.

**Elakadás #3 – átlátszó rétegek.** Az első renderen a vákuumzsák és a
gyantavezető háló túl erősen tintázta az alatta lévő gyantafrontot (zöldes lett a
borostyán helyett). Megoldás: alfa értékek hangolása a `params.json`-ban
(zsák 0,22; háló 0,55; gyanta 1,0) – és a Workbench háttérszínét a
`world.color` adja, nem a node-os háttér.

---

**Szakmai javítás #1 – terminológia.** Az AI „áramlási háló”-nak fordította a
flow mesh-t; a magyar szakmai neve **gyantavezető háló**. Egy mondatos
visszajelzés után minden fájlban (params.json, szkript, weboldal, napló)
cserélve. Tanulság: a szakmai nyelvet nekem kell hoznom – az AI a tükörfordítást
magabiztosan, de rosszul használja.

---

**Irányváltás – Fusion 360 a Blender helyett.** A cégnél a Fusion a
használt CAD, ezért a modellt abban kell(ene) építeni. Megbeszéltük, mi jár
ezzel: a Fusion nem fut a felhőben, tehát az AI nem tudja lefuttatni és
ellenőrizni a saját kódját – én futtatom, és a hibát/képernyőképet küldöm
vissza. Cserébe igazi CAD-modell lesz (f3d/STEP), amit a dob tervezésénél is
használhatunk. Amit a Fusion nem tud: a gyantafront vonulását, a tartályszint
csökkenését kulcskockázni, és GLB-t exportálni a webre.

Döntés: **hibrid**. Fusion = tervezőeszköz, Blender = animáció/render/web.
Hogy a két eszköz ugyanazt építse, az AI javaslatára a geometria kikerült egy
eszközfüggetlen Python-modulba (`blender/infusion_layout.py`): ez a params.json-
ból kiszámolja, melyik test hol van, mm-ben. Ezt importálja a Fusion-szkript
(CAD-testek) és a Blender-szkript (primitívek vagy a Fusion-export beolvasása)
is. Egy helyen van a „mi hol van” tudás.

Prompt (lényegében): „blender helyett fusion 360-ban kéne csinálni a dolgokat,
az megoldható?” – az AI nem vágott bele rögtön, hanem elmondta a
kompromisszumokat (nem tudja futtatni; animáció gyengébb) és három utat ajánlott.

**Elakadás #4 – hogyan teszteljük a Fusion-láncot Fusion nélkül?** A Blender-
oldali importáló-animáló szkriptet úgy ellenőriztük, hogy a Blender-primitíveket
„Fusion-szerűen” exportáltuk (testenként OBJ, centiméterben, Z-fel tengellyel,
ugyanolyan manifest.json-nal), és ezt olvastuk vissza. Így mire én a Fusion-
szkriptet futtatom, a lánc másik fele biztosan működik. Ami bizonytalan marad
a Fusion oldalán: a megjelenés-könyvtár neve verziónként változik (ezért a
szkript keresi, nem feltételezi), a STEP-export Personal licenc alatt lehet,
hogy tiltott (ezért try/except, az OBJ+F3D elég), és az OBJ-export tengelye
(ezért a `--yup` kapcsoló az importálóban).

---

## 1. nap – kedd

**Fusion-szkript, első futtatás: hibátlan.** Scripts and Add-Ins → „+” →
mappa kiválasztása → Run. Üzenetablak: „Kész: 29 test, 5 komponens. f3d
exportálva, STEP exportálva.” – figyelmeztetés nélkül. A STEP Personal licenc
alatt is kiment. A megjelenés-könyvtár kereső is talált anyagot, a testek
színesen jelentek meg.

Az exportot (29 OBJ + manifest.json, cm-ben, Z-fel tengellyel – a mock-
exporttal pontosan egyező formátum) a felhőbeli Blender beolvasta, animálta
és GLB-t készített belőle; a weboldal most már a **Fusion-geometriát** mutatja.

Amit a Fusion-export másképp csinál, mint a Blender-primitív: a csöveket a
szkript hengerszakaszokból és gömbökből rakja össze (TemporaryBRep), ezért
szögletesek, nem íveltek. Javítási ötlet a későbbre: Fusionban illesztett
spline-pálya mentén *sweep* – ez már „igazi” CAD-művelet, jó következő tanulási
lépés.

**Szakmai bemenet a gyakorlatból** (az én kérésemre került be):
–0,65 bar relatív vákuum az infúzió alatt; infúziós epoxi gyanta;
puffertartály a gyantacsapda és a szivattyú között, megfelelően kiépített
rendszerrel a folyamatos vákuumért. Ezek a `params.json` új `process`
blokkjába kerültek (innen olvassa a weboldal), a puffertartály pedig
vákuummérővel együtt bekerült a 3D-modellbe – az asztalt 1400-ról 1600 mm-re
kellett hosszabbítani, hogy elférjen.

**Szögletes csövek → sweep.** A Fusion-szkript 0.2: a csövek 3D illesztett
spline-pályán (`sketchFittedSplines`), a pálya kezdőpontjára merőleges síkon
rajzolt körprofil `sweep`-jével készülnek. Ha a sweep valamiért nem sikerül,
a szkript visszaesik a henger+gömb láncra és figyelmeztet. Ezt az AI nem
tudta lefuttatni – a Fusion-oldali ellenőrzés az én dolgom.

**Fusion-szkript 0.2, második futtatás: 34 test, hibátlan, a sweep elsőre
ment.** Az export 805 KB-os GLB-t ad (a sweep-elt csövek sűrűbb háromszöghálója
miatt, a korábbi 270 KB helyett) – mobilon is rendben. A weboldal mostantól
a puffertartályos, ívelt csövű Fusion-modellt mutatja.

**Szakmai javítás #2 – négy hiba a modellben** (a Fusion-nézetben vettem észre):
a csapda→puffer cső átment a tartály testén; a bevezető/elszívó csövek nem a
spirálcsövekhez csatlakoztak, hanem a köteg fölé lógtak; a vákuumfólia lapos
lemez volt, nem vette fel a rétegköteg alakját; és a tömítőszalag az asztalra
került a szerszámlap helyett (a számolt keret nagyobb volt a szerszámnál).
Javítás a layout-modulban: a puffertartály tetején két csonk, oda futnak a
csövek; a bevezető és elszívó cső a spirálcső végéhez csatlakozik és a fólia
széle alatt, a szerszámlapon kivezetve megy a tartályhoz/csapdához; a fólia
tető + négy döntött oldallap (a hasáb-primitív kapott irányvektorokat, amit a
Fusion `OrientedBoundingBox3D` és a Blender is ért), a szalag belső vonalán ér
le; a szalag a szerszám szélétől 30 mm-re, a lapon. 40 test. Fusion-szkript 0.3.
Tanulság: az AI a geometriát „nagyjából” jól rakja le, de a csatlakozásokat és
az anyagok valós viselkedését (a fólia ráfeszül, nem lebeg) nekem kell
számon kérnem.

**Szakmai javítás #3 – felismerhető berendezések, rendes csatlakozások.**
A szivattyú egy doboz volt; most forgólapátos vákuumszivattyú: talp, hengeres
motor ventilátorfedéllel, szivattyúfej szívócsonkkal, kipufogó, olajszint-ablak.
A gyantatartály és a gyantacsapda fedelet és csőcsonkokat kapott, belül
merülőcsővel (a tartályban a gyantába ér, a csapdában a térbe lóg, hogy a
gyanta ne a kimenet felé csorogjon); a csövek a csonkok tetejéhez
csatlakoznak, függőlegesen érkezve. 52 test. Fusion-szkript változatlan (0.3)
– csak a geometria-modul bővült, ez a layout-központú felépítés előnye.

**Vákuum-nyomásmérők** három helyen: a gyantacsapda fedelén (ez a zsákoldali,
a laminátumra ható vákuum – a –0,65 bar itt olvasható le), a puffertartályon
és a szivattyú szívóoldalán. Egy közös `_gauge()` segédfüggvény építi őket
(szár, ház, fehér számlap, piros mutató ~–0,65 bar állásban). 63 test.

**Fólia-perem.** A fólia lejtős oldala a szalag belső élénél ér le, és onnan
sík peremmel ráfekszik a tömítőszalagra, 15 mm-rel túl is lóg rajta – így
néz ki a valóságban is a lezárt zsák. 67 test.

**Szakmai javítás #4 – csőcsatlakozások.** A csövek a csonkok tetejére
„ráültek”, mert az illesztett spline végérintője ferde volt. Megoldás: minden
csonknál három egy vonalba eső pont (a csonk belsejében, a csonk fölött 12 és
40 mm-rel) – így a spline a végén egyenes és tengelyirányú, a cső 10 mm-re
belemegy a csonkba. A spirálcsövek végénél ugyanez tengelyirányból (`_leave`,
`_enter`, `_axial` segédfüggvények). Ez a Fusion sweep-nél is számít: az
érintő-folytonos pálya adja a szép csatlakozást.

**Fusion-szkript 0.3, harmadik futtatás: 67 test, hibátlan** – a döntött
fólialapok (`OrientedBoundingBox3D` irányvektorokkal), a műszerek és a
tengelyirányú csőcsatlakozások is rendben. A GLB 1,4 MB-ra hízott (egy
sweep-elt cső OBJ-ben ~1 MB), ezért az importáló a csövek hálóját 25%-ra
ritkítja (Decimate) → 810 KB. A weboldal mostantól ezt a Fusion-modellt
mutatja. **A 3D-modell ezzel szakmailag és technikailag lezárva.**

**GitHub és Pages (kedd délelőtt).** Fiók: `peti-polinvent`. GitHub Desktop
Mac-en. Elakadás #5: a Desktop a repót nem a projektmappában hozta létre,
hanem egy új, üres mappában (csak `.gitattributes`), és azt publikálta – az
oldal 404-et adott. Megoldás: Repository → Show in Finder, a projekt
tartalmát bemásolni a repómappába, Commit → Push. Ezután az oldal él:
https://peti-polinvent.github.io/kompozit-erthetoen/ – asztali és mobil
nézetben ellenőrizve (3D néző, animáció, jelmagyarázat, napló, sötét mód).
A repómappa innentől a hiteles másolat; a Windows-gépen klónozással jön létre.

**Videó – terv és lánc (kedd délután).** Narráció 6 jelenetben, 241 szó
(`video/narracio.md`, TTS-szegmensek `video/tts/NN.txt`). Elakadás #6: a
felhőből egyetlen neurális magyar TTS sem érhető el (Edge TTS, HuggingFace/
Piper – hálózati korlát), és a Mac-en futó parancssornak sincs hálózata.
Megoldás: a hangot a Mac beépített magyar hangjával (Tünde, `say` parancs)
állítjuk elő; addig espeak-ng gépi hanggal épül a teljes lánc. A lánc:
`build_video.py` a hangfájlok hosszából ütemtervet csinál (jelenetek közt
0,8 s), ebből VTT/SRT feliratot mondatonként, majd a `render_scenes.py`
Blenderben jelenetenként mozgó kamerával és a narrációhoz igazított animációs
időponttal renderel, végül ffmpeg vágja össze (címfeliratok, beégetett
felirat, H.264). Tanulság: a Workbench-render 720p-ben 2,7 s/kép – a 150 s-os
videó 2,5 óra lenne, ezért előbb 640×360/12 fps előnézet, és a végleges render
csak a végleges hanggal.

**Szakmai javítás #5 – az előnézeti videó után** (öt észrevétel):
1. A szivattyú nem volt egyértelműen bekötve: a szívócsonk a fej oldalára
   került, a puffertartályból jövő cső vízszintesen, tengelyben megy bele.
2. A gyantatartályban a gyanta az asztal alá lógott – klasszikus origó-hiba: a
   henger origója az alján volt, de a háló középre igazítva; a félmagasság a lap
   alá esett. A háló csúcsait eltoltam, most 0-tól a magasságig tart.
3. Felirat: nagyobb (27 px 720p-n), félkövér, sötét áttetsző sávval, csak alul.
4. A vákuumfólia Blenderben mostantól valódi hártya: 96×72-es rács, amely a
   köteg élein lekerekítve lejt a tömítőszalagig; alakkulccsal (shape key)
   „laza sátor” → „ráfeszült” animáció az összeállás és az infúzió között – ez a
   GLB-be morph-animációként átmegy, a weboldalon is látszik. (Elakadás #7: a
   glTF-exportőr az alakkulcs-animációt csak akkor vitte, ha az is NLA-sávba
   került.) A Fusion-modellben a fólia marad a lapokból álló CAD-változat.
5. Címkék: a render minden képkockához kiszámolja a címkézett alkatrészek
   képernyő-pozícióját (world_to_camera_view), egy utólépés (Pillow) buborékot
   és nyilat rajzol; a rétegek bemutatásánál egyszerre csak az épp helyére
   ereszkedő réteg címkéje látszik.
Döntés: a narráció **saját hanggal** készül (jelenetenként egy felvétel), nem
TTS-sel – hitelesebb, és a kiírás is ezt díjazza.

**Szakmai javítás #6 – a videó ellenőrző képei után.** Gelcoat élénk lila;
a gyantafront az infúzió indulásáig láthatatlan (0 szélesség); a fólia a
robbantott és összeállt nézetben sík lap, és csak a vákuumnál feszül rá;
a fólia áttetsző citromsárga; a formaleválasztó nem külön réteg, hanem a
szerszám felirata („formaleválasztóval előkészített szerszám”) – a rétegrend
így 8 elemű. Felirat: 27 px (a libass 288 px-es virtuális vászonhoz skáláz –
ezt tanulni kellett). Címkézés helyett **kiemelés**: az éppen bemutatott
alkatrész fénylő körvonalat kap (a renderelő külön maszkot renderel róla),
egyetlen névcímkével; a 2. jelenet oldalnézet kapcsos zárójeles rétegrend-
jelmagyarázattal; a buborékok automatikus, ütközésmentes elrendezést kaptak.
Az importáló a Fusion-exportból hiányzó elemeket primitívből pótolja, a
feleslegeseket kihagyja – így a geometria-módosítás nem vár a Fusion
újrafuttatására. Döntés: narráció saját hanggal.

**A sewerbot Compact dobja a modellben.** A dob Fusion-exportja (OBJ, cm,
281 ezer háromszög, 31 MB) a `params.json` új `extras` blokkján keresztül kerül
a jelenetbe: a Blender beolvassa, mértékegységet vált, a padlóra ülteti az
asztal alá. Webre 8%-ra ritkítva (22 ezer háromszög, 2 MB) – az eredeti nem
megy a repóba. Ez a következő fázis kiindulása: a dob teregetésének
(rétegrendjének) modellezése és animálása ugyanebből a paraméter-logikából.
A dob a kör alakú nyílást hordozó oldalára fektetve fekszik (`rotation_deg`
[0, −90, 0] – az első próba, [90, 0, 0], a nyakat a kamera felé fordította,
ez a kép alapján derült ki). Felülete 2/2 twill aramid mintázatú: a textúra
procedurálisan generált PNG (16 fonalköteg, sötét–világos mustársárga), Smart
UV-vetítéssel, 64 mm-es csempemérettel. **Elakadás #8:** a Workbench
renderelő nem veszi figyelembe a Mapping-csomópont skálázását, ezért a
csempeméretet közvetlenül az UV-koordináták szorzásával állítjuk be.
Döntés: a dob csak a Blender-jelenetben (weboldal, videó) szerepel, afféle
easter eggként, felirat nélkül – a Fusion CAD-modellbe nem kerül be, az
marad tisztán az infúziós összeállítás.

_(folytatás)_
