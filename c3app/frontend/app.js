/* TeaSpray Planner - front end. Talks to the FastAPI backend only; all planning and energy numbers come from the server. */
(function () {
"use strict";
const $ = id => document.getElementById(id);
const ST = {
  sites: [], site: null, z: null, n: 0, dx: 5, size: 300, zs: 1,
  poly: [], closed: false, trees: [], depot: null, tool: 'field',
  plan: null, mid: null, strat: 'optimised', routes: {}, es: null, playing: true, frame: null, spraying: [],
  log: [], bw: 777.6, started: false, page: 'start', visited: {}, sum: null, ftab: 'overview'
};
const COL = { fixed: '#ff6b6b', standard: '#8fb6ff', optimised: '#7bd88f', agent: '#ffd166', flatfirst: '#c792ea' };
const IDS = () => (ST.plan ? ST.plan.strategies.map(s => s.id) : ['fixed', 'standard', 'optimised']);
const NAMES = { fixed: 'No tree avoidance (unsafe)', standard: 'Usual route', optimised: 'Search planner (comparison)', agent: 'System route (AI agent)', flatfirst: 'Mass-aware path optimisation' };
const KIND = { transit: 'Flying', spraying: 'Spraying', turning: 'Turning' };

async function api(path, opt) {
  const r = await fetch(path, opt);
  if (!r.ok) { let d = ''; try { d = (await r.json()).detail; } catch (e) {} throw new Error(d || r.statusText); }
  return r.json();
}
const post = (p, b) => api(p, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b) });

// ------------------------------------------------------------------ colour ramps
function hex(c) { return [parseInt(c.slice(1, 3), 16), parseInt(c.slice(3, 5), 16), parseInt(c.slice(5, 7), 16)]; }
function ramp(stops, t) { t = Math.max(0, Math.min(1, t)); const n = stops.length - 1, i = Math.min(n - 1, Math.floor(t * n)), f = t * n - i, a = hex(stops[i]), b = hex(stops[i + 1]); return [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f]; }
const SLOPE = ['#2f6b45', '#6d9a4a', '#c9b24a', '#b5623a', '#8e2f2f'];
const TANK = ['#f6d365', '#fda085', '#d2557c', '#5b3fa0', '#1f2d8a'];
const BATT = ['#d64550', '#f0a04b', '#e6d95a', '#7bd88f', '#2e9d6f'];

// ------------------------------------------------------------------ terrain helpers
function zAt(x, y) {
  const z = ST.z, n = ST.n, dx = ST.dx;
  let fx = x / dx - 0.5, fy = y / dx - 0.5;
  fx = Math.max(0, Math.min(n - 1.001, fx)); fy = Math.max(0, Math.min(n - 1.001, fy));
  const i = Math.floor(fx), j = Math.floor(fy), a = fx - i, b = fy - j;
  return z[i][j] * (1 - a) * (1 - b) + z[i + 1][j] * a * (1 - b) + z[i][j + 1] * (1 - a) * b + z[i + 1][j + 1] * a * b;
}
function groundImage(px) {      // slope colours with hill shading, drawn once per site
  const c = document.createElement('canvas'); c.width = c.height = px; const g = c.getContext('2d');
  const im = g.createImageData(px, px), n = ST.n, dx = ST.dx;
  for (let r = 0; r < px; r++) for (let q = 0; q < px; q++) {
    const x = (q + 0.5) / px * ST.size, y = (1 - (r + 0.5) / px) * ST.size;
    const e = 2.5, gx = (zAt(x + e, y) - zAt(x - e, y)) / (2 * e), gy = (zAt(x, y + e) - zAt(x, y - e)) / (2 * e);
    const deg = Math.atan(Math.hypot(gx, gy)) * 57.2958;
    const col = ramp(SLOPE, deg / 14);
    const shade = 0.78 + 0.5 * Math.max(-0.5, Math.min(0.5, (-gx * 0.6 + gy * 0.8) * 3.2));
    const k = (r * px + q) * 4;
    im.data[k] = col[0] * shade; im.data[k + 1] = col[1] * shade; im.data[k + 2] = col[2] * shade; im.data[k + 3] = 255;
  }
  g.putImageData(im, 0, 0); return c;
}

// ------------------------------------------------------------------ 2D map editor
const map = $('map'), mg = map.getContext('2d');
let groundMap = null;
const M2P = v => v / ST.size * map.width;                 // metres -> pixels (x)
const MY = v => (1 - v / ST.size) * map.height;           // metres -> pixels (y, flipped)
function drawMap() {
  mg.clearRect(0, 0, map.width, map.height);
  if (groundMap) mg.drawImage(groundMap, 0, 0, map.width, map.height);
  // grid every 50 m
  mg.strokeStyle = 'rgba(255,255,255,.12)'; mg.lineWidth = 1; mg.fillStyle = 'rgba(255,255,255,.55)'; mg.font = '13px system-ui';
  for (let v = 50; v < ST.size; v += 50) {
    mg.beginPath(); mg.moveTo(M2P(v), 0); mg.lineTo(M2P(v), map.height); mg.stroke();
    mg.beginPath(); mg.moveTo(0, MY(v)); mg.lineTo(map.width, MY(v)); mg.stroke();
    mg.fillText(v + ' m', M2P(v) + 3, map.height - 4); mg.fillText(v + ' m', 4, MY(v) - 3);
  }
  // planned routes (faint) on the map as well
  if (ST.plan && ST.routes[ST.strat]) {
    const r = ST.routes[ST.strat]; mg.strokeStyle = COL[ST.strat] + 'cc'; mg.lineWidth = 1.6; mg.beginPath();
    for (let i = 0; i < r.x.length; i++) { const px = M2P(r.x[i]), py = MY(r.y[i]); i ? mg.lineTo(px, py) : mg.moveTo(px, py); }
    mg.stroke();
  }
  if (ST.poly.length) {
    mg.beginPath(); ST.poly.forEach((p, i) => i ? mg.lineTo(M2P(p[0]), MY(p[1])) : mg.moveTo(M2P(p[0]), MY(p[1])));
    if (ST.closed) { mg.closePath(); mg.fillStyle = 'rgba(123,216,143,.16)'; mg.fill(); }
    mg.strokeStyle = '#ffffff'; mg.lineWidth = 2.2; mg.stroke();
    ST.poly.forEach((p, i) => { mg.fillStyle = i === 0 && !ST.closed ? '#ffd166' : '#fff'; mg.beginPath(); mg.arc(M2P(p[0]), MY(p[1]), 5, 0, 6.2832); mg.fill(); });
  }
  ST.trees.forEach(t => {
    mg.fillStyle = 'rgba(20,90,50,.9)'; mg.beginPath(); mg.arc(M2P(t.x), MY(t.y), Math.max(4, M2P(t.r)), 0, 6.2832); mg.fill();
    mg.strokeStyle = 'rgba(255,107,107,.9)'; mg.lineWidth = 1.5; mg.setLineDash([4, 3]); mg.beginPath(); mg.arc(M2P(t.x), MY(t.y), M2P(t.r + 3.5), 0, 6.2832); mg.stroke(); mg.setLineDash([]);
  });
  if (ST.depot) {
    const x = M2P(ST.depot[0]), y = MY(ST.depot[1]); mg.fillStyle = '#ffa94d'; mg.beginPath(); mg.moveTo(x, y - 11); mg.lineTo(x + 9, y + 8); mg.lineTo(x - 9, y + 8); mg.closePath(); mg.fill();
    mg.fillStyle = '#fff'; mg.fillText('refill', x + 12, y + 4);
  }
  const adv = ST.plan && ST.plan.depot_advice;
  if (adv) { const x = M2P(adv.x), y = MY(adv.y); mg.strokeStyle = '#4cc9f0'; mg.lineWidth = 2; mg.setLineDash([5, 3]); mg.beginPath(); mg.arc(x, y, 11, 0, 6.2832); mg.stroke(); mg.setLineDash([]); mg.fillStyle = '#4cc9f0'; mg.fillText('better refill point', x + 14, y + 4); }
}
function evMetres(e) {
  const r = map.getBoundingClientRect();
  return [(e.clientX - r.left) / r.width * ST.size, (1 - (e.clientY - r.top) / r.height) * ST.size, (e.clientX - r.left) / r.width * map.width, (e.clientY - r.top) / r.height * map.height];
}
map.addEventListener('click', e => {
  const [x, y, px, py] = evMetres(e);
  if (ST.tool === 'field') {
    if (ST.closed) { ST.poly = []; ST.closed = false; }
    if (ST.poly.length >= 3) { const f = ST.poly[0]; if (Math.hypot(M2P(f[0]) - px, MY(f[1]) - py) < 14) { ST.closed = true; info(); drawMap(); return; } }
    ST.poly.push([+x.toFixed(1), +y.toFixed(1)]);
  } else if (ST.tool === 'tree') {
    ST.trees.push({ x: +x.toFixed(1), y: +y.toFixed(1), r: +$('trad').value || 2 });
  } else if (ST.tool === 'depot') { ST.depot = [+x.toFixed(1), +y.toFixed(1)]; }
  invalidate(); info(); drawMap();
});
function invalidate() { /* the plan is out of date when the inputs change */ $('planmsg').textContent = ST.plan ? 'You changed something. Press "Plan my mission" again to update the answer.' : ''; if (ST.plan) { $('st4').classList.remove('done'); $('s4').textContent = 'out of date'; } }
function info() {
  const a = ST.poly.length >= 3 ? Math.abs(ST.poly.reduce((s, p, i) => { const q = ST.poly[(i + 1) % ST.poly.length]; return s + p[0] * q[1] - q[0] * p[1]; }, 0)) / 2 : 0;
  const ok = (c, t) => `<li class="${c ? 'ok' : ''}">${t}</li>`;
  $('checks').innerHTML =
    ok(ST.closed, ST.closed ? `Field drawn: <b>${(a / 1e4).toFixed(2)} ha</b>` : `Field: ${ST.poly.length} corner${ST.poly.length === 1 ? '' : 's'} so far (need at least 3, then finish the shape)`) +
    ok(ST.depot, ST.depot ? 'Refill point placed' : 'Refill point: not placed yet (needed)') +
    ok(ST.trees.length > 0, ST.trees.length ? `${ST.trees.length} tree${ST.trees.length > 1 ? 's' : ''} marked` : 'Trees: none marked (optional)');
  const done = ST.closed && !!ST.depot;
  $('st2').classList.toggle('done', done); $('s2').textContent = done ? 'done' : 'not done';
  $('st1').classList.toggle('done', !!ST.site); $('s1').textContent = ST.site ? 'ready' : 'not loaded';
  toolHelp(); nav();
}
const HELP = {
  field: "<b>Draw field:</b> click the map once for each corner of your field. When you have all corners, press <b>Finish the field shape</b> (or click the yellow first corner).",
  tree: "<b>Add tree:</b> click on each tree or pole in or near the field. The drone will fly around it. Set the tree size below if needed.",
  depot: "<b>Refill point:</b> click where the truck and water tank stand. The drone returns here to refill and swap batteries."
};
function toolHelp() {
  const t = HELP[ST.tool] || '';
  $('toolhelp').innerHTML = t;
  const done = ST.closed && !!ST.depot;
  $('toolbar').innerHTML = done ? '<b class="good">Ready.</b> Press <b>Plan my mission</b> on the left. You can still add trees or move the refill point.' : t;
}
function setTool(t) {
  ST.tool = t; ['Field', 'Tree', 'Depot'].forEach(k => $('t' + k).classList.toggle('on', t === k.toLowerCase())); toolHelp();
}
$('tField').onclick = () => { setTool('field'); };
$('tTree').onclick = () => setTool('tree');
$('tDepot').onclick = () => setTool('depot');
$('close').onclick = () => { if (ST.poly.length >= 3) { ST.closed = true; info(); drawMap(); } else { $('toolhelp').innerHTML = '<span class="warn">Click at least 3 corners on the map first.</span>'; } };
$('tUndo').onclick = () => { if (ST.tool === 'field' && ST.poly.length) { ST.poly.pop(); ST.closed = false; } else if (ST.tool === 'tree') ST.trees.pop(); else if (ST.tool === 'depot') ST.depot = null; info(); drawMap(); };

// ------------------------------------------------------------------ sites
function makeGround() {
  if (ST.img && ST.img.complete && ST.img.naturalWidth && $('sat').checked) {
    const c = document.createElement('canvas'); c.width = c.height = 1024; c.getContext('2d').drawImage(ST.img, 0, 0, 1024, 1024);
    $('attr').style.display = 'block'; return c;
  }
  $('attr').style.display = 'none'; return groundImage(450);
}
async function loadSite(id) {
  const zs = +$('zs').value;
  const d = await api(`/api/sites/${id}?z_scale=${zs}`);
  ST.site = id; ST.z = d.z; ST.n = d.z.length; ST.dx = d.dx; ST.size = d.size; ST.zs = zs; ST.img = null;
  if (d.imagery) {
    await new Promise(res => { const im = new Image(); im.onload = () => { ST.img = im; res(); }; im.onerror = res; im.src = `/api/sites/${id}/imagery.png?t=${Date.now()}`; });
  }
  groundMap = makeGround();
  drawMap();
}
function fillSites() {
  $('site').innerHTML = ST.sites.map(s => `<option value="${s.id}">${s.name} (${s.mean_slope < 6 ? 'gentle' : s.mean_slope < 12 ? 'sloping' : 'steep'}, average slope ${s.mean_slope}°)</option>`).join('');
}
function b64(buf) { let s = ''; const a = new Uint8Array(buf); for (let i = 0; i < a.length; i += 8192) s += String.fromCharCode.apply(null, a.subarray(i, i + 8192)); return btoa(s); }
async function loadEstate(body) {
  $('busy').textContent = 'Downloading the terrain and satellite picture for your area. This takes a moment the first time...'; $('busy').style.display = 'flex'; $('estmsg').textContent = '';
  try {
    const o = await post('/api/estate', body);
    ST.sites = await api('/api/sites'); fillSites(); $('site').value = o.site.id;
    ST.plan = null; ST.routes = {}; ST.mid = null; ST.started = false; ST.sum = null; closeStream();
    ST.poly = o.polygon || []; ST.closed = !!o.polygon; ST.trees = o.trees || []; ST.depot = o.depot || null;
    $('zs').value = 1; $('zsv').textContent = '1.0x';
    await loadSite(o.site.id);
    if (ST.closed && !ST.depot) {            // no refill point in the file: suggest one just outside the south-west corner
      const mx = Math.min(...ST.poly.map(p => p[0])), my = Math.min(...ST.poly.map(p => p[1]));
      ST.depot = [Math.max(5, mx - 12), Math.max(5, my - 12)];
    }
    info(); drawMap(); resetResults();
    $('estmsg').innerHTML = `<span class="good">Loaded ${o.site.name}: a ${o.site.size} m square area, ${o.site.elevation} m above sea level, hills rise ${o.site.relief} m.</span>` +
      (o.polygon ? ` Your field is ${o.area_ha.toFixed(2)} ha.` : ' Now go to step 2 and draw your field on the map.') + (o.warnings || []).map(w => `<br><span class="warn">${w}</span>`).join('');
    build3d(); go('estate');
  } catch (e) { $('estmsg').innerHTML = `<span class="bad">${e.message}</span>`; }
  $('busy').textContent = 'Planning the mission...'; $('busy').style.display = 'none';
}
$('kmlfile').onchange = async e => { const f = e.target.files[0]; if (f) await loadEstate({ kml_b64: b64(await f.arrayBuffer()) }); e.target.value = ''; };
$('loadEstate').onclick = async () => {
  const lat = parseFloat($('lat').value), lon = parseFloat($('lon').value);
  if (isNaN(lat) || isNaN(lon)) { $('estmsg').innerHTML = '<span class="bad">Type both a latitude and a longitude (for example 6.9336 and 80.6175).</span>'; return; }
  await loadEstate({ lat, lon, size: 300 });
};
$('sat').onchange = () => { groundMap = makeGround(); drawMap(); if (ST.n) { build3d(); } };
$('site').onchange = async () => { await loadSite($('site').value); invalidate(); if (!ST.plan) build3d(); };
$('zs').oninput = () => { $('zsv').textContent = (+$('zs').value).toFixed(2).replace(/0$/, '') + 'x'; };
$('zs').onchange = async () => { await loadSite($('site').value); invalidate(); };
$('ex').onclick = async () => {
  const d = await api(`/api/example/${ST.site}?z_scale=${ST.zs}`);
  ST.poly = d.polygon; ST.closed = true; ST.trees = d.trees; ST.depot = d.depot; info(); drawMap(); invalidate();
};

// ------------------------------------------------------------------ planning
function params() {
  const o = {};
  ['tank_l', 'spray_kmh', 'swath', 'reserve', 'clearance', 'l_per_ha'].forEach(k => o[k] = +$('p_' + k).value);
  return o;
}
async function planNow() {
  if (!ST.closed || ST.poly.length < 3) { $('planmsg').innerHTML = '<span class="bad">The field is not drawn yet. Open "Estate and field", draw the field and press "Finish the field shape" (or press "Use example field").</span>'; return; }
  if (!ST.depot) { $('planmsg').innerHTML = '<span class="bad">The refill point is missing. Open "Estate and field", click "Refill point" and then click the map where the truck stands.</span>'; return; }
  $('busy').textContent = 'Planning your mission: comparing the usual route with the system\'s route...'; $('busy').style.display = 'flex'; $('plan').disabled = true; $('planmsg').textContent = '';
  try {
    const out = await post('/api/plan', { site: ST.site, polygon: ST.poly, trees: ST.trees, depot: ST.depot, params: params(), z_scale: ST.zs, agent_model: $('brain') && $('brain').value ? $('brain').value : null });
    closeStream();
    ST.plan = out; ST.mid = out.mission_id; ST.bw = out.battery_wh || 777.6;
    ST.routes = {}; out.strategies.forEach(s => ST.routes[s.id] = s.route);
    ST.strat = out.recommended; ST.trees = out.trees; ST.log = []; ST.started = false;
    $('strat').innerHTML = IDS().map(k => `<option value="${k}">${NAMES[k]}</option>`).join(''); $('strat').value = ST.strat;
    drawMap(); build3d(); results(out); bindGo($('results')); bindGo($('why'));
    $('s4').textContent = 'done'; $('st4').classList.add('done');
    $('planmsg').innerHTML = `<span class="good">Done in ${out.seconds.toFixed(1)} s.</span> The advice is below. Press "Watch the system's route in 3D" to see the flight.`;
    nav(); go('plan');
    $('results').scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (e) { $('planmsg').innerHTML = `<span class="bad">${e.message}</span>`; }
  $('busy').style.display = 'none'; $('busy').textContent = 'Planning the mission...'; $('plan').disabled = false;
}
$('plan').onclick = planNow;

function hexA(h, a) { const n = parseInt(h.slice(1), 16); return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${a})`; }
const EMPTY_RESULTS = '<div class="empty"><b>Your advice will appear here</b><span>Press "Plan my mission" above. We compare the usual route with the system\'s route on your field.</span></div>';
const EMPTY_WHY = '<div class="empty"><b>Nothing to explain yet</b><span>Plan a mission first. This page then shows where the battery saving comes from.</span><button class="pill lime" data-go="plan" style="margin-top:8px">Go to Plan and advice →</button></div>';
function resetResults() { $('results').innerHTML = EMPTY_RESULTS; $('why').innerHTML = EMPTY_WHY; bindGo($('why')); }
function results(p) {
  const S = Object.fromEntries(p.strategies.map(s => [s.id, s.metrics]));
  const std = S.standard, fix = S.fixed, ag = p.agent, useAg = !!(S.agent && ag && ag.used), ff = S.flatfirst;
  const opt = useAg ? S.agent : (p.recommended === 'flatfirst' && ff ? ff : S.optimised);
  const sysName = useAg ? 'System (AI agent)' : (opt === ff ? 'System (mass-aware path)' : 'System (search planner)');
  const extra = ff && opt !== ff ? ff : null;
  const sav = (1 - opt.energy_pct / std.energy_pct) * 100;
  const wh = m => (m.energy_pct / 100 * ST.bw);
  const ra = p.route_advice;
  const cls = ra ? ra.choice : (sav >= 5 ? 'system' : (sav >= 1 ? 'either' : 'usual'));
  const head = ra ? ra.headline : (sav >= 1 ? "Fly the system's route" : 'Fly the usual route');
  const f2 = v => v.toFixed(2), f0 = v => v.toFixed(0);
  const row = (lab, a, b, lower, fmt, unit, c) => {
    const vals = [a, b].concat(c == null ? [] : [c]).map(v => +fmt(v)), best = lower ? Math.min(...vals) : Math.max(...vals);
    const cell = (v, i) => `<td class="${vals[i] === best && vals.some(x => x !== best) ? 'win' : ''}">${fmt(v)}${unit || ''}</td>`;
    return `<tr><td>${lab}</td>${cell(a, 0)}${cell(b, 1)}${c == null ? '' : cell(c, 2)}</tr>`;
  };
  ST.sum = { sav, sorties: opt.sorties, minutes: opt.minutes, contacts: opt.contact_steps, std_sorties: std.sorties };
  let thumb = ''; try { thumb = map.toDataURL('image/jpeg', 0.82); } catch (e) { }

  // ---------------- page 4: the advice ----------------
  let h = `<div class="verdict ${cls}">
    <div class="vgrid"><div><div class="lab">Our advice for this field</div><div class="head">${head}</div>
      <div class="savebox"><span class="big ${sav > 0 ? 'good' : ''}">${sav.toFixed(1)}%</span><span class="small">${sav >= 0 ? 'less' : 'more'} battery than the usual route, with the same ground covered<br>(${f0(wh(opt) / p.field_ha)} instead of ${f0(wh(std) / p.field_ha)} Wh per hectare, field ${p.field_ha.toFixed(2)} ha)</span></div></div>
      ${thumb ? `<figure class="thumb"><img alt="Recommended route over your field" src="${thumb}"><figcaption>${NAMES[ST.strat] || 'Route'} on your field</figcaption></figure>` : '<div></div>'}</div>
    <table class="cmp"><tr><th></th><th>Usual route</th><th>${sysName}</th>${extra ? '<th>Mass-aware path</th>' : ''}</tr>
      ${row('Battery used (full charges)', std.energy_pct / 100, opt.energy_pct / 100, true, f2, '', extra && extra.energy_pct / 100)}
      ${row('Take-offs', std.sorties, opt.sorties, true, f0, '', extra && extra.sorties)}
      ${row('Time (minutes)', std.minutes, opt.minutes, true, f0, '', extra && extra.minutes)}
      ${row('Tree contacts', std.contact_steps, opt.contact_steps, true, f0, '', extra && extra.contact_steps)}
      ${row('Field covered', 100 * std.coverage, 100 * opt.coverage, false, v => v.toFixed(1), ' %', extra && 100 * extra.coverage)}
    </table>${extra ? `<div class="small" style="margin-top:8px">Mass-aware path optimisation: the order of the field strips is searched with the energy model. It uses ${Math.abs(100 * (1 - extra.energy_pct / opt.energy_pct)).toFixed(1)}% ${extra.energy_pct <= opt.energy_pct ? 'less' : 'more'} battery than the system route${extra.sorties < opt.sorties ? `, with ${opt.sorties - extra.sorties} fewer take-offs` : ''}${extra.minutes < opt.minutes - 0.5 ? ` and about ${(opt.minutes - extra.minutes).toFixed(0)} min less flying` : ''}.</div>` : ''}`;
  if (ra) {
    h += `<div style="margin-top:14px"><b>Why</b></div><ul>${ra.reasons.map(t => `<li>${t}</li>`).join('')}</ul>`;
    if (ra.cautions.length) h += `<div><b>Things to think about</b></div><ul>${ra.cautions.map(t => `<li>${t}</li>`).join('')}</ul>`;
  }
  h += `<div class="actions">
      <button class="pill lime" id="pickSystem">Watch the system's route in 3D →</button>
      <button class="pill" id="pickUsual">Watch the usual route</button>
      ${extra ? '<button class="pill" id="pickFF">Watch the mass-aware path</button>' : ''}
      <button class="pill" id="goWhy">See why it saves energy</button>
      <button class="pill" id="copySum">Copy a short summary</button></div>
    <div class="small" id="copyMsg" style="margin-top:6px"></div></div>`;
  const a = p.depot_advice;
  if (a && a.saving_pct > 0.2) h += `<div class="card"><h3>Tip: move the refill point</h3><div class="small" style="font-size:14px">The blue circle on the map (page "Estate and field") is a better place for the truck. It would save a further <b class="good">${a.saving_pct.toFixed(1)}%</b> battery.</div><button class="pill" id="useDepot" style="margin-top:10px">Use that spot and plan again</button></div>`;
  $('results').innerHTML = h;

  // ---------------- page 6: why it saves energy ----------------
  let w = `<div class="nums">
    <div><div class="num ${sav > 0 ? 'good' : ''}">${sav.toFixed(1)}%</div><div class="lbl">${sav >= 0 ? 'less' : 'more'} battery</div><div class="sub">than the usual route, same ground covered</div></div>
    <div><div class="num">${opt.sorties}</div><div class="lbl">take-offs</div><div class="sub">the usual route needs ${std.sorties}</div></div>
    <div><div class="num">${f0(opt.minutes)}</div><div class="lbl">minutes in the air</div><div class="sub">the usual route needs ${f0(std.minutes)}</div></div></div>
    <div class="ways">
      <div class="card"><div class="ic"><svg viewBox="0 0 24 24" fill="none" stroke="#111" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3s6 6.5 6 11a6 6 0 01-12 0c0-4.5 6-11 6-11z"/></svg></div><h3>Carry less liquid</h3><div class="small" style="font-size:14px">A lighter drone burns less power just to stay in the air. The planner chooses how much liquid to take on each trip.</div></div>
      <div class="card"><div class="ic"><svg viewBox="0 0 24 24" fill="none" stroke="#111" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M3 17l6-6 4 4 8-8M15 7h6v6"/></svg></div><h3>Climb while light</h3><div class="small" style="font-size:14px">Climbing with a full tank costs more than climbing with a nearly empty one. Order the strips so the steep parts come later.</div></div>
      <div class="card"><div class="ic"><svg viewBox="0 0 24 24" fill="none" stroke="#111" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12h16M14 6l6 6-6 6"/></svg></div><h3>Turn rows the right way</h3><div class="small" style="font-size:14px">The row direction changes how far the drone flies and how much it climbs. The planner tests the directions and keeps a good one.</div></div>
    </div>`;
  let d = '';
  if (ag) d += ag.error ? `<div class="card"><h3 class="bad">The AI agent could not run</h3><div class="small">${ag.error}</div></div>` :
    `<div class="card"><h3>What the AI agent decided <span class="tag">${ag.model}</span></h3><div class="small" style="font-size:14px">It turned the rows to <b>${ag.decisions.theta.toFixed(0)}°</b>, started the sweep ${ag.decisions.flip_rows ? 'from the other side' : 'from the usual side'}, and carried <b>${ag.decisions.loads_l.join(' L, ')} L</b> on the trips. A lighter drone burns less battery. Agent vs usual route: <b class="${ag.vs_standard_pct > 0 ? 'good' : 'bad'}">${ag.vs_standard_pct.toFixed(1)}%</b> battery.${ag.note ? `<br><span class="bad">${ag.note}</span>` : ''}</div></div>`;
  const SL = p.slope_load, su = SL && SL.standard, sm = SL && SL[p.recommended];
  if (su && sm && p.recommended !== 'standard') {
    const f = v => (v == null ? '-' : v.toFixed(0)), idx = v => 100 * v.mass_climb / Math.max(su.mass_climb, 1e-9);
    const dh = su.climb_heavy_m - sm.climb_heavy_m, dl = sm.climb_light_m - su.climb_light_m;
    const msg = dh > 1
      ? `The system's route climbs <b class="good">${dh.toFixed(0)} m less</b> while the tank is heavy${dl > 1 ? ` and ${dl.toFixed(0)} m more while it is light` : ''}. Climbing weighted by the drone's weight is <b class="${idx(sm) < 100 ? 'good' : 'warn'}">${Math.abs(100 - idx(sm)).toFixed(1)}% ${idx(sm) < 100 ? 'lower' : 'higher'}</b>.`
      : `On this field the system's route does not move the climbing to the light-tank part (heavy-tank climb: ${f(su.climb_heavy_m)} m usual, ${f(sm.climb_heavy_m)} m system). Its saving comes from lighter loads instead.`;
    const routes = [['standard', 'Usual', su], [p.recommended, 'System', sm]];
    const sf = SL.flatfirst; if (sf && p.recommended !== 'flatfirst') routes.push(['flatfirst', 'Mass-aware path', sf]);
    const mx = Math.max(...routes.map(r => Math.max(r[2].climb_heavy_m, r[2].climb_light_m)), 1);
    const bars = routes.map(r => `<div style="display:grid;grid-template-columns:120px 1fr;gap:8px;align-items:center;margin:6px 0"><span class="small">${r[1]}</span><div>
        <div style="display:flex;align-items:center;gap:6px"><i style="display:block;height:10px;border-radius:5px;background:#5b3fa0;width:${(65 * r[2].climb_heavy_m / mx).toFixed(1)}%;min-width:2px"></i><span class="small" style="white-space:nowrap">${f(r[2].climb_heavy_m)} m heavy</span></div>
        <div style="display:flex;align-items:center;gap:6px;margin-top:2px"><i style="display:block;height:10px;border-radius:5px;background:#f0b429;width:${(65 * r[2].climb_light_m / mx).toFixed(1)}%;min-width:2px"></i><span class="small" style="white-space:nowrap">${f(r[2].climb_light_m)} m light</span></div></div></div>`).join('');
    d += `<div class="card"><h3>Does the drone climb with a heavy or a light tank?</h3>
      <div>${bars}</div>
      <table style="margin-top:8px"><tr><th>Route</th><th>Climb, heavy tank (m)</th><th>Climb, light tank (m)</th><th>Weight x climb</th></tr>
      ${routes.map(r => `<tr><td>${r[1]}</td><td>${f(r[2].climb_heavy_m)}</td><td>${f(r[2].climb_light_m)}</td><td>${r[0] === 'standard' ? '100' : idx(r[2]).toFixed(0)}</td></tr>`).join('')}</table>
      <div style="margin-top:8px;font-size:14px">${msg}</div>
      <div class="small" style="margin-top:6px">Heavy = tank more than 2/3 full, light = less than 1/3. "Weight x climb" counts every metre climbed times the drone's weight at that moment; lower means less battery spent on climbing. Climbing is only a small part of the battery use, so this effect is small; most of the saving comes from lighter loads. To see it: in the Flight viewer choose "Colour by how heavy the tank is" and untick the satellite picture on the Drone page.</div></div>`;
  }
  d += `<div class="card"><h3>Where the saving comes from</h3><table><tr><th>One change at a time</th><th>Battery saved</th></tr>`;
  p.levers.forEach((l, i) => { if (i) d += `<tr><td>${l.label}</td><td class="${l.vs_standard_pct > 0 ? 'good' : ''}">${l.vs_standard_pct >= 0 ? '+' : ''}${l.vs_standard_pct.toFixed(1)}%</td></tr>`; });
  d += `</table></div>`;
  d += `<div class="card"><h3>All routes side by side</h3><table><tr><th>Route</th><th>Battery</th><th>Take-offs</th><th>Min</th><th>Covered</th><th>Tree hits</th></tr>`;
  p.strategies.forEach(s => {
    const m = s.metrics;
    d += `<tr><td><span class="sw" style="background:${COL[s.id]}"></span>${NAMES[s.id] || s.name}</td><td>${(m.energy_pct / 100).toFixed(2)}</td><td>${m.sorties}</td><td>${m.minutes.toFixed(0)}</td><td>${(100 * m.coverage).toFixed(1)}%</td><td class="${m.contact_steps ? 'bad' : 'good'}">${m.contact_steps}</td></tr>`;
  });
  d += `</table><div class="small" style="margin-top:6px">Battery is in full charges (1.00 = one whole battery). Tree hits = moments closer than 1 m to a tree.${fix && fix.contact_steps ? ` The "no avoidance" route flies through trees ${fix.contact_steps} times; the planned routes stay at least ${Math.min(std.min_gap_m, opt.min_gap_m).toFixed(1)} m away.` : ''}</div></div>`;
  d += `<div class="card"><h3>What if you spray faster or slower?</h3>${speedChart(p)}<div class="small">Battery for the whole field against spray speed. Check the drone's manual and spray drift before going above its rated speed.</div></div>`;
  $('why').innerHTML = w + d;

  // ---------------- buttons ----------------
  const pick = id => { $('strat').value = id; ST.started = true; $('strat').onchange(); go('viewer'); };
  const pu = $('pickUsual'), ps = $('pickSystem');
  if (pu) pu.onclick = () => pick(ra ? ra.usual_id : 'standard');
  if (ps) ps.onclick = () => pick(ra ? ra.recommended_id : p.recommended);
  const pf = $('pickFF'); if (pf) pf.onclick = () => pick('flatfirst');
  const gw = $('goWhy'); if (gw) gw.onclick = () => go('why');
  const b = $('useDepot'); if (b) b.onclick = () => { ST.depot = [+a.x.toFixed(1), +a.y.toFixed(1)]; drawMap(); planNow(); };
  const cs = $('copySum');
  if (cs) cs.onclick = async () => {
    const txt = `TeaSpray Planner summary\nField: ${p.field_ha.toFixed(2)} ha, tank ${p.params.tank_l} L\nAdvice: ${head}\nBattery: ${(opt.energy_pct / 100).toFixed(2)} charges (system) vs ${(std.energy_pct / 100).toFixed(2)} (usual), ${Math.abs(sav).toFixed(1)}% ${sav >= 0 ? 'less' : 'more'}\nTake-offs: ${opt.sorties} vs ${std.sorties}\nTime: ${opt.minutes.toFixed(0)} vs ${std.minutes.toFixed(0)} min\nTree contacts: ${opt.contact_steps} vs ${std.contact_steps}${extra ? `\nMass-aware path optimisation: ${(extra.energy_pct / 100).toFixed(2)} charges` : ''}\nNote: figures come from an energy model checked against real flight logs; the route has not been flown yet.`;
    try { await navigator.clipboard.writeText(txt); $('copyMsg').textContent = 'Copied.'; } catch (e) { $('copyMsg').textContent = txt; }
  };
}
function speedChart(p) {
  if (!p.speed_curve || p.speed_curve.length < 2) return '<div class="small">Not enough speeds could be flown on this field to draw the chart.</div>';
  const d = p.speed_curve, W = 330, H = 120, L = 34, B = 20, mx = Math.max(...d.map(r => r.energy_pct)) / 100;
  const X = i => L + i * (W - L - 8) / (d.length - 1), Y = v => 8 + (H - B - 8) * (1 - v / mx);
  let s = `<svg width="100%" viewBox="0 0 ${W} ${H}"><g stroke="#e1e3dd">`;
  [0, 0.5, 1].forEach(f => s += `<line x1="${L}" x2="${W - 8}" y1="${Y(mx * f)}" y2="${Y(mx * f)}"/>`);
  s += `</g>`;
  [0, 0.5, 1].forEach(f => s += `<text x="2" y="${Y(mx * f) + 3}">${(mx * f).toFixed(1)}</text>`);
  s += `<polyline fill="none" stroke="#2f9e44" stroke-width="2" points="${d.map((r, i) => X(i) + ',' + Y(r.energy_pct / 100)).join(' ')}"/>`;
  d.forEach((r, i) => s += `<circle cx="${X(i)}" cy="${Y(r.energy_pct / 100)}" r="3" fill="#2f9e44"/><text x="${X(i) - 8}" y="${H - 6}">${r.kmh}</text>`);
  s += `<text x="${L}" y="${H - 6}" style="display:none"></text></svg><div class="small" style="margin-top:-4px">km/h along the bottom, battery charges up the side</div>`;
  return s;
}

// ------------------------------------------------------------------ pages (sidebar)
const PAGES = ['start', 'estate', 'drone', 'plan', 'viewer', 'why', 'evidence'];
function polyHa() {
  if (ST.poly.length < 3) return 0;
  return Math.abs(ST.poly.reduce((s, p, i) => { const q = ST.poly[(i + 1) % ST.poly.length]; return s + p[0] * q[1] - q[0] * p[1]; }, 0)) / 2 / 1e4;
}
function bindGo(root) { (root || document).querySelectorAll('[data-go]').forEach(b => { if (!b.classList.contains('nv')) b.onclick = () => go(b.dataset.go); }); }
function listHtml(items) { return items.map(([ok, t]) => `<li class="${ok ? 'ok' : ''}">${t}</li>`).join(''); }
function nav() {
  fieldCard();
  const ready = ST.closed && !!ST.depot, planned = !!ST.plan;
  const mark = (p, d) => { const b = document.querySelector(`.nv[data-go="${p}"]`); if (b) b.classList.toggle('done', !!d); };
  mark('start', ST.visited.estate); mark('estate', ready); mark('drone', ST.visited.drone && ready); mark('plan', planned);
  mark('viewer', planned && ST.visited.viewer); mark('why', planned && ST.visited.why); mark('evidence', ST.visited.evidence);
  ['viewer', 'why'].forEach(p => document.querySelector(`.nv[data-go="${p}"]`).classList.toggle('lock', !planned));
  const st = $('startStatus');
  if (st) st.innerHTML = listHtml([
    [!!ST.site, ST.site ? 'Estate loaded: <b>' + ((ST.sites.find(s => s.id === ST.site) || {}).name || ST.site) + '</b>' : 'Estate: not loaded yet'],
    [ST.closed, ST.closed ? `Field drawn: <b>${polyHa().toFixed(2)} ha</b>` : 'Field: not drawn yet'],
    [!!ST.depot, ST.depot ? 'Refill point placed' : 'Refill point: not placed yet'],
    [planned, planned ? 'Mission planned: see "Plan and advice"' : 'Mission: not planned yet']]);
}
function planCheck() {
  const ready = ST.closed && !!ST.depot, nm = (ST.sites.find(s => s.id === ST.site) || {}).name;
  const brain = $('brain') && $('brain').value ? $('brain').value : null;
  $('planCheck').innerHTML = listHtml([
    [!!ST.site, ST.site ? `Estate: <b>${nm || ST.site}</b>` : 'Estate: not loaded'],
    [ST.closed, ST.closed ? `Field: <b>${polyHa().toFixed(2)} ha</b>, ${ST.trees.length} tree${ST.trees.length === 1 ? '' : 's'} marked` : 'Field: not drawn yet'],
    [!!ST.depot, ST.depot ? 'Refill point placed' : 'Refill point: not placed yet'],
    [true, `Drone: <b>${$('p_tank_l').value} L</b> tank, <b>${$('p_l_per_ha').value} L</b> per hectare`],
    [true, brain ? `Planning brain: <b>AI agent ${brain}</b>` : 'Planning brain: plain search planner (no agent)']]);
  $('planFix').style.display = ready ? 'none' : 'inline-flex';
}
function go(p) {
  if (ST.page === 'viewer' && p !== 'viewer') pauseViewer();
  ST.page = p; ST.visited[p] = true;
  PAGES.forEach(k => $('pg-' + k).classList.toggle('on', k === p));
  document.querySelectorAll('.nv').forEach(b => b.classList.toggle('on', b.dataset.go === p));
  $('content').scrollTop = 0;
  if (p === 'estate') drawMap();
  if (p === 'plan') planCheck();
  if (p === 'viewer') enterViewer();
  if (p === 'evidence') loadEvidence();
  nav();
}
function enterViewer() {
  const has = !!ST.plan;
  $('viewerEmpty').style.display = has ? 'none' : 'flex';
  $('hud').style.display = has ? 'block' : 'none'; $('legend').style.display = has ? 'block' : 'none';
  $('log').style.display = has && ST.log.length ? 'block' : 'none';
  resize(); dirty = true;
  if (has && !ST.started) { ST.started = true; startStream(0); }
}
function pauseViewer() { if (ST.es) { closeStream(); ST.playing = false; $('play').textContent = 'Play'; } }
document.querySelectorAll('.nv').forEach(b => b.onclick = () => {
  const p = b.dataset.go;
  if ((p === 'viewer' || p === 'why') && !ST.plan) { go('plan'); $('planmsg').innerHTML = '<span class="warn">Make a plan first. The ' + (p === 'viewer' ? 'flight viewer' : 'explanation') + ' opens after that.</span>'; return; }
  go(p);
});
bindGo();


// ------------------------------------------------------------------ field card on the start page
const FI = {
  area: '<path d="M4 6l8-3 8 3-2 12-6 3-6-3z"/>', tree: '<path d="M12 21v-6M12 3l5 7h-3l4 6H6l4-6H7z"/>', slope: '<path d="M3 19h18L9 6z"/>',
  relief: '<path d="M3 19l6-10 4 6 3-4 5 8z"/>', elev: '<path d="M12 3v14M7 12l5 5 5-5M5 21h14"/>', tank: '<path d="M12 3s6 6.5 6 11a6 6 0 01-12 0c0-4.5 6-11 6-11z"/>',
  spray: '<path d="M6 20V9l6-5 6 5v11zM9 20v-5h6v5"/>', speed: '<path d="M4 17a8 8 0 1116 0M12 17l4-6"/>', batt: '<rect x="3" y="8" width="16" height="9" rx="2"/><path d="M21 11v3"/>',
  save: '<path d="M3 17l6-6 4 4 8-8M15 7h6v6"/>', plane: '<path d="M12 3v7M4 13l8-3 8 3M9 21l3-4 3 4"/>', clock: '<circle cx="12" cy="12" r="8"/><path d="M12 7v5l3 2"/>', shield: '<path d="M12 3l8 3v6c0 4.5-3.2 7.8-8 9-4.8-1.2-8-4.5-8-9V6z"/>', pin: '<path d="M12 21s-6-5.2-6-10a6 6 0 1112 0c0 4.8-6 10-6 10z"/><circle cx="12" cy="11" r="2"/>'
};
function inPoly(x, y, poly) { let c = false; for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) { const a = poly[i], b = poly[j]; if ((a[1] > y) !== (b[1] > y) && x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]) c = !c; } return c; }
function fieldTerrain() {
  if (!ST.z || !ST.closed || ST.poly.length < 3) return null;
  const xs = ST.poly.map(p => p[0]), ys = ST.poly.map(p => p[1]);
  let n = 0, sum = 0, mx = 0, zmn = 1e9, zmx = -1e9, zs = 0;
  for (let x = Math.min(...xs); x <= Math.max(...xs); x += 4) for (let y = Math.min(...ys); y <= Math.max(...ys); y += 4) {
    if (!inPoly(x, y, ST.poly)) continue;
    const e = 2.5, gx = (zAt(x + e, y) - zAt(x - e, y)) / (2 * e), gy = (zAt(x, y + e) - zAt(x, y - e)) / (2 * e);
    const dg = Math.atan(Math.hypot(gx, gy)) * 57.2958, z = zAt(x, y);
    n++; sum += dg; mx = Math.max(mx, dg); zmn = Math.min(zmn, z); zmx = Math.max(zmx, z); zs += z;
  }
  return n ? { mean: sum / n, max: mx, relief: zmx - zmn, elev: zs / n } : null;
}
function fieldCard() {
  const box = $('ftiles'); if (!box) return;
  const tile = (ic, lab, val) => `<div class="ftile"><i><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">${FI[ic]}</svg></i><small>${lab}</small><b>${val}</b></div>`;
  const ha = polyHa(), ft = fieldTerrain(), t = ST.ftab, dash = '–';
  let tiles;
  if (t === 'terrain') tiles = [tile('slope', 'Mean slope', ft ? ft.mean.toFixed(1) + '°' : dash), tile('slope', 'Steepest', ft ? ft.max.toFixed(0) + '°' : dash), tile('relief', 'Height range', ft ? ft.relief.toFixed(0) + ' m' : dash), tile('elev', 'Elevation', ft ? ft.elev.toFixed(0) + ' m' : dash)];
  else if (t === 'drone') tiles = [tile('tank', 'Tank', ($('p_tank_l').value || dash) + ' L'), tile('spray', 'Spray', ($('p_l_per_ha').value || dash) + ' L/ha'), tile('speed', 'Speed', ($('p_spray_kmh').value || dash) + ' km/h'), tile('batt', 'Reserve', ($('p_reserve').value || dash) + ' %')];
  else if (t === 'plan') { const m = ST.sum; tiles = [tile('save', 'Battery saved', m ? (m.sav >= 0 ? '' : '−') + Math.abs(m.sav).toFixed(1) + '%' : dash), tile('plane', 'Take-offs', m ? m.sorties : dash), tile('clock', 'Minutes', m ? m.minutes.toFixed(0) : dash), tile('shield', 'Tree hits', m ? m.contacts : dash)]; }
  else tiles = [tile('area', 'Area', ST.closed ? ha.toFixed(2) + ' ha' : dash), tile('tree', 'Trees', ST.closed || ST.trees.length ? ST.trees.length : dash), tile('slope', 'Slope', ft ? ft.mean.toFixed(1) + '°' : dash), tile('pin', 'Refill', ST.depot ? 'Placed' : dash)];
  box.innerHTML = tiles.join('');
  document.querySelectorAll('#ftabs button').forEach(b => b.classList.toggle('on', b.dataset.ft === t));
  // the field drawn on the little map
  const g = $('fartField'); if (!g) return;
  const W = 340, H = 230, pad = 56;
  const site = ST.sites.find(s => s.id === ST.site);
  let body = '', label = 'Your field', sub = 'Draw a field to see it';
  if (ST.closed && ST.poly.length >= 3) {
    const pts = ST.poly.concat(ST.depot ? [ST.depot] : []);
    const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]), x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
    const k = Math.min((W - 2 * pad) / Math.max(x1 - x0, 1), (H - 2 * pad) / Math.max(y1 - y0, 1));
    const ox = (W - k * (x1 - x0)) / 2, oy = (H - k * (y1 - y0)) / 2;
    const X = v => (ox + (v - x0) * k).toFixed(1), Y = v => (H - oy - (v - y0) * k).toFixed(1);
    body = `<path d="M${ST.poly.map(p => X(p[0]) + ' ' + Y(p[1])).join('L')}Z" fill="#bfe5b2" stroke="#0f2418" stroke-width="2" stroke-linejoin="round"/>` +
      ST.trees.map(tr => `<circle cx="${X(tr.x)}" cy="${Y(tr.y)}" r="2.6" fill="#1f6f3a"/>`).join('') +
      (ST.depot ? `<path d="M${X(ST.depot[0])} ${(+Y(ST.depot[1]) - 7)}l6 11h-12z" fill="#ffa94d" stroke="#0f2418" stroke-width="1"/>` : '');
    label = (site && site.name) || 'Your field'; sub = `${ha.toFixed(2)} ha · ${ST.trees.length} tree${ST.trees.length === 1 ? '' : 's'}`;
  } else {
    body = '<path d="M95 70 C120 40 190 40 225 62 C260 85 250 130 215 160 C185 185 130 185 105 160 C80 135 75 95 95 70Z" fill="#bfe5b2" stroke="#0f2418" stroke-width="2" stroke-dasharray="5 4" stroke-linejoin="round" opacity=".75"/>';
  }
  g.innerHTML = body + `<g text-anchor="middle"><circle cx="170" cy="${ST.closed ? 24 : 98}" r="0" fill="none"/><text x="170" y="${ST.closed ? 24 : 112}" style="font-size:17px;font-weight:600;fill:#0f2418">${label}</text><text x="170" y="${ST.closed ? 40 : 130}" style="font-size:11px;fill:#4b5a4f">${sub}</text></g>`;
}
document.querySelectorAll('#ftabs button').forEach(b => b.onclick = () => { ST.ftab = b.dataset.ft; fieldCard(); });
['p_tank_l', 'p_l_per_ha', 'p_spray_kmh', 'p_reserve'].forEach(id => $(id).addEventListener('input', fieldCard));

// ------------------------------------------------------------------ evidence page
let evLoaded = false;
async function loadEvidence() {
  if (evLoaded) return;
  try { $('evidence').innerHTML = renderEvidence(await api('/api/evidence')); evLoaded = true; }
  catch (e) { $('evidence').innerHTML = `<div class="empty"><b>Could not load the evidence</b><span>${e.message}</span></div>`; }
}
function renderEvidence(d) {
  const F = d.facts || {}, en = d.energy && (d.energy['test (later dates)'] || d.energy.test), ag = d.agents || [];
  let h = `<div class="nums">
    <div><div class="num">${F.flights_kept || '-'}</div><div class="lbl">Real flights kept</div><div class="sub">from ${F.flights_raw || '-'} raw DJI Agras log entries, after removing duplicates and non-spraying flights.</div></div>
    <div><div class="num">${F.test_n || '-'}</div><div class="lbl">Later flights used as a test</div><div class="sub">full-tank flights from later dates, never used to fit the model.</div></div>
    <div><div class="num">${F.srtm_m ? Math.round(F.srtm_m) + ' m' : '-'}</div><div class="lbl">Source terrain data</div><div class="sub">SRTM elevation, resampled to a ${F.grid_m || 5} m grid. Smooth, so real slopes may be steeper.</div></div></div>`;
  if (en) {
    const rows = [['Physics model (hover + climb + drag, with tank weight)', en['model as saved (scale .915)'], true],
      ['Same model with scale refit on the earlier flights', en['refit scale on calibration'], true],
      ['Model that ignores tank weight', en['no-mass (constant half tank)'], false],
      ['Plain "average rate x time" baseline', en['constant rate x time'], false]].filter(r => r[1]);
    const mx = Math.max(...rows.map(r => r[1].mape), 1);
    h += `<div class="card white bars"><h3>How close is the energy model to real flights?</h3>
      <div class="small">Average error in the battery used per flight, on ${F.test_n || 'the'} later flights the model had not seen. Lower is better.</div>
      <div style="margin-top:10px">${rows.map(r => `<div class="br ${r[2] ? 'hi' : ''}"><span>${r[0]}</span><div class="tr"><i style="width:${(100 * r[1].mape / mx).toFixed(0)}%"></i></div><span class="v">${r[1].mape.toFixed(1)}%</span></div>`).join('')}</div>
      <div class="small" style="margin-top:8px">Be careful how you read this: on average the model is about as accurate as the plain baseline. Its purpose is different. The baseline cannot react to load or slope, so it cannot compare routes. The model can, and it is clearly better than the version that ignores tank weight.</div>
      <table style="margin-top:12px"><tr><th>Model</th><th>Mean error (battery %)</th><th>Relative error</th><th>R²</th></tr>
      ${rows.map(r => `<tr><td>${r[0]}</td><td>${r[1].mae.toFixed(2)}</td><td>${r[1].mape.toFixed(1)}%</td><td>${r[1].r2.toFixed(2)}</td></tr>`).join('')}</table></div>`;
  }
  h += `<div class="card white"><h3>How the AI agent was tested</h3>
    <div class="small">The agent is trained on random fields cut from the western 60% of one elevation tile, and tested on fields from the eastern 40%, so the test is new ground. "Saving" is the battery saved against the usual route, per field, counting a field as a failure if the route touches a tree.</div>`;
  if (ag.length) {
    h += `<table style="margin-top:10px"><tr><th>Agent</th><th>Training steps</th><th>Test fields</th><th>Mean saving</th><th>Median</th><th>Fields won</th><th>Fields lost</th></tr>
      ${ag.map(a => { const t = a.test || {}; return `<tr><td>${a.name}${a.hide_mass ? ' <span class="tag">blind to tank size</span>' : ''}</td><td>${a.steps != null ? a.steps.toLocaleString() : '-'}</td><td>${t.n != null ? t.n : '-'}</td><td>${t.mean != null ? t.mean.toFixed(1) + '%' : '-'}</td><td>${t.median != null ? t.median.toFixed(1) + '%' : '-'}</td><td>${t.wins != null ? t.wins : '-'}</td><td>${t.losses != null ? t.losses : '-'}</td></tr>`; }).join('')}</table>
      <div class="small" style="margin-top:8px">These results were measured with the original energy model. A re-test with the refit model is still to be done.</div>`;
  } else h += `<div class="small" style="margin-top:10px">No trained agents were found in the agents folder on this computer.</div>`;
  h += `</div>`;
  h += `<div class="card white"><h3>Limits of this prototype</h3><ul class="limits">
    <li><b>Simulation only.</b> No route has been flown with a real drone.</li>
    <li><b>Energy model:</b> calibrated on DJI Agras logs. How strongly tank weight changes power is not pinned down by the data yet, so the saving figure has an uncertainty range.</li>
    <li><b>Terrain:</b> free SRTM elevation is smooth, so real tea slopes are probably steeper. Use the "steeper hills" test on the Drone page.</li>
    <li><b>The AI agent</b> does not see the battery or the exact tree positions. It decides row direction, sweep, and load per refill; the rows themselves are flown by a rule-based follower.</li>
    <li><b>Trees</b> are marked by you. Automatic tree detection from the satellite picture is not built yet.</li>
    ${(d.assumptions || []).filter(x => !/^(Energy|Terrain):/.test(x)).map(x => `<li>${x}</li>`).join('')}</ul></div>`;
  return h;
}

// ------------------------------------------------------------------ 3D scene
const canvas = $('c3d');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2)); renderer.setClearColor(0x0a130e);
const scene = new THREE.Scene(), camera = new THREE.PerspectiveCamera(45, 1, 1, 3000);
scene.add(new THREE.AmbientLight(0xffffff, 0.8)); const sun = new THREE.DirectionalLight(0xffffff, 0.6); sun.position.set(-150, 300, 100); scene.add(sun);
const cam = { az: -0.55, el: 0.8, r: 420, tx: 150, ty: 10, tz: -150 };
function placeCam() { const ce = Math.cos(cam.el), se = Math.sin(cam.el); camera.position.set(cam.tx + cam.r * ce * Math.sin(cam.az), cam.ty + cam.r * se, cam.tz + cam.r * ce * Math.cos(cam.az)); camera.lookAt(cam.tx, cam.ty, cam.tz); }
let drag = null, dirty = true;
canvas.addEventListener('pointerdown', e => { drag = { x: e.clientX, y: e.clientY, pan: e.shiftKey || e.button === 2 }; canvas.setPointerCapture(e.pointerId); });
canvas.addEventListener('pointerup', () => drag = null);
canvas.addEventListener('contextmenu', e => e.preventDefault());
canvas.addEventListener('pointermove', e => {
  if (!drag) return; const dx = e.clientX - drag.x, dy = e.clientY - drag.y; drag.x = e.clientX; drag.y = e.clientY;
  if (drag.pan) { const k = cam.r * 0.0016; cam.tx -= Math.cos(cam.az) * dx * k; cam.tz += Math.sin(cam.az) * dx * k; cam.tx -= Math.sin(cam.az) * dy * k; cam.tz -= Math.cos(cam.az) * dy * k; }
  else { cam.az -= dx * 0.006; cam.el = Math.max(0.12, Math.min(1.5, cam.el + dy * 0.006)); }
  placeCam(); dirty = true;
});
canvas.addEventListener('wheel', e => { e.preventDefault(); cam.r = Math.max(60, Math.min(1200, cam.r * (1 + e.deltaY * 0.001))); placeCam(); dirty = true; }, { passive: false });
$('vtop').onclick = () => { cam.el = 1.5; cam.az = 0; cam.r = 280; placeCam(); dirty = true; };
$('vper').onclick = () => { cam.el = 0.8; cam.az = -0.55; cam.r = cam.rBase || 260; placeCam(); dirty = true; };
function resize() { const v = $('stage'); renderer.setSize(v.clientWidth, v.clientHeight, false); camera.aspect = v.clientWidth / v.clientHeight; camera.updateProjectionMatrix(); dirty = true; }
addEventListener('resize', resize);

let group = new THREE.Group(); scene.add(group);
let zmin = 0, EX = 2.0, tex = null, texCv = null, texG = null, baseCv = null, spCv = null, spG = null, drone = null, stem = null, routeObj = {}, treeObjs = [];
const W3 = (x, y, e) => new THREE.Vector3(x, (e - zmin) * EX, -y);
const TEXPX = 1200;

function build3d() {
  while (group.children.length) { const c = group.children.pop(); if (c.geometry) c.geometry.dispose(); }
  routeObj = {}; treeObjs = [];
  const n = ST.n, dx = ST.dx; zmin = Infinity; let zmax = -Infinity; ST.z.forEach(r => r.forEach(v => { zmin = Math.min(zmin, v); zmax = Math.max(zmax, v); }));
  EX = Math.max(1, Math.min(2, 110 / Math.max(zmax - zmin, 1)));
  const g = new THREE.PlaneGeometry(1, 1, n - 1, n - 1), pos = g.attributes.position, uv = g.attributes.uv;
  for (let r = 0; r < n; r++) for (let c = 0; c < n; c++) {
    const idx = r * n + c, i = c, j = n - 1 - r, x = (i + 0.5) * dx, y = (j + 0.5) * dx;
    pos.setXYZ(idx, x, (ST.z[i][j] - zmin) * EX, -y); uv.setXY(idx, x / ST.size, y / ST.size);
  }
  g.computeVertexNormals();
  texCv = document.createElement('canvas'); texCv.width = texCv.height = TEXPX; texG = texCv.getContext('2d');
  baseCv = document.createElement('canvas'); baseCv.width = baseCv.height = TEXPX;
  spCv = document.createElement('canvas'); spCv.width = spCv.height = TEXPX; spG = spCv.getContext('2d');
  paintBase();
  tex = new THREE.CanvasTexture(texCv); tex.anisotropy = 4;
  group.add(new THREE.Mesh(g, new THREE.MeshLambertMaterial({ map: tex, side: THREE.DoubleSide })));
  ST.trees.forEach(t => addTree(t));
  if (ST.depot) { const h = new THREE.Mesh(new THREE.ConeGeometry(3, 8, 4), new THREE.MeshLambertMaterial({ color: 0xffa94d })); h.position.copy(W3(ST.depot[0], ST.depot[1], zAt(ST.depot[0], ST.depot[1]))); h.position.y += 4; group.add(h); }
  // routes
  IDS().forEach(k => buildRoute(k));
  drone = new THREE.Group(); drone.add(new THREE.Mesh(new THREE.SphereGeometry(2.6, 16, 12), new THREE.MeshBasicMaterial({ color: 0xffffff })));
  stem = new THREE.Mesh(new THREE.CylinderGeometry(0.2, 0.2, 1, 6), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.5 })); drone.add(stem); group.add(drone);
  spraying = []; clearSpray();
  const c = ST.poly.length ? ST.poly.reduce((a, p) => [a[0] + p[0] / ST.poly.length, a[1] + p[1] / ST.poly.length], [0, 0]) : [ST.size / 2, ST.size / 2];
  cam.tx = c[0]; cam.tz = -c[1]; cam.ty = (zAt(c[0], c[1]) - zmin) * EX; cam.r = Math.max(260, (zmax - zmin) * EX * 2.2); cam.rBase = cam.r; placeCam();
  if (ST.plan) legend();
  dirty = true;
}
let spraying = [];
function paintBase() {
  const g = baseCv.getContext('2d'); g.drawImage(groundMap, 0, 0, TEXPX, TEXPX);
  const S = TEXPX / ST.size, Y = v => (ST.size - v) * S;
  if (ST.poly.length) {
    g.beginPath(); ST.poly.forEach((p, i) => i ? g.lineTo(p[0] * S, Y(p[1])) : g.moveTo(p[0] * S, Y(p[1]))); g.closePath();
    g.fillStyle = 'rgba(255,255,255,.12)'; g.fill(); g.strokeStyle = '#fff'; g.lineWidth = 3; g.stroke();
  }
  ST.trees.forEach(t => { g.strokeStyle = 'rgba(255,107,107,.9)'; g.lineWidth = 2; g.beginPath(); g.arc(t.x * S, Y(t.y), (t.r + 3.5) * S, 0, 6.2832); g.stroke(); });
  refreshTex();
}
function clearSpray() { spG.clearRect(0, 0, TEXPX, TEXPX); refreshTex(); }
function refreshTex() { texG.drawImage(baseCv, 0, 0); texG.drawImage(spCv, 0, 0); if (tex) tex.needsUpdate = true; dirty = true; }
function addTree(t) {
  const e = zAt(t.x, t.y);
  const cyl = new THREE.Mesh(new THREE.CylinderGeometry(t.r, t.r, 10, 20), new THREE.MeshLambertMaterial({ color: 0x2e7d4a, transparent: true, opacity: 0.7 }));
  cyl.position.copy(W3(t.x, t.y, e)); cyl.position.y += 5; group.add(cyl); treeObjs.push(cyl);
}
function buildRoute(k) {
  if (routeObj[k]) { group.remove(routeObj[k].mesh); routeObj[k].mesh.geometry.dispose(); }
  const r = ST.routes[k]; if (!r) return;
  const vec = r.x.map((x, i) => W3(x, r.y[i], r.alt[i]));
  const curve = new THREE.CatmullRomCurve3(vec, false, 'centripetal'), seg = vec.length - 1, rad = 4;
  const live = k === ST.strat;
  const geo = new THREE.TubeGeometry(curve, seg, live ? 0.75 : 0.35, rad, false);
  const mesh = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ vertexColors: true, transparent: !live, opacity: live ? 1 : 0.55 }));
  group.add(mesh); routeObj[k] = { mesh, geo, seg, rad, n: vec.length };
  colour(k); geo.setDrawRange(0, live ? 0 : seg * rad * 6);
  mesh.visible = live;
}
function colour(k) {
  const o = routeObj[k]; if (!o) return; const r = ST.routes[k], by = $('colby').value, per = o.rad + 1;
  const col = new THREE.BufferAttribute(new Float32Array(o.geo.attributes.position.count * 3), 3);
  const isLive = k === ST.strat, base = hex(COL[k]);
  for (let s = 0; s <= o.seg; s++) {
    const i = Math.min(s, o.n - 1); let c;
    if (!isLive) c = base;
    else if (by === 'tank') c = ramp(TANK, r.liq[i] / (ST.plan.params.tank_l || 20));
    else if (by === 'battery') c = ramp(BATT, (r.bat[i] - 15) / 85);
    else c = r.kind[i] === 1 ? [123, 216, 143] : (r.kind[i] === 2 ? [255, 209, 102] : [141, 162, 181]);
    if (isLive && by !== 'kind' && r.kind[i] === 0) c = c.map(v => v * 0.5 + 60);
    for (let q = 0; q < per; q++) col.setXYZ(s * per + q, c[0] / 255, c[1] / 255, c[2] / 255);
  }
  o.geo.setAttribute('color', col); col.needsUpdate = true; dirty = true;
}
$('colby').onchange = () => { colour(ST.strat); legend(); };
function legend() {
  const by = $('colby').value; let h = '<b>Routes (tick to show more than one)</b><br>';
  IDS().forEach(k => h += `<label style="display:inline-flex;gap:5px;margin:2px 8px 2px 0;color:var(--ink)"><input type="checkbox" id="ghost_${k}" ${k === ST.strat ? 'checked disabled' : ''}><span class="sw" style="background:${COL[k]}"></span>${NAMES[k]}</label><br>`);
  const bar = by === 'tank' ? TANK : by === 'battery' ? BATT : null;
  if (bar) h += `<div style="height:8px;border-radius:4px;margin-top:6px;background:linear-gradient(90deg,${bar.join(',')})"></div><div class="small" style="display:flex;justify-content:space-between"><span>${by === 'tank' ? 'light tank' : 'battery low'}</span><span>${by === 'tank' ? 'heavy tank' : 'battery full'}</span></div>`;
  else h += '<div class="small" style="margin-top:6px"><span class="sw" style="background:#7bd88f"></span>spraying <span class="sw" style="background:#ffd166"></span>turning <span class="sw" style="background:#8da2b5"></span>flying</div>';
  $('legend').innerHTML = h;
  IDS().forEach(k => { const c = $('ghost_' + k); if (c) c.onchange = () => { if (routeObj[k]) routeObj[k].mesh.visible = c.checked; dirty = true; }; });
}

// ------------------------------------------------------------------ live mission (server-sent events)
function closeStream() { if (ST.es) { ST.es.close(); ST.es = null; } }
function startStream(start) {
  closeStream();
  const sp = +$('speed').value;
  const es = new EventSource(`/api/mission/${ST.mid}/stream?strategy=${ST.strat}&start=${start}&speed=${sp}`);
  ST.es = es; ST.curIdx = start;
  es.onmessage = ev => {
    const f = JSON.parse(ev.data);
    if (f.done) { closeStream(); logLine('Finished: the whole field is sprayed and the drone is back at the refill point.'); $('play').textContent = 'Play'; ST.playing = false; return; }
    frame(f);
  };
  es.onerror = () => { };
  ST.playing = true; $('play').textContent = 'Pause'; $('play').classList.add('on');
}
function frame(f) {
  ST.curIdx = f.i; ST.frame = f;
  const r = ST.routes[ST.strat], o = routeObj[ST.strat];
  if (o) o.geo.setDrawRange(0, Math.min(f.i, o.seg) * o.rad * 6);
  const p = W3(f.x, f.y, f.alt); drone.position.copy(p);
  const gz = (zAt(f.x, f.y) - zmin) * EX, hgt = Math.max(0.5, p.y - gz); stem.scale.y = hgt; stem.position.y = -hgt / 2;
  if (f.kind === 'spraying') {
    const S = TEXPX / ST.size, sw = (ST.plan.params.swath || 6);
    spG.fillStyle = hexA(COL[ST.strat] || '#ff6b6b', .45);
    spG.beginPath(); spG.arc(f.x * S, (ST.size - f.y) * S, sw / 2 * S, 0, 6.2832); spG.fill();
    if (f.i % 4 === 0) refreshTex();
  }
  const tank = ST.plan.params.tank_l || 20;
  $('sBat').textContent = f.bat.toFixed(1) + ' %'; $('bBat').style.width = Math.max(0, f.bat) + '%'; $('bBat').style.background = f.bat < 25 ? 'var(--bad)' : f.bat < 45 ? 'var(--warn)' : 'var(--accent)';
  $('sLiq').textContent = f.liq.toFixed(1) + ' L'; $('bLiq').style.width = Math.min(100, f.liq / tank * 100) + '%';
  $('sKind').textContent = KIND[f.kind] || f.kind; $('sSort').textContent = f.sortie;
  $('sProg').textContent = (100 * f.progress).toFixed(0) + ' %'; $('bProg').style.width = 100 * f.progress + '%';
  $('sEta').textContent = f.eta >= 60 ? Math.floor(f.eta / 60) + ' min ' + String(Math.round(f.eta % 60)).padStart(2, '0') + ' s' : Math.round(f.eta) + ' s';
  if (f.event) logLine(f.event);
  dirty = true;
}
function logLine(t) {
  ST.log.push(t); const el = $('log'); el.style.display = 'block';
  el.innerHTML = ST.log.slice(-30).map(x => `<div>${x}</div>`).join(''); el.scrollTop = el.scrollHeight;
}
$('play').onclick = () => {
  if (ST.es) { closeStream(); ST.playing = false; $('play').textContent = 'Play'; return; }       // pause
  const n = ST.routes[ST.strat].x.length;
  if (ST.curIdx >= n - 2) { clearSpray(); ST.log = []; ST.curIdx = 0; }
  startStream(ST.curIdx || 0);
};
$('restart').onclick = () => { clearSpray(); ST.log = []; $('log').style.display = 'none'; const o = routeObj[ST.strat]; if (o) o.geo.setDrawRange(0, 0); startStream(0); };
$('speed').onchange = () => { if (ST.es) startStream(ST.curIdx); };
$('strat').onchange = () => { ST.strat = $('strat').value; for (const k in routeObj) buildRoute(k); legend(); clearSpray(); ST.log = []; $('log').style.display = 'none'; startStream(0); };

// ------------------------------------------------------------------ obstacle during the flight: server re-plans the rest
$('obst').onclick = async () => {
  if (!ST.mid) return;
  const r = ST.routes[ST.strat], i0 = ST.curIdx || 0;
  let j = Math.min(r.x.length - 2, i0 + 14);
  while (j < r.x.length - 2 && r.kind[j] !== 1) j++;
  const tree = { x: r.x[j], y: r.y[j], r: 2.5 };
  const wasPlaying = ST.playing; closeStream();
  $('obst').disabled = true;
  logLine('New tree detected ahead. Planning a new path around it...');
  try {
    const out = await post(`/api/mission/${ST.mid}/obstacle`, { strategy: ST.strat, step: i0, x: tree.x, y: tree.y, r: tree.r });
    ST.routes[ST.strat] = out.route; ST.trees = out.trees; addTree(tree); paintBase();
    IDS().forEach(k => { if (k === ST.strat) buildRoute(k); });
    const m = out.metrics;
    logLine(`<b class="good">New path ready in ${m.replan_seconds.toFixed(2)} s.</b> It costs ${m.extra_energy_pct >= 0 ? '+' : ''}${m.extra_energy_pct.toFixed(2)} % of a battery charge extra. The field is still ${(100 * m.coverage).toFixed(1)} % covered and the drone stays ${m.min_gap_m.toFixed(1)} m from the trees.`);
    const o = routeObj[ST.strat]; if (o) o.geo.setDrawRange(0, i0 * o.rad * 6);
    startStream(i0); if (!wasPlaying) { ST.playing = false; $('play').textContent = 'Play'; }
  } catch (e) { logLine(`<span class="bad">Re-plan failed: ${e.message}</span>`); }
  $('obst').disabled = false;
};

// ------------------------------------------------------------------ render loop
function loop() { requestAnimationFrame(loop); if (dirty && ST.page === 'viewer') { renderer.render(scene, camera); dirty = false; } }

// ------------------------------------------------------------------ start
async function init() {
  ST.sites = await api('/api/sites');
  fillSites(); $('site').value = ST.sites[1].id;
  await loadSite($('site').value);
  $('strat').innerHTML = ['fixed', 'standard', 'optimised'].map(k => `<option value="${k}">${NAMES[k]}</option>`).join('');
  $('strat').value = 'optimised';
  try { const ag = await api('/api/agents'); $('brain').innerHTML = '<option value="">No agent (plain search planner)</option>' + ag.map(n => `<option value="${n.name}">AI agent: ${n.name}</option>`).join(''); if (ag.length) $('brain').value = ag[0].name; } catch (e) { }
  resetResults(); info(); placeCam(); loop(); nav();
  const hp = location.hash.slice(1);
  if (PAGES.includes(hp)) go(hp);
  if (hp === 'demo') { await $('ex').onclick(); await planNow(); }
}
window.TS = { ST, planNow, frame };
init();
})();
