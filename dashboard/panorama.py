"""Vista "00 · Panorama" del dashboard: los tres enfoques (clásico, cuántico, híbrido) lado a lado y
un cuadro comparativo de ventajas y desventajas.

Todo número sale de results.json (y de hardware.json y final.json si existen) a través de R; si un dato falta, su
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
    "hybrid": None,                                   # isotipo de design/logo/, se carga abajo
}
def _logo_img(px: int = 18) -> str:
    import base64
    import os
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "design", "logo", "qgate_icono_36.png")
    with open(p, "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode("ascii")
    return f'<img src="data:image/png;base64,{b64}" width="{px}" height="{px}" alt="" aria-hidden="true" style="border-radius:3px">'


ICON["hybrid"] = _logo_img()
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


SHORTN = {"sa": "SA", "ls": "2-swap", "exact": "bloque enumeración", "exact_rand": "bloque enumeración + desempate",
          "random_valid": "bloque azar válido"}


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
    # etapa 3 (final.json): 10 semillas, todos los métodos con el mismo presupuesto; reemplaza a la corrida de 1 semilla
    Fn = R.get("final") or {}
    FS = {(x["instance"], x["solver"], x["select"]): x for x in Fn.get("summary", [])}
    finst = sorted(Fn.get("instances", []), key=lambda i: i["N"])
    fbig = finst[-1] if finst else None
    f_sa = FS.get((fbig["instance"], "sa", None)) if fbig else None
    f_q = FS.get((fbig["instance"], "qaoa", "tension")) if fbig else None
    f10 = next((i for i in finst if i["N"] == N), None)
    fq10 = FS.get((f10["instance"], "qaoa", "tension")) if f10 else None
    hits10 = (Fn.get("hits_best_found") or {}).get(f"{f10['instance']}/qaoa/tension") if f10 else None
    mv10 = ((Fn.get("attribution") or {}).get(f10["instance"], {}).get("moves_at_best_by_origin", {}).get("block")) if f10 else None
    # D5: referencia clásica = método clásico con mejor mediana en la instancia más grande; SA como segunda referencia
    order = ["ls", "exact", "exact_rand", "random_valid", "sa"]
    f_cl = min((x for x in Fn.get("summary", []) if fbig and x["instance"] == fbig["instance"] and x["solver"] != "qaoa"),
               key=lambda x: (x["cost_median"], order.index(x["solver"]) if x["solver"] in order else 9), default=None)
    out = []
    # P0.1 banner: la pregunta del reto y lo que medimos (cada cifra con su origen)
    if fbig and f_q and hq:
        names = [i["instance"] for i in finst]
        ns_ = len(Fn["meta"]["seeds"])
        dist_ = any((Fn.get("verdict", {}).get(i) or {}).get("distinguible") for i in names)
        red = [Fn.get("attribution", {}).get(i, {}).get("cost_reduction_at_best_by_origin", {}) for i in names]
        pos = sum(max(r.get("swap", 0), 0) + max(r.get("block", 0), 0) for r in red)
        share = 100 * sum(max(r.get("block", 0), 0) for r in red) / pos if pos else None
        kq = hq.get("qubits_per_subproblem")
        def src(kind, sec_, n_, file_):
            return ('<div class="q-src q-' + kind + '"><b>' + ("HARDWARE" if kind == "hw" else "SIMULADOR") + "</b> · " + e(file_) + "</div>")
        rng_n = "N=" + str(finst[0]["N"]) + " a " + str(fbig["N"])
        cards = ['<article class="q-card"><div class="q-k">Memoria</div><div class="q-big">' + e(kq) + " qubits</div>"
                 + '<div class="q-t">por bloque en cualquier N; un circuito completo serían N² qubits ('
                 + str(fbig["N"] ** 2) + " en N=" + str(fbig["N"]) + ")</div>" + src("sim", "medido y derivado · 04", rng_n, "final.json") + "</article>"]
        qual = "no distinguible" if not dist_ else "distinguible en alguna N"
        cards.append('<article class="q-card"><div class="q-k">Calidad</div><div class="q-big">' + e(qual) + '</div><div class="q-t">'
                     + ("Ningún método se distingue" if not dist_ else "Hay métodos que se distinguen")
                     + " en calidad entre " + str(ns_) + " semillas en " + str(len(names)) + " instancias"
                     + ("; los bloques QAOA aportan " + format(share, ".0f") + "% de la reducción de costo" if share is not None else "")
                     + "</div>" + src("sim", "medido y derivado · 04", rng_n, "final.json") + "</article>")
        if hxy and hx:
            cards.append('<article class="q-card"><div class="q-k">Hardware real</div><div class="q-big">' + e(pct(hxy["feasible_fraction"]))
                         + ' <span class="q-vs">vs ' + e(pct(hxy["random_feasible_baseline"])) + "</span></div>"
                         + '<div class="q-t">' + e(hw.get("backend")) + ", N=" + e(hxy["N"]) + ", un job: mixer XY válidas vs el azar de su espacio, casi igual; mixer X "
                         + e(pct(hx["feasible_fraction"])) + " vs " + e(pct(hx["random_feasible_baseline"])) + "</div>"
                         + src("hw", "medido · 05b", "N=" + str(hxy["N"]), "hardware.json") + "</article>")
        short = ("Respuesta corta: lo cuántico no mejora hoy la calidad; escala en memoria, no en calidad."
                 if not dist_ and share == 0 else "Respuesta corta: ver la pestaña 04 para el veredicto por instancia.")
        out.append('<section class="qban"><h2 class="q-question">¿Hasta dónde ayuda lo cuántico cuando los recursos son limitados?</h2>'
                   + '<div class="q-cards">' + "".join(cards) + '</div><p class="q-short">' + e(short) + "</p></section>")
    val = " · ".join(num(V[n]["optimum"]) for n in sorted(V) if V[n].get("ok"))
    val = val  # noqa: F841  (el flujo se quitó de la primera vista)

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
        cols.append(col("quantum", "QAOA en Qiskit sobre instancias pequeñas", f"×{ratio:.0f}", f"más válidas que el azar (N=4, mixer X): {pct(x4['p_feasible'])} vs {pct(x4['random_feasible_baseline'], 3)}",
                        [f"XY <b>{e(pct(xy4['p_feasible']))}</b> vs {e(pct(xy4['random_feasible_baseline']))} azar",
                         f"{e(hw.get('backend'))} N=3: X <b>{e(pct(hx['feasible_fraction']))}</b> vs {e(pct(hx['random_feasible_baseline']))} azar" if hx else None],
                        "qaoa"))
    if hq:
        cols.append(col("hybrid", "QAOA de 9 qubits dentro de búsqueda clásica", str(hq.get("qubits_per_subproblem")),
                        "qubits por pieza, en cualquier N",
                        [f"etapa 3: mediana <b>{e(num(fq10['cost_median']))}</b>, {e(hits10)}/{len(Fn['meta']['seeds'])} semillas en {e(num(f10['best_found']))}" if fq10 else None,
                         f"día 1: {e(num(hq['final_cost']))} (semilla {e(meta.get('seed'))})"],
                        "airport", ' title="azar sobre los 27 estados con una puerta por vuelo; detalle y otras líneas base en la sección 05"'))
    out.append('<div class="lanes">' + "".join(cols) + "</div>")

    def cell(mark, text):
        if text is None:
            return '<td class="na"></td>'
        sym, word = MARK[mark]
        return f'<td class="m-{mark}"><span class="mk" title="{word}">{sym}</span> <span class="sr">{word}:</span> {text}</td>'

    rows = [
        ("Calidad N=10", cell("ok", f"{num(bf['cost'])}, gap {pct(gap(bf['cost']) / 100)}") if bf else cell("ok", None),
         cell("no", f"N={N}: {N * N} qubits"), cell("mid", f"día 1: {num(hq['final_cost'])} (semilla {meta.get('seed')}); exacto {seeds.get('hits_ref')}/{len(seeds.get('seeds', []))} semillas") if hq and seeds else cell("mid", None)),
        ("Tiempo", cell("ok", sec(bf["time_s"])) if bf else cell("ok", None),
         cell("mid", f"{sec(xy4['time_s'])} (N=4)") if xy4 else cell("mid", None), cell("no", sec(hq["time_s"])) if hq else cell("no", None)),
        ("Qubits", cell("ok", "0"), cell("no", f"{N * N} (N={N})"), cell("ok", f"{hq.get('qubits_per_subproblem')}") if hq else cell("ok", None)),
        (f"Escala N={fbig['N']}",
         cell("ok", f"{SHORTN.get(f_cl['solver'], f_cl['solver'])} {num(f_cl['gap_vs_gl_median_pct'], 1)}% sobre la cota, {num(f_cl['time_median_s'])} s, "
              f"costo [{num(f_cl['cost_min'])}, {num(f_cl['cost_max'])}]"
              + (f"; SA {num(f_sa['gap_vs_gl_median_pct'], 1)}%" if f_cl['solver'] != 'sa' else "")
              + f"; {len(Fn['meta']['seeds'])} semillas, cota Gilmore-Lawler débil"),
         cell("no", f"{fbig['N'] ** 2} qubits"),
         cell("mid", f"{num(f_q['gap_vs_gl_median_pct'], 1)}% sobre la cota, {num(f_q['time_median_s'])} s, costo [{num(f_q['cost_min'])}, {num(f_q['cost_max'])}]"
              + ("" if (Fn.get("verdict", {}).get(fbig["instance"]) or {}).get("distinguible") else "; no distinguible")))
        if f_sa and f_q else
        (f"Escala N={big}", cell("ok", f"SA {num(sa_big['gap_vs_bound_pct'], 1)}% sobre la cota") if sa_big else cell("ok", None),
         cell("no", f"{big * big} qubits") if big else cell("no", None),
         cell("mid", f"{num(hq_big['gap_vs_bound_pct'], 1)}% sobre la cota") if hq_big else cell("mid", None)),
    ]
    if f_sa and f_q:
        names = [i["instance"] for i in finst]
        faster = all(FS.get((i, "sa", None)) and FS.get((i, "qaoa", "tension"))
                     and FS[(i, "sa", None)]["time_median_s"] < FS[(i, "qaoa", "tension")]["time_median_s"] for i in names)
        dist = any((Fn.get("verdict", {}).get(i) or {}).get("distinguible") for i in names)
        block0 = all(Fn.get("attribution", {}).get(i, {}).get("cost_reduction_at_best_by_origin", {}).get("block", 1) == 0 for i in names)
        verdict = (f"De N={finst[0]['N']} a {fbig['N']}: " + ("el clásico es más rápido y " if faster else "")
                   + ("ninguna diferencia de calidad es distinguible entre semillas" if not dist else "hay diferencias de calidad distinguibles (ver 04)")
                   + ("; los bloques QAOA no aportaron reducción de costo" if block0 else "")
                   + "; QAOA concentra probabilidad sobre el azar; el híbrido escala en memoria, no en calidad.")
    else:
        verdict = (f"Hoy gana el clásico en N={ns[0] if ns else N} a {big or N}; QAOA concentra probabilidad sobre el azar; "
                   "el híbrido escala en memoria, no en calidad.")
    body = "".join(f"<tr><th scope='row'>{e(r[0])}</th>{r[1]}{r[2]}{r[3]}</tr>" for r in rows)
    out.append(f"""<div class="cmp-wrap"><table class="cmp"><thead><tr><th></th><th>{chip('classic')}</th><th>{chip('quantum')}</th>
  <th>{chip('hybrid')}</th></tr></thead><tbody>{body}</tbody></table></div>
<p class="q-op"><b>Conclusión operativa.</b> Una búsqueda local clásica llega a buenas asignaciones en segundos; lo cuántico aún no se justifica por calidad ni por tiempo. Datos de un benchmark (qap10), unidades supuestas.</p>""")
    return "<!--PANO:START-->" + "\n".join(out) + "<!--PANO:END-->"
