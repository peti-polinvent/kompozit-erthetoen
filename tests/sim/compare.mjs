// Runner: computes JS results (assets/sim/clt.js), then lets the independent Python reference compare.
// Usage: node tests/sim/compare.mjs      (needs `python` with numpy on PATH; override with PYTHON env var)
import { writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { MATERIALS, DEFAULT_PANEL, analyze, loadForDeflection } from '../../assets/sim/clt.js';

const here = dirname(fileURLToPath(import.meta.url));
// test-only materials
MATERIALS['t-iso'] = { id: 't-iso', kind: 'iso', E1: 70, E2: 70, G12: 70 / 2.6, nu12: 0.3, G13: 70 / 2.6, G23: 70 / 2.6, Xt: 1, Xc: 1, Yt: 1, Yc: 1, S: 1, t: 4, rho: 1 };
MATERIALS['t-reddy'] = { id: 't-reddy', kind: 'ud', E1: 25, E2: 1, G12: 0.5, nu12: 0.25, G13: 0.5, G23: 0.2, Xt: 1, Xc: 1, Yt: 1, Yc: 1, S: 1, t: 0.25, rho: 1 };

const analytic = [];
{
  const r = analyze([{ mat: 't-iso', angle: 0 }], { a: 400, b: 400, load: { type: 'pressure', q: 1 } });
  const Dz = 70e3 * 64 / (12 * 0.91);
  analytic.push({ name: 'iso a/h=100 w/w_closed', value: r.wMax / (0.00406 * 1e-3 * 400 ** 4 / Dz), expected: 1 });
  for (const [ah, exp] of [[100, 0.6842], [10, 1.0219]]) {
    const r2 = analyze([0, 90, 90, 0].map((t) => ({ mat: 't-reddy', angle: t })), { a: ah, b: ah, load: { type: 'pressure', q: 1 } });
    analytic.push({ name: `Reddy [0/90/90/0] a/h=${ah} wbar`, value: r2.wMax * 1e3 * 1 / (1e-3 * ah ** 4) * 100, expected: exp });
  }
}

// deterministic random laminates
let seed = 12345;
const rnd = () => ((seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648);
const ids = ['gl-woven', 'gl-ud', 'gl-biax', 'gl-csm', 'cf-woven', 'cf-ud', 'ar-woven'];
const angles = [0, 90, 45, -45, 30, -60];
const pick = (arr) => arr[Math.floor(rnd() * arr.length)];
const lams = [
  ['reference 4xgl-woven [0/45/45/0]', [0, 45, 45, 0].map((t) => ({ mat: 'gl-woven', angle: t }))],
];
for (let k = 0; k < 3; k++) {
  const half = Array.from({ length: 2 + Math.floor(rnd() * 4) }, () => ({ mat: pick(ids), angle: pick(angles) }));
  lams.push([`random sym #${k + 1}`, [...half, ...half.slice().reverse()]]);
}
lams.push(['random unsym', Array.from({ length: 5 }, () => ({ mat: pick(ids), angle: pick(angles) }))]);
lams.push(['sandwich gl-woven/core10/gl-woven', [{ mat: 'gl-woven', angle: 0 }, { mat: 'gl-biax', angle: 0 }, { mat: 'core-pet', angle: 0, t: 10 }, { mat: 'gl-biax', angle: 0 }, { mat: 'gl-woven', angle: 0 }]]);

const cases = [];
for (const [name, plies] of lams) for (const load of [{ type: 'pressure', q: 10 }, { type: 'patch', P: 784.8, c: 60, d: 60 }]) {
  const opts = { ...DEFAULT_PANEL, load, terms: 31, grid: 21 };
  const r = analyze(plies, opts);
  const L = load.type === 'patch' ? load.P : load.q;
  cases.push({ name: `${name} ${load.type}`, plies, a: opts.a, b: opts.b, load, loadMag: L,
    js: { wMax: r.wMax, Ex: r.inPlane.Ex, Ey: r.inPlane.Ey, D11: r.D[0][0], fpf: r.fpf.load } });
}

// reference numbers + timing
const ref = lams[0][1];
for (const load of [{ type: 'pressure', q: 10 }, { type: 'patch', P: 784.8, c: 60, d: 60 }]) {
  const r = analyze(ref, { load });
  console.log(`REF ${load.type}: h=${r.h.toFixed(3)} mm, m=${r.massPerArea.toFixed(3)} kg/m2 (${r.panelMass.toFixed(3)} kg), wMax=${r.wMax.toFixed(2)} mm, ` +
    `FPF=${r.fpf.load.toFixed(2)} (${r.fpf.mode}, ply ${r.fpf.plyIndex}), load@5mm=${loadForDeflection(ref, { load }, 5).toFixed(2)}, Ex=${r.inPlane.Ex.toFixed(2)} GPa; warnings=${r.warnings.length}`);
}
const big = Array.from({ length: 20 }, (_, i) => ({ mat: i % 3 ? 'cf-ud' : 'gl-biax', angle: (i * 37) % 180 - 90 }));
analyze(big, { load: { type: 'patch', P: 500 } });
let t0 = performance.now(); for (let i = 0; i < 20; i++) analyze(big, { load: { type: 'patch', P: 500 } });
console.log(`timing: analyze(20 plies, 31x31, 21x21) = ${((performance.now() - t0) / 20).toFixed(2)} ms`);

const file = join(tmpdir(), 'clt_compare.json');
writeFileSync(file, JSON.stringify({ materials: MATERIALS, cases, analytic }));
const py = spawnSync(process.env.PYTHON || 'python', ['-I', join(here, 'reference.py'), '--compare', file], { stdio: 'inherit' });
process.exit(py.status ?? 1);
