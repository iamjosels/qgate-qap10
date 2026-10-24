"""Representación de una instancia QAP en la convención del archivo qap10.

Convención (cada par se cuenta UNA sola vez):

    C(pi) = const + sum_i L[i, pi_i] + sum_{i<k} T[i, pi_i, k, pi_k]

Para el caso Koopmans-Beckmann del reto: T[i, j, k, l] = F[i, k] * D[j, l] con i < k.
T se guarda simétrico (T[i,j,k,l] == T[k,l,i,j]) para simplificar los deltas,
con T[i,:,i,:] = 0 y T[:,j,:,j] = 0 (dos elementos en la misma ubicación no tienen costo
definido en el modelo linealizado; esas asignaciones son infactibles igual).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class QAPInstance:
    T: np.ndarray                 # (N, N, N, N) simétrico
    L: np.ndarray                 # (N, N) términos lineales (normalmente 0)
    const: float = 0.0
    F: np.ndarray | None = None   # flujo (si la factorización existe)
    D: np.ndarray | None = None   # distancia (si la factorización existe)
    name: str = "qap"
    meta: dict = field(default_factory=dict)

    # ------------------------------------------------------------------ básicos
    @property
    def N(self) -> int:
        return int(self.L.shape[0])

    def cost(self, perm) -> float:
        """Costo de una asignación factible. perm[i] = ubicación del elemento i."""
        p = np.asarray(perm, dtype=int)
        n = self.N
        idx = np.arange(n)
        M = self.T[idx[:, None], p[:, None], idx[None, :], p[None, :]]
        return float(np.triu(M, 1).sum() + self.L[idx, p].sum() + self.const)

    def cost_batch(self, P: np.ndarray) -> np.ndarray:
        """Costos de un lote de permutaciones P con forma (B, N)."""
        P = np.asarray(P, dtype=int)
        n = self.N
        iu, ku = np.triu_indices(n, 1)
        pair = self.T[iu[None, :], P[:, iu], ku[None, :], P[:, ku]].sum(axis=1)
        lin = self.L[np.arange(n)[None, :], P].sum(axis=1)
        return pair + lin + self.const

    def cost_x(self, x: np.ndarray) -> float:
        """Costo del modelo (sin penalidades) para una matriz binaria x (N, N).
        Coincide con cost(perm) cuando x es una permutación."""
        x = np.asarray(x, dtype=float)
        quad = 0.5 * np.einsum("ij,ijkl,kl->", x, self.T, x)
        return float(quad + (self.L * x).sum() + self.const)

    @staticmethod
    def is_permutation_matrix(x: np.ndarray) -> bool:
        x = np.asarray(x)
        return bool((x.sum(0) == 1).all() and (x.sum(1) == 1).all())

    def subinstance(self, n: int) -> "QAPInstance":
        """Primeras n filas y columnas (elementos 0..n-1, ubicaciones 0..n-1)."""
        return QAPInstance(
            T=self.T[:n, :n, :n, :n].copy(),
            L=self.L[:n, :n].copy(),
            const=self.const,
            F=None if self.F is None else self.F[:n, :n].copy(),
            D=None if self.D is None else self.D[:n, :n].copy(),
            name=f"{self.name}[:{n}]",
            meta={**self.meta, "parent": self.name, "sub_n": n},
        )

    # ------------------------------------------------------------ constructores
    @classmethod
    def from_FD(cls, F, D, name: str = "qap", convention: str = "pair_once",
                meta: dict | None = None) -> "QAPInstance":
        """Construye T desde F (flujos) y D (distancias).

        convention="pair_once": C = sum_{i<k} F_ik D_{pi_i pi_k}  (convención qap10)
        convention="full":      C = sum_{i!=k} F_ik D_{pi_i pi_k} + sum_i F_ii D_{pi_i pi_i} (QAPLIB)
        """
        F = np.asarray(F, dtype=float)
        D = np.asarray(D, dtype=float)
        n = F.shape[0]
        U = np.einsum("ik,jl->ijkl", F, D)                 # F_ik D_jl
        I = np.arange(n)
        upper = (I[:, None] < I[None, :])[:, None, :, None]   # i<k sobre ejes 0 y 2
        if convention == "pair_once":
            Tpair = U
        elif convention == "full":
            Tpair = U + U.transpose(2, 3, 0, 1)              # F_ik D_jl + F_ki D_lj
        else:
            raise ValueError(convention)
        T = np.where(upper, Tpair, Tpair.transpose(2, 3, 0, 1))
        T[I, :, I, :] = 0.0
        T[:, I, :, I] = 0.0
        L = np.zeros((n, n))
        if convention == "full":
            L = np.outer(np.diag(F), np.diag(D))
        return cls(T=T, L=L, const=0.0, F=F.copy(), D=D.copy(), name=name,
                   meta={"convention": convention, **(meta or {})})

    @classmethod
    def synthetic(cls, n: int, seed: int = 0, density: float = 0.6,
                  name: str | None = None) -> "QAPInstance":
        """Instancia tipo Nugent: puertas en grilla (distancia Manhattan) y flujos
        enteros dispersos y simétricos. SOLO para pruebas de escalabilidad."""
        rng = np.random.default_rng(seed)
        cols = int(np.ceil(np.sqrt(n)))
        xy = np.array([(g % cols, g // cols) for g in range(n)], dtype=float)
        D = np.abs(xy[:, None, :] - xy[None, :, :]).sum(-1)
        F = rng.integers(1, 10, size=(n, n)).astype(float)
        F *= rng.random((n, n)) < density
        F = np.triu(F, 1)
        F = F + F.T
        inst = cls.from_FD(F, D, name=name or f"synthetic-{n}",
                           meta={"synthetic": True, "seed": seed, "gate_xy": xy.tolist()})
        return inst

    @classmethod
    def from_qaplib(cls, path: str, convention: str = "full") -> "QAPInstance":
        """Lee formato QAPLIB (n, matriz A, matriz B). Por defecto convención 'full'
        (la de QAPLIB). Usa convention='pair_once' para la convención de qap10."""
        with open(path) as fh:
            nums = [float(t) for t in fh.read().split()]
        n = int(nums[0])
        A = np.array(nums[1:1 + n * n]).reshape(n, n)
        B = np.array(nums[1 + n * n:1 + 2 * n * n]).reshape(n, n)
        return cls.from_FD(A, B, name=path.rsplit("/", 1)[-1], convention=convention)

    @classmethod
    def from_matrices_file(cls, path: str) -> "QAPInstance":
        """Lee un .npz con F y D (convención pair_once)."""
        z = np.load(path)
        return cls.from_FD(z["F"], z["D"], name=path.rsplit("/", 1)[-1])

    def save_FD(self, path: str) -> None:
        if self.F is None or self.D is None:
            raise ValueError("La instancia no tiene F y D factorizadas")
        np.savez(path, F=self.F, D=self.D)


def mds_2d(D: np.ndarray) -> np.ndarray:
    """Coordenadas 2D de las ubicaciones a partir de D por MDS clásico (para el mapa).

    B = -1/2 J D^2 J con J = I - 11^T/n; se toman los dos mayores autovalores de B.
    Solo es una proyección visual: D no tiene por qué ser euclidiana.
    """
    D = np.asarray(D, dtype=float)
    n = D.shape[0]
    J = np.eye(n) - np.ones((n, n)) / n
    B = -0.5 * J @ (D ** 2) @ J
    w, V = np.linalg.eigh(B)
    idx = np.argsort(w)[::-1][:2]
    return V[:, idx] * np.sqrt(np.clip(w[idx], 0.0, None))
