"""Línea base honesta para las piezas de 3 vuelos del híbrido (P0.2) y del hardware N=3 (P0.4).

Uso:
    python analysis/baselines.py --mps data/qap10.mps.gz

No modifica results.json ni hardware.json. Repite las corridas del híbrido de semilla 7 (QAOA con 512 y
con 8 shots, mismos argumentos que el bench) registrando cada pieza visitada, verifica que el historial
coincide con el reportado y guarda en results/extra.json, por corrida:
  - p_opt_valido = n_óptimos / 6 (azar sobre las 6 permutaciones válidas de la pieza)
  - P(acierto con k muestras) = 1 - (1 - p)^k, promediado sobre piezas, para k = 8 y 512,
    con p = n_óptimos/6 (6 permutaciones válidas) y p = n_óptimos/27 (27 estados con una puerta por vuelo)
  - enumeración exacta = 100%
y, para el hardware N=3, P(óptimo) del azar: n_óptimos/27 (XY) y n_óptimos/512 (X).
"""
from __future__ import annotations

import argparse
import datetime as dt
import itertools
import json
import os
import platform
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from qgate.hybrid import qgate_lns  # noqa: E402
from qgate.mps import recover_qap  # noqa: E402


def versions():
    v = {"python": platform.python_version(), "numpy": np.__version__}
    for m in ("scipy", "qiskit", "qiskit_aer"):
        try:
            v[m] = __import__(m).__version__
        except Exception:
            v[m] = None
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mps", default="data/qap10.mps.gz")
    ap.add_argument("--only", choices=["qaoa", "qaoa_s8", "all"], default="all")
    args = ap.parse_args()
    R = json.load(open(os.path.join(ROOT, "results", "results.json"), encoding="utf-8"))
    a = R["meta"]["args"]
    seed, H = a["seed"], a.get("hybrid_iters") or (120 if a["quick"] else 300)
    inst = recover_qap(os.path.join(ROOT, args.mps)).candidates[R["data"]["index_strategy"]]
    Hs = {h["method"]: h for h in R["hybrid"]}
    out_path = os.path.join(ROOT, "results", "extra.json")
    extra = json.load(open(out_path, encoding="utf-8")) if os.path.exists(out_path) else {}
    runs = {"qaoa": ("qgate_lns_qaoa", 512), "qaoa_s8": ("qgate_lns_qaoa_s8", 8)}
    sel = runs if args.only == "all" else {args.only: runs[args.only]}
    for key, (method, shots) in sel.items():
        log = []
        start = np.random.default_rng(seed + 100).permutation(inst.N)
        h = qgate_lns(inst, k=3, iters=H, solver="qaoa", seed=seed, start_perm=start, shots=shots, piece_log=log)
        same = [x["best"] for x in h["history"]] == [x["best"] for x in Hs[method]["history"]]
        n = np.array([p["n_opt"] for p in log], dtype=float)
        stats = {"method": method, "shots_qaoa": shots, "pieces": len(log), "history_matches_results_json": same,
                 "n_opt_mean": float(n.mean()),
                 "p_opt_random_valid_6": float((n / 6).mean()),
                 "p_opt_random_states_27": float((n / 27).mean()),
                 "qaoa_sub_success_rate_reported": Hs[method]["sub_success_rate"],
                 "qaoa_p_optimal_mean_reported": Hs[method]["qaoa_p_optimal_mean"],
                 "enumeration_success": 1.0}
        for k in (8, 512):
            stats[f"hit_k{k}_random_valid_6"] = float((1 - (1 - n / 6) ** k).mean())
            stats[f"hit_k{k}_random_states_27"] = float((1 - (1 - n / 27) ** k).mean())
        extra[f"baselines_{key}"] = stats
        print(key, json.dumps(stats, ensure_ascii=False))

    # hardware N=3: azar de P(óptimo)
    hwp = os.path.join(ROOT, "results", "hardware.json")
    if os.path.exists(hwp):
        hw = json.load(open(hwp, encoding="utf-8"))
        sub = inst.subinstance(3)
        costs = [sub.cost(p) for p in itertools.permutations(range(3))]
        n_opt = sum(abs(c - min(costs)) < 1e-9 for c in costs)
        rows = []
        for e in hw["experiments"]:
            base = n_opt / (27 if e["mixer"] == "xy" else 2 ** e["qubits"])
            rows.append({"id": e["id"], "mixer": e["mixer"], "n_opt": n_opt, "random_p_optimal": base,
                         "hardware_p_optimal": e["p_optimal"], "ratio_hw_vs_random": e["p_optimal"] / base})
        extra["hardware_random_p_optimal"] = {"backend": hw["backend"], "job_id": hw["job_id"], "N": 3, "rows": rows}
        print("hardware", json.dumps(rows))
    extra["meta_baselines"] = {"seed": seed, "versions": versions(), "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
                               "command": "python analysis/baselines.py --mps " + args.mps}
    if os.path.exists(out_path):                 # fusionar con lo que otra corrida haya escrito mientras tanto
        merged = json.load(open(out_path, encoding="utf-8"))
        merged.update(extra)
        extra = merged
    json.dump(extra, open(out_path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("guardado", out_path)


if __name__ == "__main__":
    main()
