// Rétegrend-építő: felület a clt.js számítómotorhoz (#epits szekció).
import { MATERIALS, analyze, loadForDeflection, DEFAULT_PANEL } from './clt.js';

const G = 9.81, MAX = 20, A = DEFAULT_PANEL.a, B = DEFAULT_PANEL.b;
const RX = 30, RY = 24, DUR = 650, VIS = 90; // renderrács, animáció (ms), látható lehajlás felső határa (mm)
const QV = [0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1, 1.5, 2, 3, 4, 5, 7.5, 10, 15, 20, 30, 50]; // kPa
const $ = (id) => document.getElementById(id);
const root = $('epits');
if (!root) throw new Error('#epits hiányzik');

const nf = (v, d) => Number.isFinite(v) ? v.toLocaleString('hu-HU', { minimumFractionDigits: d, maximumFractionDigits: d }) : '–';
const sm = (v) => !Number.isFinite(v) ? '–' : nf(v, Math.abs(v) < 1 ? 2 : Math.abs(v) < 10 ? 1 : 0);
const tx = (r) => nf(r, r < 10 ? 1 : 0) + '×';
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);

const mk = (m, ...angles) => angles.map((a) => ({ mat: m, angle: a }));
const REF = mk('gl-woven', 0, 45, 45, 0);
const PRESETS = [
  ['A mi lapunk (4× üvegszövet)', REF],
  ['Szénszálas, kvázi-izotróp', mk('cf-ud', 0, 45, -45, 90, 90, -45, 45, 0)],
  ['Szendvics (üveg + PET hab)', [...mk('gl-woven', 0, 45), { mat: 'core-pet', angle: 0, t: 10 }, ...mk('gl-woven', 45, 0)]],
  ['Aszimmetrikus (hibás) példa', mk('gl-ud', 0, 0, 90, 90)],
  ['Kevlár', mk('ar-woven', 0, 45, 0, 0, 45, 0)],
];

let uid = 0;
const S = { plies: [], mode: 'pressure', qi: 6, kg: 10, target: 5 };
const setPlies = (list) => { S.plies = list.map((p) => ({ ...p, id: ++uid })); };
setPlies(REF);

/* ---------- szögek ---------- */
function choices(m) {
  if (m.kind === 'ud') return [[0, '0°'], [45, '45°'], [-45, '−45°'], [90, '90°']];
  if (m.kind === 'woven') return [[0, '0/90°'], [45, '±45°']];
  if (m.kind === 'biax') return [[0, '±45°'], [45, '0/90°']];
  return null;
}
function angleText(p) {
  const m = MATERIALS[p.mat];
  if (m.kind === 'core') return `${p.t} mm vastag`;
  if (m.kind === 'mat') return 'minden irányban egyforma';
  const c = choices(m).find((c) => c[0] === p.angle);
  return c ? c[1] : p.angle + '°';
}
const plyName = (p) => `${MATERIALS[p.mat].name}, ${angleText(p)}`;
const same = (x, y) => x.length === y.length && x.every((p, i) => p.mat === y[i].mat && p.angle === y[i].angle && (p.t || 0) === (y[i].t || 0));
// ±45°-os irányban álló szálak?
const is45 = (p) => { const k = MATERIALS[p.mat].kind; return (k === 'biax' && p.angle === 0) || ((k === 'ud' || k === 'woven') && Math.abs(p.angle) === 45); };
const isFibre = (p) => !['core', 'mat'].includes(MATERIALS[p.mat].kind);

/* ---------- vezérlők ---------- */
const presetsEl = $('bPresets'), palEl = $('bPalette'), listEl = $('bPlies'), xsecEl = $('bXsec');
presetsEl.innerHTML = PRESETS.map((p, i) => `<button type="button" data-p="${i}" aria-pressed="false">${esc(p[0])}</button>`).join('');
palEl.innerHTML = Object.values(MATERIALS).map((m) =>
  `<button type="button" data-m="${m.id}"><i class="chip" style="background:${m.color};box-shadow:inset 0 0 0 1px rgba(0,0,0,.18)"></i><b>${esc(m.name)}</b><small>${esc(m.note)}</small></button>`).join('');

presetsEl.addEventListener('click', (e) => {
  const b = e.target.closest('button'); if (!b) return;
  setPlies(PRESETS[+b.dataset.p][1]); changed();
});
palEl.addEventListener('click', (e) => {
  const b = e.target.closest('button'); if (!b || S.plies.length >= MAX) return;
  const m = MATERIALS[b.dataset.m];
  const p = { mat: m.id, angle: 0, id: ++uid };
  if (m.kind === 'core') p.t = (m.thicknessOptions && m.thicknessOptions[1]) || m.t;
  S.plies.push(p); changed();
});
listEl.addEventListener('click', (e) => {
  const b = e.target.closest('button[data-act]'); if (!b) return;
  const i = +b.closest('li').dataset.i, act = b.dataset.act, id = S.plies[i].id;
  if (act === 'del') { S.plies.splice(i, 1); changed(); const n = listEl.querySelector(`li[data-i="${Math.min(i, S.plies.length - 1)}"] button[data-act="del"]`); (n || palEl.querySelector('button')).focus(); return; }
  const j = act === 'up' ? i + 1 : i - 1;
  if (j < 0 || j >= S.plies.length) return;
  [S.plies[i], S.plies[j]] = [S.plies[j], S.plies[i]];
  changed();
  const f = listEl.querySelector(`li[data-id="${id}"] button[data-act="${act}"]`);
  (f && !f.disabled ? f : listEl.querySelector(`li[data-id="${id}"] select, li[data-id="${id}"] button`)).focus();
});
listEl.addEventListener('change', (e) => {
  const s = e.target.closest('select'); if (!s) return;
  const p = S.plies[+s.closest('li').dataset.i];
  if (MATERIALS[p.mat].kind === 'core') p.t = +s.value; else p.angle = +s.value;
  changed(false);
});
$('bMode').addEventListener('click', (e) => {
  const b = e.target.closest('button'); if (!b) return;
  S.mode = b.dataset.mode; syncLoad(); schedule();
});
const loadEl = $('bLoad');
loadEl.addEventListener('input', () => { if (S.mode === 'pressure') S.qi = +loadEl.value; else S.kg = +loadEl.value; loadLabel(); schedule(); });
$('bTarget').addEventListener('input', (e) => { const v = parseFloat(String(e.target.value).replace(',', '.')); if (v > 0) { S.target = v; schedule(); } });

function syncLoad() {
  for (const b of $('bMode').querySelectorAll('button')) b.setAttribute('aria-pressed', String(b.dataset.mode === S.mode));
  if (S.mode === 'pressure') Object.assign(loadEl, { min: 0, max: QV.length - 1, step: 1, value: S.qi });
  else Object.assign(loadEl, { min: 0, max: 200, step: 1, value: S.kg });
  loadLabel();
}
function loadLabel() {
  const l = $('bLoadLbl');
  if (S.mode === 'pressure') {
    const q = QV[S.qi];
    l.textContent = `Nyomás: ${sm(q)} kPa (≈ ${sm(q * 1000 / G)} kg/m², a lapon összesen kb. ${sm(q * 1000 * A * B / 1e6 / G)} kg)`;
    loadEl.setAttribute('aria-valuetext', `${sm(q)} kilopascal`);
  } else {
    l.textContent = `Súly a lap közepén, 6 × 6 cm-en: ${S.kg} kg`;
    loadEl.removeAttribute('aria-valuetext');
  }
}

function renderStack() {
  const n = S.plies.length;
  $('bCount').textContent = `${n} / ${MAX}`;
  for (const b of palEl.querySelectorAll('button')) b.disabled = n >= MAX;
  for (const b of presetsEl.querySelectorAll('button')) b.setAttribute('aria-pressed', String(same(S.plies, PRESETS[+b.dataset.p][1])));
  const th = (p) => MATERIALS[p.mat].kind === 'core' ? p.t : MATERIALS[p.mat].t;
  const tot = S.plies.reduce((s, p) => s + th(p), 0) || 1, k = Math.min(30, 90 / tot);
  xsecEl.innerHTML = S.plies.map((p) => `<i style="height:${Math.max(4, th(p) * k).toFixed(1)}px;background:${MATERIALS[p.mat].color}"></i>`).join('');
  if (!n) { listEl.innerHTML = '<li><span class="none">Még nincs réteg. Válassz egy anyagot fent, vagy egy kész rétegrendet.</span></li>'; return; }
  let html = '';
  for (let i = n - 1; i >= 0; i--) {
    const p = S.plies[i], m = MATERIALS[p.mat], no = i + 1;
    const opts = m.kind === 'core' ? (m.thicknessOptions || [m.t]).map((t) => [t, t + ' mm']) : choices(m);
    const ctl = opts
      ? `<select aria-label="${no}. réteg ${m.kind === 'core' ? 'vastagsága' : 'iránya'}">${opts.map(([v, l]) => `<option value="${v}"${v === (m.kind === 'core' ? p.t : p.angle) ? ' selected' : ''}>${l}</option>`).join('')}</select>`
      : '<span class="pa">minden irányban</span>';
    html += `<li data-i="${i}" data-id="${p.id}"><i style="background:${m.color}"></i><span class="pn">${esc(m.name)}<small>alulról ${no}.</small></span>${ctl}` +
      `<button type="button" data-act="up" aria-label="${no}. réteg feljebb"${i === n - 1 ? ' disabled' : ''}>↑</button>` +
      `<button type="button" data-act="down" aria-label="${no}. réteg lejjebb"${i === 0 ? ' disabled' : ''}>↓</button>` +
      `<button type="button" data-act="del" aria-label="${no}. réteg törlése">×</button></li>`;
  }
  listEl.innerHTML = html;
}
function changed(rerender = true) { if (rerender) renderStack(); else renderStack(); schedule(); }

/* ---------- számítás ---------- */
let pending = 0;
function schedule() { if (!pending) pending = requestAnimationFrame(() => { pending = 0; compute(); }); }
const clean = (pl) => pl.map(({ mat, angle, t }) => (t ? { mat, angle, t } : { mat, angle }));
function loadSpec() { return S.mode === 'pressure' ? { type: 'pressure', q: QV[S.qi] } : { type: 'patch', P: S.kg * G, c: 60, d: 60 }; }
// 0 kg esetén egységnyi terheléssel számolunk (a tönkremeneteli terhelés így is értelmes), a lehajlást 0-val szorozzuk.
function run(pl, load) {
  const eff = load.type === 'patch' && !(load.P > 0) ? { ...load, P: G } : load;
  const r = analyze(clean(pl), { ...DEFAULT_PANEL, load: eff, terms: 31, grid: 21 });
  if (r) r.scale = eff === load ? 1 : 0;
  return r;
}
const refCache = new Map();
function refFor(load) { const k = JSON.stringify(load); if (!refCache.has(k)) refCache.set(k, run(REF, load)); return refCache.get(k); }

function compute() {
  const load = loadSpec(), pressure = load.type === 'pressure';
  let r = null;
  try { r = S.plies.length ? run(S.plies, load) : null; } catch (err) { console.error(err); }
  const ids = ['rW', 'rF', 'rH', 'rM', 'rE', 'rT'];
  if (!r) {
    ids.forEach((id) => { $(id).textContent = '–'; });
    ['rWp', 'rFm', 'rMp', 'rEp', 'rTp', 'rFu', 'rTu'].forEach((id) => { $(id).textContent = ''; });
    $('rFbox').classList.remove('bad');
    $('bExplain').innerHTML = `<li>${S.plies.length ? 'Ezt a rétegrendet nem sikerült kiszámolni.' : 'Adj hozzá legalább egy réteget, és máris számolunk.'}</li>`;
    view.cracked = false; view.fpf = null; view.patch = false; view.exag = 1; view.wMax = 0;
    setTarget(new Float32Array((RX + 1) * (RY + 1)));
    return;
  }
  const ref = refFor(load), wMax = r.wMax * r.scale;
  const cur = pressure ? load.q : S.kg;
  const fpfU = pressure ? r.fpf.load : r.fpf.load / G;
  const cracked = Number.isFinite(fpfU) && cur >= fpfU && cur > 0;
  const fp = S.plies[r.fpf.plyIndex];

  $('rW').textContent = sm(wMax);
  $('rWp').textContent = pressure ? `${sm(load.q)} kPa egyenletes nyomásnál` : `${S.kg} kg-os súllyal középen`;
  $('rF').textContent = pressure ? sm(fpfU) : (Number.isFinite(fpfU) ? nf(fpfU, fpfU < 10 ? 1 : 0) : '–');
  $('rFu').textContent = pressure ? 'kPa' : 'kg';
  $('rFm').textContent = fp ? `${cap(r.fpf.mode)} az alulról ${r.fpf.plyIndex + 1}. rétegben (${plyName(fp)}).${pressure ? ` Ez kb. ${sm(fpfU * 1000 / G)} kg/m².` : ''}${cracked ? ' A mostani terhelés ezt már meghaladja: a lap ennél jóval kisebb terhelésnél megreped.' : ''}` : '';
  $('rFbox').classList.toggle('bad', cracked);
  $('rH').textContent = nf(r.h, 2);
  $('rM').textContent = nf(r.massPerArea, 2);
  $('rMp').textContent = `A 400 × 300 mm-es lap ${nf(r.panelMass * 1000, 0)} g.`;
  const ex = r.inPlane.Ex / ref.inPlane.Ex, ey = r.inPlane.Ey / ref.inPlane.Ey;
  $('rE').textContent = `${sm(r.inPlane.Ex)} / ${sm(r.inPlane.Ey)}`;
  $('rEp').textContent = same(S.plies, REF) ? 'Ez a mi lapunk: ehhez hasonlítjuk a többit.' : `A mi lapunkhoz képest ${ratio(ex)} x irányban, ${ratio(ey)} y irányban.`;
  let need = NaN;
  try { need = loadForDeflection(clean(S.plies), { ...DEFAULT_PANEL, load: load.type === 'patch' && !(load.P > 0) ? { ...load, P: G } : load, terms: 31, grid: 21 }, S.target); } catch (err) { console.error(err); }
  const needU = pressure ? need : need / G;
  $('rT').textContent = sm(needU);
  $('rTu').textContent = pressure ? 'kPa' : 'kg';
  $('rTp').textContent = !Number.isFinite(needU) ? '' : pressure ? `≈ ${sm(needU * 1000 / G)} kg/m² egyenletesen elterítve.` + (needU > fpfU ? ' Ennyi lehajlás előtt már megreped.' : '') : `Súly a lap közepén.${needU > fpfU ? ' Ennyi lehajlás előtt már megreped.' : ''}`;

  $('bExplain').innerHTML = explain(r, ref, wMax, fpfU, pressure, load).join('');

  // nézet
  const FACT = [1000, 500, 200, 100, 50, 20, 10, 5, 2, 1, 0.5, 0.2, 0.1, 0.05];
  const ex2 = wMax > 0 ? (FACT.find((f) => wMax * f <= VIS) || 0.05) : 1;
  Object.assign(view, { cracked, exag: ex2, wMax, patch: !pressure, fpf: Number.isFinite(fpfU) ? [r.fpf.x, r.fpf.y] : null });
  const T = new Float32Array((RX + 1) * (RY + 1)), v = r.w.values, nx = r.w.nx, ny = r.w.ny, k = r.scale * ex2;
  for (let j = 0; j <= RY; j++) for (let i = 0; i <= RX; i++) {
    const fx = i / RX * (nx - 1), fy = j / RY * (ny - 1), i0 = Math.min(nx - 2, fx | 0), j0 = Math.min(ny - 2, fy | 0), u = fx - i0, w = fy - j0;
    const a = v[j0 * nx + i0], b = v[j0 * nx + i0 + 1], c = v[(j0 + 1) * nx + i0], d = v[(j0 + 1) * nx + i0 + 1];
    T[j * (RX + 1) + i] = ((a * (1 - u) + b * u) * (1 - w) + (c * (1 - u) + d * u) * w) * k;
  }
  $('bCap').textContent = (wMax > 0 ? (ex2 === 1 ? 'Valós léptékben' : ex2 > 1 ? `A lehajlás ${nf(ex2, 0)}× felnagyítva` : `A lehajlás ${nf(ex2, 2)}× kicsinyítve`) + ', ' : '') +
    'a sötétebb szín nagyobb lehajlást jelent. ' + (cracked ? 'Pirossal: itt már megrepedt az első réteg.' : 'A karika jelöli, hol jelenne meg az első repedés.');
  $('bCanvas').setAttribute('aria-label', `A lap lehajlása: legnagyobb ${sm(wMax)} mm.${cracked ? ' A lap megrepedt.' : ''}`);
  setTarget(T);
}
const cap = (s) => s ? s[0].toUpperCase() + s.slice(1) : '';
const ratio = (r) => Math.abs(r - 1) < 0.05 ? 'ugyanolyan merev' : r > 1 ? `${tx(r)} merevebb` : `${tx(1 / r)} hajlékonyabb`;

/* ---------- magyarázat ---------- */
function explain(r, ref, wMax, fpfU, pressure, load) {
  const out = [], li = (s) => out.push(`<li>${s}</li>`), pl = S.plies, isRef = same(pl, REF);
  if (isRef) li('Ez a mi lapunk: négy réteg üvegszövet, kívül 0/90°-ban, belül ±45°-ban. A többi rétegrendet ehhez hasonlítjuk.');
  else if (r.scale) {
    const q = r.wMax / ref.wMax;
    if (q < 0.95) li(`Ugyanekkora terhelés alatt ${tx(1 / q)} kevesebbet hajlik, mint a mi négyrétegű üveglapunk (${sm(ref.wMax)} mm helyett ${sm(wMax)} mm).`);
    else if (q > 1.05) li(`Ugyanekkora terhelés alatt ${tx(q)} többet hajlik, mint a mi négyrétegű üveglapunk (${sm(ref.wMax)} mm helyett ${sm(wMax)} mm).`);
    else li('Hajlításban nagyjából olyan merev, mint a mi négyrétegű üveglapunk.');
  }
  const d = r.flexural.Efx / r.flexural.Efy;
  if (d > 1.4) li(`Hajlításban hosszában (a 400 mm-es oldal mentén) ${tx(d)} merevebb, mint keresztben: a szálak többsége erre fut, keresztben jórészt a gyanta dolgozik.`);
  else if (d < 1 / 1.4) li(`Hajlításban keresztben (a 300 mm-es oldal mentén) ${tx(1 / d)} merevebb, mint hosszában: a szálak többsége erre fut.`);
  const fib = pl.filter(isFibre);
  if (fib.length && fib.every(is45)) li('Minden szál ±45°-ban áll: a lap a nyírást és a csavarást jól viseli, de hajlításban hajlékonyabb, mintha a szálak egy része a lap éleivel párhuzamosan futna.');
  else if (fib.some(is45)) li('A ±45°-os rétegek a nyírást és a csavarást viszik: a lap kevésbé csavarodik el, ha a terhelés nem pont középen éri.');
  if (!r.symmetric) li('A rétegrend nem tükörszimmetrikus a középsíkra. Kikeményedéskor a rétegek másképp húzódnak össze, és a lap megvetemedik. Ugyanezek a rétegek tükrözve (pl. 0/90/90/0) síkok maradnának.');
  else if (pl.length > 1) li('A rétegrend tükörszimmetrikus a középsíkra, ezért kikeményedés után is sík marad.');
  if (pl.some((p) => p.mat === 'ar-woven')) {
    const m = MATERIALS['ar-woven'], fp = pl[r.fpf.plyIndex];
    li(`Az aramid (kevlár) húzásra kiváló, nyomásra viszont gyenge: nyomva kb. ${tx(m.Xt / m.Xc)} kevesebbet bír, mint húzva. Hajlításkor a lap egyik oldala mindig nyomott${fp && fp.mat === 'ar-woven' ? ', és itt is egy aramidréteg reped meg elsőként' : ''}. Ezért a nyomott oldalra jobb üveget vagy szenet tenni.`);
  }
  const cores = pl.filter((p) => MATERIALS[p.mat].kind === 'core');
  if (cores.length && cores.length < pl.length) {
    try {
      const skins = run(pl.filter((p) => MATERIALS[p.mat].kind !== 'core'), load);
      const st = skins.wMax / r.wMax, mp = (r.massPerArea / skins.massPerArea - 1) * 100;
      const skinPl = pl.filter((p) => MATERIALS[p.mat].kind !== 'core');
      li(same(skinPl, REF)
        ? `Hab nélkül ez épp a mi lapunk lenne – a különbséget tehát csak a ${cores.map((c) => c.t).join(' + ')} mm-es hab adja, miközben a tömeg mindössze ${nf(mp, 0)}%-kal nő. A hab széthúzza egymástól a két héjat, és a hajlítómerevség nagyjából a két héj távolságának négyzetével nő (szendvicshatás).`
        :`A ${cores.map((c) => c.t).join(' + ')} mm-es hab ${tx(st)} merevebbé teszi a lapot, mint ugyanezek a rétegek hab nélkül, a tömeg pedig csak ${nf(mp, 0)}%-kal nő. A hab széthúzza egymástól a két héjat, és a hajlítómerevség nagyjából a két héj távolságának négyzetével nő (szendvicshatás).`);
    } catch (err) { console.error(err); }
  }
  if (pl.some((p) => p.mat === 'gl-csm')) li('A paplan minden irányban egyforma, de gyengébb a szövetnél; epoxi gyantához porkötésű változat kell, mert a szokásos (emulziós) kötőanyagot csak a poliésztergyanta sztirolja oldja fel.');
  const mr = r.massPerArea / ref.massPerArea;
  if (!isRef && Math.abs(mr - 1) > 0.05) li(`Négyzetméterenként ${nf(r.massPerArea, 2)} kg: ${mr > 1 ? tx(mr) + ' nehezebb' : tx(1 / mr) + ' könnyebb'}, mint a mi lapunk (${nf(ref.massPerArea, 2)} kg/m²).`);
  if (Number.isFinite(fpfU)) {
    li(pressure
      ? `Kb. ${sm(fpfU)} kPa nyomásnál (ez ≈ ${sm(fpfU * 1000 / G)} kg/m², a lapon összesen kb. ${sm(fpfU * 1000 * A * B / 1e6 / G)} kg) jelenik meg az első repedés. A lap ennél általában többet bír, de ez már károsodás.`
      : `Kb. ${sm(fpfU)} kg-os súly középen ráállva jelenik meg az első repedés. A lap ennél általában többet bír, de ez már károsodás.`);
    const kgC = pressure ? fpfU * 1000 * A * B / 1e6 / G : fpfU;
    if (kgC < 40) li(`Egy ${nf(r.h, 1)} mm vékony lap tehát már ${pressure ? `kb. ${sm(kgC)} kg egyenletesen elterített terhet` : `egy kb. ${sm(kgC)} kg-os súlyt`} sem bír ki repedés nélkül${isRef ? ' – ezért kell egy valódi termékhez több réteg vagy maganyag. Próbáld ki a szendvics rétegrendet!' : '.'}`);
  }
  for (const w of r.warnings) {
    if (/Aszimmetrikus/.test(w)) continue; // fent már elmondtuk közérthetően
    if (/lapvastagság fele/.test(w) && (!r.scale || wMax <= 0.5 * r.h)) continue;
    out.push(`<li class="warn"><b>Figyelem:</b> ${esc(w)}</li>`);
  }
  return out;
}

/* ---------- rajz ---------- */
const cv = $('bCanvas'), ctx = cv.getContext('2d');
const view = { cracked: false, exag: 1, wMax: 0, patch: false, fpf: null };
let W = 0, H = 0, dpr = 1, C = {}, D = null, F0 = null, T = null, t0 = 0, raf = 0, animating = false;
const reduce = matchMedia('(prefers-reduced-motion: reduce)'), dark = matchMedia('(prefers-color-scheme: dark)');
const hex = (s) => { s = s.replace('#', ''); if (s.length === 3) s = [...s].map((c) => c + c).join(''); return [0, 2, 4].map((i) => parseInt(s.slice(i, i + 2), 16)); };
const mix = (a, b, t) => [0, 1, 2].map((i) => a[i] + (b[i] - a[i]) * t);
const rgb = (c, f = 1) => `rgb(${c.map((v) => Math.max(0, Math.min(255, Math.round(v * f)))).join(',')})`;
function colors() {
  const cs = getComputedStyle(document.documentElement), g = (n) => cs.getPropertyValue(n).trim();
  const raised = hex(g('--raised')), resin = hex(g('--resin'));
  C = { lo: mix(raised, resin, 0.22), mid: resin, hi: hex(g('--resin-deep')), peel: hex(g('--peel')), ink: g('--ink'), muted: g('--muted'), steel: g('--steel'), raised: g('--raised') };
}
function size() {
  dpr = Math.min(window.devicePixelRatio || 1, 3);
  const r = cv.getBoundingClientRect(); W = r.width; H = r.height;
  cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr); draw();
}
function setTarget(nt) {
  T = nt;
  if (!D || D.length !== nt.length || reduce.matches) { D = Float32Array.from(nt); animating = false; draw(); return; }
  F0 = Float32Array.from(D); t0 = performance.now(); animating = true;
  if (!raf) raf = requestAnimationFrame(step);
}
function step(now) {
  const k = Math.min(1, (now - t0) / DUR), e = k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
  for (let i = 0; i < D.length; i++) D[i] = F0[i] + (T[i] - F0[i]) * e;
  animating = k < 1; draw();
  raf = animating ? requestAnimationFrame(step) : 0;
}
const CX = Math.cos(Math.PI / 6), SY = 0.5;
function sample(x, y) { // a kirajzolt (felnagyított) lehajlás egy pontban
  const fx = Math.max(0, Math.min(RX, x / A * RX)), fy = Math.max(0, Math.min(RY, y / B * RY));
  const i0 = Math.min(RX - 1, fx | 0), j0 = Math.min(RY - 1, fy | 0), u = fx - i0, w = fy - j0, n = RX + 1;
  return (D[j0 * n + i0] * (1 - u) + D[j0 * n + i0 + 1] * u) * (1 - w) + (D[(j0 + 1) * n + i0] * (1 - u) + D[(j0 + 1) * n + i0 + 1] * u) * w;
}
function draw() {
  if (!W || !D) return;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, W, H);
  const pad = W < 480 ? 14 : 28, top = view.patch ? 46 : 0;
  const s = Math.min((W - 2 * pad) / ((A + B) * CX), (H - 2 * pad - 18) / ((A + B) * SY + VIS * 1.1 + top));
  const ox = pad + B * CX * s + ((W - 2 * pad) - (A + B) * CX * s) / 2, oy = pad + top * s;
  const P = (x, y, v) => [ox + (x - y) * CX * s, oy + ((x + y) * SY + v) * s];
  const n = RX + 1, dx = A / RX, dy = B / RY;
  let vmax = 1e-9; for (let i = 0; i < D.length; i++) if (D[i] > vmax) vmax = D[i];
  const crack = view.cracked && !animating && view.fpf;
  // felület, hátulról előre
  ctx.lineJoin = 'round';
  for (let sum = 0; sum <= RX + RY - 2; sum++) {
    for (let i = Math.max(0, sum - RY + 1); i <= Math.min(RX - 1, sum); i++) {
      const j = sum - i, k = j * n + i;
      const a = D[k], b = D[k + 1], c = D[k + n + 1], d = D[k + n];
      const t = (a + b + c + d) / 4 / vmax;
      let col = t < 0.5 ? mix(C.lo, C.mid, t * 2) : mix(C.mid, C.hi, (t - 0.5) * 2);
      // egyszerű megvilágítás a lejtésből
      const gx = ((b + c) - (a + d)) / 2 / dx, gy = ((c + d) - (a + b)) / 2 / dy;
      const shade = 1 + Math.max(-0.22, Math.min(0.22, (gy - gx) * 1.6));
      if (crack) {
        const cxm = (i + 0.5) * dx, cym = (j + 0.5) * dy, r = Math.hypot(cxm - view.fpf[0], cym - view.fpf[1]);
        if (r < 95) col = mix(col, C.peel, Math.min(1, 1.6 * (1 - r / 95)));
      }
      const f = rgb(col, shade);
      const p1 = P(i * dx, j * dy, a), p2 = P((i + 1) * dx, j * dy, b), p3 = P((i + 1) * dx, (j + 1) * dy, c), p4 = P(i * dx, (j + 1) * dy, d);
      ctx.beginPath(); ctx.moveTo(...p1); ctx.lineTo(...p2); ctx.lineTo(...p3); ctx.lineTo(...p4); ctx.closePath();
      ctx.fillStyle = f; ctx.strokeStyle = f; ctx.lineWidth = 0.75; ctx.fill(); ctx.stroke();
    }
  }
  // alátámasztott élek
  ctx.strokeStyle = C.steel; ctx.lineWidth = 4;
  ctx.beginPath(); ctx.moveTo(...P(0, 0, 0)); ctx.lineTo(...P(A, 0, 0)); ctx.lineTo(...P(A, B, 0)); ctx.lineTo(...P(0, B, 0)); ctx.closePath(); ctx.stroke();
  // méretek
  ctx.fillStyle = C.muted; ctx.font = '600 12px Archivo, system-ui, sans-serif'; ctx.textBaseline = 'top';
  let q = P(A / 2, B, 0); ctx.textAlign = 'right'; ctx.fillText('400 mm', q[0] - 8, q[1] + 8);
  q = P(A, B / 2, 0); ctx.textAlign = 'left'; ctx.fillText('300 mm', q[0] + 8, q[1] + 8);
  // súly középen
  if (view.patch) {
    const c0 = A / 2 - 30, c1 = A / 2 + 30, r0 = B / 2 - 30, r1 = B / 2 + 30, v = sample(A / 2, B / 2), hgt = 40;
    const tp = (x, y) => P(x, y, v - hgt);
    ctx.fillStyle = C.ink;
    poly([P(c1, r0, v), P(c1, r1, v), tp(c1, r1), tp(c1, r0)]); ctx.globalAlpha = 0.8;
    poly([P(c0, r1, v), P(c1, r1, v), tp(c1, r1), tp(c0, r1)]); ctx.globalAlpha = 0.65;
    poly([tp(c0, r0), tp(c1, r0), tp(c1, r1), tp(c0, r1)]); ctx.globalAlpha = 1;
  }
  // első repedés helye
  if (view.fpf) {
    const [x, y] = view.fpf, p = P(x, y, sample(x, y));
    if (crack) {
      ctx.strokeStyle = rgb(C.peel, 0.45); ctx.lineWidth = 3; ctx.beginPath();
      const pts = [[-115, 6], [-84, -8], [-60, 4], [-38, -6], [-20, 5], [0, -3], [18, 7], [36, -5], [58, 3], [82, -7], [112, 5]];
      pts.forEach(([u, w], i) => { const xx = Math.max(0, Math.min(A, x + u)), yy = Math.max(0, Math.min(B, y + w)); const pp = P(xx, yy, sample(xx, yy)); i ? ctx.lineTo(...pp) : ctx.moveTo(...pp); });
      ctx.stroke();
    } else if (!animating) {
      ctx.beginPath(); ctx.arc(p[0], p[1], 8, 0, Math.PI * 2);
      ctx.strokeStyle = C.raised; ctx.lineWidth = 5; ctx.stroke(); ctx.strokeStyle = C.ink; ctx.lineWidth = 2.5; ctx.stroke();
    }
  }
}
function poly(pts) { ctx.beginPath(); ctx.moveTo(...pts[0]); for (const p of pts.slice(1)) ctx.lineTo(...p); ctx.closePath(); ctx.fill(); }

colors();
dark.addEventListener('change', () => { colors(); draw(); });
document.addEventListener('themechange', () => { colors(); draw(); });
new ResizeObserver(size).observe(cv);
syncLoad();
renderStack();
compute();
