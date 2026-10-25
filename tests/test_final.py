import json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from qgate.instance import QAPInstance
from qgate.loader import load_official
from qgate.twophase import two_phase, tension

T = tempfile.mkdtemp(prefix="qgate_final_")
inst = QAPInstance.synthetic(14, seed=21)
p = np.random.default_rng(0).permutation(14)
np.savez(os.path.join(T, "i.npz"), F=inst.F, D=inst.D)
json.dump({"F": inst.F.tolist(), "D": inst.D.tolist()}, open(os.path.join(T, "i.json"), "w"))
np.save(os.path.join(T, "F.npy"), inst.F); np.save(os.path.join(T, "D.npy"), inst.D)
np.savetxt(os.path.join(T, "F.csv"), inst.F, delimiter=","); np.savetxt(os.path.join(T, "D.csv"), inst.D, delimiter=",")
np.savetxt(os.path.join(T, "Fl.txt"), np.tril(inst.F)); np.savetxt(os.path.join(T, "D.txt"), inst.D)
for args in (["i.npz"], ["i.json"], ["F.npy", "D.npy"], ["F.csv", "D.csv"], ["Fl.txt", "D.txt"]):
    li, rep = load_official(*[os.path.join(T, a) for a in args])
    assert li.N == 14 and rep["origen"] == "oficial"
    assert abs(li.cost(p) - inst.cost(p)) < 1e-9, (args, li.cost(p), inst.cost(p))
    print(args, rep["F"], rep["D_simetrica"], rep["avisos"])
try:
    np.save(os.path.join(T, "bad.npy"), np.zeros((14, 13)))
    load_official(os.path.join(T, "bad.npy"), os.path.join(T, "D.npy")); raise SystemExit("debió fallar")
except ValueError as e:
    print("rechaza no cuadrada:", e)
# tensión = sum_m F[i,m] D[pi(i),pi(m)] con F simétrica
t = tension(inst, p)
manual = np.array([sum(inst.F[i, m] * inst.D[p[i], p[m]] for m in range(14) if m != i) for i in range(14)])
assert np.allclose(t, manual)
# dos fases: factible, costo coherente y atribución que cuadra
r = two_phase(inst, solver="exact", select="tension", B=15, seed=1, shots=8)
assert r["feasible"] and abs(inst.cost(r["best_perm"]) - r["best_cost"]) < 1e-9
o = r["origin_at_best"]
assert abs(sum(v["reduction"] for v in o.values()) - (r["start_cost"] - r["best_cost"])) < 1e-6
print("two_phase ok", r["best_cost"], {k: v["moves"] for k, v in o.items()})
