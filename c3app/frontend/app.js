/* TeaSpray Planner - front end. Talks to the FastAPI backend only; all planning and energy numbers come from the server. */
(function () {
"use strict";
const $ = id => document.getElementById(id);
const ST = {
  sites: [], site: null, z: null, n: 0, dx: 5, size: 300, zs: 1,
  poly: [], closed: false, trees: [], depot: null, tool: 'field',
  plan: null, mid: null, strat: 'optimised', routes: {}, es: null, playing: true, frame: null, spraying: [],
  log: [], bw: 777.6
};
const COL = { fixed: '#ff6b6b', standard: '#8fb6ff', optimised: '#7bd88f', agent: '#ffd166' };
const IDS = () => (ST.plan ? ST.plan.strategies.map(s => s.id) : ['fixed', 'standard', 'optimised']);
const NAMES = { fixed: 'No tree avoidance (unsafe)', standard: 'Usual route', optimised: 'Search planner (comparison)', agent: 'System route (AI agent)' };
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
  toolHelp();
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
  $('tab3d').disabled = false;
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
    ST.plan = null; ST.routes = {}; ST.mid = null; closeStream();
    ST.poly = o.polygon || []; ST.closed = !!o.polygon; ST.trees = o.trees || []; ST.depot = o.depot || null;
    $('zs').value = 1; $('zsv').textContent = '1.0x';
    await loadSite(o.site.id);
    if (ST.closed && !ST.depot) {            // no refill point in the file: suggest one just outside the south-west corner
      const mx = Math.min(...ST.poly.map(p => p[0])), my = Math.min(...ST.poly.map(p => p[1]));
      ST.depot = [Math.max(5, mx - 12), Math.max(5, my - 12)];
    }
    info(); drawMap(); $('results').innerHTML = '';
    $('estmsg').innerHTML = `<span class="good">Loaded ${o.site.name}: a ${o.site.size} m square area, ${o.site.elevation} m above sea level, hills rise ${o.site.relief} m.</span>` +
      (o.polygon ? ` Your field is ${o.area_ha.toFixed(2)} ha.` : ' Now go to step 2 and draw your field on the map.') + (o.warnings || []).map(w => `<br><span class="warn">${w}</span>`).join('');
    build3d(); show('map');
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
  if (!ST.closed || ST.poly.length < 3) { $('planmsg').innerHTML = '<span class="bad">Step 2 is not finished: draw the field and press "Finish the field shape" (or press "Use example field").</span>'; return; }
  if (!ST.depot) { $('planmsg').innerHTML = '<span class="bad">Step 2 is not finished: click "Refill point" and then click the map where the truck stands.</span>'; return; }
  $('busy').textContent = 'Planning your mission: comparing the usual route with the system\'s route...'; $('busy').style.display = 'flex'; $('plan').disabled = true; $('planmsg').textContent = ''; $('welcome').style.display = 'none';
  try {
    const out = await post('/api/plan', { site: ST.site, polygon: ST.poly, trees: ST.trees, depot: ST.depot, params: params(), z_scale: ST.zs, agent_model: $('brain') && $('brain').value ? $('brain').value : null });
    closeStream();
    ST.plan = out; ST.mid = out.mission_id; ST.bw = out.battery_wh || 777.6;
    ST.routes = {}; out.strategies.forEach(s => ST.routes[s.id] = s.route);
    ST.strat = out.recommended; ST.trees = out.trees; ST.log = [];
    $('tab3d').disabled = false;
    $('strat').innerHTML = IDS().map(k => `<option value="${k}">${NAMES[k]}</option>`).join(''); $('strat').value = ST.strat;
    results(out); drawMap(); build3d(); show('3d');
    $('s4').textContent = 'done'; $('st4').classList.add('done');
    $('planmsg').innerHTML = `<span class="good">Done in ${out.seconds.toFixed(1)} s.</span> The advice is below. The flight is playing in the 3D view.`;
    $('results').scrollIntoView({ behavior: 'smooth', block: 'start' });
    startStream(0);
  } catch (e) { $('planmsg').innerHTML = `<span class="bad">${e.message}</span>`; }
  $('busy').style.display = 'none'; $('busy').textContent = 'Planning the mission...'; $('plan').disabled = false;
}
$('plan').onclick = planNow;

function hexA(h, a) { const n = parseInt(h.slice(1), 16); return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${a})`; }
function results(p) {
  const S = Object.fromEntries(p.strategies.map(s => [s.id, s.metrics]));
  const std = S.standard, fix = S.fixed, ag = p.agent, useAg = !!(S.agent && ag && ag.used), opt = useAg ? S.agent : S.optimised;
  const sysName = useAg ? 'System (AI agent)' : 'System (search planner)';
  const sav = (1 - opt.energy_pct / std.energy_pct) * 100;
  const wh = m => (m.energy_pct / 100 * ST.bw);
  const ra = p.route_advice;
  const cls = ra ? ra.choice : (sav >= 5 ? 'system' : (sav >= 1 ? 'either' : 'usual'));
  const head = ra ? ra.headline : (sav >= 1 ? "Fly the system's route" : 'Fly the usual route');
  const f2 = v => v.toFixed(2), f0 = v => v.toFixed(0);
  const row = (lab, a, b, lower, fmt, unit) => { const A = +fmt(a), B = +fmt(b), wA = lower ? A < B : A > B, wB = lower ? B < A : B > A; return `<tr><td>${lab}</td><td class="${wA ? 'win' : ''}">${fmt(a)}${unit || ''}</td><td class="${wB ? 'win' : ''}">${fmt(b)}${unit || ''}</td></tr>`; };
  let h = `<div class="verdict ${cls}"><div class="lab">Our advice for this field</div><div class="head">${head}</div>
    <div class="savebox"><span class="big ${sav > 0 ? 'good' : ''}">${sav.toFixed(1)}%</span><span class="small">${sav >= 0 ? 'less' : 'more'} battery than the usual route, with the same ground covered (${f0(wh(opt) / p.field_ha)} instead of ${f0(wh(std) / p.field_ha)} Wh per hectare, field ${p.field_ha.toFixed(2)} ha)</span></div>
    <table class="cmp"><tr><th></th><th>Usual route</th><th>${sysName}</th></tr>
      ${row('Battery used (full charges)', std.energy_pct / 100, opt.energy_pct / 100, true, f2)}
      ${row('Take-offs', std.sorties, opt.sorties, true, f0)}
      ${row('Time (minutes)', std.minutes, opt.minutes, true, f0)}
      ${row('Tree contacts', std.contact_steps, opt.contact_steps, true, f0)}
      ${row('Field covered', 100 * std.coverage, 100 * opt.coverage, false, v => v.toFixed(1), ' %')}
    </table>`;
  if (ra) {
    h += `<div class="small" style="margin-top:8px"><b>Why</b></div><ul class="small" style="margin:2px 0 4px 18px;padding:0">${ra.reasons.map(t => `<li>${t}</li>`).join('')}</ul>`;
    if (ra.cautions.length) h += `<div class="small"><b>Things to think about</b></div><ul class="small" style="margin:2px 0 4px 18px;padding:0">${ra.cautions.map(t => `<li>${t}</li>`).join('')}</ul>`;
  }
  h += `<div class="small" style="margin-top:6px"><b>Watch the flight</b> (opens the 3D view):</div>
    <div style="display:flex;gap:8px;margin-top:4px"><button id="pickUsual" style="flex:1">Watch the usual route</button><button id="pickSystem" class="on" style="flex:1">Watch the system's route</button></div>
    <div class="small" id="pickMsg" style="margin-top:4px"></div></div>`;

  const a = p.depot_advice;
  if (a && a.saving_pct > 0.2) h += `<div class="card"><b>Tip: move the refill point</b><div class="small">The blue circle on the map is a better place for the truck. It would save a further <b class="good">${a.saving_pct.toFixed(1)}%</b> battery.</div><button id="useDepot" style="margin-top:6px;width:100%">Use that spot and plan again</button></div>`;

  // ---- details, hidden until asked for
  let d = '';
  if (ag) d += ag.error ? `<div class="card"><b class="bad">The AI agent could not run</b><div class="small">${ag.error}</div></div>` :
    `<div class="card"><b>What the AI agent decided</b> <span class="tag">${ag.model}</span><div class="small">It turned the rows to <b>${ag.decisions.theta.toFixed(0)}°</b>, started the sweep ${ag.decisions.flip_rows ? 'from the other side' : 'from the usual side'}, and carried <b>${ag.decisions.loads_l.join(' L, ')} L</b> on the trips. A lighter drone burns less battery. Agent vs usual route: <b class="${ag.vs_standard_pct > 0 ? 'good' : 'bad'}">${ag.vs_standard_pct.toFixed(1)}%</b> battery.${ag.note ? `<br><span class="bad">${ag.note}</span>` : ''}</div></div>`;
  const SL = p.slope_load, su = SL && SL.standard, sm = SL && SL[p.recommended];
  if (su && sm && p.recommended !== 'standard') {
    const f = v => (v == null ? '-' : v.toFixed(0)), idx = 100 * sm.mass_climb / Math.max(su.mass_climb, 1e-9);
    const dh = su.climb_heavy_m - sm.climb_heavy_m, dl = sm.climb_light_m - su.climb_light_m;
    const msg = dh > 1
      ? `The system's route climbs <b class="good">${dh.toFixed(0)} m less</b> while the tank is heavy${dl > 1 ? ` and ${dl.toFixed(0)} m more while it is light` : ''}. Climbing weighted by the drone's weight is <b class="${idx < 100 ? 'good' : 'warn'}">${Math.abs(100 - idx).toFixed(1)}% ${idx < 100 ? 'lower' : 'higher'}</b>.`
      : `On this field the system's route does not move the climbing to the light-tank part (heavy-tank climb: ${f(su.climb_heavy_m)} m usual, ${f(sm.climb_heavy_m)} m system). Its saving comes from lighter loads instead.`;
    d += `<div class="card"><b>Does the drone climb with a heavy or a light tank?</b>
      <table style="margin-top:6px"><tr><th>Route</th><th>Climb, heavy tank (m)</th><th>Climb, light tank (m)</th><th>Weight x climb</th></tr>
      <tr><td>Usual</td><td>${f(su.climb_heavy_m)}</td><td>${f(su.climb_light_m)}</td><td>100</td></tr>
      <tr><td>System</td><td>${f(sm.climb_heavy_m)}</td><td>${f(sm.climb_light_m)}</td><td>${idx.toFixed(0)}</td></tr></table>
      <div class="small" style="margin-top:4px">${msg}</div>
      <div class="small" style="margin-top:4px">Heavy = tank more than 2/3 full, light = less than 1/3. Climbing is only a small part of the battery use, so this effect is small; most of the saving comes from lighter loads. To see it: in the 3D view choose "Colour by how heavy the tank is" and untick the satellite picture in step 3.</div></div>`;
  }
  d += `<div class="card"><b>Where the saving comes from</b><table style="margin-top:6px"><tr><th>One change at a time</th><th>Battery saved</th></tr>`;
  p.levers.forEach((l, i) => { if (i) d += `<tr><td>${l.label}</td><td class="${l.vs_standard_pct > 0 ? 'good' : ''}">${l.vs_standard_pct >= 0 ? '+' : ''}${l.vs_standard_pct.toFixed(1)}%</td></tr>`; });
  d += `</table></div>`;
  d += `<div class="card"><b>All routes side by side</b><table style="margin-top:6px"><tr><th>Route</th><th>Battery</th><th>Take-offs</th><th>Min</th><th>Covered</th><th>Tree hits</th></tr>`;
  p.strategies.forEach(s => {
    const m = s.metrics;
    d += `<tr><td><span class="sw" style="background:${COL[s.id]}"></span>${NAMES[s.id] || s.name}</td><td>${(m.energy_pct / 100).toFixed(2)}</td><td>${m.sorties}</td><td>${m.minutes.toFixed(0)}</td><td>${(100 * m.coverage).toFixed(1)}%</td><td class="${m.contact_steps ? 'bad' : 'good'}">${m.contact_steps}</td></tr>`;
  });
  d += `</table><div class="small" style="margin-top:4px">Battery is in full charges (1.00 = one whole battery). Tree hits = moments closer than 1 m to a tree.${fix.contact_steps ? ` The "no avoidance" route flies through trees ${fix.contact_steps} times; the planned routes stay at least ${Math.min(std.min_gap_m, opt.min_gap_m).toFixed(1)} m away.` : ''}</div></div>`;
  d += `<div class="card"><b>What if you spray faster or slower?</b>${speedChart(p)}<div class="small">Battery for the whole field against spray speed. Check the drone's manual and spray drift before going above its rated speed.</div></div>`;
  d += `<div class="card"><b>Assumptions and limits</b><ul class="small" style="margin:4px 0 0 18px;padding:0">${p.assumptions.map(x => `<li>${x}</li>`).join('')}</ul></div>`;
  h += `<details class="more"><summary>Show the details (why it is better, numbers, assumptions)</summary>${d}</details>`;
  h += `<button id="copySum" style="width:100%;margin-top:10px">Copy a short summary to share</button><div class="small" id="copyMsg"></div>`;
  $('results').innerHTML = h;

  const pick = id => { $('strat').value = id; $('strat').onchange(); show('3d'); const t = $('pickMsg'); if (t) t.textContent = 'Showing: ' + NAMES[id] + '. Press Play in the 3D view to watch it.'; };
  const pu = $('pickUsual'), ps = $('pickSystem');
  if (pu) pu.onclick = () => pick(ra ? ra.usual_id : 'standard');
  if (ps) ps.onclick = () => pick(ra ? ra.recommended_id : p.recommended);
  const b = $('useDepot'); if (b) b.onclick = () => { ST.depot = [+a.x.toFixed(1), +a.y.toFixed(1)]; drawMap(); planNow(); };
  const cs = $('copySum');
  if (cs) cs.onclick = async () => {
    const txt = `TeaSpray Planner summary\nField: ${p.field_ha.toFixed(2)} ha, tank ${p.params.tank_l} L\nAdvice: ${head}\nBattery: ${(opt.energy_pct / 100).toFixed(2)} charges (system) vs ${(std.energy_pct / 100).toFixed(2)} (usual), ${sav.toFixed(1)}% ${sav >= 0 ? 'less' : 'more'}\nTake-offs: ${opt.sorties} vs ${std.sorties}\nTime: ${opt.minutes.toFixed(0)} vs ${std.minutes.toFixed(0)} min\nTree contacts: ${opt.contact_steps} vs ${std.contact_steps}\nNote: figures come from an energy model checked against real flight logs; the route has not been flown yet.`;
    try { await navigator.clipboard.writeText(txt); $('copyMsg').textContent = 'Copied.'; } catch (e) { $('copyMsg').textContent = txt; }
  };
}
function speedChart(p) {
  const d = p.speed_curve, W = 330, H = 120, L = 34, B = 20, mx = Math.max(...d.map(r => r.energy_pct)) / 100;
  const X = i => L + i * (W - L - 8) / (d.length - 1), Y = v => 8 + (H - B - 8) * (1 - v / mx);
  let s = `<svg width="100%" viewBox="0 0 ${W} ${H}"><g stroke="#27402f">`;
  [0, 0.5, 1].forEach(f => s += `<line x1="${L}" x2="${W - 8}" y1="${Y(mx * f)}" y2="${Y(mx * f)}"/>`);
  s += `</g>`;
  [0, 0.5, 1].forEach(f => s += `<text x="2" y="${Y(mx * f) + 3}">${(mx * f).toFixed(1)}</text>`);
  s += `<polyline fill="none" stroke="#7bd88f" stroke-width="2" points="${d.map((r, i) => X(i) + ',' + Y(r.energy_pct / 100)).join(' ')}"/>`;
  d.forEach((r, i) => s += `<circle cx="${X(i)}" cy="${Y(r.energy_pct / 100)}" r="3" fill="#7bd88f"/><text x="${X(i) - 8}" y="${H - 6}">${r.kmh}</text>`);
  s += `<text x="${L}" y="${H - 6}" style="display:none"></text></svg><div class="small" style="margin-top:-4px">km/h along the bottom, battery charges up the side</div>`;
  return s;
}

// ------------------------------------------------------------------ tabs
function show(which) {
  const is3 = which === '3d';
  $('mapwrap').style.display = is3 ? 'none' : 'flex'; $('c3d').style.display = is3 ? 'block' : 'none';
  $('tabMap').classList.toggle('on', !is3); $('tab3d').classList.toggle('on', is3);
  $('toolbar').style.display = is3 ? 'none' : 'block'; $('hud').style.display = is3 && ST.plan ? 'block' : 'none'; $('legend').style.display = is3 && ST.plan ? 'block' : 'none'; $('log').style.display = is3 && ST.log.length ? 'block' : 'none';
  if (is3) { resize(); dirty = true; } else drawMap();
}
$('tabMap').onclick = () => show('map'); $('welcomeClose').onclick = e => { e.preventDefault(); $('welcome').style.display = 'none'; }; $('tab3d').onclick = () => { if (!ST.plan) build3d(); show('3d'); };

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
$('strat').onchange = () => { ST.strat = $('strat').value; for (const k in routeObj) buildRoute(k); legend(); clearSpray(); startStream(0); };

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
function loop() { requestAnimationFrame(loop); if (dirty && $('c3d').style.display !== 'none') { renderer.render(scene, camera); dirty = false; } }

// ------------------------------------------------------------------ start
async function init() {
  ST.sites = await api('/api/sites');
  fillSites(); $('site').value = ST.sites[1].id;
  await loadSite($('site').value);
  $('strat').innerHTML = ['fixed', 'standard', 'optimised'].map(k => `<option value="${k}">${NAMES[k]}</option>`).join('');
  $('strat').value = 'optimised';
  try { const ag = await api('/api/agents'); $('brain').innerHTML = '<option value="">No agent (plain search planner)</option>' + ag.map(n => `<option value="${n.name}">AI agent: ${n.name}</option>`).join(''); if (ag.length) $('brain').value = ag[0].name; } catch (e) { }
  info(); placeCam(); loop();
  if (location.hash === '#demo') { await $('ex').onclick(); await planNow(); }
}
window.TS = { ST, planNow, frame };
init();
})();
