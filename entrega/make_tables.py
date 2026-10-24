"""Inserta en README.md las tablas de resultados generadas desde results/results.json.

Uso:
    python entrega/make_tables.py [results/results.json] [README.md]

Reemplaza el bloque entre <!-- RESULTS:START --> y <!-- RESULTS:END -->.
"""
from __future__ import annotations

import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
START, END = "<!-- RESULTS:START -->", "<!-- RESULTS:END -->"
FSTART, FEND = "<!-- FINDINGS:START -->", "<!-- FINDINGS:END -->"


def g(x, d=None):
    if x is None:
        return "-"
    return f"{x:g}" if d is None else f"{x:.{d}f}"


def fp(x):
    if x is None:
        return "-"
    return f"{x:.3f}" if x >= 0.1 else f"{x:.2g}"


def tables(R: dict) -> str:
    meta, ref = R["meta"], R["meta"]["reference_optimum"]
    out = []
    out.append("### Validación de escala\n")
    out.append("| N | Óptimo calculado | Esperado | OK | Tiempo (s) |\n|---|---|---|---|---|")
    for v in R["validation"]:
        out.append(f"| {v['n']} | {g(v['optimum'])} | {g(v['expected'])} | {'sí' if v['ok'] else 'no'} | {g(v['time_s'], 3)} |")

    out.append("\n### Instancia completa N = 10 (gap solo sobre asignaciones válidas)\n")
    out.append("| Método | Costo | Gap vs 340 (%) | Tiempo (s) | Notas |\n|---|---|---|---|---|")
    for c in R["classical"]:
        if c["method"] == "brute_force":
            out.append(f"| Fuerza bruta (10! permutaciones) | {g(c['cost'])} | {g(c['gap_pct'], 1)} | {g(c['time_s'], 1)} | {c.get('n_optimal_perms', '-')} óptimo(s) |")
        elif c["method"] == "simulated_annealing":
            out.append(f"| Simulated annealing | {g(c['cost'])} | {g(c['gap_pct'], 1)} | {g(c['time_s'], 1)} | clásico puro |")
        elif c["method"] == "gilmore_lawler_bound":
            out.append(f"| Cota Gilmore-Lawler | {g(c['bound'])} (cota inferior) | - | {g(c['time_s'], 3)} | no es una asignación |")
    for h in R["hybrid"]:
        if h["method"] == "qgate_lns_qaoa":
            out.append(f"| **QGate híbrido (QAOA p={h['p']}, 9 qubits, {h['shots']} shots)** crudo | **{g(h['final_cost'])}** | "
                       f"{g(h['gap_pct'], 1)} | {g(h['time_s'], 1)} | {h['iters']} iteraciones, {h['subproblems']} subproblemas |")
            if h.get("polished_cost") is not None:
                out.append(f"| QGate híbrido + pulido 2-swap (clásico) | {g(h['polished_cost'])} | {g(h['polished_gap_pct'], 1)} | - | reportado aparte del crudo |")
        elif h["method"] == "qgate_lns_exact":
            out.append(f"| QGate con subproblema exacto (control) | {g(h['final_cost'])} | {g(h['gap_pct'], 1)} | {g(h['time_s'], 2)} | mismo presupuesto, semilla y arranque |")
    rnd = next((a for a in R.get("assignments", []) if a["label"] == "Aleatoria"), None)
    if rnd:
        out.append(f"| Asignación aleatoria | {g(rnd['cost'])} | {g(100 * (rnd['cost'] - ref) / ref, 1)} | - | referencia |")
    abl = [h for h in R["hybrid"] if h["method"].startswith("qgate_lns")]
    if abl:
        out.append("\n### Ablación del solver del subproblema (mismas iteraciones, semilla y arranque)\n")
        out.append("| Solver | Shots | Costo final | Gap (%) | Éxito en subproblemas | P(óptimo) medio por subproblema | Azar P(óptimo) | Tiempo (s) |")
        out.append("|---|---|---|---|---|---|---|---|")
        for h in abl:
            pm = h.get("qaoa_p_optimal_mean") if h.get("solver") == "qaoa" else (
                h.get("random_p_optimal_mean") if h.get("solver") == "random" else 1.0)
            out.append(f"| {h['label']} | {h.get('shots') or '-'} | {g(h['final_cost'])} | {g(h['gap_pct'], 1)} | "
                       f"{g(100 * h['sub_success_rate'], 0)}% | {fp(pm)} | {fp(h.get('random_p_optimal_mean'))} | {g(h['time_s'], 1)} |")
        out.append("\n*Éxito = el solver devolvió el óptimo del subproblema (sin muestra válida cuenta como fallo). "
                   "Azar = muestras uniformes sobre los estados con una puerta por vuelo (el mismo espacio que el estado W).*")
    S = R.get("hybrid_seeds")
    if S:
        out.append(f"\nRobustez (solver exacto, {S['iters']} iteraciones, semillas {S['seeds'][0]} a {S['seeds'][-1]}): "
                   f"media {g(S['mean'], 1)} (gap medio {g(S['mean_gap_pct'], 1)}%), mejor {g(S['best'])}, peor {g(S['worst'])}, "
                   f"llega a {g(ref)} en {S['hits_ref']} de {len(S['seeds'])}.")

    out.append("\n### QAOA en subinstancias (Qiskit Aer)\n")
    out.append("| Experimento | Qubits | Mixer | p | Ruido | P(válida) ideal | Válidas en shots | Azar | P(óptimo) | Mejor costo | Ratio medio | Tiempo (s) | CX | Profundidad |")
    out.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for q in R["quantum"]:
        out.append(f"| {q['id']} | {q['qubits']} | {q['mixer'].upper()} | {q['p']} | {q['noise'].replace('depolarizing', 'desp.')} | "
                   f"{fp(q['p_feasible'])} | {fp(q['feasible_fraction_shots'])} | {fp(q['random_feasible_baseline'])} | {fp(q['p_optimal'])} | "
                   f"{g(q['best_feasible_cost'])} (ópt {g(q['optimum'])}) | {g(q.get('mean_approx_ratio'), 3)} | {g(q['time_s'], 1)} | "
                   f"{q.get('cx_count', '-')} | {q.get('depth', '-')} |")
    out.append("\n*Ratio medio = óptimo / costo medio de las muestras válidas. Azar: para mixer X es la fracción de "
               "bitstrings válidos; para XY, la fracción válida entre estados con una puerta por vuelo.*")

    L = R.get("lambda_sweep", [])
    if L:
        out.append("\n### Barrido de λ (N = 3, p = 1)\n")
        facs = sorted({r["lam_factor"] for r in L})
        out.append("| Mixer | " + " | ".join(f"λ0×{f:g}" for f in facs) + " |")
        out.append("|---|" + "---|" * len(facs))
        for m in ("x", "xy"):
            row = {r["lam_factor"]: r for r in L if r["mixer"] == m}
            if row:
                out.append(f"| {m.upper()} P(válida) / P(óptimo) | " +
                           " | ".join(f"{fp(row[f]['p_feasible'])} / {fp(row[f]['p_optimal'])}" if f in row else "-" for f in facs) + " |")

    sc = R.get("scaling", [])
    if sc:
        out.append("\n### Escalamiento (N > 10 son instancias sintéticas)\n")
        out.append("| N | Instancia | Método | Costo | Cota GL | Gap vs cota (%) | Tiempo (s) | Memoria pico (MB) | Qubits |")
        out.append("|---|---|---|---|---|---|---|---|---|")
        names = {"simulated_annealing": "SA", "qgate_lns_exact": "QGate exacto", "qgate_lns_qaoa": "QGate QAOA"}
        for r in sc:
            out.append(f"| {r['N']} | {r['instance']} | {names.get(r['method'], r['method'])} | {g(r['best_cost'])} | {g(r['lower_bound'])} | "
                       f"{g(r['gap_vs_bound_pct'], 1)} | {g(r['time_s'], 2)} | {g(r['peak_mem_mb'], 2)} | {r['qubits']} |")

    hw = R.get("hardware")
    if hw and hw.get("experiments"):
        out.append(f"\n### IBM Quantum real · {hw['backend']} (job `{hw['job_id']}`)\n")
        out.append("| Experimento | Qubits | Válidas en hardware | Ideal (Aer) | Aer con ruido 1% | Azar | P(óptimo) | Mejor costo | Profundidad | Compuertas 2q |")
        out.append("|---|---|---|---|---|---|---|---|---|---|")
        for e in hw["experiments"]:
            out.append(f"| {e['id']} | {e['qubits']} | **{fp(e['feasible_fraction'])}** | {fp(e['sim_ideal_p_feasible'])} | "
                       f"{fp(e.get('sim_noise_feasible_fraction'))} | {fp(e['random_feasible_baseline'])} | {fp(e['p_optimal'])} | "
                       f"{g(e['best_feasible_cost'])} (ópt {g(e['optimum'])}) | {e.get('depth', '-')} | {e.get('two_qubit_gates', '-')} |")
        out.append(f"\n*{hw['experiments'][0]['shots']} shots por circuito, ángulos optimizados en el simulador, circuito transpilado "
                   f"para {hw['backend']}" + (f"; {g(hw['usage_quantum_seconds'])} s de QPU" if hw.get("usage_quantum_seconds") else "")
                   + ". Resultado de hardware, separado del resto (simulador).*")
    M = meta.get("statevector_memory")
    if M:
        out.append("\n### Memoria de un statevector genérico (16 bytes por amplitud)\n")
        out.append("| N | Qubits (N²) | Memoria |\n|---|---|---|")
        for m in M:
            b = m["bytes"]
            human = next((f"{b / 1024 ** i:g} {u}" for i, u in enumerate(("B", "KiB", "MiB", "GiB", "TiB"))
                          if b < 1024 ** (i + 1)), f"{b:.2e} B")
            out.append(f"| {m['N']} | {m['qubits']} | {human} |")
    v = meta["versions"]
    out.append(f"\n*Generado {meta['generated_at']} · semilla {meta['seed']} · Python {v.get('python')}, Qiskit {v.get('qiskit')}, "
               f"Qiskit Aer {v.get('qiskit_aer')}, NumPy {v.get('numpy')}, SciPy {v.get('scipy')} · "
               f"corrida total {g(meta['total_time_s'] / 60, 1)} min.*")
    return "\n".join(out)


def _scale_iters(meta: dict) -> int:
    """Iteraciones del híbrido en el escalamiento (bench: max(H // 2, 40))."""
    a = meta.get("args", {})
    H = a.get("hybrid_iters") or (120 if a.get("quick") else 300)
    return max(H // 2, 40)


def findings(R: dict) -> str:
    """Lectura de resultados en prosa; cada número sale del JSON."""
    meta, ref = R["meta"], R["meta"]["reference_optimum"]
    Q = {q["id"]: q for q in R["quantum"]}
    H = {h["method"]: h for h in R["hybrid"]}
    C = {c["method"]: c for c in R["classical"]}
    v = {x["n"]: x for x in R["validation"]}
    out = [f"1. **Datos.** La reconstrucción del MPS reproduce los óptimos de control: N=3 → {g(v[3]['optimum'])}, "
           f"N=4 → {g(v[4]['optimum'])}, N=10 → {g(v[meta['N']]['optimum'])}."]
    x4, xy4 = Q.get("N4-x-p1"), Q.get("N4-xy-p1")
    if x4 and xy4:
        out.append(f"2. **QAOA directo (N=4, 16 qubits).** Con mixer X, P(válida) = {fp(x4['p_feasible'])} frente a "
                   f"{fp(x4['random_feasible_baseline'])} del azar ({x4['p_feasible'] / x4['random_feasible_baseline']:.0f} veces). "
                   f"Con mixer XY + estado W, {fp(xy4['p_feasible'])} frente a {fp(xy4['random_feasible_baseline'])} "
                   f"(azar sobre estados con una puerta por vuelo). "
                   + (f"El mejor costo muestreado es el óptimo ({g(xy4['optimum'])}) en ambos, pero "
                      if x4["best_feasible_cost"] == x4["optimum"] and xy4["best_feasible_cost"] == xy4["optimum"]
                      else f"Mejor costo muestreado: {g(x4['best_feasible_cost'])} y {g(xy4['best_feasible_cost'])} (óptimo {g(xy4['optimum'])}); ")
                   + f"P(óptimo) es baja ({fp(x4['p_optimal'])} y {fp(xy4['p_optimal'])}): QAOA p=1 concentra poco.")
    nx, nxy = Q.get("N3-x-p1-noise0.01"), Q.get("N3-xy-p1-noise0.01")
    if nx and nxy:
        out.append(f"3. **Ruido.** Con ruido despolarizante de 1%, la fracción válida del mixer XY cae de {fp(nxy['p_feasible'])} a "
                   f"{fp(nxy['feasible_fraction_shots'])} (su azar es {fp(nxy['random_feasible_baseline'])}); la del mixer X, de "
                   f"{fp(nx['p_feasible'])} a {fp(nx['feasible_fraction_shots'])}. La ventaja estructural de XY es frágil al ruido.")
    hq, he, hr = H.get("qgate_lns_qaoa"), H.get("qgate_lns_exact"), H.get("qgate_lns_random")
    hq8, hr8 = H.get("qgate_lns_qaoa_s8"), H.get("qgate_lns_random_s8")
    if hq:
        txt = (f"4. **Híbrido N=10.** Con la semilla {meta['seed']}, QGate con QAOA ({hq['shots']} shots) termina en "
               f"**{g(hq['final_cost'])}** (gap {g(hq['gap_pct'], 1)}%) en {g(hq['time_s'], 0)} s.")
        if he and hr:
            txt += (f" El control exacto termina en {g(he['final_cost'])} y el azar con las mismas {hr['shots']} muestras en "
                    f"{g(hr['final_cost'])}: con piezas de 3 vuelos (6 asignaciones) y {hq['shots']} muestras, el azar también "
                    f"encuentra el óptimo de cada pieza.")
        out.append(txt)
        out.append(f"5. **Qué aporta QAOA.** P(óptimo) medio por subproblema: {fp(hq['qaoa_p_optimal_mean'])} con QAOA p={hq['p']} "
                   f"frente a {fp(hq['random_p_optimal_mean'])} del azar "
                   f"({hq['qaoa_p_optimal_mean'] / hq['random_p_optimal_mean']:.1f} veces)."
                   + (f" Con solo 8 shots, QAOA resuelve el {g(100 * hq8['sub_success_rate'], 0)}% de los subproblemas y el azar el "
                      f"{g(100 * hr8['sub_success_rate'], 0)}%; el costo final es {g(hq8['final_cost'])} frente a {g(hr8['final_cost'])}."
                      if hq8 and hr8 else ""))
    S = R.get("hybrid_seeds")
    if S:
        out.append(f"6. **Robustez.** En {len(S['seeds'])} semillas y arranques, el mismo marco con solver exacto (equivale a QAOA "
                   f"cuando QAOA acierta) llega a {g(ref)} en {S['hits_ref']} y su media es {g(S['mean'], 1)} "
                   f"(gap medio {g(S['mean_gap_pct'], 1)}%). El límite es el vecindario de 3 vuelos, no el solver.")
    bf, sa = C.get("brute_force"), C.get("simulated_annealing")
    if bf and sa and hq:
        out.append(f"7. **Tiempo.** En simulador, lo clásico gana: fuerza bruta {g(bf['time_s'], 1)} s y simulated annealing "
                   f"{g(sa['time_s'], 1)} s llegan a {g(bf['cost'])}; el híbrido con QAOA tarda {g(hq['time_s'], 0)} s. "
                   f"No afirmamos ventaja cuántica.")
    hw = R.get("hardware")
    if hw and hw.get("experiments"):
        parts = [f"{e['id']}: {fp(e['feasible_fraction'])} válidas (ideal {fp(e['sim_ideal_p_feasible'])}, azar {fp(e['random_feasible_baseline'])})"
                 for e in hw["experiments"]]
        out.append(f"9. **Hardware real.** Una corrida N=3 (9 qubits) en {hw['backend']} de IBM Quantum: " + "; ".join(parts) + ".")
    sc = [r for r in R.get("scaling", []) if r["method"] == "qgate_lns_qaoa"]
    if sc:
        ns = sorted(r["N"] for r in sc)
        mem = max(r["peak_mem_mb"] for r in sc)
        big = ns[-1]
        allsc = R.get("scaling", [])
        qb = next(r for r in allsc if r["N"] == big and r["method"] == "qgate_lns_qaoa")
        sb = next((r for r in allsc if r["N"] == big and r["method"] == "simulated_annealing"), None)
        out.append(f"8. **Escala.** De N={ns[0]} a N={big} el subproblema cuántico sigue en 9 qubits y la memoria pico de "
                   f"QGate no pasa de {g(mem, 1)} MB; un QUBO directo de N={big} serían {big ** 2} qubits."
                   + (f" Con {qb.get('iters') or _scale_iters(meta)} iteraciones, en N={big} el híbrido queda a {g(qb['gap_vs_bound_pct'], 1)}% "
                      f"de la cota y SA a {g(sb['gap_vs_bound_pct'], 1)}%: con N grande, 3 vuelos por paso es un vecindario chico. "
                      if sb else " ")
                   + "Las diferencias entre QAOA y el control exacto en esta tabla vienen de empates entre permutaciones "
                     "óptimas del subproblema y de mejoras no óptimas que cambian la trayectoria; no son ventaja de QAOA.")
    return "\n".join(out)


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "results", "results.json")
    readme = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "README.md")
    with open(src, encoding="utf-8") as fh:
        R = json.load(fh)
    hwp = os.path.join(os.path.dirname(os.path.abspath(src)), "hardware.json")
    if os.path.exists(hwp):
        with open(hwp, encoding="utf-8") as fh:
            H = json.load(fh)
        if not H.get("fake"):
            R["hardware"] = H
    with open(readme, encoding="utf-8") as fh:
        txt = fh.read()
    i, j = txt.index(START), txt.index(END)
    txt = txt[:i + len(START)] + "\n" + tables(R) + "\n" + txt[j:]
    if FSTART in txt:
        i, j = txt.index(FSTART), txt.index(FEND)
        txt = txt[:i + len(FSTART)] + "\n" + findings(R) + "\n" + txt[j:]
    with open(readme, "w", encoding="utf-8") as fh:
        fh.write(txt)
    print(f"README actualizado desde {src}")


if __name__ == "__main__":
    main()
