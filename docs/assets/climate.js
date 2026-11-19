/* Page logic for the climate study: glossary, map, shares, decoupling, scenarios, robustness. */
window.GLOSSARY = {
  foundation: ['Social foundation', 'The minimum for a decent life used here: life expectancy of at least 74 years, under-5 mortality of at most 25 per 1,000 births, electricity for at least 95% of people and employment for at least 94% of the labour force. A country meets it only when all four are met in the same year.'],
  boundary: ['Climate boundary (fair share)', 'An equal share for every person of the CO₂ the world can still emit while keeping warming below 2 °C: 1.61 t per person per year. The 1.5 °C share is 0.79 t.'],
  consumption: ['Consumption-based CO₂', 'Emissions counted where goods and services are used. Emissions released abroad to make imported goods count for the importing country; emissions from exports count for the buyer.'],
  production: ['Production-based CO₂', 'Emissions counted where they are physically released, inside a country’s borders, whoever uses the goods.'],
  config: ['Situation (configuration)', 'Which of the four combinations of the two tests a country is in: shortfall within the boundary, shortfall and overshoot, foundation met with overshoot, or safe and just.'],
  sj: ['Safe and just space', 'Meeting all four basic needs while emitting no more than the fair share of 1.61 t CO₂ per person. No country with consumption-based data reached it in 1990–2022.'],
  overshoot: ['Overshoot', 'Emitting more CO₂ per person than the fair share of 1.61 t a year.'],
  shortfall: ['Shortfall', 'Missing at least one of the four basic-needs thresholds.'],
  attainment: ['Social attainment', 'A 0-to-1 score: each indicator is divided by its threshold (inverted for mortality), capped at 1, and the four are averaged. It is 1.0 only when every threshold is met.'],
  crossing: ['Crossing', 'The first year a country goes from missing at least one threshold to meeting all four.'],
  requirement: ['Carbon requirement', 'The CO₂ per person at which a model predicts that half of countries meet the social foundation. A summary of what development has typically cost in carbon, not a target for any single country.'],
  logistic: ['Logistic model', 'A regression for yes/no outcomes. Here it estimates how the chance of meeting the foundation rises with (log) CO₂ per person, so the 50% point can be read off.'],
  bootstrap: ['Bootstrap interval', 'Uncertainty found by re-running the estimate thousands of times on samples of countries drawn with replacement. The middle 95% of the results forms the interval.'],
  ci: ['95% confidence interval', 'A range that would contain the true value in 95% of repeated samples. Narrow means precise; if a change’s interval excludes zero, the change is statistically significant at 5%.'],
  log: ['Log scale', 'An axis where each step multiplies the value (0.5, 1, 2, 5, 10…) instead of adding to it, so small and very large emitters fit on one chart and equal distances mean equal percentage differences.'],
  decoupling: ['Absolute decoupling', 'Income (GDP per person) grows while CO₂ per person falls. Relative decoupling means emissions grow, but more slowly than income.'],
  pooled: ['Pooled estimate', 'One model fitted to all years together with a time trend, which smooths the year-to-year noise of separate yearly estimates.'],
  provisional: ['Provisional data', 'The newest public values, fetched weekly. They are not part of the paper, are not gap-filled and may be revised by the source.'],
  paired: ['Paired comparison', 'Compares the same countries at two dates, so differences between countries do not blur the change. The interval comes from a paired t-test.']
};

(function () {
  const D = window.CLIMATE;
  if (!D) return;
  const Y0 = 1990, B = 1.61;
  const QN = ['Shortfall, within boundary', 'Shortfall and overshoot', 'Foundation met, overshoot', 'Safe and just'];
  const QC = ['#f2c14e', '#ef6f6c', '#5aa9ff', '#5fd1b0'];
  const fmt = (v, n = 1) => (v == null ? 'n/a' : (+v).toFixed(n));
  const pct = v => Math.round(v * 100) + '%';
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
  const sw = (k, txt) => `<i class="sw" style="background:${QC[k]}"></i>${txt}`;
  Explain.terms();
  Explain.glossary(document.getElementById('gloss'));

  // ------------------------------------------------------------- world map
  (async function map() {
    const svg = document.getElementById('map');
    if (!svg) return;
    const viz = document.getElementById('mapviz');
    Explain.guide(viz, [
      'Each country is coloured by its <strong>situation</strong> in the chosen year: ' + sw(0, 'needs unmet, low CO₂') + ', ' + sw(1, 'needs unmet, high CO₂') + ', ' + sw(2, 'needs met, high CO₂') + ', ' + sw(3, 'safe and just') + '.',
      'Drag the slider or press <strong>▶</strong> to move through 1991–2022. Point at a country for its numbers.',
      'Dark grey means no estimate for that year. <strong>Production</strong> counts emissions where they are released and covers all 155 countries.'
    ]);
    const RO = Explain.readout(viz), TK = Explain.takeaway(viz);
    const world = await fetch('assets/world.json').then(r => r.json());
    const S = { year: 2022, acc: 'cons', timer: null };
    const m = WorldMap(svg, world, {
      include: iso => !!D.C[iso],
      tip: iso => {
        const c = D.C[iso];
        if (!c) return null;
        const i = S.year - Y0, q = quad(c, i, S.acc), e = c[S.acc][i];
        return `<b>${c.n}</b>${S.year} · ${q == null ? 'not classified' : QN[q]}<br>CO₂ (${S.acc === 'cons' ? 'consumption' : 'production'}): ${e == null ? 'n/a' : fmt(e) + ' t'}${e == null ? '' : ` · ${(e / B).toFixed(1)}× the fair share`}<br>Basic needs met: ${c.met[i] == null ? 'n/a' : c.met[i] + ' of 4'}`;
      }
    });
    const leg = document.getElementById('map-legend'), note = document.getElementById('map-note');
    const out = document.getElementById('map-out'), yr = document.getElementById('map-year');
    const counts = (year, acc) => {
      const i = year - Y0, n = [0, 0, 0, 0];
      for (const iso in D.C) { const q = quad(D.C[iso], i, acc); if (q != null) n[q]++; }
      return n;
    };
    function paint() {
      const i = S.year - Y0;
      m.paint(iso => { const c = D.C[iso]; if (!c) return null; const q = quad(c, i, S.acc); return q == null ? null : QC[q]; });
      const n = counts(S.year, S.acc), tot = n.reduce((a, b) => a + b, 0), n0 = counts(1991, S.acc), t0 = n0.reduce((a, b) => a + b, 0);
      out.textContent = S.year;
      leg.innerHTML = QN.map((q, k) => `<span><i style="background:${QC[k]}"></i>${q} <strong>${n[k]}</strong></span>`).join('') + '<span><i style="background:#1a1d22"></i>No data</span>';
      note.textContent = `${S.acc === 'cons' ? 'Consumption' : 'Production'}-based emissions. Counts are countries with complete data for that year.`;
      RO.set([
        ['Year', S.year],
        ['Countries classified', tot],
        ['Needs unmet', n[0] + n[1], `${pct((n[0] + n[1]) / tot)} of classified`],
        ['Needs met, overshoot', n[2], `${pct(n[2] / tot)} · 1991: ${pct(n0[2] / t0)}`],
        ['Safe and just', n[3], n[3] ? 'within the fair share' : 'none', n[3] ? 'up' : 'warn']
      ]);
      TK.set(`In <b>${S.year}</b>, ${n[2]} of ${tot} countries met all four basic needs, and every one of them emitted more than the fair share. ${n[0] + n[1]} still missed at least one need${n[0] ? `; ${n[0]} of those stayed within the fair share` : ''}. ${n[3] ? `${n[3]} ${n[3] === 1 ? 'was' : 'were'} safe and just.` : 'No country was safe and just.'}`);
    }
    yr.addEventListener('input', () => { stop(); S.year = +yr.value; paint(); });
    viz.querySelectorAll('[data-acc]').forEach(b => b.addEventListener('click', () => {
      S.acc = b.dataset.acc;
      viz.querySelectorAll('[data-acc]').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
      paint();
    }));
    const play = document.getElementById('map-play');
    function stop() { clearInterval(S.timer); S.timer = null; play.textContent = '▶'; play.setAttribute('aria-label', 'Play years'); }
    play.addEventListener('click', () => {
      if (S.timer) return stop();
      if (S.year >= 2022) S.year = 1991;
      play.textContent = '❚❚'; play.setAttribute('aria-label', 'Pause');
      S.timer = setInterval(() => { S.year++; yr.value = S.year; paint(); if (S.year >= 2022) stop(); }, 420);
    });
    paint();
    onReveal(viz, () => { if (!prefersReducedMotion) { S.year = 1991; yr.value = 1991; paint(); play.click(); } });
  })();

  // ------------------------------------------------------------- shares (stacked area)
  (function shares() {
    const svg = document.getElementById('shares');
    if (!svg) return;
    const viz = document.getElementById('sharesviz');
    Explain.guide(viz, [
      'Each coloured band is the <strong>share of countries</strong> in one situation; the four bands add up to 100%.',
      'Read a year straight up from the axis. <strong>Point at the chart</strong> to see that year’s numbers.',
      'The thin green band for <span class="sw" style="background:#5fd1b0"></span>safe and just never appears: it is 0% in every year.'
    ]);
    const RO = Explain.readout(viz), TK = Explain.takeaway(viz);
    const W = 1100, H = 360, m = { l: 44, r: 210, t: 12, b: 30 };
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    const x = y => m.l + (y - 1991) / (2022 - 1991) * (W - m.l - m.r), y = v => m.t + (1 - v) * (H - m.t - m.b);
    const ax = svgEl('g', { class: 'axis' }, svg);
    [0, .25, .5, .75, 1].forEach(v => { svgEl('line', { x1: m.l, x2: W - m.r, y1: y(v), y2: y(v), stroke: 'rgba(255,255,255,.06)' }, ax); const t = svgEl('text', { x: m.l - 8, y: y(v) + 4, 'text-anchor': 'end' }, ax); t.textContent = Math.round(v * 100) + '%'; });
    [1991, 1995, 2000, 2005, 2010, 2015, 2022].forEach(v => { const t = svgEl('text', { x: x(v), y: H - 8, 'text-anchor': 'middle' }, ax); t.textContent = v; });
    const clip = svgEl('clipPath', { id: 'shclip' }, svgEl('defs', {}, svg));
    const cr = svgEl('rect', { x: 0, y: 0, width: 0, height: H }, clip);
    const g = svgEl('g', { 'clip-path': 'url(#shclip)' }, svg);
    const rows = D.q, last = rows[rows.length - 1], first = rows[0];
    for (let k = 3; k >= 0; k--) {
      const top = rows.map(r => [x(r[0]), y(r.slice(1, k + 2).reduce((a, b) => a + b, 0))]);
      const bot = rows.map(r => [x(r[0]), y(r.slice(1, k + 1).reduce((a, b) => a + b, 0))]).reverse();
      svgEl('path', { d: 'M' + top.map(p => p.join(',')).join('L') + 'L' + bot.map(p => p.join(',')).join('L') + 'Z', fill: QC[k], opacity: .9 }, g);
    }
    // end labels: share of each band in 2022, placed at the band's middle
    const ann = svgEl('g', {}, svg);
    const cursor = svgEl('line', { y1: m.t, y2: H - m.b, stroke: '#fff', 'stroke-width': 1, opacity: 0 }, svg);
    function set(r) {
      const tot = r.slice(1).reduce((a, b) => a + b, 0) || 1;
      RO.set([
        ['Year', r[0]],
        ['Needs unmet, within', pct(r[1] / tot)],
        ['Needs unmet, overshoot', pct(r[2] / tot)],
        ['Needs met, overshoot', pct(r[3] / tot), r[0] === 1991 ? '' : `1991: ${pct(first[3])}`],
        ['Safe and just', pct(r[4] / tot), '', r[4] ? 'up' : 'warn']
      ]);
    }
    set(last);
    TK.set(`The share of countries meeting all four basic needs rose from <b>${pct(first[3])}</b> in 1991 to <b>${pct(last[3])}</b> in 2022, and every one of them overshot the fair share. The share with unmet needs and low emissions fell from ${pct(first[1])} to ${pct(last[1])}: countries left that group by raising emissions as well as living standards.`);
    const hit = svgEl('rect', { x: m.l, y: m.t, width: W - m.l - m.r, height: H - m.t - m.b, fill: 'transparent' }, svg);
    hit.addEventListener('pointermove', e => {
      const b = svg.getBoundingClientRect(), vx = (e.clientX - b.left) / b.width * W;
      const yr = Math.max(1991, Math.min(2022, Math.round(1991 + (vx - m.l) / (W - m.l - m.r) * 31)));
      const r = rows.find(z => z[0] === yr); if (!r) return;
      cursor.setAttribute('x1', x(yr)); cursor.setAttribute('x2', x(yr)); cursor.setAttribute('opacity', .6);
      set(r);
    });
    hit.addEventListener('pointerleave', () => { cursor.setAttribute('opacity', 0); set(last); });
    onReveal(viz, () => {
      const labels = () => {
        let acc = 0;
        [0, 1, 2].forEach(k => {
          const v = last[k + 1], mid = acc + v / 2; acc += v;
          Explain.annotate(ann, { x: x(2022), y: y(mid), tx: x(2022) + 22, ty: y(mid), text: [QN[k].toUpperCase(), `${pct(v)} in 2022`], color: QC[k], r: 3, delay: 200 + k * 250 });
        });
        Explain.annotate(ann, { x: x(2022), y: y(1), tx: x(2022) + 22, ty: y(1) + 6, text: ['SAFE AND JUST', '0% every year'], color: QC[3], r: 3, delay: 1000 });
      };
      if (prefersReducedMotion) { cr.setAttribute('width', W); return labels(); }
      const t0 = performance.now();
      const step = t => { const k = Math.max(0, Math.min(1, (t - t0) / 1800)), e = 1 - Math.pow(1 - k, 3); cr.setAttribute('width', W * e); if (k < 1) requestAnimationFrame(step); else labels(); };
      requestAnimationFrame(step);
    });
  })();

  // ------------------------------------------------------------- decoupling dumbbell
  (function dec() {
    const svg = document.getElementById('dec');
    if (!svg) return;
    const viz = document.getElementById('decviz');
    Explain.guide(viz, [
      'Each row is a country whose economy grew while its CO₂ per person <strong>fell</strong> in 2011–2022, but which is still above the fair share.',
      'The <strong>white dot</strong> is how fast it actually cut emissions each year. The <strong>orange diamond</strong> is the yearly cut it would need to reach 1.61 t by 2050.',
      'The orange line is the gap. Rows in <strong style="color:#5fd1b0">green</strong> are already cutting fast enough.'
    ]);
    const rows = D.dec.filter(d => d.w === '2011--2022' && d.cls === 'Absolute' && d.ab).sort((a, b) => a.g - b.g);
    const med = a => { const s = [...a].sort((p, q) => p - q), n = s.length; return n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2; };
    const mg = med(rows.map(d => d.g)), mr = med(rows.map(d => d.req)), ok = rows.filter(d => d.ok);
    Explain.readout(viz).set([
      ['Countries', rows.length, 'decoupling, above 1.61 t'],
      ['On track for 2050', ok.length, ok.map(d => d.n).join(', '), 'warn'],
      ['Median cut achieved', fmt(mg) + '%', 'per year'],
      ['Median cut required', fmt(mr) + '%', 'per year'],
      ['Speed-up needed', (mr / mg).toFixed(1) + '×', 'median country']
    ]);
    const W = 1100, rh = 17, m = { l: 170, r: 30, t: 24, b: 30 }, H = m.t + m.b + rows.length * rh;
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    const xmin = -14, xmax = 0;
    const x = v => m.l + (Math.max(xmin, v) - xmin) / (xmax - xmin) * (W - m.l - m.r);
    const ax = svgEl('g', { class: 'axis' }, svg);
    [-14, -12, -10, -8, -6, -4, -2, 0].forEach(v => { svgEl('line', { x1: x(v), x2: x(v), y1: m.t - 6, y2: H - m.b, stroke: 'rgba(255,255,255,.06)' }, ax); const t = svgEl('text', { x: x(v), y: H - 8, 'text-anchor': 'middle' }, ax); t.textContent = v + '% / yr'; });
    const ttl = svgEl('text', { x: x(-14), y: 12 }, ax); ttl.textContent = '← FASTER CUTS';
    const ttr = svgEl('text', { x: x(0), y: 12, 'text-anchor': 'end' }, ax); ttr.textContent = 'SLOWER CUTS →';
    const g = svgEl('g', {}, svg);
    rows.forEach((d, k) => {
      const yy = m.t + k * rh + rh / 2;
      if (k % 2 === 0) svgEl('rect', { x: 0, y: yy - rh / 2, width: W, height: rh, fill: 'rgba(255,255,255,.018)' }, g);
      const lab = svgEl('text', { x: m.l - 12, y: yy + 4, 'text-anchor': 'end', fill: d.ok ? '#5fd1b0' : '#a5a9b4', 'font-size': 12, 'font-family': 'Barlow' }, g); lab.textContent = d.n;
      const ln = svgEl('line', { x1: x(d.g), x2: x(d.g), y1: yy, y2: yy, stroke: d.ok ? '#5fd1b0' : 'rgba(255,180,84,.5)', 'stroke-width': 2 }, g);
      const req = svgEl('rect', { x: x(d.req) - 4, y: yy - 4, width: 8, height: 8, fill: '#ffb454', transform: `rotate(45 ${x(d.req)} ${yy})`, opacity: 0 }, g);
      const ach = svgEl('circle', { cx: x(d.g), cy: yy, r: 4.5, fill: d.ok ? '#5fd1b0' : '#fff' }, g);
      const tipH = `<b>${d.n}</b>Cut achieved: ${fmt(-d.g)}% a year<br>Cut needed for 1.61 t by 2050: ${fmt(-d.req)}% a year<br>${d.ok ? 'On track' : `Needs to cut ${(d.req / d.g).toFixed(1)}× faster`} · CO₂ in 2022: ${fmt(d.last)} t`;
      [ach, req, lab].forEach(n => { n.addEventListener('pointerenter', e => showTip(tipH, e.clientX, e.clientY)); n.addEventListener('pointerleave', hideTip); });
      ln.dataset.to = x(d.req);
    });
    Explain.takeaway(viz).set(`Of ${rows.length} countries that cut emissions while growing, only <b>${ok.length}</b> (${ok.map(d => d.n).join(' and ')}) are cutting fast enough to reach the fair share by 2050. The typical country cut ${fmt(-mg)}% a year but needs ${fmt(-mr)}% a year: about <b>${(mr / mg).toFixed(1)} times faster</b>.`);
    onReveal(viz, () => {
      g.querySelectorAll('line').forEach((ln, k) => {
        ln.style.transition = `all .9s cubic-bezier(.2,.7,.1,1) ${k * 0.025}s`;
        requestAnimationFrame(() => requestAnimationFrame(() => ln.setAttribute('x2', ln.dataset.to)));
      });
      g.querySelectorAll('rect[transform]').forEach((r, k) => { r.style.transition = `opacity .4s ${0.6 + k * 0.025}s`; requestAnimationFrame(() => requestAnimationFrame(() => r.setAttribute('opacity', 1))); });
      const yU = m.t + rows.findIndex(d => d.i === 'USA') * rh + rh / 2, u = rows.find(d => d.i === 'USA');
      if (u) Explain.annotate(svg, { x: x(u.req), y: yU, tx: x(-12.4), ty: yU - 22, anchor: 'start', text: ['UNITED STATES', `cut ${fmt(-u.g)}%/yr, needs ${fmt(-u.req)}%/yr`], color: '#ffb454', delay: 2200 });
    });
  })();

  // ------------------------------------------------------------- scenarios
  (function scen() {
    const host = document.getElementById('scen');
    if (!host) return;
    const viz = document.getElementById('scenviz');
    Explain.guide(viz, [
      'Each row is a <strong>what-if</strong>: every one of the 41 countries keeps cutting at a constant rate from 2022.',
      'The bar shows how many of them would reach the fair share of 1.61 t by 2050.',
      'The small text is the typical (median) cut per year that the scenario assumes.'
    ]);
    host.innerHTML = D.scen.map(s => `<div class="scen-row"><span class="scen-l">${s[0].replace('--', '–')}<small>median cut ${fmt(-s[1])}% a year</small></span><span class="scen-bar"><i style="--w:${(s[2] / s[3] * 100).toFixed(1)}%"></i></span><b>${s[2]}</b></div>`).join('');
    Explain.takeaway(viz).set(`At today’s pace only <b>${D.scen[0][2]} of 41</b> get there. Even if every country matched the fastest cut any of them achieved, only ${D.scen[3][2]} would. Reaching the boundary needs cuts of about ${fmt(-D.scen[4][1])}% a year, more than three times today’s typical pace.`);
  })();

  // ------------------------------------------------------------- robustness
  const rb = document.querySelector('#rob tbody');
  if (rb) rb.innerHTML = D.rob.map(r => `<tr><td>${r[0]}</td><td class="n">${r[1]}</td><td class="n">${r[2] === '' ? 'n/a' : fmt(r[2])}</td><td class="n">${r[3] === '' ? 'n/a' : fmt(r[3]) + '%'}</td></tr>`).join('');
})();
