"""Genera un reporte HTML autocontenido a partir de results.json (solo stdlib).

Uso:
    python dashboard/build_report.py results/results.json results/report.html

El JSON va embebido en <script id="data" type="application/json">; todo el dibujo ocurre en el
navegador (Chart.js desde cdnjs, fuentes de Google Fonts). Cada sección se oculta si falta su dato.
"""
from __future__ import annotations

import json
import math
import os
import sys


def _clean(o):
    """NaN/Infinity no son JSON válido para el navegador: se reemplazan por null."""
    if isinstance(o, float):
        return None if (math.isnan(o) or math.isinf(o)) else o
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_clean(v) for v in o]
    return o


def _slim(R: dict) -> dict:
    """Quita campos pesados que el reporte no usa."""
    for q in R.get("quantum", []):
        q.pop("perm_distribution", None)
    for h in R.get("hybrid", []):
        hist = h.get("history") or []
        if len(hist) > 600:                       # submuestreo para no inflar el HTML
            step = math.ceil(len(hist) / 600)
            h["history"] = hist[::step] + [hist[-1]]
    return R


def build(json_path: str, out_path: str) -> str:
    with open(json_path, encoding="utf-8") as fh:
        R = json.load(fh)
    payload = json.dumps(_clean(_slim(R)), ensure_ascii=False, allow_nan=False)
    payload = payload.replace("</", "<\\/")       # no cerrar el <script> por accidente
    html = TEMPLATE.replace("__DATA__", payload)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(html)
    return out_path


TEMPLATE = r"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>QGate · Vuelos a puertas</title>
<meta name="description" content="QGate: asignación de vuelos a puertas (QAP qap10) con QAOA híbrido en Qiskit. IBM Quantum Hackathon 2026, reto NTT DATA.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;600;700&family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
:root {
  color-scheme: dark;
  --bg: #0a101c;
  --surface: #111a2b;
  --surface-2: #17233a;
  --line: #24324d;
  --grid: #1c2840;
  --text: #e8edf5;
  --text-2: #a9b4c7;
  --muted: #74829b;
  --amber: #f5b942;          /* acento de interfaz (texto, badges) */
  --cyan-text: #5fd4ee;      /* texto de lo cuántico */
  --ok: #3ecf8e;
  /* series (validadas sobre --surface: banda L, croma, CVD, contraste) */
  --s-quantum: #1c9ab8;
  --s-quantum-2: #7fd3e6;
  --s-classic: #c98500;
  --s-sa: #9085e9;
  --s-alt: #e66767;
  --s-ref: #74829b;
  --radius: 14px;
  --font-ui: "Inter", system-ui, sans-serif;
  --font-head: "Space Grotesk", "Inter", sans-serif;
  --font-num: "JetBrains Mono", ui-monospace, monospace;
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  margin: 0; background: var(--bg); color: var(--text);
  font: 15px/1.5 var(--font-ui);
  background-image: radial-gradient(1200px 500px at 85% -10%, rgba(28,154,184,.13), transparent 60%),
                    radial-gradient(900px 420px at -10% 10%, rgba(245,185,66,.08), transparent 60%);
  background-attachment: fixed;
}
a { color: var(--cyan-text); }
.wrap { max-width: 1180px; margin: 0 auto; padding: 0 16px; }
.num { font-family: var(--font-num); font-variant-numeric: tabular-nums; }
/* barra superior */
.topbar { position: sticky; top: 0; z-index: 10; background: rgba(10,16,28,.86);
  backdrop-filter: blur(8px); border-bottom: 1px solid var(--line); }
.topbar .wrap { display: flex; align-items: center; gap: 18px; height: 52px; }
.logo { font: 700 18px var(--font-head); letter-spacing: .02em; color: var(--text); text-decoration: none; }
.logo b { color: var(--amber); }
.nav { display: flex; gap: 14px; overflow-x: auto; scrollbar-width: none; margin-left: auto; }
.nav a { color: var(--text-2); text-decoration: none; font-size: 13px; white-space: nowrap; }
.nav a:hover { color: var(--amber); }
@media (max-width: 720px) { .nav { display: none; } }
/* hero */
.hero { padding: 44px 0 26px; }
.badges { display: flex; gap: 8px; flex-wrap: wrap; }
.badge { font: 600 12px var(--font-num); letter-spacing: .06em; text-transform: uppercase;
  padding: 5px 10px; border-radius: 999px; border: 1px solid var(--line); color: var(--amber);
  background: rgba(245,185,66,.08); }
.badge.q { color: var(--cyan-text); background: rgba(28,154,184,.12); }
.badge.n { color: var(--text-2); background: transparent; }
h1 { font: 700 clamp(44px, 9vw, 84px)/1 var(--font-head); margin: 18px 0 6px; letter-spacing: -.02em; }
h1 span { color: var(--amber); }
.sub { font: 500 clamp(18px, 3.2vw, 24px) var(--font-head); color: var(--text-2); margin: 0; }
.sub .arrow { color: var(--amber); }
.kpis { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-top: 28px; }
@media (max-width: 900px) { .kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
.kpi { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius);
  padding: 16px 16px 14px; position: relative; overflow: hidden; min-width: 0; }
.kpi::before { content: ""; position: absolute; inset: 0 auto 0 0; width: 3px; background: var(--amber); }
.kpi.q::before { background: var(--s-quantum); }
.kpi .lbl { font-size: 12px; color: var(--text-2); text-transform: uppercase; letter-spacing: .06em; }
.kpi .val { font: 700 clamp(28px, 5vw, 40px)/1.15 var(--font-num); margin-top: 6px; }
.kpi .val small { font-size: .45em; color: var(--text-2); font-weight: 600; margin-left: 4px; }
.kpi .foot { font-size: 12.5px; color: var(--muted); margin-top: 4px; }
.kpi .foot b { color: var(--ok); font-weight: 600; }
.disclaimer { color: var(--muted); font-size: 12.5px; margin-top: 14px; }
/* secciones */
section { padding: 30px 0 6px; }
.sec-head { display: flex; align-items: baseline; gap: 12px; margin-bottom: 14px; flex-wrap: wrap; }
.sec-head .idx { font: 600 12px var(--font-num); color: var(--amber); letter-spacing: .1em; }
h2 { font: 600 clamp(21px, 3.4vw, 27px) var(--font-head); margin: 0; }
.sec-head p { margin: 0; color: var(--text-2); font-size: 14px; flex-basis: 100%; }
.card { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius);
  padding: 18px; min-width: 0; }
.card h3 { font: 600 14px var(--font-head); margin: 0 0 12px; color: var(--text-2);
  text-transform: uppercase; letter-spacing: .07em; }
.grid2 { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
.grid3 { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }
@media (max-width: 860px) { .grid2, .grid3 { grid-template-columns: minmax(0, 1fr); } }
.chart-box { position: relative; height: 300px; }
.chart-box.tall { height: 340px; }
.legend { display: flex; flex-wrap: wrap; gap: 14px; font-size: 13px; color: var(--text-2); margin: 0 0 10px; }
.legend i { display: inline-block; width: 12px; height: 12px; border-radius: 3px; margin-right: 6px;
  vertical-align: -1px; }
.legend i.line { height: 3px; border-radius: 2px; vertical-align: 3px; width: 16px; }
.legend i.dash { height: 0; border-top: 2px dashed; background: none !important; vertical-align: 3px; width: 16px; }
/* tablas tipo tablero de salidas */
.tbl-wrap { overflow-x: auto; border-radius: 10px; border: 1px solid var(--line); }
table { border-collapse: collapse; width: 100%; font-size: 13.5px; }
th { text-align: left; font: 600 11px var(--font-ui); text-transform: uppercase; letter-spacing: .08em;
  color: var(--muted); padding: 9px 12px; background: var(--surface-2); white-space: nowrap; }
td { padding: 9px 12px; border-top: 1px solid var(--grid); white-space: nowrap; }
td.num, th.num { text-align: right; }
tr:hover td { background: rgba(255,255,255,.02); }
.board td { font-family: var(--font-num); }
.board td.hl { color: var(--amber); font-weight: 600; }
.check { color: var(--ok); font-weight: 700; }
.cross { color: var(--s-alt); font-weight: 700; }
.tag { font: 600 11px var(--font-num); padding: 2px 7px; border-radius: 6px; background: var(--surface-2);
  color: var(--text-2); border: 1px solid var(--line); }
.tag.q { color: var(--cyan-text); }
.tag.c { color: var(--amber); }
/* validación */
.valid-row { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-bottom: 14px; }
@media (max-width: 560px) { .valid-row { grid-template-columns: minmax(0, 1fr); } }
.vcell { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); padding: 14px 16px;
  display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.vcell .n { font: 600 13px var(--font-num); color: var(--text-2); }
.vcell .v { font: 700 34px var(--font-num); }
.vcell .ok { font: 600 12px var(--font-num); color: var(--ok); text-align: right; }
.vcell .ok.bad { color: var(--s-alt); }
.facts { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
.fact { font: 500 12.5px var(--font-num); color: var(--text-2); background: var(--surface-2);
  border: 1px solid var(--line); border-radius: 8px; padding: 5px 9px; }
.fact b { color: var(--text); font-weight: 600; }
/* heatmaps */
.heat { display: grid; gap: 2px; max-width: 330px; margin: 0 auto; }
.heat div { aspect-ratio: 1; border-radius: 3px; display: flex; align-items: center; justify-content: center;
  font: 600 10px var(--font-num); color: rgba(255,255,255,.0); cursor: default; }
.heat div:hover { outline: 1px solid var(--text); color: var(--text); }
.heat-axis { max-width: 330px; margin-left: auto; margin-right: auto; display: flex; justify-content: space-between; font: 11px var(--font-num); color: var(--muted); margin-top: 6px; }
/* mapa */
.map-layout { display: grid; grid-template-columns: minmax(0, 1.65fr) minmax(0, 1fr); gap: 14px; }
@media (max-width: 900px) { .map-layout { grid-template-columns: minmax(0, 1fr); } }
.seg { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
.seg button { font: 600 13px var(--font-ui); color: var(--text-2); background: var(--surface-2);
  border: 1px solid var(--line); border-radius: 10px; padding: 8px 12px; cursor: pointer; display: flex;
  gap: 8px; align-items: baseline; }
.seg button .c { font-family: var(--font-num); color: var(--muted); }
.seg button.on { color: var(--bg); background: var(--amber); border-color: var(--amber); }
.seg button.on .c { color: rgba(10,16,28,.75); }
.seg button:focus-visible { outline: 2px solid var(--cyan-text); outline-offset: 2px; }
#map svg { width: 100%; height: auto; display: block; }
#map .edge { fill: none; stroke: var(--amber); stroke-linecap: round; transition: d .7s ease, stroke-opacity .7s ease, stroke-width .7s ease; }
#map .edge:hover { stroke: var(--cyan-text); stroke-opacity: 1 !important; }
#map .gate circle { fill: var(--surface-2); stroke: var(--line); stroke-width: 2; }
#map .gate .g { font: 600 13px var(--font-num); fill: var(--muted); text-anchor: middle; }
#map .gate .f { font: 700 17px var(--font-num); fill: var(--amber); text-anchor: middle; dominant-baseline: central; transition: opacity .3s; }
.costbig { display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap; margin-bottom: 10px; }
.costbig .v { font: 700 46px/1 var(--font-num); color: var(--amber); }
.costbig .l { color: var(--text-2); font-size: 13px; }
.costbig .g { font: 600 14px var(--font-num); color: var(--text-2); }
.map-note { color: var(--muted); font-size: 12.5px; margin-top: 8px; }
/* qiskit vs clásico */
.split { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; margin-top: 14px; }
@media (max-width: 700px) { .split { grid-template-columns: minmax(0, 1fr); } }
.split ul { margin: 0; padding-left: 18px; color: var(--text-2); font-size: 13.5px; }
.split li { margin: 3px 0; }
.split .card.q { border-color: rgba(28,154,184,.5); }
.split .card.q h3 { color: var(--cyan-text); }
.split .card.c h3 { color: var(--amber); }
/* semillas */
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip { font: 600 13px var(--font-num); padding: 5px 9px; border-radius: 8px; background: var(--surface-2);
  border: 1px solid var(--line); color: var(--text-2); }
.chip.hit { color: var(--ok); border-color: rgba(62,207,142,.45); }
.stats { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin-bottom: 12px; }
@media (max-width: 560px) { .stats { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
.stat .l { font-size: 11.5px; color: var(--muted); text-transform: uppercase; letter-spacing: .06em; }
.stat .v { font: 700 24px var(--font-num); }
.limits { margin: 0; padding-left: 18px; color: var(--text-2); }
.limits li { margin: 5px 0; }
.chips.v .chip b { color: var(--text); }
footer { padding: 34px 0 50px; color: var(--muted); font-size: 12.5px; border-top: 1px solid var(--line); margin-top: 34px; }
.hidden { display: none !important; }
.msg { color: var(--muted); font-size: 13px; }
</style>
</head>
<body>
<script id="data" type="application/json">__DATA__</script>

<div class="topbar"><div class="wrap">
  <a class="logo" href="#top">Q<b>Gate</b></a>
  <nav class="nav">
    <a href="#datos">Datos</a><a href="#mapa">Mapa</a><a href="#qaoa">QAOA</a><a href="#lambda">λ</a>
    <a href="#hibrido">Híbrido</a><a href="#escala">Escala</a><a href="#repro">Reproducir</a>
    <a href="https://github.com/iamjosels/qgate-qap10">GitHub</a>
  </nav>
</div></div>

<main class="wrap" id="top">
  <header class="hero">
    <div class="badges">
      <span class="badge">Track A · Aeropuerto</span>
      <span class="badge q" id="b-qiskit">Qiskit</span>
      <span class="badge n">MIPLIB qap10</span>
    </div>
    <h1>Q<span>Gate</span></h1>
    <p class="sub">Vuelos <span class="arrow">→</span> puertas con QAOA híbrido</p>
    <div class="kpis" id="kpis"></div>
    <p class="disclaimer">Datos: benchmark qap10. Pasajeros y distancias son supuestos de negocio. Todo lo cuántico corre en simulador (Qiskit Aer).</p>
  </header>

  <section id="datos">
    <div class="sec-head"><span class="idx">01</span><h2>Datos validados</h2>
      <p>MPS linealizado → flujos F y distancias D. Escala verificada con los óptimos de control.</p></div>
    <div class="valid-row" id="valid"></div>
    <div class="grid2">
      <div class="card"><h3>F · pasajeros en conexión</h3><div class="heat" id="heatF"></div>
        <div class="heat-axis"><span>vuelo 1</span><span>vuelo N</span></div></div>
      <div class="card"><h3>D · distancia entre puertas</h3><div class="heat" id="heatD"></div>
        <div class="heat-axis"><span>puerta 1</span><span>puerta N</span></div></div>
    </div>
    <div class="facts" id="facts"></div>
  </section>

  <section id="mapa">
    <div class="sec-head"><span class="idx">02</span><h2>Mapa de puertas</h2>
      <p>Grosor = pasajeros que conectan. Brillo = costo del par (flujo × distancia). Mejor asignación: líneas gruesas más cortas.</p></div>
    <div class="seg" id="assignBtns" role="tablist" aria-label="Asignación"></div>
    <div class="map-layout">
      <div class="card" id="map"></div>
      <div class="card">
        <div class="costbig"><span class="v num" id="mapCost">-</span><span class="l">costo C<br>(cada par una vez)</span></div>
        <div class="costbig"><span class="g" id="mapGap"></span></div>
        <div class="tbl-wrap"><table class="board"><thead><tr><th>Vuelo</th><th>Puerta</th><th class="num">Pasajeros</th><th class="num">Pax × dist</th></tr></thead>
          <tbody id="boardBody"></tbody></table></div>
        <p class="map-note">Pax × dist suma las conexiones de cada vuelo (cada par aparece en sus dos vuelos: la columna suma 2C). Posiciones de puertas por MDS clásico sobre D (proyección visual).</p>
      </div>
    </div>
  </section>

  <section id="qaoa">
    <div class="sec-head"><span class="idx">03</span><h2>QAOA vs azar</h2>
      <p>Probabilidad de muestrear una asignación válida (escala log). Mixer X: todo penalizado. Mixer XY + estado W: filas válidas por construcción.</p></div>
    <div class="card">
      <div class="legend"><span><i style="background:var(--s-quantum)"></i>QAOA (ideal)</span>
        <span><i style="background:var(--s-quantum-2)"></i>QAOA (muestras)</span>
        <span><i style="background:var(--s-ref)"></i>Azar uniforme</span></div>
      <div class="chart-box tall"><canvas id="cQaoa" aria-label="P(válida) QAOA vs azar"></canvas></div>
    </div>
    <div class="tbl-wrap" style="margin-top:14px"><table><thead><tr>
      <th>Experimento</th><th class="num">N</th><th class="num">Qubits</th><th>Mixer</th><th class="num">p</th><th>Ruido</th>
      <th class="num">P(válida)</th><th class="num">Muestras válidas</th><th class="num">Azar</th><th class="num">P(óptimo)</th>
      <th class="num">Mejor costo</th><th class="num">Ratio medio</th><th class="num">Tiempo s</th><th class="num">CX</th><th class="num">Prof.</th>
    </tr></thead><tbody id="qaoaBody"></tbody></table></div>
    <div class="split">
      <div class="card q"><h3>Qiskit hace</h3><ul>
        <li>Circuito QAOA parametrizado (costo Ising + mixer)</li>
        <li>Estado W por fila y mixer XY que conserva filas válidas</li>
        <li>Simulación statevector y muestreo con shots (Aer)</li>
        <li>Modelo de ruido despolarizante</li>
        <li>Transpilación: profundidad y número de CX</li>
        <li>Cada subproblema de 9 qubits del híbrido (QAOA p=2)</li></ul></div>
      <div class="card c"><h3>Clásico hace</h3><ul>
        <li>Leer el MPS y reconstruir F y D</li>
        <li>QUBO, λ y paso a Ising</li>
        <li>COBYLA ajusta los ángulos (CVaR)</li>
        <li>Elegir vecindarios y aceptar movimientos (LNS)</li>
        <li>Referencias: fuerza bruta, SA, cota Gilmore-Lawler</li></ul></div>
    </div>
  </section>

  <section id="lambda">
    <div class="sec-head"><span class="idx">04</span><h2>Barrido de λ</h2>
      <p>λ chico deja ganar inválidas; λ grande aplana el paisaje. λ0 = mayor aporte posible de una asignación.</p></div>
    <div class="card">
      <div class="legend"><span><i class="line" style="background:var(--s-quantum)"></i>XY</span>
        <span><i class="line" style="background:var(--s-sa)"></i>X</span>
        <span><i class="line" style="background:var(--text-2)"></i>P(válida)</span>
        <span><i class="dash" style="border-color:var(--text-2)"></i>P(óptimo)</span></div>
      <div class="chart-box"><canvas id="cLambda" aria-label="Barrido de lambda"></canvas></div>
    </div>
  </section>

  <section id="hibrido">
    <div class="sec-head"><span class="idx">05</span><h2>Híbrido QGate</h2>
      <p>Subproblemas de 3 vuelos (9 qubits) resueltos con QAOA dentro de una búsqueda clásica por vecindarios. Controles con el mismo presupuesto, semilla y arranque: solver exacto y muestreo al azar.</p></div>
    <div class="grid3" id="hybStats" style="margin-bottom:14px"></div>
    <div class="card">
      <div class="seg" id="hybAxis"><button class="on" data-ax="iter">Iteración</button><button data-ax="t">Tiempo (s)</button></div>
      <div class="legend" id="hybLegend"></div>
      <div class="chart-box tall"><canvas id="cHyb" aria-label="Convergencia del híbrido"></canvas></div>
    </div>
    <div class="tbl-wrap" id="ablWrap" style="margin-top:14px"><table><thead><tr><th>Solver del subproblema</th><th class="num">Shots</th>
      <th class="num">Costo final</th><th class="num">Gap %</th><th class="num">Éxito subproblema</th><th class="num">P(óptimo) medio</th>
      <th class="num">Azar P(óptimo)</th><th class="num">Tiempo s</th></tr></thead><tbody id="ablBody"></tbody></table></div>
    <p class="map-note">Ablación con mismas iteraciones, semilla y arranque. Con 512 shots el azar también encuentra el óptimo de 3 vuelos (6 asignaciones); con 8 shots se ve cuánto concentra QAOA.</p>
    <div class="card" id="seedsCard" style="margin-top:14px"><h3>Robustez · solver exacto en varias semillas</h3>
      <div class="stats" id="seedStats"></div><div class="chips" id="seedChips"></div></div>
  </section>

  <section id="escala">
    <div class="sec-head"><span class="idx">06</span><h2>Escalabilidad</h2>
      <p>Qubits constantes (9) aunque N crezca. Sin óptimo conocido en N > 10: se mide contra la cota Gilmore-Lawler. * = instancia sintética.</p></div>
    <div class="grid2">
      <div class="card"><h3>Gap vs cota inferior (%)</h3><div class="legend" id="scLegend"></div>
        <div class="chart-box"><canvas id="cScaleGap"></canvas></div></div>
      <div class="card"><h3>Tiempo (s, log)</h3><div class="legend" id="scLegend2"></div>
        <div class="chart-box"><canvas id="cScaleT"></canvas></div></div>
    </div>
    <div style="margin-top:14px">
      <div class="tbl-wrap"><table><thead><tr><th>N</th><th>Instancia</th><th>Método</th><th class="num">Costo</th>
        <th class="num">Cota</th><th class="num">Gap cota</th><th class="num">Gap 340</th><th class="num">Tiempo s</th><th class="num">Mem MB</th><th class="num">Qubits</th></tr></thead>
        <tbody id="scaleBody"></tbody></table></div>
      <div class="card" style="margin-top:14px;max-width:520px"><h3>Muro de memoria · statevector</h3>
        <div class="tbl-wrap"><table><thead><tr><th class="num">N</th><th class="num">Qubits N²</th><th class="num">Memoria</th></tr></thead>
        <tbody id="memBody"></tbody></table></div>
        <p class="map-note">QGate usa siempre subproblemas de 9 qubits: memoria constante.</p></div>
    </div>
  </section>

  <section id="repro">
    <div class="sec-head"><span class="idx">07</span><h2>Reproducibilidad y límites</h2></div>
    <div class="grid2">
      <div class="card"><h3>Entorno</h3><div class="chips v" id="versions"></div>
        <pre class="num" id="cmd" style="white-space:pre-wrap;color:var(--text-2);font-size:12.5px;margin:14px 0 0"></pre></div>
      <div class="card"><h3>Limitaciones</h3><ul class="limits" id="limits"></ul></div>
    </div>
  </section>
</main>

<footer><div class="wrap">
  QGate · IBM Quantum Hackathon 2026 · Reto NTT DATA QAP10 · <a href="https://github.com/iamjosels/qgate-qap10">código en GitHub</a>.
  Librerías: Qiskit, Qiskit Aer, NumPy, SciPy, Matplotlib, Chart.js. Datos: MIPLIB 2017, instancia qap10.
  <span id="gen"></span>
</div></footer>

<script>
(function () {
  "use strict";
  const R = JSON.parse(document.getElementById("data").textContent);
  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const C = { q: css("--s-quantum"), q2: css("--s-quantum-2"), c: css("--s-classic"), sa: css("--s-sa"),
              alt: css("--s-alt"), ref: css("--s-ref"), text: css("--text"), text2: css("--text-2"),
              muted: css("--muted"), grid: css("--grid"), amber: css("--amber"), surface: css("--surface") };
  const $ = (id) => document.getElementById(id);
  const hide = (id) => { const el = $(id); if (el) el.classList.add("hidden"); };
  const has = (a) => Array.isArray(a) && a.length > 0;
  const f = (v, d = 0) => (v === null || v === undefined || Number.isNaN(v)) ? "-" : Number(v).toFixed(d);
  const fp = (v) => (v === null || v === undefined) ? "-" : (v >= 0.1 ? v.toFixed(3) : v.toPrecision(2));
  const esc = (s) => String(s).replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));
  const meta = R.meta || {}, data = R.data || {};
  const REF = meta.reference_optimum;
  const gap = (c) => (REF && c !== null && c !== undefined) ? 100 * (c - REF) / REF : null;
  const N = meta.N;

  if (window.Chart) {
    Chart.defaults.color = C.text2;
    Chart.defaults.font.family = "Inter, system-ui, sans-serif";
    Chart.defaults.font.size = 12;
    Chart.defaults.borderColor = C.grid;
    Chart.defaults.plugins.legend.display = false;
    Chart.defaults.plugins.tooltip.backgroundColor = "#0a101c";
    Chart.defaults.plugins.tooltip.borderColor = "#24324d";
    Chart.defaults.plugins.tooltip.borderWidth = 1;
    Chart.defaults.plugins.tooltip.titleFont = { family: "JetBrains Mono", weight: "600" };
    Chart.defaults.plugins.tooltip.bodyFont = { family: "JetBrains Mono" };
    Chart.defaults.maintainAspectRatio = false;
  }
  const v = meta.versions || {};
  if (v.qiskit) $("b-qiskit").textContent = "Qiskit " + v.qiskit + (v.qiskit_aer ? " · Aer " + v.qiskit_aer : "");

  // ------------------------------------------------------------------ KPIs
  const hyb = (R.hybrid || []);
  const hq = hyb.find((h) => h.method === "qgate_lns_qaoa");
  const he = hyb.find((h) => h.method === "qgate_lns_exact");
  const bf = (R.classical || []).find((c) => c.method === "brute_force");
  const q4 = (R.quantum || []).filter((q) => q.N === 4 && q.noise === "none");
  const kp = [];
  const best = R.best_assignment || (hq ? { cost: hq.final_cost } : null);
  if (best) {
    const g = gap(best.cost);
    const pol = hq && hq.polished_cost !== undefined && hq.polished_cost < hq.final_cost
      ? ` · pulido ${f(hq.polished_cost)}` : "";
    kp.push(`<div class="kpi q"><div class="lbl">QGate híbrido</div><div class="val num">${f(best.cost)}</div>
      <div class="foot">${g === null ? "" : (g <= 1e-9 ? "<b>gap 0 %</b> vs 340" : "gap " + f(g, 1) + " % vs " + f(REF))}${pol}</div></div>`);
  }
  if (bf) kp.push(`<div class="kpi"><div class="lbl">Óptimo exacto</div><div class="val num">${f(bf.cost)}</div>
      <div class="foot">fuerza bruta ${N}! en ${f(bf.time_s, 1)} s</div></div>`);
  if (q4.length) {
    const qb = q4.reduce((a, b) => ((b.mean_approx_ratio || 0) > (a.mean_approx_ratio || 0) ? b : a));
    kp.push(`<div class="kpi q"><div class="lbl">QAOA N=4 · ${esc(qb.mixer.toUpperCase())}</div>
      <div class="val num">${f(qb.mean_approx_ratio, 2)}<small>ratio</small></div>
      <div class="foot">P(válida) ${fp(qb.p_feasible)} vs azar ${fp(qb.random_feasible_baseline)}</div></div>`);
  }
  kp.push(`<div class="kpi q"><div class="lbl">Qubits por subproblema</div><div class="val num">${meta.qubits_per_subproblem || 9}</div>
      <div class="foot">QUBO completo N=${N}: ${N * N} qubits</div></div>`);
  $("kpis").innerHTML = kp.join("");

  // ------------------------------------------------------------- validación
  if (has(R.validation)) {
    $("valid").innerHTML = R.validation.map((r) => `<div class="vcell"><div><div class="n">N = ${r.n}</div>
      <div class="v num">${f(r.optimum)}</div></div><div class="ok ${r.ok === false ? "bad" : ""}">${r.ok === false ? "✗" : (r.ok ? "✓" : "")}
      ${r.expected !== null && r.expected !== undefined ? "esperado " + f(r.expected) : ""}<br>${f(r.time_s, r.time_s < 1 ? 3 : 1)} s</div></div>`).join("");
  } else hide("valid");
  function heat(id, M, color) {
    const el = $(id);
    if (!has(M)) { el.closest(".card").classList.add("hidden"); return; }
    const n = M.length, mx = Math.max(...M.flat()) || 1;
    el.style.gridTemplateColumns = `repeat(${n}, minmax(0, 1fr))`;
    el.innerHTML = M.map((row, i) => row.map((x, j) => {
      const a = x / mx;
      const bg = x === 0 ? "#141e31" : `color-mix(in oklab, ${color} ${Math.round(15 + 85 * a)}%, #141e31)`;
      return `<div style="background:${bg}" title="${i + 1}, ${j + 1}: ${x}">${x}</div>`;
    }).join("")).join("");
  }
  heat("heatF", data.F, C.c);
  heat("heatD", data.D, C.q);
  const mr = data.mps_report || {};
  const facts = [];
  if (mr.n_cols) facts.push(`<span class="fact">variables <b>${mr.n_cols}</b> = ${mr.n_x} x + ${mr.n_y} y</span>`);
  if (mr.n_rows) facts.push(`<span class="fact">restricciones <b>${mr.n_rows}</b></span>`);
  if (mr.y_mapped !== undefined) facts.push(`<span class="fact">y mapeadas <b>${mr.y_mapped}/${mr.y_expected}</b></span>`);
  if (data.factorization_residual !== null && data.factorization_residual !== undefined)
    facts.push(`<span class="fact">residuo SVD F·D <b>${data.factorization_residual}</b></span>`);
  if (data.index_strategy) facts.push(`<span class="fact">índices <b>${esc(data.index_strategy)}</b></span>`);
  if (has(data.index_candidates)) facts.push(`<span class="fact">candidatas que dan 24/32 <b>${data.index_candidates.filter((c) => c.match).length}/${data.index_candidates.length}</b></span>`);
  facts.push(`<span class="fact">convención <b>cada par una vez</b></span>`);
  $("facts").innerHTML = facts.join("");

  // ------------------------------------------------------------------ mapa
  (function map() {
    const xy = data.gate_xy, F = data.F, D = data.D, A = R.assignments || [];
    if (!has(xy) || !has(F) || !has(D) || !has(A)) { hide("mapa"); return; }
    const n = xy.length, W = 1000, H = 600, pad = 70;
    const xs = xy.map((p) => p[0]), ys = xy.map((p) => p[1]);
    const minx = Math.min(...xs), maxx = Math.max(...xs), miny = Math.min(...ys), maxy = Math.max(...ys);
    const sc = Math.min((W - 2 * pad) / ((maxx - minx) || 1), (H - 2 * pad) / ((maxy - miny) || 1));
    const ox = (W - sc * (maxx - minx)) / 2, oy = (H - sc * (maxy - miny)) / 2;
    const P = xy.map((p) => [ox + sc * (p[0] - minx), oy + sc * (p[1] - miny)]);
    const Fmax = Math.max(...F.flat()) || 1;
    const pairs = [];
    for (let i = 0; i < n; i++) for (let k = i + 1; k < n; k++) if (F[i][k] > 0) pairs.push([i, k]);
    let cmax = 1;
    A.forEach((a) => pairs.forEach(([i, k]) => { cmax = Math.max(cmax, F[i][k] * D[a.perm[i]][a.perm[k]]); }));
    const curve = (a, b) => {
      const [x1, y1] = P[a], [x2, y2] = P[b];
      const mx = (x1 + x2) / 2, my = (y1 + y2) / 2, dx = x2 - x1, dy = y2 - y1;
      const cx = mx - dy * 0.18, cy = my + dx * 0.18;
      return `M ${x1.toFixed(1)} ${y1.toFixed(1)} Q ${cx.toFixed(1)} ${cy.toFixed(1)} ${x2.toFixed(1)} ${y2.toFixed(1)}`;
    };
    let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Mapa de puertas y conexiones">`;
    pairs.forEach(([i, k]) => {
      svg += `<path class="edge" id="e${i}_${k}" stroke-width="${(1 + 9 * F[i][k] / Fmax).toFixed(2)}"><title></title></path>`;
    });
    P.forEach((p, j) => {
      svg += `<g class="gate"><circle cx="${p[0].toFixed(1)}" cy="${p[1].toFixed(1)}" r="27"></circle>
        <text class="g" x="${p[0].toFixed(1)}" y="${(p[1] - 36).toFixed(1)}">P${j + 1}</text>
        <text class="f" id="gf${j}" x="${p[0].toFixed(1)}" y="${p[1].toFixed(1)}"></text></g>`;
    });
    $("map").innerHTML = svg + "</svg>";
    function show(idx) {
      const a = A[idx], perm = a.perm;
      pairs.forEach(([i, k]) => {
        const e = $(`e${i}_${k}`), c = F[i][k] * D[perm[i]][perm[k]];
        const d = curve(perm[i], perm[k]);
        e.style.d = `path("${d}")`;
        e.setAttribute("d", d);
        e.style.strokeOpacity = (0.12 + 0.85 * c / cmax).toFixed(3);
        e.querySelector("title").textContent = `V${i + 1} ↔ V${k + 1} · ${F[i][k]} pasajeros × distancia ${D[perm[i]][perm[k]]} = ${c}`;
      });
      const inv = new Array(n);
      perm.forEach((g, i) => { inv[g] = i; });
      inv.forEach((i, g) => { $(`gf${g}`).textContent = "V" + (i + 1); });
      $("mapCost").textContent = f(a.cost);
      const g = gap(a.cost);
      $("mapGap").textContent = g === null ? a.label : `gap ${f(g, 1)} % vs óptimo ${f(REF)}`;
      $("boardBody").innerHTML = perm.map((g2, i) => {
        let flow = 0, cost = 0;
        for (let k = 0; k < n; k++) if (k !== i) { flow += F[Math.min(i, k)][Math.max(i, k)]; cost += F[Math.min(i, k)][Math.max(i, k)] * D[g2][perm[k]]; }
        return `<tr><td class="hl">V${i + 1}</td><td>P${g2 + 1}</td><td class="num">${flow}</td><td class="num">${cost}</td></tr>`;
      }).join("");
      document.querySelectorAll("#assignBtns button").forEach((b, j) => {
        b.classList.toggle("on", j === idx); b.setAttribute("aria-selected", j === idx);
      });
    }
    $("assignBtns").innerHTML = A.map((a) => `<button role="tab"><span>${esc(a.label)}</span><span class="c">${f(a.cost)}</span></button>`).join("");
    document.querySelectorAll("#assignBtns button").forEach((b, j) => b.addEventListener("click", () => show(j)));
    const start = A.findIndex((a) => a.label === "Aleatoria");
    show(start >= 0 ? start : 0);
    const target = A.findIndex((a) => a.label === "QGate híbrido");
    if (target >= 0 && target !== start) setTimeout(() => show(target), 900);
  })();

  // ------------------------------------------------------------------ QAOA
  (function qaoa() {
    const Q = R.quantum || [];
    if (!has(Q)) { hide("qaoa"); return; }
    if (window.Chart) new Chart($("cQaoa"), {
      type: "bar",
      data: { labels: Q.map((q) => q.id), datasets: [
        { label: "QAOA (ideal)", data: Q.map((q) => q.p_feasible), backgroundColor: C.q, borderRadius: 4, borderSkipped: "start" },
        { label: "QAOA (muestras)", data: Q.map((q) => q.feasible_fraction_shots), backgroundColor: C.q2, borderRadius: 4, borderSkipped: "start" },
        { label: "Azar", data: Q.map((q) => q.random_feasible_baseline), backgroundColor: C.ref, borderRadius: 4, borderSkipped: "start" }] },
      options: { datasets: { bar: { categoryPercentage: 0.72, barPercentage: 0.9 } },
        scales: { y: { type: "logarithmic", min: 1e-4, max: 1, title: { display: true, text: "P(válida)" },
                       ticks: { callback: (val) => [1, 0.1, 0.01, 0.001, 0.0001].includes(val) ? val : "" } },
                  x: { grid: { display: false }, ticks: { font: { family: "JetBrains Mono", size: 11 } } } },
        plugins: { tooltip: { mode: "index", intersect: false,
          callbacks: { label: (c) => `${c.dataset.label}: ${fp(c.parsed.y)}` } } } } });
    $("qaoaBody").innerHTML = Q.map((q) => `<tr><td><span class="tag q">${esc(q.id)}</span></td><td class="num">${q.N}</td><td class="num">${q.qubits}</td>
      <td>${esc(q.mixer.toUpperCase())}</td><td class="num">${q.p}</td><td>${q.noise === "none" ? "-" : esc(q.noise.replace("depolarizing ", "desp. "))}</td>
      <td class="num">${fp(q.p_feasible)}</td><td class="num">${fp(q.feasible_fraction_shots)}</td><td class="num">${fp(q.random_feasible_baseline)}</td>
      <td class="num">${fp(q.p_optimal)}</td><td class="num">${f(q.best_feasible_cost)}</td><td class="num">${f(q.mean_approx_ratio, 3)}</td>
      <td class="num">${f(q.time_s, 1)}</td><td class="num">${q.cx_count ?? "-"}</td><td class="num">${q.depth ?? "-"}</td></tr>`).join("");
  })();

  // ---------------------------------------------------------------- lambda
  (function lam() {
    const L = R.lambda_sweep || [];
    if (!has(L) || !window.Chart) { hide("lambda"); return; }
    const facs = [...new Set(L.map((r) => r.lam_factor))].sort((a, b) => a - b);
    const ds = [];
    [["xy", C.q], ["x", C.sa]].forEach(([m, col]) => {
      const rows = facs.map((fc) => L.find((r) => r.mixer === m && r.lam_factor === fc));
      if (!rows.some(Boolean)) return;
      ds.push({ label: `${m.toUpperCase()} · P(válida)`, data: rows.map((r) => r ? r.p_feasible : null), borderColor: col, backgroundColor: col, borderWidth: 2, pointRadius: 4 });
      ds.push({ label: `${m.toUpperCase()} · P(óptimo)`, data: rows.map((r) => r ? r.p_optimal : null), borderColor: col, backgroundColor: col, borderWidth: 2, borderDash: [6, 4], pointRadius: 4 });
    });
    new Chart($("cLambda"), { type: "line", data: { labels: facs.map((x) => "λ0×" + x), datasets: ds },
      options: { interaction: { mode: "index", intersect: false },
        scales: { y: { min: 0, max: 1, title: { display: true, text: "probabilidad" } }, x: { grid: { display: false } } },
        plugins: { tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${fp(c.parsed.y)}` } } } } });
  })();

  // --------------------------------------------------------------- híbrido
  (function hybrid() {
    const Hs = (R.hybrid || []).filter((h) => has(h.history) && h.method.startsWith("qgate_lns"));
    if (!has(Hs)) { hide("hibrido"); return; }
    const STY = { qgate_lns_qaoa: [C.q, 4, []], qgate_lns_exact: [C.c, 2, [6, 4]], qgate_lns_random: [C.ref, 2, [2, 3]],
                  qgate_lns_qaoa_s8: [C.q2, 2, []], qgate_lns_random_s8: [C.alt, 2, []] };
    const colOf = (h) => (STY[h.method] || [C.sa])[0];
    const st = [];
    if (hq) st.push(`<div class="card"><h3>QGate · QAOA</h3><div class="stat"><div class="v num" style="color:var(--cyan-text)">${f(hq.final_cost)}</div>
      <div class="l">${hq.start_cost !== undefined ? "desde " + f(hq.start_cost) + " · " : ""}${hq.iters} iter · ${f(hq.time_s, 1)} s</div></div>
      <div class="facts"><span class="fact">P(óptimo) por subproblema <b>${fp(hq.qaoa_p_optimal_mean)}</b> vs azar ${fp(hq.random_p_optimal_mean)}</span>
      <span class="fact">éxito con ${hq.shots} shots <b>${f(100 * hq.sub_success_rate, 0)} %</b></span>${hq.polished_cost !== undefined ? `<span class="fact">pulido 2-swap <b>${f(hq.polished_cost)}</b></span>` : ""}</div></div>`);
    if (he) st.push(`<div class="card"><h3>Control · subproblema exacto</h3><div class="stat"><div class="v num" style="color:var(--amber)">${f(he.final_cost)}</div>
      <div class="l">${he.iters} iter · ${f(he.time_s, 2)} s</div></div>
      <div class="facts"><span class="fact">mismo marco, k! = 6 permutaciones</span>${he.polished_cost !== undefined ? `<span class="fact">pulido 2-swap <b>${f(he.polished_cost)}</b></span>` : ""}</div></div>`);
    const sa = (R.hybrid || []).find((h) => h.method === "simulated_annealing");
    if (sa) st.push(`<div class="card"><h3>Simulated annealing</h3><div class="stat"><div class="v num" style="color:var(--s-sa)">${f(sa.final_cost)}</div>
      <div class="l">${f(sa.time_s, 1)} s · clásico puro</div></div>
      <div class="facts"><span class="fact">gap <b>${f(sa.gap_pct, 1)} %</b></span></div></div>`);
    $("hybStats").innerHTML = st.join("");
    $("hybLegend").innerHTML = Hs.map((h) => `<span data-m="${h.method}"><i class="${(STY[h.method] || [0, 0, []])[2].length ? "dash" : "line"}" style="background:${colOf(h)};border-color:${colOf(h)}"></i>${esc(h.label)}</span>`).join("")
      + (REF ? `<span><i class="dash" style="border-color:${C.text2}"></i>óptimo ${f(REF)}</span>` : "");
    let chart = null;
    function draw(ax) {
      const use = Hs;
      const ds = use.map((h) => ({ label: h.label, data: h.history.map((p, i) => ({ x: ax === "iter" ? (p.iter ?? i) : Math.max(p.t, 1e-3), y: p.best })),
        borderColor: colOf(h), backgroundColor: colOf(h), borderWidth: (STY[h.method] || [0, 2])[1], borderDash: (STY[h.method] || [0, 0, []])[2],
        pointRadius: 0, stepped: true }));
      if (REF) {
        const xmax = Math.max(...ds.flatMap((d) => d.data.map((p) => p.x)));
        ds.push({ label: "Óptimo (solo referencia)", data: [{ x: ax === "iter" ? 0 : 1e-3, y: REF }, { x: xmax, y: REF }], borderColor: C.text2, borderDash: [6, 5], borderWidth: 1.5, pointRadius: 0 });
      }
      if (chart) chart.destroy();
      chart = new Chart($("cHyb"), { type: "line", data: { datasets: ds },
        options: { parsing: true, interaction: { mode: "nearest", axis: "x", intersect: false },
          scales: { x: { type: ax === "t" ? "logarithmic" : "linear", title: { display: true, text: ax === "iter" ? "iteración" : "tiempo (s, log)" } },
                    y: { title: { display: true, text: "mejor costo" } } },
          plugins: { tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${f(c.parsed.y)}` } } } } });
    }
    if (window.Chart) draw("iter");
    document.querySelectorAll("#hybAxis button").forEach((b) => b.addEventListener("click", () => {
      document.querySelectorAll("#hybAxis button").forEach((x) => x.classList.toggle("on", x === b)); draw(b.dataset.ax);
    }));
    $("ablBody").innerHTML = Hs.map((h) => `<tr><td><span class="tag ${h.solver === "qaoa" ? "q" : "c"}">${esc(h.label)}</span></td>
      <td class="num">${h.shots ?? "-"}</td><td class="num">${f(h.final_cost)}</td><td class="num">${f(h.gap_pct, 1)}</td>
      <td class="num">${h.sub_success_rate === undefined ? "-" : f(100 * h.sub_success_rate, 0) + " %"}</td>
      <td class="num">${h.solver === "qaoa" ? fp(h.qaoa_p_optimal_mean) : h.solver === "random" ? fp(h.random_p_optimal_mean) : "1"}</td>
      <td class="num">${fp(h.random_p_optimal_mean)}</td><td class="num">${f(h.time_s, 1)}</td></tr>`).join("");
    const S = R.hybrid_seeds;
    if (!S || !has(S.final_costs)) { hide("seedsCard"); return; }
    $("seedStats").innerHTML = [["media", f(S.mean, 1)], ["mejor", f(S.best)], ["peor", f(S.worst)],
      ["llega a " + f(REF), S.hits_ref === null ? "-" : `${S.hits_ref}/${S.final_costs.length}`]]
      .map(([l, val]) => `<div class="stat"><div class="l">${l}</div><div class="v num">${val}</div></div>`).join("");
    $("seedChips").innerHTML = S.final_costs.map((c, i) => `<span class="chip ${REF && Math.abs(c - REF) < 1e-6 ? "hit" : ""}" title="semilla ${S.seeds[i]}">s${S.seeds[i]} · ${f(c)}</span>`).join("")
      + `<span class="chip">${S.iters} iteraciones c/u</span>`;
  })();

  // ---------------------------------------------------------- escalabilidad
  (function scale() {
    const S = R.scaling || [];
    if (!has(S)) { hide("escala"); return; }
    const realName = meta.instance;
    const Ns = [...new Set(S.map((r) => r.N))].sort((a, b) => a - b);
    const lab = (n) => { const r = S.find((x) => x.N === n); return "N=" + n + (r && r.instance !== realName ? "*" : ""); };
    const meths = [...new Set(S.map((r) => r.method))];
    const nameOf = { simulated_annealing: "SA", qgate_lns_exact: "QGate exacto", qgate_lns_qaoa: "QGate QAOA" };
    const colOf = { simulated_annealing: C.sa, qgate_lns_exact: C.c, qgate_lns_qaoa: C.q };
    const leg = meths.map((m) => `<span><i class="line" style="background:${colOf[m] || C.ref}"></i>${nameOf[m] || m}</span>`).join("");
    $("scLegend").innerHTML = leg; $("scLegend2").innerHTML = leg;
    const mk = (key) => meths.map((m) => ({ label: nameOf[m] || m, data: Ns.map((n) => { const r = S.find((x) => x.N === n && x.method === m); return r ? r[key] : null; }),
      borderColor: colOf[m] || C.ref, backgroundColor: colOf[m] || C.ref, borderWidth: 2, pointRadius: 5 }));
    if (window.Chart) {
      new Chart($("cScaleGap"), { type: "line", data: { labels: Ns.map(lab), datasets: mk("gap_vs_bound_pct") },
        options: { interaction: { mode: "index", intersect: false }, scales: { y: { min: 0, title: { display: true, text: "% sobre la cota" } }, x: { grid: { display: false } } },
          plugins: { tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${f(c.parsed.y, 1)} %` } } } } });
      new Chart($("cScaleT"), { type: "line", data: { labels: Ns.map(lab), datasets: mk("time_s") },
        options: { interaction: { mode: "index", intersect: false }, scales: { y: { type: "logarithmic", title: { display: true, text: "segundos" },
          ticks: { callback: (val) => [0.01, 0.1, 1, 10, 100, 1000].includes(val) ? String(val) : "" } }, x: { grid: { display: false } } },
          plugins: { tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${f(c.parsed.y, 2)} s` } } } } });
    }
    $("scaleBody").innerHTML = S.map((r) => `<tr><td class="num">${r.N}</td><td>${esc(r.instance)}${r.instance !== realName ? " *" : ""}</td>
      <td><span class="tag ${r.method.includes("qaoa") ? "q" : "c"}">${nameOf[r.method] || esc(r.method)}</span></td><td class="num">${f(r.best_cost)}</td>
      <td class="num">${f(r.lower_bound)}</td><td class="num">${f(r.gap_vs_bound_pct, 1)}</td><td class="num">${r.gap_vs_opt_pct === null ? "-" : f(r.gap_vs_opt_pct, 1)}</td>
      <td class="num">${f(r.time_s, 2)}</td><td class="num">${f(r.peak_mem_mb, 1)}</td><td class="num">${r.qubits}</td></tr>`).join("");
    const M = meta.statevector_memory || [];
    const hb = (b) => { const u = ["B", "KiB", "MiB", "GiB", "TiB"]; let i = 0; while (b >= 1024 && i < u.length - 1) { b /= 1024; i++; }
      return i < u.length - 1 || b < 1024 ? `${b % 1 ? b.toFixed(1) : b} ${u[i]}` : `${(b * 1024 ** i).toExponential(2)} B`; };
    if (has(M)) $("memBody").innerHTML = M.map((m) => `<tr><td class="num">${m.N}</td><td class="num">${m.qubits}</td>
      <td class="num">${m.bytes > 1024 ** 5 ? m.bytes.toExponential(2) + " B" : hb(m.bytes)}</td></tr>`).join("");
    else $("memBody").closest(".card").classList.add("hidden");
  })();

  // ------------------------------------------------------- reproducibilidad
  (function repro() {
    const vv = Object.entries(v).map(([k, val]) => `<span class="chip">${esc(k)} <b>${esc(val)}</b></span>`);
    if (meta.seed !== undefined) vv.push(`<span class="chip">semilla <b>${meta.seed}</b></span>`);
    if (meta.generated_at) vv.push(`<span class="chip">fecha <b>${esc(meta.generated_at)}</b></span>`);
    if (meta.total_time_s) vv.push(`<span class="chip">corrida <b>${f(meta.total_time_s / 60, 1)} min</b></span>`);
    $("versions").innerHTML = vv.join("");
    const a = meta.args || {};
    $("cmd").textContent = a.mps ? `python -m qgate.bench --mps ${a.mps}${a.quick ? " --quick" : ""} --scale ${a.scale} --seed ${a.seed}` : "";
    const L = meta.limitations || [];
    if (has(L)) $("limits").innerHTML = L.map((l) => `<li>${esc(l)}</li>`).join("");
    else $("limits").closest(".card").classList.add("hidden");
    $("gen").textContent = meta.generated_at ? "Generado " + meta.generated_at + "." : "";
  })();
})();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "results/results.json"
    dst = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(src), "report.html")
    print(build(src, dst))
