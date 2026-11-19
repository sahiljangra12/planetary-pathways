/* Climate study, part 2: the social–climate space, the crossing, the pooled carbon requirement and country profiles. */
(async function () {
  const D = window.CLIMATE;
  if (!D) return;
  const [X, LIVE] = await Promise.all([
    fetch('data/climate-extra.json?v=20261119d').then(r => r.json()),
    // live layer: newest copy on the main branch (refreshed weekly by GitHub Actions), else the deployed copy
    fetch('https://raw.githubusercontent.com/sahiljangra12/planetary-pathways/main/docs/data/live.json', { cache: 'no-store' })
      .then(r => (r.ok ? r.json() : Promise.reject())).catch(() => fetch('data/live.json').then(r => (r.ok ? r.json() : null)).catch(() => null))
  ]);
  const LAST = 2022;
  // newer years shown only where at least 50 countries have a social indicator
  const LIVE_YEARS = LIVE ? [...new Set(Object.values(LIVE.countries).flatMap(c => Object.keys(c.years).map(Number)))]
    .filter(y => y > LAST && Object.values(LIVE.countries).filter(c => c.years[y] && c.years[y].le != null).length >= 50).sort() : [];
  const YMAX = Math.max(LAST, ...LIVE_YEARS);
  const QIDX = { 'Shortfall, within boundary': 0, 'Shortfall and overshoot': 1, 'Foundation met, overshoot': 2, 'Safe and just': 3 };
  const liveRow = (iso, y) => (LIVE && LIVE.countries[iso] ? LIVE.countries[iso].years[y] : null);
  const liveVal = (r, key) => (r == null ? null : key === 'em' ? (r.un == null ? null : 100 - r.un) : r[key]);
  const Y0 = 1990, B = 1.61, B15 = 0.79;
  const QN = ['Shortfall, within boundary', 'Shortfall and overshoot', 'Foundation met, overshoot', 'Safe and just'];
  const QC = ['#f2c14e', '#ef6f6c', '#5aa9ff', '#5fd1b0'];
  const fmt = (v, n = 1) => (v == null ? 'n/a' : (+v).toFixed(n));
  const xr = v => (v / 1.61).toFixed(v / 1.61 < 2 ? 2 : 1); // multiple of the fair share
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
    const viz = document.getElementById('spaceviz');
    Explain.guide(viz, [
      'Each bubble is a <strong>country</strong>; its size is its population and its colour is its situation that year.',
      '<strong>Higher</strong> = closer to meeting all four basic needs. The dotted line at 1.0 means all four are met.',
      '<strong>Further right</strong> = more CO₂ per person. Left of the orange line is within the fair share of 1.61 t.'
    ]);
    const RO = Explain.readout(viz), TK = Explain.takeaway(viz);
    const W = 1100, H = 580, m = { l: 62, r: 24, t: 40, b: 50 };
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
    const xl = svgEl('text', { x: W - m.r, y: H - 10, 'text-anchor': 'end' }, ax); xl.textContent = 'CO₂ PER PERSON PER YEAR, CONSUMPTION-BASED (TONNES, LOG SCALE) →';
    const yl = svgEl('text', { x: 16, y: (m.t + H - m.b) / 2, 'text-anchor': 'middle', transform: `rotate(-90 16 ${(m.t + H - m.b) / 2})` }, ax); yl.textContent = 'SOCIAL ATTAINMENT (1.0 = ALL FOUR NEEDS MET) →';
    // safe and just corner
    svgEl('rect', { x: m.l, y: y(1.02), width: x(B) - m.l, height: y(0.985) - y(1.02), fill: 'rgba(95,209,176,.12)', stroke: '#5fd1b0', 'stroke-dasharray': '4 4' }, svg);
    const sjt = svgEl('text', { x: m.l + 8, y: y(1.02) - 9, fill: '#5fd1b0', 'font-family': 'IBM Plex Mono', 'font-size': 11, 'font-weight': 500, 'letter-spacing': '.08em' }, svg);
    sjt.textContent = 'SAFE AND JUST SPACE';
    svgEl('line', { x1: x(B), x2: x(B), y1: m.t - 14, y2: H - m.b, stroke: '#ffb454', 'stroke-width': 1.5, 'stroke-dasharray': '6 5' }, svg);
    const bt = svgEl('text', { x: x(B) + 8, y: H - m.b - 10, fill: '#ffb454', 'font-family': 'IBM Plex Mono', 'font-size': 11, 'font-weight': 500, 'letter-spacing': '.06em' }, svg); bt.textContent = 'FAIR SHARE 1.61 T';
    svgEl('line', { x1: m.l, x2: W - m.r, y1: y(1), y2: y(1), stroke: 'rgba(255,255,255,.35)', 'stroke-dasharray': '2 4' }, svg);
    const big = svgEl('text', { x: W - m.r - 4, y: H - m.b - 18, 'text-anchor': 'end', fill: 'rgba(255,255,255,.08)', 'font-family': 'Barlow Condensed', 'font-weight': 700, 'font-size': 130 }, svg);
    const trails = svgEl('g', {}, svg);
    const g = svgEl('g', {}, svg);
    const labels = svgEl('g', {}, svg);
    const ann = svgEl('g', {}, svg);
    const S = { year: 1991, region: 'All', hl: ['IND', 'CHN', 'USA', 'BRA', 'CRI', 'NGA'], timer: null };
    const nodes = {};
    const order = [...isos].sort((a, b) => (D.C[b].pop[32] || 0) - (D.C[a].pop[32] || 0));
    for (const iso of order) {
      const c = svgEl('circle', { r: 0, 'fill-opacity': .78, stroke: '#000', 'stroke-width': .7, tabindex: 0 }, g);
      c.style.transition = 'cx .55s linear, cy .55s linear, r .55s, fill .4s, opacity .4s';
      const show = e => {
        const k = D.C[iso], i = S.year - Y0, q = quad(k, i);
        const r = c.getBoundingClientRect();
        showTip(`<b>${k.n}</b>${S.year} · ${q == null ? 'not classified' : QN[q]}<br>CO₂ ${fmt(k.cons[i])} t per person (${xr(k.cons[i])}× fair share)<br>Basic needs met: ${k.met[i] ?? 'n/a'} of 4 · attainment ${fmt(k.att[i], 2)}<br>Population ${fmt(k.pop[i], 0)} million · click to trace its path`, e.clientX || r.x, e.clientY || r.y);
      };
      c.addEventListener('pointerenter', show); c.addEventListener('focus', show);
      c.addEventListener('pointerleave', hideTip); c.addEventListener('blur', hideTip);
      c.addEventListener('click', () => toggle(iso));
      nodes[iso] = c;
    }
    function stats(i) {
      let n = 0, met = 0, within = 0, sj = 0;
      for (const iso of isos) {
        const k = D.C[iso];
        if (S.region !== 'All' && k.c !== S.region) continue;
        const q = quad(k, i); if (q == null) continue;
        n++; if (q >= 2) met++; if (q === 0 || q === 3) within++; if (q === 3) sj++;
      }
      return { n, met, within, sj };
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
      const placed = [];
      for (const iso of S.hl) {
        const k = D.C[iso]; if (!k) continue;
        const pts = [];
        for (let yy = 1991; yy <= S.year; yy++) { const j = yy - Y0; if (k.cons[j] != null && k.att[j] != null) pts.push([x(k.cons[j]), y(Math.min(1, k.att[j]))]); }
        if (pts.length > 1) svgEl('path', { d: 'M' + pts.map(p => p.map(v => v.toFixed(1)).join(',')).join('L'), fill: 'none', stroke: 'rgba(255,255,255,.55)', 'stroke-width': 1.3 }, trails);
        if (pts.length) {
          const [px, py] = pts[pts.length - 1];
          // nudge labels so they never sit on top of each other
          let ly = py - 10;
          for (let t = 0; t < 8 && placed.some(p => Math.abs(p[0] - px) < 90 && Math.abs(p[1] - ly) < 14); t++) ly -= 14;
          placed.push([px, ly]);
          const t = svgEl('text', { x: px + 8, y: ly, fill: '#fff', 'font-family': 'Barlow', 'font-weight': 600, 'font-size': 12.5, 'letter-spacing': '.03em', 'paint-order': 'stroke', stroke: '#000', 'stroke-width': 3 }, labels);
          t.textContent = k.n;
        }
      }
      document.getElementById('sp-out').textContent = S.year;
      document.getElementById('sp-year').value = S.year;
      const st = stats(i);
      sjt.textContent = st.sj ? `SAFE AND JUST SPACE · ${st.sj}` : 'SAFE AND JUST SPACE · EMPTY';
      RO.set([
        ['Year', S.year],
        ['Countries shown', st.n, S.region === 'All' ? 'all regions' : (S.region === 'America' ? 'Americas' : S.region)],
        ['All 4 needs met', st.met, `${Math.round(st.met / st.n * 100)}% of shown`],
        ['Within fair share', st.within, `${Math.round(st.within / st.n * 100)}% of shown`],
        ['Both (safe and just)', st.sj, st.sj ? '' : 'empty', st.sj ? 'up' : 'warn']
      ]);
      TK.set(`In <b>${S.year}</b>, ${st.met} of ${st.n} countries${S.region === 'All' ? '' : ' in ' + (S.region === 'America' ? 'the Americas' : S.region)} met all four basic needs and ${st.within} stayed within the fair share of 1.61 t. ${st.sj ? `${st.sj} managed both.` : '<b>None managed both</b>: every country that reached the top line did so to the right of the orange line.'}`);
      chips();
    }
    function chips() {
      document.getElementById('sp-chips').innerHTML = S.hl.map(i => `<button class="chip" data-i="${i}" aria-label="Remove ${D.C[i].n}">${D.C[i].n} ×</button>`).join('') + (S.hl.length ? '<button class="chip ghost" data-clear>Clear</button>' : '<span class="muted small">Click a bubble or type a name to trace a country’s path.</span>');
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
      S.timer = setInterval(() => { if (S.year >= 2022) { stop(); return annotate(); } S.year++; draw(); }, 560);
    }
    let annotated = false;
    function annotate() {
      if (annotated) return; annotated = true;
      Explain.annotate(ann, { x: x(0.4), y: y(1.0), tx: x(0.12), ty: y(0.9), r: 0.1, ring: false, anchor: 'start', text: ['NO COUNTRY HAS EVER BEEN HERE', 'needs met within the fair share'], color: '#5fd1b0' });
      Explain.annotate(ann, { x: x(B), y: y(0.47), tx: x(B) + 12, ty: y(0.47), ring: false, anchor: 'start', text: ['FAIR SHARE: 1.61 T', 'equal share of a 2 °C budget'], color: '#ffb454', delay: 500 });
    }
    play.addEventListener('click', () => (S.timer ? stop() : start()));
    order.forEach(iso => { nodes[iso].setAttribute('cx', x(B)); nodes[iso].setAttribute('cy', y(0.65)); });
    onReveal(viz, () => { draw(); if (!prefersReducedMotion) setTimeout(start, 900); else { S.year = 2022; draw(); annotate(); } });
  })();

  // =============================================================== the crossing (beeswarm)
  (function crossing() {
    const svg = document.getElementById('cross');
    if (!svg) return;
    const viz = document.getElementById('crossviz');
    Explain.guide(viz, [
      'Each dot is one of the <strong>36 countries</strong> that went from missing a basic need to meeting all four.',
      'Its position shows the <strong>CO₂ per person</strong> it emitted in that year (log scale). Point at a dot for details.',
      'The green zone left of the orange line is the fair share. <strong>It is empty.</strong>'
    ]);
    const W = 1100, H = 380, m = { l: 30, r: 30, t: 34, b: 40 };
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    const lx0 = Math.log(0.5), lx1 = Math.log(50);
    const x = v => m.l + (Math.log(v) - lx0) / (lx1 - lx0) * (W - m.l - m.r);
    const ax = svgEl('g', { class: 'axis' }, svg);
    [0.5, 1, 2, 5, 10, 20, 50].forEach(v => { const t = svgEl('text', { x: x(v), y: H - 12, 'text-anchor': 'middle' }, ax); t.textContent = v + ' t'; svgEl('line', { x1: x(v), x2: x(v), y1: m.t, y2: H - m.b + 6, stroke: 'rgba(255,255,255,.05)' }, ax); });
    svgEl('rect', { x: m.l, y: m.t, width: x(B) - m.l, height: H - m.t - m.b, fill: 'rgba(95,209,176,.07)' }, svg);
    svgEl('line', { x1: x(B), x2: x(B), y1: m.t - 14, y2: H - m.b + 6, stroke: '#ffb454', 'stroke-width': 2, 'stroke-dasharray': '6 5' }, svg);
    const t1 = svgEl('text', { x: x(B) - 10, y: m.t - 4, 'text-anchor': 'end', fill: '#5fd1b0', 'font-family': 'IBM Plex Mono', 'font-size': 11, 'font-weight': 500 }, svg); t1.textContent = 'WITHIN FAIR SHARE: 0 COUNTRIES';
    const t2 = svgEl('text', { x: x(B) + 10, y: m.t - 4, fill: '#ffb454', 'font-family': 'IBM Plex Mono', 'font-size': 11, 'font-weight': 500 }, svg); t2.textContent = '1.61 T →  ABOVE: 36 COUNTRIES';
    const cy = (m.t + H - m.b) / 2 + 4, r = 9;
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
      const show = e => showTip(`<b>${p.n}</b>Met all four needs in ${p.y}<br>${fmt(p.co2)} t CO₂ per person · ${xr(p.co2)}× the fair share${p.sust ? '<br>Kept meeting them for at least three years' : '<br>Not sustained for three years'}`, e.clientX || p.x, e.clientY || p.py);
      c.addEventListener('pointerenter', show); c.addEventListener('focus', show);
      c.addEventListener('pointerleave', hideTip); c.addEventListener('blur', hideTip);
      return c;
    });
    const leg = document.getElementById('cross-legend');
    function colour(mode) {
      dots.forEach((c, k) => c.setAttribute('fill', mode === 'decade' ? decCol(pts[k].y) : (pts[k].sust ? '#ef6f6c' : '#6f7480')));
      leg.innerHTML = mode === 'decade'
        ? '<span><i style="background:#8fd3ff;border-radius:50%"></i>Crossed in the 1990s</span><span><i style="background:#5aa9ff;border-radius:50%"></i>2000s</span><span><i style="background:#b48cff;border-radius:50%"></i>2010–2022</span>'
        : '<span><i style="background:#ef6f6c;border-radius:50%"></i>Met for at least three years</span><span><i style="background:#6f7480;border-radius:50%"></i>Not sustained</span>';
    }
    viz.querySelectorAll('[data-c]').forEach(b => b.addEventListener('click', () => {
      viz.querySelectorAll('[data-c]').forEach(x => x.setAttribute('aria-pressed', String(x === b))); colour(b.dataset.c);
    }));
    colour('decade');
    const co = pts.map(p => p.co2).sort((a, b) => a - b), med = (co[17] + co[18]) / 2, lo = pts[0];
    Explain.readout(viz).set([
      ['Countries crossing', pts.length, '1991–2022'],
      ['Within fair share', 0, 'when they crossed', 'warn'],
      ['Median CO₂ at crossing', fmt(med) + ' t', `${(med / B).toFixed(1)}× the fair share`],
      ['Lowest-carbon crossing', fmt(lo.co2) + ' t', `${lo.n}, ${lo.y}`]
    ]);
    Explain.takeaway(viz).set(`Even the lowest-carbon crossing, <b>${lo.n} in ${lo.y}</b>, emitted ${fmt(lo.co2)} t per person, ${xr(lo.co2)} times the fair share. The typical country crossed at ${fmt(med)} t. On this evidence, no country has yet met all four basic needs on a fair-share carbon budget.`);
    onReveal(viz, () => {
      requestAnimationFrame(() => requestAnimationFrame(() => dots.forEach((c, k) => c.setAttribute('cy', pts[k].py))));
      const marks = [[lo, 'LOWEST'], [pts.find(q => q.i === 'CHN'), 'CHINA'], [pts[pts.length - 1], 'HIGHEST']];
      marks.forEach(([p, lab], k) => {
        if (!p) return;
        const up = p.py < cy;
        const anc = p.x > W - 140 ? 'end' : p.x < 140 ? 'start' : 'middle';
        Explain.annotate(svg, { x: p.x, y: p.py, r: r + 3, tx: anc === 'end' ? p.x + 12 : anc === 'start' ? p.x - 12 : p.x, ty: up ? m.t + 14 : H - m.b - 8, anchor: anc, elbow: anc !== 'middle', text: [`${lab === 'CHINA' ? p.n.toUpperCase() : lab + ': ' + p.n.toUpperCase()}`, `${p.y} · ${fmt(p.co2)} t`], color: '#fff', delay: 1700 + k * 300 });
      });
    });
  })();

  // =============================================================== pooled carbon requirement
  (function req() {
    const svg = document.getElementById('req');
    if (!svg) return;
    const viz = document.getElementById('reqviz');
    Explain.guide(viz, [
      'The <strong>solid line</strong> is the CO₂ per person at which half of all countries meet the chosen needs. Lower means development costs less carbon.',
      'The <strong>shaded band</strong> is its 95% confidence interval; the faint dots are separate one-year estimates.',
      'The <strong>dashed lines</strong> are the fair shares. The vertical gap between line and dashed line is how far there is still to go.'
    ]);
    const RO = Explain.readout(viz), TK = Explain.takeaway(viz);
    const W = 1100, H = 440, m = { l: 50, r: 24, t: 16, b: 32 };
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    const lo = Math.log(0.5), hi = Math.log(300);
    const x = v => m.l + (v - 1991) / (2022 - 1991) * (W - m.l - m.r - 150);
    const y = v => m.t + (1 - (Math.log(Math.min(300, Math.max(v, 0.5))) - lo) / (hi - lo)) * (H - m.t - m.b);
    const ax = svgEl('g', { class: 'axis' }, svg);
    [0.5, 1, 2, 5, 10, 20, 50, 100, 300].forEach(v => { svgEl('line', { x1: m.l, x2: W - m.r, y1: y(v), y2: y(v), stroke: 'rgba(255,255,255,.06)' }, ax); const t = svgEl('text', { x: m.l - 8, y: y(v) + 4, 'text-anchor': 'end' }, ax); t.textContent = v + ' t'; });
    [1991, 1995, 2000, 2005, 2010, 2015, 2022].forEach(v => { const t = svgEl('text', { x: x(v), y: H - 8, 'text-anchor': 'middle' }, ax); t.textContent = v; });
    [[B, 'FAIR SHARE 2 °C · 1.61 T', '#ffb454'], [B15, 'FAIR SHARE 1.5 °C · 0.79 T', '#8a8f99']].forEach(([v, l, c]) => {
      svgEl('line', { x1: m.l, x2: W - m.r, y1: y(v), y2: y(v), stroke: c, 'stroke-dasharray': '5 5' }, svg);
      const t = svgEl('text', { x: m.l + 8, y: y(v) - 7, fill: c, 'font-size': 11, 'font-family': 'IBM Plex Mono', 'font-weight': 500 }, svg); t.textContent = l;
    });
    const layer = svgEl('g', {}, svg);
    const COL = { main: '#ffffff', health: '#5fd1b0', production: '#8fd3ff' };
    const NAME = { main: 'all four needs', health: 'the two health needs', production: 'all four needs (production CO₂)' };
    const YEARLY = { main: 'main', health: 'health', production: 'prod' };
    const leg = document.getElementById('req-legend');
    function draw(s) {
      layer.innerHTML = '';
      const P = X.pooled[s], col = COL[s];
      const up = P.pts.map(p => [x(p[0]), y(p[3])]), dn = P.pts.map(p => [x(p[0]), y(p[2])]).reverse();
      const band = svgEl('path', { d: 'M' + up.map(q => q.join(',')).join('L') + 'L' + dn.map(q => q.join(',')).join('L') + 'Z', fill: col, 'fill-opacity': .2 }, layer);
      band.style.opacity = 0; band.style.transition = 'opacity 1.2s .4s';
      (D.req[YEARLY[s]] || []).forEach(([yr, est]) => svgEl('circle', { cx: x(yr), cy: y(est), r: 3, fill: col, 'fill-opacity': .4 }, layer));
      const line = svgEl('path', { d: 'M' + P.pts.map(p => `${x(p[0])},${y(p[1])}`).join('L'), fill: 'none', stroke: col, 'stroke-width': 3, class: 'draw' }, layer);
      const len = line.getTotalLength(); line.style.setProperty('--len', len);
      requestAnimationFrame(() => requestAnimationFrame(() => { line.style.strokeDashoffset = 0; band.style.opacity = 1; }));
      const a = P.pts[0], b = P.pts[P.pts.length - 1];
      const tv = v => (v >= 10 ? Math.round(v) : fmt(v));
      Explain.annotate(layer, { x: x(a[0]), y: y(a[1]), tx: x(a[0]) + 16, ty: y(a[1]) - 26, anchor: 'start', text: [`1991: ${tv(a[1])} T`, `95% CI ${tv(a[2])}–${tv(a[3])} t`], color: col, delay: 900 });
      Explain.annotate(layer, { x: x(b[0]), y: y(b[1]), tx: x(b[0]) + 16, ty: y(b[1]) - 6, anchor: 'start', text: [`2022: ${tv(b[1])} T`, `95% CI ${tv(b[2])}–${tv(b[3])} t`], color: col, delay: 1300 });
      // the remaining gap at 2022
      const gx = x(2022) + 110, ratio = b[1] / B;
      const gap = svgEl('g', { class: 'annot' }, layer);
      svgEl('line', { x1: gx, x2: gx, y1: y(b[1]), y2: y(B), stroke: '#ffb454', 'stroke-width': 1.5 }, gap);
      svgEl('line', { x1: gx - 5, x2: gx + 5, y1: y(b[1]), y2: y(b[1]), stroke: '#ffb454' }, gap);
      svgEl('line', { x1: gx - 5, x2: gx + 5, y1: y(B), y2: y(B), stroke: '#ffb454' }, gap);
      const gt = svgEl('text', { x: gx + 10, y: (y(b[1]) + y(B)) / 2, fill: '#ffb454', 'font-family': 'IBM Plex Mono', 'font-size': 12, 'font-weight': 500 }, gap); gt.textContent = `${ratio.toFixed(1)}×`;
      const gt2 = svgEl('text', { x: gx + 10, y: (y(b[1]) + y(B)) / 2 + 15, fill: '#a5a9b4', 'font-family': 'IBM Plex Mono', 'font-size': 10.5 }, gap); gt2.textContent = 'THE GAP';
      setTimeout(() => gap.classList.add('on'), prefersReducedMotion ? 0 : 1700);
      P.pts.forEach(p => {
        const h = svgEl('rect', { x: x(p[0]) - 12, y: m.t, width: 24, height: H - m.t - m.b, fill: 'transparent' }, layer);
        h.addEventListener('pointerenter', e => showTip(`<b>${p[0]}</b>Half of countries meet ${NAME[s]} at ${fmt(p[1])} t CO₂ per person<br>95% CI ${fmt(p[2])}–${fmt(p[3])} t · ${(p[1] / B).toFixed(1)}× the fair share`, e.clientX, e.clientY));
        h.addEventListener('pointerleave', hideTip);
      });
      RO.set([
        ['Measure', s === 'main' ? 'All 4 needs' : s === 'health' ? 'Health only' : 'Production CO₂'],
        ['1991', tv(a[1]) + ' t', `95% CI ${tv(a[2])}–${tv(a[3])}`],
        ['2022', fmt(b[1]) + ' t', `95% CI ${fmt(b[2])}–${fmt(b[3])}`],
        ['Change per year', fmt(P.pct) + '%', `95% CI ${fmt(P.pct_lo)} to ${fmt(P.pct_hi)}`, 'up'],
        ['Gap to fair share', ratio.toFixed(1) + '×', '2022 vs 1.61 t', ratio > 1 ? 'warn' : 'up']
      ]);
      TK.set(`For half of countries to meet ${NAME[s]}, it took about <b>${tv(a[1])} t</b> of CO₂ per person in 1991 and <b>${fmt(b[1])} t</b> in 2022: a fall of ${fmt(-P.pct)}% a year (95% CI ${fmt(-P.pct_hi)} to ${fmt(-P.pct_lo)}%). The cost of development in carbon is falling, but in 2022 it was still <b>${ratio.toFixed(1)} times</b> the fair share.`);
      leg.innerHTML = `<span><i style="background:${col}"></i>Pooled estimate</span><span><i style="background:${col};opacity:.3"></i>95% interval</span><span><i style="background:${col};opacity:.45;border-radius:50%"></i>One-year estimates</span>`;
    }
    viz.querySelectorAll('[data-s]').forEach(b => b.addEventListener('click', () => {
      viz.querySelectorAll('[data-s]').forEach(x => x.setAttribute('aria-pressed', String(x === b))); draw(b.dataset.s);
    }));
    onReveal(viz, () => draw('main'));
  })();

  // =============================================================== country profiles
  (function profile() {
    const sel = document.getElementById('pf-country');
    if (!sel) return;
    const viz = document.getElementById('profviz');
    Explain.guide(viz, [
      'The <strong>coloured strip</strong> shows the country\u2019s situation in every year from 1991, using the same four colours as the map.',
      'Each small chart is one basic need or one CO₂ measure. The <strong>orange dashed line</strong> is its threshold.',
      '<strong style="color:#5fd1b0">Green</strong> points pass the threshold, <strong style="color:#ef6f6c">red</strong> points fail. Outlined points are provisional newer data.'
    ]);
    const RO = Explain.readout(viz), TK = Explain.takeaway(viz);
    document.getElementById("pf-strip").after(RO.el);
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
    function spark(host, key, label, unit, thr, higher, lo, hi, c, iso) {
      const W = 300, H = 140, m = { l: 34, r: 8, t: 26, b: 20 };
      const vals = c[key], lv = LIVE_YEARS.map(y => [y - Y0, liveVal(liveRow(iso, y), key)]).filter(p => p[1] != null);
      const v = [...vals.filter(z => z != null), ...lv.map(p => p[1])];
      const box = document.createElement('div'); box.className = 'pf-card';
      const last = [...vals].reverse().find(z => z != null);
      const pass = last == null ? null : (higher ? last >= thr : last <= thr);
      const thrTxt = `${key === 'cons' || key === 'prod' ? 'fair share' : 'threshold'} ${higher ? '≥' : '≤'} ${thr}${key === 'cons' || key === 'prod' ? ' t' : ''}`;
      box.innerHTML = `<div class="pf-t"><span>${label}</span><b>${last == null ? 'n/a' : fmt(last, key === 'cons' || key === 'prod' ? 2 : 1)}<small> ${unit}</small></b></div><div class="pf-thr"><span>${thrTxt}</span>${pass == null ? '' : `<em class="${pass ? 'ok' : 'no'}">${pass ? 'PASS' : 'FAIL'} 2022</em>`}</div>`;
      host.appendChild(box);
      if (!v.length) { box.insertAdjacentHTML('beforeend', '<p class="muted small">No data</p>'); return; }
      const svg = svgEl('svg', { viewBox: `0 0 ${W} ${H}` }, box);
      const ymin = lo ?? 0, ymax = hi ?? Math.max(thr * 1.4, ...v) * 1.08;
      const x = i => m.l + (i - 1) / (YMAX - Y0 - 1) * (W - m.l - m.r), y = z => m.t + (1 - (z - ymin) / (ymax - ymin)) * (H - m.t - m.b);
      const ax = svgEl('g', { class: 'axis' }, svg);
      [ymin, ymax].forEach(z => { const t = svgEl('text', { x: m.l - 6, y: y(z) + 4, 'text-anchor': 'end' }, ax); t.textContent = Math.round(z); });
      [[1, '1991'], [YMAX - Y0, String(YMAX)]].forEach(([i, l]) => { const t = svgEl('text', { x: x(i), y: H - 4, 'text-anchor': i === 1 ? 'start' : 'end' }, ax); t.textContent = l; });
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
      lv.forEach(([i, z]) => {
        const ok = higher ? z >= thr : z <= thr;
        const d = svgEl('circle', { cx: x(i), cy: y(Math.min(ymax, Math.max(ymin, z))), r: 3, fill: '#000', stroke: ok ? '#5fd1b0' : '#ef6f6c', 'stroke-width': 1.5 }, svg);
        d.addEventListener('pointerenter', e => showTip(`<b>${c.n} · ${1990 + i} · provisional</b>${label}: ${fmt(z)} ${unit}<br>Latest public data, not in the paper`, e.clientX, e.clientY));
        d.addEventListener('pointerleave', hideTip);
      });
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
      LIVE_YEARS.forEach(y => {
        const pr = liveRow(iso, y)?.provisional, qq = pr && pr.configuration ? QIDX[pr.configuration] : null, s = document.createElement('span');
        s.className = 'prov'; s.style.background = 'transparent'; s.style.boxShadow = `inset 0 0 0 1.5px ${qq == null ? '#3a3f47' : QC[qq]}`;
        s.title = `${y} (provisional): ${qq == null ? 'not classified, data incomplete' : QN[qq]}`;
        strip.appendChild(s);
      });
      strip.style.gridTemplateColumns = `repeat(${YMAX - Y0},1fr)`;
      strip.insertAdjacentHTML('beforeend', `<em>1991</em><em>${YMAX}${YMAX > LAST ? ' · outlined = provisional' : ''}</em>`);
      const grid = document.getElementById('pf-grid'); grid.innerHTML = '';
      PANELS.forEach(([k, l, u, t, h, lo, hi]) => spark(grid, k, l, u, t, h, lo, hi, c, iso));
      // summary: needs met in 2022, which are missing, emissions vs fair share, years in each situation
      const names = { le: 'life expectancy', cm: 'child survival', el: 'electricity', em: 'employment' };
      const miss = PANELS.slice(0, 4).filter(([k, , , t, h]) => c[k][i] != null && !(h ? c[k][i] >= t : c[k][i] <= t)).map(p => names[p[0]]);
      const yrs = [0, 0, 0, 0]; let first = null;
      for (let j = 1; j <= 32; j++) { const qq = quad(c, j); if (qq != null) yrs[qq]++; if (first == null && c.met[j] === 4) first = 1990 + j; }
      const e = c.cons[i] ?? c.prod[i], basis = c.cons[i] != null ? 'consumption' : 'production';
      RO.set([
        ['Needs met, 2022', c.met[i] == null ? 'n/a' : `${c.met[i]} of 4`, miss.length ? 'missing: ' + miss.join(', ') : 'all four', c.met[i] === 4 ? 'up' : 'down'],
        ['CO₂ per person', e == null ? 'n/a' : fmt(e, 2) + ' t', basis + ', 2022'],
        ['vs fair share', e == null ? 'n/a' : xr(e) + '×', '1.61 t per person', e != null && e > B ? 'down' : 'up'],
        ['First met all four', first ?? 'never', first ? 'since 1991' : 'in 1991–2022'],
        ['Years safe and just', yrs[3], 'of 32', yrs[3] ? 'up' : 'warn']
      ]);
      TK.set(`In 2022 <b>${c.n}</b> met ${c.met[i] ?? 'an unknown number of'} of the four basic needs${miss.length ? ` (falling short on ${miss.join(' and ')})` : ''} and emitted ${e == null ? 'an unknown amount of' : `<b>${fmt(e, 2)} t</b>`} CO₂ per person on a ${basis} basis${e == null ? '' : `, ${e > B ? xr(e) + ' times' : 'within'} the fair share`}. ${first === 1991 ? 'It already met all four in 1991.' : first ? `It first met all four in ${first}.` : 'It has not met all four in any year since 1991.'} ${yrs[3] ? `It was safe and just in ${yrs[3]} years.` : 'It was never safe and just.'}`);
    }
    show('IND');
  })();

  // =============================================================== latest data (provisional)
  (function live() {
    const kv = document.getElementById('lv-kv'); if (!kv) return;
    if (!LIVE) { kv.innerHTML = '<dt>Status</dt><dd>The live feed could not be reached just now. The paper\'s results do not depend on it.</dd>'; return; }
    const d = new Date(LIVE.fetched.replace('Z', ':00Z'));
    document.getElementById('lv-when').textContent = isNaN(d) ? 'weekly' : d.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
    const S = LIVE.sources, C = Object.entries(LIVE.countries);
    // newest year with data for at least half of the 155 countries, per series
    const newest = k => { const cnt = {}; C.forEach(([, c]) => Object.entries(c.years).forEach(([y, r]) => { if (r[k] != null) cnt[y] = (cnt[y] || 0) + 1; })); const ys = Object.keys(cnt).filter(y => cnt[y] >= 78).map(Number); return ys.length ? `${Math.max(...ys)} (${cnt[Math.max(...ys)]} countries)` : 'n/a'; };
    kv.innerHTML = `<dt>Last fetched</dt><dd>${LIVE.fetched.replace('T', ' ')} (UTC)</dd>` +
      ['le', 'cm', 'el', 'un', 'cons', 'prod'].map(k => `<dt>${S[k].label}</dt><dd>newest broad year ${newest(k)} · ${S[k].source}${S[k].last_updated ? ', updated ' + S[k].last_updated : ''}</dd>`).join('') +
      `<dt>Rule</dt><dd>${LIVE.rule}</dd>`;
    // paired change in consumption CO2 per person, 2022 (paper data) to the newest live year, same countries
    const host = document.getElementById('lv-tests');
    const tq = p => { const t = [12.71, 4.30, 3.18, 2.78, 2.57, 2.45, 2.36, 2.31, 2.26, 2.23]; return p <= 10 ? t[p - 1] : 1.96 + 2.4 / p; };
    const paired = (key, label, unit) => {
      let best = null;
      for (const y of LIVE_YEARS) {
        const pairs = Object.keys(D.C).map(iso => [D.C[iso][key][32], liveVal(liveRow(iso, y), key)]).filter(p => p[0] != null && p[1] != null);
        if (pairs.length >= 30) best = { y, pairs };
      }
      if (!best) return '';
      const dif = best.pairs.map(p => p[1] - p[0]), n = dif.length, mu = dif.reduce((a, b) => a + b, 0) / n;
      const sd = Math.sqrt(dif.reduce((a, b) => a + (b - mu) ** 2, 0) / (n - 1)), se = sd / Math.sqrt(n), q = tq(n - 1);
      const lo = mu - q * se, hi = mu + q * se, sig = lo > 0 || hi < 0;
      return `<div class="lv-test"><span class="k">${label}, 2022 → ${best.y}</span><b>${mu >= 0 ? '+' : ''}${fmt(mu, 2)} <small>${unit}</small></b><span class="ci">95% CI ${fmt(lo, 2)} to ${fmt(hi, 2)} · paired t, n = ${n} countries</span><span class="verdict ${sig ? 'yes' : 'no'}">${sig ? 'Change detected' : 'Within uncertainty'}</span></div>`;
    };
    // counts of provisional configurations for each year after the paper
    const rows = LIVE_YEARS.map(y => {
      const cnt = [0, 0, 0, 0]; let un = 0;
      C.forEach(([, c]) => { const r = c.years[y]; if (!r) return; const q = r.provisional && r.provisional.configuration; if (q) cnt[QIDX[q]]++; else un++; });
      const n = cnt.reduce((a, b) => a + b, 0);
      return n ? `<tr><td>${y}</td><td class="n">${n}</td>${[0, 1, 2, 3].map(k => `<td class="n" style="color:${QC[k]}">${cnt[k]}</td>`).join('')}<td class="n muted">${un}</td></tr>` : '';
    }).join('');
    host.innerHTML = paired('cons', 'Consumption CO₂ per person', 't') + paired('le', 'Life expectancy', 'years') +
      (rows ? `<div class="scroll-x" style="grid-column:1/-1"><table class="table"><thead><tr><th>Year</th><th class="n">Classified</th>${QN.map((q, k) => `<th class="n" style="color:${QC[k]}">${q}</th>`).join('')}<th class="n">Incomplete data</th></tr></thead><tbody>${rows}</tbody></table></div>` : '');
    if (!host.innerHTML) host.innerHTML = '<p class="muted small">No years beyond 2022 have enough data yet.</p>';
  })();
})();
