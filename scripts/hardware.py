"""QAOA de N = 3 en hardware real de IBM Quantum (o en un backend fake para probar sin gastar tiempo).

Uso:
    python scripts/hardware.py check              # verifica credenciales guardadas y lista las QPUs
    python scripts/hardware.py submit             # envía UN job con N3-x-p1 y N3-xy-p1 a la QPU menos ocupada
    python scripts/hardware.py fetch              # cuando el job termina: escribe results/hardware.json
    python scripts/hardware.py submit --fake      # prueba completa local con FakeTorino (ruido de una QPU Heron)

Credenciales: haber corrido antes, en esta máquina,
    QiskitRuntimeService.save_account(token=..., instance=..., set_as_default=True)
Este script nunca lee, pide ni imprime la API key.

Regla de oro: los ángulos de QAOA ya se optimizaron en el simulador (results/results.json). Al hardware
solo se manda el circuito final, una vez. Un job de 2 circuitos x 4096 shots usa segundos de QPU.
Un resultado de --fake se guarda en results/hardware_fake.json y NUNCA se presenta como hardware real.
"""
from __future__ import annotations

import argparse
import datetime as dt
import itertools
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from qgate.instance import QAPInstance  # noqa: E402
from qgate.qubo import build_qubo, feasible_mask  # noqa: E402
from qgate.quantum import build_qaoa_circuit  # noqa: E402

RES = os.path.join(ROOT, "results", "results.json")
JOBS = os.path.join(ROOT, "results", "hardware_jobs.json")
DEFAULT_IDS = ["N3-x-p1", "N3-xy-p1"]


# ----------------------------------------------------------------- utilidades
def load_results():
    with open(RES, encoding="utf-8") as fh:
        return json.load(fh)


def instance_from_results(R) -> QAPInstance:
    F, D = np.array(R["data"]["F"], dtype=float), np.array(R["data"]["D"], dtype=float)
    return QAPInstance.from_FD(F, D, name=R["meta"].get("instance", "qap10"))


def sub_optimum(sub: QAPInstance):
    best = min(itertools.permutations(range(sub.N)), key=lambda p: sub.cost(p))
    return sub.cost(best), list(best)


def build_circuits(R, ids):
    """Reconstruye cada circuito con los ángulos óptimos guardados y verifica que la distribución
    ideal coincide con la del simulador (prueba de que es el mismo circuito)."""
    from qiskit.quantum_info import Statevector

    inst = instance_from_results(R)
    Q = {q["id"]: q for q in R["quantum"]}
    out = []
    for qid in ids:
        if qid not in Q:
            raise SystemExit(f"No existe el experimento {qid} en results.json")
        q = Q[qid]
        sub = inst.subinstance(q["N"])
        opt, _ = sub_optimum(sub)
        if q.get("optimum") is not None and abs(opt - q["optimum"]) > 1e-9:
            raise SystemExit(f"{qid}: óptimo recalculado {opt} != {q['optimum']} del results.json")
        qubo = build_qubo(sub, lam=q["lam"])
        qc, g, bt, _ = build_qaoa_circuit(qubo, q["p"], q["mixer"])
        p = q["p"]
        th = q["params"]
        binds = {**{g[i]: th[i] for i in range(p)}, **{bt[i]: th[p + i] for i in range(p)}}
        circ = qc.assign_parameters(binds)
        probs = Statevector(circ).probabilities()
        feas = feasible_mask(sub.N, qubo.all_bits())
        p_feas = float(probs[feas].sum())
        if abs(p_feas - q["p_feasible"]) > 1e-3:
            raise SystemExit(f"{qid}: P(válida) ideal {p_feas:.4f} != {q['p_feasible']:.4f}: el circuito no coincide")
        circ.measure_all()
        circ.name = qid
        out.append({"id": qid, "q": q, "sub": sub, "optimum": opt, "circuit": circ, "ideal_p_feasible": p_feas})
        print(f"  {qid}: circuito reconstruido, P(válida) ideal {p_feas:.4f} = results.json ✓")
    return out


def metrics(sub: QAPInstance, counts: dict, optimum: float) -> dict:
    tot = sum(counts.values())
    n = sub.N
    feas = opt_hits = 0
    best, acc = None, 0.0
    for bstr, c in counts.items():
        x = np.array([int(ch) for ch in bstr.replace(" ", "")[::-1]]).reshape(n, n)  # qubit 0 a la derecha
        if (x.sum(0) == 1).all() and (x.sum(1) == 1).all():
            perm = [int(np.argmax(r)) for r in x]
            cost = sub.cost(perm)
            feas += c
            acc += cost * c
            best = cost if best is None else min(best, cost)
            if abs(cost - optimum) < 1e-9:
                opt_hits += c
    return {"shots": tot, "feasible_fraction": feas / tot, "p_optimal": opt_hits / tot,
            "best_feasible_cost": best, "mean_feasible_cost": (acc / feas) if feas else None}


def two_qubit_count(circ) -> int:
    return sum(1 for ins in circ.data if ins.operation.num_qubits == 2 and ins.operation.name != "barrier")


def service():
    try:
        from qiskit_ibm_runtime import QiskitRuntimeService
        return QiskitRuntimeService()
    except Exception as e:  # sin cuenta guardada o sin red
        raise SystemExit(
            "No pude abrir la cuenta de IBM Quantum guardada.\n"
            "Guárdala una vez en esta máquina (la key no se escribe en el repo):\n"
            "  python -c \"from qiskit_ibm_runtime import QiskitRuntimeService as S; "
            "S.save_account(token=input('API key: '), instance='<CRN>', set_as_default=True, overwrite=True)\"\n"
            f"Detalle: {type(e).__name__}: {e}")


# ------------------------------------------------------------------ comandos
def cmd_check(args):
    svc = service()
    backs = svc.backends(operational=True, simulator=False)
    print(f"Cuenta OK. QPUs disponibles para esta instancia: {len(backs)}")
    for b in backs:
        try:
            pend = b.status().pending_jobs
        except Exception:
            pend = "?"
        print(f"  {b.name:<16} {b.num_qubits:>4} qubits   jobs en cola: {pend}")
    try:
        print("Menos ocupada (>= 16 qubits):", svc.least_busy(operational=True, simulator=False, min_num_qubits=16).name)
    except Exception as e:
        print("No pude calcular la menos ocupada:", e)


def cmd_submit(args):
    from qiskit.transpiler import generate_preset_pass_manager
    from qiskit_ibm_runtime import SamplerV2

    R = load_results()
    print("Reconstruyendo circuitos desde results.json...")
    items = build_circuits(R, args.ids)
    if args.fake:
        from qiskit_ibm_runtime.fake_provider import FakeTorino
        backend = FakeTorino()
    else:
        svc = service()
        backend = svc.backend(args.backend) if args.backend else svc.least_busy(
            operational=True, simulator=False, min_num_qubits=16)
    print(f"Backend: {backend.name}{' (FAKE: simulación local con el modelo de ruido de IBM)' if args.fake else ''}")
    pm = generate_preset_pass_manager(optimization_level=3, backend=backend, seed_transpiler=7)
    isa = []
    for it in items:
        t = pm.run(it["circuit"])
        it["depth"], it["two_qubit_gates"] = int(t.depth()), two_qubit_count(t)
        print(f"  {it['id']}: profundidad {it['depth']}, compuertas de 2 qubits {it['two_qubit_gates']} (tras ruteo real)")
        isa.append(t)
    sampler = SamplerV2(mode=backend)
    if not args.fake:
        for setter in (lambda o: setattr(o.dynamical_decoupling, "enable", True),
                       lambda o: setattr(o.twirling, "enable_gates", True)):
            try:
                setter(sampler.options)
            except Exception:
                pass
    job = sampler.run(isa, shots=args.shots)
    info = {"job_id": job.job_id(), "backend": backend.name, "fake": bool(args.fake),
            "submitted_at": dt.datetime.now().isoformat(timespec="seconds"), "shots": args.shots,
            "ids": args.ids, "transpiled": {it["id"]: {"depth": it["depth"], "two_qubit_gates": it["two_qubit_gates"]}
                                            for it in items}}
    if not args.fake:
        with open(JOBS, "w", encoding="utf-8") as fh:
            json.dump(info, fh, indent=1, ensure_ascii=False)
        print(f"Job enviado: {info['job_id']} en {backend.name}. Guardado en results/hardware_jobs.json")
        print("Revisa con: python scripts/hardware.py fetch")
        if not args.wait:
            return
    print("Esperando resultado...")
    finish(R, items, job, info)


def cmd_fetch(args):
    if not os.path.exists(JOBS):
        raise SystemExit("No hay results/hardware_jobs.json: primero corre submit.")
    with open(JOBS, encoding="utf-8") as fh:
        info = json.load(fh)
    svc = service()
    job = svc.job(info["job_id"])
    status = job.status()
    status = getattr(status, "name", status)
    print(f"Job {info['job_id']} en {info['backend']}: {status}")
    if str(status).upper() not in ("DONE", "COMPLETED"):
        print("Todavía no termina. Vuelve a correr fetch en unos minutos.")
        return
    R = load_results()
    items = build_circuits(R, info["ids"])
    for it in items:
        tr = info.get("transpiled", {}).get(it["id"], {})
        it["depth"], it["two_qubit_gates"] = tr.get("depth"), tr.get("two_qubit_gates")
    finish(R, items, job, info)


def finish(R, items, job, info):
    res = job.result()
    usage = None
    try:
        usage = float(job.usage())
    except Exception:
        try:
            usage = float(job.metrics().get("usage", {}).get("quantum_seconds"))
        except Exception:
            usage = None
    Q = {q["id"]: q for q in R["quantum"]}
    exps = []
    for i, it in enumerate(items):
        counts = res[i].data.meas.get_counts()
        m = metrics(it["sub"], counts, it["optimum"])
        q = it["q"]
        noisy = Q.get(f"{it['id']}-noise0.01", {})
        exps.append({"id": it["id"], "N": q["N"], "qubits": q["qubits"], "mixer": q["mixer"], "p": q["p"],
                     "optimum": it["optimum"], **m,
                     "random_feasible_baseline": q["random_feasible_baseline"],
                     "sim_ideal_p_feasible": q["p_feasible"],
                     "sim_noise_feasible_fraction": noisy.get("feasible_fraction_shots"),
                     "depth": it.get("depth"), "two_qubit_gates": it.get("two_qubit_gates")})
        print(f"  {it['id']}: válidas {m['feasible_fraction']:.3f} (ideal {q['p_feasible']:.3f}, "
              f"azar {q['random_feasible_baseline']:.3f}) · P(óptimo) {m['p_optimal']:.3f} · mejor válido {m['best_feasible_cost']}")
    top = max(exps, key=lambda e: e["feasible_fraction"])
    out = {"backend": info["backend"], "job_id": info["job_id"], "fake": info["fake"],
           "date": dt.datetime.now().isoformat(timespec="seconds"), "usage_quantum_seconds": usage,
           "N": top["N"], "qubits": top["qubits"], "best_feasible_cost": top["best_feasible_cost"],
           "optimum": top["optimum"], "time_s": usage, "experiments": exps}
    path = os.path.join(ROOT, "results", "hardware_fake.json" if info["fake"] else "hardware.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    print(f"Guardado {os.path.relpath(path, ROOT)}" + (" (FAKE: no usar como hardware real)" if info["fake"] else ""))
    if not info["fake"]:
        print("Ahora: python entrega/publicar.py  (regenera dashboard, README y PPT con la fila de hardware)")


def main():
    for stream in (sys.stdout, sys.stderr):   # la consola de Windows (cp1252) no imprime ✓ ni λ
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="QAOA N=3 en IBM Quantum")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    s = sub.add_parser("submit")
    s.add_argument("--fake", action="store_true", help="FakeTorino local, sin cuenta ni tiempo de QPU")
    s.add_argument("--backend", help="nombre de la QPU (por defecto la menos ocupada)")
    s.add_argument("--shots", type=int, default=4096)
    s.add_argument("--ids", nargs="+", default=DEFAULT_IDS)
    s.add_argument("--wait", action="store_true", help="esperar el resultado en vez de usar fetch")
    sub.add_parser("fetch")
    args = ap.parse_args()
    {"check": cmd_check, "submit": cmd_submit, "fetch": cmd_fetch}[args.cmd](args)


if __name__ == "__main__":
    main()
