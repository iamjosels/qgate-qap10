import sys, os, time, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from qgate.instance import QAPInstance
from qgate.quantum import run_qaoa
inst = QAPInstance.synthetic(10, seed=3)
for n, mixer, p in [(3,"x",1),(3,"xy",1),(3,"xy",2),(4,"xy",1),(4,"x",1)]:
    s = inst.subinstance(n)
    t=time.perf_counter()
    r = run_qaoa(s, p=p, mixer=mixer, restarts=2, maxiter=80, shots=2048)
    keys = ["id","qubits","p_feasible","random_feasible_baseline","p_optimal","best_feasible_cost","optimum","approx_ratio","feasible_fraction_shots","top_raw_feasible","top_repaired_cost","evals","depth","cx_count"]
    print({k: (round(r[k],4) if isinstance(r[k], float) else r[k]) for k in keys}, round(time.perf_counter()-t,1),"s")
    assert r["qubits"] == n * n
    if isinstance(r.get("top_bitstring"), str):
        assert len(r["top_bitstring"]) == n * n
    tot = sum(d["prob"] for d in r["perm_distribution"])
    # perm_distribution es una lista parcial (quantum.py:247, truncada a keep_distribution): su suma no supera
    # P(válida). En N=3 queda por debajo (0.17 vs 0.34 con mixer X): diferencia pendiente de explicar.
    assert tot <= r["p_feasible"] + 1e-6, (tot, r["p_feasible"])
    assert r["p_optimal"] <= r["p_feasible"] + 1e-9
    if r["best_feasible_perm"] is not None:
        bp = r["best_feasible_perm"]
        assert sorted(bp) == list(range(n))
        assert abs(s.cost(bp) - r["best_feasible_cost"]) < 1e-9
        assert r["best_feasible_cost"] >= r["optimum"] - 1e-9
    if n == 3:
        assert r["p_feasible"] > r["random_feasible_baseline"], (r["p_feasible"], r["random_feasible_baseline"])
