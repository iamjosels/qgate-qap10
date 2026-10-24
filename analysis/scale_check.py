"""Control de escala (P1.3): costo de la asignación óptima de N=10 contando cada par una y dos veces.

    python analysis/scale_check.py --mps data/qap10.mps.gz

Con la convención del archivo (cada par una vez) la asignación óptima cuesta 340; contando cada par dos
veces cuesta 680. Se calcula en código desde F y D recuperados del MPS y se guarda en results/extra.json.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from qgate.mps import recover_qap  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--mps", default="data/qap10.mps.gz")
a = ap.parse_args()
R = json.load(open(os.path.join(ROOT, "results", "results.json"), encoding="utf-8"))
rec = recover_qap(os.path.join(ROOT, a.mps))
inst = rec.candidates[R["data"]["index_strategy"]]
perm = np.array(next(v["perm"] for v in R["validation"] if v["n"] == R["meta"]["N"]))
F, D = inst.F, inst.D
n = len(perm)
once = sum(F[i, k] * D[perm[i], perm[k]] for i in range(n) for k in range(i + 1, n))
twice = sum(F[i, k] * D[perm[i], perm[k]] for i in range(n) for k in range(n) if k != i)
rep = rec.report
out = {"perm": perm.tolist(), "cost_pair_once": float(once), "cost_pair_twice": float(twice),
       "cost_inst_cost": float(inst.cost(perm)), "assignment_rows": 2 * n, "n_x": rep["n_x"], "n_y": rep["n_y"],
       "n_rows": rep["n_rows"], "factorization_residual": rep["factorization_residual"],
       "candidates": rep["candidates"], "command": "python analysis/scale_check.py --mps " + a.mps}
path = os.path.join(ROOT, "results", "extra.json")
ex = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
ex["scale_check"] = out
json.dump(ex, open(path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(json.dumps(out))
