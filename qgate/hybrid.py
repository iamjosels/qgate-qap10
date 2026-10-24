"""QGate: búsqueda en vecindarios grandes (LNS) con subproblemas resueltos por QAOA.

En cada iteración:
  1. Se eligen k elementos (k=3 -> 9 qubits) y sus ubicaciones actuales.
  2. Se arma el subproblema: reasignar esos k elementos entre esas k ubicaciones con el
     resto fijo. Las interacciones con los elementos fijos entran como términos lineales.
  3. Se resuelve con QAOA (mixer XY) y se acepta si mejora.
El tamaño cuántico es constante (k^2 qubits) sin importar N: la memoria no crece con N.
Como control, el mismo marco puede usar un solver exacto (k! permutaciones).
"""
from __future__ import annotations

import itertools
import math
import time
import tracemalloc

import numpy as np

from .instance import QAPInstance
from .classical import local_search


def build_subproblem(inst: QAPInstance, perm: np.ndarray, elems: list[int]) -> QAPInstance:
    locs = [int(perm[e]) for e in elems]
    k = len(elems)
    fixed = [m for m in range(inst.N) if m not in elems]
    T = inst.T
    Ts = T[np.ix_(elems, locs, elems, locs)].copy()
    Ls = np.zeros((k, k))
    for a, e in enumerate(elems):
        for s, loc in enumerate(locs):
            Ls[a, s] = inst.L[e, loc] + sum(T[e, loc, m, perm[m]] for m in fixed)
    # constante = costo de la parte fija (pares fijos + lineales fijos)
    const = inst.const
    for x, m1 in enumerate(fixed):
        const += inst.L[m1, perm[m1]]
        for m2 in fixed[x + 1:]:
            const += T[m1, perm[m1], m2, perm[m2]]
    sub = QAPInstance(T=Ts, L=Ls, const=float(const), name="sub",
                      meta={"elems": elems, "locs": locs})
    return sub


def _exact_sub(sub: QAPInstance):
    """Óptimo del subproblema por enumeración (k! permutaciones) y cuántas permutaciones lo alcanzan."""
    best = (math.inf, None)
    costs = []
    for pm in itertools.permutations(range(sub.N)):
        c = sub.cost(pm)
        costs.append(c)
        if c < best[0]:
            best = (c, list(pm))
    n_opt = sum(abs(c - best[0]) < 1e-9 for c in costs)
    return best[0], best[1], n_opt


def _random_sub(sub: QAPInstance, shots: int, seed: int):
    """Control de ablación: `shots` muestras uniformes del mismo espacio que el estado W por fila
    (cada elemento en una ubicación al azar, k^k estados); devuelve la mejor permutación válida."""
    k = sub.N
    draws = np.random.default_rng(seed).integers(0, k, size=(shots, k))
    best = (math.inf, None)
    for row in np.unique(draws, axis=0):
        if len(set(row.tolist())) == k:
            c = sub.cost(row)
            if c < best[0]:
                best = (c, row.tolist())
    return best[1]


def qgate_lns(inst: QAPInstance, k: int = 3, iters: int = 120, solver: str = "qaoa",
              p: int = 2, seed: int = 0, start_perm=None, select: str = "mixed",
              time_limit: float | None = None, shots: int = 512, maxiter: int = 40,
              polish: bool = True, label: str | None = None, stall_limit: int = 10,
              kick_swaps: int = 3, adaptive_kick: bool = True, sideways: bool = False,
              warm_start: bool = False) -> dict:
    from .quantum import solve_subproblem_qaoa   # import diferido (Qiskit)

    rng = np.random.default_rng(seed)
    n = inst.N
    tracemalloc.start()
    t0 = time.perf_counter()
    perm = np.array(start_perm if start_perm is not None else rng.permutation(n), dtype=int)
    cur = inst.cost(perm)
    start_cost = cur
    history = [{"iter": 0, "t": 0.0, "current": cur, "best": cur}]
    stats = {"subproblems": 0, "improvements": 0, "qaoa_found_sub_opt": 0,
             "no_feasible_sample": 0, "sampler_found_sub_opt": 0}
    p_opt_acc, p_rand_opt_acc, p_feas_acc = 0.0, 0.0, 0.0   # P(óptimo) del subproblema: QAOA vs azar
    warm = None
    best_cost, best_perm = cur, perm.copy()
    stall = 0
    failed_kicks = 0                         # kicks seguidos sin mejorar el mejor conocido
    stats["kicks"] = 0
    for it in range(1, iters + 1):
        # perturbación (iterated local search) si nos estancamos en un óptimo local
        if stall >= stall_limit:
            perm = best_perm.copy()          # reiniciar desde el mejor conocido
            # perturbación adaptativa (tipo VNS): más swaps tras cada kick que no mejoró
            n_swaps = kick_swaps + (min(failed_kicks, n // 2) if adaptive_kick else 0)
            failed_kicks += 1
            for _ in range(n_swaps):
                a, b = rng.choice(n, 2, replace=False)
                perm[a], perm[b] = perm[b], perm[a]
            cur = inst.cost(perm)
            stall = 0
            stats["kicks"] += 1
        if time_limit and time.perf_counter() - t0 > time_limit:
            break
        # selección: aleatoria o sesgada a elementos con mayor contribución
        if select == "random" or (select == "mixed" and it % 2 == 0):
            elems = sorted(rng.choice(n, k, replace=False).tolist())
        else:
            contrib = np.array([sum(inst.T[e, perm[e], m, perm[m]] for m in range(n))
                                for e in range(n)], dtype=float)
            w = contrib - contrib.min() + 1e-9
            elems = sorted(rng.choice(n, k, replace=False, p=w / w.sum()).tolist())
        sub = build_subproblem(inst, perm, elems)
        sub_opt_cost, sub_opt_perm, n_opt = _exact_sub(sub)   # k! = 6: solo para medir
        cur_sub = sub.cost(list(range(k)))                    # asignación actual = identidad
        stats["subproblems"] += 1
        p_rand_opt_acc += n_opt / k ** k                      # azar sobre el espacio del estado W
        if solver == "exact":
            new_sub = sub_opt_perm
        else:
            if solver == "random":
                new_sub = _random_sub(sub, shots, seed + it)
            else:
                new_sub, warm, info = solve_subproblem_qaoa(sub, p=p, shots=shots, seed=seed + it,
                                                            init_params=warm if warm_start else None,
                                                            maxiter=maxiter)
                p_opt_acc += info["p_optimal"]
                p_feas_acc += info["p_feasible"]
            if new_sub is None:
                stats["no_feasible_sample"] += 1
                stall += 1
                history.append({"iter": it, "t": time.perf_counter() - t0,
                                "current": cur, "best": best_cost})
                continue
            if abs(sub.cost(new_sub) - sub_opt_cost) < 1e-9:
                stats["sampler_found_sub_opt"] += 1
                if solver == "qaoa":
                    stats["qaoa_found_sub_opt"] += 1
        new_sub_cost = sub.cost(new_sub)
        # solo mejoras estrictas: el solver exacto devuelve la identidad ante empates y QAOA
        # puede devolver otra permutación del mismo costo; aceptar empates haría que ambas
        # trayectorias diverjan por azar y no por la calidad del solver del subproblema
        accept = new_sub_cost < cur_sub - 1e-9 or (sideways and new_sub_cost <= cur_sub + 1e-9)
        if accept and list(new_sub) != list(range(k)):
            locs = sub.meta["locs"]
            for a, e in enumerate(elems):
                perm[e] = locs[new_sub[a]]
            cur = inst.cost(perm)
            if new_sub_cost < cur_sub - 1e-9:
                stats["improvements"] += 1
        if cur < best_cost - 1e-9:
            best_cost, best_perm = cur, perm.copy()
            stall = 0
            failed_kicks = 0
        else:
            stall += 1
        history.append({"iter": it, "t": time.perf_counter() - t0, "current": cur,
                        "best": best_cost})
    raw_cost = inst.cost(best_perm)
    raw_perm = best_perm.tolist()
    nsub = max(stats["subproblems"], 1)
    out = {
        "method": f"qgate_lns_{solver}", "label": label or {
            "qaoa": "QGate · QAOA", "random": "Muestreo aleatorio (control)"}.get(
            solver, "QGate · subproblema exacto (control)"),
        "solver": solver, "shots": shots if solver in ("qaoa", "random") else None,
        "N": n, "k": k, "qubits_per_subproblem": k * k if solver == "qaoa" else 0,
        "p": p if solver == "qaoa" else None, "iters": len(history) - 1,
        "start_cost": float(start_cost), "final_cost": float(raw_cost), "final_perm": raw_perm,
        "time_s": time.perf_counter() - t0, "history": history, **stats,
        "qaoa_sub_success_rate": (stats["qaoa_found_sub_opt"] / max(stats["subproblems"]
                                  - stats["no_feasible_sample"], 1)) if solver == "qaoa" else None,
        # éxito sobre todos los subproblemas (sin muestra válida cuenta como fallo)
        "sub_success_rate": stats["sampler_found_sub_opt"] / nsub if solver != "exact" else 1.0,
        "random_p_optimal_mean": p_rand_opt_acc / nsub,
        "qaoa_p_optimal_mean": p_opt_acc / nsub if solver == "qaoa" else None,
        "qaoa_p_feasible_mean": p_feas_acc / nsub if solver == "qaoa" else None,
    }
    if polish:
        ls = local_search(inst, raw_perm)
        out["polished_cost"] = ls["cost"]
        out["polished_perm"] = ls["perm"]
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    out["peak_mem_mb"] = peak / 1e6
    return out
