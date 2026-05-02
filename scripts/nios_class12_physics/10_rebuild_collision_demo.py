"""Rebuild the row-126 1D collision demo with a layout that ALWAYS
keeps the controls visible: sidebar layout (canvas left, controls
right) on wide screens, stacked layout on narrow ones with controls
above the canvas.

Re-uses the existing row + cache_key, so the SPA doesn't need to be
reloaded — the artifact at /generated-content/126/artifact will be
overwritten with the new HTML.

Run:
    PYTHONPATH=. .venv/Scripts/python.exe scripts/nios_class12_physics/10_rebuild_collision_demo.py
"""

from __future__ import annotations

from sqlalchemy import select

from app.db.session import SessionLocal
from app.llm.schemas.simulation import SimulationOutput
from app.models.generation import GeneratedContent
from app.rendering.simulation_html import render_simulation_html
from app.services.artifact_store import get_artifact_store


ROW_ID = 126


# Authored as a real Python string (no manual JSON escaping).
HTML_BODY = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>1D Collision sandbox</title>
<style>
  :root {
    --bg:#0b1020; --panel:rgba(15,20,35,0.94); --border:rgba(255,255,255,0.12);
    --text:#e8ecf5; --muted:#9aa3b2; --accent:#22d3ee;
    --c1:#3b82f6; --c2:#f97316; --p:#fbbf24; --ke:#22c55e; --bad:#ef4444;
  }
  html,body { margin:0; padding:0; height:100%; background:var(--bg); color:var(--text);
    font-family:-apple-system,'Segoe UI',Roboto,sans-serif; overflow:hidden; }

  /* Sidebar layout: canvas takes the flex region, controls live in a
     fixed-width side panel that is always visible. On narrow screens
     the layout stacks with the controls above the canvas (still
     always visible). */
  #root { display:flex; height:100%; min-height:0; }
  #stage { position:relative; flex:1 1 auto; min-width:0; min-height:0; background:#070b18; }
  canvas { position:absolute; inset:0; width:100%; height:100%; display:block; }

  #side { width:340px; flex:0 0 340px; min-height:0; overflow:auto;
    background:var(--panel); border-left:1px solid var(--border);
    padding:14px 16px; box-sizing:border-box; }
  @media (max-width: 760px) {
    #root { flex-direction:column; }
    #side { width:100%; flex:0 0 auto; max-height:55vh; border-left:none; border-bottom:1px solid var(--border); order:-1; }
    #stage { flex:1 1 auto; }
  }

  h2 { margin:14px 0 6px; font-size:11px; text-transform:uppercase; letter-spacing:0.06em; color:var(--muted); }
  h2:first-child { margin-top:0; }
  .label-c1 { color:var(--c1); font-weight:700; }
  .label-c2 { color:var(--c2); font-weight:700; }
  .row { display:grid; grid-template-columns: 80px 1fr 70px; align-items:center; gap:10px; margin:6px 0; font-size:13px; }
  .row label { color:#cdd5e2; }
  .row input[type=range] { width:100%; accent-color:var(--accent); }
  .row .v { text-align:right; color:var(--accent); font-variant-numeric:tabular-nums; font-size:12px; }
  .modes { display:flex; gap:8px; }
  .modes button { background:var(--bg); color:var(--text); border:1px solid var(--border); border-radius:999px; padding:6px 12px; font-size:12px; cursor:pointer; flex:1; }
  .modes button.active { background:var(--accent); color:var(--bg); border-color:var(--accent); }
  .actions { display:flex; gap:10px; margin-top:14px; }
  button.primary { background:var(--accent); color:var(--bg); border:1px solid var(--accent); border-radius:999px; padding:9px 22px; font-size:13px; font-weight:700; cursor:pointer; flex:1; }
  button.primary:hover { filter:brightness(1.1); }
  button.ghost { background:transparent; color:var(--text); border:1px solid var(--border); border-radius:999px; padding:9px 16px; font-size:13px; cursor:pointer; }
  button.ghost:hover { border-color:var(--accent); color:var(--accent); }

  /* Live-readout bars */
  .barRow { display:grid; grid-template-columns: 100px 1fr 86px; gap:6px; align-items:center; margin:5px 0; font-size:11px; color:var(--muted); }
  .bar { position:relative; height:10px; background:rgba(255,255,255,0.06); border-radius:5px; overflow:hidden; }
  .bar > span { position:absolute; top:0; left:0; height:100%; }
  .bar.p > span { background:var(--p); }
  .bar.ke > span { background:var(--ke); }
  .bar > span.transition { transition: width 350ms ease, background 200ms ease; }
  .num { color:#dbe1ec; font-variant-numeric:tabular-nums; text-align:right; font-size:11px; }
  .tag { display:inline-block; padding:1px 6px; border-radius:999px; background:rgba(34,197,94,0.18); color:var(--ke); font-size:10px; margin-left:4px; }
  .tag.bad { background:rgba(239,68,68,0.18); color:#fca5a5; }

  .hint { position:absolute; left:14px; bottom:14px; color:var(--muted); font-size:11px; pointer-events:none;
    background:rgba(11,16,32,0.6); padding:5px 9px; border:1px solid var(--border); border-radius:6px; }
</style>
</head>
<body>
<div id="root">
  <div id="stage">
    <canvas id="c"></canvas>
    <div class="hint">Press Launch to run the collision · Adjust sliders any time</div>
  </div>

  <aside id="side">
    <h2><span class="label-c1">Cart A</span></h2>
    <div class="row"><label>Mass</label><input id="mA" type="range" min="0.5" max="10" step="0.1" value="2" /><span class="v" id="mA-v"></span></div>
    <div class="row"><label>Velocity</label><input id="vA" type="range" min="-10" max="10" step="0.1" value="4" /><span class="v" id="vA-v"></span></div>

    <h2><span class="label-c2">Cart B</span></h2>
    <div class="row"><label>Mass</label><input id="mB" type="range" min="0.5" max="10" step="0.1" value="3" /><span class="v" id="mB-v"></span></div>
    <div class="row"><label>Velocity</label><input id="vB" type="range" min="-10" max="10" step="0.1" value="-2" /><span class="v" id="vB-v"></span></div>

    <h2>Collision type</h2>
    <div class="modes">
      <button id="m-elastic">Elastic</button>
      <button id="m-inelastic">Inelastic (stick)</button>
    </div>

    <h2>Live readout</h2>
    <div id="bars"></div>

    <div class="actions">
      <button class="primary" id="go">▶  Launch</button>
      <button class="ghost" id="reset">Reset</button>
    </div>
  </aside>
</div>

<script>
(function () {
  var canvas = document.getElementById('c');
  var ctx = canvas.getContext('2d');
  var dpr = Math.min(window.devicePixelRatio || 1, 2);
  var W = 0, H = 0;

  function resize() {
    var r = canvas.parentElement.getBoundingClientRect();
    W = r.width; H = r.height;
    canvas.width = Math.round(W * dpr);
    canvas.height = Math.round(H * dpr);
    canvas.style.width = W + 'px';
    canvas.style.height = H + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    drawScene();
  }
  window.addEventListener('resize', resize);

  var state = { mA: 2, vA: 4, mB: 3, vB: -2, mode: 'elastic' };
  var sim = null;     // { xA, xB, vA, vB, collided }

  function readControls() {
    state.mA = parseFloat(document.getElementById('mA').value);
    state.vA = parseFloat(document.getElementById('vA').value);
    state.mB = parseFloat(document.getElementById('mB').value);
    state.vB = parseFloat(document.getElementById('vB').value);
    document.getElementById('mA-v').textContent = state.mA.toFixed(1) + ' kg';
    document.getElementById('vA-v').textContent = state.vA.toFixed(1) + ' m/s';
    document.getElementById('mB-v').textContent = state.mB.toFixed(1) + ' kg';
    document.getElementById('vB-v').textContent = state.vB.toFixed(1) + ' m/s';
    drawScene();
    updateBars();
  }

  function setMode(m) {
    state.mode = m;
    document.getElementById('m-elastic').classList.toggle('active', m === 'elastic');
    document.getElementById('m-inelastic').classList.toggle('active', m === 'inelastic');
    updateBars();
  }
  ['mA','vA','mB','vB'].forEach(function(id){
    document.getElementById(id).addEventListener('input', readControls);
  });
  document.getElementById('m-elastic').addEventListener('click', function(){ setMode('elastic'); });
  document.getElementById('m-inelastic').addEventListener('click', function(){ setMode('inelastic'); });

  function totals(vA, vB) {
    var p = state.mA * vA + state.mB * vB;
    var ke = 0.5 * state.mA * vA * vA + 0.5 * state.mB * vB * vB;
    return { p: p, ke: ke };
  }

  function postCollision() {
    if (state.mode === 'elastic') {
      var u1 = state.vA, u2 = state.vB, m1 = state.mA, m2 = state.mB;
      var v1 = ((m1 - m2) * u1 + 2 * m2 * u2) / (m1 + m2);
      var v2 = ((m2 - m1) * u2 + 2 * m1 * u1) / (m1 + m2);
      return { vA: v1, vB: v2 };
    }
    var v = (state.mA * state.vA + state.mB * state.vB) / (state.mA + state.mB);
    return { vA: v, vB: v };
  }

  function updateBars() {
    var pre = totals(state.vA, state.vB);
    var post = postCollision();
    var postT = totals(post.vA, post.vB);
    var maxAbsP = Math.max(Math.abs(pre.p), Math.abs(postT.p), 1);
    var maxKE = Math.max(pre.ke, postT.ke, 1);
    var pConserved = Math.abs(pre.p - postT.p) < 1e-6;
    var keConserved = Math.abs(pre.ke - postT.ke) < 1e-6;
    var keDelta = pre.ke ? ((postT.ke - pre.ke) / pre.ke * 100) : 0;
    var rows = '' +
      barRow('p before', pre.p, maxAbsP, 'p',  pre.p.toFixed(2) + ' kg·m/s') +
      barRow('p after',  postT.p, maxAbsP, 'p', postT.p.toFixed(2) +
        (pConserved ? ' <span class="tag">conserved</span>' : ' <span class="tag bad">drift</span>')) +
      barRow('KE before', pre.ke, maxKE, 'ke', pre.ke.toFixed(2) + ' J') +
      barRow('KE after',  postT.ke, maxKE, 'ke', postT.ke.toFixed(2) +
        (keConserved ? ' <span class="tag">conserved</span>' : ' <span class="tag bad">' + keDelta.toFixed(0) + '% Δ</span>'));
    document.getElementById('bars').innerHTML = rows;
  }

  function barRow(label, val, max, kind, num) {
    var pct = Math.min(100, Math.abs(val) / max * 100);
    return '<div class="barRow"><div>' + label + '</div>' +
           '<div class="bar ' + kind + '"><span class="transition" style="width:' + pct.toFixed(0) + '%"></span></div>' +
           '<div class="num">' + num + '</div></div>';
  }

  // --- Drawing ---------------------------------------------------------
  function drawScene() {
    if (!W || !H) return;
    ctx.fillStyle = '#070b18'; ctx.fillRect(0, 0, W, H);
    var trackY = H * 0.55;
    // Track
    ctx.strokeStyle = 'rgba(255,255,255,0.18)';
    ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(W * 0.04, trackY); ctx.lineTo(W * 0.96, trackY); ctx.stroke();
    ctx.strokeStyle = 'rgba(255,255,255,0.08)';
    ctx.lineWidth = 1;
    for (var i = 0; i <= 12; i++) {
      var x = W * 0.04 + (W * 0.92) * (i / 12);
      ctx.beginPath(); ctx.moveTo(x, trackY); ctx.lineTo(x, trackY + 6); ctx.stroke();
    }
    drawCart(sim ? sim.xA : 0.25, state.mA, '#3b82f6', 'A', sim ? sim.vA : state.vA, trackY);
    drawCart(sim ? sim.xB : 0.75, state.mB, '#f97316', 'B', sim ? sim.vB : state.vB, trackY);
  }

  function drawCart(xPct, m, color, label, v, trackY) {
    var x = W * 0.04 + (W * 0.92) * xPct;
    var size = 24 + Math.sqrt(m) * 7;
    ctx.fillStyle = color;
    ctx.fillRect(x - size / 2, trackY - size, size, size);
    ctx.strokeStyle = 'rgba(255,255,255,0.5)';
    ctx.strokeRect(x - size / 2, trackY - size, size, size);
    ctx.fillStyle = '#fff';
    ctx.font = 'bold 18px ui-sans-serif,system-ui';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText(label, x, trackY - size / 2);
    // Velocity arrow
    var mag = Math.min(70, Math.abs(v) * 7);
    var dir = v >= 0 ? 1 : -1;
    if (mag > 2) {
      ctx.strokeStyle = color; ctx.lineWidth = 3;
      var ax = x + dir * (size / 2 + 4), ay = trackY - size / 2;
      ctx.beginPath(); ctx.moveTo(ax, ay); ctx.lineTo(ax + dir * mag, ay); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(ax + dir * mag, ay);
      ctx.lineTo(ax + dir * (mag - 8), ay - 6);
      ctx.lineTo(ax + dir * (mag - 8), ay + 6);
      ctx.closePath(); ctx.fill();
    }
    ctx.fillStyle = '#cdd5e2';
    ctx.font = '12px ui-monospace,Consolas,monospace';
    ctx.fillText(m.toFixed(1) + ' kg · ' + v.toFixed(1) + ' m/s', x, trackY + 22);
  }

  // --- Animation -------------------------------------------------------
  var running = false;
  var lastT = 0;

  function start() {
    sim = { xA: 0.18, xB: 0.78, vA: state.vA, vB: state.vB, collided: false };
    running = true;
    lastT = performance.now();
    requestAnimationFrame(step);
  }

  function step(t) {
    if (!running) return;
    var dt = Math.min(0.04, (t - lastT) / 1000);
    lastT = t;
    var trackLen = 14;
    sim.xA += sim.vA * dt / trackLen;
    sim.xB += sim.vB * dt / trackLen;
    if (!sim.collided && sim.xA + 0.04 >= sim.xB - 0.04 && sim.vA - sim.vB > 0) {
      var post = postCollision();
      sim.vA = post.vA; sim.vB = post.vB;
      sim.collided = true;
    }
    var leftOff = sim.xA < -0.05 || sim.xB > 1.05;
    var settled = sim.collided && Math.abs(sim.vA) + Math.abs(sim.vB) < 0.05;
    if (leftOff || settled) running = false;
    drawScene();
    if (running) requestAnimationFrame(step);
  }

  document.getElementById('go').addEventListener('click', start);
  document.getElementById('reset').addEventListener('click', function () {
    running = false; sim = null; drawScene(); updateBars();
  });

  // Init: run resize once after layout settles, plus a delayed second
  // pass for browsers that report 0 size on first measurement.
  setMode('elastic');
  readControls();
  setTimeout(resize, 0);
  setTimeout(resize, 100);
})();
</script>
</body>
</html>
"""


def main() -> None:
    db = SessionLocal()
    store = get_artifact_store()
    try:
        row = db.get(GeneratedContent, ROW_ID)
        if row is None:
            raise SystemExit(f"row {ROW_ID} not found")
        if row.content_type.value != "simulation":
            raise SystemExit(f"row {ROW_ID} is not a simulation: {row.content_type}")

        # Build the new payload from the existing one (preserves title /
        # instructions / outcome_codes_covered) and only swap html_body.
        old = row.output_json or {}
        payload = {
            "template": "custom_html",
            "title": old.get("title", "1D Collision sandbox"),
            "instructions": old.get(
                "instructions",
                "Two carts on a frictionless track. Adjust mass and velocity, "
                "pick the collision type, then press Launch.",
            ),
            "outcome_codes_covered": old.get("outcome_codes_covered", []),
            "custom": {
                "requires_libraries": [],
                "html_body": HTML_BODY,
            },
        }
        validated = SimulationOutput.model_validate(payload)
        row.output_json = validated.model_dump(mode="json")

        # Re-render the artifact and save with the same name (overwrites).
        data = render_simulation_html(validated)
        # Strip the previous artifact filename's extension and re-save.
        ext = (row.artifact_url or f"{row.id}.html").rsplit(".", 1)[-1] or "html"
        row.artifact_url = store.save(content_id=row.id, extension=ext, data=data)
        db.commit()
        print(f"[ok] row {row.id}: rewrote html_body, re-rendered artifact = {row.artifact_url} ({len(data):,} bytes)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
