"""Genera results/MANIFEST.json: huella de la instancia y sha256 de cada archivo de resultados.

Para results.json, hardware.json, extra.json y final.json existentes la atestación es "a posteriori": se
calcula hoy, sin modificar su contenido. Para hardware.json se comprueba que su N=3 coincide con la
subinstancia N=3 de results.json (óptimo) y que su P(válida) ideal coincide con la de results.json, lo que
indica que se usaron los mismos ángulos (hardware.json no los guarda; se registran los de results.json).

Uso: python analysis/make_manifest.py [results]
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from qgate.provenance import file_sha256, instance_fingerprint  # noqa: E402

FILES = {
    "results.json": "python -m qgate.bench --mps data/qap10.mps.gz --scale 10,12,14,16 (día 1)",
    "hardware.json": "python scripts/hardware.py (ibm_kingston, N=3)",
    "extra.json": "python analysis/baselines.py y python analysis/scale_check.py",
    "final.json": "python -m qgate.final --sizes 14,16,20 --seeds 10 (etapa 3)",
    "final_verif.json": "python -m qgate.final --sizes 14,16,20 --seeds 5 --out results/final_verif.json (corrida de verificación reducida)",
    "final_runs.json.gz": "corridas completas de la corrida de verificación (best_perm, trayectoria, F y D)",
}


def main():
    rd = sys.argv[1] if len(sys.argv) > 1 else "results"
    R = json.load(open(os.path.join(rd, "results.json"), encoding="utf-8"))
    F, D = R["data"]["F"], R["data"]["D"]
    fp = instance_fingerprint(F, D, R["meta"].get("instance", "qap10"))
    now = dt.datetime.now().isoformat(timespec="seconds")
    man = {"generated_at": now, "instance": fp, "files": {}}
    for f, how in FILES.items():
        p = os.path.join(rd, f)
        if os.path.exists(p):
            man["files"][f] = {"sha256": file_sha256(p), "instance_sha256": fp["sha256"], "producido_por": how,
                               "atestacion": f"a posteriori, {now}" if f in ("results.json", "hardware.json", "extra.json", "final.json") else f"al generar, {now}"}
    hp = os.path.join(rd, "hardware.json")
    if os.path.exists(hp):
        H = json.load(open(hp, encoding="utf-8"))
        sub = instance_fingerprint([r[:3] for r in F[:3]], [r[:3] for r in D[:3]], "qap10 N=3")
        Q = {q["id"]: q for q in R["quantum"]}
        V = {v["n"]: v for v in R["validation"]}
        checks = []
        for e in H["experiments"]:
            q = Q.get(e["id"])
            checks.append({"id": e["id"], "optimo_coincide": abs(e["optimum"] - V[3]["optimum"]) < 1e-9,
                           "p_valida_ideal_coincide": bool(q) and abs(e["sim_ideal_p_feasible"] - q["p_feasible"]) < 1e-9,
                           "angulos_de_results_json": q.get("params") if q else None})
        man["files"]["hardware.json"].update({"job_id": H["job_id"], "backend": H["backend"], "subinstancia_N3": sub, "checks": checks,
                                              "consistente": all(c["optimo_coincide"] and c["p_valida_ideal_coincide"] for c in checks)})
    out = os.path.join(rd, "MANIFEST.json")
    json.dump(man, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"Guardado {out}: instancia {fp['sha256'][:12]}, {len(man['files'])} archivos"
          + (f", hardware consistente: {man['files']['hardware.json']['consistente']}" if "hardware.json" in man["files"] else ""))


if __name__ == "__main__":
    main()
