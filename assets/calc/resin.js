/* Gyantaszükséglet-kalkulátor – önálló ES modul.
   Beül a #gyanta-kalk elembe (ha van), saját CSS-t tesz a <head>-be, a nyelvet a
   <html lang> adja, 'langchange' eseményre újrarajzol. A compute() tiszta függvény,
   a tests/calc/resin_check.mjs ezt ellenőrzi. Modell és források:
   .claude/skills/gyantaszukseglet/SKILL.md */

/* ---------- Alapértékek (forrásokkal a SKILL.md-ben) ---------- */
export const DEF = {
  rhoR: 1.15,                        // kevert, kikeményedett epoxi g/cm³ (1,10–1,20)
  rhoF: { glass: 2.56, carbon: 1.76, aramid: 1.44, basalt: 2.65 },
  vf: {                               // szálvolumen-hányad, óvatos (kisebb Vf = több gyanta)
    infusion: { fabric: 50, csm: 30 },
    bag:      { fabric: 38, csm: 25 },
    hand:     { fabric: 30, csm: 17.5 }
  },
  vfRange: {
    infusion: { fabric: [45, 55], csm: [28, 35] },
    bag:      { fabric: [35, 45], csm: [20, 30] },
    hand:     { fabric: [25, 40], csm: [15, 20] }
  },
  // Lantor Soric TDS v2.2 (2020): gyantafelvétel kg/m² a névleges vastagságnál
  soric: {
    XF: [[1.5, 1.0], [2, 1.0], [3, 1.4], [4, 1.9], [5, 2.4], [6, 2.8], [10, 5.4]],
    TF: [[1.5, 0.8], [2, 1.0], [3, 1.4]],
    LRC: 0.35                          // kg/m² per mm
  },
  soricDryPerMm: 0.06,                // száraz tömeg kb. kg/m² per mm (XF 2–6: 135–345 g/m²)
  // sima habfelület gyantafelvétele oldalanként kg/m²: Gurit Structural Core Processing Guide rev 7
  // (2024) Table 4, infúzió, két oldal: PVC 80 0,62, PVC 100 0,56, Kerdyn (PET) 100 1,04 → ÷ 2
  foamSurf: { pvc: 0.30, pet: 0.50 },
  foamDensity: { pvc: 80, pet: 100 },
  groove: { w: 1.2, d: 2.5, pitch: 20 },   // Airex GP geometria
  perf: { d: 2, pitch: 50 },
  grid: { kerf: 1, pitch: 30 },
  peel: 0.10,                          // kg/m² (0,05–0,15)
  mesh: 0.60,                          // kg/m² (0,35–0,70)
  lineId: 10,
  waste: 10,                           // % (5–20)
  pot: 0.10,                           // kg
  mix: [100, 30]
};

/* ---------- Tiszta számítás ---------- */
function interp(tab, t) {
  if (t <= tab[0][0]) return tab[0][1] / tab[0][0] * t;
  for (let i = 1; i < tab.length; i++) {
    const [x0, y0] = tab[i - 1], [x1, y1] = tab[i];
    if (t <= x1) return y0 + (y1 - y0) * (t - x0) / (x1 - x0);
  }
  const [xl, yl] = tab[tab.length - 1];
  return yl / xl * t;
}

/* Egy sor gyantája (kg), szála és száraz tömege (kg), illetve hogy a laminátumba épül-e. */
export function rowResin(r, g) {
  const n = (r.layers ?? 1) * (r.area ?? 0);
  const rhoR = g.rhoR;
  switch (r.type) {
    case 'fabric':
    case 'csm': {
      const rhoF = r.type === 'csm' ? DEF.rhoF.glass : (r.rhoF ?? DEF.rhoF[r.fibre || 'glass']);
      const vf = (r.type === 'csm' ? g.vfCsm : g.vfFabric) / 100;
      const fibre = r.gsm / 1000 * n;
      const resin = fibre * (rhoR / rhoF) * (1 - vf) / vf;
      return { resin, fibre, dry: fibre, inLam: true };
    }
    case 'soric': {
      const t = r.t;
      const perM2 = r.grade === 'LRC' ? DEF.soric.LRC * t : interp(DEF.soric[r.grade || 'XF'], t);
      return { resin: perM2 * n, fibre: 0, dry: DEF.soricDryPerMm * t * n, inLam: true };
    }
    case 'foam': {
      const f = r.finish || 'plain', t = r.t;
      let vol = 0;                                   // mm³/mm² = mm (térfogat / felület)
      const sides = f === 'g1' ? 1 : (f === 'g2' || f === 'gp') ? 2 : 0;
      if (sides) vol += sides * 2 * r.gw * r.gd / r.gpitch;          // keresztirányú hornyok
      if (f === 'p' || f === 'gp') vol += Math.PI * (r.pd / 2) ** 2 * t / (r.pp * r.pp);
      if (f === 'grid') vol += 2 * r.kerf * t / r.kp;                 // átmenő bevágások két irányban
      const perM2 = 2 * r.surf + vol / 1000 * rhoR * 1000;            // mm → m³/m², × kg/m³
      return { resin: perM2 * n, fibre: 0, dry: r.density * t / 1000 * n, inLam: true };
    }
    case 'sheet': return { resin: r.u * n, fibre: 0, dry: 0, inLam: true };
    case 'peel':
    case 'mesh': return { resin: r.u * n, fibre: 0, dry: 0, inLam: false };
    case 'line': {
      const resin = r.len * Math.PI * (r.id / 2000) ** 2 * rhoR * 1000;
      return { resin, fibre: 0, dry: 0, inLam: false };
    }
  }
  return { resin: 0, fibre: 0, dry: 0, inLam: false };
}

/* g: { rhoR, vfFabric, vfCsm, waste, pot, mixA, mixB }, rows: [...] – minden szám. */
export function compute(g, rows) {
  const per = rows.map(r => rowResin(r, g));
  let net = 0, lamResin = 0, lamDry = 0, fib = 0, fibResin = 0, refArea = 0;
  per.forEach((p, i) => {
    net += p.resin;
    if (p.inLam) { lamResin += p.resin; lamDry += p.dry; refArea = Math.max(refArea, rows[i].area || 0); }
    if (p.fibre) { fib += p.fibre; fibResin += p.resin; }
  });
  const wasteKg = net * g.waste / 100;
  const total = net + wasteKg + g.pot;
  const hardener = total * g.mixB / (g.mixA + g.mixB);
  const lam = lamResin + lamDry;
  const wf = fib ? fib / (fib + fibResin) : null;
  // Vf a szöveteknél: szál térfogat / (szál + gyanta térfogat)
  let vFib = 0;
  rows.forEach((r, i) => {
    if (r.type === 'fabric') vFib += per[i].fibre / (r.rhoF ?? DEF.rhoF[r.fibre || 'glass']);
    if (r.type === 'csm') vFib += per[i].fibre / DEF.rhoF.glass;
  });
  const vf = fib ? vFib / (vFib + fibResin / g.rhoR) : null;
  return {
    per, net, wasteKg, total, litres: total / g.rhoR,
    resin: total - hardener, hardener,
    laminate: lam, refArea, laminatePerM2: refArea ? lam / refArea : 0, vf, wf
  };
}

/* ---------- Szövegek ---------- */
const LOC = { hu: 'hu-HU', en: 'en-GB', de: 'de-DE', zh: 'zh-CN' };
const S = {
  hu: {
    title: 'Mennyi gyantát keverjek?',
    intro: 'Add meg a rétegrendet: anyag, felület és rétegszám. A kalkulátor kiszámolja a bekeverendő gyanta és edző tömegét.',
    process: 'Eljárás', infusion: 'Vákuuminfúzió', bag: 'Vákuumzsák (kézi laminálás után)', hand: 'Kézi laminálás',
    vfFabric: 'Szövet szálvolumene, Vf (%)', vfCsm: 'Paplan szálvolumene, Vf (%)',
    rhoR: 'Gyanta sűrűsége (g/cm³)', mixA: 'Gyanta (tömegrész)', mixB: 'Edző (tömegrész)',
    mixNote: 'A 100:30 csak kiinduló érték. Mindig a saját gyantád adatlapján szereplő tömegarányt írd be.',
    waste: 'Ráhagyás (%)', pot: 'Edényben és tömlőben maradó gyanta (kg)',
    presets: 'Minták', pOurs: 'A mi lapunk: 4× 300 g/m² üvegszövet, 0,12 m², infúzió',
    pSandwich: 'Szendvics: 2+2× 450 g/m² üveg, 10 mm hornyolt-perforált PVC, 1 m²',
    pSoric: 'Soric XF 3 mm, 2+2× 300 g/m² üveg, 1 m²',
    layers: 'Rétegrend', add: 'Sor hozzáadása', remove: 'Sor törlése', type: 'Anyag',
    t_fabric: 'Szövet vagy varrott szövet (NCF)', t_csm: 'Vágott üvegszál-paplan (CSM)',
    t_soric: 'Infúziós magpaplan (Soric-típus)', t_foam: 'Habmag (PVC, PET)',
    t_peel: 'Leszakítószövet (peel ply)', t_mesh: 'Infúziós háló', t_sheet: 'Adatlap szerinti felvétel', t_line: 'Infúziós cső',
    fibre: 'Szál', glass: 'Üveg (E)', carbon: 'Szén', aramid: 'Aramid', basalt: 'Bazalt',
    gsm: 'Felületi tömeg (g/m²)', nl: 'Rétegszám', area: 'Felület (m²)', thick: 'Vastagság (mm)',
    grade: 'Típus', mat: 'Hab', pvc: 'PVC', pet: 'PET', density: 'Sűrűség (kg/m³)', finish: 'Felület',
    plain: 'Sima', g1: 'Hornyolt, egy oldalon', g2: 'Hornyolt, két oldalon', p: 'Perforált', gp: 'Hornyolt és perforált', grid: 'Átvágott, hálóra ragasztott',
    surf: 'Felszíni felvétel oldalanként (kg/m²)', gw: 'Horony szélessége (mm)', gd: 'Horony mélysége (mm)', gpitch: 'Hornyok távolsága (mm)',
    pd: 'Furat átmérője (mm)', pp: 'Furatok távolsága (mm)', kerf: 'Vágás szélessége (mm)', kp: 'Vágások távolsága (mm)',
    u: 'Gyantafelvétel (kg/m²)', len: 'Hossz (m)', id: 'Belső átmérő (mm)',
    bad: 'Ide pozitív szám kell.', badSome: 'Van hibás mező, azt a számítás kihagyja.',
    total: 'Bekeverendő gyantarendszer', litre: 'liter', resin: 'Gyanta', hard: 'Edző',
    lam: 'A kész laminát tömege', perM2: 'négyzetméterenként (a legnagyobb felületre vetítve)',
    fib: 'Szálarány a szövetekben', net: 'Beépül és a segédanyagokban marad', wasteL: 'Ráhagyás', potL: 'Edény és tömlők',
    rowOut: 'gyanta', how: 'Hogyan számol?',
    how1: 'Szövet és paplan: a gyanta tömege a szál tömegéből jön. Egy réteg gyantája = felületi tömeg × (gyanta sűrűsége ÷ szál sűrűsége) × (1 − Vf) ÷ Vf. A Vf az eljárástól függ: infúzióval a szál jobban tömörödik, kevesebb gyanta kell, mint kézi laminálásnál. A paplan (CSM) mindig több gyantát visz.',
    how2: 'Magok: a Soric-típusú paplan a gyártói táblázat szerint vastagságtól függően vesz fel gyantát (3 mm ≈ 1,4 kg/m²). A habmag sima felületén csak a felvágott cellák telnek meg (80-as PVC ≈ 0,3 kg/m² oldalanként, PET-nél több), a hornyok, furatok és vágások viszont megtelnek gyantával: ezek térfogatát a megadott méretekből számolja.',
    how3: 'Segédanyagok: a leszakítószövet és az infúziós háló a lap felett telítődik, és a gyantájuk a bontáskor a szemétbe kerül. A cső belseje is megtelik.',
    how4: 'A végén hozzáadja a ráhagyást és az edényben maradó gyantát, majd a tömegarány szerint szétosztja gyantára és edzőre. A liter a gyanta sűrűségével számolt.',
    defs: 'Alapértékek, tartományok, források', dVal: 'Alapérték', dRange: 'Tartomány', dSrc: 'Forrás',
    dVf: 'Vf szövet, infúzió / vákuumzsák / kézi', dVfC: 'Vf paplan, infúzió / vákuumzsák / kézi', dRho: 'Szálsűrűség üveg / szén / aramid / bazalt (g/cm³)',
    dSoric: 'Soric XF felvétel 2 / 3 / 4 / 6 mm (kg/m²)', dFoam: 'Habfelület felvétele oldalanként (kg/m²)', dGroove: 'Horony (szél. × mély. @ táv., mm)',
    dMesh: 'Infúziós háló (kg/m²)', dPeel: 'Leszakítószövet (kg/m²)', dPot: 'Edény és tömlők (kg)', dWaste: 'Ráhagyás (%)',
    src1: 'csak egy megbízható forrás – próbalapon érdemes mérni', src0: 'nincs számszerű forrás, gyakorlati becslés'
  },
  en: {
    title: 'How much resin to mix?',
    intro: 'Enter the layup: material, area and number of layers. The calculator gives the mass of resin and hardener to mix.',
    process: 'Process', infusion: 'Vacuum infusion', bag: 'Vacuum bagging (wet lay-up)', hand: 'Hand lay-up',
    vfFabric: 'Fabric fibre volume fraction, Vf (%)', vfCsm: 'Mat fibre volume fraction, Vf (%)',
    rhoR: 'Resin density (g/cm³)', mixA: 'Resin (parts by weight)', mixB: 'Hardener (parts by weight)',
    mixNote: '100:30 is only a starting value. Always enter the mix ratio by weight from your own resin datasheet.',
    waste: 'Allowance (%)', pot: 'Resin left in pot and tubing (kg)',
    presets: 'Examples', pOurs: 'Our panel: 4× 300 g/m² glass fabric, 0.12 m², infusion',
    pSandwich: 'Sandwich: 2+2× 450 g/m² glass, 10 mm grooved and perforated PVC, 1 m²',
    pSoric: 'Soric XF 3 mm, 2+2× 300 g/m² glass, 1 m²',
    layers: 'Layup', add: 'Add row', remove: 'Remove row', type: 'Material',
    t_fabric: 'Woven or stitched fabric (NCF)', t_csm: 'Chopped strand mat (CSM)',
    t_soric: 'Infusion core mat (Soric type)', t_foam: 'Foam core (PVC, PET)',
    t_peel: 'Peel ply', t_mesh: 'Infusion flow mesh', t_sheet: 'Uptake from datasheet', t_line: 'Infusion tube',
    fibre: 'Fibre', glass: 'Glass (E)', carbon: 'Carbon', aramid: 'Aramid', basalt: 'Basalt',
    gsm: 'Areal weight (g/m²)', nl: 'Layers', area: 'Area (m²)', thick: 'Thickness (mm)',
    grade: 'Grade', mat: 'Foam', pvc: 'PVC', pet: 'PET', density: 'Density (kg/m³)', finish: 'Surface',
    plain: 'Plain', g1: 'Grooved, one side', g2: 'Grooved, both sides', p: 'Perforated', gp: 'Grooved and perforated', grid: 'Grid-scored on scrim',
    surf: 'Surface uptake per side (kg/m²)', gw: 'Groove width (mm)', gd: 'Groove depth (mm)', gpitch: 'Groove spacing (mm)',
    pd: 'Hole diameter (mm)', pp: 'Hole spacing (mm)', kerf: 'Cut width (mm)', kp: 'Cut spacing (mm)',
    u: 'Resin uptake (kg/m²)', len: 'Length (m)', id: 'Inner diameter (mm)',
    bad: 'Enter a positive number.', badSome: 'Some fields are invalid and are left out of the result.',
    total: 'Resin system to mix', litre: 'litres', resin: 'Resin', hard: 'Hardener',
    lam: 'Finished laminate mass', perM2: 'per m² (over the largest area)',
    fib: 'Fibre content of the fabrics', net: 'In the part and the consumables', wasteL: 'Allowance', potL: 'Pot and tubing',
    rowOut: 'resin', how: 'How it works',
    how1: 'Fabrics and mats: resin follows from the fibre mass. Resin per layer = areal weight × (resin density ÷ fibre density) × (1 − Vf) ÷ Vf. Vf depends on the process: infusion compacts the fibres more, so it needs less resin than hand lay-up. Chopped strand mat always takes more resin.',
    how2: 'Cores: a Soric-type mat takes up resin by thickness, as in the maker’s table (3 mm ≈ 1.4 kg/m²). On a plain foam surface only the cut cells fill (PVC 80 ≈ 0.3 kg/m² per side, more for PET), while grooves, holes and cuts fill with resin; their volume comes from the dimensions you enter.',
    how3: 'Consumables: peel ply and flow mesh soak up resin above the part, and it goes in the bin on demoulding. The tube fills up too.',
    how4: 'Finally the allowance and the resin left in the pot are added, and the total is split into resin and hardener by the weight ratio. Litres use the resin density.',
    defs: 'Defaults, ranges, sources', dVal: 'Default', dRange: 'Range', dSrc: 'Source',
    dVf: 'Fabric Vf, infusion / bagging / hand', dVfC: 'Mat Vf, infusion / bagging / hand', dRho: 'Fibre density glass / carbon / aramid / basalt (g/cm³)',
    dSoric: 'Soric XF uptake 2 / 3 / 4 / 6 mm (kg/m²)', dFoam: 'Foam surface uptake per side (kg/m²)', dGroove: 'Groove (width × depth @ spacing, mm)',
    dMesh: 'Flow mesh (kg/m²)', dPeel: 'Peel ply (kg/m²)', dPot: 'Pot and tubing (kg)', dWaste: 'Allowance (%)',
    src1: 'single reputable source only – worth measuring on a test panel', src0: 'no numerical source, rule of thumb'
  },
  de: {
    title: 'Wie viel Harz anmischen?',
    intro: 'Gib den Lagenaufbau ein: Material, Fläche und Lagenzahl. Der Rechner liefert die Masse von Harz und Härter zum Anmischen.',
    process: 'Verfahren', infusion: 'Vakuuminfusion', bag: 'Vakuumsack (nach Handlaminat)', hand: 'Handlaminieren',
    vfFabric: 'Faservolumengehalt Gewebe, Vf (%)', vfCsm: 'Faservolumengehalt Matte, Vf (%)',
    rhoR: 'Harzdichte (g/cm³)', mixA: 'Harz (Gewichtsteile)', mixB: 'Härter (Gewichtsteile)',
    mixNote: '100:30 ist nur ein Startwert. Trage immer das Mischungsverhältnis nach Gewicht aus dem Datenblatt deines Harzes ein.',
    waste: 'Zuschlag (%)', pot: 'Rest in Becher und Schläuchen (kg)',
    presets: 'Beispiele', pOurs: 'Unsere Platte: 4× 300 g/m² Glasgewebe, 0,12 m², Infusion',
    pSandwich: 'Sandwich: 2+2× 450 g/m² Glas, 10 mm PVC genutet und perforiert, 1 m²',
    pSoric: 'Soric XF 3 mm, 2+2× 300 g/m² Glas, 1 m²',
    layers: 'Lagenaufbau', add: 'Zeile hinzufügen', remove: 'Zeile entfernen', type: 'Material',
    t_fabric: 'Gewebe oder Gelege (NCF)', t_csm: 'Wirrfasermatte (CSM)',
    t_soric: 'Infusions-Kernvlies (Typ Soric)', t_foam: 'Schaumkern (PVC, PET)',
    t_peel: 'Abreißgewebe', t_mesh: 'Fließhilfe (Infusionsnetz)', t_sheet: 'Aufnahme laut Datenblatt', t_line: 'Infusionsschlauch',
    fibre: 'Faser', glass: 'Glas (E)', carbon: 'Kohlenstoff', aramid: 'Aramid', basalt: 'Basalt',
    gsm: 'Flächengewicht (g/m²)', nl: 'Lagen', area: 'Fläche (m²)', thick: 'Dicke (mm)',
    grade: 'Typ', mat: 'Schaum', pvc: 'PVC', pet: 'PET', density: 'Dichte (kg/m³)', finish: 'Oberfläche',
    plain: 'Glatt', g1: 'Genutet, einseitig', g2: 'Genutet, beidseitig', p: 'Perforiert', gp: 'Genutet und perforiert', grid: 'Gitterschnitt auf Trägergewebe',
    surf: 'Oberflächenaufnahme je Seite (kg/m²)', gw: 'Nutbreite (mm)', gd: 'Nuttiefe (mm)', gpitch: 'Nutabstand (mm)',
    pd: 'Lochdurchmesser (mm)', pp: 'Lochabstand (mm)', kerf: 'Schlitzbreite (mm)', kp: 'Schlitzabstand (mm)',
    u: 'Harzaufnahme (kg/m²)', len: 'Länge (m)', id: 'Innendurchmesser (mm)',
    bad: 'Bitte eine positive Zahl eingeben.', badSome: 'Einige Felder sind ungültig und bleiben unberücksichtigt.',
    total: 'Anzumischendes Harzsystem', litre: 'Liter', resin: 'Harz', hard: 'Härter',
    lam: 'Masse des fertigen Laminats', perM2: 'pro m² (bezogen auf die größte Fläche)',
    fib: 'Fasergehalt der Gewebe', net: 'Im Bauteil und in den Hilfsstoffen', wasteL: 'Zuschlag', potL: 'Becher und Schläuche',
    rowOut: 'Harz', how: 'So wird gerechnet',
    how1: 'Gewebe und Matten: Die Harzmenge folgt aus der Fasermasse. Harz je Lage = Flächengewicht × (Harzdichte ÷ Faserdichte) × (1 − Vf) ÷ Vf. Vf hängt vom Verfahren ab: Bei der Infusion wird die Faser stärker verdichtet, es braucht weniger Harz als beim Handlaminieren. Wirrfasermatte nimmt immer mehr Harz auf.',
    how2: 'Kerne: Ein Kernvlies vom Typ Soric nimmt je nach Dicke Harz auf, wie in der Herstellertabelle (3 mm ≈ 1,4 kg/m²). Auf einer glatten Schaumoberfläche füllen sich nur die angeschnittenen Zellen (PVC 80 ≈ 0,3 kg/m² je Seite, PET mehr), Nuten, Bohrungen und Schlitze füllen sich dagegen mit Harz; ihr Volumen ergibt sich aus den eingegebenen Maßen.',
    how3: 'Hilfsstoffe: Abreißgewebe und Fließhilfe saugen sich über dem Bauteil voll, dieses Harz landet beim Entformen im Müll. Auch der Schlauch füllt sich.',
    how4: 'Zum Schluss kommen Zuschlag und Becherrest dazu, dann wird die Summe nach dem Gewichtsverhältnis auf Harz und Härter aufgeteilt. Die Liter sind mit der Harzdichte gerechnet.',
    defs: 'Standardwerte, Bereiche, Quellen', dVal: 'Standard', dRange: 'Bereich', dSrc: 'Quelle',
    dVf: 'Vf Gewebe, Infusion / Vakuumsack / Hand', dVfC: 'Vf Matte, Infusion / Vakuumsack / Hand', dRho: 'Faserdichte Glas / Kohlenstoff / Aramid / Basalt (g/cm³)',
    dSoric: 'Soric XF Aufnahme 2 / 3 / 4 / 6 mm (kg/m²)', dFoam: 'Schaumoberfläche je Seite (kg/m²)', dGroove: 'Nut (Breite × Tiefe @ Abstand, mm)',
    dMesh: 'Fließhilfe (kg/m²)', dPeel: 'Abreißgewebe (kg/m²)', dPot: 'Becher und Schläuche (kg)', dWaste: 'Zuschlag (%)',
    src1: 'nur eine belastbare Quelle – am Probelaminat nachmessen', src0: 'keine Zahlenquelle, Erfahrungswert'
  },
  zh: {
    title: '需要调配多少树脂？',
    intro: '输入铺层：材料、面积和层数。计算器给出需要调配的树脂和固化剂质量。',
    process: '工艺', infusion: '真空导入', bag: '真空袋压（手糊后）', hand: '手糊',
    vfFabric: '织物纤维体积含量 Vf（%）', vfCsm: '短切毡纤维体积含量 Vf（%）',
    rhoR: '树脂密度（g/cm³）', mixA: '树脂（质量份）', mixB: '固化剂（质量份）',
    mixNote: '100:30 只是初始值。请务必填写所用树脂技术数据表中的质量配比。',
    waste: '余量（%）', pot: '残留在杯和管中的树脂（kg）',
    presets: '示例', pOurs: '我们的板：4 层 300 g/m² 玻璃纤维布，0.12 m²，真空导入',
    pSandwich: '夹芯板：上下各 2 层 450 g/m² 玻纤，10 mm 开槽打孔 PVC，1 m²',
    pSoric: 'Soric XF 3 mm，上下各 2 层 300 g/m² 玻纤，1 m²',
    layers: '铺层', add: '添加一行', remove: '删除此行', type: '材料',
    t_fabric: '机织布或多轴向经编布（NCF）', t_csm: '短切毡（CSM）',
    t_soric: '导流芯毡（Soric 类）', t_foam: '泡沫芯材（PVC、PET）',
    t_peel: '脱模布', t_mesh: '导流网', t_sheet: '按技术数据表的吸胶量', t_line: '导入管',
    fibre: '纤维', glass: '玻璃纤维（E）', carbon: '碳纤维', aramid: '芳纶', basalt: '玄武岩纤维',
    gsm: '面密度（g/m²）', nl: '层数', area: '面积（m²）', thick: '厚度（mm）',
    grade: '型号', mat: '泡沫', pvc: 'PVC', pet: 'PET', density: '密度（kg/m³）', finish: '表面',
    plain: '平面', g1: '单面开槽', g2: '双面开槽', p: '打孔', gp: '开槽并打孔', grid: '切块贴网',
    surf: '每面表面吸胶量（kg/m²）', gw: '槽宽（mm）', gd: '槽深（mm）', gpitch: '槽间距（mm）',
    pd: '孔径（mm）', pp: '孔间距（mm）', kerf: '切缝宽度（mm）', kp: '切缝间距（mm）',
    u: '吸胶量（kg/m²）', len: '长度（m）', id: '内径（mm）',
    bad: '请输入正数。', badSome: '部分输入无效，计算时已忽略。',
    total: '需调配的树脂体系', litre: '升', resin: '树脂', hard: '固化剂',
    lam: '成品层合板质量', perM2: '每平方米（按最大面积计）',
    fib: '织物的纤维含量', net: '进入制件及辅材', wasteL: '余量', potL: '杯和管路',
    rowOut: '树脂', how: '计算方法',
    how1: '织物和短切毡：树脂量由纤维质量推算。每层树脂 = 面密度 ×（树脂密度 ÷ 纤维密度）×（1 − Vf）÷ Vf。Vf 取决于工艺：真空导入压实程度更高，所需树脂比手糊少。短切毡总是吸更多树脂。',
    how2: '芯材：Soric 类芯毡按厂家表格随厚度吸胶（3 mm ≈ 1.4 kg/m²）。平面泡沫表面只有被切开的泡孔会吸胶（PVC 80 每面约 0.3 kg/m²，PET 更多），而槽、孔和切缝会被树脂填满，其体积按输入的尺寸计算。',
    how3: '辅材：脱模布和导流网在制件上方被树脂浸透，脱模时随之丢弃。导入管内部也会充满树脂。',
    how4: '最后加上余量和杯中残留，再按质量配比分成树脂和固化剂。升数按树脂密度换算。',
    defs: '默认值、范围与来源', dVal: '默认值', dRange: '范围', dSrc: '来源',
    dVf: '织物 Vf：真空导入 / 真空袋压 / 手糊', dVfC: '短切毡 Vf：真空导入 / 真空袋压 / 手糊', dRho: '纤维密度 玻纤 / 碳纤 / 芳纶 / 玄武岩（g/cm³）',
    dSoric: 'Soric XF 吸胶量 2 / 3 / 4 / 6 mm（kg/m²）', dFoam: '泡沫每面表面吸胶量（kg/m²）', dGroove: '槽（宽 × 深 @ 间距，mm）',
    dMesh: '导流网（kg/m²）', dPeel: '脱模布（kg/m²）', dPot: '杯和管路（kg）', dWaste: '余量（%）',
    src1: '仅有一个可靠来源，建议用试板实测', src0: '无数值来源，经验值'
  }
};

/* ---------- Felület (csak böngészőben) ---------- */
const TYPES = ['fabric', 'csm', 'soric', 'foam', 'sheet', 'peel', 'mesh', 'line'];
const FIELDS = {
  fabric: ['gsm', 'nl', 'area'], csm: ['gsm', 'nl', 'area'], soric: ['t', 'nl', 'area'],
  foam: ['t', 'density', 'nl', 'area', 'surf'], sheet: ['u', 'nl', 'area'],
  peel: ['u', 'nl', 'area'], mesh: ['u', 'nl', 'area'], line: ['len', 'id']
};
const LABEL = { t: 'thick', nl: 'nl', len: 'len', id: 'id' };

function newRow(type, o = {}) {
  const b = { type, nl: '1', area: '1' };
  if (type === 'fabric') Object.assign(b, { fibre: 'glass', gsm: '300' });
  if (type === 'csm') Object.assign(b, { gsm: '450' });
  if (type === 'soric') Object.assign(b, { grade: 'XF', t: '3' });
  if (type === 'foam') Object.assign(b, { mat: 'pvc', t: '10', density: '80', finish: 'plain', surf: String(DEF.foamSurf.pvc),
    gw: String(DEF.groove.w), gd: String(DEF.groove.d), gpitch: String(DEF.groove.pitch),
    pd: String(DEF.perf.d), pp: String(DEF.perf.pitch), kerf: String(DEF.grid.kerf), kp: String(DEF.grid.pitch) });
  if (type === 'sheet') Object.assign(b, { u: '1' });
  if (type === 'peel') Object.assign(b, { u: String(DEF.peel) });
  if (type === 'mesh') Object.assign(b, { u: String(DEF.mesh) });
  if (type === 'line') Object.assign(b, { len: '2', id: String(DEF.lineId) });
  return Object.assign(b, o);
}

const PRESETS = {
  pOurs: () => ({ process: 'infusion', rows: [
    newRow('fabric', { gsm: '300', nl: '4', area: '0.12' }),
    newRow('peel', { area: '0.12' }), newRow('mesh', { area: '0.12' }) ] }),
  pSandwich: () => ({ process: 'infusion', rows: [
    newRow('fabric', { gsm: '450', nl: '2' }), newRow('foam', { finish: 'gp' }),
    newRow('fabric', { gsm: '450', nl: '2' }), newRow('peel'), newRow('mesh') ] }),
  pSoric: () => ({ process: 'infusion', rows: [
    newRow('fabric', { gsm: '300', nl: '2' }), newRow('soric'),
    newRow('fabric', { gsm: '300', nl: '2' }), newRow('peel'), newRow('mesh') ] })
};

function freshState() {
  const p = PRESETS.pOurs();
  return { process: p.process, vfFabric: String(DEF.vf.infusion.fabric), vfCsm: String(DEF.vf.infusion.csm),
    rhoR: String(DEF.rhoR), mixA: String(DEF.mix[0]), mixB: String(DEF.mix[1]),
    waste: String(DEF.waste), pot: String(DEF.pot), rows: p.rows };
}

const num = s => { const v = Number(String(s).trim().replace(/\s/g, '').replace(',', '.')); return String(s).trim() === '' ? NaN : v; };
const LIMITS = { vfFabric: [5, 85], vfCsm: [5, 85], rhoR: [0.5, 3], mixA: [0.001, 1e6], mixB: [0, 1e6] };
function valid(k, s) {
  const v = num(s);
  if (!Number.isFinite(v) || v < 0) return false;
  const l = LIMITS[k]; if (l && (v < l[0] || v > l[1])) return false;
  if (['gpitch', 'pp', 'kp', 't'].includes(k) && v === 0) return false;
  return true;
}

const CSS = `
#gyanta-kalk{--gk-gap:clamp(12px,2vw,20px);color:var(--ink);font-family:var(--display)}
.gk{display:grid;gap:var(--gk-gap);max-width:100%}
.gk *{box-sizing:border-box;min-width:0}
.gk h3{font:700 var(--s3,22px)/1.2 var(--display);margin:0}
.gk h4{font:650 var(--s2,17px)/1.3 var(--display);margin:0 0 8px}
.gk p{margin:0;max-width:68ch}
.gk-panel{background:var(--raised);padding:clamp(14px,2.4vw,24px);border-radius:2px;display:grid;gap:14px}
.gk-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px 14px;align-items:end}
.gk label{display:grid;gap:4px;font:500 var(--s1,14px)/1.3 var(--display);color:var(--muted)}
.gk input,.gk select{font:500 16px/1.2 var(--display);color:var(--ink);background:var(--sunk);border:0;border-radius:2px;padding:10px;width:100%;font-variant-numeric:tabular-nums}
.gk input[aria-invalid=true]{outline:2px solid #c84b4b;outline-offset:-2px}
.gk input:focus-visible,.gk select:focus-visible,.gk button:focus-visible,.gk summary:focus-visible{outline:2px solid var(--resin);outline-offset:2px}
.gk button{font:600 var(--s1,14px)/1.2 var(--display);border:0;border-radius:2px;padding:10px 14px;cursor:pointer;background:var(--sunk);color:var(--ink);text-align:left}
.gk button:hover{background:var(--ink);color:var(--ground)}
.gk button[aria-pressed=true]{background:var(--resin);color:var(--on-resin)}
.gk-seg{display:flex;flex-wrap:wrap;gap:6px}
.gk-note{font-size:var(--s1,14px);color:var(--muted)}
.gk-row{background:var(--raised);border-radius:2px;padding:14px;display:grid;gap:12px;border-left:6px solid var(--sunk)}
.gk-row[data-cat=lam]{border-left-color:var(--resin)}
.gk-row-head{display:flex;flex-wrap:wrap;gap:10px;align-items:end}
.gk-row-head label{flex:1 1 220px}
.gk-row-out{font:600 var(--s1,14px)/1.3 var(--display);color:var(--ink);font-variant-numeric:tabular-nums}
.gk-row-out small{color:var(--muted);font-weight:500}
.gk-res{background:var(--ink);color:var(--ground);border-radius:2px;padding:clamp(16px,3vw,28px);display:grid;gap:14px}
.gk-big{font:750 clamp(34px,6vw,56px)/1 var(--display);font-variant-numeric:tabular-nums;letter-spacing:-.01em}
.gk-big span{font-size:.45em;font-weight:600;margin-left:.25em}
.gk-split{display:flex;flex-wrap:wrap;gap:8px 28px;font-variant-numeric:tabular-nums}
.gk-split b{display:block;font-size:var(--s3,22px)}
.gk-swatch{display:inline-block;width:10px;height:10px;margin-right:6px;background:var(--resin);border-radius:2px}
.gk-res dl{display:grid;grid-template-columns:1fr auto;gap:4px 16px;margin:0;font-size:var(--s1,14px)}
.gk-res dd{margin:0;text-align:right;font-variant-numeric:tabular-nums}
.gk-res .gk-note{color:inherit;opacity:.8}
.gk details{background:var(--raised);border-radius:2px;padding:14px}
.gk summary{cursor:pointer;font-weight:650}
.gk-how{display:grid;gap:10px;margin-top:12px}
.gk-tw{overflow-x:auto;margin-top:12px}
.gk table{border-collapse:collapse;font-size:var(--s1,14px);width:100%;min-width:520px}
.gk th,.gk td{text-align:left;padding:7px 10px 7px 0;vertical-align:top}
.gk tbody tr:nth-child(odd){background:var(--sunk)}
.gk td:first-child,.gk th:first-child{padding-left:8px}
.gk-add{justify-self:start;background:var(--resin)!important;color:var(--on-resin)!important}
.gk-rm{flex:none}
@media(max-width:560px){.gk-grid{grid-template-columns:1fr 1fr}.gk-split{gap:8px 18px}}
`;

export function mount(el) {
  if (!el || el.__gk) return;
  el.__gk = true;
  if (!document.getElementById('gk-css')) {
    const st = document.createElement('style'); st.id = 'gk-css'; st.textContent = CSS; document.head.appendChild(st);
  }
  const state = freshState();
  let lang = 'hu';
  const T = k => (S[lang] && S[lang][k]) ?? S.hu[k] ?? k;
  const f = (v, d = 2) => Number(v).toLocaleString(LOC[lang], { minimumFractionDigits: d, maximumFractionDigits: d });
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
  const showNum = s => { const v = num(s); return Number.isFinite(v) ? v.toLocaleString(LOC[lang], { maximumFractionDigits: 6, useGrouping: false }) : s; };

  function field(key, val, idx, lbl) {
    const ok = valid(key, val);
    return `<label>${esc(T(lbl || LABEL[key] || key))}<input inputmode="decimal" autocomplete="off" data-k="${key}" data-i="${idx}" value="${esc(showNum(val))}" aria-invalid="${!ok}"></label>`;
  }
  function select(key, val, opts, idx, lbl) {
    return `<label>${esc(T(lbl || key))}<select data-k="${key}" data-i="${idx}">${opts.map(o =>
      `<option value="${o}"${o === val ? ' selected' : ''}>${esc(T(o) === o && /^[A-Z]/.test(o) ? o : T(o))}</option>`).join('')}</select></label>`;
  }
  function rowHtml(r, i) {
    const cat = ['peel', 'mesh', 'line'].includes(r.type) ? 'aux' : 'lam';
    let extra = '';
    if (r.type === 'fabric') extra += select('fibre', r.fibre, ['glass', 'carbon', 'aramid', 'basalt'], i);
    if (r.type === 'soric') extra += select('grade', r.grade, ['XF', 'TF', 'LRC'], i);
    if (r.type === 'foam') extra += select('mat', r.mat, ['pvc', 'pet'], i) + select('finish', r.finish, ['plain', 'g1', 'g2', 'p', 'gp', 'grid'], i);
    let fields = FIELDS[r.type].map(k => field(k, r[k], i)).join('');
    if (r.type === 'foam') {
      if (['g1', 'g2', 'gp'].includes(r.finish)) fields += ['gw', 'gd', 'gpitch'].map(k => field(k, r[k], i)).join('');
      if (['p', 'gp'].includes(r.finish)) fields += ['pd', 'pp'].map(k => field(k, r[k], i)).join('');
      if (r.finish === 'grid') fields += ['kerf', 'kp'].map(k => field(k, r[k], i)).join('');
    }
    return `<li class="gk-row" data-cat="${cat}">
      <div class="gk-row-head">${select('type', r.type, TYPES, i).replace(/>(\w+)<\/option>/g, (m, k) => '>' + esc(T('t_' + k)) + '</option>')}
      <button type="button" class="gk-rm" data-rm="${i}" aria-label="${esc(T('remove'))} (${i + 1})">${esc(T('remove'))}</button></div>
      <div class="gk-grid">${extra}${fields}</div>
      <div class="gk-row-out" data-out="${i}"></div></li>`;
  }
  function defsTable() {
    const L = DEF.vfRange, v = DEF.vf;
    const q = (a, d = 2) => a.map(x => f(x, d)).join(' / ');
    const rg = (a, b, d = 2) => `${f(a, d)}–${f(b, d)}`;
    const rows = [
      ['dVf', q([v.infusion.fabric, v.bag.fabric, v.hand.fabric], 0), [L.infusion, L.bag, L.hand].map(x => rg(x.fabric[0], x.fabric[1], 0)).join(' / '), 'JEC Composites Mag. 35 (2007): infusion Vf 0.5, hand 0.3; Gurit Guide to Composites (hand 30–40 %); bagging: {1}'],
      ['dVfC', q([v.infusion.csm, v.bag.csm, v.hand.csm], 1), [L.infusion, L.bag, L.hand].map(x => rg(x.csm[0], x.csm[1], 0)).join(' / '), 'Saertex SAERcore 2025 (17.5 / 33 %); fram.nl (hand ≈ 1/3 glass by weight); bagging: {1}'],
      ['dRho', q([2.56, 1.76, 1.44, 2.65]), `${rg(2.54, 2.6)} / ${rg(1.75, 1.95)} / ${rg(1.44, 1.45)} / ${rg(2.63, 2.7)}`, 'Gurit Guide; fibre-density tables; basalt: Mafic TDS 2.63, GBF 2.65'],
      ['rhoR', f(DEF.rhoR), rg(1.1, 1.2), 'Gurit Guide; epoxy TDS'],
      ['dSoric', q([1.0, 1.4, 1.9, 2.8], 1), `≈ ${rg(0.47, 0.67)} / mm`, 'Lantor Soric XF TDS v2.2; ACP Composites'],
      ['dFoam', `${f(DEF.foamSurf.pvc)} (PVC) / ${f(DEF.foamSurf.pet)} (PET)`, rg(0, 0.5), 'Gurit Structural Core Processing Guide 2024, Table 4 (÷ 2 sides); boatdesign.net (H80 ≈ 0.3); {1}'],
      ['dGroove', `${f(1.2, 1)} × ${f(2.5, 1)} @ 20`, '—', 'Airex GP (Univ. Plymouth FPCM-10); Gurit: 2 × 2 mm; {1}'],
      ['dMesh', f(DEF.mesh), rg(0.35, 0.7), 'Diatex via R&G; Easy Composites FM100'],
      ['dPeel', f(DEF.peel), rg(0.03, 0.1), 'Explore Composites (30–50 g/m²); Directeck WS877 (83 g/m²)'],
      ['dPot', f(DEF.pot), f(0.1), 'Easy Composites; Univ. Texas wiki'],
      ['dWaste', f(DEF.waste, 0), rg(5, 20, 0), '{0}']
    ];
    return `<div class="gk-tw"><table><thead><tr><th scope="col"></th><th scope="col">${esc(T('dVal'))}</th><th scope="col">${esc(T('dRange'))}</th><th scope="col">${esc(T('dSrc'))}</th></tr></thead><tbody>${
      rows.map(r => `<tr><th scope="row">${esc(T(r[0]))}</th><td>${r[1]}</td><td>${r[2]}</td><td>${esc(r[3].replace('{1}', T('src1')).replace('{0}', T('src0')))}</td></tr>`).join('')}</tbody></table></div>`;
  }

  function render() {
    lang = (document.documentElement.lang || 'hu').slice(0, 2).toLowerCase();
    if (!S[lang]) lang = 'hu';
    const g = state;
    el.innerHTML = `<div class="gk" lang="${lang}">
      <h2>${esc(T('title'))}</h2><p>${esc(T('intro'))}</p>
      <div class="gk-panel">
        <div><h4 id="gk-proc">${esc(T('process'))}</h4><div class="gk-seg" role="group" aria-labelledby="gk-proc">${
          ['infusion', 'bag', 'hand'].map(p => `<button type="button" data-proc="${p}" aria-pressed="${g.process === p}">${esc(T(p))}</button>`).join('')}</div></div>
        <div class="gk-grid">${field('vfFabric', g.vfFabric, 'g')}${field('vfCsm', g.vfCsm, 'g')}${field('rhoR', g.rhoR, 'g')}
          ${field('mixA', g.mixA, 'g')}${field('mixB', g.mixB, 'g')}${field('waste', g.waste, 'g')}${field('pot', g.pot, 'g')}</div>
        <p class="gk-note">${esc(T('mixNote'))}</p>
      </div>
      <div><h4 id="gk-pre">${esc(T('presets'))}</h4><div class="gk-seg" role="group" aria-labelledby="gk-pre">${
        Object.keys(PRESETS).map(k => `<button type="button" data-preset="${k}">${esc(T(k))}</button>`).join('')}</div></div>
      <div><h4>${esc(T('layers'))}</h4><ul style="list-style:none;margin:0;padding:0;display:grid;gap:10px">${g.rows.map(rowHtml).join('')}</ul></div>
      <button type="button" class="gk-add" data-add>${esc(T('add'))}</button>
      <div class="gk-res" aria-live="polite" data-res></div>
      <details><summary>${esc(T('how'))}</summary><div class="gk-how">${['how1', 'how2', 'how3', 'how4'].map(k => `<p>${esc(T(k))}</p>`).join('')}</div></details>
      <details><summary>${esc(T('defs'))}</summary>${defsTable()}</details>
    </div>`;
    update();
  }

  function numbers() {
    let bad = false;
    const n = (k, s) => { if (!valid(k, s)) { bad = true; return null; } return num(s); };
    const g = { rhoR: n('rhoR', state.rhoR), vfFabric: n('vfFabric', state.vfFabric), vfCsm: n('vfCsm', state.vfCsm),
      waste: n('waste', state.waste), pot: n('pot', state.pot), mixA: n('mixA', state.mixA), mixB: n('mixB', state.mixB) };
    const fb = { rhoR: DEF.rhoR, vfFabric: DEF.vf[state.process].fabric, vfCsm: DEF.vf[state.process].csm, waste: 0, pot: 0, mixA: 100, mixB: 0 };
    for (const k in g) if (g[k] === null) g[k] = fb[k];
    const rows = state.rows.map(r => {
      const o = { type: r.type, fibre: r.fibre, grade: r.grade, finish: r.finish };
      let rowBad = false;
      for (const k of ['gsm', 'nl', 'area', 't', 'density', 'surf', 'gw', 'gd', 'gpitch', 'pd', 'pp', 'kerf', 'kp', 'u', 'len', 'id']) {
        if (r[k] === undefined) continue;
        const v = n(k, r[k]); if (v === null) rowBad = true; o[k] = v;
      }
      o.layers = o.nl;
      return rowBad ? { type: 'skip' } : o;
    });
    return { g, rows, bad };
  }

  function update() {
    const { g, rows, bad } = numbers();
    const r = compute(g, rows);
    r.per.forEach((p, i) => {
      const o = el.querySelector(`[data-out="${i}"]`); if (!o) return;
      o.innerHTML = rows[i].type === 'skip' ? `<small>${esc(T('bad'))}</small>` : `≈ ${f(p.resin, 3)} kg <small>${esc(T('rowOut'))}</small>`;
    });
    const box = el.querySelector('[data-res]');
    const pct = v => v == null ? '—' : f(v * 100, 0) + ' %';
    box.innerHTML = `
      <div>${esc(T('total'))}</div>
      <div class="gk-big">${f(r.total, 3)}<span>kg</span></div>
      <div class="gk-note">≈ ${f(r.litres, 2)} ${esc(T('litre'))}</div>
      <div class="gk-split"><div><span class="gk-swatch"></span>${esc(T('resin'))}<b>${f(r.resin, 3)} kg</b></div>
        <div><span class="gk-swatch" style="background:var(--ground)"></span>${esc(T('hard'))}<b>${f(r.hardener, 3)} kg</b></div></div>
      <dl>
        <dt>${esc(T('net'))}</dt><dd>${f(r.net, 3)} kg</dd>
        <dt>${esc(T('wasteL'))} (${f(g.waste, 0)} %)</dt><dd>${f(r.wasteKg, 3)} kg</dd>
        <dt>${esc(T('potL'))}</dt><dd>${f(g.pot, 3)} kg</dd>
        <dt>${esc(T('lam'))}</dt><dd>${f(r.laminate, 3)} kg</dd>
        <dt>${esc(T('lam'))}, ${esc(T('perM2'))}</dt><dd>${f(r.laminatePerM2, 2)} kg/m²</dd>
        <dt>${esc(T('fib'))}</dt><dd>Vf ${pct(r.vf)} · Wf ${pct(r.wf)}</dd>
      </dl>${bad ? `<div class="gk-note">${esc(T('badSome'))}</div>` : ''}`;
  }

  el.addEventListener('input', e => {
    const t = e.target; if (t.tagName !== 'INPUT') return;
    const k = t.dataset.k, i = t.dataset.i;
    if (i === 'g') state[k] = t.value; else state.rows[+i][k] = t.value;
    t.setAttribute('aria-invalid', String(!valid(k, t.value)));
    update();
  });
  el.addEventListener('change', e => {
    const t = e.target; if (t.tagName !== 'SELECT') return;
    const k = t.dataset.k, i = +t.dataset.i;
    if (k === 'type') state.rows[i] = newRow(t.value, { nl: state.rows[i].nl, area: state.rows[i].area ?? '1' });
    else {
      state.rows[i][k] = t.value;
      if (k === 'mat') { state.rows[i].density = String(DEF.foamDensity[t.value]); state.rows[i].surf = String(DEF.foamSurf[t.value]); }
    }
    render();
    const again = el.querySelector(`select[data-k="${k}"][data-i="${i}"]`); if (again) again.focus();
  });
  el.addEventListener('click', e => {
    const b = e.target.closest('button'); if (!b) return;
    if (b.dataset.proc) {
      state.process = b.dataset.proc;
      state.vfFabric = String(DEF.vf[b.dataset.proc].fabric); state.vfCsm = String(DEF.vf[b.dataset.proc].csm);
      render(); el.querySelector(`[data-proc="${b.dataset.proc}"]`).focus();
    } else if (b.dataset.preset) {
      const p = PRESETS[b.dataset.preset]();
      Object.assign(state, { process: p.process, rows: p.rows, vfFabric: String(DEF.vf[p.process].fabric), vfCsm: String(DEF.vf[p.process].csm) });
      render(); el.querySelector(`[data-preset="${b.dataset.preset}"]`).focus();
    } else if (b.dataset.rm !== undefined) {
      state.rows.splice(+b.dataset.rm, 1); render();
      const nb = el.querySelector('[data-rm]') || el.querySelector('[data-add]'); nb.focus();
    } else if (b.hasAttribute('data-add')) {
      state.rows.push(newRow('fabric')); render();
      const sels = el.querySelectorAll('select[data-k="type"]'); sels[sels.length - 1].focus();
    }
  });
  document.addEventListener('langchange', render);
  render();
}

if (typeof document !== 'undefined') {
  const go = () => mount(document.getElementById('gyanta-kalk'));
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', go); else go();
}
