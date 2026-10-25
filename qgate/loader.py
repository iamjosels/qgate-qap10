"""Cargador de instancias oficiales (etapa 3, N >= 14) con validaciones.

Uso:
    python -m qgate.loader F.npy D.npy            # también .csv / .txt (np.loadtxt)
    python -m qgate.loader instancia.json         # {"F": [[...]], "D": [[...]]}
    python -m qgate.loader instancia.npz          # arrays F y D
    python -m qgate.loader instancia.dat          # formato QAPLIB (n, A, B)
    python -m qgate.loader instancia.mps.gz       # MPS linealizado como qap10

Convención del proyecto: cada par se cuenta una vez, C = sum_{i<k} F_ik D_{pi(i) pi(k)}.
F puede venir simétrica o triangular superior (se usa F_ik con i<k); si viene triangular inferior se
transpone y se avisa. D debe ser simétrica con diagonal cero. Todo se reporta, nada se corrige en silencio.
"""
from __future__ import annotations

import json
import os
import sys
import time
import tracemalloc

import numpy as np

from .instance import QAPInstance


def _read_matrix(path: str) -> np.ndarray:
    if path.endswith(".npy"):
        return np.load(path)
    delim = "," if path.endswith(".csv") else None
    return np.loadtxt(path, delimiter=delim)


def validate(F: np.ndarray, D: np.ndarray) -> tuple[np.ndarray, np.ndarray, dict]:
    checks, warn = {}, []
    for name, M in (("F", F), ("D", D)):
        if M.ndim != 2 or M.shape[0] != M.shape[1]:
            raise ValueError(f"{name} no es una matriz cuadrada: forma {M.shape}")
    if F.shape != D.shape:
        raise ValueError(f"N incoherente: F {F.shape} y D {D.shape}")
    n = F.shape[0]
    up, lo = np.triu(F, 1), np.tril(F, -1)
    if np.allclose(F, F.T):
        checks["F"] = "simétrica"
    elif np.allclose(lo, 0):
        checks["F"] = "triangular superior"
    elif np.allclose(up, 0):
        F = F.T.copy()
        checks["F"] = "triangular inferior (transpuesta)"
        warn.append("F venía triangular inferior: se transpuso")
    else:
        checks["F"] = "no simétrica ni triangular"
        warn.append("F no es simétrica ni triangular: con la convención de pares se usa solo F_ik con i<k")
    checks["D_simetrica"] = bool(np.allclose(D, D.T))
    if not checks["D_simetrica"]:
        warn.append("D no es simétrica")
    checks["diag_F_cero"] = bool(np.allclose(np.diag(F), 0))
    checks["diag_D_cero"] = bool(np.allclose(np.diag(D), 0))
    if not checks["diag_D_cero"]:
        warn.append("D tiene diagonal distinta de cero (no afecta al costo de pares)")
    checks["no_negativos"] = bool((F >= 0).all() and (D >= 0).all())
    checks["N"] = n
    checks["avisos"] = warn
    return F, D, checks


def load_official(*paths: str, convention: str = "pair_once") -> tuple[QAPInstance, dict]:
    """Devuelve (instancia, reporte). Rotula la instancia como 'oficial'."""
    tracemalloc.start()
    t0 = time.perf_counter()
    p0 = paths[0]
    name = os.path.basename(p0).split(".")[0]
    if p0.endswith((".mps", ".mps.gz")):
        from .mps import recover_qap
        rec = recover_qap(p0, name=name)
        F, D = rec.instance.F, rec.instance.D
    elif p0.endswith(".dat"):
        q = QAPInstance.from_qaplib(p0, convention="pair_once")
        F, D = q.F, q.D
    elif p0.endswith(".json"):
        z = json.load(open(p0, encoding="utf-8"))
        F, D = np.array(z["F"], dtype=float), np.array(z["D"], dtype=float)
    elif p0.endswith(".npz"):
        z = np.load(p0)
        F, D = z["F"], z["D"]
    else:
        if len(paths) < 2:
            raise ValueError("Para .npy/.csv/.txt pasa dos archivos: F y D")
        F, D = _read_matrix(paths[0]), _read_matrix(paths[1])
    F, D, checks = validate(np.asarray(F, dtype=float), np.asarray(D, dtype=float))
    inst = QAPInstance.from_FD(F, D, name=name, convention=convention, meta={"origen": "oficial", "files": list(paths)})
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    rep = {"name": name, "origen": "oficial", **checks, "load_time_s": time.perf_counter() - t0, "load_peak_mem_mb": peak / 1e6}
    return inst, rep


if __name__ == "__main__":
    inst, rep = load_official(*sys.argv[1:])
    print(json.dumps(rep, ensure_ascii=False, indent=1))
