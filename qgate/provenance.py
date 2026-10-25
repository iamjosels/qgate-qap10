"""Procedencia de los resultados (revisión externa, punto 1).

Huella de instancia: sha256 de N, F y D en bytes canónicos (float64, little-endian, orden C). Dos archivos de
resultados pertenecen a la misma instancia solo si su huella coincide. results/MANIFEST.json guarda la huella y
el sha256 de cada archivo; dashboard/build_report.py se niega a mezclar archivos que no coinciden.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import platform
import subprocess

import numpy as np


def instance_fingerprint(F, D, name: str = "") -> dict:
    F = np.ascontiguousarray(np.asarray(F, dtype="<f8"))
    D = np.ascontiguousarray(np.asarray(D, dtype="<f8"))
    h = hashlib.sha256()
    h.update(np.int64(F.shape[0]).tobytes())
    h.update(F.tobytes())
    h.update(D.tobytes())
    return {"name": name, "N": int(F.shape[0]), "sha256": h.hexdigest()}


def file_sha256(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def run_context(args=None, seed=None, procs=None) -> dict:
    """Versiones, commit, semilla, argumentos, fecha y procesos de una corrida."""
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5).stdout.strip() or None
    except Exception:
        commit = None
    vers = {"python": platform.python_version()}
    for mod in ("numpy", "scipy", "qiskit", "qiskit_aer"):
        try:
            vers[mod] = __import__(mod).__version__
        except Exception:
            vers[mod] = None
    return {"date": dt.datetime.now().isoformat(timespec="seconds"), "commit": commit, "versions": vers,
            "seed": seed, "args": args, "procs": procs}


def load_manifest(results_dir: str):
    p = os.path.join(results_dir, "MANIFEST.json")
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)
