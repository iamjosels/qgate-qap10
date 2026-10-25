"""Genera entrega/QGate.pptx con el estilo de design/Slide.dc.html y design/SlideContent.dc.html.

Uso:
    python entrega/make_ppt.py [results/results.json] [entrega/QGate.pptx]

Cada slide se escribe como HTML 1280x720 con las fuentes de marca (Barlow Condensed, IBM Plex),
se renderiza a PNG con Chrome o Edge en modo headless (entrega/slides/) y se arma el PPTX con esas
imágenes y las notas del orador. BRAND.md lo permite cuando las fuentes no están instaladas.
Todos los números salen de results.json; los nombres, de entrega/equipo.json.
Requiere python-pptx y Chrome o Edge.
"""
from __future__ import annotations

import html
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile

from pptx import Presentation
from pptx.util import Inches

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BROWSERS = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            "/usr/bin/google-chrome", "/usr/bin/chromium", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]

PLANE = ('<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="#0B0B0C" stroke-width="1.8" '
         'stroke-linecap="round" stroke-linejoin="round"><path d="M17.8 19.2 16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 '
         '0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 '
         '3.5 5.3c.3.4.8.5 1.3.3l.5-.2c.4-.3.6-.7.5-1.2z"/></svg>')

BASE = """<!doctype html><html lang="es"><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700;800&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
html,body{margin:0;background:#0B0B0C}
.s{width:1280px;height:720px;box-sizing:border-box;background:#0B0B0C;color:#F4F1E8;font-family:'IBM Plex Sans',sans-serif;overflow:hidden;position:relative}
.c{padding:48px 56px 40px;display:flex;flex-direction:column;gap:28px;box-sizing:border-box}
.hd{display:flex;align-items:center;gap:16px}
.no{padding:6px 14px;border-radius:6px;background:#FFC629;color:#0B0B0C;font:800 34px/1 'Barlow Condensed',sans-serif}
h1{margin:0;font:800 56px/1 'Barlow Condensed',sans-serif;letter-spacing:.01em;text-transform:uppercase}
.brandk{margin-left:auto;font:13px 'IBM Plex Mono',monospace;letter-spacing:.14em;color:#6E6C66}
.mono{font-family:'IBM Plex Mono',monospace}
.card{background:#141518;border-radius:14px;padding:28px 32px;display:flex;flex-direction:column;justify-content:space-between;min-width:0;box-sizing:border-box}
.k{font:14px 'IBM Plex Mono',monospace;letter-spacing:.14em;text-transform:uppercase}
.big{font:800 180px/.8 'Barlow Condensed',sans-serif}
.mid{font:800 110px/.85 'Barlow Condensed',sans-serif}
.unit{font:700 44px 'Barlow Condensed',sans-serif}
.sub{font:18px 'IBM Plex Mono',monospace;color:#C9C6BC}
.chips{display:flex;flex-wrap:wrap;gap:10px}
.chip{padding:8px 14px;border-radius:999px;border:1px solid #2C2F35;font:14px 'IBM Plex Mono',monospace;color:#C9C6BC}
.chip.q{border-color:#4FE3E0;color:#4FE3E0}
.g2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:28px;flex-grow:1;min-height:0}
.g3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:24px;flex-grow:1;min-height:0}
.y{color:#FFC629}.q{color:#4FE3E0}.o{color:#FF6B3D}
img.fig{max-width:100%;max-height:100%;border-radius:10px;display:block;margin:auto}
</style></head><body><div class="s">__BODY__</div></body></html>"""


from final_tables import stage3_tail, tie_label  # noqa: E402  (misma regla que el README)

def g(x, d=None):
    if x is None:
        return "-"
    return f"{x:g}" if d is None else f"{x:.{d}f}"


def sp(n):
    return f"{int(round(n)):,}".replace(",", "\u202f")


def pct(x, d=1):
    return f"{100 * x:.{d}f}%"


def _logo(name):
    import base64
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "design", "logo", name)
    with open(p, "rb") as fh:
        return "data:image/png;base64," + base64.b64encode(fh.read()).decode("ascii")


def head(no, title):
    return (f'<div class="hd"><div class="no">{no}</div><h1>{html.escape(title)}</h1>'
            f'<div class="brandk" style="display:flex;align-items:center;gap:10px"><img src="{_logo("qgate_icono_64.png")}" '
            f'width="32" height="32" alt="" style="border-radius:6px">QGATE</div></div>')


def chips(items):
    return '<div class="chips">' + "".join(
        f'<div class="chip{" q" if q else ""}">{html.escape(t)}</div>' for t, q in items) + "</div>"


def slides(R, team, img):
    meta, data = R["meta"], R["data"]
    ref, N = meta["reference_optimum"], meta["N"]
    val = {v["n"]: v for v in R["validation"]}
    C = {c["method"]: c for c in R["classical"]}
    Q = {q["id"]: q for q in R["quantum"]}
    H = {h["method"]: h for h in R["hybrid"]}
    hq, hq8, hr8 = H["qgate_lns_qaoa"], H.get("qgate_lns_qaoa_s8"), H.get("qgate_lns_random_s8")
    rnd = next(a for a in R["assignments"] if a["label"] == "Aleatoria")
    seeds = R.get("hybrid_seeds", {})
    out = []

    # 1 · portada (Slide.dc.html)
    names = "".join(f"<div>{html.escape(n)}</div>" for n in team["integrantes"])
    out.append((f"""<div style="display:flex;height:100%">
  <div style="flex:1;padding:56px 56px 44px;display:flex;flex-direction:column;justify-content:space-between">
    <div class="mono" style="font-size:14px;letter-spacing:.16em;color:#9A9890">IBM QUANTUM HACKATHON 2026 · RETO NTT DATA QAP10</div>
    <div style="display:flex;flex-direction:column;gap:20px">
      <img src="{_logo('qgate_logo_completo_360.png')}" alt="QGate" style="width:300px;height:auto;display:block">
      <div style="font-size:36px;font-weight:500">Vuelos → puertas con QAOA híbrido</div>
    </div>
    <div class="mono" style="display:grid;grid-template-columns:repeat(2,max-content);gap:10px 40px;font-size:15px;color:#C9C6BC">{names}</div>
  </div>
  <div style="width:380px;background:#FFC629;color:#0B0B0C;padding:48px 40px;box-sizing:border-box;display:flex;flex-direction:column;justify-content:space-between">
    {PLANE.format(s=96)}
    <div style="display:flex;flex-direction:column;gap:4px">
      <div style="font:800 88px/.85 'Barlow Condensed'">P01–P{N:02d}</div>
      <div style="display:flex;align-items:center;gap:12px;font:700 40px 'Barlow Condensed'">
        <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="#0B0B0C" stroke-width="2.4" stroke-linecap="square"><path d="M5 12h13"/><path d="M13 6l6 6-6 6"/></svg>Categoría Industria</div>
    </div>
    <div class="mono" style="font-size:13px;letter-spacing:.12em">TRACK A · AEROPUERTO</div>
  </div></div>""",
                "Somos QGate. Asignamos vuelos de conexión a puertas de embarque usando QAOA de Qiskit como pieza "
                "dentro de una búsqueda clásica."))

    # 2 · problema
    out.append((f"""<div class="c" style="height:100%">{head("01", "El problema")}
  <div style="display:grid;grid-template-columns:400px minmax(0,1fr);gap:28px;flex-grow:1;min-height:0">
    <div class="card" style="border-top:6px solid #FFC629">
      <div class="k y">{N} vuelos · {N} puertas</div>
      <div><div class="mid" style="font-size:92px">{sp(math.factorial(N))}</div><div class="unit" style="margin-top:8px">asignaciones</div></div>
      <div class="sub">C = Σ pasajeros × distancia<br>cada par se cuenta una vez</div>
    </div>
    <div class="card" style="padding:18px;justify-content:center"><img class="fig" src="{img('mapa_puertas.png')}"></div>
  </div>
  {chips([("qap10 (MIPLIB) · unidades supuestas", False), (f"al azar: costo {g(rnd['cost'])}", False), (f"QGate: costo {g(hq['final_cost'])}", True)])}
</div>""",
                f"Diez vuelos de conexión, diez puertas: {sp(math.factorial(N))} asignaciones posibles. El costo suma "
                f"pasajeros por distancia. A la izquierda una asignación al azar, costo {g(rnd['cost'])}; a la derecha "
                f"la de QGate, {g(hq['final_cost'])}. Los datos son el benchmark qap10: las unidades son supuestos."))

    # 3 · datos verificados
    tiles = "".join(
        f"""<div class="card" style="border-top:6px solid #FFC629;align-items:flex-start">
      <div class="k" style="color:#9A9890">N = {n}</div>
      <div class="big y">{g(val[n]['optimum'])}</div>
      <div class="sub">{'✓ esperado ' + g(val[n]['expected']) if val[n]['ok'] else '✗'}</div></div>"""
        for n in (3, 4, N))
    mr = data["mps_report"]
    out.append((f"""<div class="c" style="height:100%">{head("02", "Datos verificados")}
  <div class="g3">{tiles}</div>
  {chips([(f"MPS: {sp(mr['n_cols'])} variables", False), (f"{sp(mr['n_rows'])} restricciones", False),
          (f"residuo F·D = {g(data['factorization_residual'])}", False), ("cada par una vez (no 48 · 64 · 680)", False),
          ("340 solo para medir el gap", False)])}
</div>""",
                "El MPS viene linealizado. Las filas con lado derecho 1 identifican las x; cada variable y aparece junto "
                "a dos x y su coeficiente es flujo por distancia. Factorizamos con residuo cero y la escala cuadra: "
                f"{g(val[3]['optimum'])}, {g(val[4]['optimum'])} y {g(val[N]['optimum'])}."))

    # 4 · qiskit
    x4, xy4 = Q["N4-x-p1"], Q["N4-xy-p1"]
    out.append((f"""<div class="c" style="height:100%">{head("03", "Qiskit: QAOA en 16 qubits")}
  <div class="g2">
    <div class="card" style="border-top:6px solid #4FE3E0">
      <div class="k q">Mixer X · N = 4 · P(válida) · SIMULADOR</div>
      <div style="display:flex;align-items:baseline;gap:16px"><div class="big q">×{x4['p_feasible'] / x4['random_feasible_baseline']:.0f}</div><div class="unit">el azar de su espacio</div></div>
      <div class="sub">{pct(x4['p_feasible'])} vs {pct(x4['random_feasible_baseline'], 3)} (2<sup>16</sup> estados)</div>
    </div>
    <div class="card" style="border-top:6px solid #4FE3E0">
      <div class="k q">Mixer XY + estado W · P(válida) · SIMULADOR</div>
      <div class="big q">{pct(xy4['p_feasible'], 0)}</div>
      <div class="sub">azar con una puerta por vuelo: {pct(xy4['random_feasible_baseline'])}</div>
    </div>
  </div>
  {chips([(f"{xy4['qubits']} qubits · {xy4['cx_count']} CX · p = 1", True), ("QUBO → Ising → QAOA", False),
          ("Aer: statevector + shots", True), ("COBYLA clásico ajusta γ, β", False)])}
</div>""",
                "Pasamos el QUBO a Ising y corremos QAOA en Qiskit Aer. Con el mixer estándar X, QAOA muestrea "
                f"asignaciones válidas {x4['p_feasible'] / x4['random_feasible_baseline']:.0f} veces más que el azar. "
                f"Con el mixer XY y estado W, cada vuelo queda en una sola puerta y llegamos a {pct(xy4['p_feasible'], 0)} válidas."))

    # 5 · límites (SlideContent.dc.html)
    nxy = Q.get("N3-xy-p1-noise0.01")
    lim_chips = [("λ elegida con barrido", False), ("crudo vs pulido, por separado", False)]
    if nxy:
        lim_chips.insert(1, (f"ruido 1%: XY {pct(nxy['p_feasible'], 0)} → {pct(nxy['feasible_fraction_shots'], 0)} válidas", False))
    hw = R.get("hardware")
    hxy = None
    if hw and hw.get("backend"):
        hxy = next((e for e in hw.get("experiments", []) if e["mixer"] == "xy"), None)
        hx_ = next((e for e in hw.get("experiments", []) if e["mixer"] == "x"), None)
        if hxy and hx_:
            lim_chips = [lim_chips[0], (f"HARDWARE {hw['backend']} N=3: XY {pct(hxy['feasible_fraction'])} vs azar {pct(hxy['random_feasible_baseline'])} (casi sin ventaja) · "
                                        f"X {pct(hx_['feasible_fraction'])} vs {pct(hx_['random_feasible_baseline'])}", True),
                         (f"SIMULADOR ruido 1%: coincidió con XY ({pct(hxy['sim_noise_feasible_fraction'])}) y sobreestimó X ({pct(hx_['sim_noise_feasible_fraction'])})", False),
                         ("un solo job, un solo backend", False)]
    out.append((f"""<div class="c" style="height:100%">{head("04", "Límites")}
  <div class="g2">
    <div class="card" style="border-top:6px solid #FF6B3D">
      <div class="k o">QAOA directo · N = {N}</div>
      <div style="display:flex;align-items:baseline;gap:16px"><div class="big" style="font-size:200px;text-decoration:line-through;text-decoration-color:#FF6B3D;text-decoration-thickness:10px">{N * N}</div><div class="unit">qubits</div></div>
      <div class="sub">2<sup>{N * N}</sup> amplitudes · imposible de simular</div>
    </div>
    <div class="card" style="border-top:6px solid #4FE3E0">
      <div class="k q">QGate · cualquier N</div>
      <div style="display:flex;align-items:baseline;gap:16px"><div class="big q" style="font-size:200px">9</div><div class="unit">qubits</div></div>
      <div class="sub">por subproblema · siempre</div>
    </div>
  </div>
  {chips(lim_chips)}
</div>""",
                f"Simular el problema completo exige {N * N} qubits: imposible. QGate usa siempre piezas de 9. Elegimos "
                "lambda con un criterio analítico y lo validamos con un barrido. Medimos el ruido: con 1% el mixer XY "
                "pierde casi toda su ventaja de factibilidad. "
                + (f"Además corrimos N=3 una vez en {hw['backend']} de IBM Quantum: con mixer XY salieron "
                   f"{pct(hxy['feasible_fraction'], 0)} de asignaciones válidas, frente a {pct(hxy['sim_ideal_p_feasible'], 0)} "
                   f"ideal y {pct(hxy['random_feasible_baseline'], 0)} al azar."
                   if hw and hxy else "Todo es simulador.")))

    # 6 · híbrido
    abl = []
    if hq8 and hr8:
        bv = (R.get("extra") or {}).get("baselines_qaoa_s8")
        abl = [(f"8 shots, semilla {meta['seed']}: QAOA {pct(hq8['sub_success_rate'], 0)} · azar 27 estados {pct(hr8['sub_success_rate'], 0)}"
                + (f" · azar 6 válidas {pct(bv['hit_k8_random_valid_6'], 0)} · enumerar 100%" if bv else ""), True)]
    out.append((f"""<div class="c" style="height:100%">{head("05", "QAOA como subrutina")}
  <div style="display:grid;grid-template-columns:400px minmax(0,1fr);gap:28px;flex-grow:1;min-height:0">
    <div style="display:flex;flex-direction:column;gap:20px;min-height:0">
      <div class="card" style="border-top:6px solid #FFC629;flex:1">
        <div class="k y">QGate · N = {N} · semilla {meta['seed']} · SIMULADOR</div>
        <div class="mid y" style="font-size:130px">{g(hq['final_cost'])}</div>
        <div class="sub">gap {g(hq['gap_pct'], 1)}% · {hq['iters']} iteraciones</div>
      </div>
      <div class="card" style="border-top:6px solid #4FE3E0;flex:1">
        <div class="k q">P(óptimo) por pieza</div>
        <div class="mid q" style="font-size:90px">{g(hq['qaoa_p_optimal_mean'], 3)}</div>
        <div class="sub">azar 27 estados: {g(hq['random_p_optimal_mean'], 3)}{(" · 6 válidas: " + g(R["extra"]["baselines_qaoa"]["p_opt_random_valid_6"], 3)) if (R.get("extra") or {}).get("baselines_qaoa") else ""}</div>
      </div>
    </div>
    <div class="card" style="padding:18px;justify-content:center"><img class="fig" src="{img('hibrido_convergencia.png')}"></div>
  </div>
  {chips(abl + [(f"solver exacto, {len(seeds.get('seeds', []))} semillas: {g(ref)} en {seeds.get('hits_ref')}", False)])}
</div>""",
                f"QGate elige 3 vuelos, arma una pieza de 9 qubits con el resto fijo y la resuelve con QAOA. Con nuestra "
                f"semilla llega a {g(hq['final_cost'])}. Con 512 muestras hasta el azar resuelve piezas tan chicas, por eso "
                "medimos con 8: " + (f"QAOA resuelve {pct(hq8['sub_success_rate'], 0)} de las piezas y el azar sobre los 27 estados de su espacio "
                                     f"{pct(hr8['sub_success_rate'], 0)}. " if hq8 and hr8 else "")
                + (f"Pero el azar sobre las 6 permutaciones válidas llegaría a {pct((R.get('extra') or {})['baselines_qaoa_s8']['hit_k8_random_valid_6'], 0)} y enumerar las 6 opciones, a 100%: "
                   "QAOA concentra probabilidad respecto a su espacio de partida, pero en piezas de 3 vuelos aún no supera a esas alternativas. "
                   if (R.get("extra") or {}).get("baselines_qaoa_s8") else "")
                + f"Con el solver exacto en cada vecindario, {seeds.get('hits_ref')} de {len(seeds.get('seeds', []))} semillas llegan a {g(ref)}; el QAOA lo corrimos con la semilla {meta['seed']}: el límite es la búsqueda."))

    # 7 · escala
    Fn = R.get("final")
    solvers_all = {x["solver"] for x in Fn["summary"]} if Fn else set()
    if Fn:
        S = {(x["instance"], x["solver"], x["select"]): x for x in Fn["summary"]}
        rows_html = ""
        for i in Fn["instances"]:
            sa_ = S.get((i["instance"], "sa", None))
            q_ = S.get((i["instance"], "qaoa", "tension"))
            v = Fn["verdict"].get(i["instance"], {})
            a = Fn["attribution"].get(i["instance"], {})
            rd = a.get("cost_reduction_at_best_by_origin", {})
            if not (sa_ and q_):
                continue
            rows_html += (f"<tr><td>{html.escape(i['instance'])}<br><span style='font-size:12px;color:#9A9890'>{html.escape(i['origen'])}</span></td>"
                          f"<td>{g(sa_['cost_median'])} [{g(sa_['cost_min'])}, {g(sa_['cost_max'])}]<br><span style='font-size:12px;color:#9A9890'>{g(sa_['time_median_s'], 0)} s</span></td>"
                          f"<td>{g(q_['cost_median'])} [{g(q_['cost_min'])}, {g(q_['cost_max'])}]<br><span style='font-size:12px;color:#9A9890'>{g(q_['time_median_s'], 0)} s</span></td>"
                          f"<td>{100 * a.get('variables_quantum_frac', 0):.2f}%</td><td>{g(rd.get('block'))} de {g(sum(rd.values()))}</td>"
                          f"<td>{100 * a.get('frac_wall_in_qaoa_mean', 0):.0f}%</td>"
                          f"<td>{html.escape(tie_label(v, solvers_all))}</td></tr>")
        m_ = Fn["meta"]
        synth = [i["instance"] for i in Fn["instances"] if i["origen"] == "sintética"]
        fin_tail = stage3_tail(Fn, short=True)
        if all(Fn["attribution"].get(i, {}).get("cost_reduction_at_best_by_origin", {}).get("block", 1) == 0 for i in synth):
            fin_tail += " Bloques QAOA: 0 de reducción de costo."
        out.append((f"""<div class="c" style="height:100%">{head("06", "Escala (etapa 3)")}
  <div style="font:600 22px 'IBM Plex Sans';color:#F4F1E8;border-left:4px solid #FFC629;padding-left:14px">La memoria cuántica no crece con N; la calidad todavía no escala. {html.escape(fin_tail)}</div>
  <div class="card" style="padding:16px 20px;justify-content:flex-start">
  <table style="width:100%;border-collapse:collapse;font:15px 'IBM Plex Mono';color:#F4F1E8">
  <tr style="color:#9A9890;font-size:12px;letter-spacing:.1em;text-align:left"><th>INSTANCIA</th><th>SA mediana [mín, máx]</th><th>QGATE QAOA · TENSIÓN</th><th>VARIABLES CUÁNTICAS</th><th>REDUCCIÓN POR BLOQUES QAOA</th><th>% TIEMPO EN QAOA</th><th>MEJOR MEDIANA</th></tr>
  {rows_html}</table></div>
  {chips([(f"SIMULADOR · {len(m_['seeds'])} semillas · B={m_['blocks_B']} · {m_['shots']} shots", False), ("N > 10 sintéticas", False), ("fuente: results/final.json", False)])}
</div>""",
                    "Para la final medimos N de 10 a 20 con 10 semillas y el mismo presupuesto para todos. La memoria cuántica no crece: "
                    "siempre 9 qubits. La calidad todavía no escala: la tabla muestra la mediana y el rango entre semillas de SA y del híbrido "
                    "con QAOA, cuánto de la reducción de costo vino de los bloques QAOA y qué fracción del tiempo se fue en QAOA."))
    sc = R.get("scaling", []) if not Fn else []
    if not Fn:
        ns = sorted({r["N"] for r in sc})
        big = ns[-1]
        sa_b = next(r for r in sc if r["N"] == big and r["method"] == "simulated_annealing")
        q_b = next(r for r in sc if r["N"] == big and r["method"] == "qgate_lns_qaoa")
        mem = max(r["peak_mem_mb"] for r in sc if r["method"] == "qgate_lns_qaoa")
        out.append((f"""<div class="c" style="height:100%">{head("06", "Escala")}
      <div style="display:grid;grid-template-columns:340px minmax(0,1fr);gap:28px;flex-grow:1;min-height:0">
        <div class="card" style="border-top:6px solid #4FE3E0">
          <div class="k q">N = {ns[0]} → {big}</div>
          <div style="display:flex;align-items:baseline;gap:12px"><div class="big q">9</div><div class="unit">qubits</div></div>
          <div class="sub">QUBO directo N = {big}: {big * big} qubits<br>memoria pico QGate {g(mem, 1)} MB</div>
        </div>
        <div class="card" style="padding:18px;justify-content:center"><img class="fig" src="{img('escalabilidad.png')}"></div>
      </div>
      {chips([("N > 10 sintéticas · gap contra cota Gilmore-Lawler", False),
              (f"N = {big}: SA {g(sa_b['gap_vs_bound_pct'], 0)}% · QGate {g(q_b['gap_vs_bound_pct'], 0)}% sobre la cota", False),
              ("SA gana en calidad y tiempo", False)])}
    </div>""",
                    f"Al crecer hasta N={big} la parte cuántica sigue en 9 qubits y la memoria no crece. Sin óptimo conocido "
                    "medimos contra una cota inferior. Lo decimos claro: en simulador, simulated annealing gana en calidad y tiempo."))

    # 8 · cierre
    bf, sa = C["brute_force"], C["simulated_annealing"]
    lim = ["Simulador más lento que SA", "El ruido borra la ventaja de XY", "Con muchos shots el azar también llega"]
    if Fn and all(Fn["attribution"].get(i["instance"], {}).get("cost_reduction_at_best_by_origin", {}).get("block", 1) == 0
                  for i in Fn["instances"]):
        lim.append("Etapa 3: bloques QAOA sin reducción de costo")
    cols = [("Hoy", "#4FE3E0", ["XY + estado W: reglas por construcción", "QAOA concentra probabilidad en el óptimo",
                                 "Pieza cuántica de tamaño fijo"]),
            ("Límites", "#FF6B3D", lim),
            ("Siguiente", "#FFC629", ["Más corridas en hardware IBM" if R.get("hardware") else "Hardware IBM real (9 qubits)",
                                      "Piezas de 4 vuelos (16 qubits)", "Mitigación de errores"])]
    colh = "".join(f"""<div class="card" style="border-top:6px solid {c};justify-content:flex-start;gap:18px">
      <div class="k" style="color:{c}">{t}</div>{''.join(f'<div style="font-size:24px;line-height:1.25">{html.escape(i)}</div>' for i in items)}</div>"""
                   for t, c, items in cols)
    out.append((f"""<div class="c" style="height:100%">{head("07", "Qué aporta lo cuántico hoy")}
  <div class="g3">{colh}</div>
  <div style="font:600 24px 'IBM Plex Sans';color:#F4F1E8">El híbrido escala en memoria, todavía no en calidad.</div>
  <div class="mono" style="font-size:22px;color:#C9C6BC">Exacto <b class="y">{g(bf['cost'])}</b> · SA <b class="y">{g(sa['cost'])}</b> · QGate <b class="q">{g(hq['final_cost'])}</b> · azar <b>{g(rnd['cost'])}</b></div>
  <div class="mono" style="font-size:12px;letter-spacing:.12em;color:#6E6C66">QISKIT · QISKIT AER · NUMPY · SCIPY · MIPLIB 2017 (QAP10) · {html.escape(team['repo'].replace('https://', '').upper())}</div>
</div>""",
                "Hoy lo cuántico aporta estructura y concentración de probabilidad en piezas pequeñas, no velocidad en "
                "simulador, y lo mostramos con números. "
                + (f"Lo medimos en el simulador Qiskit Aer y en una corrida en {R['hardware']['backend']} de IBM Quantum. "
                   "El siguiente paso es más tiempo de hardware, piezas más grandes y mitigación de errores. Gracias."
                   if R.get("hardware") else
                   "El siguiente paso es hardware IBM real, piezas más grandes y mitigación de errores. Gracias.")
                + " Desarrollado con asistencia de Claude Code (Anthropic), supervisada por el equipo; parte del motor se preparó antes de la jornada; los cuatro integrantes pueden explicar su funcionamiento."))
    return out


def find_browser():
    for b in BROWSERS:
        if os.path.exists(b):
            return b
    return shutil.which("chrome") or shutil.which("msedge") or shutil.which("chromium")


def build(results_path, out_path):
    with open(results_path, encoding="utf-8") as fh:
        R = json.load(fh)
    with open(os.path.join(HERE, "equipo.json"), encoding="utf-8") as fh:
        team = json.load(fh)
    exp = os.path.join(os.path.dirname(os.path.abspath(results_path)), "extra.json")
    if os.path.exists(exp):
        with open(exp, encoding="utf-8") as fh:
            R["extra"] = json.load(fh)
    finp = os.path.join(os.path.dirname(os.path.abspath(results_path)), "final.json")
    if os.path.exists(finp):
        with open(finp, encoding="utf-8") as fh:
            R["final"] = json.load(fh)
    hwp = os.path.join(os.path.dirname(os.path.abspath(results_path)), "hardware.json")
    if os.path.exists(hwp):
        with open(hwp, encoding="utf-8") as fh:
            H = json.load(fh)
        if not H.get("fake"):                      # un resultado fake nunca va al PPT
            R["hardware"] = H
    img_dir = os.path.dirname(os.path.abspath(results_path))
    img = lambda n: "file:///" + os.path.join(img_dir, n).replace("\\", "/")  # noqa: E731
    browser = find_browser()
    if not browser:
        sys.exit("Se necesita Chrome o Edge para renderizar las slides.")
    png_dir = os.path.join(HERE, "slides")
    os.makedirs(png_dir, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="qgate_slides_")
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    for i, (body, note) in enumerate(slides(R, team, img), 1):
        hp = os.path.join(tmp, f"s{i}.html")
        with open(hp, "w", encoding="utf-8") as fh:
            fh.write(BASE.replace("__BODY__", body))
        png = os.path.join(png_dir, f"slide{i:02d}.png")
        subprocess.run([browser, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--allow-file-access-from-files", "--force-device-scale-factor=2",
                        "--virtual-time-budget=6000", "--window-size=1280,720",
                        f"--user-data-dir={os.path.join(tmp, 'profile')}",
                        f"--screenshot={png}", "file:///" + hp.replace("\\", "/")],
                       check=True, capture_output=True, timeout=120)
        s = prs.slides.add_slide(prs.slide_layouts[6])
        s.shapes.add_picture(png, 0, 0, width=prs.slide_width, height=prs.slide_height)
        s.notes_slide.notes_text_frame.text = note
    prs.save(out_path)
    shutil.rmtree(tmp, ignore_errors=True)
    return out_path


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "results", "results.json")
    dst = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "QGate.pptx")
    print(build(src, dst))
