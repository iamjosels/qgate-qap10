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
