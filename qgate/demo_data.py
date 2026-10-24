"""Agrega a un results.json existente los datos del modo demo, sin repetir todo el bench.

    python -m qgate.demo_data --mps data/qap10.mps.gz --results results/results.json

- frames de QAOA N=4 (mixer X y XY, p=1): se repite el experimento con la misma semilla y
  configuración y se verifica que P(válida) coincide con la reportada.
- eventos del híbrido QGate con QAOA (asignación tras cada movimiento): se repite la corrida con
  la misma semilla y arranque y se verifica que el historial coincide.
El bench completo ya guarda ambos datos; este script solo completa resultados anteriores.
"""
from __future__ import annotations

import argparse
import json

import numpy as np

from .bench import _jsonable, log
from .hybrid import qgate_lns
from .mps import recover_qap
from .quantum import run_qaoa


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mps", required=True)
    ap.add_argument("--results", default="results/results.json")
    args = ap.parse_args(argv)
    with open(args.results, encoding="utf-8") as fh:
        R = json.load(fh)
    a = R["meta"]["args"]
    rec = recover_qap(args.mps, name="qap10")
    inst = rec.candidates[R["data"]["index_strategy"]]
    seed, quick = a["seed"], a["quick"]
    sub_opt = {v["n"]: v["optimum"] for v in R["validation"]}

    for q in R["quantum"]:
        if q["N"] == 4 and q["p"] == 1 and q["noise"] == "none":
            r = run_qaoa(inst.subinstance(4), p=1, mixer=q["mixer"], restarts=2 if quick else 4,
                         maxiter=100 if quick else 200, shots=4096, seed=seed, optimum=sub_opt.get(4),
                         compute_stats=False, keep_distribution=0, trace=True)
            ok = abs(r["p_feasible"] - q["p_feasible"]) < 1e-9
            log(f"frames {q['id']}: {len(r['frames']['p'])} frames, P(válida) coincide: {ok}")
            if ok:
                q["frames"] = r["frames"]

    H = a.get("hybrid_iters") or (120 if quick else 300)
    for h in R["hybrid"]:
        if h["method"] == "qgate_lns_qaoa":
            start = np.random.default_rng(seed + 100).permutation(inst.N)
            log(f"repitiendo {h['label']} ({H} iteraciones) para registrar eventos...")
            r = qgate_lns(inst, k=3, iters=H, solver="qaoa", seed=seed, start_perm=start,
                          shots=h.get("shots") or 512, label=h["label"])
            same = [x["best"] for x in r["history"]] == [x["best"] for x in h["history"]]
            log(f"  final {r['final_cost']} (reportado {h['final_cost']}), historial idéntico: {same}")
            if same:
                h["events"] = r["events"]

    with open(args.results, "w", encoding="utf-8") as fh:
        json.dump(R, fh, default=_jsonable, indent=1, ensure_ascii=False)
    log(f"Guardado {args.results}")


if __name__ == "__main__":
    main()
