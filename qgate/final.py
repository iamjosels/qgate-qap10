"""Etapa 3 del reto (final): escalamiento N >= 14 con el híbrido en dos fases. Escribe results/final.json.

Uso:
    python -m qgate.final --mps data/qap10.mps.gz --sizes 14,16,20 --seeds 5 --blocks 100 --shots 8 --procs 14
    python -m qgate.final ... --official F.npy D.npy        # agrega una instancia oficial (rotulada así)
    python -m qgate.final ... --estimate                    # solo mide y estima el tiempo, no corre la matriz

Matriz: por instancia y semilla, (a) SA y, con selector random y tension, los solvers de bloque del modo
dos fases: (b) ls = búsqueda 2-swap con reinicios, (c) exact, (d) random_valid, (e) exact_rand, (f) qaoa.
Mismo presupuesto B, semilla y arranque para todos. Instancias N>10 sintéticas salvo las oficiales.
No toca results.json, hardware.json ni extra.json.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import platform
import statistics as st
import sys
import time
import tracemalloc

import numpy as np

SOLVERS = ["ls", "exact", "random_valid", "exact_rand", "qaoa"]
SELECTS = ["random", "tension"]


def _versions():
    v = {"python": platform.python_version(), "numpy": np.__version__}
    for m in ("scipy", "qiskit", "qiskit_aer"):
        try:
            v[m] = __import__(m).__version__
        except Exception:
            v[m] = None
    return v


def _job(args):
    kind, inst, label, origen, seed, start, solver, select, B, shots, sa_iters = args
    if kind == "sa":
        from .classical import simulated_annealing
        tracemalloc.start()
        t = time.perf_counter()
        r = simulated_annealing(inst, iters=sa_iters, restarts=3, seed=seed, start=start)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        return {"instance": label, "origen": origen, "N": inst.N, "solver": "sa", "select": None, "seed": seed,
                "best_cost": float(r["cost"]), "feasible": sorted(r["perm"]) == list(range(inst.N)),
                "time_s": time.perf_counter() - t, "peak_mem_mb": peak / 1e6, "sa_iters": sa_iters, "sa_restarts": 3}
    from .twophase import two_phase
    r = two_phase(inst, solver=solver, select=select, B=B, seed=seed, start_perm=start, shots=shots)
    r.pop("history", None)
    r.pop("best_perm", None)
    return {"instance": label, "origen": origen, **r}


def _instances(a):
    from .instance import QAPInstance
    from .mps import recover_qap
    out = []
    if a.mps:
        rec = recover_qap(a.mps, name="qap10")
        R = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "results.json"), encoding="utf-8"))
        out.append((rec.candidates[R["data"]["index_strategy"]], "qap10", "oficial (qap10)"))
    for n in [int(x) for x in a.sizes.split(",") if x.strip()]:
        out.append((QAPInstance.synthetic(n, seed=a.seed0 + n), f"synthetic-{n}", "sintética"))
    if a.official:
        from .loader import load_official
        inst, rep = load_official(*a.official)
        out.append((inst, rep["name"], "oficial"))
    return out


def summarize(rows, gl, best_found):
    groups = {}
    for r in rows:
        groups.setdefault((r["instance"], r["solver"], r["select"]), []).append(r)
    summ = []
    for (inst, solver, select), rs in sorted(groups.items(), key=lambda kv: (kv[0][0], SOLVERS.index(kv[0][1]) if kv[0][1] in SOLVERS else -1, str(kv[0][2]))):
        c = [r["best_cost"] for r in rs]
        b = gl[inst]
        bf = best_found[inst]
        row = {"instance": inst, "origen": rs[0]["origen"], "N": rs[0]["N"], "solver": solver, "select": select, "seeds": len(rs),
               "cost_median": st.median(c), "cost_min": min(c), "cost_max": max(c),
               "gap_vs_gl_median_pct": 100 * (st.median(c) - b) / b if b else None,
               "gap_vs_best_found_median_pct": 100 * (st.median(c) - bf) / bf if bf else None,
               "gap_vs_best_found_min_pct": 100 * (min(c) - bf) / bf if bf else None,
               "gap_vs_best_found_max_pct": 100 * (max(c) - bf) / bf if bf else None,
               "time_median_s": st.median(r["time_s"] for r in rs), "peak_mem_median_mb": st.median(r["peak_mem_mb"] for r in rs),
               "feasible_rate": sum(1 for r in rs if r["feasible"]) / len(rs)}
        if solver not in ("sa", "ls"):
            row["blocks_tried_median"] = st.median(r["blocks_tried"] for r in rs)
            row["block_improve_rate_mean"] = st.mean(r["block_improve_rate_from_local_opt"] or 0 for r in rs)
        if solver == "qaoa":
            row["evals_per_block_mean"] = st.mean(r["qaoa"]["evals_per_block"] for r in rs)
            row["p_opt_block_mean"] = st.mean(r["qaoa"]["p_opt_mean"] for r in rs)
            row["frac_wall_in_qaoa_mean"] = st.mean(r["qaoa"]["frac_wall_in_qaoa"] for r in rs)
            row["frac_wall_in_aer_mean"] = st.mean(r["qaoa"]["frac_wall_in_aer"] for r in rs)
            row["fallback_cold_total"] = sum(r["qaoa"]["fallback_cold"] for r in rs)
        summ.append(row)
    # distinguible: el mejor por mediana solo se marca si su máximo queda por debajo del mínimo de todos los demás
    verdict = {}
    for inst in {s["instance"] for s in summ}:
        ss = [s for s in summ if s["instance"] == inst]
        top = min(ss, key=lambda s: s["cost_median"])
        others = [s for s in ss if s is not top]
        disting = all(top["cost_max"] < o["cost_min"] for o in others)
        verdict[inst] = {"best_median": f"{top['solver']}/{top['select']}", "distinguible": disting,
                         "ties_at_best_median": sorted(f"{s['solver']}/{s['select']}" for s in ss if s["cost_median"] == top["cost_median"])}
    return summ, verdict


def attribution(rows):
    """F6: atribución cuántico vs clásico para el híbrido QAOA (y tasa de mejora de bloques por solver)."""
    out = {}
    for inst in sorted({r["instance"] for r in rows}):
        q = [r for r in rows if r["instance"] == inst and r["solver"] == "qaoa"]
        if not q:
            continue
        n = q[0]["N"]
        mv = {o: sum(r["origin_at_best"][o]["moves"] for r in q) for o in ("swap", "block", "kick")}
        red = {o: sum(r["origin_at_best"][o]["reduction"] for r in q) for o in ("swap", "block", "kick")}
        tot = sum(red.values())
        rates = {}
        for s in ("exact", "random_valid", "exact_rand", "qaoa"):
            rs = [r for r in rows if r["instance"] == inst and r["solver"] == s]
            tried = sum(r["blocks_tried"] for r in rs)
            rates[s] = {"blocks_tried": tried, "blocks_improved": sum(r["blocks_improved"] for r in rs),
                        "rate": (sum(r["blocks_improved"] for r in rs) / tried) if tried else None}
        out[inst] = {"N": n, "runs": len(q),
                     "variables_quantum_frac": 9 / (n * n),
                     "moves_at_best_by_origin": mv,
                     "cost_reduction_at_best_by_origin": red,
                     "cost_reduction_share": {o: (red[o] / tot if tot else None) for o in red},
                     "frac_wall_in_qaoa_mean": st.mean(r["qaoa"]["frac_wall_in_qaoa"] for r in q),
                     "frac_wall_in_aer_mean": st.mean(r["qaoa"]["frac_wall_in_aer"] for r in q),
                     "block_improve_rate_from_local_opt": rates}
    return out


def angle_reuse(inst, seed=7, n_blocks=40, shots=8):
    """F4: mismos bloques (tomados de una trayectoria exacta con selector tension), QAOA con arranque
    frío vs con los ángulos del bloque anterior. Mide evaluaciones, tiempo y P(óptimo) del bloque."""
    from .hybrid import build_subproblem
    from .quantum import solve_subproblem_qaoa
    from .twophase import two_phase, PERMS3
    log = []
    two_phase(inst, solver="exact", select="tension", B=n_blocks, seed=seed, shots=shots, block_log=log)
    res = {"cold": [], "warm": []}
    warm = None
    for i, b in enumerate(log):
        sub = build_subproblem(inst, np.array(b["perm_before"]), b["elems"])
        for mode in ("cold", "warm"):
            t = time.perf_counter()
            _, params, info = solve_subproblem_qaoa(sub, p=2, shots=shots, seed=seed * 1000 + i,
                                                     init_params=(warm if mode == "warm" else None), maxiter=40)
            res[mode].append({"evals": info["evals"], "time_s": time.perf_counter() - t, "p_optimal": info["p_optimal"],
                              "p_feasible": info["p_feasible"]})
            if mode == "warm":
                warm = params
    agg = {m: {"blocks": len(v), "evals_mean": st.mean(x["evals"] for x in v), "time_mean_s": st.mean(x["time_s"] for x in v),
               "p_optimal_mean": st.mean(x["p_optimal"] for x in v), "p_feasible_mean": st.mean(x["p_feasible"] for x in v)}
           for m, v in res.items()}
    return {"instance": inst.name, "N": inst.N, "seed": seed, "shots": shots, **agg}


def main(argv=None):
    for s_ in (sys.stdout, sys.stderr):
        try:
            s_.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--mps", default="data/qap10.mps.gz")
    ap.add_argument("--sizes", default="14,16,20")
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--seed0", type=int, default=7)
    ap.add_argument("--blocks", type=int, default=100)
    ap.add_argument("--shots", type=int, default=8)
    ap.add_argument("--sa-iters", type=int, default=50000)
    ap.add_argument("--procs", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    ap.add_argument("--official", nargs="*")
    ap.add_argument("--estimate", action="store_true")
    ap.add_argument("--out", default="results/final.json")
    a = ap.parse_args(argv)
    os.environ.setdefault("OMP_NUM_THREADS", "1")       # una semilla por proceso, sin sobresuscribir hilos
    from multiprocessing import Pool
    from .classical import gilmore_lawler_bound
    insts = _instances(a)
    seeds = list(range(a.seed0, a.seed0 + a.seeds))
    jobs = []
    for inst, label, origen in insts:
        for sd in seeds:
            start = np.random.default_rng(sd + 100).permutation(inst.N)
            jobs.append(("sa", inst, label, origen, sd, start, "sa", None, a.blocks, a.shots, a.sa_iters))
            for sel in SELECTS:
                for sv in SOLVERS:
                    jobs.append(("tp", inst, label, origen, sd, start, sv, sel, a.blocks, a.shots, a.sa_iters))
    t0 = time.perf_counter()
    if a.estimate:
        # piloto: una corrida QAOA y una SA del N más grande con B reducido, luego extrapola
        big = max(insts, key=lambda x: x[0].N)
        pb = max(5, a.blocks // 10)
        t = time.perf_counter(); _job(("tp", big[0], big[1], big[2], seeds[0], None, "qaoa", "tension", pb, a.shots, a.sa_iters)); tq = (time.perf_counter() - t) / pb
        t = time.perf_counter(); _job(("sa", big[0], big[1], big[2], seeds[0], None, "sa", None, pb, a.shots, a.sa_iters // 10)); tsa = (time.perf_counter() - t) * 10
        nq = sum(1 for j in jobs if j[6] == "qaoa")
        cpu = nq * tq * a.blocks + sum(1 for j in jobs if j[0] == "sa") * tsa + (len(jobs) - nq) * 3
        print(json.dumps({"jobs": len(jobs), "qaoa_jobs": nq, "s_per_qaoa_block_maxN": tq, "s_per_sa_run_maxN": tsa,
                          "cpu_s_upper_bound": cpu, "wall_min_estimate": cpu / a.procs / 60, "procs": a.procs}, indent=1))
        return
    print(f"{len(jobs)} corridas en {a.procs} procesos...", flush=True)
    with Pool(a.procs) as pool:
        rows = []
        for i, r in enumerate(pool.imap_unordered(_job, jobs, chunksize=1), 1):
            rows.append(r)
            if i % 20 == 0:
                print(f"  {i}/{len(jobs)} ({time.perf_counter() - t0:.0f} s)", flush=True)
    gl = {label: gilmore_lawler_bound(inst)["bound"] for inst, label, _ in insts}
    best_found = {label: min(r["best_cost"] for r in rows if r["instance"] == label) for _, label, _ in insts}
    summ, verdict = summarize(rows, gl, best_found)
    attr = attribution(rows)
    big = max(insts, key=lambda x: x[0].N)[0]
    ar = angle_reuse(big)
    out = {"meta": {"generated_at": dt.datetime.now().isoformat(timespec="seconds"), "command": "python -m qgate.final " + " ".join(argv or sys.argv[1:]),
                    "seeds": seeds, "blocks_B": a.blocks, "shots": a.shots, "sa_iters": a.sa_iters, "sa_restarts": 3, "procs": a.procs,
                    "wall_s": time.perf_counter() - t0, "versions": _versions(), "entorno": "SIMULADOR (Qiskit Aer) y CPU",
                    "nota_tiempos": f"tiempos medidos con {a.procs} procesos en paralelo; comparables entre métodos de la misma corrida",
                    "solvers": {"sa": "simulated annealing (referencia clásica, presupuesto propio)", "ls": "búsqueda 2-swap con reinicios",
                                "exact": "bloque k=3 por enumeración", "random_valid": f"bloque: {a.shots} muestras de las 6 permutaciones válidas",
                                "exact_rand": "bloque: enumeración con desempate aleatorio entre mejoras", "qaoa": f"bloque: QAOA p=2 XY, {a.shots} shots, ángulos reutilizados con respaldo frío"}},
           "instances": [{"instance": label, "origen": origen, "N": inst.N, "gl_bound": gl[label], "best_found": best_found[label]} for inst, label, origen in insts],
           "summary": summ, "verdict": verdict, "attribution": attr, "angle_reuse": ar, "runs": rows}
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    json.dump(out, open(a.out, "w", encoding="utf-8"), indent=1, ensure_ascii=False, default=float)
    print(f"Guardado {a.out} en {time.perf_counter() - t0:.0f} s")


if __name__ == "__main__":
    main()
