"""Regenera todo el material de entrega desde results/results.json.

Uso:
    python entrega/publicar.py

1. dashboard  -> results/report.html y docs/index.html (GitHub Pages)
2. tablas y lectura de resultados del README
3. entrega/QGate.pptx (nombres desde entrega/equipo.json)
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RES = os.path.join(ROOT, "results", "results.json")


def run(*args):
    print("$", " ".join(os.path.relpath(a, ROOT) if os.path.isabs(a) else a for a in args))
    subprocess.run([sys.executable, *args], check=True, cwd=ROOT)


if __name__ == "__main__":
    report = os.path.join(ROOT, "results", "report.html")
    run(os.path.join(ROOT, "dashboard", "build_report.py"), RES, report)
    shutil.copyfile(report, os.path.join(ROOT, "docs", "index.html"))
    print("docs/index.html actualizado")
    run(os.path.join(HERE, "make_tables.py"), RES, os.path.join(ROOT, "README.md"))
    run(os.path.join(HERE, "make_ppt.py"), RES, os.path.join(HERE, "QGate.pptx"))
