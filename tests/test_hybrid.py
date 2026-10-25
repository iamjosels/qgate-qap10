import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from qgate.instance import QAPInstance
from qgate.hybrid import qgate_lns, build_subproblem
inst = QAPInstance.synthetic(10, seed=3)  # optimo 211
perm = np.random.default_rng(1).permutation(10)
sub = build_subproblem(inst, perm, [1,4,7])
assert abs(sub.cost([0,1,2]) - inst.cost(perm)) < 1e-9
q = perm.copy(); q[[1,4,7]] = perm[[4,7,1]]
assert abs(sub.cost([1,2,0]) - inst.cost(q)) < 1e-9
print("subproblem ok")
for solver in ("exact","qaoa"):
    t=time.perf_counter()
    r = qgate_lns(inst, iters=150 if solver=="exact" else 80, solver=solver, seed=2)
    print(solver, {k:r[k] for k in ["start_cost","final_cost","polished_cost","improvements","subproblems","qaoa_sub_success_rate","no_feasible_sample","peak_mem_mb"]}, round(time.perf_counter()-t,1),"s")
    fp = list(r["final_perm"])
    assert sorted(fp) == list(range(10))                                   # permutación válida
    manual = sum(inst.F[i, k] * inst.D[fp[i], fp[k]] for i in range(10) for k in range(i + 1, 10))
    assert abs(manual - r["final_cost"]) < 1e-9, (manual, r["final_cost"])
    bests = [h["best"] for h in r["history"]]
    assert all(b2 <= b1 + 1e-9 for b1, b2 in zip(bests, bests[1:]))      # el mejor nunca sube
    for e1, e2 in zip(r["events"], r["events"][1:]):
        assert sorted(e2["perm"]) == list(range(10))
        if e2["type"] != "kick":
            assert e2["cost"] <= e1["cost"] + 1e-9, (e1, e2)               # solo la perturbación sube el costo
    if solver == "exact":
        r2 = qgate_lns(inst, iters=150, solver="exact", seed=2)
        assert list(r2["final_perm"]) == fp and r2["final_cost"] == r["final_cost"]   # misma semilla, mismo resultado
print("hybrid asserts ok")
