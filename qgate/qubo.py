"""QUBO con penalidades y su Hamiltoniano de Ising.

Variables: x_ij -> índice v = i*N + j  (qubit v en Qiskit).

H(x) = C(x) + lam * sum_i (sum_j x_ij - 1)^2 + lam * sum_j (sum_i x_ij - 1)^2

Con x = (1 - Z)/2: el qubit en |1> significa x = 1.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import linear_sum_assignment

from .instance import QAPInstance


@dataclass
class QUBO:
    A: np.ndarray        # (n, n) triangular superior: términos x_v x_w (v < w)
    b: np.ndarray        # (n,) términos lineales
    c: float             # constante
    N: int               # lado (n = N*N)
    lam: float

    @property
    def n(self) -> int:
        return self.N * self.N

    def energy(self, xvec) -> float:
        x = np.asarray(xvec, dtype=float)
        return float(x @ self.A @ x + self.b @ x + self.c)

    def all_bits(self) -> np.ndarray:
        n = self.n
        if n > 22:
            raise ValueError("Enumeración completa limitada a 22 variables")
        s = np.arange(2 ** n, dtype=np.int64)
        return ((s[:, None] >> np.arange(n)[None, :]) & 1).astype(np.int8)

    def energies_all(self, bits: np.ndarray | None = None) -> np.ndarray:
        """Energía para cada estado de la base (índice entero = bits de los qubits)."""
        B = self.all_bits() if bits is None else bits
        Bf = B.astype(np.float64)
        return np.einsum("sv,vw,sw->s", Bf, self.A, Bf) + Bf @ self.b + self.c

    def to_ising(self):
        """Devuelve (h, J, offset) con H = offset + sum h_v Z_v + sum J_vw Z_v Z_w."""
        n = self.n
        Asym = self.A + self.A.T
        h = -self.b / 2.0 - Asym.sum(axis=1) / 4.0
        J = {}
        for v in range(n):
            for w in range(v + 1, n):
                if self.A[v, w] != 0:
                    J[(v, w)] = self.A[v, w] / 4.0
        offset = self.c + self.b.sum() / 2.0 + self.A.sum() / 4.0
        return h, J, offset

    def to_sparse_pauli_op(self):
        from qiskit.quantum_info import SparsePauliOp
        h, J, offset = self.to_ising()
        terms = [("Z", [v], float(h[v])) for v in range(self.n) if abs(h[v]) > 0]
        terms += [("ZZ", [v, w], float(val)) for (v, w), val in J.items()]
        op = SparsePauliOp.from_sparse_list(terms, num_qubits=self.n)
        return op, offset


def lambda_auto(inst: QAPInstance) -> float:
    """lam0 = máxima contribución posible de una sola asignación x_ij = 1:
        max_ij ( L_ij + sum_{k != i} max_{l != j} T[i,j,k,l] )
    Quitar o duplicar una asignación cambia el costo como mucho en lam0, y viola
    al menos una restricción (penalidad >= lam). Por eso lam ~ lam0 es el punto de partida
    y se valida con un barrido (fracción factible vs calidad)."""
    n = inst.N
    best = 0.0
    for i in range(n):
        for j in range(n):
            s = inst.L[i, j]
            for k in range(n):
                if k != i:
                    s += inst.T[i, j, k].max()
            best = max(best, s)
    return float(max(best, 1.0))


def build_qubo(inst: QAPInstance, lam: float | None = None) -> QUBO:
    N = inst.N
    n = N * N
    lam = lambda_auto(inst) if lam is None else float(lam)
    A = np.zeros((n, n))
    b = np.zeros(n)
    c = inst.const
    for i in range(N):
        for j in range(N):
            v = i * N + j
            b[v] += inst.L[i, j]
            for k in range(i + 1, N):
                for l in range(N):
                    w = k * N + l
                    if inst.T[i, j, k, l] != 0:
                        A[v, w] += inst.T[i, j, k, l]
    # penalidades: lam * (sum x - 1)^2 = lam * (-sum x + 2 sum_{pares} x x + 1)
    for i in range(N):
        for j in range(N):
            v = i * N + j
            b[v] += -2.0 * lam
            for l in range(j + 1, N):            # misma fila
                A[v, i * N + l] += 2.0 * lam
            for k in range(i + 1, N):            # misma columna
                A[v, k * N + j] += 2.0 * lam
    c += 2.0 * N * lam
    return QUBO(A=np.triu(A, 1), b=b, c=float(c), N=N, lam=lam)


# --------------------------------------------------------------- decodificar
def index_to_x(s: int, N: int) -> np.ndarray:
    n = N * N
    bits = (s >> np.arange(n)) & 1
    return bits.reshape(N, N)


def bitstring_to_x(bitstr: str, N: int) -> np.ndarray:
    """Qiskit devuelve el qubit 0 a la DERECHA (little-endian)."""
    bits = np.array([int(ch) for ch in bitstr[::-1]], dtype=int)
    return bits.reshape(N, N)


def x_to_perm(x: np.ndarray) -> list[int] | None:
    if not QAPInstance.is_permutation_matrix(x):
        return None
    return [int(np.argmax(row)) for row in x]


def repair(x: np.ndarray) -> list[int]:
    """Permutación más cercana a x (máxima coincidencia), vía asignación lineal.
    Se reporta SIEMPRE por separado del resultado crudo."""
    r, c = linear_sum_assignment(-np.asarray(x, dtype=float))
    perm = [0] * len(r)
    for i, j in zip(r, c):
        perm[i] = int(j)
    return perm


def feasible_mask(N: int, bits: np.ndarray) -> np.ndarray:
    X = bits.reshape(-1, N, N)
    return (X.sum(axis=2) == 1).all(axis=1) & (X.sum(axis=1) == 1).all(axis=1)
