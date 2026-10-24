import numpy as np, itertools, time, sys, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from qgate.instance import QAPInstance
from qgate.mps import write_linearized_mps, recover_qap
from qgate.classical import brute_force, simulated_annealing, gilmore_lawler_bound, local_search, swap_delta
from qgate.qubo import build_qubo, feasible_mask, index_to_x, x_to_perm

TMP = tempfile.mkdtemp(prefix="qgate_")
inst = QAPInstance.synthetic(10, seed=3)
# cost checks
p = np.random.default_rng(0).permutation(10)
F, D = inst.F, inst.D
manual = sum(F[i,k]*D[p[i],p[k]] for i in range(10) for k in range(i+1,10))
assert abs(manual - inst.cost(p)) < 1e-9, (manual, inst.cost(p))
x = np.zeros((10,10)); x[np.arange(10), p] = 1
assert abs(inst.cost_x(x) - manual) < 1e-9
# swap delta
for _ in range(50):
    a,b = np.random.default_rng(_).choice(10,2,replace=False)
    q = p.copy(); q[a],q[b]=q[b],q[a]
    assert abs(swap_delta(inst,p,a,b) - (inst.cost(q)-inst.cost(p))) < 1e-9
print("costs ok")
# MPS roundtrip (opaque names, shuffled rows)
write_linearized_mps(inst, os.path.join(TMP, "test.mps.gz"), opaque_names=True, shuffle_seed=1)
rec = recover_qap(os.path.join(TMP, "test.mps.gz"))
print(rec.report)
for tag, cand in rec.candidates.items():
    print(tag, "maxdiff T:", np.abs(cand.T - inst.T).max(), "resid", cand.meta["factorization_residual"])
c = rec.candidates["orden_columnas"]
assert np.abs(c.T - inst.T).max() < 1e-9
assert np.allclose(np.outer(c.F[np.triu_indices(10,1)], 1), np.outer(c.F[np.triu_indices(10,1)],1))
# named version
write_linearized_mps(inst, os.path.join(TMP, "test_named.mps"), opaque_names=False)
rec2 = recover_qap(os.path.join(TMP, "test_named.mps"))
print("named candidates", rec2.report["candidates"], np.abs(rec2.candidates["nombres"].T - inst.T).max())
# subinstances
for n in (3,4):
    s = inst.subinstance(n); print("sub", n, brute_force(s)["cost"])
t=time.perf_counter(); bf = brute_force(inst); print("BF N=10", bf["cost"], bf["n_optimal_perms"], round(bf["time_s"],1),"s")
sa = simulated_annealing(inst, iters=30000, restarts=3, seed=1); print("SA", sa["cost"], round(sa["time_s"],2))
gl = gilmore_lawler_bound(inst); print("GLB", gl["bound"], round(gl["time_s"],3))
assert gl["bound"] <= bf["cost"] + 1e-9
ls = local_search(inst, np.random.default_rng(5).permutation(10)); print("LS", ls["cost"])
# QUBO check N=3
s3 = inst.subinstance(3); q = build_qubo(s3)
E = q.energies_all(); bits = q.all_bits(); fm = feasible_mask(3, bits)
for sidx in np.where(fm)[0]:
    perm = x_to_perm(index_to_x(int(sidx),3)); assert abs(E[sidx]-s3.cost(perm))<1e-9
print("QUBO feasible energies == costs; min E overall", E.min(), "min feasible", E[fm].min(), "lam", q.lam)
assert E.argmin() in np.where(fm)[0]
# ising check
h,J,off = q.to_ising()
z = 1-2*bits.astype(float)
Ei = off + z@h + sum(val*z[:,v]*z[:,w] for (v,w),val in J.items())
assert np.allclose(Ei, E); print("ising ok")
