"""QAOA con Qiskit para subinstancias del QAP.

Dos variantes:
  - mixer="x":  QAOA estándar (estado |+>^n, mixer RX). Todas las restricciones van como penalidad.
  - mixer="xy": Quantum Alternating Operator Ansatz. Estado inicial = estado W por fila
                (cada elemento en una ubicación en superposición) y mixer XY en anillo por fila,
                que conserva "una ubicación por elemento". Solo las columnas quedan penalizadas.

La optimización usa la distribución exacta (simulación de estado con Aer) y una vez
fijados los parámetros se MUESTREA con shots (y opcionalmente con ruido) para reportar.
"""
from __future__ import annotations

import math
import time

import numpy as np
from scipy.optimize import minimize

from qiskit import QuantumCircuit, transpile
from qiskit.circuit import ParameterVector
from qiskit.circuit.library import StatePreparation

from .instance import QAPInstance
from .qubo import QUBO, build_qubo, feasible_mask, index_to_x, x_to_perm, repair

try:
    from qiskit_aer import AerSimulator
    _HAS_AER = True
except Exception:  # pragma: no cover
    _HAS_AER = False


# ------------------------------------------------------------------ circuito
def w_state_amplitudes(m: int) -> np.ndarray:
    amp = np.zeros(2 ** m)
    for j in range(m):
        amp[1 << j] = 1.0 / math.sqrt(m)
    return amp


def _w_state(qc: QuantumCircuit, qubits: list[int]) -> None:
    """Estado W (superposición uniforme de los estados con un solo 1) con RY controladas."""
    m = len(qubits)
    qc.x(qubits[0])
    for j in range(m - 1):
        theta = 2.0 * math.acos(math.sqrt(1.0 / (m - j)))
        qc.cry(theta, qubits[j], qubits[j + 1])
        qc.cx(qubits[j + 1], qubits[j])


def build_qaoa_circuit(qubo: QUBO, p: int, mixer: str = "x", measure: bool = False):
    """Construye el circuito parametrizado. Devuelve (qc, gammas, betas, scale)."""
    N, n = qubo.N, qubo.n
    h, J, _ = qubo.to_ising()
    scale = max(np.abs(h).max(initial=0.0), max((abs(v) for v in J.values()), default=0.0), 1e-12)
    g = ParameterVector("g", p)
    bt = ParameterVector("b", p)
    qc = QuantumCircuit(n)
    if mixer == "x":
        qc.h(range(n))
    elif mixer == "xy":
        for i in range(N):
            _w_state(qc, [i * N + j for j in range(N)])
    else:
        raise ValueError(mixer)
    ring = [(j, (j + 1) % N) for j in range(N)] if N > 2 else [(0, 1)]
    for r in range(p):
        for v in range(n):
            if abs(h[v]) > 0:
                qc.rz(2.0 * g[r] * h[v] / scale, v)
        for (v, w_), val in J.items():
            qc.rzz(2.0 * g[r] * val / scale, v, w_)
        if mixer == "x":
            for v in range(n):
                qc.rx(2.0 * bt[r], v)
        else:
            for i in range(N):
                for (j1, j2) in ring:
                    a, b = i * N + j1, i * N + j2
                    qc.rxx(bt[r], a, b)
                    qc.ryy(bt[r], a, b)
    if measure:
        qc.measure_all()
    return qc, g, bt, scale


def circuit_stats(qc: QuantumCircuit, params: dict | None = None) -> dict:
    """Profundidad y número de CX tras transpilar a una base genérica (sin topología)."""
    c = qc.assign_parameters(params) if params else qc
    t = transpile(c, basis_gates=["cx", "rz", "sx", "x"], optimization_level=1, seed_transpiler=7)
    ops = t.count_ops()
    return {"depth": int(t.depth()), "cx_count": int(ops.get("cx", 0)),
            "n_gates": int(sum(ops.values()))}


# ---------------------------------------------------------------- simulación
_SIM_CACHE = {}


def _statevector_sim():
    if "sv" not in _SIM_CACHE:
        _SIM_CACHE["sv"] = AerSimulator(method="statevector")
    return _SIM_CACHE["sv"]


class _ProbEngine:
    """Calcula probabilidades exactas del estado para parámetros dados."""

    def __init__(self, qc: QuantumCircuit, g, bt):
        self.g, self.bt = list(g), list(bt)
        self.n = qc.num_qubits
        if _HAS_AER:
            self.sim = _statevector_sim()
            c = qc.copy()
            c.save_probabilities()
            self.tqc = c          # Aer ejecuta directamente compuertas estándar (sin transpilar)
        else:
            from qiskit.quantum_info import Statevector  # noqa
            self.qc = qc

    def probs(self, theta: np.ndarray) -> np.ndarray:
        p = len(self.g)
        binds = {**{self.g[i]: float(theta[i]) for i in range(p)},
                 **{self.bt[i]: float(theta[p + i]) for i in range(p)}}
        if _HAS_AER:
            res = self.sim.run(self.tqc.assign_parameters(binds)).result()
            return np.asarray(res.data(0)["probabilities"], dtype=float)
        from qiskit.quantum_info import Statevector
        return Statevector(self.qc.assign_parameters(binds)).probabilities()


def _cvar(probs: np.ndarray, E_sorted: np.ndarray, order: np.ndarray, alpha: float) -> float:
    ps = probs[order]
    cum = np.cumsum(ps)
    k = int(np.searchsorted(cum, alpha))
    if k == 0:
        return float(E_sorted[0])
    mass = cum[k - 1]
    val = (ps[:k] * E_sorted[:k]).sum() + (alpha - mass) * E_sorted[k]
    return float(val / alpha)


def _noise_model(level: float):
    from qiskit_aer.noise import NoiseModel, depolarizing_error, ReadoutError
    nm = NoiseModel()
    nm.add_all_qubit_quantum_error(depolarizing_error(level / 10, 1), ["sx", "x", "rz"])
    nm.add_all_qubit_quantum_error(depolarizing_error(level, 2), ["cx"])
    ro = level / 2
    nm.add_all_qubit_readout_error(ReadoutError([[1 - ro, ro], [ro, 1 - ro]]))
    return nm


# ------------------------------------------------------------------- runner
def run_qaoa(inst: QAPInstance, p: int = 1, mixer: str = "xy", lam: float | None = None,
             objective: str = "cvar", alpha: float = 0.2, restarts: int = 3,
             maxiter: int = 150, shots: int = 4096, seed: int = 7,
             noise: float = 0.0, init_params: np.ndarray | None = None,
             optimum: float | None = None, exp_id: str | None = None,
             keep_distribution: int = 12, compute_stats: bool = True,
             ideal_sampling: bool = False) -> dict:
    """Optimiza QAOA sobre la subinstancia `inst` (N <= 4 recomendado; N=5 son 25 qubits)."""
    t0 = time.perf_counter()
    N = inst.N
    qubo = build_qubo(inst, lam)
    n = qubo.n
    bits = qubo.all_bits()
    E = qubo.energies_all(bits)
    feas = feasible_mask(N, bits)
    order = np.argsort(E)
    E_sorted = E[order]

    qc, g, bt, scale = build_qaoa_circuit(qubo, p, mixer)
    eng = _ProbEngine(qc, g, bt)
    rng = np.random.default_rng(seed)
    evals = 0

    def f(theta):
        nonlocal evals
        evals += 1
        pr = eng.probs(theta)
        if objective == "cvar":
            return _cvar(pr, E_sorted, order, alpha)
        return float(pr @ E)

    best = (math.inf, None)
    starts = []
    if init_params is not None:
        starts.append(np.asarray(init_params, dtype=float))
    while len(starts) < max(restarts, 1):
        starts.append(np.concatenate([rng.uniform(0, math.pi, p), rng.uniform(0, math.pi, p)]))
    for x0 in starts:
        res = minimize(f, x0, method="COBYLA", options={"maxiter": maxiter, "rhobeg": 0.4})
        if res.fun < best[0]:
            best = (float(res.fun), res.x.copy())
    theta = best[1]
    probs = eng.probs(theta)

    # métricas exactas
    feas_cost = {}
    for sidx in np.where(feas)[0]:
        perm = tuple(x_to_perm(index_to_x(int(sidx), N)))
        feas_cost[int(sidx)] = (perm, float(E[sidx]))          # en estados factibles E == costo
    opt_cost = min(c for _, c in feas_cost.values())
    opt = optimum if optimum is not None else opt_cost
    p_feas = float(probs[feas].sum())
    p_opt = float(sum(probs[s] for s, (_, c) in feas_cost.items() if abs(c - opt_cost) < 1e-9))
    if mixer == "x":
        random_base = math.factorial(N) / 2 ** n
    else:
        random_base = math.factorial(N) / N ** N

    # muestreo con shots (Aer), opcionalmente con ruido
    if ideal_sampling and not noise:
        # muestreo ideal directo desde la distribución exacta del estado (equivale a shots sin ruido)
        draws = np.random.default_rng(seed).choice(len(probs), size=shots, p=probs / probs.sum())
        uniq, cnts = np.unique(draws, return_counts=True)
        counts = {format(int(s), f"0{n}b"): int(c) for s, c in zip(uniq, cnts)}
    else:
        counts = _sample(qc, g, bt, theta, shots, seed, noise)
    tot = sum(counts.values())
    feas_shots, best_feas, mean_acc, nfeas = 0, math.inf, 0.0, 0
    best_feas_perm = None
    for bstr, cnt in counts.items():
        x = np.array([int(ch) for ch in bstr[::-1]]).reshape(N, N)
        perm = x_to_perm(x)
        if perm is not None:
            c = inst.cost(perm)
            feas_shots += cnt
            mean_acc += c * cnt
            if c < best_feas:
                best_feas, best_feas_perm = c, perm
    top = max(counts.items(), key=lambda kv: kv[1])[0]
    x_top = np.array([int(ch) for ch in top[::-1]]).reshape(N, N)
    top_perm = x_to_perm(x_top)
    rep_perm = repair(x_top)

    dist = sorted(((float(probs[s]), list(pm), c) for s, (pm, c) in feas_cost.items()),
                  reverse=True)[:keep_distribution]
    out = {
        "id": exp_id or f"N{N}-{mixer}-p{p}" + (f"-noise{noise}" if noise else ""),
        "N": N, "qubits": n, "mixer": mixer, "p": p, "lam": qubo.lam,
        "objective": objective, "alpha": alpha if objective == "cvar" else None,
        "shots": shots, "noise": f"depolarizing {noise}" if noise else "none",
        "params": [float(t) for t in theta], "hamiltonian_scale": float(scale),
        "objective_value": best[0],
        "p_feasible": p_feas,
        "feasible_fraction_shots": feas_shots / tot,
        "random_feasible_baseline": random_base,
        "p_optimal": p_opt,
        "optimum": float(opt),
        "best_feasible_cost": None if best_feas_perm is None else float(best_feas),
        "best_feasible_perm": best_feas_perm,
        "approx_ratio": None if best_feas_perm is None else float(opt / best_feas) if best_feas > 0 else 1.0,
        "mean_feasible_cost": None if feas_shots == 0 else mean_acc / feas_shots,
        # óptimo / costo medio de las muestras válidas (más informativo que el mejor de los shots)
        "mean_approx_ratio": None if feas_shots == 0 or mean_acc <= 0 else float(opt) / (mean_acc / feas_shots),
        "top_bitstring": top,
        "top_raw_feasible": top_perm is not None,
        "top_raw_energy_penalized": float(qubo.energy(x_top.ravel())),
        "top_repaired_perm": rep_perm,
        "top_repaired_cost": float(inst.cost(rep_perm)),
        "evals": evals, "time_s": time.perf_counter() - t0,
        "perm_distribution": [{"perm": pm, "cost": c, "prob": pr} for pr, pm, c in dist],
    }
    if compute_stats:
        out.update(circuit_stats(qc, {**{g[i]: theta[i] for i in range(p)},
                                      **{bt[i]: theta[p + i] for i in range(p)}}))
    return out


def _sample(qc, g, bt, theta, shots, seed, noise):
    p = len(g)
    binds = {**{g[i]: float(theta[i]) for i in range(p)},
             **{bt[i]: float(theta[p + i]) for i in range(p)}}
    c = qc.assign_parameters(binds)
    c.measure_all()
    if _HAS_AER:
        if noise:
            sim = AerSimulator(noise_model=_noise_model(noise), seed_simulator=seed)
            tc = transpile(c, basis_gates=["cx", "rz", "sx", "x"], optimization_level=1,
                           seed_transpiler=seed)
        else:
            sim = _statevector_sim()
            tc = c
        return sim.run(tc, shots=shots, seed_simulator=seed).result().get_counts()
    from qiskit.primitives import StatevectorSampler
    res = StatevectorSampler(seed=seed).run([c], shots=shots).result()
    return res[0].data.meas.get_counts()


def solve_subproblem_qaoa(inst: QAPInstance, p: int = 1, shots: int = 512, seed: int = 0,
                          init_params=None, maxiter: int = 30, alpha: float = 0.25):
    """Versión ligera para el híbrido: devuelve (mejor_perm_factible | None, params, info).
    Parámetros con arranque en caliente (warm start) desde el subproblema anterior."""
    r = run_qaoa(inst, p=p, mixer="xy", objective="cvar", alpha=alpha, restarts=1,
                 maxiter=maxiter, shots=shots, seed=seed, init_params=init_params,
                 keep_distribution=0, compute_stats=False, ideal_sampling=True)
    return r["best_feasible_perm"], np.array(r["params"]), r
