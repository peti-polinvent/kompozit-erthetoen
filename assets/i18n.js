/* Többnyelvűség (hu = forrás, a HTML-ben; en/de/zh = assets/i18n/*.json).
   A <head>-ben, blokkolóan töltjük be (a theme.js előtt). Nyelv: mentett választás,
   különben a böngésző nyelve, különben magyar. Váltáskor 'langchange' eseményt küld. */
(function () {
  var KEY = 'kompozit-lang', LANGS = ['hu', 'en', 'de', 'zh'];
  var LOCALE = { hu: 'hu-HU', en: 'en-GB', de: 'de-DE', zh: 'zh-CN' };
  var root = document.documentElement, dicts = {}, cur = 'hu', domReady = false;
  var base = (document.currentScript && document.currentScript.src || '').replace(/[^\/]*$/, '');

  function stored() { try { return localStorage.getItem(KEY); } catch (e) { return null; } }
  function detect() {
    var s = stored(); if (LANGS.indexOf(s) >= 0) return s;
    var l = (navigator.languages || [navigator.language || '']);
    for (var i = 0; i < l.length; i++) { var c = String(l[i]).slice(0, 2).toLowerCase(); if (LANGS.indexOf(c) >= 0) return c; }
    return 'hu';
  }
  function fill(s, v) { return v ? String(s).replace(/\{(\w+)\}/g, function (m, k) { return k in v ? v[k] : m; }) : s; }
  function t(k, hu, v) {
    var d = dicts[cur], s = (cur !== 'hu' && d && k in d) ? d[k] : hu;
    return fill(s == null ? k : s, v);
  }
  function load(l) {
    if (l === 'hu' || dicts[l]) return Promise.resolve();
    return fetch(base + 'i18n/' + l + '.json').then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (d) { dicts[l] = d; });
  }

  function remember(el, prop, val) { if (!el.__hu) el.__hu = {}; if (!(prop in el.__hu)) el.__hu[prop] = val; return el.__hu[prop]; }
  function apply() {
    var d = cur === 'hu' ? null : dicts[cur] || {};
    root.lang = cur === 'zh' ? 'zh-Hans' : cur;
    root.setAttribute('data-lang', cur);
    document.querySelectorAll('[data-i18n]').forEach(function (el) {
      var hu = remember(el, 'text', el.textContent), k = el.getAttribute('data-i18n');
      el.textContent = d && k in d ? d[k] : hu;
    });
    document.querySelectorAll('[data-i18n-html]').forEach(function (el) {
      var hu = remember(el, 'html', el.innerHTML), k = el.getAttribute('data-i18n-html');
      el.innerHTML = d && k in d ? d[k] : hu;
    });
    document.querySelectorAll('[data-i18n-attr]').forEach(function (el) {
      el.getAttribute('data-i18n-attr').split(';').forEach(function (pair) {
        var p = pair.split(':'), a = p[0].trim(), k = (p[1] || '').trim(); if (!a || !k) return;
        var hu = remember(el, '@' + a, el.getAttribute(a));
        el.setAttribute(a, d && k in d ? d[k] : hu);
      });
    });
    document.querySelectorAll('.only-xl').forEach(function (el) { el.hidden = cur === 'hu'; });
    var sel = document.getElementById('langSel'); if (sel) sel.value = cur;
    video();
    root.classList.remove('i18n-wait');
    document.dispatchEvent(new CustomEvent('langchange', { detail: { lang: cur, locale: LOCALE[cur] } }));
  }

  /* videó: honosított változat, ha létezik (HEAD), különben a magyar + megjegyzés */
  var headCache = {};
  function exists(u) {
    if (!(u in headCache)) headCache[u] = fetch(u, { method: 'HEAD', cache: 'no-store' }).then(function (r) { return r.ok; }, function () { return false; });
    return headCache[u];
  }
  function video() {
    var v = document.getElementById('vid'); if (!v) return;
    var src = v.querySelector('source'), tr = v.querySelector('track'), note = document.getElementById('filmNote');
    var o = { src: remember(v, 'src', src.getAttribute('src')), poster: remember(v, 'poster', v.getAttribute('poster')),
      track: tr && remember(v, 'track', tr.getAttribute('src')) };
    var q = (o.src.match(/\?.*$/) || [''])[0], l = cur;
    function set(s, p, t, lang, label, local) {
      if (src.getAttribute('src') !== s) { src.setAttribute('src', s); if (p) v.setAttribute('poster', p); v.load(); }
      if (tr && t) { tr.setAttribute('src', t); tr.setAttribute('srclang', lang); tr.setAttribute('label', label); }
      document.querySelectorAll('[data-video-link]').forEach(function (a) { a.setAttribute('href', s.replace(/\?.*$/, '')); });
      if (note) note.setAttribute('data-local', local ? '1' : '0');
      document.dispatchEvent(new CustomEvent('videochange', { detail: { localized: local } }));
    }
    if (l === 'hu') { set(o.src, o.poster, o.track, 'hu', 'magyar', true); return; }
    var mp4 = 'assets/kompozit_erthetoen_' + l + '.mp4';
    exists(mp4).then(function (ok) {
      if (cur !== l) return;
      if (!ok) { set(o.src, o.poster, o.track, 'hu', 'magyar', false); return; }
      Promise.all([exists('assets/kompozit_erthetoen_' + l + '.vtt'), exists('assets/poster_' + l + '.jpg')]).then(function (r) {
        if (cur !== l) return;
        set(mp4 + q, r[1] ? 'assets/poster_' + l + '.jpg' + q : o.poster, r[0] ? 'assets/kompozit_erthetoen_' + l + '.vtt' + q : o.track,
          r[0] ? l : 'hu', r[0] ? ({ en: 'English', de: 'Deutsch', zh: '中文' })[l] : 'magyar', true);
      });
    });
  }

  function setLang(l) {
    if (LANGS.indexOf(l) < 0) l = 'hu';
    try { localStorage.setItem(KEY, l); } catch (e) {}
    return load(l).then(function () { cur = l; if (domReady) apply(); }, function () { cur = 'hu'; if (domReady) apply(); });
  }

  window.I18N = {
    get lang() { return cur; }, get locale() { return LOCALE[cur]; },
    t: t, set: setLang,
    num: function (n, d, dmax) { return Number(n).toLocaleString(LOCALE[cur], { minimumFractionDigits: d, maximumFractionDigits: dmax == null ? d : dmax }); }
  };

  var first = detect();
  if (first !== 'hu') {
    root.classList.add('i18n-wait');
    var st = document.createElement('style'); st.textContent = '.i18n-wait body{opacity:0}'; document.head.appendChild(st);
    setTimeout(function () { root.classList.remove('i18n-wait'); }, 1500);
  }
  root.lang = first === 'zh' ? 'zh-Hans' : first;
  var ready = load(first).then(function () { cur = first; }, function () { cur = 'hu'; });
  document.addEventListener('DOMContentLoaded', function () {
    var sel = document.getElementById('langSel');
    if (sel) sel.addEventListener('change', function () { setLang(sel.value); });
    ready.then(function () { domReady = true; apply(); });
  });
})();
