"""Vista "00 · Panorama" del dashboard: los tres enfoques (clásico, cuántico, híbrido) lado a lado y
un cuadro comparativo de ventajas y desventajas.

Todo número sale de results.json (y de hardware.json si existe) a través de R; si un dato falta, su
celda o línea no se genera. Se construye en Python (no en JavaScript) para que
dashboard/check_panorama.py pueda verificar cada número contra los JSON.
"""
from __future__ import annotations

import html
import math

ICON = {
    "classic": ('<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
                'stroke-linecap="round" aria-hidden="true"><rect x="6" y="6" width="12" height="12" rx="1.5"/>'
                '<rect x="9.5" y="9.5" width="5" height="5"/><path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3"/></svg>'),
    "quantum": ('<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
                'stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="9" ry="3.5"/>'
                '<path d="M12 12 16 6"/><circle cx="16" cy="6" r="1.3" fill="currentColor"/></svg>'),
    "hybrid": ('<svg width="18" height="18" viewBox="0 0 64 64" aria-hidden="true"><rect width="64" height="64" rx="10" fill="currentColor"/>'
               '<circle cx="29" cy="29" r="15" fill="none" stroke="#0B0B0C" stroke-width="7"/>'
               '<path d="M38 38 L48 48" stroke="#0B0B0C" stroke-width="7" stroke-linecap="square"/>'
               '<polygon points="55,55 55,40 40,55" fill="#0B0B0C"/></svg>'),
}
NAME = {"classic": "CLÁSICO", "quantum": "CUÁNTICO", "hybrid": "HÍBRIDO"}
WHERE = {"classic": "CPU (NumPy/SciPy)", "quantum": "Qiskit Aer + IBM ibm_kingston", "hybrid": "QAOA de 9 qubits + búsqueda clásica"}
MARK = {"ok": ("✓", "ventaja"), "no": ("✗", "desventaja"), "mid": ("~", "parcial")}


def e(s) -> str:
    return html.escape(str(s))


def pct(v, d=1):
    return None if v is None else f"{100 * v:.{d}f}%"


def num(v, d=0):
    return None if v is None else (f"{v:.{d}f}" if d else f"{v:.0f}")


def sec(v):
    return None if v is None else f"{v:.1f} s"


def sci(v) -> str:
    """2.03e31 -> 2.0×10³¹ (legible en proyector)."""
    m, ex = f"{v:.1e}".split("e")
    sup = str(int(ex)).translate(str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻"))
    return f"{m}×10{sup}"


def chip(kind: str, where: bool = False) -> str:
    return (f'<span class="ap ap-{kind}">{ICON[kind]}<b>{NAME[kind]}</b>'
            + (f'<span class="ap-w">{e(WHERE[kind])}</span>' if where else "") + "</span>")


def _get(R):
    meta = R.get("meta", {})
    C = {c["method"]: c for c in R.get("classical", [])}
    Q = {q["id"]: q for q in R.get("quantum", [])}
    H = {h["method"]: h for h in R.get("hybrid", [])}
    V = {v["n"]: v for v in R.get("validation", [])}
    hw = R.get("hardware") or {}
    HW = {x["mixer"]: x for x in hw.get("experiments", [])}
    sc = R.get("scaling", [])
    return meta, C, Q, H, V, hw, HW, sc


def render(R: dict) -> str:
    meta, C, Q, H, V, hw, HW, sc = _get(R)
    ref, N = meta.get("reference_optimum"), meta.get("N")
    bf, sa, gl = C.get("brute_force"), C.get("simulated_annealing"), C.get("gilmore_lawler_bound")
    x4, xy4 = Q.get("N4-x-p1"), Q.get("N4-xy-p1")
    hq, hq8, hr8 = H.get("qgate_lns_qaoa"), H.get("qgate_lns_qaoa_s8"), H.get("qgate_lns_random_s8")
    seeds = R.get("hybrid_seeds") or {}
    hxy, hx = HW.get("xy"), HW.get("x")
    ns = sorted({r["N"] for r in sc})
    big = ns[-1] if ns else None
    row = lambda n, m: next((r for r in sc if r["N"] == n and r["method"] == m), None)  # noqa: E731
    sa_big, hq_big = (row(big, "simulated_annealing"), row(big, "qgate_lns_qaoa")) if big else (None, None)
    gap = lambda c: None if c is None or not ref else 100 * (c - ref) / ref  # noqa: E731
    mem_n = {m["N"]: m for m in meta.get("statevector_memory", [])}
    out = []

    # ---------------------------------------------------------------- flujo
    val = " · ".join(num(V[n]["optimum"]) for n in sorted(V) if V[n].get("ok"))
    out.append(f"""<div class="flow">
  <div class="fbox"><div class="kick">Datos</div><b>MPS qap10</b><span>{e(num(R.get('data', {}).get('mps_report', {}).get('n_cols')) or '')} variables</span></div>
  <div class="farr" aria-hidden="true">→</div>
  <div class="fbox"><div class="kick">Modelo verificado</div><b>F y D</b><span>{e(val)}</span></div>
  <div class="farr" aria-hidden="true">→</div>
  <div class="flanes">{chip('classic')}{chip('quantum')}{chip('hybrid')}</div>
  <div class="farr" aria-hidden="true">→</div>
  <div class="fbox"><div class="kick">Resultado</div><b>Comparación</b><span>gap vs {e(num(ref))}</span></div>
</div>""")

    # --------------------------------------------------------- tres columnas
    def col(kind, what, steps, rows, star, star_sub, extra, goto):
        rws = "".join(f'<div class="kv"><span>{e(k)}</span><b>{e(v)}</b></div>' for k, v in rows if v is not None)
        stp = "".join(f"<li>{e(s)}</li>" for s in steps)
        ex = "".join(f'<div class="pline">{x}</div>' for x in extra if x)
        st = f'<div class="star">{e(star)}</div><div class="star-s">{e(star_sub)}</div>' if star else ""
        return (f'<article class="lane lane-{kind}"><div class="lane-h">{chip(kind, True)}</div>'
                f'<p class="what">{e(what)}</p>{st}{ex}<ol class="steps">{stp}</ol><div class="kvs">{rws}</div>'
                f'<button class="goto" type="button" data-goto="{goto}">Ver detalle →</button></article>')

    cols = []
    if bf:
        cols.append(col(
            "classic", f"Busca la mejor asignación de {N} vuelos con métodos clásicos, sin qubits.",
            [f"Fuerza bruta: evalúa las {N}! permutaciones en bloques", "Simulated annealing: intercambios de 2 vuelos",
             "Cota de Gilmore-Lawler: piso para medir el gap"],
            [("Dónde corre", WHERE["classic"]), ("Qubits", "0"), ("Tiempo", f"{sec(bf['time_s'])} fuerza bruta"
              + (f" · {sec(sa['time_s'])} SA" if sa else "")),
             ("Mejor costo válido", num(bf["cost"])), (f"Gap vs {num(ref)}", pct((gap(bf['cost']) or 0) / 100))],
            num(bf["cost"]), f"óptimo exacto en {sec(bf['time_s'])}",
            [f"SA llega a <b>{e(num(sa['cost']))}</b> en {e(sec(sa['time_s']))}" if sa else None,
             f"Cota Gilmore-Lawler <b>{e(num(gl['bound']))}</b>" if gl else None], "result"))
    if x4 or xy4:
        q_extra = []
        if xy4:
            q_extra.append(f"N=4 mixer XY: <b>{e(pct(xy4['p_feasible']))}</b> válidas vs {e(pct(xy4['random_feasible_baseline']))} al azar")
        if hxy:
            q_extra.append(f"<span class='hw'>{e(hw.get('backend'))} · N=3 real</span> XY <b>{e(pct(hxy['feasible_fraction']))}</b> "
                           f"(ideal {e(pct(hxy['sim_ideal_p_feasible']))}, azar {e(pct(hxy['random_feasible_baseline']))}, "
                           f"ruido simulado {e(pct(hxy['sim_noise_feasible_fraction']))})")
        if hx:
            q_extra.append(f"<span class='hw'>{e(hw.get('backend'))} · N=3 real</span> X <b>{e(pct(hx['feasible_fraction']))}</b> "
                           f"(azar {e(pct(hx['random_feasible_baseline']))})")
        ratio = x4["p_feasible"] / x4["random_feasible_baseline"] if x4 and x4.get("random_feasible_baseline") else None
        t_q = (f"{sec(xy4['time_s'])} N=4 en Aer" if xy4 else "") + (
            f" · {num(hw.get('usage_quantum_seconds'))} s QPU N=3" if hw.get("usage_quantum_seconds") else "")
        best_q = (f"{num(xy4['best_feasible_cost'])} en N=4 (óptimo {num(xy4['optimum'])})" if xy4 else None)
        cols.append(col(
            "quantum", "QAOA en Qiskit sobre instancias completas pequeñas (N=3 y N=4).",
            ["QUBO con penalidad λ y paso a Ising", "Circuito QAOA: mixer X, o estado W + mixer XY",
             "COBYLA ajusta γ y β con el statevector de Aer", "Muestreo de 4096 shots (Aer e IBM Quantum)"],
            [("Dónde corre", WHERE["quantum"]),
             ("Qubits", f"{xy4['qubits'] if xy4 else ''} en N=4" + (f" · {hxy['qubits']} en hardware" if hxy else "")),
             ("Tiempo", t_q or None), ("Mejor costo válido", best_q),
             (f"Gap vs {num(ref)}", f"no aplica: N={N} serían {N * N} qubits" if N else None)],
            f"×{ratio:.0f}" if ratio else None, "más válidas que el azar · N=4 mixer X" if ratio else "", q_extra, "qaoa"))
    if hq:
        h_extra = []
        bv = (R.get("extra") or {}).get("baselines_qaoa_s8")
        if hq8 and hr8:
            h_extra.append(f"Con 8 muestras QAOA acierta <b>{e(pct(hq8['sub_success_rate'], 0))}</b> de las piezas; azar (27 estados) "
                           f"{e(pct(hr8['sub_success_rate'], 0))}" + (f"; azar (6 permutaciones válidas) <b>{e(pct(bv['hit_k8_random_valid_6'], 0))}</b>; enumeración 100%" if bv else "")
                           + f" (costo QAOA {e(num(hq8['final_cost']))} vs azar 27 estados {e(num(hr8['final_cost']))})")
        if seeds.get("seeds"):
            h_extra.append(f"Llega a {e(num(ref))} en <b>{e(seeds['hits_ref'])} de {e(len(seeds['seeds']))}</b> semillas")
        if ns:
            h_extra.append(f"De N={e(ns[0])} a N={e(big)}: siempre <b>{e(hq.get('qubits_per_subproblem'))} qubits</b>")
        cols.append(col(
            "hybrid", "QAOA de 9 qubits resuelve piezas de 3 vuelos dentro de una búsqueda clásica.",
            ["Elegir 3 vuelos; el resto queda fijo", f"Pieza de {hq.get('qubits_per_subproblem')} qubits: QAOA p={hq.get('p')} en Aer",
             "Aceptar si baja el costo", "Si se estanca, perturbar desde la mejor"],
            [("Dónde corre", WHERE["hybrid"]), ("Qubits", f"{hq.get('qubits_per_subproblem')} por pieza"),
             ("Tiempo", f"{sec(hq['time_s'])} en Aer"), ("Mejor costo válido", f"{num(hq['final_cost'])} (semilla {meta.get('seed')})"),
             (f"Gap vs {num(ref)}", pct(gap(hq['final_cost']) / 100))],
            str(hq.get("qubits_per_subproblem")), "qubits por pieza, en cualquier N", h_extra, "airport"))
    out.append('<div class="lanes">' + "".join(cols) + "</div>")

    # ------------------------------------------------------ cuadro comparativo
    def cell(mark, text):
        if text is None:
            return '<td class="na"></td>'
        sym, word = MARK[mark]
        return f'<td class="m-{mark}"><span class="mk" title="{word}">{sym}</span> <span class="sr">{word}:</span> {text}</td>'

    fact = lambda n: math.factorial(n) if n else None  # noqa: E731
    rows = []
    rows.append(("Calidad en N=10",
                 cell("ok", f"{num(bf['cost'])} exacto (gap {pct(gap(bf['cost']) / 100)})") if bf else cell("ok", None),
                 cell("no", f"no resuelve N={N} directo ({N * N} qubits); N=4 llega a {num(xy4['best_feasible_cost'])} = óptimo") if xy4 else cell("no", None),
                 cell("mid", f"{num(hq['final_cost'])} con semilla {meta.get('seed')}; "
                             f"{seeds.get('hits_ref')} de {len(seeds.get('seeds', []))} semillas llegan a {num(ref)}") if hq and seeds else cell("mid", None)))
    rows.append(("Tiempo",
                 cell("ok", f"{sec(bf['time_s'])} fuerza bruta · {sec(sa['time_s'])} SA") if bf and sa else cell("ok", None),
                 cell("mid", f"{sec(xy4['time_s'])} N=4 en Aer" + (f" · {num(hw.get('usage_quantum_seconds'))} s QPU N=3" if hw.get('usage_quantum_seconds') else "")) if xy4 else cell("mid", None),
                 cell("no", f"{sec(hq['time_s'])} N=10 en Aer (vs {sec(sa['time_s'])} SA)") if hq and sa else cell("no", None)))
    m10 = mem_n.get(N)
    rows.append(("Qubits / memoria",
                 cell("ok", "0 qubits"),
                 cell("no", f"N²: N={N} son {N * N} qubits, statevector {sci(m10['bytes'])} B") if m10 else cell("no", None),
                 cell("ok", f"{hq.get('qubits_per_subproblem')} qubits; memoria pico {max(r['peak_mem_mb'] for r in sc if r['method'] == 'qgate_lns_qaoa'):.1f} MB")
                 if hq and sc else cell("ok", None)))
    rows.append((f"Escala a N={ns[-2] if len(ns) > 1 else big}-{big}" if big else "Escala",
                 cell("ok", f"SA a {num(sa_big['gap_vs_bound_pct'], 1)}% de la cota en N={big}, {sec(sa_big['time_s'])}; fuerza bruta inviable ({big}! = {sci(fact(big))})") if sa_big else cell("ok", None),
                 cell("no", f"N={big} serían {big * big} qubits") if big else cell("no", None),
                 cell("mid", f"siempre {hq.get('qubits_per_subproblem')} qubits; {num(hq_big['gap_vs_bound_pct'], 1)}% de la cota en N={big}, {sec(hq_big['time_s'])}") if hq_big and hq else cell("mid", None)))
    rows.append(("Garantiza el óptimo",
                 cell("ok", f"sí con fuerza bruta ({N}! = {fact(N):,} permutaciones)".replace(",", " ")) if bf else cell("ok", None),
                 cell("no", f"no: P(óptimo) {pct(xy4['p_optimal'])} en N=4") if xy4 else cell("no", None),
                 cell("no", f"no: {seeds.get('hits_ref')} de {len(seeds.get('seeds', []))} semillas") if seeds.get("seeds") else cell("no", None)))
    rows.append(("Sensibilidad al ruido",
                 cell("ok", "ninguna: cómputo exacto en CPU"),
                 cell("no", f"XY {pct(hxy['sim_ideal_p_feasible'])} ideal → {pct(hxy['feasible_fraction'])} en {hw.get('backend')} (azar {pct(hxy['random_feasible_baseline'])})") if hxy else cell("no", None),
                 cell("mid", f"no medido en hardware; piezas de {hq.get('qubits_per_subproblem')} qubits como la corrida N=3") if hq else cell("mid", None)))
    rows.append(("Soluciones válidas",
                 cell("ok", "100%: siempre una permutación"),
                 cell("mid", f"N=4: X {pct(x4['p_feasible'])}, XY {pct(xy4['p_feasible'])}" + (f"; hardware XY {pct(hxy['feasible_fraction'])}" if hxy else "")) if x4 and xy4 else cell("mid", None),
                 cell("ok", "100%: solo acepta piezas válidas")))
    rows.append(("Corre en hardware actual",
                 cell("ok", "sí, cualquier CPU"),
                 cell("mid", f"sí N=3 en {hw.get('backend')} ({hxy['two_qubit_gates']} compuertas 2q), XY {pct(hxy['feasible_fraction'])} vs azar {pct(hxy['random_feasible_baseline'])}") if hxy else cell("mid", None),
                 cell("mid", f"las piezas de {hq.get('qubits_per_subproblem')} qubits caben; el híbrido corrió en simulador") if hq else cell("mid", None)))
    ratio = x4["p_feasible"] / x4["random_feasible_baseline"] if x4 else None
    rows.append(("Ventaja principal",
                 cell("ok", f"exacto y rápido en N={N}: {num(bf['cost'])} en {sec(bf['time_s'])}") if bf else cell("ok", None),
                 cell("ok", f"concentra probabilidad: ×{ratio:.0f} el azar de su espacio (N=4, mixer X)") if ratio else cell("ok", None),
                 cell("ok", f"qubits constantes: {hq.get('qubits_per_subproblem')} de N={ns[0]} a N={big}") if hq and ns else cell("ok", None)))
    rows.append(("Desventaja principal",
                 cell("no", f"fuerza bruta explota: {big}! = {sci(fact(big))} en N={big}") if big else cell("no", None),
                 cell("no", f"qubits N² y ruido: XY cae a {pct(hxy['feasible_fraction'])} en hardware") if hxy else cell("no", None),
                 cell("no", f"más lento y peor que SA: {sec(hq['time_s'])} vs {sec(sa['time_s'])}; N={big} {num(hq_big['gap_vs_bound_pct'], 1)}% vs {num(sa_big['gap_vs_bound_pct'], 1)}%") if hq and sa and hq_big and sa_big else cell("no", None)))
    body = "".join(f"<tr><th scope='row'>{e(r[0])}</th>{r[1]}{r[2]}{r[3]}</tr>" for r in rows)
    out.append(f"""<div class="cmp-wrap"><table class="cmp"><thead><tr><th></th>
  <th>{chip('classic')}<div class="th-s">Clásico</div></th><th>{chip('quantum')}<div class="th-s">Cuántico (QAOA directo)</div></th>
  <th>{chip('hybrid')}<div class="th-s">Híbrido (QGate)</div></th></tr></thead><tbody>{body}</tbody></table>
  <div class="legend cmp-leg"><span><b class="m-ok">✓</b> ventaja</span><span><b class="m-no">✗</b> desventaja</span><span><b class="m-mid">~</b> parcial</span></div></div>
<p class="verdict">Hoy gana el clásico en N={ns[0] if ns else N} a {big or N}. QAOA concentra la probabilidad muy por encima del azar, incluso en hardware real con el circuito corto. El híbrido escala en memoria, todavía no en calidad.</p>
<p class="verdict" style="border-left-color:var(--mute)">QAOA concentra probabilidad respecto a su espacio de partida; en piezas de 3 vuelos aún no supera a muestrear permutaciones válidas ni a enumerar las 6 opciones.</p>""")
    return "<!--PANO:START-->" + "\n".join(out) + "<!--PANO:END-->"
