# QGate

Asignación de vuelos a puertas de embarque (QAP, instancia MIPLIB qap10) con métodos clásicos,
QAOA en Qiskit y un híbrido por vecindarios.

IBM Quantum Hackathon 2026 · Reto NTT DATA QAP10 · Track A Aeropuerto.

> README provisional. La versión final se genera en la fase P3 del plan (ver `CLAUDE.md`).

## Reproducir

```bash
pip install -r requirements.txt
python -m qgate.bench --mps data/qap10.mps.gz
```

Datos: `qap10.mps.gz` desde https://miplib.zib.de/instance_details_qap10.html
