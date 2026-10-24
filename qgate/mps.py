"""Lectura del MPS linealizado de qap10 y reconstrucción del modelo cuadrático.

Estrategia (no depende de los nombres de las variables):

1. Parsear el MPS (libre/fijo, .gz o texto).
2. Restricciones de asignación = filas con rhs = 1 y todos los coeficientes = 1.
   Sus variables son las x_ij (deben ser N*N, y 2N filas).
3. Separar esas 2N filas en dos familias (las que no se cruzan con la primera fila
   son de su misma familia). Familia A -> índice i (elemento), familia B -> j (ubicación).
4. Cada variable y del modelo linealizado aparece en restricciones de enlace junto a
   exactamente dos x: x_ij y x_kl. Su coeficiente objetivo es F_ik * D_jl.
   Así se recupera el tensor T sin conocer la nomenclatura del archivo.
5. Factorizar T en F y D (rango 1 por par) y reportar el residuo.

El orden de los índices (qué elemento es el 0, el 1, ...) importa para las
subinstancias "primeras N filas y columnas". Se generan varias candidatas
(números en los nombres, orden de columnas, orden de filas) y el benchmark elige la
que reproduce los óptimos de control 24 (N=3) y 32 (N=4).
"""
from __future__ import annotations

import gzip
import itertools
import math
import re
from collections import defaultdict
from dataclasses import dataclass, field

import numpy as np

from .instance import QAPInstance


@dataclass
class MPSModel:
    name: str = ""
    obj_row: str | None = None
    sense: int = 1                      # 1 = minimizar, -1 = maximizar
    row_types: dict = field(default_factory=dict)
    row_order: list = field(default_factory=list)
    cols: dict = field(default_factory=dict)        # col -> {row: val}
    col_order: list = field(default_factory=list)
    rhs: dict = field(default_factory=dict)
    integer_cols: set = field(default_factory=set)


def read_mps(path: str) -> MPSModel:
    opener = gzip.open if path.endswith(".gz") else open
    m = MPSModel()
    section = None
    in_int = False
    with opener(path, "rt", errors="replace") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("*"):
                continue
            if not line[0].isspace():
                tok = line.split()
                section = tok[0].upper()
                if section == "NAME":
                    m.name = tok[1] if len(tok) > 1 else ""
                elif section == "OBJSENSE" and len(tok) > 1:
                    m.sense = -1 if tok[1].upper().startswith("MAX") else 1
                if section == "ENDATA":
                    break
                continue
            tok = line.split()
            if section == "OBJSENSE":
                m.sense = -1 if tok[0].upper().startswith("MAX") else 1
            elif section == "ROWS":
                t, r = tok[0].upper(), tok[1]
                m.row_types[r] = t
                m.row_order.append(r)
                if t == "N" and m.obj_row is None:
                    m.obj_row = r
            elif section == "COLUMNS":
                if any("MARKER" in t.upper() for t in tok):
                    if any("INTORG" in t.upper() for t in tok):
                        in_int = True
                    elif any("INTEND" in t.upper() for t in tok):
                        in_int = False
                    continue
                c = tok[0]
                if c not in m.cols:
                    m.cols[c] = {}
                    m.col_order.append(c)
                if in_int:
                    m.integer_cols.add(c)
                rest = tok[1:]
                for r, v in zip(rest[0::2], rest[1::2]):
                    m.cols[c][r] = m.cols[c].get(r, 0.0) + float(v)
            elif section == "RHS":
                rest = tok[1:] if len(tok) % 2 == 1 else tok
                for r, v in zip(rest[0::2], rest[1::2]):
                    m.rhs[r] = float(v)
            # BOUNDS / RANGES no se necesitan para reconstruir el QAP
    if m.obj_row is None:
        raise ValueError("El MPS no tiene fila objetivo (tipo N)")
    return m


@dataclass
class Recovery:
    instance: QAPInstance
    candidates: dict                    # estrategia -> QAPInstance
    report: dict


def _ints_in(name: str) -> list[int]:
    return [int(t) for t in re.findall(r"\d+", name)]


def recover_qap(path: str, name: str = "qap10") -> Recovery:
    m = read_mps(path)
    obj = m.obj_row
    sense = m.sense

    # filas -> {col: coef} (sin objetivo)
    row_vars: dict[str, dict[str, float]] = defaultdict(dict)
    obj_coef: dict[str, float] = {}
    for c, entries in m.cols.items():
        for r, v in entries.items():
            if r == obj:
                obj_coef[c] = sense * v
            else:
                row_vars[r][c] = v

    # 1) filas de asignación
    assign_rows = [r for r in m.row_order
                   if r in row_vars and m.row_types.get(r) == "E"
                   and abs(m.rhs.get(r, 0.0) - 1.0) < 1e-9
                   and all(abs(v - 1.0) < 1e-9 for v in row_vars[r].values())]
    xvars = set()
    for r in assign_rows:
        xvars |= set(row_vars[r])
    N = int(round(math.sqrt(len(xvars))))
    if N * N != len(xvars) or len(assign_rows) != 2 * N:
        raise ValueError(f"Estructura inesperada: {len(xvars)} variables x en "
                         f"{len(assign_rows)} filas de asignación")

    # 2) dos familias
    r0 = assign_rows[0]
    s0 = set(row_vars[r0])
    famA = [r for r in assign_rows if r == r0 or not (set(row_vars[r]) & s0)]
    famB = [r for r in assign_rows if r not in famA]
    assert len(famA) == N and len(famB) == N, "No se pudieron separar las familias"
    rowA = {c: a for a, r in enumerate(famA) for c in row_vars[r]}
    rowB = {c: b for b, r in enumerate(famB) for c in row_vars[r]}

    # 3) variables y -> par de x
    x_rows: dict[str, set] = defaultdict(set)   # x -> filas de enlace donde aparece
    col_rows: dict[str, list] = defaultdict(list)
    assign_set = set(assign_rows)
    for r, vs in row_vars.items():
        if r in assign_set:
            continue
        for c in vs:
            col_rows[c].append(r)
    yvars = [c for c in m.col_order if c not in xvars]
    pairs = {}
    bad = 0
    for y in yvars:
        xs = set()
        for r in col_rows.get(y, []):
            xs |= {c for c in row_vars[r] if c in xvars}
        if len(xs) != 2:
            bad += 1
            continue
        a, b = sorted(xs, key=lambda c: (rowA[c], rowB[c]))
        pairs[y] = (a, b)

    # linear y constante
    lin_x = {c: obj_coef.get(c, 0.0) for c in xvars}
    obj_const = -sense * m.rhs.get(obj, 0.0)    # convención habitual: rhs del objetivo = -offset

    # 4) candidatas de orden de índices
    def build(idx_of_x: dict[str, tuple[int, int]], tag: str) -> QAPInstance:
        T = np.zeros((N, N, N, N))
        L = np.zeros((N, N))
        for c, (i, j) in idx_of_x.items():
            L[i, j] += lin_x[c]
        for y, (a, b) in pairs.items():
            cy = obj_coef.get(y, 0.0)
            if cy == 0.0:
                continue
            i, j = idx_of_x[a]
            k, l = idx_of_x[b]
            T[i, j, k, l] += cy
            T[k, l, i, j] += cy
        inst = QAPInstance(T=T, L=L, const=obj_const, name=name,
                           meta={"source": "mps", "index_strategy": tag})
        _attach_factorization(inst)
        return inst

    candidates: dict[str, QAPInstance] = {}
    # (a) números en los nombres de x
    nums = {c: _ints_in(c) for c in xvars}
    if all(len(v) >= 2 for v in nums.values()):
        a_vals = sorted({v[-2] for v in nums.values()})
        b_vals = sorted({v[-1] for v in nums.values()})
        if len(a_vals) == N and len(b_vals) == N:
            ia = {v: k for k, v in enumerate(a_vals)}
            ib = {v: k for k, v in enumerate(b_vals)}
            idx = {c: (ia[v[-2]], ib[v[-1]]) for c, v in nums.items()}
            if len(set(idx.values())) == N * N:
                candidates["nombres"] = build(idx, "nombres")
    # (b) orden de aparición de las x en COLUMNS
    xorder = [c for c in m.col_order if c in xvars]
    pos = {c: t for t, c in enumerate(xorder)}
    firstA = sorted(range(N), key=lambda a: min(pos[c] for c in row_vars[famA[a]]))
    firstB = sorted(range(N), key=lambda b: min(pos[c] for c in row_vars[famB[b]]))
    ra = {a: t for t, a in enumerate(firstA)}
    rb = {b: t for t, b in enumerate(firstB)}
    candidates["orden_columnas"] = build({c: (ra[rowA[c]], rb[rowB[c]]) for c in xvars},
                                         "orden_columnas")
    # (c) orden de las filas en ROWS
    candidates["orden_filas"] = build({c: (rowA[c], rowB[c]) for c in xvars}, "orden_filas")

    first = next(iter(candidates.values()))
    report = {
        "name": m.name, "N": N, "n_cols": len(m.cols), "n_rows": len(m.row_order) - 1,
        "n_x": len(xvars), "n_y": len(yvars), "y_mapped": len(pairs), "y_unmapped": bad,
        "y_expected": (N * (N - 1) // 2) * (N * (N - 1)),
        "objective_constant": obj_const, "sense": "min" if sense == 1 else "max",
        "linear_terms_nonzero": int(sum(1 for v in lin_x.values() if v != 0)),
        "candidates": list(candidates),
        "factorization_residual": first.meta.get("factorization_residual"),
    }
    return Recovery(instance=first, candidates=candidates, report=report)


def _attach_factorization(inst: QAPInstance) -> None:
    """Intenta escribir T[i,j,k,l] = F_ik D_jl (i<k). Guarda F, D y el residuo relativo."""
    n = inst.N
    iu, ku = np.triu_indices(n, 1)
    V = np.stack([inst.T[i, :, k, :].ravel() for i, k in zip(iu, ku)])   # (pares, n*n)
    if not np.any(V):
        inst.meta["factorization_residual"] = None
        return
    U, S, Wt = np.linalg.svd(V, full_matrices=False)
    d = Wt[0] * S[0]
    f = U[:, 0]
    if d.sum() < 0:
        d, f = -d, -f
    pos = d[d > 1e-9]
    scale = pos.min() if pos.size else 1.0
    d = d / scale
    # redondeo a enteros si corresponde
    if np.allclose(d, np.round(d), atol=1e-6):
        d = np.round(d)
    f = V @ d / (d @ d)
    if np.allclose(f, np.round(f), atol=1e-6):
        f = np.round(f)
    # reescalar para que D sea entera con mcd 1 y F entera si es posible
    resid = np.linalg.norm(V - np.outer(f, d)) / max(np.linalg.norm(V), 1e-12)
    F = np.zeros((n, n))
    F[iu, ku] = f
    F = F + F.T
    D = d.reshape(n, n)
    inst.F, inst.D = F, D
    inst.meta["factorization_residual"] = float(resid)


# ---------------------------------------------------------------------------
# Escritor de MPS sintético con la MISMA estructura (para probar el parser)
# ---------------------------------------------------------------------------
def write_linearized_mps(inst: QAPInstance, path: str, opaque_names: bool = True,
                         shuffle_seed: int | None = None) -> None:
    """Escribe el QAP linealizado (x + y con i<k, j!=l; 2N filas de asignación;
    filas de enlace por elemento y por ubicación). Formato equivalente al de MIPLIB."""
    n = inst.N
    rng = np.random.default_rng(shuffle_seed) if shuffle_seed is not None else None
    xname = {}
    cols = {}
    rows = []
    rhs = {}
    t = 0

    def newc():
        nonlocal t
        t += 1
        return f"C{t:05d}"

    for i in range(n):
        for j in range(n):
            xname[i, j] = newc() if opaque_names else f"x#{i+1}#{j+1}"
            cols[xname[i, j]] = {}
    for i in range(n):
        r = f"R_a{i}"
        rows.append(r); rhs[r] = 1.0
        for j in range(n):
            cols[xname[i, j]][r] = 1.0
    for j in range(n):
        r = f"R_b{j}"
        rows.append(r); rhs[r] = 1.0
        for i in range(n):
            cols[xname[i, j]][r] = 1.0
    yname = {}
    for i in range(n):
        for k in range(i + 1, n):
            for j in range(n):
                for l in range(n):
                    if j == l:
                        continue
                    nm = newc() if opaque_names else f"y#{i+1}#{j+1}#{k+1}#{l+1}"
                    yname[i, j, k, l] = nm
                    c = inst.T[i, j, k, l]
                    cols[nm] = {"OBJ": c} if c != 0 else {}
    # enlaces: por (i,j,k): sum_l y = x_ij ; por (i,j,l): sum_k y = x_ij
    for (i, j, k, l), nm in yname.items():
        for (a, b, other_e, other_loc) in ((i, j, k, l), (k, l, i, j)):
            re_ = f"E_{a}_{b}_e{other_e}"
            rl_ = f"E_{a}_{b}_l{other_loc}"
            for r in (re_, rl_):
                cols[nm][r] = 1.0
                cols[xname[a, b]][r] = -1.0
                if r not in rhs:
                    rows.append(r); rhs[r] = 0.0
    order = list(cols)
    if rng is not None:
        rng.shuffle(rows)
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "wt") as fh:
        fh.write(f"NAME          {inst.name}\nROWS\n N  OBJ\n")
        for r in rows:
            fh.write(f" E  {r}\n")
        fh.write("COLUMNS\n    MARKER                 'MARKER'                 'INTORG'\n")
        for c in order:
            for r, v in cols[c].items():
                fh.write(f"    {c}  {r}  {v:g}\n")
        fh.write("    MARKER                 'MARKER'                 'INTEND'\nRHS\n")
        for r in rows:
            if rhs[r] != 0:
                fh.write(f"    RHS  {r}  {rhs[r]:g}\n")
        fh.write("BOUNDS\n")
        for c in order:
            fh.write(f" UP BND  {c}  1\n")
        fh.write("ENDATA\n")
