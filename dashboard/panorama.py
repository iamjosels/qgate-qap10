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
    """Versión compacta: entra en una pantalla 1440x900. Solo cifras que ya muestra el reporte."""
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
    out = []
    val = " · ".join(num(V[n]["optimum"]) for n in sorted(V) if V[n].get("ok"))
    out.append(f"""<div class="flow">
  <div class="fbox"><b>MPS qap10</b></div><div class="farr" aria-hidden="true">→</div>
  <div class="fbox"><b>F y D</b><span>{e(val)}</span></div><div class="farr" aria-hidden="true">→</div>
  <div class="flanes">{chip('classic')}{chip('quantum')}{chip('hybrid')}</div><div class="farr" aria-hidden="true">→</div>
  <div class="fbox"><b>Comparación</b></div>
</div>""")

    def col(kind, what, star, star_s, lines, goto, title=""):
        ln = "".join(f'<div class="pline">{x}</div>' for x in lines if x)
        return (f'<article class="lane lane-{kind}"{title}><div class="lane-h">{chip(kind)}</div><p class="what">{e(what)}</p>'
                f'<div class="star">{e(star)}</div><div class="star-s">{e(star_s)}</div>{ln}'
                f'<button class="goto" type="button" data-goto="{goto}">Ver detalle →</button></article>')

    cols = []
    if bf:
        cols.append(col("classic", "Busca la mejor asignación sin qubits", num(bf["cost"]), f"óptimo exacto en {sec(bf['time_s'])}",
                        [f"SA <b>{e(num(sa['cost']))}</b> en {e(sec(sa['time_s']))}" if sa else None,
                         f"cota <b>{e(num(gl['bound']))}</b>" if gl else None], "result"))
    if x4 and xy4:
        ratio = x4["p_feasible"] / x4["random_feasible_baseline"]
        cols.append(col("quantum", "QAOA en Qiskit sobre instancias pequeñas", f"×{ratio:.0f}", "más válidas que el azar (N=4)",
                        [f"XY <b>{e(pct(xy4['p_feasible']))}</b> vs {e(pct(xy4['random_feasible_baseline']))} azar",
                         f"{e(hw.get('backend'))} N=3: X <b>{e(pct(hx['feasible_fraction']))}</b> vs {e(pct(hx['random_feasible_baseline']))} azar" if hx else None],
                        "qaoa"))
    if hq:
        cols.append(col("hybrid", "QAOA de 9 qubits dentro de búsqueda clásica", str(hq.get("qubits_per_subproblem")),
                        "qubits por pieza, en cualquier N",
                        [f"8 muestras: QAOA <b>{e(pct(hq8['sub_success_rate'], 0))}</b> vs azar {e(pct(hr8['sub_success_rate'], 0))}" if hq8 and hr8 else None,
                         f"{e(num(ref))} en <b>{e(seeds.get('hits_ref'))} de {e(len(seeds.get('seeds', [])))}</b> semillas" if seeds.get("seeds") else None],
                        "airport", ' title="azar sobre los 27 estados con una puerta por vuelo; detalle y otras líneas base en la sección 05"'))
    out.append('<div class="lanes">' + "".join(cols) + "</div>")

    def cell(mark, text):
        if text is None:
            return '<td class="na"></td>'
        sym, word = MARK[mark]
        return f'<td class="m-{mark}"><span class="mk" title="{word}">{sym}</span> <span class="sr">{word}:</span> {text}</td>'

    rows = [
        ("Calidad N=10", cell("ok", f"{num(bf['cost'])}, gap {pct(gap(bf['cost']) / 100)}") if bf else cell("ok", None),
         cell("no", f"N={N}: {N * N} qubits"), cell("mid", f"{num(hq['final_cost'])} en {seeds.get('hits_ref')}/{len(seeds.get('seeds', []))} semillas") if hq and seeds else cell("mid", None)),
        ("Tiempo", cell("ok", sec(bf["time_s"])) if bf else cell("ok", None),
         cell("mid", f"{sec(xy4['time_s'])} (N=4)") if xy4 else cell("mid", None), cell("no", sec(hq["time_s"])) if hq else cell("no", None)),
        ("Qubits", cell("ok", "0"), cell("no", f"{N * N} (N={N})"), cell("ok", f"{hq.get('qubits_per_subproblem')}") if hq else cell("ok", None)),
        (f"Escala N={big}", cell("ok", f"SA {num(sa_big['gap_vs_bound_pct'], 1)}% sobre la cota") if sa_big else cell("ok", None),
         cell("no", f"{big * big} qubits") if big else cell("no", None),
         cell("mid", f"{num(hq_big['gap_vs_bound_pct'], 1)}% sobre la cota") if hq_big else cell("mid", None)),
        ("Ruido", cell("ok", "no aplica"),
         cell("no", f"XY {pct(hxy['feasible_fraction'])} vs {pct(hxy['random_feasible_baseline'])} azar ({hw.get('backend')})") if hxy else cell("no", None),
         cell("mid", "no medido")),
        ("Garantiza óptimo", cell("ok", "sí (fuerza bruta)"), cell("no", f"P(óptimo) {pct(xy4['p_optimal'])}") if xy4 else cell("no", None),
         cell("no", f"{seeds.get('hits_ref')}/{len(seeds.get('seeds', []))} semillas") if seeds.get("seeds") else cell("no", None)),
    ]
    body = "".join(f"<tr><th scope='row'>{e(r[0])}</th>{r[1]}{r[2]}{r[3]}</tr>" for r in rows)
    out.append(f"""<div class="cmp-wrap"><table class="cmp"><thead><tr><th></th><th>{chip('classic')}</th><th>{chip('quantum')}</th>
  <th>{chip('hybrid')}</th></tr></thead><tbody>{body}</tbody></table></div>
<p class="verdict">Hoy gana el clásico en N={ns[0] if ns else N} a {big or N}; QAOA concentra probabilidad sobre el azar; el híbrido escala en memoria, no en calidad.</p>""")
    return "<!--PANO:START-->" + "\n".join(out) + "<!--PANO:END-->"
