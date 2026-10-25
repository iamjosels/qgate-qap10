"""A0 (a) de la auditoría: reproduce que build_report.py incorpora hardware.json, extra.json y final.json
aunque results.json sea de otra instancia. Hoy FALLA a propósito (código de salida 1): queda como evidencia
hasta que exista la verificación de procedencia (A2, pendiente).

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
for f in ("hardware.json", "extra.json", "final.json"):  # archivos auxiliares de la corrida original
    shutil.copy(os.path.join(ROOT, "results", f), tmp)
out = os.path.join(tmp, "report.html")
p = subprocess.run([sys.executable, os.path.join(ROOT, "dashboard", "build_report.py"), os.path.join(tmp, "results.json"), out],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
html = open(out, encoding="utf-8").read() if os.path.exists(out) else ""
incl = {k: (f'"{k}":' in html) for k in ("hardware", "extra", "final")}
aviso = "no corresponde a esta corrida" in html or "no corresponde" in (p.stdout + p.stderr)
print(f"build_report: código {p.returncode}; incluye {incl}; aviso de procedencia: {aviso}")
if p.returncode == 0 and any(incl.values()) and not aviso:
    print("FALLA: se incluyeron JSON auxiliares de otra instancia sin aviso (fail-closed pendiente)")
    sys.exit(1)
print("OK: build falla o excluye con aviso")
