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
                       f"{g(r['gap_vs_bound_pct'], 1)} | {g(r['time_s'], 2)} | {g(r['peak_mem_mb'], 1)} | {r['qubits']} |")

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


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "results", "results.json")
    readme = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "README.md")
    with open(src, encoding="utf-8") as fh:
        R = json.load(fh)
    with open(readme, encoding="utf-8") as fh:
        txt = fh.read()
    i, j = txt.index(START), txt.index(END)
    txt = txt[:i + len(START)] + "\n" + tables(R) + "\n" + txt[j:]
    with open(readme, "w", encoding="utf-8") as fh:
        fh.write(txt)
    print(f"README actualizado desde {src}")


if __name__ == "__main__":
    main()
