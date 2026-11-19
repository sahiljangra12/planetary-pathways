/* Page logic for the climate study: map, shares, carbon requirement, decoupling, scenarios, robustness. */
(function () {
  const D = window.CLIMATE;
  if (!D) return;
  const Y0 = 1990, B = 1.61, B15 = 0.79;
  const QN = ['Shortfall, within boundary', 'Shortfall and overshoot', 'Foundation met, overshoot', 'Safe and just'];
  const QC = ['#f2c14e', '#ef6f6c', '#5aa9ff', '#5fd1b0'];
  const fmt = (v, n = 1) => (v == null ? 'n/a' : (+v).toFixed(n));
  const quad = (c, i, acc) => {
    const m = c.met[i], e = c[acc][i];
    if (m == null || e == null) return null;
    return m === 4 ? (e <= B ? 3 : 2) : (e <= B ? 0 : 1);
  };
  const onReveal = (el, fn) => {
    let done = false;
    const go = () => { if (!done) { done = true; fn(); } };
    if (el.classList.contains('in')) go(); else el.addEventListener('reveal', go, { once: true });
  };

  // ------------------------------------------------------------- world map
  (async function map() {
    const svg = document.getElementById('map');
    if (!svg) return;
    const world = await fetch('assets/world.json').then(r => r.json());
    const S = { year: 2022, acc: 'cons', timer: null };
    const m = WorldMap(svg, world, {
      include: iso => !!D.C[iso],
      tip: iso => {
        const c = D.C[iso];
        if (!c) return null;
        const i = S.year - Y0, q = quad(c, i, S.acc), e = c[S.acc][i];
        return `<b>${c.n}</b>${S.year} · ${q == null ? 'no classification' : QN[q]}<br>CO₂ (${S.acc === 'cons' ? 'consumption' : 'production'}): ${e == null ? 'n/a' : fmt(e) + ' t'}<br>Thresholds met: ${c.met[i] == null ? 'n/a' : c.met[i] + ' of 4'}`;
      }
    });
    const leg = document.getElementById('map-legend'), note = document.getElementById('map-note');
    const out = document.getElementById('map-out'), yr = document.getElementById('map-year');
    function paint() {
      const i = S.year - Y0, n = [0, 0, 0, 0];
      m.paint(iso => {
        const c = D.C[iso]; if (!c) return null;
        const q = quad(c, i, S.acc); if (q == null) return null;
        n[q]++; return QC[q];
      });
      out.textContent = S.year;
      leg.innerHTML = QN.map((q, k) => `<span><i style="background:${QC[k]}"></i>${q} <strong>${n[k]}</strong></span>`).join('') + '<span><i style="background:#1a1d22"></i>No data</span>';
      const tot = n.reduce((a, b) => a + b, 0);
      note.textContent = `${S.year}: ${tot} countries classified on a ${S.acc === 'cons' ? 'consumption' : 'production'} basis; ${n[3]} safe and just, ${n[2]} meet the foundation while overshooting.`;
    }
    yr.addEventListener('input', () => { S.year = +yr.value; paint(); });
    document.querySelectorAll('#mapviz [data-acc]').forEach(b => b.addEventListener('click', () => {
      S.acc = b.dataset.acc;
      document.querySelectorAll('#mapviz [data-acc]').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
      paint();
    }));
    const play = document.getElementById('map-play');
    const stop = () => { clearInterval(S.timer); S.timer = null; play.textContent = '▶'; play.setAttribute('aria-label', 'Play years'); };
    play.addEventListener('click', () => {
      if (S.timer) return stop();
      if (S.year >= 2022) S.year = 1990;
      play.textContent = '❚❚'; play.setAttribute('aria-label', 'Pause');
      S.timer = setInterval(() => { S.year++; yr.value = S.year; paint(); if (S.year >= 2022) stop(); }, 420);
    });
    paint();
    // autoplay once when first seen
    onReveal(document.getElementById('mapviz'), () => { if (!prefersReducedMotion) { S.year = 1990; play.click(); } });
  })();

  // ------------------------------------------------------------- shares (stacked area)
  (function shares() {
    const svg = document.getElementById('shares');
    if (!svg) return;
    const W = 640, H = 340, m = { l: 40, r: 8, t: 10, b: 28 };
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    const x = y => m.l + (y - 1991) / (2022 - 1991) * (W - m.l - m.r), y = v => m.t + (1 - v) * (H - m.t - m.b);
    const ax = svgEl('g', { class: 'axis' }, svg);
    [0, .25, .5, .75, 1].forEach(v => { svgEl('line', { x1: m.l, x2: W - m.r, y1: y(v), y2: y(v), stroke: 'rgba(255,255,255,.06)' }, ax); const t = svgEl('text', { x: m.l - 8, y: y(v) + 4, 'text-anchor': 'end' }, ax); t.textContent = Math.round(v * 100) + '%'; });
    [1991, 2000, 2010, 2022].forEach(v => { const t = svgEl('text', { x: x(v), y: H - 8, 'text-anchor': 'middle' }, ax); t.textContent = v; });
    const clip = svgEl('clipPath', { id: 'shclip' }, svgEl('defs', {}, svg));
    const cr = svgEl('rect', { x: 0, y: 0, width: 0, height: H }, clip);
    const g = svgEl('g', { 'clip-path': 'url(#shclip)' }, svg);
    const rows = D.q;
    for (let k = 3; k >= 0; k--) {
      // cumulative from bottom: order SW (0) at bottom
      const top = rows.map(r => [x(r[0]), y(r.slice(1, k + 2).reduce((a, b) => a + b, 0))]);
      const bot = rows.map(r => [x(r[0]), y(r.slice(1, k + 1).reduce((a, b) => a + b, 0))]).reverse();
      svgEl('path', { d: 'M' + top.map(p => p.join(',')).join('L') + 'L' + bot.map(p => p.join(',')).join('L') + 'Z', fill: QC[k], opacity: .9 }, g);
    }
    onReveal(document.getElementById('sharesviz'), () => {
      if (prefersReducedMotion) return cr.setAttribute('width', W);
      const t0 = performance.now();
      const step = t => { const k = Math.max(0, Math.min(1, (t - t0) / 1800)), e = 1 - Math.pow(1 - k, 3); cr.setAttribute('width', W * e); if (k < 1) requestAnimationFrame(step); };
      requestAnimationFrame(step);
    });
  })();

  // ------------------------------------------------------------- carbon requirement
  (function req() {
    const svg = document.getElementById('req');
    if (!svg) return;
    const W = 680, H = 420, m = { l: 44, r: 16, t: 14, b: 30 };
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    const lo = Math.log(0.5), hi = Math.log(300);
    const x = v => m.l + (v - 1991) / (2022 - 1991) * (W - m.l - m.r);
    const y = v => m.t + (1 - (Math.log(Math.max(v, 0.5)) - lo) / (hi - lo)) * (H - m.t - m.b);
    const ax = svgEl('g', { class: 'axis' }, svg);
    [0.5, 1, 2, 5, 10, 20, 50, 100, 300].forEach(v => { svgEl('line', { x1: m.l, x2: W - m.r, y1: y(v), y2: y(v), stroke: 'rgba(255,255,255,.06)' }, ax); const t = svgEl('text', { x: m.l - 8, y: y(v) + 4, 'text-anchor': 'end' }, ax); t.textContent = v; });
    [1991, 2000, 2010, 2022].forEach(v => { const t = svgEl('text', { x: x(v), y: H - 8, 'text-anchor': 'middle' }, ax); t.textContent = v; });
    [[B, '1.61 t · 2 °C boundary', '#ffb454'], [B15, '0.79 t · 1.5 °C', '#8a8f99']].forEach(([v, l, c]) => {
      svgEl('line', { x1: m.l, x2: W - m.r, y1: y(v), y2: y(v), stroke: c, 'stroke-dasharray': '5 5' }, svg);
      const t = svgEl('text', { x: W - m.r, y: y(v) - 6, 'text-anchor': 'end', fill: c, 'font-size': 11, 'font-family': 'Barlow', 'letter-spacing': '.08em' }, svg); t.textContent = l.toUpperCase();
    });
    const layer = svgEl('g', {}, svg);
    // pooled trend from the main robustness row: level in 2022 and annual % change
    const main = D.rob[0], end = +main[2], g = +main[3] / 100;
    function draw(series) {
      layer.innerHTML = '';
      const pts = D.req[series];
      const col = series === 'main' ? '#ffffff' : '#5fd1b0';
      const gp = svgEl('g', {}, layer);
      pts.forEach((p, k) => {
        const [yr, est, l, h] = p;
        const wl = svgEl('line', { x1: x(yr), x2: x(yr), y1: y(l), y2: y(h), stroke: col, 'stroke-opacity': .28, 'stroke-width': 2 }, gp);
        const c = svgEl('circle', { cx: x(yr), cy: y(est), r: 3.6, fill: col, opacity: 0 }, gp);
        c.style.transition = `opacity .4s ${k * 0.03}s`; wl.style.transition = c.style.transition; wl.setAttribute('opacity', 0);
        requestAnimationFrame(() => requestAnimationFrame(() => { c.setAttribute('opacity', 1); wl.setAttribute('opacity', 1); }));
        c.addEventListener('pointerenter', e => showTip(`<b>${yr}</b>${fmt(est)} t (95% CI ${fmt(l)}–${fmt(h)})`, e.clientX, e.clientY));
        c.addEventListener('pointerleave', hideTip);
      });
      if (series === 'main') {
        const d = [];
        for (let yr = 1991; yr <= 2022; yr++) d.push([x(yr), y(end / Math.pow(1 + g, 2022 - yr))]);
        const p = svgEl('path', { d: 'M' + d.map(q => q.join(',')).join('L'), fill: 'none', stroke: '#fff', 'stroke-width': 3, class: 'draw' }, layer);
        const len = p.getTotalLength(); p.style.setProperty('--len', len);
        requestAnimationFrame(() => requestAnimationFrame(() => p.style.strokeDashoffset = 0));
        const a = end / Math.pow(1 + g, 2022 - 1991);
        [[1991, a, `≈${Math.round(a)} t`], [2022, end, `${fmt(end)} t`]].forEach(([yr, v, l]) => {
          const t = svgEl('text', { x: x(yr) + (yr === 1991 ? 8 : -8), y: y(v) - 12, 'text-anchor': yr === 1991 ? 'start' : 'end', fill: '#fff', 'font-family': 'Barlow Condensed', 'font-weight': 700, 'font-size': 22 }, layer);
          t.textContent = l;
        });
      }
    }
    document.querySelectorAll('#reqviz [data-s]').forEach(b => b.addEventListener('click', () => {
      document.querySelectorAll('#reqviz [data-s]').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
      draw(b.dataset.s);
    }));
    onReveal(document.getElementById('reqviz'), () => draw('main'));
  })();

  // ------------------------------------------------------------- decoupling dumbbell
  (function dec() {
    const svg = document.getElementById('dec');
    if (!svg) return;
    const rows = D.dec.filter(d => d.w === '2011--2022' && d.cls === 'Absolute' && d.ab).sort((a, b) => a.g - b.g);
    const rh = 15, m = { l: 150, r: 20, t: 22, b: 26 }, W = 640, H = m.t + m.b + rows.length * rh;
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    const xmin = -14, xmax = 0;
    const x = v => m.l + (Math.max(xmin, v) - xmin) / (xmax - xmin) * (W - m.l - m.r);
    const ax = svgEl('g', { class: 'axis' }, svg);
    [-14, -12, -10, -8, -6, -4, -2, 0].forEach(v => { svgEl('line', { x1: x(v), x2: x(v), y1: m.t - 6, y2: H - m.b, stroke: 'rgba(255,255,255,.06)' }, ax); const t = svgEl('text', { x: x(v), y: H - 8, 'text-anchor': 'middle' }, ax); t.textContent = v + '%'; });
    const g = svgEl('g', {}, svg);
    rows.forEach((d, k) => {
      const yy = m.t + k * rh + rh / 2;
      const lab = svgEl('text', { x: m.l - 10, y: yy + 4, 'text-anchor': 'end', fill: d.ok ? '#5fd1b0' : '#a5a9b4', 'font-size': 11, 'font-family': 'Barlow' }, g); lab.textContent = d.n;
      const ln = svgEl('line', { x1: x(d.g), x2: x(d.g), y1: yy, y2: yy, stroke: d.ok ? '#5fd1b0' : 'rgba(255,180,84,.45)', 'stroke-width': 2 }, g);
      const req = svgEl('rect', { x: x(d.req) - 3.5, y: yy - 3.5, width: 7, height: 7, fill: '#ffb454', transform: `rotate(45 ${x(d.req)} ${yy})`, opacity: 0 }, g);
      const ach = svgEl('circle', { cx: x(d.g), cy: yy, r: 4, fill: d.ok ? '#5fd1b0' : '#fff' }, g);
      const tipH = `<b>${d.n}</b>Achieved ${fmt(d.g)}%/yr · required ${fmt(d.req)}%/yr<br>CO₂ in 2022: ${fmt(d.last)} t`;
      [ach, req, lab].forEach(n => { n.addEventListener('pointerenter', e => showTip(tipH, e.clientX, e.clientY)); n.addEventListener('pointerleave', hideTip); });
      ln.dataset.to = x(d.req); req.dataset.k = k;
    });
    onReveal(document.getElementById('decviz'), () => {
      g.querySelectorAll('line').forEach((ln, k) => {
        ln.style.transition = `all .9s cubic-bezier(.2,.7,.1,1) ${k * 0.025}s`;
        requestAnimationFrame(() => requestAnimationFrame(() => ln.setAttribute('x2', ln.dataset.to)));
      });
      g.querySelectorAll('rect').forEach((r, k) => { r.style.transition = `opacity .4s ${0.6 + k * 0.025}s`; requestAnimationFrame(() => requestAnimationFrame(() => r.setAttribute('opacity', 1))); });
    });
  })();

  // ------------------------------------------------------------- scenarios
  (function scen() {
    const host = document.getElementById('scen');
    if (!host) return;
    host.innerHTML = D.scen.map(s => `<div class="scen-row"><span class="scen-l">${s[0].replace('--', '–')}<small>median ${fmt(-s[1])}% a year</small></span><span class="scen-bar"><i style="--w:${(s[2] / s[3] * 100).toFixed(1)}%"></i></span><b>${s[2]}</b></div>`).join('');
  })();

  // ------------------------------------------------------------- robustness
  const rb = document.querySelector('#rob tbody');
  if (rb) rb.innerHTML = D.rob.map(r => `<tr><td>${r[0]}</td><td class="n">${r[1]}</td><td class="n">${r[2] === '' ? 'n/a' : fmt(r[2])}</td><td class="n">${r[3] === '' ? 'n/a' : fmt(r[3]) + '%'}</td></tr>`).join('');
})();
