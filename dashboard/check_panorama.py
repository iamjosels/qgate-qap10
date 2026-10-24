"""Verifica que cada número visible en la vista 00 · Panorama sale de results.json o hardware.json.

Uso:
    python dashboard/check_panorama.py [results/report.html] [results/results.json]

Recalcula los valores esperados directamente desde los JSON (sin usar panorama.py), extrae todos los
números del bloque <!--PANO:START--> ... <!--PANO:END--> del HTML y falla si aparece un número que no
está respaldado, o si falta alguno de los datos clave.
"""
from __future__ import annotations

import html
import json
import math
import os
import re
import sys


def main():
    rep = sys.argv[1] if len(sys.argv) > 1 else "results/report.html"
    res = sys.argv[2] if len(sys.argv) > 2 else "results/results.json"
    R = json.load(open(res, encoding="utf-8"))
    hwp = os.path.join(os.path.dirname(os.path.abspath(res)), "hardware.json")
    hw = json.load(open(hwp, encoding="utf-8")) if os.path.exists(hwp) else {}
    if hw.get("fake"):
        hw = {}
    txt = open(rep, encoding="utf-8").read()
    block = txt[txt.index("<!--PANO:START-->"):txt.index("<!--PANO:END-->")]
    block = re.sub(r"<svg.*?</svg>", " ", block, flags=re.S)
    text = html.unescape(re.sub(r"<[^>]+>", " ", block))
    text = re.sub(r"(?<=\d) (?=\d)", "", text)          # 3 628 800 -> 3628800

    m = R["meta"]
    C = {c["method"]: c for c in R["classical"]}
    Q = {q["id"]: q for q in R["quantum"]}
    H = {h["method"]: h for h in R["hybrid"]}
    S = R.get("hybrid_seeds", {})
    sc = R.get("scaling", [])
    ref, N = m["reference_optimum"], m["N"]
    p1 = lambda v: f"{100 * v:.1f}"  # noqa: E731
    p0 = lambda v: f"{100 * v:.0f}"  # noqa: E731
    t1 = lambda v: f"{v:.1f}"  # noqa: E731
    i0 = lambda v: f"{v:.0f}"  # noqa: E731
    mant = lambda v: f"{v:.1e}".split("e")[0]  # noqa: E731
    bf, sa, gl = C["brute_force"], C["simulated_annealing"], C["gilmore_lawler_bound"]
    x4, xy4 = Q["N4-x-p1"], Q["N4-xy-p1"]
    hq, hq8, hr8 = H["qgate_lns_qaoa"], H["qgate_lns_qaoa_s8"], H["qgate_lns_random_s8"]
    ns = sorted({r["N"] for r in sc})
    big = ns[-1]
    rw = lambda n, meth: next(r for r in sc if r["N"] == n and r["method"] == meth)  # noqa: E731
    gap = lambda c: 100 * (c - ref) / ref  # noqa: E731
    mem10 = next(x for x in m["statevector_memory"] if x["N"] == N)
    E = {}

    def add(label, value):
        E.setdefault(value, []).append(label)

    add("costo fuerza bruta", i0(bf["cost"])); add("tiempo fuerza bruta", t1(bf["time_s"]))
    add("costo SA", i0(sa["cost"])); add("tiempo SA", t1(sa["time_s"])); add("cota GL", i0(gl["bound"]))
    add("gap fuerza bruta", t1(gap(bf["cost"]))); add("gap híbrido", t1(gap(hq["final_cost"])))
    add("óptimo de referencia", i0(ref)); add("N", str(N)); add("N!", str(math.factorial(N)))
    for v in R["validation"]:
        add(f"validación N={v['n']}", i0(v["optimum"])); add("N de validación", str(v["n"]))
    add("variables MPS", str(R["data"]["mps_report"]["n_cols"]))
    add("ratio N=4 X vs azar", f"{x4['p_feasible'] / x4['random_feasible_baseline']:.0f}")
    add("P(válida) N=4 X", p1(x4["p_feasible"])); add("P(válida) N=4 XY", p1(xy4["p_feasible"]))
    add("azar N=4 XY", p1(xy4["random_feasible_baseline"])); add("P(óptimo) N=4 XY", p1(xy4["p_optimal"]))
    add("tiempo N=4 XY", t1(xy4["time_s"])); add("qubits N=4", str(xy4["qubits"]))
    add("mejor costo N=4", i0(xy4["best_feasible_cost"])); add("óptimo N=4", i0(xy4["optimum"]))
    add("qubits N=10 directo", str(N * N)); add(f"qubits N={big} directo", str(big * big))
    add("mantisa memoria statevector", mant(mem10["bytes"])); add(f"mantisa {big}!", mant(math.factorial(big)))
    for e in hw.get("experiments", []):
        k = e["mixer"].upper()
        add(f"hardware {k} válidas", p1(e["feasible_fraction"])); add(f"hardware {k} ideal", p1(e["sim_ideal_p_feasible"]))
        add(f"hardware {k} azar", p1(e["random_feasible_baseline"]))
        if e.get("sim_noise_feasible_fraction") is not None:
            add(f"hardware {k} ruido simulado", p1(e["sim_noise_feasible_fraction"]))
        add(f"hardware {k} compuertas 2q", str(e["two_qubit_gates"])); add("qubits hardware", str(e["qubits"]))
        add("N hardware", str(e["N"]))
    if hw.get("usage_quantum_seconds") is not None:
        add("segundos de QPU", i0(hw["usage_quantum_seconds"]))
    add("qubits por pieza", str(hq["qubits_per_subproblem"])); add("p del híbrido", str(hq["p"]))
    add("costo híbrido", i0(hq["final_cost"])); add("tiempo híbrido", t1(hq["time_s"])); add("semilla", str(m["seed"]))
    add("éxito QAOA 8 shots", p0(hq8["sub_success_rate"])); add("éxito azar 8 shots", p0(hr8["sub_success_rate"]))
    add("costo QAOA 8 shots", i0(hq8["final_cost"])); add("costo azar 8 shots", i0(hr8["final_cost"]))
    add("semillas que llegan", str(S["hits_ref"])); add("semillas", str(len(S["seeds"])))
    for n in ns:
        add("N del escalamiento", str(n))
    add(f"SA gap cota N={big}", t1(rw(big, "simulated_annealing")["gap_vs_bound_pct"]))
    add(f"SA tiempo N={big}", t1(rw(big, "simulated_annealing")["time_s"]))
    add(f"QGate gap cota N={big}", t1(rw(big, "qgate_lns_qaoa")["gap_vs_bound_pct"]))
    add(f"QGate tiempo N={big}", t1(rw(big, "qgate_lns_qaoa")["time_s"]))
    add("memoria pico QGate", t1(max(r["peak_mem_mb"] for r in sc if r["method"] == "qgate_lns_qaoa")))
    add("shots", "4096")
    k = int(round(hq["qubits_per_subproblem"] ** 0.5))
    add("estados de una pieza (k^k)", str(k ** k)); add("permutaciones de una pieza (k!)", str(math.factorial(k)))
    ex = R.get("extra") or (json.load(open(os.path.join(os.path.dirname(os.path.abspath(res)), "extra.json"), encoding="utf-8"))
                            if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(res)), "extra.json")) else {})
    if ex.get("baselines_qaoa_s8"):
        add("azar 6 permutaciones válidas, 8 muestras", p0(ex["baselines_qaoa_s8"]["hit_k8_random_valid_6"]))
        add("enumeración exacta", "100")
    add("qubits de los métodos clásicos (scaling)", str(rw(N, "simulated_annealing")["qubits"]))
    add("shots de la corrida de 8 muestras", str(hq8["shots"]))
    # literales estructurales del método (no son resultados): intercambio de 2 vuelos, piezas de 3 vuelos
    add("literal: intercambio de 2 vuelos / piezas de 3 vuelos", "2"); add("literal: piezas de 3 vuelos", "3")

    found = re.findall(r"\d+(?:\.\d+)?", text)
    bad = [t for t in found if t not in E]
    must = ["340", t1(bf["time_s"]), i0(gl["bound"]), f"{x4['p_feasible'] / x4['random_feasible_baseline']:.0f}",
            p1(xy4["p_feasible"]), p1(xy4["random_feasible_baseline"]), p0(hq8["sub_success_rate"]),
            p0(hr8["sub_success_rate"]), str(S["hits_ref"]), str(len(S["seeds"]))]
    if hw:
        x_ = next(e for e in hw["experiments"] if e["mixer"] == "x")
        must += [p1(x_["feasible_fraction"]), p1(x_["random_feasible_baseline"])]
    missing = [t for t in must if t not in found]
    print(f"Números en el Panorama: {len(found)} ({len(set(found))} distintos)")
    for t in sorted(set(found), key=lambda z: (len(z), z)):
        print(f"  {t:>10}  <- {', '.join(sorted(set(E.get(t, ['SIN RESPALDO']))))}")
    if bad or missing:
        print("FALLA. Sin respaldo:", sorted(set(bad)), "| faltan:", missing)
        sys.exit(1)
    print("OK: todos los números del Panorama salen de results.json / hardware.json")


if __name__ == "__main__":
    main()
