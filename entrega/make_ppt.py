"""Genera entrega/QGate.pptx a partir de results/results.json y los PNG del bench.

Uso:
    python entrega/make_ppt.py [results/results.json] [entrega/QGate.pptx]

Todos los números salen del JSON; nombres del equipo desde entrega/equipo.json.
Requiere python-pptx (pip install python-pptx).
"""
from __future__ import annotations

import json
import math
import os
import sys

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

BG = RGBColor(0x0A, 0x10, 0x1C)
SURF = RGBColor(0x11, 0x1A, 0x2B)
LINE = RGBColor(0x24, 0x32, 0x4D)
TEXT = RGBColor(0xE8, 0xED, 0xF5)
TEXT2 = RGBColor(0xA9, 0xB4, 0xC7)
MUTED = RGBColor(0x74, 0x82, 0x9B)
AMBER = RGBColor(0xF5, 0xB9, 0x42)
CYAN = RGBColor(0x5F, 0xD4, 0xEE)
OK = RGBColor(0x3E, 0xCF, 0x8E)
HEAD, BODY, MONO = "Segoe UI Semibold", "Segoe UI", "Consolas"


def g(x, d=None):
    if x is None:
        return "-"
    if d is None:
        return f"{x:g}"
    return f"{x:.{d}f}"


# ---------------------------------------------------------------- helpers
def bg(slide):
    f = slide.background.fill
    f.solid()
    f.fore_color.rgb = BG


def text(slide, x, y, w, h, runs, size=18, color=TEXT, font=BODY, bold=False, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, spacing=None):
    """runs: str o lista de párrafos; cada párrafo str o lista de (texto, {opciones})."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.02)
    tf.margin_top = tf.margin_bottom = Inches(0.02)
    paras = runs if isinstance(runs, list) else [runs]
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        if spacing:
            p.space_after = Pt(spacing)
        parts = para if isinstance(para, list) else [(para, {})]
        for t, opt in parts:
            r = p.add_run()
            r.text = t
            r.font.size = Pt(opt.get("size", size))
            r.font.bold = opt.get("bold", bold)
            r.font.name = opt.get("font", font)
            r.font.color.rgb = opt.get("color", color)
    return tb


def box(slide, x, y, w, h, fill=SURF, line=LINE, radius=True):
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE,
                                 Inches(x), Inches(y), Inches(w), Inches(h))
    if radius:
        shp.adjustments[0] = min(0.08, 0.12 / min(w, h))
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
        shp.line.width = Pt(1)
    shp.shadow.inherit = False
    return shp


def accent(slide, x, y, h, color=AMBER):
    a = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(0.06), Inches(h))
    a.fill.solid()
    a.fill.fore_color.rgb = color
    a.line.fill.background()


def kpi(slide, x, y, w, h, value, label, color=AMBER, sub=None, vsize=40):
    box(slide, x, y, w, h)
    accent(slide, x, y + 0.12, h - 0.24, color)
    text(slide, x + 0.25, y + 0.12, w - 0.35, 0.35, label.upper(), size=11, color=TEXT2, bold=True)
    text(slide, x + 0.25, y + 0.42, w - 0.35, h - 0.55, value, size=vsize, color=color, font=MONO, bold=True)
    if sub:
        text(slide, x + 0.25, y + h - 0.45, w - 0.35, 0.35, sub, size=11, color=MUTED)


def header(slide, idx, title, sub=None):
    text(slide, 0.6, 0.38, 1.0, 0.4, idx, size=14, color=AMBER, font=MONO, bold=True)
    text(slide, 0.6, 0.68, 12.0, 0.8, title, size=34, color=TEXT, font=HEAD, bold=True)
    if sub:
        text(slide, 0.6, 1.38, 12.0, 0.45, sub, size=16, color=TEXT2)


def image(slide, path, x, y, w=None, h=None):
    if not os.path.exists(path):
        return None
    kw = {}
    if w:
        kw["width"] = Inches(w)
    if h:
        kw["height"] = Inches(h)
    return slide.shapes.add_picture(path, Inches(x), Inches(y), **kw)


def footer(slide, txt):
    text(slide, 0.6, 7.0, 12.2, 0.35, txt, size=10, color=MUTED)


def notes(slide, txt):
    slide.notes_slide.notes_text_frame.text = txt


def human_bytes(b):
    if b >= 1024 ** 5:
        e = int(math.floor(math.log10(b)))
        return f"{b / 10 ** e:.1f}·10^{e} B"
    for u in ("B", "KiB", "MiB", "GiB", "TiB"):
        if b < 1024:
            return f"{b:g} {u}"
        b /= 1024
    return f"{b:g} PiB"


# ------------------------------------------------------------------ slides
def build(results_path, out_path):
    with open(results_path, encoding="utf-8") as fh:
        R = json.load(fh)
    with open(os.path.join(HERE, "equipo.json"), encoding="utf-8") as fh:
        team = json.load(fh)
    img_dir = os.path.dirname(os.path.abspath(results_path))
    img = lambda n: os.path.join(img_dir, n)  # noqa: E731

    meta, data = R["meta"], R["data"]
    ref = meta["reference_optimum"]
    N = meta["N"]
    val = {v["n"]: v for v in R["validation"]}
    bf = next(c for c in R["classical"] if c["method"] == "brute_force")
    sa = next(c for c in R["classical"] if c["method"] == "simulated_annealing")
    glb = next(c for c in R["classical"] if c["method"] == "gilmore_lawler_bound")
    Q = {q["id"]: q for q in R["quantum"]}
    hq = next(h for h in R["hybrid"] if h["method"] == "qgate_lns_qaoa")
    he = next(h for h in R["hybrid"] if h["method"] == "qgate_lns_exact")
    seeds = R.get("hybrid_seeds", {})
    mr = data["mps_report"]
    rnd = next(a for a in R["assignments"] if a["label"] == "Aleatoria")
    vers = meta["versions"]

    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    blank = prs.slide_layouts[6]

    # 1 · portada
    s = prs.slides.add_slide(blank)
    bg(s)
    text(s, 0.8, 0.7, 8, 0.4, "IBM QUANTUM HACKATHON 2026 · RETO NTT DATA QAP10", size=13, color=AMBER,
         font=MONO, bold=True)
    text(s, 0.8, 1.5, 9, 1.8, [[("Q", {"color": TEXT}), ("Gate", {"color": AMBER})]], size=96, font=HEAD,
         bold=True)
    text(s, 0.8, 3.15, 10, 0.7, [[("Vuelos ", {}), ("→", {"color": AMBER}), (" puertas con QAOA híbrido", {})]],
         size=30, color=TEXT2, font=HEAD)
    text(s, 0.8, 4.1, 10, 0.5, "Track A · Aeropuerto · Qiskit " + str(vers.get("qiskit")) + " + Aer",
         size=16, color=CYAN, font=MONO)
    text(s, 0.8, 5.35, 11, 0.5, "   ·   ".join(team["integrantes"]), size=18, color=TEXT)
    text(s, 0.8, 5.85, 11, 0.4, f"Equipo {team['equipo']}", size=13, color=MUTED)
    footer(s, f"{team['repo']}   ·   demo: {team['demo']}")
    notes(s, "Somos QGate. Asignamos vuelos de conexión a puertas de embarque con un método híbrido: "
             "QAOA en Qiskit resuelve piezas pequeñas dentro de una búsqueda clásica.")

    # 2 · problema
    s = prs.slides.add_slide(blank)
    bg(s)
    header(s, "01", "El problema", "Pasajeros en conexión caminan entre puertas")
    kpi(s, 0.6, 2.1, 2.9, 1.5, f"{N} × {N}", "vuelos × puertas", AMBER)
    kpi(s, 0.6, 3.8, 2.9, 1.5, f"{math.factorial(N) / 1e6:.1f} M", f"asignaciones ({N}!)", AMBER, vsize=36)
    box(s, 0.6, 5.5, 2.9, 1.25)
    text(s, 0.8, 5.6, 2.6, 1.1, [[("C = Σ", {"font": MONO, "color": AMBER, "bold": True}),
                                  ("i<k", {"size": 11, "font": MONO, "color": AMBER}),
                                  (" F·D", {"font": MONO, "color": AMBER, "bold": True})],
                                 [("pasajeros × distancia, cada par una vez", {"size": 11, "color": TEXT2})]],
         size=20)
    image(s, img("mapa_puertas.png"), 3.8, 2.05, w=9.0)
    footer(s, "qap10 (MIPLIB) es un benchmark matemático: pasajeros y distancias son supuestos de negocio.")
    notes(s, f"Un aeropuerto asigna {N} vuelos de conexión a {N} puertas. Si dos vuelos comparten muchos "
             f"pasajeros y sus puertas quedan lejos, la gente camina más. Hay {math.factorial(N):,} asignaciones. "
             f"A la izquierda una asignación aleatoria (costo {g(rnd['cost'])}), a la derecha la de QGate.")

    # 3 · datos
    s = prs.slides.add_slide(blank)
    bg(s)
    header(s, "02", "Datos: del MPS al modelo", "Verificamos la escala con los óptimos de control")
    steps = [("4150", "variables = 100 x + 4050 y"), (str(mr["n_rows"]), "restricciones de igualdad"),
             ("y ↔ (x_ij , x_kl)", "coeficiente = F_ik · D_jl"),
             (g(data.get("factorization_residual")), "residuo SVD (F, D exactos)")]
    for i, (v, l) in enumerate(steps):
        y = 2.05 + i * 1.18
        box(s, 0.6, y, 5.6, 1.0)
        text(s, 0.85, y + 0.12, 5.2, 0.5, v, size=22, color=CYAN, font=MONO, bold=True)
        text(s, 0.85, y + 0.58, 5.2, 0.35, l, size=12, color=TEXT2)
    for i, n in enumerate((3, 4, N)):
        v = val[n]
        x = 6.8 + i * 2.05
        box(s, x, 2.05, 1.85, 2.3)
        text(s, x, 2.2, 1.85, 0.4, f"N = {n}", size=14, color=TEXT2, font=MONO, align=PP_ALIGN.CENTER)
        text(s, x, 2.65, 1.85, 0.9, g(v["optimum"]), size=40, color=AMBER, font=MONO, bold=True,
             align=PP_ALIGN.CENTER)
        text(s, x, 3.6, 1.85, 0.4, "✓ esperado " + g(v["expected"]) if v["ok"] else "✗",
             size=12, color=OK if v["ok"] else AMBER, font=MONO, align=PP_ALIGN.CENTER)
    text(s, 6.8, 4.65, 6.0, 2.2,
         [[("Cómo: ", {"bold": True, "color": TEXT}),
           ("las filas de asignación (rhs 1) identifican las x; cada y aparece junto a dos x y su costo es F·D. "
            "Armamos T, lo factorizamos en F y D y probamos el orden de índices hasta reproducir 24 y 32.", {})],
          [("Si se duplicaran pares saldría 48 · 64 · 680.", {"color": MUTED})]],
         size=14, color=TEXT2, spacing=8)
    footer(s, f"Fuerza bruta N={N}: {math.factorial(N):,} permutaciones en {g(bf['time_s'], 1)} s · "
              f"{bf.get('n_optimal_perms', 1)} óptimo · el 340 solo se usa para medir el gap")
    notes(s, "El MPS está linealizado. Reconstruimos el costo sin depender de nombres: las filas de asignación "
             "dan las 100 x, y cada variable y une dos x con coeficiente F por D. Factorizamos con residuo cero y "
             f"validamos: N=3 da {g(val[3]['optimum'])}, N=4 da {g(val[4]['optimum'])} y la instancia completa "
             f"{g(val[N]['optimum'])}. La escala es correcta.")

    # 4 · qiskit
    s = prs.slides.add_slide(blank)
    bg(s)
    header(s, "03", "Qiskit: QUBO → Ising → QAOA", "Mixer X (todo penalizado) vs mixer XY + estado W (filas válidas)")
    image(s, img("qaoa_vs_azar.png"), 0.6, 2.0, w=8.0)
    q4x, q4xy = Q.get("N4-x-p1"), Q.get("N4-xy-p1")
    y = 2.0
    if q4x:
        kpi(s, 8.95, y, 3.8, 1.55, f"×{q4x['p_feasible'] / q4x['random_feasible_baseline']:.0f}",
            "N=4 · mixer X vs azar", CYAN,
            sub=f"P(válida) {q4x['p_feasible']:.3f} vs {q4x['random_feasible_baseline']:.4f}")
        y += 1.75
    if q4xy:
        kpi(s, 8.95, y, 3.8, 1.55, f"{q4xy['p_feasible']:.2f}", "N=4 · mixer XY P(válida)", CYAN,
            sub=f"azar con filas válidas {q4xy['random_feasible_baseline']:.3f}")
        y += 1.75
        kpi(s, 8.95, y, 3.8, 1.3, f"{q4xy['qubits']} q · {q4xy['cx_count']} CX", "circuito N=4, p=1", CYAN,
            vsize=26)
    footer(s, "Qiskit construye el circuito, simula (Aer statevector + shots) y transpila. "
              "Lo clásico: leer MPS, QUBO, λ, COBYLA, búsqueda.")
    notes(s, "Pasamos el QUBO a un Hamiltoniano de Ising y lo resolvemos con QAOA en Qiskit Aer. Comparamos dos "
             "ansatz: el estándar con mixer X, donde todo es penalidad, y el de operador alternante con mixer XY y "
             "estado W, que mantiene una puerta por vuelo. QAOA siempre supera al azar en asignaciones válidas.")

    # 5 · límites
    s = prs.slides.add_slide(blank)
    bg(s)
    header(s, "04", "Límites y cómo los manejamos", "Memoria, penalidad λ y ruido")
    box(s, 0.6, 2.0, 4.3, 3.6)
    text(s, 0.85, 2.12, 3.9, 0.4, "STATEVECTOR", size=11, color=TEXT2, bold=True)
    rows = [m for m in meta.get("statevector_memory", []) if m["N"] in (4, 5, 10, 14)]
    for i, m in enumerate(rows):
        yy = 2.6 + i * 0.7
        text(s, 0.85, yy, 1.2, 0.5, f"N={m['N']}", size=18, color=TEXT2, font=MONO)
        text(s, 1.95, yy, 1.2, 0.5, f"{m['qubits']} q", size=18, color=CYAN, font=MONO)
        text(s, 3.0, yy, 1.85, 0.5, human_bytes(m["bytes"]), size=18,
             color=AMBER if m["N"] >= 10 else TEXT, font=MONO, bold=m["N"] >= 10)
    text(s, 0.85, 5.15, 3.9, 0.4, "→ subproblemas de 9 qubits", size=14, color=AMBER, bold=True)
    image(s, img("ruido.png"), 5.15, 2.0, h=3.6)
    nx, nxy = Q.get("N3-x-p1-noise0.01"), Q.get("N3-xy-p1-noise0.01")
    if nxy:
        text(s, 0.6, 5.85, 12.2, 1.0,
             [[("Ruido 1%: ", {"bold": True, "color": AMBER}),
               (f"XY {nxy['p_feasible']:.2f} → {nxy['feasible_fraction_shots']:.2f} válidas "
                f"(azar {nxy['random_feasible_baseline']:.2f})", {}),
               (f"   ·   X {nx['p_feasible']:.2f} → {nx['feasible_fraction_shots']:.3f}" if nx else "", {})]],
             size=18, color=TEXT2)
    footer(s, "λ0 = mayor aporte posible de una asignación, validado con barrido λ/λ0 (dashboard). "
              "Simulador con ruido despolarizante; no es hardware real.")
    notes(s, "Simular N=10 completo exige 100 qubits: imposible en memoria. Por eso usamos piezas de 9 qubits. "
             "Elegimos lambda como el mayor aporte posible de una asignación y lo validamos con un barrido. Y "
             "medimos ruido: el mixer XY pierde casi toda su ventaja de factibilidad con 1% de ruido.")

    # 6 · híbrido
    s = prs.slides.add_slide(blank)
    bg(s)
    header(s, "05", "QGate: QAOA como subrutina", "Búsqueda clásica por vecindarios · 3 vuelos = 9 qubits por paso")
    loop = ["Elegir 3 vuelos", "Subproblema 9 qubits", "QAOA (Aer)", "Aceptar si mejora", "Perturbar si se estanca"]
    for i, st in enumerate(loop):
        yy = 2.0 + i * 0.78
        box(s, 0.6, yy, 3.6, 0.62, fill=SURF, line=CYAN if "QAOA" in st or "qubits" in st else LINE)
        text(s, 0.8, yy + 0.08, 3.3, 0.46, f"{i + 1}  {st}", size=15,
             color=CYAN if "QAOA" in st or "qubits" in st else TEXT, anchor=MSO_ANCHOR.MIDDLE)
    image(s, img("hibrido_convergencia.png"), 4.5, 1.95, w=5.6)
    hs8 = next((h for h in R["hybrid"] if h["method"] == "qgate_lns_qaoa_s8"), None)
    rs8 = next((h for h in R["hybrid"] if h["method"] == "qgate_lns_random_s8"), None)
    kpi(s, 10.35, 1.95, 2.45, 1.5, f"{hq['qaoa_p_optimal_mean']:.2f}", "P(óptimo) por pieza", CYAN,
        sub=f"azar {hq['random_p_optimal_mean']:.3f}", vsize=34)
    kpi(s, 10.35, 3.6, 2.45, 1.5, g(hq["final_cost"]), f"QGate · {hq['shots']} shots", CYAN,
        sub=f"gap {g(hq['gap_pct'], 1)} % · {hq['iters']} iter", vsize=34)
    if hs8 and rs8:
        kpi(s, 10.35, 5.25, 2.45, 1.5, f"{100 * hs8['sub_success_rate']:.0f}% · {100 * rs8['sub_success_rate']:.0f}%",
            "8 shots: QAOA · azar", CYAN, sub=f"costo {g(hs8['final_cost'])} vs {g(rs8['final_cost'])}", vsize=24)
    if seeds:
        text(s, 0.6, 6.05, 3.9, 0.9,
             [[(f"{len(seeds['seeds'])} semillas (exacto): ", {"bold": True, "color": TEXT}),
               (f"media {g(seeds['mean'], 1)}, llega a {g(ref)} en {seeds['hits_ref']}/{len(seeds['seeds'])}", {})]],
             size=13, color=TEXT2)
    footer(s, f"Con {hq['shots']} shots el azar también resuelve piezas de 3 vuelos (6 opciones). "
              "Con 8 shots se ve lo que aporta QAOA: concentra probabilidad en el óptimo.")
    notes(s, f"QGate elige 3 vuelos, arma un subproblema de 9 qubits con el resto fijo y lo resuelve con QAOA. "
             f"Con la semilla del bench llega a {g(hq['final_cost'])}, gap {g(hq['gap_pct'], 1)}%. Fuimos honestos: con "
             f"{hq['shots']} muestras hasta el azar resuelve piezas tan chicas. Por eso medimos con 8 muestras: QAOA "
             + (f"resuelve {100 * hs8['sub_success_rate']:.0f}% de las piezas y el azar {100 * rs8['sub_success_rate']:.0f}%. "
                if hs8 and rs8 else "") +
             f"En varias semillas el marco llega a {g(ref)} en {seeds.get('hits_ref')} de {len(seeds.get('seeds', []))}.")

    # 7 · escala
    s = prs.slides.add_slide(blank)
    bg(s)
    sc = R.get("scaling", [])
    ns = sorted({r["N"] for r in sc})
    header(s, "06", "Escalabilidad", f"N = {', '.join(map(str, ns))} · qubits constantes")
    image(s, img("escalabilidad.png"), 0.6, 2.0, w=9.3)
    big = max(ns) if ns else N
    kpi(s, 10.2, 2.0, 2.6, 1.5, "9", "qubits en todo N", CYAN, vsize=40)
    kpi(s, 10.2, 3.7, 2.6, 1.5, f"{big * big}", f"qubits QUBO N={big}", AMBER, vsize=40)
    qrows = [r for r in sc if r["method"] == "qgate_lns_qaoa"]
    if qrows:
        mem = max(r["peak_mem_mb"] for r in qrows)
        kpi(s, 10.2, 5.4, 2.6, 1.4, f"{mem:.1f} MB", "memoria pico QGate", CYAN, vsize=28)
    footer(s, f"N > {N}: sintéticas sin óptimo conocido, gap contra la cota Gilmore-Lawler (N={N}: cota {g(glb['bound'])}). "
              "SA gana en calidad y tiempo; lo que no crece es la parte cuántica.")
    notes(s, "Al crecer N el subproblema cuántico sigue siendo de 9 qubits y la memoria no crece. Sin óptimo "
             "conocido en N mayores, medimos contra una cota inferior. La búsqueda es más lenta que simulated "
             "annealing en simulador: eso es honesto y es lo que esperamos mejorar con hardware.")

    # 8 · cierre
    s = prs.slides.add_slide(blank)
    bg(s)
    header(s, "07", "Qué aporta lo cuántico hoy")
    cols = [("HOY", CYAN, ["XY + estado W: factibilidad por construcción",
                           "QAOA concentra probabilidad en el óptimo de cada pieza",
                           "Memoria constante al crecer N"]),
            ("LÍMITES", AMBER, ["Simulador más lento que SA",
                                "Ruido borra la ventaja de XY",
                                "Piezas de 3 vuelos: el azar con muchos shots también llega"]),
            ("SIGUIENTE", TEXT, ["Hardware IBM real (N=3, 9 qubits)",
                                 "Vecindarios k=4 (16 qubits)",
                                 "Warm start y mitigación de errores"])]
    for i, (t, col, items) in enumerate(cols):
        x = 0.6 + i * 4.15
        box(s, x, 1.75, 3.95, 3.9)
        accent(s, x, 1.9, 3.6, col)
        text(s, x + 0.3, 1.95, 3.5, 0.4, t, size=13, color=col, font=MONO, bold=True)
        text(s, x + 0.3, 2.5, 3.5, 3.0, items, size=17, color=TEXT, spacing=14)
    text(s, 0.6, 5.95, 12.2, 0.5,
         [[("Exacto ", {"color": TEXT2}), (g(bf["cost"]), {"color": AMBER, "bold": True, "font": MONO}),
           ("   ·   SA ", {"color": TEXT2}), (g(sa["cost"]), {"color": AMBER, "bold": True, "font": MONO}),
           ("   ·   QGate ", {"color": TEXT2}), (g(hq["final_cost"]), {"color": CYAN, "bold": True, "font": MONO}),
           ("   ·   aleatoria ", {"color": TEXT2}), (g(rnd["cost"]), {"color": MUTED, "bold": True, "font": MONO})]],
         size=18)
    footer(s, "Qiskit · Qiskit Aer · NumPy · SciPy · Matplotlib · MIPLIB 2017 (qap10) · " + team["repo"])
    notes(s, "Lo cuántico hoy aporta estructura: el mixer XY respeta las restricciones y QAOA resuelve bien piezas "
             "pequeñas. No tiene ventaja de tiempo frente al clásico en simulador, y lo decimos con números. "
             "El siguiente paso es hardware IBM real, vecindarios más grandes y mitigación de errores.")

    prs.save(out_path)
    return out_path


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "results", "results.json")
    dst = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "QGate.pptx")
    print(build(src, dst))
