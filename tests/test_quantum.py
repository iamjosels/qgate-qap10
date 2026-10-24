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
