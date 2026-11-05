/* Téma: alapból a készülék beállítását követi; a gomb kézzel vált, és megjegyzi.
   Ha a választás egyezik a készülékével, visszaáll „automatikusra”. A <head>-ben,
   blokkolóan töltjük be, hogy ne villanjon az oldal. */
(function () {
  var KEY = 'kompozit-theme', root = document.documentElement;
  var mq = window.matchMedia ? matchMedia('(prefers-color-scheme: dark)') : { matches: false };
  function stored() { try { return localStorage.getItem(KEY); } catch (e) { return null; } }
  function effective() { var s = root.getAttribute('data-theme'); return s || (mq.matches ? 'dark' : 'light'); }
  function apply(t) {
    if (t) root.setAttribute('data-theme', t); else root.removeAttribute('data-theme');
    var b = document.getElementById('themeToggle');
    if (b) {
      var dark = effective() === 'dark';
      b.setAttribute('aria-pressed', String(dark));
      var T = window.I18N ? I18N.t : function (k, hu) { return hu; };
      b.querySelector('span').textContent = dark ? T('theme.light', 'Világos téma') : T('theme.dark', 'Sötét téma');
      b.title = T('theme.title', 'Világos / sötét téma');
    }
    document.dispatchEvent(new CustomEvent('themechange', { detail: effective() }));
  }
  var s = stored(); if (s === 'light' || s === 'dark') root.setAttribute('data-theme', s);
  document.addEventListener('DOMContentLoaded', function () {
    var b = document.getElementById('themeToggle');
    if (b) b.addEventListener('click', function () {
      var next = effective() === 'dark' ? 'light' : 'dark';
      var sys = mq.matches ? 'dark' : 'light';
      try { if (next === sys) localStorage.removeItem(KEY); else localStorage.setItem(KEY, next); } catch (e) {}
      apply(next === sys ? null : next);
    });
    apply(root.getAttribute('data-theme'));
  });
  document.addEventListener('langchange', function () { apply(root.getAttribute('data-theme')); });
  if (mq.addEventListener) mq.addEventListener('change', function () { if (!stored()) apply(null); });
})();
