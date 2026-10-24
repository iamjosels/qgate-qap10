"""Benchmark completo de QGate. Genera results/results.json, gráficos PNG y report.html.

Uso:
    python -m qgate.bench --mps qap10.mps.gz                 # instancia real
    python -m qgate.bench --mps qap10.mps.gz --quick         # versión rápida (~3-5 min)
    python -m qgate.bench --synthetic 10                     # prueba sin el archivo real
    python -m qgate.bench --mps qap10.mps.gz --scale 10,12,14,16
    python -m qgate.bench --mps qap10.mps.gz --scale-files inst14.dat inst16.dat
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import platform
import sys
import time
import tracemalloc

import numpy as np

from .instance import QAPInstance, mds_2d
from .classical import (brute_force, simulated_annealing, gilmore_lawler_bound,
                        random_assignment)
from .hybrid import qgate_lns
from .qubo import lambda_auto


def _jsonable(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (set, tuple)):
        return list(o)
    raise TypeError(type(o))


def _versions():
    v = {"python": platform.python_version(), "numpy": np.__version__}
    for mod in ("scipy", "qiskit", "qiskit_aer"):
        try:
            v[mod] = __import__(mod).__version__
        except Exception:
            v[mod] = None
    return v


def log(msg):
    print(f"[{dt.datetime.now():%H:%M:%S}] {msg}", flush=True)


def gap(c, ref):
    return None if (ref is None or c is None) else 100.0 * (c - ref) / ref


# --------------------------------------------------------------------- carga
def load_instance(args):
    report, cand_table = {}, []
    if args.mps:
        from .mps import recover_qap
        rec = recover_qap(args.mps, name=os.path.basename(args.mps).split(".")[0])
        report = rec.report
        log(f"MPS: {report}")
        chosen = None
        for tag, cand in rec.candidates.items():
            row = {"strategy": tag}
            for n, exp in zip((3, 4), args.expect[:2]):
                row[f"opt_N{n}"] = brute_force(cand.subinstance(n))["cost"]
                row[f"expected_N{n}"] = exp
            row["match"] = all(abs(row[f"opt_N{n}"] - e) < 1e-6
                               for n, e in zip((3, 4), args.expect[:2]))
            cand_table.append(row)
            log(f"  candidata {tag}: {row}")
            if row["match"] and chosen is None:
                chosen = cand
        if chosen is None:
            log("ATENCIÓN: ninguna candidata reproduce los óptimos de control; uso la primera "
                "y lo reporto como limitación. Revisen el orden de índices.")
            chosen = rec.instance
        inst = chosen
    elif args.fd:
        inst = QAPInstance.from_matrices_file(args.fd)
    else:
        inst = QAPInstance.synthetic(args.synthetic, seed=args.seed)
        args.expect = [None, None, None]
    return inst, report, cand_table


# -------------------------------------------------------------------- bench
def main(argv=None):
    for stream in (sys.stdout, sys.stderr):   # consola de Windows (cp1252) no imprime λ
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="QGate benchmark")
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--mps", help="ruta a qap10.mps.gz")
    src.add_argument("--fd", help=".npz con F y D")
    src.add_argument("--synthetic", type=int, default=10)
    ap.add_argument("--expect", default="24,32,340",
                    help="óptimos de control N=3,N=4,N completo")
    ap.add_argument("--out", default="results")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--skip-bf", action="store_true", help="no correr fuerza bruta en N completo")
    ap.add_argument("--hybrid-iters", type=int, default=None)
    ap.add_argument("--scale", default="10,12,14,16",
                    help="N para la prueba de escalabilidad (sintéticas si N != N real)")
    ap.add_argument("--scale-files", nargs="*", default=[],
                    help="instancias N>=14 (formato QAPLIB .dat o .npz con F,D)")
    ap.add_argument("--qaplib-convention", default="pair_once", choices=["pair_once", "full"])
    ap.add_argument("--no-quantum", action="store_true")
    ap.add_argument("--noise", type=float, default=0.01, help="nivel de ruido despolarizante")
    args = ap.parse_args(argv)
    args.expect = [float(t) if t.strip() else None for t in args.expect.split(",")]
    os.makedirs(args.out, exist_ok=True)
    q = args.quick
    H = args.hybrid_iters or (120 if q else 300)   # mismo H para QAOA y exacto

    R = {"meta": {}, "data": {}, "validation": [], "classical": [], "quantum": [],
         "lambda_sweep": [], "hybrid": [], "scaling": [], "assignments": []}
    t_all = time.perf_counter()

    inst, mps_report, cand_table = load_instance(args)
    N = inst.N
    ref = args.expect[2] if len(args.expect) > 2 else None
    log(f"Instancia {inst.name}: N={N}")

    # ---------------------------------------------------------- validación
    for n, exp in zip((3, 4), args.expect[:2]):
        r = brute_force(inst.subinstance(n))
        R["validation"].append({"n": n, "optimum": r["cost"], "expected": exp,
                                "ok": None if exp is None else abs(r["cost"] - exp) < 1e-6,
                                "perm": r["perm"], "time_s": r["time_s"]})
        log(f"Validación N={n}: óptimo {r['cost']} (esperado {exp})")
    bf = None
    if N <= 10 and not args.skip_bf:
        log(f"Fuerza bruta N={N} ({math.factorial(N)} permutaciones)...")
        bf = brute_force(inst)
        R["validation"].append({"n": N, "optimum": bf["cost"], "expected": ref,
                                "ok": None if ref is None else abs(bf["cost"] - ref) < 1e-6,
                                "perm": bf["perm"], "time_s": bf["time_s"]})
        R["classical"].append({**bf, "gap_pct": gap(bf["cost"], ref)})
        log(f"  óptimo exacto {bf['cost']} en {bf['time_s']:.1f}s ({bf['n_optimal_perms']} óptimos)")
        if ref is None:
            ref = bf["cost"]

    # ------------------------------------------------------------- clásicos
    sa = simulated_annealing(inst, iters=30_000 if q else 80_000, restarts=4, seed=args.seed)
    sa_out = {k: v for k, v in sa.items() if k != "history"}
    R["classical"].append({**sa_out, "gap_pct": gap(sa["cost"], ref)})
    log(f"Simulated annealing: {sa['cost']} ({sa['time_s']:.1f}s)")
    gl = gilmore_lawler_bound(inst)
    R["classical"].append(gl)
    log(f"Cota Gilmore-Lawler: {gl['bound']:.1f}")
    rnd = random_assignment(inst, seed=args.seed)
    R["assignments"].append({"label": "Aleatoria", "perm": rnd["perm"], "cost": rnd["cost"]})
    best_classic = bf or sa
    R["assignments"].append({"label": "Clásico exacto" if bf else "Clásico (SA)",
                             "perm": best_classic["perm"], "cost": best_classic["cost"]})

    # ---------------------------------------------------------------- QAOA
    if not args.no_quantum:
        from .quantum import run_qaoa
        rs = 2 if q else 4
        mi = 100 if q else 200
        exps = [(3, "x", 1, 0.0), (3, "x", 2, 0.0), (3, "xy", 1, 0.0), (3, "xy", 2, 0.0),
                (4, "xy", 1, 0.0), (4, "x", 1, 0.0)]
        if not q:
            exps += [(4, "xy", 2, 0.0)]
        if args.noise:
            exps += [(3, "x", 1, args.noise), (3, "xy", 1, args.noise)]
        sub_opt = {v["n"]: v["optimum"] for v in R["validation"]}
        for n, mixer, p, noise in exps:
            s = inst.subinstance(n)
            r = run_qaoa(s, p=p, mixer=mixer, restarts=rs, maxiter=mi, shots=4096,
                         seed=args.seed, noise=noise, optimum=sub_opt.get(n),
                         trace=(n == 4 and p == 1 and not noise))   # frames del modo demo
            R["quantum"].append(r)
            log(f"QAOA {r['id']}: P(fact)={r['p_feasible']:.4f} ideal, {r['feasible_fraction_shots']:.4f} shots "
                f"vs azar {r['random_feasible_baseline']:.4f} | "
                f"P(ópt)={r['p_optimal']:.4f} | mejor factible {r['best_feasible_cost']} "
                f"(ópt {r['optimum']}) | {r['time_s']:.1f}s | CX={r.get('cx_count')}")
        # barrido de lambda
        s3 = inst.subinstance(3)
        lam0 = lambda_auto(s3)
        for mixer in ("x", "xy"):
            for fct in (0.25, 0.5, 1.0, 2.0, 4.0):
                r = run_qaoa(s3, p=1, mixer=mixer, lam=lam0 * fct, restarts=2, maxiter=mi,
                             shots=4096, seed=args.seed, optimum=sub_opt.get(3),
                             compute_stats=False, keep_distribution=0)
                R["lambda_sweep"].append({"N": 3, "mixer": mixer, "lam": r["lam"], "lam_factor": fct,
                                          "p_feasible": r["p_feasible"], "p_optimal": r["p_optimal"],
                                          "best_feasible_cost": r["best_feasible_cost"],
                                          "top_raw_feasible": r["top_raw_feasible"]})
            log(f"Barrido λ ({mixer}) listo (λ0={lam0:.1f})")

    # -------------------------------------------------------------- híbrido
    start = np.random.default_rng(args.seed + 100).permutation(N)
    # mismo presupuesto, semilla y arranque para todos los solvers del subproblema.
    # Ablación: azar uniforme con las mismas muestras; con 8 shots se ve cuánto concentra QAOA.
    runs = [("exact", H, 512, "qgate_lns_exact", "Control · subproblema exacto"),
            ("random", H, 512, "qgate_lns_random", "Control · azar (512 shots)"),
            ("random", H, 8, "qgate_lns_random_s8", "Control · azar (8 shots)")]
    if not args.no_quantum:
        runs = [("qaoa", H, 512, "qgate_lns_qaoa", "QGate · QAOA (512 shots)")] + runs[:2] +                [("qaoa", H, 8, "qgate_lns_qaoa_s8", "QGate · QAOA (8 shots)")] + runs[2:]
    best_h = None
    for solver, iters, shots, method, label in runs:
        log(f"Híbrido QGate ({label}, {iters} iteraciones)...")
        h = qgate_lns(inst, k=3, iters=iters, solver=solver, seed=args.seed, start_perm=start,
                      shots=shots, label=label)
        h["method"] = method
        h["gap_pct"] = gap(h["final_cost"], ref)
        h["polished_gap_pct"] = gap(h.get("polished_cost"), ref)
        R["hybrid"].append(h)
        log(f"  {h['label']}: {h['start_cost']} -> {h['final_cost']} (pulido {h.get('polished_cost')}) "
            f"gap {h['gap_pct']}% | éxito subproblema {h['sub_success_rate']:.2f} | "
            f"P(ópt) QAOA {h['qaoa_p_optimal_mean']} vs azar {h['random_p_optimal_mean']:.3f} | {h['time_s']:.1f}s")
        if method in ("qgate_lns_qaoa", "qgate_lns_exact") and best_h is None:
            best_h = h
    if best_h:
        R["best_assignment"] = {"method": best_h["method"], "perm": best_h["final_perm"],
                                "cost": best_h["final_cost"]}
        R["assignments"].append({"label": "QGate híbrido", "perm": best_h["final_perm"],
                                 "cost": best_h["final_cost"]})
        if best_h.get("polished_cost") is not None and best_h["polished_cost"] < best_h["final_cost"] - 1e-9:
            R["assignments"].append({"label": "QGate + pulido 2-swap", "perm": best_h["polished_perm"],
                                     "cost": best_h["polished_cost"]})
    # robustez: el mismo marco con solver exacto (barato) en varias semillas y arranques
    seeds = list(range(args.seed, args.seed + (6 if q else 12)))
    ms = []
    for sd in seeds:
        st = np.random.default_rng(sd + 100).permutation(N)
        ms.append(qgate_lns(inst, k=3, iters=H, solver="exact", seed=sd, start_perm=st,
                            polish=False)["final_cost"])
    R["hybrid_seeds"] = {"solver": "exact", "iters": H, "seeds": seeds, "final_costs": ms,
                         "mean": float(np.mean(ms)), "best": float(min(ms)), "worst": float(max(ms)),
                         "hits_ref": int(sum(abs(c - ref) < 1e-6 for c in ms)) if ref else None,
                         "mean_gap_pct": gap(float(np.mean(ms)), ref)}
    log(f"Híbrido exacto en {len(seeds)} semillas: media {np.mean(ms):.1f}, mejor {min(ms)}, "
        f"llega a la referencia {R['hybrid_seeds']['hits_ref']}/{len(seeds)}")
    R["hybrid"].append({"method": "simulated_annealing", "label": "Simulated annealing",
                        "N": N, "final_cost": sa["cost"], "time_s": sa["time_s"],
                        "gap_pct": gap(sa["cost"], ref),
                        "history": [{"iter": i, "t": hh["t"], "current": hh["current"],
                                     "best": hh["best"]} for i, hh in enumerate(sa["history"])
                                    if hh["restart"] == 0]})

    # ---------------------------------------------------------- escalabilidad
    scale_insts = []
    for tok in [t for t in args.scale.split(",") if t.strip()]:
        n_s = int(tok)
        scale_insts.append(inst if n_s == N else QAPInstance.synthetic(n_s, seed=args.seed + n_s))
    for pth in args.scale_files:
        if pth.endswith(".npz"):
            scale_insts.append(QAPInstance.from_matrices_file(pth))
        else:
            scale_insts.append(QAPInstance.from_qaplib(pth, convention=args.qaplib_convention))
    for si in scale_insts:
        ns = si.N
        lb = gilmore_lawler_bound(si)["bound"]
        opt = ref if si is inst else None
        tracemalloc.start()
        s_sa = simulated_annealing(si, iters=20_000 if q else 50_000, restarts=3, seed=args.seed)
        peak = tracemalloc.get_traced_memory()[1] / 1e6
        tracemalloc.stop()
        rows = [("simulated_annealing", s_sa["cost"], s_sa["time_s"], peak, 0)]
        st = np.random.default_rng(args.seed).permutation(ns)
        hs = max(H // 2, 40)        # mismo presupuesto para ambos solvers del subproblema
        h_e = qgate_lns(si, iters=hs, solver="exact", seed=args.seed, start_perm=st, polish=False)
        rows.append(("qgate_lns_exact", h_e["final_cost"], h_e["time_s"], h_e["peak_mem_mb"], 0))
        if not args.no_quantum:
            h_q = qgate_lns(si, iters=hs, solver="qaoa", seed=args.seed,
                            start_perm=st, polish=False)
            rows.append(("qgate_lns_qaoa", h_q["final_cost"], h_q["time_s"], h_q["peak_mem_mb"], 9))
        for meth, c, t, mem, qb in rows:
            R["scaling"].append({"N": ns, "instance": si.name, "method": meth, "best_cost": c,
                                 "lower_bound": lb, "gap_vs_bound_pct": gap(c, lb),
                                 "gap_vs_opt_pct": gap(c, opt), "time_s": t,
                                 "peak_mem_mb": mem, "qubits": qb, "iters": hs if meth != "simulated_annealing" else None,
                                 "search_space": f"{ns}! = {float(np.prod(np.arange(1, ns + 1, dtype=float))):.3g}"})
        log(f"Escala N={ns} ({si.name}): " + ", ".join(f"{m}={c:.0f}" for m, c, *_ in rows)
            + f" | cota {lb:.0f}")

    # ------------------------------------------------------------- metadatos
    R["meta"] = {
        "instance": inst.name, "N": N, "source": inst.meta.get("source", "synthetic"),
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"), "seed": args.seed,
        "reference_optimum": ref, "track": "A", "versions": _versions(),
        # memoria de un statevector genérico: 2^(N^2) amplitudes complejas de 16 bytes
        "statevector_memory": [{"N": n_, "qubits": n_ * n_, "bytes": 16.0 * 2.0 ** (n_ * n_)}
                               for n_ in (3, 4, 5, 10, 14)],
        "qubits_per_subproblem": 9,
        "args": vars(args), "total_time_s": time.perf_counter() - t_all,
        "limitations": [
            "Statevector exacto solo hasta ~20 qubits: QAOA directo llega a N=4 (16 qubits)",
            "N=10 completo serían 100 qubits: se resuelve por vecindarios de 3 vuelos (9 qubits)",
            "Penalidades: λ grande aplana el paisaje, λ chico deja ganar soluciones inválidas",
            "Con ruido despolarizante el mixer XY pierde buena parte de su ventaja de factibilidad",
            "Todo corre en simulador (Qiskit Aer); no se usó hardware real",
            "La calidad final del híbrido la limita el vecindario de 3 vuelos, no el solver QAOA",
            "Con 512 shots el azar también resuelve los subproblemas de 3 vuelos: el aporte medible de QAOA es concentrar probabilidad en el óptimo (se ve con pocos shots)",
            "N>10 son instancias sintéticas sin óptimo conocido: se comparan contra la cota Gilmore-Lawler",
            "Las unidades del aeropuerto son supuestos: qap10 es un benchmark matemático",
            "El pulido 2-swap y la reparación clásica se reportan aparte del resultado crudo",
        ],
    }
    R["data"] = {
        "F": inst.F, "D": inst.D,
        "factorization_residual": inst.meta.get("factorization_residual"),
        "index_strategy": inst.meta.get("index_strategy", "synthetic"),
        "mps_report": mps_report, "index_candidates": cand_table,
        "gate_xy": inst.meta.get("gate_xy") or (mds_2d(inst.D).tolist() if inst.D is not None else None),
    }
    path = os.path.join(args.out, "results.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(R, fh, default=_jsonable, indent=1, ensure_ascii=False)
    log(f"Guardado {path} ({time.perf_counter() - t_all:.0f}s en total)")

    try:
        from .plots import make_all
        make_all(R, args.out)
        log("Gráficos PNG generados")
    except Exception as e:  # pragma: no cover
        log(f"No se generaron gráficos: {e}")
    builder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "dashboard", "build_report.py")
    if os.path.exists(builder):
        import subprocess
        subprocess.run([sys.executable, builder, path, os.path.join(args.out, "report.html")], check=False)
        log(f"Reporte: {os.path.join(args.out, 'report.html')}")
    _summary(R)


def _summary(R):
    print("\n================ RESUMEN ================")
    for v in R["validation"]:
        print(f"N={v['n']:>2}: óptimo {v['optimum']}  esperado {v['expected']}  ok={v['ok']}")
    for c in R["classical"]:
        print(f"{c['method']:<24} {c.get('cost', c.get('bound'))}  gap={c.get('gap_pct')}  t={c['time_s']:.2f}s")
    for qq in R["quantum"]:
        print(f"{qq['id']:<18} P(fact)={qq['p_feasible']:.4f} azar={qq['random_feasible_baseline']:.4f} "
              f"P(ópt)={qq['p_optimal']:.4f} mejor={qq['best_feasible_cost']}")
    for h in R["hybrid"]:
        print(f"{h['label']:<36} final={h['final_cost']} gap={h.get('gap_pct')} t={h['time_s']:.1f}s")


if __name__ == "__main__":
    main()
