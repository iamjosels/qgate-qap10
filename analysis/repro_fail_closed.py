"""A0 (a) y A2.4 de la auditoría: cambia un coeficiente de F en results.json, deja hardware.json, extra.json,
final.json y MANIFEST.json de la corrida original y exige que build_report.py falle o los excluya con aviso.
Antes de A2 salía con código 1 (los incluía sin aviso); con la verificación de procedencia debe pasar.

Uso: python analysis/repro_fail_closed.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tmp = tempfile.mkdtemp(prefix="qgate_failclosed_")
R = json.load(open(os.path.join(ROOT, "results", "results.json"), encoding="utf-8"))
F = R["data"]["F"]
F[0][1] += 1                                     # otra instancia: un coeficiente de F distinto
F[1][0] = F[0][1]
json.dump(R, open(os.path.join(tmp, "results.json"), "w", encoding="utf-8"))
for f in ("hardware.json", "extra.json", "final.json", "MANIFEST.json"):  # archivos de la corrida original
    shutil.copy(os.path.join(ROOT, "results", f), tmp)
out = os.path.join(tmp, "report.html")
p = subprocess.run([sys.executable, os.path.join(ROOT, "dashboard", "build_report.py"), os.path.join(tmp, "results.json"), out],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
html = open(out, encoding="utf-8").read() if os.path.exists(out) else ""
incl = {k: (f'"{k}":' in html) for k in ("hardware", "extra", "final")}
aviso = "no corresponde a esta corrida" in html and "no corresponde" in (p.stdout + p.stderr)
print(f"build_report: código {p.returncode}; incluye {incl}; aviso de procedencia: {aviso}")
if p.returncode == 0 and any(incl.values()) and not aviso:
    print("FALLA: se incluyeron JSON auxiliares de otra instancia sin aviso (fail-closed pendiente)")
    sys.exit(1)
print("OK: build falla o excluye con aviso")
