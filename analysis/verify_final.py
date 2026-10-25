"""Verificación independiente de las corridas de la etapa 3 (revisión externa, punto 2).

Para cada corrida de results/final_runs.json.gz: comprueba que best_perm es una permutación válida de N
elementos y recalcula su costo con bucles explícitos sobre F y D guardados con la corrida (sin usar el
código de producción: ni QAPInstance.cost ni el tensor T). Compara con best_cost y feasible reportados.

Convención del reto: cada par se cuenta una vez. Con F simétrica, C = sum_{i<k} F_ik D_{p(i)p(k)}; con F
triangular, el término del otro lado es cero. La fórmula de abajo cubre los dos casos.

Opcional --compare results/final.json: compara corrida por corrida (instancia, método, selector, semilla)
el costo nuevo con el publicado, y las medianas por método e instancia en las semillas comunes.

Uso:
    python analysis/verify_final.py [results/final_runs.json.gz] [--compare results/final.json]
Código de salida 1 si hay una discrepancia o una corrida no factible.
"""
from __future__ import annotations

import argparse
import gzip
import json
import statistics
import sys


def pair_once_cost(F, D, p):
    n = len(p)
    symF = all(F[i][k] == F[k][i] for i in range(n) for k in range(n))
    c = 0.0
    for i in range(n):
        for k in range(i + 1, n):
            c += F[i][k] * D[p[i]][p[k]] + F[k][i] * D[p[k]][p[i]]
    return c / 2 if symF else c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="?", default="results/final_runs.json.gz")
    ap.add_argument("--compare")
    ap.add_argument("--out", help="guarda el resumen en este JSON")
    a = ap.parse_args()
    for s_ in (sys.stdout, sys.stderr):
        try:
            s_.reconfigure(encoding="utf-8")
        except Exception:
            pass
    d = json.load(gzip.open(a.runs, "rt", encoding="utf-8"))
    inst = d["instances"]
    for name, I in inst.items():
        D = I["D"]
        if any(D[j][l] != D[l][j] for j in range(I["N"]) for l in range(I["N"])):
            print(f"AVISO: D de {name} no es simétrica")
    bad, infeasible, n = [], [], 0
    for r in d["runs"]:
        n += 1
        I = inst[r["instance"]]
        p = r.get("best_perm")
        ok_perm = isinstance(p, list) and len(p) == I["N"] and sorted(p) == list(range(I["N"]))
        if not ok_perm:
            infeasible.append(r)
            if r.get("feasible"):
                bad.append((r, "feasible=true con permutación inválida"))
            continue
        c = pair_once_cost(I["F"], I["D"], p)
        if abs(c - r["best_cost"]) > 1e-6:
            bad.append((r, f"costo recalculado {c} vs reportado {r['best_cost']}"))
        if not r.get("feasible"):
            bad.append((r, "feasible=false con permutación válida"))
    print(f"Corridas: {n} · discrepancias: {len(bad)} · no factibles: {len(infeasible)}")
    res = {"fecha": __import__("datetime").datetime.now().isoformat(timespec="seconds"), "comando": "python " + " ".join(sys.argv),
           "archivo": a.runs, "corridas": n, "discrepancias": len(bad), "no_factibles": len(infeasible),
           "semillas": sorted({r["seed"] for r in d["runs"]})}
    for r, why in bad[:10]:
        print(f"  {r['instance']} {r['solver']}/{r.get('select')} semilla {r['seed']}: {why}")

    if a.compare:
        P = json.load(open(a.compare, encoding="utf-8"))
        pub = {(x["instance"], x["solver"], x.get("select"), x["seed"]): x["best_cost"] for x in P.get("runs", [])}
        eq = diff = miss = 0
        diffs = []
        for r in d["runs"]:
            k = (r["instance"], r["solver"], r.get("select"), r["seed"])
            if k not in pub:
                miss += 1
            elif abs(pub[k] - r["best_cost"]) < 1e-9:
                eq += 1
            else:
                diff += 1
                diffs.append((k, pub[k], r["best_cost"]))
        print(f"Contra {a.compare}: {eq} corridas con el mismo costo, {diff} distintas, {miss} sin par publicado")
        for k, x, y in diffs[:12]:
            print(f"  {k[0]} {k[1]}/{k[2]} semilla {k[3]}: publicado {x:g}, nuevo {y:g}")
        seeds = sorted({r["seed"] for r in d["runs"]})
        groups = sorted({(r["instance"], r["solver"], r.get("select")) for r in d["runs"]}, key=str)
        same = 0
        for g in groups:
            new = [r["best_cost"] for r in d["runs"] if (r["instance"], r["solver"], r.get("select")) == g]
            old = [pub[(*g, s)] for s in seeds if (*g, s) in pub]
            if old and new and (statistics.median(new), min(new), max(new)) == (statistics.median(old), min(old), max(old)):
                same += 1
        print(f"Mediana y rango por método e instancia en las semillas {seeds[0]} a {seeds[-1]}: {same} de {len(groups)} grupos iguales")
        res["comparacion"] = {"contra": a.compare, "corridas_mismo_costo": eq, "corridas_distintas": diff, "sin_par_publicado": miss,
                              "grupos_mediana_y_rango_iguales": same, "grupos": len(groups),
                              "diferencias": [{"instancia": k[0], "metodo": k[1], "selector": k[2], "semilla": k[3], "publicado": x, "nuevo": y}
                                              for k, x, y in diffs]}
    if a.out:
        json.dump(res, open(a.out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    sys.exit(1 if bad or infeasible else 0)


if __name__ == "__main__":
    main()
