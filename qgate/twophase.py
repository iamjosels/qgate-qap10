"""Híbrido en dos fases (final, etapa 3 del reto).

Fase 1: búsqueda local 2-swap (mejor mejora) hasta un óptimo local. Clásica.
Fase 2: un bloque de k=3 vuelos (9 qubits) elegido por el selector de vecindario; el bloque se
        resuelve con el solver indicado. Si mejora, se vuelve a la fase 1; si no, se perturba
        desde la mejor asignación conocida (swaps aleatorios, más fuertes tras cada fallo).

Presupuesto idéntico para todos los solvers: B iteraciones externas; cada una es
(fase 1 hasta óptimo local) + (un intento de bloque; si falla, perturbación). El solver "ls" no
intenta bloque (búsqueda 2-swap con reinicios). Mismo selector, semilla y arranque para todos.

Solvers del bloque:
  exact        enumeración de las 3! = 6 permutaciones; ante empates devuelve la primera
  exact_rand   enumeración, pero elige al azar entre las permutaciones que mejoran (diversificación)
  random_valid S muestras uniformes de las 6 permutaciones válidas; devuelve la mejor
  qaoa         QAOA p=2, mixer XY + estado W, S shots; ángulos reutilizados del bloque anterior
               con respaldo a arranque frío si la distribución resultante queda por debajo del
               azar en P(válida) (criterio que no usa el óptimo)
Cada movimiento aceptado se registra con su origen (swap, block, kick) y su reducción de costo.
"""
from __future__ import annotations

import itertools
import math
import time
import tracemalloc

import numpy as np

from .classical import swap_delta
from .hybrid import build_subproblem
from .instance import QAPInstance

PERMS3 = list(itertools.permutations(range(3)))


def tension(inst: QAPInstance, perm: np.ndarray) -> np.ndarray:
    """tension(i) = sum_m F[i,m] * D[pi(i), pi(m)] con la convención del proyecto (vía T simétrico)."""
    n = inst.N
    idx = np.arange(n)
    M = inst.T[idx[:, None], perm[:, None], idx[None, :], perm[None, :]]
    return M.sum(axis=1) + inst.L[idx, perm]


def select_block(inst, perm, rng, k, mode, last=None, temp=1.0):
    """random: k elementos uniformes. tension: ruleta softmax sobre la tensión normalizada,
    sin reemplazo; si sale el mismo trío que el bloque anterior, se vuelve a muestrear."""
    n = inst.N
    for _ in range(8):
        if mode == "random":
            el = sorted(rng.choice(n, k, replace=False).tolist())
        else:
            t = tension(inst, perm)
            z = (t - t.max()) / (temp * (t.std() + 1e-12))
            w = np.exp(z)
            el = sorted(rng.choice(n, k, replace=False, p=w / w.sum()).tolist())
        if el != last:
            return el
    return el


def local_search_moves(inst, perm, cost):
    """2-swap de mejor mejora hasta óptimo local. Devuelve (perm, costo, n_movimientos, reducción)."""
    n = inst.N
    moves, red = 0, 0.0
    while True:
        best = (-1e-9, None)
        for a in range(n):
            for b in range(a + 1, n):
                d = swap_delta(inst, perm, a, b)
                if d < best[0]:
                    best = (d, (a, b))
        if best[1] is None:
            return perm, cost, moves, red
        a, b = best[1]
        perm[a], perm[b] = perm[b], perm[a]
        cost += best[0]
        moves += 1
        red -= best[0]


def _solve_block(sub, solver, rng, shots, seed, warm, cur_sub, qstats):
    """Devuelve (permutación del bloque o None, ángulos para el siguiente bloque)."""
    costs = [sub.cost(p) for p in PERMS3]
    if solver == "exact":
        return list(PERMS3[int(np.argmin(costs))]), warm
    if solver == "exact_rand":
        better = [i for i, c in enumerate(costs) if c < cur_sub - 1e-9]
        return (list(PERMS3[better[rng.integers(len(better))]]) if better else [0, 1, 2]), warm
    if solver == "random_valid":
        draws = rng.integers(0, 6, size=shots)
        i = min(set(draws.tolist()), key=lambda j: costs[j])
        return list(PERMS3[i]), warm
    if solver == "qaoa":
        from .quantum import solve_subproblem_qaoa
        t = time.perf_counter()
        perm_q, params, info = solve_subproblem_qaoa(sub, p=2, shots=shots, seed=seed, init_params=warm, maxiter=40)
        evals = info["evals"]
        if warm is not None:
            qstats["warm"] += 1
            if info["p_feasible"] < info["random_feasible_baseline"]:      # respaldo a arranque frío
                qstats["fallback_cold"] += 1
                perm_q, params, info = solve_subproblem_qaoa(sub, p=2, shots=shots, seed=seed, init_params=None, maxiter=40)
                evals += info["evals"]
        qstats["evals"] += evals
        qstats["blocks"] += 1
        qstats["p_opt_sum"] += info["p_optimal"]
        qstats["qaoa_s"] += time.perf_counter() - t
        return perm_q, params
    raise ValueError(solver)


def two_phase(inst: QAPInstance, solver: str = "qaoa", select: str = "tension", B: int = 100,
              seed: int = 0, start_perm=None, shots: int = 8, k: int = 3, warm_start: bool = True,
              block_log: list | None = None) -> dict:
    from . import quantum
    rng = np.random.default_rng(seed)
    n = inst.N
    tracemalloc.start()
    aer0 = quantum.TIMERS["aer_s"]
    t0 = time.perf_counter()
    perm = np.array(start_perm if start_perm is not None else rng.permutation(n), dtype=int)
    cost = inst.cost(perm)
    start_cost = cost
    best_cost, best_perm = cost, perm.copy()
    origin = {"swap": {"moves": 0, "reduction": 0.0}, "block": {"moves": 0, "reduction": 0.0},
              "kick": {"moves": 0, "reduction": 0.0}}
    snap = {kk: dict(v) for kk, v in origin.items()}           # atribución al momento del mejor
    qstats = {"evals": 0, "blocks": 0, "warm": 0, "fallback_cold": 0, "p_opt_sum": 0.0, "qaoa_s": 0.0}
    blocks_tried = blocks_improved = 0
    failed = 0
    warm, last = None, None
    history = [{"it": 0, "best": float(best_cost)}]

    def mark():
        nonlocal best_cost, best_perm, snap
        if cost < best_cost - 1e-9:
            best_cost, best_perm = cost, perm.copy()
            snap = {kk: dict(v) for kk, v in origin.items()}

    for it in range(1, B + 1):
        perm, cost, mv, red = local_search_moves(inst, perm, cost)            # fase 1
        origin["swap"]["moves"] += mv
        origin["swap"]["reduction"] += red
        mark()
        improved = False
        if solver != "ls":                                                    # fase 2
            el = select_block(inst, perm, rng, k, select, last)
            last = el
            sub = build_subproblem(inst, perm, el)
            if block_log is not None:
                sub.meta["perm_before"] = perm.tolist()
            cur_sub = sub.cost([0, 1, 2])
            new, warm = _solve_block(sub, solver, rng, shots, seed * 100003 + it, warm if warm_start else None,
                                     cur_sub, qstats)
            blocks_tried += 1
            if new is not None and sub.cost(new) < cur_sub - 1e-9:
                locs = sub.meta["locs"]
                for a, e in enumerate(el):
                    perm[e] = locs[new[a]]
                new_cost = inst.cost(perm)
                origin["block"]["moves"] += 1
                origin["block"]["reduction"] += cost - new_cost
                cost = new_cost
                blocks_improved += 1
                improved = True
                mark()
            if block_log is not None:
                block_log.append({"it": it, "elems": el, "improved": improved, "perm_before": sub.meta.get("perm_before")})
        if not improved:                                                      # perturbación
            prev = cost
            perm = best_perm.copy()
            cost = best_cost
            n_sw = 3 + min(failed, n // 2)
            failed += 1
            for _ in range(n_sw):
                a, b = rng.choice(n, 2, replace=False)
                perm[a], perm[b] = perm[b], perm[a]
            cost = inst.cost(perm)
            origin["kick"]["moves"] += 1
            origin["kick"]["reduction"] += prev - cost
        else:
            failed = 0
        history.append({"it": it, "best": float(best_cost)})
    perm, cost, mv, red = local_search_moves(inst, perm, cost)
    origin["swap"]["moves"] += mv
    origin["swap"]["reduction"] += red
    mark()
    wall = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    feasible = sorted(best_perm.tolist()) == list(range(n))
    return {
        "solver": solver, "select": select, "N": n, "B": B, "seed": seed, "shots": shots if solver in ("qaoa", "random_valid") else None,
        "start_cost": float(start_cost), "best_cost": float(inst.cost(best_perm)), "best_perm": best_perm.tolist(),
        "feasible": feasible, "time_s": wall, "peak_mem_mb": peak / 1e6,
        "blocks_tried": blocks_tried, "blocks_improved": blocks_improved,
        "block_improve_rate_from_local_opt": (blocks_improved / blocks_tried) if blocks_tried else None,
        "origin_at_best": snap, "origin_total": origin,
        "qaoa": ({**qstats, "p_opt_mean": qstats["p_opt_sum"] / max(qstats["blocks"], 1),
                  "evals_per_block": qstats["evals"] / max(qstats["blocks"], 1),
                  "aer_s": quantum.TIMERS["aer_s"] - aer0,
                  "frac_wall_in_qaoa": qstats["qaoa_s"] / wall if wall else None,
                  "frac_wall_in_aer": (quantum.TIMERS["aer_s"] - aer0) / wall if wall else None}
                 if solver == "qaoa" else None),
        "variables_quantum_frac": (k * k) / (n * n) if solver == "qaoa" else 0.0,
        "history": history,
    }
