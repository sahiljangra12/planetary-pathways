/* Climate study, part 2: the social–climate space, the crossing, the pooled carbon requirement and country profiles. */
(async function () {
  const D = window.CLIMATE;
  if (!D) return;
  const X = await fetch('data/climate-extra.json').then(r => r.json());
  const Y0 = 1990, B = 1.61, B15 = 0.79;
  const QN = ['Shortfall, within boundary', 'Shortfall and overshoot', 'Foundation met, overshoot', 'Safe and just'];
  const QC = ['#f2c14e', '#ef6f6c', '#5aa9ff', '#5fd1b0'];
  const fmt = (v, n = 1) => (v == null ? 'n/a' : (+v).toFixed(n));
  const quad = (c, i, acc = 'cons') => {
    const m = c.met[i], e = c[acc][i];
    if (m == null || e == null) return null;
    return m === 4 ? (e <= B ? 3 : 2) : (e <= B ? 0 : 1);
  };
  const onReveal = (el, fn) => {
    let done = false;
    const go = () => { if (!done) { done = true; fn(); } };
    if (el.classList.contains('in')) go(); else el.addEventListener('reveal', go, { once: true });
  };
  const isos = Object.keys(D.C).filter(i => D.C[i].cons.some(v => v != null)).sort((a, b) => D.C[a].n.localeCompare(D.C[b].n));
  const nameToIso = Object.fromEntries(Object.keys(D.C).map(i => [D.C[i].n.toLowerCase(), i]));

  // =============================================================== the space (animated bubbles)
  (function space() {
    const svg = document.getElementById('space-svg');
    if (!svg) return;
    const W = 1100, H = 560, m = { l: 56, r: 24, t: 24, b: 46 };
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    const lx0 = Math.log(0.04), lx1 = Math.log(60);
    const x = v => m.l + (Math.log(Math.max(0.04, v)) - lx0) / (lx1 - lx0) * (W - m.l - m.r);
    const y = v => m.t + (1 - (v - 0.3) / (1.02 - 0.3)) * (H - m.t - m.b);
    const ax = svgEl('g', { class: 'axis' }, svg);
    [0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 25, 50].forEach(v => {
      svgEl('line', { x1: x(v), x2: x(v), y1: m.t, y2: H - m.b, stroke: 'rgba(255,255,255,.05)' }, ax);
      const t = svgEl('text', { x: x(v), y: H - m.b + 18, 'text-anchor': 'middle' }, ax); t.textContent = v;
    });
    [0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1].forEach(v => {
      svgEl('line', { x1: m.l, x2: W - m.r, y1: y(v), y2: y(v), stroke: 'rgba(255,255,255,.05)' }, ax);
      const t = svgEl('text', { x: m.l - 8, y: y(v) + 4, 'text-anchor': 'end' }, ax); t.textContent = v.toFixed(1);
    });
    const xl = svgEl('text', { x: W - m.r, y: H - 8, 'text-anchor': 'end' }, ax); xl.textContent = 'CO₂ PER PERSON, CONSUMPTION-BASED (T, LOG) →';
    const yl = svgEl('text', { x: m.l, y: m.t - 10 }, ax); yl.textContent = '↑ SOCIAL ATTAINMENT';
    // safe and just corner
    const sj = svgEl('rect', { x: m.l, y: y(1.02), width: x(B) - m.l, height: y(0.985) - y(1.02), fill: 'rgba(95,209,176,.10)', stroke: '#5fd1b0', 'stroke-dasharray': '4 4' }, svg);
    const sjt = svgEl('text', { x: m.l + 10, y: y(0.985) + 18, fill: '#5fd1b0', 'font-family': 'Barlow', 'font-size': 11, 'letter-spacing': '.18em', 'font-weight': 600 }, svg);
    sjt.textContent = 'SAFE AND JUST SPACE';
    svgEl('line', { x1: x(B), x2: x(B), y1: m.t, y2: H - m.b, stroke: '#ffb454', 'stroke-width': 1.5, 'stroke-dasharray': '6 5' }, svg);
    const bt = svgEl('text', { x: x(B) + 8, y: H - m.b - 10, fill: '#ffb454', 'font-family': 'Barlow', 'font-size': 11, 'letter-spacing': '.14em', 'font-weight': 600 }, svg); bt.textContent = '1.61 T BOUNDARY';
    svgEl('line', { x1: m.l, x2: W - m.r, y1: y(1), y2: y(1), stroke: 'rgba(255,255,255,.35)', 'stroke-dasharray': '2 4' }, svg);
    const ft = svgEl('text', { x: W - m.r, y: y(1) + 18, 'text-anchor': 'end', fill: 'rgba(255,255,255,.6)', 'font-family': 'Barlow', 'font-size': 11, 'letter-spacing': '.14em', 'font-weight': 600 }, svg); ft.textContent = 'ALL FOUR THRESHOLDS MET';
    const big = svgEl('text', { x: W - m.r - 4, y: H - m.b - 18, 'text-anchor': 'end', fill: 'rgba(255,255,255,.09)', 'font-family': 'Barlow Condensed', 'font-weight': 700, 'font-size': 120 }, svg);
    const trails = svgEl('g', {}, svg);
    const g = svgEl('g', {}, svg);
    const labels = svgEl('g', {}, svg);
    const S = { year: 1991, region: 'All', hl: ['IND', 'CHN', 'USA', 'BRA', 'CRI', 'NGA'], timer: null };
    const nodes = {};
    const order = [...isos].sort((a, b) => (D.C[b].pop[32] || 0) - (D.C[a].pop[32] || 0));
    for (const iso of order) {
      const c = svgEl('circle', { r: 0, 'fill-opacity': .78, stroke: '#000', 'stroke-width': .7, tabindex: 0 }, g);
      c.style.transition = 'cx .55s linear, cy .55s linear, r .55s, fill .4s, opacity .4s';
      const show = e => {
        const k = D.C[iso], i = S.year - Y0, q = quad(k, i);
        const r = c.getBoundingClientRect();
        showTip(`<b>${k.n}</b>${S.year} · ${q == null ? 'not classified' : QN[q]}<br>CO₂ ${fmt(k.cons[i])} t · attainment ${fmt(k.att[i], 2)}<br>Thresholds met: ${k.met[i] ?? 'n/a'} of 4 · pop. ${fmt(k.pop[i], 0)} m`, e.clientX || r.x, e.clientY || r.y);
      };
      c.addEventListener('pointerenter', show); c.addEventListener('focus', show);
      c.addEventListener('pointerleave', hideTip); c.addEventListener('blur', hideTip);
      c.addEventListener('click', () => toggle(iso));
      nodes[iso] = c;
    }
    function draw() {
      const i = S.year - Y0;
      big.textContent = S.year;
      for (const iso of order) {
        const k = D.C[iso], c = nodes[iso], e = k.cons[i], a = k.att[i];
        const vis = e != null && a != null && (S.region === 'All' || k.c === S.region);
        if (!vis) { c.setAttribute('r', 0); continue; }
        const q = quad(k, i);
        c.setAttribute('cx', x(e)); c.setAttribute('cy', y(Math.min(1, a)));
        c.setAttribute('r', Math.max(3, Math.sqrt(k.pop[i] || 1) * 0.9));
        c.setAttribute('fill', q == null ? '#777' : QC[q]);
        c.setAttribute('opacity', S.hl.length && !S.hl.includes(iso) ? .5 : 1);
        c.setAttribute('stroke', S.hl.includes(iso) ? '#fff' : '#000');
      }
      trails.innerHTML = ''; labels.innerHTML = '';
      for (const iso of S.hl) {
        const k = D.C[iso]; if (!k) continue;
        const pts = [];
        for (let yy = 1991; yy <= S.year; yy++) { const j = yy - Y0; if (k.cons[j] != null && k.att[j] != null) pts.push([x(k.cons[j]), y(Math.min(1, k.att[j]))]); }
        if (pts.length > 1) svgEl('path', { d: 'M' + pts.map(p => p.map(v => v.toFixed(1)).join(',')).join('L'), fill: 'none', stroke: 'rgba(255,255,255,.55)', 'stroke-width': 1.3 }, trails);
        if (pts.length) {
          const [px, py] = pts[pts.length - 1];
          const t = svgEl('text', { x: px + 10, y: py - 8, fill: '#fff', 'font-family': 'Barlow', 'font-weight': 600, 'font-size': 12, 'letter-spacing': '.04em' }, labels);
          t.textContent = k.n;
        }
      }
      document.getElementById('sp-out').textContent = S.year;
      document.getElementById('sp-year').value = S.year;
      const n = isos.filter(iso => quad(D.C[iso], i) === 3).length;
      sjt.textContent = n ? `SAFE AND JUST SPACE · ${n}` : 'SAFE AND JUST SPACE · EMPTY';
      chips();
    }
    function chips() {
      document.getElementById('sp-chips').innerHTML = S.hl.map(i => `<button class="chip" data-i="${i}" aria-label="Remove ${D.C[i].n}">${D.C[i].n} ×</button>`).join('') + (S.hl.length ? '<button class="chip ghost" data-clear>Clear</button>' : '');
    }
    document.getElementById('sp-chips').addEventListener('click', e => {
      const b = e.target.closest('button'); if (!b) return;
      if (b.hasAttribute('data-clear')) S.hl = []; else S.hl = S.hl.filter(i => i !== b.dataset.i);
      draw();
    });
    function toggle(iso) { S.hl = S.hl.includes(iso) ? S.hl.filter(i => i !== iso) : [...S.hl, iso].slice(-8); draw(); }
    const dl = document.getElementById('sp-list');
    dl.innerHTML = isos.map(i => `<option value="${D.C[i].n}">`).join('');
    const find = document.getElementById('sp-find');
    find.addEventListener('change', () => { const iso = nameToIso[find.value.trim().toLowerCase()]; if (iso && !S.hl.includes(iso)) toggle(iso); find.value = ''; });
    const regions = ['All', 'Africa', 'America', 'Asia', 'Europe', 'Oceania'];
    const rg = document.getElementById('sp-region');
    rg.innerHTML = regions.map(r => `<button aria-pressed="${r === 'All'}" data-r="${r}">${r === 'America' ? 'Americas' : r}</button>`).join('');
    rg.addEventListener('click', e => { const b = e.target.closest('button'); if (!b) return; S.region = b.dataset.r; rg.querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', String(x === b))); draw(); });
    document.getElementById('sp-year').addEventListener('input', e => { stop(); S.year = +e.target.value; draw(); });
    const play = document.getElementById('sp-play');
    function stop() { clearInterval(S.timer); S.timer = null; play.textContent = '▶'; }
    function start() {
      if (S.year >= 2022) S.year = 1991;
      play.textContent = '❚❚';
      S.timer = setInterval(() => { if (S.year >= 2022) return stop(); S.year++; draw(); }, 560);
    }
    play.addEventListener('click', () => (S.timer ? stop() : start()));
    // start everything at the centre, then fly in
    order.forEach(iso => { nodes[iso].setAttribute('cx', x(B)); nodes[iso].setAttribute('cy', y(0.65)); });
    onReveal(document.getElementById('spaceviz'), () => { draw(); if (!prefersReducedMotion) setTimeout(start, 900); else { S.year = 2022; draw(); } });
  })();

  // =============================================================== the crossing (beeswarm)
  (function crossing() {
    const svg = document.getElementById('cross');
    if (!svg) return;
    const W = 680, H = 420, m = { l: 20, r: 20, t: 30, b: 40 };
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    const lx0 = Math.log(0.5), lx1 = Math.log(50);
    const x = v => m.l + (Math.log(v) - lx0) / (lx1 - lx0) * (W - m.l - m.r);
    const ax = svgEl('g', { class: 'axis' }, svg);
    [0.5, 1, 2, 5, 10, 20, 50].forEach(v => { const t = svgEl('text', { x: x(v), y: H - 12, 'text-anchor': 'middle' }, ax); t.textContent = v + ' t'; svgEl('line', { x1: x(v), x2: x(v), y1: m.t, y2: H - m.b + 6, stroke: 'rgba(255,255,255,.05)' }, ax); });
    svgEl('rect', { x: m.l, y: m.t, width: x(B) - m.l, height: H - m.t - m.b, fill: 'rgba(95,209,176,.07)' }, svg);
    svgEl('line', { x1: x(B), x2: x(B), y1: m.t - 10, y2: H - m.b + 6, stroke: '#ffb454', 'stroke-width': 2, 'stroke-dasharray': '6 5' }, svg);
    const t1 = svgEl('text', { x: x(B) - 8, y: m.t + 4, 'text-anchor': 'end', fill: '#5fd1b0', 'font-family': 'Barlow', 'font-size': 11, 'font-weight': 600, 'letter-spacing': '.14em' }, svg); t1.textContent = 'WITHIN BOUNDARY: 0';
    const t2 = svgEl('text', { x: x(B) + 8, y: m.t + 4, fill: '#ffb454', 'font-family': 'Barlow', 'font-size': 11, 'font-weight': 600, 'letter-spacing': '.14em' }, svg); t2.textContent = '1.61 T';
    // beeswarm placement around the centre line
    const cy = (m.t + H - m.b) / 2 + 8, r = 9;
    const pts = [...X.crossers].sort((a, b) => a.co2 - b.co2).map(d => ({ ...d, x: x(d.co2) }));
    const placed = [];
    for (const p of pts) {
      let best = null;
      for (let k = 0; k < 40 && best == null; k++) {
        for (const s of k ? [1, -1] : [1]) {
          const yy = cy + s * k * (r * 0.9);
          if (placed.every(q => (q.x - p.x) ** 2 + (q.y - yy) ** 2 >= (2 * r + 1) ** 2)) { best = yy; break; }
        }
      }
      p.py = best ?? cy; placed.push({ x: p.x, y: p.py });
    }
    const decCol = yr => (yr < 2000 ? '#8fd3ff' : yr < 2010 ? '#5aa9ff' : '#b48cff');
    const g = svgEl('g', {}, svg);
    const dots = pts.map((p, k) => {
      const c = svgEl('circle', { cx: p.x, cy: -20, r, fill: decCol(p.y), stroke: '#000', 'stroke-width': 1, tabindex: 0 }, g);
      c.style.transition = `cy .9s cubic-bezier(.3,1.4,.5,1) ${k * 0.035}s, fill .4s`;
      const show = e => showTip(`<b>${p.n}</b>Crossed in ${p.y}<br>${fmt(p.co2)} t CO₂ per person · ${(p.co2 / B).toFixed(1)}× the boundary${p.sust ? '' : '<br>Not sustained for three years'}`, e.clientX || p.x, e.clientY || p.py);
      c.addEventListener('pointerenter', show); c.addEventListener('focus', show);
      c.addEventListener('pointerleave', hideTip); c.addEventListener('blur', hideTip);
      return c;
    });
    ['CHN', 'ARE', 'ALB'].forEach(iso => {
      const p = pts.find(q => q.i === iso); if (!p) return;
      const t = svgEl('text', { x: p.x, y: p.py < cy ? p.py - 13 : p.py + 22, 'text-anchor': 'middle', fill: '#cfd3dc', 'font-family': 'Barlow', 'font-size': 11 }, g);
      t.textContent = `${p.n} ${p.y}`; t.style.opacity = 0; t.style.transition = 'opacity .6s 1.6s'; t.classList.add('lab');
    });
    const leg = document.getElementById('cross-legend');
    function colour(mode) {
      dots.forEach((c, k) => c.setAttribute('fill', mode === 'decade' ? decCol(pts[k].y) : (pts[k].sust ? '#ef6f6c' : '#6f7480')));
      leg.innerHTML = mode === 'decade'
        ? '<span><i style="background:#8fd3ff;border-radius:50%"></i>Crossed in the 1990s</span><span><i style="background:#5aa9ff;border-radius:50%"></i>2000s</span><span><i style="background:#b48cff;border-radius:50%"></i>2010–2022</span>'
        : '<span><i style="background:#ef6f6c;border-radius:50%"></i>Met for at least three years</span><span><i style="background:#6f7480;border-radius:50%"></i>Not sustained</span>';
    }
    document.querySelectorAll('#crossviz [data-c]').forEach(b => b.addEventListener('click', () => {
      document.querySelectorAll('#crossviz [data-c]').forEach(x => x.setAttribute('aria-pressed', String(x === b))); colour(b.dataset.c);
    }));
    colour('decade');
    onReveal(document.getElementById('crossviz'), () => {
      requestAnimationFrame(() => requestAnimationFrame(() => {
        dots.forEach((c, k) => c.setAttribute('cy', pts[k].py));
        g.querySelectorAll('.lab').forEach(t => { t.style.opacity = 1; });
      }));
    });
  })();

  // =============================================================== pooled carbon requirement
  (function req() {
    const svg = document.getElementById('req');
    if (!svg) return;
    const W = 680, H = 420, m = { l: 44, r: 16, t: 14, b: 30 };
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    const lo = Math.log(0.5), hi = Math.log(300);
    const x = v => m.l + (v - 1991) / (2022 - 1991) * (W - m.l - m.r);
    const y = v => m.t + (1 - (Math.log(Math.min(300, Math.max(v, 0.5))) - lo) / (hi - lo)) * (H - m.t - m.b);
    const ax = svgEl('g', { class: 'axis' }, svg);
    [0.5, 1, 2, 5, 10, 20, 50, 100, 300].forEach(v => { svgEl('line', { x1: m.l, x2: W - m.r, y1: y(v), y2: y(v), stroke: 'rgba(255,255,255,.06)' }, ax); const t = svgEl('text', { x: m.l - 8, y: y(v) + 4, 'text-anchor': 'end' }, ax); t.textContent = v; });
    [1991, 2000, 2010, 2022].forEach(v => { const t = svgEl('text', { x: x(v), y: H - 8, 'text-anchor': 'middle' }, ax); t.textContent = v; });
    [[B, '1.61 t · 2 °C boundary', '#ffb454'], [B15, '0.79 t · 1.5 °C', '#8a8f99']].forEach(([v, l, c]) => {
      svgEl('line', { x1: m.l, x2: W - m.r, y1: y(v), y2: y(v), stroke: c, 'stroke-dasharray': '5 5' }, svg);
      const t = svgEl('text', { x: W - m.r, y: y(v) - 6, 'text-anchor': 'end', fill: c, 'font-size': 11, 'font-family': 'Barlow', 'letter-spacing': '.08em' }, svg); t.textContent = l.toUpperCase();
    });
    const layer = svgEl('g', {}, svg);
    const COL = { main: '#ffffff', health: '#5fd1b0', production: '#8fd3ff' };
    const YEARLY = { main: 'main', health: 'health', production: 'prod' };
    function draw(s) {
      layer.innerHTML = '';
      const P = X.pooled[s], col = COL[s];
      const up = P.pts.map(p => [x(p[0]), y(p[3])]), dn = P.pts.map(p => [x(p[0]), y(p[2])]).reverse();
      const band = svgEl('path', { d: 'M' + up.map(q => q.join(',')).join('L') + 'L' + dn.map(q => q.join(',')).join('L') + 'Z', fill: col, 'fill-opacity': .12 }, layer);
      band.style.opacity = 0; band.style.transition = 'opacity 1.2s .4s';
      (D.req[YEARLY[s]] || []).forEach(([yr, est]) => svgEl('circle', { cx: x(yr), cy: y(est), r: 3, fill: col, 'fill-opacity': .45 }, layer));
      const line = svgEl('path', { d: 'M' + P.pts.map(p => `${x(p[0])},${y(p[1])}`).join('L'), fill: 'none', stroke: col, 'stroke-width': 3, class: 'draw' }, layer);
      const len = line.getTotalLength(); line.style.setProperty('--len', len);
      requestAnimationFrame(() => requestAnimationFrame(() => { line.style.strokeDashoffset = 0; band.style.opacity = 1; }));
      const a = P.pts[0], b = P.pts[P.pts.length - 1];
      [[a, 'start'], [b, 'end']].forEach(([p, anc]) => {
        const t = svgEl('text', { x: x(p[0]) + (anc === 'start' ? 6 : -6), y: y(p[1]) - 14, 'text-anchor': anc, fill: col, 'font-family': 'Barlow Condensed', 'font-weight': 700, 'font-size': 22 }, layer);
        t.textContent = `${p[1] >= 10 ? Math.round(p[1]) : fmt(p[1])} t`;
      });
      const note = svgEl('text', { x: x(2022) - 6, y: y(b[1]) + 26, 'text-anchor': 'end', fill: '#a5a9b4', 'font-family': 'Barlow', 'font-size': 12 }, layer);
      note.textContent = `${fmt(P.pct)}% a year (95% CI ${fmt(P.pct_lo)} to ${fmt(P.pct_hi)}) · 2022: ${fmt(b[2])}–${fmt(b[3])} t`;
      P.pts.forEach(p => {
        const h = svgEl('rect', { x: x(p[0]) - 9, y: m.t, width: 18, height: H - m.t - m.b, fill: 'transparent' }, layer);
        h.addEventListener('pointerenter', e => showTip(`<b>${p[0]}</b>Pooled: ${fmt(p[1])} t (95% CI ${fmt(p[2])}–${fmt(p[3])})`, e.clientX, e.clientY));
        h.addEventListener('pointerleave', hideTip);
      });
    }
    document.querySelectorAll('#reqviz [data-s]').forEach(b => b.addEventListener('click', () => {
      document.querySelectorAll('#reqviz [data-s]').forEach(x => x.setAttribute('aria-pressed', String(x === b))); draw(b.dataset.s);
    }));
    onReveal(document.getElementById('reqviz'), () => draw('main'));
  })();

  // =============================================================== country profiles
  (function profile() {
    const sel = document.getElementById('pf-country');
    if (!sel) return;
    sel.innerHTML = isos.map(i => `<option value="${i}"${i === 'IND' ? ' selected' : ''}>${D.C[i].n}</option>`).join('');
    const quick = ['IND', 'CHN', 'USA', 'BRA', 'NGA', 'CRI', 'LKA', 'DEU'];
    const qh = document.getElementById('pf-quick');
    qh.innerHTML = quick.filter(i => D.C[i]).map(i => `<button class="chip" data-i="${i}">${D.C[i].n}</button>`).join('');
    qh.addEventListener('click', e => { const b = e.target.closest('[data-i]'); if (b) { sel.value = b.dataset.i; show(b.dataset.i); } });
    sel.addEventListener('change', () => show(sel.value));
    const PANELS = [
      ['le', 'Life expectancy', 'years', 74, true, 40, 85],
      ['cm', 'Under-5 mortality', 'per 1,000', 25, false, 0, null],
      ['el', 'Electricity access', '%', 95, true, 0, 100],
      ['em', 'Employment', '% of labour force', 94, true, 60, 100],
      ['cons', 'CO₂, consumption', 't per person', B, false, 0, null],
      ['prod', 'CO₂, production', 't per person', B, false, 0, null]
    ];
    function spark(host, key, label, unit, thr, higher, lo, hi, c) {
      const W = 300, H = 140, m = { l: 34, r: 8, t: 26, b: 20 };
      const vals = c[key], v = vals.filter(z => z != null);
      const box = document.createElement('div'); box.className = 'pf-card';
      const last = [...vals].reverse().find(z => z != null);
      box.innerHTML = `<div class="pf-t"><span>${label}</span><b>${last == null ? 'n/a' : fmt(last, key === 'cons' || key === 'prod' ? 2 : 1)}<small> ${unit}</small></b></div>`;
      host.appendChild(box);
      if (!v.length) { box.insertAdjacentHTML('beforeend', '<p class="muted small">No data</p>'); return; }
      const svg = svgEl('svg', { viewBox: `0 0 ${W} ${H}` }, box);
      const ymin = lo ?? 0, ymax = hi ?? Math.max(thr * 1.4, ...v) * 1.08;
      const x = i => m.l + (i - 1) / 31 * (W - m.l - m.r), y = z => m.t + (1 - (z - ymin) / (ymax - ymin)) * (H - m.t - m.b);
      const ax = svgEl('g', { class: 'axis' }, svg);
      [ymin, ymax].forEach(z => { const t = svgEl('text', { x: m.l - 6, y: y(z) + 4, 'text-anchor': 'end' }, ax); t.textContent = Math.round(z); });
      [[1, '1991'], [32, '2022']].forEach(([i, l]) => { const t = svgEl('text', { x: x(i), y: H - 4, 'text-anchor': i === 1 ? 'start' : 'end' }, ax); t.textContent = l; });
      svgEl('line', { x1: m.l, x2: W - m.r, y1: y(thr), y2: y(thr), stroke: '#ffb454', 'stroke-dasharray': '4 4' }, svg);
      const segs = []; let cur = [];
      for (let i = 1; i <= 32; i++) { if (vals[i] == null) { if (cur.length) segs.push(cur); cur = []; } else cur.push([x(i), y(vals[i])]); }
      if (cur.length) segs.push(cur);
      segs.forEach(sg => { const p = svgEl('path', { d: 'M' + sg.map(q => q.join(',')).join('L'), fill: 'none', stroke: 'rgba(255,255,255,.5)', 'stroke-width': 1.5 }, svg); });
      for (let i = 1; i <= 32; i++) {
        if (vals[i] == null) continue;
        const ok = higher ? vals[i] >= thr : vals[i] <= thr;
        const d = svgEl('circle', { cx: x(i), cy: y(vals[i]), r: 2.6, fill: ok ? '#5fd1b0' : '#ef6f6c' }, svg);
        d.addEventListener('pointerenter', e => showTip(`<b>${c.n} · ${1990 + i}</b>${label}: ${fmt(vals[i])} ${unit}`, e.clientX, e.clientY));
        d.addEventListener('pointerleave', hideTip);
      }
    }
    function show(iso) {
      const c = D.C[iso];
      document.getElementById('pf-name').textContent = c.n;
      const i = 32, q = quad(c, i);
      document.getElementById('pf-sub').textContent = `${c.c === 'America' ? 'Americas' : c.c} · ${fmt(c.pop[i], 1)} million people · GDP ${c.gdp[i] == null ? 'n/a' : '$' + Math.round(c.gdp[i]).toLocaleString('en-US')} per person (2011 PPP)`;
      document.getElementById('pf-status').innerHTML = q == null ? '<span class="pill">2022: not classified</span>' : `<span class="pill" style="border-color:${QC[q]};color:${QC[q]}">2022 · ${QN[q]}</span>`;
      const strip = document.getElementById('pf-strip');
      strip.innerHTML = '';
      for (let j = 1; j <= 32; j++) {
        const qq = quad(c, j), s = document.createElement('span');
        s.style.background = qq == null ? '#1a1d22' : QC[qq]; s.title = `${1990 + j}: ${qq == null ? 'not classified' : QN[qq]}`;
        s.style.transitionDelay = (j * 0.015) + 's';
        strip.appendChild(s);
      }
      strip.insertAdjacentHTML('beforeend', '<em>1991</em><em>2022</em>');
      const grid = document.getElementById('pf-grid'); grid.innerHTML = '';
      PANELS.forEach(([k, l, u, t, h, lo, hi]) => spark(grid, k, l, u, t, h, lo, hi, c));
    }
    show('IND');
  })();
})();
