// Kézzel számolt referenciaesetek a gyantakalkulátor compute() függvényéhez.
// Futtatás: node tests/calc/resin_check.mjs
import { compute, rowResin } from '../../assets/calc/resin.js';

let fail = 0, n = 0;
function eq(name, got, want, tol = 1e-6) {
  n++;
  const ok = Math.abs(got - want) <= tol;
  if (!ok) fail++;
  console.log(`${ok ? 'OK  ' : 'FAIL'} ${name}: ${got.toFixed(6)} (várt ${want.toFixed(6)})`);
}
const G = (o = {}) => Object.assign({ rhoR: 1.15, vfFabric: 50, vfCsm: 30, waste: 0, pot: 0, mixA: 100, mixB: 30 }, o);

// 1) 1 réteg 300 g/m² üvegszövet, 1 m², Vf 50 %: 0,3 · 1,15/2,56 · 0,5/0,5 = 0,134765625 kg
eq('üvegszövet 300, Vf 50', rowResin({ type: 'fabric', fibre: 'glass', gsm: 300, layers: 1, area: 1 }, G()).resin, 0.134765625);

// 2) CSM 450, kézi, Vf 17,5 %: 0,45 · 1,15/2,56 · 0,825/0,175 = 0,952985491 kg
eq('CSM 450 kézi', rowResin({ type: 'csm', gsm: 450, layers: 1, area: 1 }, G({ vfCsm: 17.5 })).resin, 0.45 * 1.15 / 2.56 * 0.825 / 0.175);
eq('CSM 450 kézi (szám)', rowResin({ type: 'csm', gsm: 450, layers: 1, area: 1 }, G({ vfCsm: 17.5 })).resin, 0.952985491, 1e-8);

// 3) Soric XF 3 mm, 2 m²: 1,4 · 2 = 2,8 kg; XF 2,5 mm interpolálva 1,2 kg/m²
eq('Soric XF 3, 2 m²', rowResin({ type: 'soric', grade: 'XF', t: 3, layers: 1, area: 2 }, G()).resin, 2.8);
eq('Soric XF 2,5 interp.', rowResin({ type: 'soric', grade: 'XF', t: 2.5, layers: 1, area: 1 }, G()).resin, 1.2);

// 4) PVC 10 mm, hornyolt+perforált (1,2×2,5 @20 mm, két oldal, keresztben; Ø2 @50 mm), felület 0,15/oldal
//    0,30 + 0,6 mm·1,15 = 0,69 + π·1²·10/2500 mm = 0,0125664 mm → 0,0144513 → 1,0044513 kg/m²
const foam = { type: 'foam', finish: 'gp', t: 10, density: 80, surf: 0.15, gw: 1.2, gd: 2.5, gpitch: 20, pd: 2, pp: 50, layers: 1, area: 1 };
eq('PVC 10 GP', rowResin(foam, G()).resin, 0.3 + 0.69 + Math.PI * 10 / 2500 / 1000 * 1150);
eq('PVC 10 GP (szám)', rowResin(foam, G()).resin, 1.0044513, 1e-6);

// 5) Szendvics 1 m²: 450 üveg | PVC 10 sima | 450 üveg + peel 0,1 + háló 0,6, ráhagyás 10 %, edény 0,1, 100:30
//    szövet 2·0,2021484 = 0,4042969; mag 0,30; nettó 1,4042969; ×1,1 = 1,5447266; +0,1 = 1,6447266
//    edző = 1,6447266·30/130 = 0,3795523; laminát = 0,9 + 0,4042969 + 0,3 + 0,8 = 2,4042969; Vf = 0,5
const sw = compute(G({ waste: 10, pot: 0.1 }), [
  { type: 'fabric', fibre: 'glass', gsm: 450, layers: 1, area: 1 },
  { type: 'foam', finish: 'plain', t: 10, density: 80, surf: 0.15, layers: 1, area: 1 },
  { type: 'fabric', fibre: 'glass', gsm: 450, layers: 1, area: 1 },
  { type: 'peel', u: 0.1, layers: 1, area: 1 },
  { type: 'mesh', u: 0.6, layers: 1, area: 1 }
]);
eq('szendvics nettó', sw.net, 1.404296875);
eq('szendvics összesen', sw.total, 1.6447265625);
eq('szendvics edző', sw.hardener, 1.6447265625 * 30 / 130);
eq('szendvics gyanta', sw.resin, 1.6447265625 * 100 / 130);
eq('szendvics laminát', sw.laminate, 2.404296875);
eq('szendvics Vf', sw.vf, 0.5);
eq('szendvics Wf', sw.wf, 0.9 / 1.304296875);

// 6) Infúziós cső 2 m, belső Ø 10 mm: π·0,005²·2·1150 = 0,1806416 kg
eq('cső 2 m Ø10', rowResin({ type: 'line', len: 2, id: 10 }, G()).resin, Math.PI * 0.005 ** 2 * 2 * 1150);

// 7) "A mi lapunk": 4×300 g/m² üveg, 0,12 m², infúzió (Vf 48 %), peel + háló 0,12 m², 10 %, 0,1 kg
//    szál 0,144 kg; gyanta 0,144·1,15/2,56·0,52/0,48 = 0,0700781; +0,012 +0,072 = 0,1540781; ×1,1 +0,1 = 0,2694859
const ours = compute(G({ vfFabric: 48, waste: 10, pot: 0.1 }), [
  { type: 'fabric', fibre: 'glass', gsm: 300, layers: 4, area: 0.12 },
  { type: 'peel', u: 0.1, layers: 1, area: 0.12 },
  { type: 'mesh', u: 0.6, layers: 1, area: 0.12 }
]);
eq('a mi lapunk összesen', ours.total, (0.144 * 1.15 / 2.56 * 0.52 / 0.48 + 0.084) * 1.1 + 0.1);
eq('a mi lapunk (szám)', ours.total, 0.2694859, 1e-6);

// 8) Szén 200 g/m², Vf 50 %: 0,2 · 1,15/1,76 = 0,1306818 kg (Wf ≈ 60,5 %, egyezik az Easy Composites 60:40-nel)
eq('szénszövet 200', rowResin({ type: 'fabric', fibre: 'carbon', gsm: 200, layers: 1, area: 1 }, G()).resin, 0.2 * 1.15 / 1.76);

console.log(`\n${n - fail}/${n} rendben`);
process.exit(fail ? 1 : 0);
