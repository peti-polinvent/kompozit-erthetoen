// Laminált lemez számítómotor – CLT (ABD) + FSDT Navier-sor, Tsai-Wu első rétegtörés.
// ES-modul, DOM és függőség nélkül. Bemenet: mm, GPa, MPa, kPa, N. Belül: N, mm, MPa.
// Specifikáció: .claude/skills/laminalt-lemez-szimulacio/SKILL.md

export const MATERIALS = {
  'gl-woven': { id: 'gl-woven', name: 'Üvegszövet 300 (vászon/köper)', kind: 'woven', E1: 21, E2: 21, G12: 3.8, nu12: 0.13, G13: 3.0, G23: 3.0, Xt: 350, Xc: 300, Yt: 350, Yc: 300, S: 55, t: 0.23, areal: 300, rho: 1.90, color: '#d9e4ea', note: 'Mindkét irányban egyforma, olcsó, jól infúzionálható.' },
  'gl-ud': { id: 'gl-ud', name: 'UD üveg 300', kind: 'ud', E1: 40, E2: 10, G12: 3.8, nu12: 0.28, G13: 3.8, G23: 3.4, Xt: 900, Xc: 600, Yt: 35, Yc: 120, S: 55, t: 0.23, areal: 300, rho: 1.95, color: '#c8dbe6', note: 'Csak szálirányban erős és merev.' },
  'gl-biax': { id: 'gl-biax', name: 'Üveg biax ±45° 600 (varrott)', kind: 'biax', E1: 40, E2: 10, G12: 3.8, nu12: 0.28, G13: 3.8, G23: 3.4, Xt: 900, Xc: 600, Yt: 35, Yc: 120, S: 55, t: 0.46, areal: 600, rho: 1.95, color: '#b7cfdd', note: 'Két UD altréteg ±45°-ban: a nyírást és a csavarást viszi.' },
  'gl-csm': { id: 'gl-csm', name: 'Üvegpaplan (CSM) 450', kind: 'mat', E1: 7.5, E2: 7.5, G12: 2.8, nu12: 0.32, G13: 2.8, G23: 2.8, Xt: 95, Xc: 140, Yt: 95, Yc: 140, S: 65, t: 0.60, areal: 450, rho: 1.50, color: '#eef1e6', note: 'Minden irányban egyforma, de gyengébb; infúzióhoz porkötésű változat kell.' },
  'cf-woven': { id: 'cf-woven', name: 'Szénszövet 200 (köper)', kind: 'woven', E1: 55, E2: 55, G12: 4.0, nu12: 0.05, G13: 3.5, G23: 3.5, Xt: 600, Xc: 500, Yt: 600, Yc: 500, S: 80, t: 0.22, areal: 200, rho: 1.50, color: '#2b2b2e', note: 'Merev és könnyű, de drága.' },
  'cf-ud': { id: 'cf-ud', name: 'UD szén 300', kind: 'ud', E1: 120, E2: 8, G12: 4.2, nu12: 0.30, G13: 4.2, G23: 3.0, Xt: 1800, Xc: 1100, Yt: 45, Yc: 180, S: 70, t: 0.30, areal: 300, rho: 1.55, color: '#3a3a3f', note: 'Szálirányban kiemelkedően merev és erős, keresztben gyenge.' },
  'ar-woven': { id: 'ar-woven', name: 'Aramid (kevlár) szövet 170', kind: 'woven', E1: 25, E2: 25, G12: 2.2, nu12: 0.10, G13: 2.0, G23: 2.0, Xt: 450, Xc: 130, Yt: 450, Yc: 130, S: 45, t: 0.25, areal: 170, rho: 1.35, color: '#e3c84a', note: 'Húzásra kiváló, nyomásra gyenge.' },
  'core-pet': { id: 'core-pet', name: 'PET hab maganyag', kind: 'core', E1: 0.08, E2: 0.08, G12: 0.025, nu12: 0.30, G13: 0.025, G23: 0.025, Xt: 1.8, Xc: 1.3, Yt: 1.8, Yc: 1.3, S: 0.9, t: 10, thicknessOptions: [5, 10, 20], areal: 0, rho: 0.10, color: '#f2e2c4', note: 'A hajlítómerevséget a vastagság köbével növeli, kis tömeggel.' },
};

export const DEFAULT_PANEL = { a: 400, b: 300 };

const PI = Math.PI;

function inv3(M) {
  const [a, b, c] = M[0], [d, e, f] = M[1], [g, h, i] = M[2];
  const A = e * i - f * h, B = -(d * i - f * g), C = d * h - e * g;
  const det = a * A + b * B + c * C;
  if (!(Math.abs(det) > 0)) throw new Error('Szinguláris merevségi mátrix');
  const k = 1 / det;
  return [
    [A * k, -(b * i - c * h) * k, (b * f - c * e) * k],
    [B * k, (a * i - c * g) * k, -(a * f - c * d) * k],
    [C * k, -(a * h - b * g) * k, (a * e - b * d) * k],
  ];
}
const mul3 = (X, Y) => X.map((r) => [0, 1, 2].map((j) => r[0] * Y[0][j] + r[1] * Y[1][j] + r[2] * Y[2][j]));
const mv3 = (X, v) => [X[0][0] * v[0] + X[0][1] * v[1] + X[0][2] * v[2], X[1][0] * v[0] + X[1][1] * v[1] + X[1][2] * v[2], X[2][0] * v[0] + X[2][1] * v[1] + X[2][2] * v[2]];
const zero3 = () => [[0, 0, 0], [0, 0, 0], [0, 0, 0]];

// Rétegek kibontása (biax → 2 UD altréteg), anyagi merevségek MPa-ban.
function expand(plies) {
  const layers = [];
  plies.forEach((p, idx) => {
    const m = MATERIALS[p.mat];
    if (!m) throw new Error('Ismeretlen anyag: ' + p.mat);
    const ang = +p.angle || 0;
    if (m.kind === 'biax') {
      layers.push({ idx, m, angle: ang + 45, t: m.t / 2 });
      layers.push({ idx, m, angle: ang - 45, t: m.t / 2 });
    } else if (m.kind === 'core') {
      layers.push({ idx, m, angle: ang, t: p.t > 0 ? +p.t : m.t, core: true });
    } else layers.push({ idx, m, angle: ang, t: m.t });
  });
  let h = 0;
  for (const L of layers) h += L.t;
  let z = -h / 2;
  for (const L of layers) {
    const m = L.m, E1 = m.E1 * 1e3, E2 = m.E2 * 1e3, G12 = m.G12 * 1e3, n12 = m.nu12, n21 = n12 * E2 / E1;
    const den = 1 - n12 * n21;
    const Q11 = E1 / den, Q22 = E2 / den, Q12 = n12 * E2 / den, Q66 = G12;
    const th = L.angle * PI / 180, c = Math.cos(th), s = Math.sin(th);
    const c2 = c * c, s2 = s * s, cs = c * s;
    const Qb = [
      [Q11 * c2 * c2 + 2 * (Q12 + 2 * Q66) * s2 * c2 + Q22 * s2 * s2, (Q11 + Q22 - 4 * Q66) * s2 * c2 + Q12 * (c2 * c2 + s2 * s2), (Q11 - Q12 - 2 * Q66) * cs * c2 + (Q12 - Q22 + 2 * Q66) * cs * s2],
      [0, Q11 * s2 * s2 + 2 * (Q12 + 2 * Q66) * s2 * c2 + Q22 * c2 * c2, (Q11 - Q12 - 2 * Q66) * cs * s2 + (Q12 - Q22 + 2 * Q66) * cs * c2],
      [0, 0, (Q11 + Q22 - 2 * Q12 - 2 * Q66) * s2 * c2 + Q66 * (s2 * s2 + c2 * c2)],
    ];
    Qb[1][0] = Qb[0][1]; Qb[2][0] = Qb[0][2]; Qb[2][1] = Qb[1][2];
    Object.assign(L, {
      zBot: z, zTop: z + L.t, c, s, Q11, Q22, Q12, Q66, Qb,
      G44: (m.G23 * c2 + m.G13 * s2) * 1e3, G55: (m.G13 * c2 + m.G23 * s2) * 1e3,
    });
    z += L.t;
  }
  return { layers, h };
}

function tsaiWuCoeffs(m) {
  const { Xt, Xc, Yt, Yc, S } = m;
  return { F1: 1 / Xt - 1 / Xc, F2: 1 / Yt - 1 / Yc, F11: 1 / (Xt * Xc), F22: 1 / (Yt * Yc), F66: 1 / (S * S), F12: -0.5 / Math.sqrt(Xt * Xc * Yt * Yc) };
}

// Pozitív gyök: a·λ² + b·λ = 1
function lambdaTW(F, s1, s2, t12) {
  const a = F.F11 * s1 * s1 + F.F22 * s2 * s2 + F.F66 * t12 * t12 + 2 * F.F12 * s1 * s2;
  const b = F.F1 * s1 + F.F2 * s2;
  if (a > 1e-300) return (2) / (b + Math.sqrt(b * b + 4 * a)); // = (−b+√(b²+4a))/(2a), stabil alak
  return b > 0 ? 1 / b : Infinity;
}

function modeLabel(F, s1, s2, t12) {
  const f = Math.abs(F.F1 * s1 + F.F11 * s1 * s1), m = Math.abs(F.F2 * s2 + F.F22 * s2 * s2), sh = F.F66 * t12 * t12;
  if (f >= m && f >= sh) return s1 >= 0 ? 'szálszakadás (húzás)' : 'szálnyomás';
  if (m >= sh) return 'mátrixrepedés (keresztirány)';
  return 'nyírás';
}

function core(plies, opts) {
  const a = (opts && opts.a) || DEFAULT_PANEL.a, b = (opts && opts.b) || DEFAULT_PANEL.b;
  const terms = (opts && opts.terms) || 31, ng = (opts && opts.grid) || 21;
  const load = (opts && opts.load) || { type: 'pressure', q: 1 };
  const { layers, h } = expand(plies);

  // ABD
  const A = zero3(), B = zero3(), D = zero3();
  let A44 = 0, A55 = 0, sumT44 = 0, sumT55 = 0, hasCore = false;
  for (const L of layers) {
    const z1 = L.zBot, z2 = L.zTop;
    for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) {
      const q = L.Qb[i][j];
      A[i][j] += q * (z2 - z1); B[i][j] += q * (z2 * z2 - z1 * z1) / 2; D[i][j] += q * (z2 ** 3 - z1 ** 3) / 3;
    }
    A44 += L.G44 * L.t; A55 += L.G55 * L.t;
    sumT44 += L.t / L.G44; sumT55 += L.t / L.G55;
    if (L.core) hasCore = true;
  }
  // Transzverzális nyírómerevség: (5/6)·Σ G·t; maggal soros (egyenletes nyírófeszültség) összegzés.
  if (hasCore) { A44 = h * h / sumT44; A55 = h * h / sumT55; } else { A44 *= 5 / 6; A55 *= 5 / 6; }

  let Bmax = 0, Amax = 0;
  for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) { Bmax = Math.max(Bmax, Math.abs(B[i][j])); Amax = Math.max(Amax, Math.abs(A[i][j])); }
  const symmetric = Bmax <= 1e-9 * Amax * h;
  const Ainv = inv3(A);
  const Ds = symmetric ? D.map((r) => r.slice()) : (() => { const X = mul3(mul3(B, Ainv), B); return D.map((r, i) => r.map((v, j) => v - X[i][j])); })();
  const Dsinv = inv3(Ds);
  const AinvB = mul3(Ainv, B);

  // Navier FSDT, egységnyi terhelésre (q = 1 kPa = 1e-3 MPa, ill. P = 1 N)
  const D11 = Ds[0][0], D22 = Ds[1][1], D12 = Ds[0][1], D66 = Ds[2][2];
  const mList = []; for (let m = 1; m <= terms; m += 2) mList.push(m);
  const M = mList.length, NN = M * M;
  const cW = new Float64Array(NN), cX = new Float64Array(NN), cY = new Float64Array(NN);
  const patch = load.type === 'patch';
  const pc = patch ? (load.c || 60) : 0, pd = patch ? (load.d || 60) : 0;
  for (let im = 0; im < M; im++) for (let jn = 0; jn < M; jn++) {
    const m = mList[im], n = mList[jn], al = m * PI / a, be = n * PI / b;
    let Q;
    if (patch) Q = 16 / (PI * PI * m * n * pc * pd) * Math.sin(m * PI / 2) * Math.sin(n * PI / 2) * Math.sin(m * PI * pc / (2 * a)) * Math.sin(n * PI * pd / (2 * b));
    else Q = 16e-3 / (PI * PI * m * n);
    const s11 = A55 * al * al + A44 * be * be, s12 = A55 * al, s13 = A44 * be;
    const s22 = D11 * al * al + D66 * be * be + A55, s23 = (D12 + D66) * al * be, s33 = D66 * al * al + D22 * be * be + A44;
    // eliminálás: X, Y kifejezése W-vel a 2. és 3. egyenletből
    const det = s22 * s33 - s23 * s23;
    const xW = (-s12 * s33 + s13 * s23) / det, yW = (-s13 * s22 + s12 * s23) / det;
    const W = Q / (s11 + s12 * xW + s13 * yW);
    const k = im * M + jn;
    cW[k] = W; cX[k] = xW * W; cY[k] = yW * W;
  }

  // sin/cos táblák
  const xs = new Float64Array(ng), ys = new Float64Array(ng);
  for (let i = 0; i < ng; i++) { xs[i] = a * i / (ng - 1); ys[i] = b * i / (ng - 1); }
  const SX = new Float64Array(M * ng), CX = new Float64Array(M * ng), SY = new Float64Array(M * ng), CY = new Float64Array(M * ng);
  for (let im = 0; im < M; im++) for (let i = 0; i < ng; i++) {
    const m = mList[im];
    SX[im * ng + i] = Math.sin(m * PI * xs[i] / a); CX[im * ng + i] = Math.cos(m * PI * xs[i] / a);
    SY[im * ng + i] = Math.sin(m * PI * ys[i] / b); CY[im * ng + i] = Math.cos(m * PI * ys[i] / b);
  }
  // tagonkénti együtthatók a mezőkhöz
  const kMx = new Float64Array(NN), kMy = new Float64Array(NN), kMxy = new Float64Array(NN), kQx = new Float64Array(NN), kQy = new Float64Array(NN);
  for (let im = 0; im < M; im++) for (let jn = 0; jn < M; jn++) {
    const k = im * M + jn, al = mList[im] * PI / a, be = mList[jn] * PI / b;
    // fizikai görbület (z felfelé, w lefelé): κx = αX·ss, κy = βY·ss, κxy = −(βX+αY)·cc
    kMx[k] = D11 * al * cX[k] + D12 * be * cY[k];
    kMy[k] = D12 * al * cX[k] + D22 * be * cY[k];
    kMxy[k] = -D66 * (be * cX[k] + al * cY[k]);
    kQx[k] = A55 * (al * cW[k] + cX[k]);
    kQy[k] = A44 * (be * cW[k] + cY[k]);
  }
  const NP = ng * ng;
  const w = new Float64Array(NP), Mx = new Float64Array(NP), My = new Float64Array(NP), Mxy = new Float64Array(NP), Qr = new Float64Array(NP);
  // részösszegek y irányban: minden (j, m)-re összegezve n szerint
  const tW = new Float64Array(M), tMx = new Float64Array(M), tMy = new Float64Array(M), tMxy = new Float64Array(M), tQx = new Float64Array(M), tQy = new Float64Array(M);
  for (let j = 0; j < ng; j++) {
    for (let im = 0; im < M; im++) {
      let sw = 0, sx = 0, sy = 0, sxy = 0, qx = 0, qy = 0;
      for (let jn = 0; jn < M; jn++) {
        const k = im * M + jn, sy_ = SY[jn * ng + j], cy_ = CY[jn * ng + j];
        sw += cW[k] * sy_; sx += kMx[k] * sy_; sy += kMy[k] * sy_; sxy += kMxy[k] * cy_; qx += kQx[k] * sy_; qy += kQy[k] * cy_;
      }
      tW[im] = sw; tMx[im] = sx; tMy[im] = sy; tMxy[im] = sxy; tQx[im] = qx; tQy[im] = qy;
    }
    for (let i = 0; i < ng; i++) {
      let vw = 0, vx = 0, vy = 0, vxy = 0, qx = 0, qy = 0;
      for (let im = 0; im < M; im++) {
        const sx_ = SX[im * ng + i], cx_ = CX[im * ng + i];
        vw += tW[im] * sx_; vx += tMx[im] * sx_; vy += tMy[im] * sx_; vxy += tMxy[im] * cx_; qx += tQx[im] * cx_; qy += tQy[im] * sx_;
      }
      const p = j * ng + i;
      w[p] = vw; Mx[p] = vx; My[p] = vy; Mxy[p] = vxy; Qr[p] = Math.hypot(qx, qy);
    }
  }
  let wUnit = 0; for (let p = 0; p < NP; p++) if (w[p] > wUnit) wUnit = w[p];
  return { a, b, ng, xs, ys, load, layers, h, A, B, D, Ds, Dsinv, Ainv, AinvB, A44, A55, symmetric, hasCore, w, Mx, My, Mxy, Qr, wUnit };
}

function loadMagnitude(load) {
  return load.type === 'patch' ? +load.P || 0 : +load.q || 0;
}

export function analyze(plies, opts = {}) {
  if (!plies || !plies.length) return null;
  const load = opts.load || { type: 'pressure', q: 1 };
  const R = core(plies, { ...opts, load });
  const { layers, h, A, B, D, Ds, Dsinv, AinvB, symmetric, ng, xs, ys, a, b } = R;
  const L0 = loadMagnitude(load);
  const NP = ng * ng;

  // Ply-feszültségek (egységnyi terhelésre) és Tsai-Wu
  const TW = layers.map((L) => tsaiWuCoeffs(L.m));
  const plyLam = new Array(plies.length).fill(Infinity);
  let best = { lam: Infinity, plyIndex: -1, mode: '', x: 0, y: 0 };
  for (let p = 0; p < NP; p++) {
    const Mv = [Mx(p), My(p), Mxy(p)];
    const kap = mv3(Dsinv, Mv);
    const e0 = symmetric ? [0, 0, 0] : mv3(AinvB, kap).map((v) => -v);
    for (let li = 0; li < layers.length; li++) {
      const L = layers[li], F = TW[li];
      for (const z of [L.zBot, L.zTop]) {
        const ex = e0[0] + z * kap[0], ey = e0[1] + z * kap[1], gxy = e0[2] + z * kap[2];
        const c = L.c, s = L.s;
        const e1 = c * c * ex + s * s * ey + c * s * gxy;
        const e2 = s * s * ex + c * c * ey - c * s * gxy;
        const g12 = 2 * c * s * (ey - ex) + (c * c - s * s) * gxy;
        const s1 = L.Q11 * e1 + L.Q12 * e2, s2 = L.Q12 * e1 + L.Q22 * e2, t12 = L.Q66 * g12;
        const lam = lambdaTW(F, s1, s2, t12);
        if (lam < plyLam[L.idx]) plyLam[L.idx] = lam;
        if (lam < best.lam) best = { lam, plyIndex: L.idx, mode: modeLabel(F, s1, s2, t12), x: xs[p % ng], y: ys[(p / ng) | 0] };
      }
    }
  }
  function Mx(p) { return R.Mx[p]; } function My(p) { return R.My[p]; } function Mxy(p) { return R.Mxy[p]; }

  // Mag nyírás
  if (R.hasCore) {
    let qMax = 0, pq = 0; for (let p = 0; p < NP; p++) if (R.Qr[p] > qMax) { qMax = R.Qr[p]; pq = p; }
    const hTot = h;
    for (const L of layers) if (L.core) {
      const tBot = L.zBot + hTot / 2, tTop = hTot / 2 - L.zTop;
      const tau = qMax / (L.t + (tBot + tTop) / 2);
      const lam = tau > 0 ? L.m.S / tau : Infinity;
      if (lam < plyLam[L.idx]) plyLam[L.idx] = lam;
      if (lam < best.lam) best = { lam, plyIndex: L.idx, mode: 'mag nyírótörése', x: xs[pq % ng], y: ys[(pq / ng) | 0] };
    }
  }

  // Merevségi jellemzők
  const ai = R.Ainv, di = Dsinv;
  const inPlane = { Ex: 1 / (h * ai[0][0]) / 1e3, Ey: 1 / (h * ai[1][1]) / 1e3, Gxy: 1 / (h * ai[2][2]) / 1e3, nuxy: -ai[0][1] / ai[0][0] };
  const flexural = { Efx: 12 / (h ** 3 * di[0][0]) / 1e3, Efy: 12 / (h ** 3 * di[1][1]) / 1e3 };

  let massPerArea = 0; for (const L of layers) massPerArea += L.t * L.m.rho;
  const wMax = R.wUnit * L0;
  const values = new Float64Array(NP); for (let p = 0; p < NP; p++) values[p] = R.w[p] * L0;

  const warnings = [];
  if (!symmetric) warnings.push('Aszimmetrikus rétegrend: a lap kikeményedéskor vetemedni fog. A számítás csökkentett hajlítómerevséggel (D* = D − B·A⁻¹·B) dolgozik.');
  if (Math.abs(D[0][2]) / D[0][0] > 0.1 || Math.abs(D[1][2]) / D[1][1] > 0.1)
    warnings.push('Jelentős hajlítás–csavarás csatolás (|D16|/D11 vagy |D26|/D22 > 0,1): a lehajlásszámítás ezt elhanyagolja, az eredmény pontatlanabb.');
  if (wMax > 0.5 * h) warnings.push('A lehajlás nagyobb, mint a lapvastagság fele: a valóságban a membránhatás merevít, a lineáris modell túlbecsüli a lehajlást (biztonságos irány).');
  if (R.hasCore) warnings.push('Maganyagos (szendvics) lap: a mag nyírási alakváltozását egyszerűsítve vesszük figyelembe, a mag nyírószilárdságát külön ellenőrizzük. A héj leválását és a helyi benyomódást a modell nem vizsgálja.');

  const fpfLoad = best.lam; // egységnyi terhelésre számolt szorzó = tönkremeneteli terhelés
  const plyResults = plies.map((p, i) => {
    const ls = layers.filter((L) => L.idx === i);
    return { index: i, mat: p.mat, angle: +p.angle || 0, zBot: ls[0].zBot, zTop: ls[ls.length - 1].zTop, maxFailureIndex: isFinite(plyLam[i]) ? L0 / plyLam[i] : 0 };
  });

  return {
    h, massPerArea, panelMass: massPerArea * a * b / 1e6, A, B, D, symmetric, warnings,
    inPlane, flexural, wMax, w: { nx: ng, ny: ng, values },
    fpf: { factor: L0 > 0 ? fpfLoad / L0 : Infinity, load: fpfLoad, plyIndex: best.plyIndex, mode: best.mode, x: best.x, y: best.y, criterion: 'Tsai-Wu' },
    plyResults,
    _Dstar: Ds, _A44: R.A44, _A55: R.A55,
  };
}

export function loadForDeflection(plies, opts = {}, wTarget) {
  if (!plies || !plies.length || !(wTarget > 0)) return 0;
  const load = opts.load || { type: 'pressure', q: 1 };
  const R = core(plies, { ...opts, load, grid: opts.grid || 21 });
  return R.wUnit > 0 ? wTarget / R.wUnit : Infinity;
}
