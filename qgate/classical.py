"""Métodos clásicos: exacto (fuerza bruta), simulated annealing, búsqueda local y
cota inferior de Gilmore-Lawler (generalizada a T arbitrario)."""
from __future__ import annotations

import itertools
import math
import time

import numpy as np
from scipy.optimize import linear_sum_assignment

from .instance import QAPInstance


# ----------------------------------------------------------------- exacto
def brute_force(inst: QAPInstance, chunk: int = 200_000) -> dict:
    """Evalúa las N! permutaciones en lotes, sin guardarlas todas en memoria."""
    n = inst.N
    t0 = time.perf_counter()
    best_cost, best_perm, n_opt, total = math.inf, None, 0, 0
    it = itertools.permutations(range(n))
    while True:
        block = list(itertools.islice(it, chunk))
        if not block:
            break
        P = np.array(block, dtype=np.int64)
        c = inst.cost_batch(P)
        total += len(block)
        m = c.min()
        if m < best_cost - 1e-9:
            best_cost, best_perm = float(m), P[int(c.argmin())].tolist()
            n_opt = int(np.isclose(c, m).sum())
        elif abs(m - best_cost) <= 1e-9:
            n_opt += int(np.isclose(c, m).sum())
    return {"method": "brute_force", "N": n, "cost": best_cost, "perm": best_perm,
            "n_optimal_perms": n_opt, "evaluated": total,
            "time_s": time.perf_counter() - t0}


# ---------------------------------------------------------------- deltas
def swap_delta(inst: QAPInstance, p: np.ndarray, a: int, b: int) -> float:
    """Cambio de costo al intercambiar las ubicaciones de los elementos a y b. O(N)."""
    T, L = inst.T, inst.L
    pa, pb = p[a], p[b]
    n = len(p)
    m = np.arange(n)
    mask = (m != a) & (m != b)
    mm, pm = m[mask], p[mask]
    d = (T[a, pb, mm, pm] - T[a, pa, mm, pm] + T[b, pa, mm, pm] - T[b, pb, mm, pm]).sum()
    d += T[a, pb, b, pa] - T[a, pa, b, pb]
    d += L[a, pb] + L[b, pa] - L[a, pa] - L[b, pb]
    return float(d)


def local_search(inst: QAPInstance, perm, max_rounds: int = 1000) -> dict:
    """Búsqueda local de mejor mejora con intercambios de 2 elementos."""
    t0 = time.perf_counter()
    p = np.array(perm, dtype=int)
    cost = inst.cost(p)
    n = inst.N
    rounds = 0
    while rounds < max_rounds:
        rounds += 1
        best = (0.0, None)
        for a in range(n):
            for b in range(a + 1, n):
                d = swap_delta(inst, p, a, b)
                if d < best[0] - 1e-12:
                    best = (d, (a, b))
        if best[1] is None:
            break
        a, b = best[1]
        p[a], p[b] = p[b], p[a]
        cost += best[0]
    return {"method": "local_search_2swap", "N": n, "cost": float(inst.cost(p)),
            "perm": p.tolist(), "rounds": rounds, "time_s": time.perf_counter() - t0}


def simulated_annealing(inst: QAPInstance, iters: int = 60_000, restarts: int = 4,
                        seed: int = 0, T0: float | None = None,
                        T_end_ratio: float = 1e-3, start=None) -> dict:
    """SA con intercambios de 2 elementos y enfriamiento geométrico. Multi-arranque."""
    rng = np.random.default_rng(seed)
    n = inst.N
    t0 = time.perf_counter()
    best_cost, best_perm = math.inf, None
    history = []
    for r in range(restarts):
        p = np.array(start, dtype=int) if (start is not None and r == 0) else rng.permutation(n)
        cost = inst.cost(p)
        if T0 is None:
            ds = [abs(swap_delta(inst, p, *rng.choice(n, 2, replace=False))) for _ in range(50)]
            temp0 = max(np.mean(ds), 1e-6)
        else:
            temp0 = T0
        alpha = T_end_ratio ** (1.0 / max(iters, 1))
        temp = temp0
        rb_cost, rb_perm = cost, p.copy()
        for t in range(iters):
            a, b = rng.choice(n, 2, replace=False)
            d = swap_delta(inst, p, a, b)
            if d <= 0 or rng.random() < math.exp(-d / temp):
                p[a], p[b] = p[b], p[a]
                cost += d
                if cost < rb_cost - 1e-9:
                    rb_cost, rb_perm = cost, p.copy()
            temp *= alpha
            if t % max(iters // 50, 1) == 0:
                history.append({"restart": r, "iter": t, "t": time.perf_counter() - t0,
                                "current": float(cost), "best": float(min(rb_cost, best_cost))})
        if rb_cost < best_cost:
            best_cost, best_perm = rb_cost, rb_perm.copy()
    best_cost = inst.cost(best_perm)   # recalcular sin error acumulado
    return {"method": "simulated_annealing", "N": n, "cost": float(best_cost),
            "perm": best_perm.tolist(), "iters": iters, "restarts": restarts,
            "time_s": time.perf_counter() - t0, "history": history}


# ------------------------------------------------------------- cota inferior
def gilmore_lawler_bound(inst: QAPInstance) -> dict:
    """Cota inferior tipo Gilmore-Lawler para T general (convención pares una vez).

    C(pi) = sum_i L[i,pi_i] + 1/2 sum_i sum_{k!=i} T[i,pi_i,k,pi_k]
    Para cada (i,j): m_ij = min sobre biyecciones de los demás de sum_k T[i,j,k,pi_k]
    => C >= LAP( L + m/2 ) + const.
    """
    t0 = time.perf_counter()
    n = inst.N
    m = np.zeros((n, n))
    for i in range(n):
        others_e = [k for k in range(n) if k != i]
        for j in range(n):
            others_l = [l for l in range(n) if l != j]
            sub = inst.T[i, j][np.ix_(others_e, others_l)]
            r, c = linear_sum_assignment(sub)
            m[i, j] = sub[r, c].sum()
    W = inst.L + 0.5 * m
    r, c = linear_sum_assignment(W)
    bound = float(W[r, c].sum() + inst.const)
    return {"method": "gilmore_lawler_bound", "N": n, "bound": bound,
            "time_s": time.perf_counter() - t0}


def random_assignment(inst: QAPInstance, seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)
    p = rng.permutation(inst.N)
    return {"method": "random", "N": inst.N, "cost": inst.cost(p), "perm": p.tolist()}
