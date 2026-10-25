"""Genera el reporte HTML autocontenido de QGate a partir de results.json (solo stdlib).

Uso:
    python dashboard/build_report.py results/results.json results/report.html

Sigue design/BRAND.md y los mockups design/*.dc.html: tres escenas del modo demo
(01 QAOA, 02 Aeropuerto, 03 Resultado) con reproducción, x2 y pantalla completa, y debajo las
secciones de detalle. El JSON va embebido en <script id="data" type="application/json">; todos los
gráficos son SVG propios, así que funciona sin red salvo las fuentes de Google Fonts.
Si existe hardware.json junto a results.json se agrega como fila aparte. Un dato que no existe
oculta su elemento: nunca se muestra un valor de relleno.
"""
from __future__ import annotations

import json
import math
import os
import sys


def _clean(o):
    """NaN/Infinity no son JSON válido para el navegador: se reemplazan por null."""
    if isinstance(o, float):
        return None if (math.isnan(o) or math.isinf(o)) else o
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_clean(v) for v in o]
    return o


def _slim(R: dict) -> dict:
    for q in R.get("quantum", []):
        q.pop("perm_distribution", None)
    for h in R.get("hybrid", []):
        hist = h.get("history") or []
        if len(hist) > 600:
            step = math.ceil(len(hist) / 600)
            h["history"] = hist[::step] + [hist[-1]]
    return R


def _grid_layout(D):
    """Si D es distancia Manhattan entre puntos de una grilla entera, devuelve sus coordenadas
    (columna, fila); si no, None. Se usa solo para dibujar el terminal con la geometría real."""
    if not D:
        return None
    n = len(D)
    try:
        D = [[int(round(abs(float(v)))) for v in row] for row in D]
    except (TypeError, ValueError):
        return None
    span = max(max(r) for r in D)
    if span > 12:
        return None
    xs = sorted(range(-span, span + 1), key=lambda v: (abs(v), v < 0))   # preferir crecer a la derecha
    cand = [(x, y) for y in range(0, span + 1) for x in xs]
    pos = [None] * n
    pos[0] = (0, 0)

    def ok(j, p):
        return all(abs(p[0] - pos[i][0]) + abs(p[1] - pos[i][1]) == D[i][j] and p != pos[i]
                   for i in range(j))

    def bt(j):
        if j == n:
            return True
        for p in cand:
            if ok(j, p):
                pos[j] = p
                if bt(j + 1):
                    return True
        pos[j] = None
        return False

    if not bt(1):
        return None
    mx, my = min(p[0] for p in pos), min(p[1] for p in pos)
    return [[p[0] - mx, p[1] - my] for p in pos]


def build(json_path: str, out_path: str) -> str:
    with open(json_path, encoding="utf-8") as fh:
        R = json.load(fh)
    hw = os.path.join(os.path.dirname(os.path.abspath(json_path)), "hardware.json")
    if os.path.exists(hw):
        with open(hw, encoding="utf-8") as fh:
            H = json.load(fh)
        if not H.get("fake"):                      # un resultado fake nunca se muestra como hardware
            R["hardware"] = H
            lim = R.get("meta", {}).get("limitations", [])
            R["meta"]["limitations"] = [
                (f"Simulador Qiskit Aer y una corrida N={H.get('N')} en {H.get('backend')} de IBM Quantum "
                 f"(job {H.get('job_id')}); el resto es simulación") if "hardware real" in l else l for l in lim]
    ex = os.path.join(os.path.dirname(os.path.abspath(json_path)), "extra.json")
    if os.path.exists(ex):                         # cifras nuevas de analysis/baselines.py
        with open(ex, encoding="utf-8") as fh:
            R["extra"] = json.load(fh)
    fin = os.path.join(os.path.dirname(os.path.abspath(json_path)), "final.json")
    if os.path.exists(fin):                        # etapa 3 (final): python -m qgate.final
        with open(fin, encoding="utf-8") as fh:
            Fj = json.load(fh)
        Fj.pop("runs", None)                       # el reporte usa el resumen, no cada corrida
        R["final"] = Fj
    data = R.setdefault("data", {})
    data["gate_grid"] = _grid_layout(data.get("D"))
    payload = json.dumps(_clean(_slim(R)), ensure_ascii=False, allow_nan=False)
    payload = payload.replace("</", "<\\/")
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import panorama
    html = TEMPLATE.replace("__DATA__", payload).replace("__PANORAMA__", panorama.render(R))
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(html)
    return out_path


TEMPLATE = r"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>QGate · Vuelos a puertas</title>
<meta name="description" content="QGate: asignación de vuelos a puertas (QAP qap10) con QAOA híbrido en Qiskit. IBM Quantum Hackathon 2026, reto NTT DATA.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700;800&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root {
  --ink: #0B0B0C; --board: #141518; --flap: #1E2024; --line: #2C2F35; --well: #0E0F11;
  --signal: #FFC629; --qubit: #4FE3E0; --invalid: #FF6B3D; --invalid-bar: #7A3A26;
  --paper: #F4F1E8; --mute: #9A9890; --ink-2: #55534D; --soft: #C9C6BC; --dim: #6E6C66;
  --head: "Barlow Condensed", "Arial Narrow", sans-serif;
  --sans: "IBM Plex Sans", system-ui, sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, monospace;
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body { margin: 0; background: var(--ink); color: var(--paper); font: 16px/1.45 var(--sans); }
a { color: var(--signal); } a:hover { color: #FFD866; }
.wrap { max-width: 1440px; margin: 0 auto; padding: 0 32px; }
@media (max-width: 640px) { .wrap { padding: 0 16px; } }
.mono { font-family: var(--mono); }
.kick { font-family: var(--mono); font-size: 12px; letter-spacing: .14em; color: var(--mute); text-transform: uppercase; }
.hidden { display: none !important; }
.off-tab { display: none !important; }   /* sección de detalle de otra pestaña */
button { font: inherit; }
button:focus-visible, a:focus-visible { outline: 2px solid var(--qubit); outline-offset: 2px; }

.top { position: sticky; top: 0; z-index: 20; background: var(--ink); border-bottom: 1px solid var(--line); }
.top .wrap { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px 16px; padding-top: 14px; padding-bottom: 12px; }
.brand { display: flex; align-items: center; gap: 12px; }
.brand b { font: 800 32px/1 var(--head); letter-spacing: .02em; }
.brand .kick { margin-left: 6px; }
@media (max-width: 760px) { .brand .kick { display: none; } .top { position: static; } }
.tabs { display: flex; gap: 4px; overflow-x: auto; max-width: 100%; scrollbar-width: none; }
.tabs::-webkit-scrollbar { display: none; }
.tabs button { background: none; border: 0; border-bottom: 3px solid transparent; padding: 10px 14px; color: var(--mute);
  font: 13px var(--mono); letter-spacing: .08em; cursor: pointer; white-space: nowrap; }
@media (max-width: 640px) { .tabs button { padding: 8px 8px; font-size: 12px; } }
.tabs button[aria-selected="true"] { color: var(--signal); border-bottom-color: var(--signal); }
.tabs button[data-scene="qaoa"][aria-selected="true"] { color: var(--qubit); border-bottom-color: var(--qubit); }
.ctrl { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.btn { height: 46px; padding: 0 14px; border-radius: 8px; border: 1px solid var(--line); background: var(--board); color: var(--paper);
  font: 13px var(--mono); cursor: pointer; }
.btn.play { width: 48px; padding: 0; border: 0; background: var(--signal); display: flex; align-items: center; justify-content: center; }
.btn.play.q { background: var(--qubit); }
.btn[aria-pressed="true"] { background: var(--paper); color: var(--ink); }
.seg { display: flex; border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }
.seg button { height: 44px; padding: 0 14px; border: 0; background: var(--board); color: var(--mute); font: 13px var(--mono); cursor: pointer; }
.seg button[aria-pressed="true"] { background: var(--qubit); color: var(--ink); font-weight: 600; }

.stage.wrap { padding: 20px 32px 28px; }
@media (max-width: 640px) { .stage.wrap { padding: 16px 16px 24px; } .flanes { flex-direction: row; flex-wrap: wrap; } }
.stage:fullscreen { background: var(--ink); overflow: auto; padding: 24px; max-width: none; }
.scene { display: flex; flex-wrap: wrap; gap: 20px; }
.panel { background: var(--board); border-radius: 12px; padding: 20px 22px; min-width: 0; }
@media (max-width: 640px) { .panel { padding: 16px 14px; } }
.main-col { flex: 999 1 640px; min-width: 0; display: flex; flex-direction: column; gap: 14px; }
.side-col { flex: 1 1 340px; min-width: 0; display: flex; flex-direction: column; gap: 16px; }
h2.big { margin: 0; font: 800 clamp(34px, 5vw, 52px)/.95 var(--head); letter-spacing: .01em; text-transform: uppercase; }
h2.mid { margin: 0; font: 800 clamp(28px, 4vw, 40px)/1 var(--head); letter-spacing: .01em; text-transform: uppercase; }
.lede { font-size: 17px; color: var(--soft); margin: 0; }
.stat { background: var(--board); border-radius: 12px; padding: 20px; display: flex; flex-direction: column; gap: 6px; border-top: 4px solid var(--qubit); }
.stat.y { border-top-color: var(--signal); }
.stat .v { font: 800 clamp(64px, 9vw, 96px)/.9 var(--head); color: var(--qubit); font-variant-numeric: tabular-nums; }
.stat.y .v { font-size: clamp(52px, 7vw, 72px); color: var(--signal); }
.stat .s { font: 13px var(--mono); color: var(--soft); }

.hist { position: relative; height: 420px; border-radius: 10px; background: var(--well); padding: 20px 16px 40px; display: flex; align-items: flex-end; gap: 3px; }
@media (max-width: 640px) { .hist { height: 280px; gap: 1px; padding: 14px 8px 52px; } }
.hist .bar { flex: 1; min-width: 1px; border-radius: 2px 2px 0 0; transition: height .18s linear; }
.hist .cap { position: absolute; left: 16px; right: 16px; bottom: 10px; display: flex; justify-content: space-between; gap: 4px 10px; flex-wrap: wrap;
  font: 11px var(--mono); color: var(--dim); text-transform: uppercase; }
.prog { display: flex; align-items: center; gap: 14px; }
.prog .lbl { font: 12px var(--mono); color: var(--mute); white-space: nowrap; }
.track { position: relative; flex: 1; height: 6px; border-radius: 3px; background: var(--line); cursor: pointer; }
.track .fill { height: 100%; border-radius: 3px; background: var(--qubit); width: 0; }
.track .knob { position: absolute; top: 50%; width: 18px; height: 18px; border-radius: 50%; background: var(--paper); transform: translate(-50%, -50%); left: 0; }
.track.y .fill { background: var(--signal); }
.legend { display: flex; flex-wrap: wrap; gap: 10px 18px; font: 12px var(--mono); color: var(--mute); }
.legend span { display: flex; align-items: center; gap: 6px; }
.legend i { width: 14px; height: 14px; border-radius: 2px; display: inline-block; }
.legend i.ln { height: 4px; width: 22px; border-radius: 0; }
.legend i.dash { height: 0; width: 22px; border-top: 3px dashed var(--qubit); border-radius: 0; }

.wire { position: relative; display: flex; align-items: center; gap: 10px; height: 34px; }
.wire .wl { width: 58px; font: 12px var(--mono); color: var(--mute); }
.wire .wr { position: relative; flex: 1; height: 34px; display: flex; align-items: center; justify-content: space-around; }
.wire .wr::before { content: ""; position: absolute; left: 0; right: 0; top: 16px; height: 2px; background: var(--line); }
.gate { position: relative; padding: 4px 8px; border-radius: 4px; color: var(--ink); font: 600 12px var(--mono); }
.meas { position: relative; width: 22px; height: 22px; border-radius: 4px; border: 2px solid var(--paper); }

.terminal { position: relative; border-radius: 10px; background: var(--well); overflow: hidden; }
.terminal svg { position: absolute; inset: 0; width: 100%; height: 100%; }
.gpost { position: absolute; transform: translate(-50%, -50%); display: flex; flex-direction: column; align-items: center; gap: 5px; z-index: 2; }
.gsign { min-width: 64px; padding: 5px 8px; border-radius: 6px; background: var(--signal); color: var(--ink); font: 800 24px/1 var(--head); text-align: center; }
.gchip { min-width: 64px; padding: 5px 8px; border-radius: 6px; background: var(--flap); border: 2px solid var(--line); color: var(--paper);
  font: 600 15px var(--mono); text-align: center; transition: border-color .3s, color .3s; }
.gchip.moved { border-color: var(--qubit); color: var(--qubit); }
@media (max-width: 640px) { .gsign { min-width: 36px; font-size: 15px; padding: 3px 4px; } .gchip { min-width: 36px; font-size: 10px; padding: 2px 3px; } }
.tlegend { position: absolute; left: 14px; bottom: 12px; z-index: 3; }

.flaps { display: flex; gap: 4px; align-items: center; }
.flap { position: relative; border-radius: 4px; background: var(--flap); display: flex; align-items: center; justify-content: center;
  font-family: var(--mono); font-weight: 600; perspective: 300px; overflow: hidden; flex: 0 0 auto; }
.flap::after { content: ""; position: absolute; left: 0; right: 0; top: calc(50% - 1px); height: 2px; background: var(--ink); z-index: 3; }
.flap .ov { position: absolute; left: 0; right: 0; top: 0; height: 50%; overflow: hidden; background: var(--flap); transform-origin: bottom; z-index: 2; }
.flap .ov span { position: absolute; left: 0; right: 0; top: 0; display: flex; align-items: center; justify-content: center; }
.board-row { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; align-items: center; }
.board-row .flap { width: 22px; height: 34px; font-size: 17px; }
@media (max-width: 640px) { .board-row .flap { width: 17px; height: 28px; font-size: 13px; } }
.board-head { font: 11px var(--mono); letter-spacing: .12em; color: var(--mute); padding: 0 4px; }
.st { font: 600 12px var(--mono); letter-spacing: .1em; color: var(--mute); }
.st.mv { color: var(--qubit); }
.cost-flaps .flap { width: 64px; height: 88px; font-size: 54px; border-radius: 6px; }
@media (max-width: 640px) { .cost-flaps .flap { width: 46px; height: 64px; font-size: 38px; } }
.pill { padding: 6px 10px; border-radius: 999px; border: 1px solid var(--qubit); color: var(--qubit); font: 12px var(--mono); }
.pill.n { border-color: var(--line); color: var(--soft); }
.foot-strip { font: 12px var(--mono); letter-spacing: .14em; color: var(--dim); overflow: hidden; white-space: nowrap; text-overflow: ellipsis; min-width: 0; }

.passes { display: flex; flex-wrap: wrap; gap: 20px; }
.pass { position: relative; flex: 1 1 340px; min-width: 0; display: flex; background: var(--paper); color: var(--ink); border-radius: 14px; overflow: hidden; min-height: 290px; }
.pass .body { flex: 1; min-width: 0; padding: 20px 22px; display: flex; flex-direction: column; gap: 12px; }
.pass .k { font: 11px var(--mono); letter-spacing: .16em; color: var(--ink-2); }
.pass .tag { padding: 3px 8px; border-radius: 4px; color: var(--ink); font: 600 11px var(--mono); }
.pass .route { display: flex; align-items: center; gap: 12px; font: 800 44px/.9 var(--head); flex-wrap: wrap; }
.pass .fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px 16px; margin-top: auto; }
.pass .fk { font: 10px var(--mono); letter-spacing: .14em; color: var(--ink-2); }
.pass .fv { font: 600 20px var(--mono); }
.pass .cut { width: 0; border-left: 2px dashed #B9B5A8; margin: 16px 0; }
.pass .stub { width: 116px; padding: 20px 10px; display: flex; flex-direction: column; justify-content: space-between; align-items: center; gap: 12px; }
.pass .stub .sv { font: 800 48px/1 var(--head); }
.pass .notch { position: absolute; right: 105px; width: 22px; height: 22px; border-radius: 50%; background: var(--ink); }
@media (max-width: 480px) { .pass .stub { width: 84px; } .pass .notch { right: 73px; } .pass .route { font-size: 34px; } .pass .fv { font-size: 16px; } }
.barcode { display: flex; gap: 2px; height: 72px; }
.barcode i { background: var(--ink); display: block; }

.tbl { background: var(--board); border-radius: 12px; padding: 14px 16px; overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font: 14px var(--mono); }
th { text-align: left; color: var(--mute); font-size: 11px; letter-spacing: .14em; font-weight: 500; padding: 8px 10px; white-space: nowrap; }
td { padding: 11px 10px; border-top: 1px solid var(--line); white-space: nowrap; }
td.r, th.r { text-align: right; }
.detail { padding: 34px 0 10px; border-top: 1px solid var(--line); }
.sec-head { display: flex; align-items: center; gap: 14px; margin-bottom: 16px; flex-wrap: wrap; }
.num-sign { padding: 4px 12px; border-radius: 6px; background: var(--signal); color: var(--ink); font: 800 28px/1 var(--head); }
.sec-head h3 { margin: 0; font: 800 clamp(30px, 4vw, 44px)/1 var(--head); text-transform: uppercase; }
.sec-head p { margin: 0; flex-basis: 100%; color: var(--soft); }
.grid2 { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px; }
@media (max-width: 900px) { .grid2 { grid-template-columns: minmax(0, 1fr); } }
.heat { display: grid; gap: 2px; max-width: 340px; }
.heat div { aspect-ratio: 1; border-radius: 2px; }
.chart svg { width: 100%; height: auto; display: block; }
#lamChart { max-width: 860px; }
.chart text { font-family: var(--mono); font-size: 11px; fill: var(--mute); }
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chips span { padding: 6px 10px; border-radius: 999px; border: 1px solid var(--line); font: 12px var(--mono); color: var(--soft); }
.chips b { color: var(--paper); font-weight: 600; }
ul.lim { margin: 0; padding-left: 18px; color: var(--soft); } ul.lim li { margin: 6px 0; }
.twocol { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
@media (max-width: 700px) { .twocol { grid-template-columns: minmax(0, 1fr); } }
.twocol ul { margin: 8px 0 0; padding-left: 18px; color: var(--soft); font-size: 15px; }
.qside { border-top: 4px solid var(--qubit); } .cside { border-top: 4px solid var(--signal); }
.waves { display: block; width: 100%; height: 48px; margin-top: 6px; }
/* 00 Panorama: código de enfoques (ícono + palabra, nunca solo color) */
.ap { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 999px; border: 1.5px solid currentColor;
  font: 600 12px var(--mono); letter-spacing: .08em; white-space: nowrap; vertical-align: middle; }
.ap b { font-weight: 600; }
.ap-w { font-weight: 400; letter-spacing: .02em; opacity: .85; margin-left: 4px; white-space: normal; }
.ap-classic { color: var(--paper); } .ap-quantum { color: var(--qubit); } .ap-hybrid { color: var(--signal); }
.sec-head .ap { margin-left: 4px; }
td .ap { font-size: 10px; padding: 2px 7px; margin-right: 6px; }
#scene-pano { flex-direction: column; flex-wrap: nowrap; gap: 12px; }
#scene-pano h2.big { font-size: clamp(28px, 3.4vw, 40px); }
#scene-pano .fbox { padding: 8px 14px; flex-direction: row; align-items: baseline; gap: 10px; }
#scene-pano .fbox b { font-size: 24px; }
#scene-pano .flanes { flex-direction: row; gap: 6px; flex-wrap: wrap; }
#scene-pano .pline { font-size: 16px; }
#scene-pano .goto { height: 34px; margin-top: 4px; }
#scene-pano table.cmp td, #scene-pano table.cmp th { padding: 6px 12px; }
#scene-pano .cmp-wrap { padding: 8px 14px; }
.flow { display: flex; align-items: stretch; gap: 10px; flex-wrap: wrap; }
.fbox { background: var(--board); border-radius: 10px; padding: 12px 16px; display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.fbox b { font: 800 30px/1 var(--head); text-transform: uppercase; }
.fbox span { font: 13px var(--mono); color: var(--soft); }
.farr { align-self: center; font: 800 30px var(--head); color: var(--signal); }
.flanes { display: flex; flex-direction: column; justify-content: center; gap: 6px; }
.lanes { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 18px; }
@media (max-width: 1000px) { .lanes { grid-template-columns: minmax(0, 1fr); } .farr { display: none; } }
.lane { background: var(--board); border-radius: 12px; padding: 14px 18px; display: flex; flex-direction: column; gap: 6px; border-top: 5px solid; min-width: 0; }
.lane-classic { border-top-color: var(--paper); } .lane-quantum { border-top-color: var(--qubit); } .lane-hybrid { border-top-color: var(--signal); }
.lane .ap { font-size: 13px; padding: 6px 12px; white-space: normal; }
.what { margin: 0; color: var(--soft); font-size: 16px; }
.star { font: 800 clamp(56px, 6vw, 80px)/.9 var(--head); }
.lane-classic .star { color: var(--paper); } .lane-quantum .star { color: var(--qubit); } .lane-hybrid .star { color: var(--signal); }
.star-s { font: 13px var(--mono); color: var(--soft); margin-top: -4px; }
.pline { font-size: 15px; color: var(--soft); } .pline b { color: var(--paper); }
.pline .hw { font: 600 11px var(--mono); color: var(--ink); background: var(--qubit); padding: 1px 6px; border-radius: 4px; margin-right: 4px; }
.steps { margin: 4px 0 0; padding-left: 20px; color: var(--paper); font-size: 15px; } .steps li { margin: 3px 0; }
.kvs { display: grid; gap: 4px; margin-top: auto; border-top: 1px solid var(--line); padding-top: 10px; }
.kv { display: flex; justify-content: space-between; gap: 10px; font: 13px var(--mono); }
.kv span { color: var(--mute); } .kv b { font-weight: 600; text-align: right; }
.goto { align-self: flex-start; height: 40px; padding: 0 14px; border-radius: 8px; border: 1px solid var(--line); background: var(--flap); color: var(--paper); font: 13px var(--mono); cursor: pointer; }
.goto:hover { border-color: var(--signal); color: var(--signal); }
.cmp-wrap { position: relative; background: var(--board); border-radius: 12px; padding: 14px 16px; overflow-x: auto; }
table.cmp td { position: relative; }
table.cmp { min-width: 860px; font: 16px var(--sans); }
table.cmp th { vertical-align: bottom; padding: 10px 12px; } table.cmp thead th { white-space: normal; }
.th-s { font: 600 14px var(--sans); color: var(--paper); letter-spacing: 0; margin-top: 6px; text-transform: none; }
table.cmp tbody th { color: var(--paper); font: 600 15px var(--sans); letter-spacing: 0; text-align: left; white-space: normal; width: 170px; border-top: 1px solid var(--line); vertical-align: top; padding-top: 11px; }
table.cmp td { white-space: normal; vertical-align: top; line-height: 1.35; }
.mk { font: 700 18px var(--mono); }
.m-ok .mk, b.m-ok { color: var(--paper); } .m-no .mk, b.m-no { color: var(--invalid); } .m-mid .mk, b.m-mid { color: var(--mute); }
.sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
.cmp-leg { margin-top: 10px; }
.verdict { margin: 0; font: 600 clamp(18px, 2vw, 22px)/1.35 var(--sans); border-left: 4px solid var(--signal); padding: 4px 0 4px 14px; }
footer { border-top: 1px solid var(--line); margin-top: 30px; padding: 22px 0 40px; font: 12px var(--mono); letter-spacing: .08em; color: var(--mute); }
@media (prefers-reduced-motion: reduce) { .hist .bar, .gchip { transition: none; } }
</style>
</head>
<body>
<script id="data" type="application/json">__DATA__</script>

<header class="top"><div class="wrap">
  <div class="brand">
    <svg width="40" height="40" viewBox="0 0 64 64" role="img" aria-label="QGate"><rect width="64" height="64" rx="10" fill="#FFC629"></rect><circle cx="29" cy="29" r="15" fill="none" stroke="#0B0B0C" stroke-width="7"></circle><path d="M38 38 L48 48" stroke="#0B0B0C" stroke-width="7" stroke-linecap="square"></path><polygon points="55,55 55,40 40,55" fill="#0B0B0C"></polygon></svg>
    <b>QGATE</b><span id="kicker" hidden></span>
  </div>
  <nav class="tabs" role="tablist" aria-label="Escenas">
    <button role="tab" data-scene="pano" aria-selected="true">00 PANORAMA</button>
    <button role="tab" data-scene="qaoa" aria-selected="false">01 QAOA</button>
    <button role="tab" data-scene="airport" aria-selected="false">02 AEROPUERTO</button>
    <button role="tab" data-scene="result" aria-selected="false">03 RESULTADO</button>
    <button role="tab" data-scene="final" aria-selected="false" id="tabFinal">04 ESCALA</button>
  </nav>
  <div class="ctrl">
    <button class="btn play q" id="play" type="button" aria-label="Reproducir"></button>
    <button class="btn" id="speed" type="button" aria-pressed="false">x2</button>
    <div class="seg" id="mixerSeg" role="group" aria-label="Mixer">
      <button type="button" data-mixer="x" aria-pressed="false">MIXER X</button>
      <button type="button" data-mixer="xy" aria-pressed="true">MIXER XY</button>
    </div>
    <button class="btn" id="fs" type="button">Pantalla completa</button>
  </div>
</div></header>

<main>
<div class="stage wrap" id="stage">

  <div class="scene" id="scene-pano">
    <h2 class="big">Tres enfoques, un problema</h2>
    __PANORAMA__
  </div>

  <div class="scene hidden" id="scene-qaoa">
    <section class="panel main-col">
      <div style="display:flex;flex-direction:column;gap:6px">
        <h2 class="big">QAOA aprende a respetar las reglas</h2>
        <p class="lede" id="qLede"></p>
      </div>
      <div class="hist" id="hist"><div class="cap"><span id="histCap"></span><span id="histShots"></span></div></div>
      <div class="prog" id="qProg"><span class="lbl" id="qIter"></span><div class="track" id="qTrack"><div class="fill"></div><div class="knob"></div></div></div>
      <div class="legend">
        <span><i style="background:var(--invalid-bar)"></i>Inválida (rompe una regla)</span>
        <span><i style="background:var(--qubit)"></i>Válida</span>
        <span><i style="background:var(--signal)"></i>Óptima</span>
      </div>
    </section>
    <section class="side-col">
      <div class="stat" id="qValidBox"><div class="kick">P(asignación válida)</div><div class="v" id="qValid"></div><div class="s" id="qValidS"></div></div>
      <div class="stat y" id="qOptBox"><div class="kick">P(asignación óptima)</div><div class="v" id="qOpt"></div><div class="s" id="qOptS"></div></div>
      <div class="panel" style="display:flex;flex-direction:column;gap:12px">
        <div class="kick" id="wireHead"></div>
        <div id="wires"></div>
        <div style="font-size:14px;color:var(--soft)" id="wireNote"></div>
        <svg class="waves" viewBox="0 0 400 48" preserveAspectRatio="none" aria-hidden="true">
          <path d="M0 24 C 25 4, 50 44, 75 24 S 125 4, 150 24 S 200 44, 225 24 S 275 4, 300 24 S 350 44, 400 24" fill="none" stroke="#4FE3E0" stroke-width="1.5"/>
          <path d="M0 24 C 25 13, 50 35, 75 24 S 125 13, 150 24 S 200 35, 225 24 S 275 13, 300 24 S 350 35, 400 24" fill="none" stroke="#4FE3E0" stroke-opacity=".55" stroke-width="1"/>
          <path d="M0 24 C 25 20, 50 28, 75 24 S 125 20, 150 24 S 200 28, 225 24 S 275 20, 300 24 S 350 28, 400 24" fill="none" stroke="#4FE3E0" stroke-opacity=".3" stroke-width="1"/>
        </svg>
      </div>
    </section>
  </div>

  <div class="scene hidden" id="scene-airport">
    <section class="panel main-col">
      <div style="display:flex;justify-content:space-between;align-items:baseline;gap:12px;flex-wrap:wrap">
        <h2 class="mid">Terminal Q · Muelle A</h2>
        <span class="kick">Grosor = pasajeros en conexión</span>
        <span class="kick" style="flex-basis:100%;color:var(--signal)" id="replayNote"></span>
      </div>
      <div class="terminal" id="terminal"></div>
      <div class="prog" id="hProg"><span class="lbl" id="hIterLbl"></span><div class="track y" id="hTrack"><div class="fill"></div><div class="knob"></div></div></div>
    </section>
    <section class="side-col">
      <div class="panel" style="display:flex;flex-direction:column;gap:10px">
        <div style="display:flex;align-items:center;gap:12px">
          <div style="width:40px;height:40px;border-radius:6px;background:var(--signal);display:flex;align-items:center;justify-content:center;flex:0 0 auto">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#0B0B0C" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M17.8 19.2 16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.2c.4-.3.6-.7.5-1.2z"></path></svg>
          </div>
          <h2 class="mid" style="color:var(--signal)">Salidas</h2>
          <span class="kick" style="margin-left:auto" id="vuelta"></span>
        </div>
        <div class="board-row board-head"><div>VUELO</div><div>PUERTA</div><div>ESTADO</div></div>
        <div id="board" style="display:flex;flex-direction:column;gap:8px"></div>
      </div>
      <div class="panel" style="display:flex;flex-direction:column;gap:12px">
        <div style="display:flex;justify-content:space-between;align-items:baseline;gap:10px;flex-wrap:wrap">
          <span class="kick">Costo total · caminata ponderada</span><span class="kick" id="optLbl"></span>
        </div>
        <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap">
          <div class="flaps cost-flaps" id="costFlaps"></div>
          <div style="display:flex;flex-direction:column;gap:4px">
            <div style="font:700 28px var(--head);color:var(--signal)" id="gapLbl"></div>
            <div class="kick" style="letter-spacing:.06em;text-transform:none">valores reales desde results.json</div>
          </div>
        </div>
        <div style="height:6px;border-radius:3px;background:var(--line);overflow:hidden"><div id="costBar" style="height:100%;width:0;background:var(--signal);transition:width .3s"></div></div>
        <div style="display:flex;flex-wrap:wrap;gap:8px" id="hPills"></div>
      </div>
    </section>
    <div class="foot-strip" style="flex-basis:100%" id="strip"></div>
  </div>

  <div class="scene hidden" id="scene-final" style="flex-direction:column;flex-wrap:nowrap;gap:16px">
    <h2 class="big">Etapa 3 · escalamiento</h2>
    <p class="verdict" id="finSentence"></p>
    <p class="lede" style="font-size:14px" id="finMeta"></p>
    <div class="panel"><div class="kick" style="margin-bottom:8px">¿Cuánto es cuántico y cuánto clásico? · híbrido QAOA en dos fases · SIMULADOR</div>
      <div class="tbl" style="padding:0;background:none"><table><thead><tr><th>INSTANCIA</th><th class="r">(I) VARIABLES CUÁNTICAS 9/N²</th>
        <th class="r">(II) MOVIMIENTOS SWAP · BLOQUE QAOA · PERTURBACIÓN</th><th class="r">(III) REDUCCIÓN DE COSTO SWAP · BLOQUE · PERTURBACIÓN</th>
        <th class="r">(IV) % TIEMPO EN QAOA · SOLO AER</th></tr></thead><tbody id="finAttr"></tbody></table></div>
      <ul class="lim" id="finDefs" style="font-size:13px;margin-top:10px"></ul></div>
    <div class="panel"><div class="kick" style="margin-bottom:8px">(V) Tasa de mejora de los bloques k=3 desde un óptimo local 2-swap</div>
      <div class="tbl" style="padding:0;background:none"><table><thead><tr><th>INSTANCIA</th><th class="r">ENUMERACIÓN</th><th class="r">AZAR 6 VÁLIDAS</th><th class="r">ENUMERACIÓN + DESEMPATE</th><th class="r">QAOA</th></tr></thead><tbody id="finRates"></tbody></table></div></div>
    <div class="tbl"><div class="kick" style="padding:6px 10px">Escalamiento · costo mediana [mín, máx] entre semillas · gap vs cota GL y vs mejor costo encontrado</div>
      <table><thead><tr><th>INSTANCIA</th><th>MÉTODO</th><th>SELECTOR</th><th class="r">COSTO MEDIANA [MÍN, MÁX]</th><th class="r">GAP COTA GL</th><th class="r">GAP VS MEJOR ENCONTRADO</th><th class="r">TIEMPO</th><th class="r">MEMORIA</th><th class="r">FACTIBLE</th></tr></thead>
      <tbody id="finRows"></tbody></table></div>
    <p class="lede" style="font-size:14px" id="finReuse"></p>
  </div>

  <div class="scene hidden" id="scene-result" style="flex-direction:column;flex-wrap:nowrap">
    <h2 class="big">Tres tarjetas de embarque, una por pregunta</h2>
    <div class="passes" id="passes"></div>
    <div class="tbl"><table><thead><tr><th>MÉTODO</th><th>N</th><th>QUBITS</th><th>MEJOR COSTO VÁLIDO</th><th>GAP</th><th>TIEMPO</th><th>DÓNDE CORRIÓ</th></tr></thead>
      <tbody id="resRows"></tbody></table></div>
    <p class="lede" style="font-size:14px" id="resNote"></p>
  </div>
</div>

<div class="wrap">
  <section class="detail" id="d-valid">
    <div class="sec-head"><span class="num-sign">04</span><h3>Datos validados</h3>
      <p>Del MPS linealizado a flujos F y distancias D. La escala se verifica con los óptimos de control; cada par se cuenta una vez.</p></div>
    <div class="grid2">
      <div><div class="tbl"><table><thead><tr><th>N</th><th class="r">ÓPTIMO CALCULADO</th><th class="r">ESPERADO</th><th>OK</th><th class="r">TIEMPO</th></tr></thead><tbody id="valRows"></tbody></table></div>
        <div class="chips" id="facts" style="margin-top:14px"></div></div>
      <div class="panel"><div class="grid2" style="gap:16px">
        <div><div class="kick" style="margin-bottom:8px">F · pasajeros en conexión</div><div class="heat" id="heatF"></div></div>
        <div><div class="kick" style="margin-bottom:8px">D · distancia entre puertas</div><div class="heat" id="heatD"></div></div>
      </div></div>
    </div>
    <div class="panel" style="margin-top:20px" id="recBox"><div class="kick" style="margin-bottom:8px">Cómo se recuperaron los coeficientes del MPS</div>
      <ol class="steps" id="recSteps"></ol></div>
    <div class="twocol" style="margin-top:20px">
      <div class="panel qside"><div class="kick" style="color:var(--qubit)">Qiskit hace</div><ul>
        <li>Circuito QAOA: costo Ising + mixer X, o estado W + mixer XY</li>
        <li>Statevector exacto y muestreo con shots en Aer, con y sin ruido</li>
        <li>Transpilación: profundidad y CX</li>
        <li>Cada subproblema de 9 qubits del híbrido (QAOA p=2)</li></ul></div>
      <div class="panel cside"><div class="kick" style="color:var(--signal)">Clásico hace</div><ul>
        <li>Leer el MPS y reconstruir F y D</li>
        <li>QUBO, λ, paso a Ising; COBYLA ajusta los ángulos</li>
        <li>Elegir vecindarios, aceptar mejoras, perturbar</li>
        <li>Referencias: fuerza bruta, SA, cota Gilmore-Lawler</li></ul></div>
    </div>
  </section>

  <section class="detail" id="d-ablation">
    <div class="sec-head"><span class="num-sign">05</span><h3>¿Cuánto aporta QAOA?</h3>
      <p>El mismo híbrido con distintos solvers del subproblema, mismas iteraciones, semilla (una sola, la 7) y arranque. Con muchas muestras el azar también resuelve piezas de 3 vuelos; con pocas se ve la concentración de QAOA.</p></div>
    <div class="tbl"><table><thead><tr><th>SOLVER</th><th class="r">SHOTS</th><th class="r">COSTO FINAL</th><th class="r">GAP</th><th class="r">PIEZAS RESUELTAS</th><th class="r">P(ÓPTIMO) POR PIEZA</th><th class="r">AZAR (27 ESTADOS)</th><th class="r">TIEMPO</th></tr></thead>
      <tbody id="ablRows"></tbody></table></div>
    <p class="verdict" id="ablRead" style="margin-top:14px"></p>
    <div class="panel" style="margin-top:14px" id="whyBox"><div class="kick" style="margin-bottom:8px">¿Por qué QAOA aquí?</div><ul class="lim" id="whyList"></ul></div>
    <div class="chips" id="seedChips" style="margin-top:14px"></div>
  </section>

  <section class="detail hidden" id="d-hw">
    <div class="sec-head"><span class="num-sign">05b</span><h3>IBM Quantum real</h3>
      <p id="hwLede"></p></div>
    <div class="tbl"><table><thead><tr><th>EXPERIMENTO</th><th class="r">QUBITS</th><th class="r">VÁLIDAS EN HARDWARE</th><th class="r">IDEAL (AER)</th><th class="r">AER CON RUIDO 1%</th><th class="r">AZAR P(VÁLIDA)</th><th class="r">P(ÓPTIMO)</th><th class="r">AZAR P(ÓPTIMO) · RAZÓN</th><th class="r">MEJOR COSTO</th><th class="r">PROFUNDIDAD</th><th class="r">COMPUERTAS 2Q</th></tr></thead>
      <tbody id="hwRows"></tbody></table></div>
  </section>

  <section class="detail" id="d-lambda">
    <div class="sec-head"><span class="num-sign">06</span><h3>Barrido de λ</h3>
      <p>λ0 es el mayor aporte posible de una asignación: criterio suficiente razonable, validado con este barrido. λ chico deja ganar inválidas; λ grande aplana el paisaje.</p></div>
    <div class="panel"><div class="legend" id="lamLegend" style="margin-bottom:10px"></div><div class="chart" id="lamChart"></div></div>
  </section>

  <section class="detail" id="d-scale">
    <div class="sec-head"><span class="num-sign">07</span><h3 id="scTitle">Escalamiento</h3>
      <p>La parte cuántica no crece: 9 qubits por subproblema en todo N. 150 iteraciones por N (no comparable con 02, que usa 300). La cota Gilmore-Lawler es débil: en N=10 SA está en el óptimo y aun así marca más de 10% contra ella. Sin óptimo conocido en N &gt; 10 se mide contra la cota Gilmore-Lawler. * = instancia sintética.</p>
      <p id="scDay1" hidden style="border-left:3px solid var(--signal);padding-left:10px"></p></div>
    <div class="grid2">
      <div class="panel"><div class="kick" style="margin-bottom:8px">Gap vs cota inferior (%)</div><div class="legend" id="scLeg" style="margin-bottom:8px"></div><div class="chart" id="scGap"></div></div>
      <div class="panel"><div class="kick" style="margin-bottom:8px">Tiempo (s, escala log)</div><div class="legend" id="scLeg2" style="margin-bottom:8px"></div><div class="chart" id="scTime"></div></div>
    </div>
    <div class="tbl" style="margin-top:20px"><table><thead><tr><th>N</th><th>INSTANCIA</th><th>MÉTODO</th><th class="r">COSTO</th><th class="r">COTA</th><th class="r">GAP COTA</th><th class="r">TIEMPO</th><th class="r">MEMORIA PICO</th><th class="r">QUBITS</th></tr></thead><tbody id="scRows"></tbody></table></div>
    <div class="tbl" style="margin-top:20px;max-width:560px" id="memBox"><div class="kick" style="padding:6px 10px">Muro de memoria · statevector genérico</div>
      <table><thead><tr><th class="r">N</th><th class="r">QUBITS N²</th><th class="r">MEMORIA</th></tr></thead><tbody id="memRows"></tbody></table></div>
  </section>

  <section class="detail" id="d-repro">
    <div class="sec-head"><span class="num-sign">08</span><h3>Reproducibilidad y límites</h3></div>
    <div class="grid2">
      <div class="panel"><div class="kick" style="margin-bottom:10px">Entorno</div><div class="chips" id="versions"></div>
        <pre class="mono" id="cmd" style="white-space:pre-wrap;color:var(--soft);font-size:13px;margin:14px 0 0"></pre></div>
      <div class="panel"><div class="kick" style="margin-bottom:10px">Limitaciones</div><ul class="lim" id="limits"></ul></div>
    </div>
  </section>
</div>
</main>

<footer><div class="wrap">AMARILLO = SEÑALÉTICA Y LO ÓPTIMO · CIAN = TODO LO QUE SALE DE QISKIT · NARANJA = INVÁLIDO<br>
QGate · IBM Quantum Hackathon 2026 · Reto NTT DATA QAP10 · Track A Aeropuerto · Qiskit, Qiskit Aer, NumPy, SciPy · datos MIPLIB 2017 qap10 ·
<a href="https://github.com/iamjosels/qgate-qap10">código</a> <span id="gen"></span><br>
Desarrollado con asistencia de Claude Code (Anthropic), supervisada por el equipo; parte del motor se preparó antes de la jornada; los cuatro integrantes pueden explicar su funcionamiento. Créditos: Qiskit, Qiskit Aer, qiskit-ibm-runtime, NumPy, SciPy, MIPLIB 2017 (qap10), Claude Code.</div></footer>

<script>
(function () {
  "use strict";
  const R = JSON.parse(document.getElementById("data").textContent);
  const $ = (id) => document.getElementById(id);
  const has = (a) => Array.isArray(a) && a.length > 0;
  const num = (v) => typeof v === "number" && isFinite(v);
  const hide = (el) => { if (typeof el === "string") el = $(el); if (el) el.classList.add("hidden"); };
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const f = (v, d = 0) => num(v) ? Number(v).toFixed(d) : null;
  const pct = (v, d = 1) => num(v) ? (100 * v).toFixed(d) + "%" : null;
  const sp = (n) => num(n) ? String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, " ") : null;
  const pad2 = (i) => String(i + 1).padStart(2, "0");
  const V = (i) => "V" + pad2(i), P = (j) => "P" + pad2(j);
  const RM = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  /* Pone el texto o, si el dato no existe, oculta el elemento (nunca un valor de relleno). */
  const put = (id, txt, box) => { const el = $(id); if (!el) return; if (txt === null || txt === undefined || txt === "") hide(box ? $(box) : el); else { el.textContent = txt; el.classList.remove("hidden"); } };

  const meta = R.meta || {}, data = R.data || {};
  const REF = meta.reference_optimum, N = meta.N;
  const gap = (c, ref = REF) => (num(c) && num(ref) && ref) ? 100 * (c - ref) / ref : null;
  const Q = {}; (R.quantum || []).forEach((q) => { Q[q.id] = q; });
  const H = {}; (R.hybrid || []).forEach((h) => { H[h.method] = h; });
  const C = {}; (R.classical || []).forEach((c) => { C[c.method] = c; });
  const valid = {}; (R.validation || []).forEach((v) => { valid[v.n] = v; });
  /* chip de enfoque (ícono + palabra): se copia del que genera panorama.py */
  const AP = (k) => { const el = document.querySelector(".flanes .ap-" + k); return el ? el.outerHTML : ""; };

  /* split-flap: la mitad superior del carácter anterior gira hacia abajo, escalonado por ficha */
  function flapSet(el, text) {
    const chars = String(text).split("");
    while (el.children.length < chars.length) { const d = document.createElement("div"); d.className = "flap"; d.innerHTML = "<b></b>"; el.appendChild(d); }
    while (el.children.length > chars.length) el.removeChild(el.lastChild);
    chars.forEach((ch, i) => {
      const d = el.children[i], b = d.firstChild, old = b.textContent;
      if (old === ch) return;
      b.textContent = ch;
      if (RM || old === "" || !d.animate) return;
      const ov = document.createElement("div"); ov.className = "ov";
      const sp2 = document.createElement("span"); sp2.textContent = old; sp2.style.height = d.clientHeight + "px"; ov.appendChild(sp2);
      d.appendChild(ov);
      ov.animate([{ transform: "rotateX(0deg)" }, { transform: "rotateX(-90deg)" }],
        { duration: 220, delay: i * 45, easing: "ease-in", fill: "forwards" }).onfinish = () => ov.remove();
    });
  }

  /* reproducción: cada escena registra un player con step/atEnd/reset/seek */
  let scene = "qaoa", playing = false, speed = 1, timer = null;
  const players = {};
  function tick() {
    const pl = players[scene];
    if (!pl || !playing) return;
    if (!pl.step()) { playing = false; syncPlay(); return; }
    timer = setTimeout(tick, pl.delay / speed);
  }
  function syncPlay() {
    const b = $("play");
    b.setAttribute("aria-label", playing ? "Pausar" : "Reproducir");
    b.innerHTML = playing
      ? '<svg width="20" height="20" viewBox="0 0 24 24" fill="#0B0B0C" aria-hidden="true"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>'
      : '<svg width="20" height="20" viewBox="0 0 24 24" fill="#0B0B0C" aria-hidden="true"><path d="M7 4l13 8-13 8z"/></svg>';
    b.classList.toggle("q", scene === "qaoa");
    b.classList.toggle("hidden", !players[scene]);
    $("speed").classList.toggle("hidden", !players[scene]);
  }
  function setPlaying(on) {
    clearTimeout(timer); playing = !!on && !!players[scene];
    if (playing && players[scene].atEnd()) players[scene].reset();
    syncPlay(); if (playing) timer = setTimeout(tick, 120);
  }
  $("play").addEventListener("click", () => setPlaying(!playing));
  $("speed").addEventListener("click", () => { speed = speed === 1 ? 2 : 1; $("speed").setAttribute("aria-pressed", speed === 2); });
  $("fs").addEventListener("click", () => {
    const st = $("stage");
    if (document.fullscreenElement) document.exitFullscreen(); else if (st.requestFullscreen) st.requestFullscreen();
  });
  function showScene(s) {
    scene = s; clearTimeout(timer);
    document.querySelectorAll(".tabs button").forEach((b) => b.setAttribute("aria-selected", b.dataset.scene === s));
    ["pano", "qaoa", "airport", "result", "final"].forEach((k) => $("scene-" + k).classList.toggle("hidden", k !== s));
    /* cada sección de detalle vive bajo la pestaña de su enfoque: así cada dato aparece una sola vez */
    const TAB = { "d-hw": "qaoa", "d-lambda": "qaoa", "d-ablation": "airport", "d-scale": "airport", "d-valid": "result", "d-repro": "result" };
    Object.entries(TAB).forEach(([id, tab]) => { const el = $(id); if (el) el.classList.toggle("off-tab", tab !== s); });
    $("mixerSeg").classList.toggle("hidden", s !== "qaoa");
    $("kicker").textContent = { pano: "PANORAMA · CLÁSICO · CUÁNTICO · HÍBRIDO", qaoa: "MODO DEMO · COMPUERTAS CUÁNTICAS", airport: "MODO DEMO · TRACK A AEROPUERTO", result: "RESULTADOS · QAP10", final: "ETAPA 3 · ESCALAMIENTO · SIMULADOR" }[s];
    setPlaying(!RM && !!players[s]);
  }
  document.querySelectorAll(".tabs button").forEach((b) => b.addEventListener("click", () => showScene(b.dataset.scene)));
  function bindTrack(id, pl) {
    const tr = $(id);
    tr.addEventListener("click", (e) => { const r = tr.getBoundingClientRect(); setPlaying(false); pl.seek(Math.max(0, Math.min(1, (e.clientX - r.left) / r.width))); });
  }
  function setTrack(id, frac) {
    const tr = $(id); frac = Math.max(0, Math.min(1, frac));
    tr.querySelector(".fill").style.width = (100 * frac) + "%"; tr.querySelector(".knob").style.left = (100 * frac) + "%";
  }

  /* ---------------- 01 QAOA: histograma animado con los frames de la optimización ---------------- */
  (function qaoaScene() {
    const byMixer = {};
    ["x", "xy"].forEach((m) => { const q = (R.quantum || []).find((x) => x.N === 4 && x.p === 1 && x.mixer === m && x.noise === "none"); if (q) byMixer[m] = q; });
    let mixer = byMixer.xy ? "xy" : (byMixer.x ? "x" : null);
    if (!mixer) { hide("mixerSeg"); $("scene-qaoa").innerHTML = '<p class="lede">Sin experimento QAOA N=4 en results.json.</p>'; return; }
    let fi = 0, bars = [];
    const hist = $("hist");
    function render() {
      const q = byMixer[mixer], fr = q.frames;
      const nValid = fr ? fr.kind.filter((k) => k !== "invalid").length : null;
      $("qLede").textContent = `Con ${q.qubits} qubits hay ${sp(2 ** q.qubits)} combinaciones` + (nValid ? ` y solo ${nValid} son asignaciones válidas.` : ".")
        + (fr ? " Mira cómo la probabilidad se mueve hacia ellas mientras el optimizador ajusta los ángulos." : "");
      put("qValidS", num(q.random_feasible_baseline) ? `vs ${pct(q.random_feasible_baseline)} al azar con el mismo mixer` : null);
      put("qOptS", valid[4] && num(valid[4].optimum) ? `óptimo de control N = 4: ${f(valid[4].optimum)}` : null);
      $("wireHead").textContent = `Una fila del circuito · vuelo V01 · ${q.N} qubits`;
      const gates = mixer === "xy" ? [["W", "var(--paper)"], ["COSTO γ", "var(--signal)"], ["XY β", "var(--qubit)"]]
                                   : [["H", "var(--paper)"], ["COSTO γ", "var(--signal)"], ["X β", "var(--qubit)"]];
      $("wires").innerHTML = Array.from({ length: q.N }, (_, j) => `<div class="wire"><div class="wl">V01·P${j + 1}</div><div class="wr">`
        + gates.map(([t, c]) => `<div class="gate" style="background:${c}">${t}</div>`).join("") + '<div class="meas"></div></div></div>').join("");
      $("wireNote").textContent = mixer === "xy" ? "El mixer XY mueve al vuelo entre puertas sin dejarlo nunca en dos a la vez."
        : "El mixer X cambia cada qubit por separado: las reglas solo se cumplen por penalidad.";
      document.querySelectorAll("#mixerSeg button").forEach((b) => { b.setAttribute("aria-pressed", b.dataset.mixer === mixer); b.disabled = !byMixer[b.dataset.mixer]; });
      hist.querySelectorAll(".bar").forEach((b) => b.remove());
      bars = [];
      if (fr) {
        const col = { invalid: "var(--invalid-bar)", valid: "var(--qubit)", optimal: "var(--signal)" };
        const cap = hist.querySelector(".cap");
        fr.kind.forEach((k) => { const b = document.createElement("div"); b.className = "bar"; b.style.background = col[k]; hist.insertBefore(b, cap); bars.push(b); });
        $("histCap").textContent = `Probabilidad exacta de ${fr.states.length} configuraciones (${nValid} válidas + inválidas más probables) · mixer ${mixer.toUpperCase()} · N = ${q.N}`;
        put("histShots", num(q.shots) ? `SHOTS ${q.shots}` : null);
        $("qProg").classList.remove("hidden");
      } else {
        $("histCap").textContent = "Sin frames de la optimización en results.json"; hide("qProg");
      }
      fi = 0; draw();
    }
    function draw() {
      const q = byMixer[mixer], fr = q.frames;
      if (!fr) { put("qValid", pct(q.p_feasible), "qValidBox"); put("qOpt", pct(q.p_optimal), "qOptBox"); return; }
      const mx = Math.max(...fr.p.flat()) || 1, row = fr.p[fi];
      bars.forEach((b, i) => { b.style.height = Math.max(0.6, 100 * row[i] / mx) + "%"; b.title = `${fr.kind[i]} · p = ${row[i].toFixed(4)}`; });
      $("qValid").textContent = pct(fr.p_valid[fi]); $("qOpt").textContent = pct(fr.p_opt[fi]);
      $("qIter").textContent = `EVALUACIÓN ${fr.eval[fi]} / ${fr.n_evals}`;
      setTrack("qTrack", fr.p.length > 1 ? fi / (fr.p.length - 1) : 1);
    }
    document.querySelectorAll("#mixerSeg button").forEach((b) => b.addEventListener("click", () => {
      if (!byMixer[b.dataset.mixer]) return; mixer = b.dataset.mixer; render(); setPlaying(!RM && !!byMixer[mixer].frames);
    }));
    render();
    if (Object.values(byMixer).some((q) => q.frames)) {
      players.qaoa = {
        delay: 160,
        step() { const fr = byMixer[mixer].frames; if (!fr || fi >= fr.p.length - 1) return false; fi++; draw(); return true; },
        atEnd() { const fr = byMixer[mixer].frames; return !fr || fi >= fr.p.length - 1; },
        reset() { fi = 0; draw(); },
        seek(x) { const fr = byMixer[mixer].frames; if (!fr) return; fi = Math.round(x * (fr.p.length - 1)); draw(); },
      };
      bindTrack("qTrack", players.qaoa);
    }
  })();

  /* ---------------- 02 AEROPUERTO: el híbrido mueve vuelos entre puertas ---------------- */
  (function airportScene() {
    const F = data.F, D = data.D, grid = data.gate_grid, xy = data.gate_xy;
    const hq = H.qgate_lns_qaoa, best = R.best_assignment;
    if (!has(F) || !has(D) || !(hq || best)) { $("scene-airport").innerHTML = '<p class="lede">Sin datos del híbrido en results.json.</p>'; return; }
    const n = F.length;
    let pos;
    if (has(grid)) {        // geometría real: D es distancia Manhattan en una grilla
      const cx = Math.max(...grid.map((p) => p[0])), cy = Math.max(...grid.map((p) => p[1]));
      pos = grid.map((p) => [9 + 82 * (cx ? p[0] / cx : .5), 14 + 72 * (cy ? p[1] / cy : .5)]);
    } else if (has(xy)) {   // si no, proyección MDS
      const xs = xy.map((p) => p[0]), ys = xy.map((p) => p[1]);
      const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
      pos = xy.map((p) => [9 + 82 * (p[0] - x0) / ((x1 - x0) || 1), 14 + 72 * (p[1] - y0) / ((y1 - y0) || 1)]);
    } else { hide("scene-airport"); return; }
    const term = $("terminal");
    const rowsN = has(grid) ? Math.max(...grid.map((p) => p[1])) + 1 : 4;
    term.style.height = `min(${170 * rowsN + 130}px, 72vh)`;
    term.style.minHeight = (110 * rowsN + 60) + "px";
    const fmax = Math.max(...F.flat()) || 1;
    const pairs = []; for (let i = 0; i < n; i++) for (let k = i + 1; k < n; k++) if (F[i][k] > 0) pairs.push([i, k]);
    const evs = (hq && has(hq.events)) ? hq.events : null;
    const final = hq ? hq.final_perm : best.perm;
    let cmax = 1; [evs ? evs[0].perm : final, final].forEach((pm) => pairs.forEach(([i, k]) => { cmax = Math.max(cmax, F[i][k] * D[pm[i]][pm[k]]); }));
    let svg = '<svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">';
    pairs.forEach(([i, k]) => { svg += `<path id="fe${i}_${k}" fill="none" stroke="#FFC629" vector-effect="non-scaling-stroke" stroke-linecap="round" stroke-width="${(1 + 7 * F[i][k] / fmax).toFixed(1)}"></path>`; });
    for (let i = 0; i < n; i++) svg += `<path id="mv${i}" fill="none" stroke="#4FE3E0" stroke-width="3" stroke-dasharray="6 5" vector-effect="non-scaling-stroke"></path>`;
    term.innerHTML = svg + "</svg>" + pos.map((p, j) => `<div class="gpost" style="left:${p[0]}%;top:${p[1]}%"><div class="gsign">${P(j)}</div><div class="gchip" id="gc${j}"></div></div>`).join("")
      + '<div class="legend tlegend"><span><i class="ln" style="background:var(--signal)"></i>Flujo entre vuelos</span><span><i class="dash"></i>Cambio propuesto por QAOA</span></div>';
    const curve = (a, b) => {
      const [x1, y1] = pos[a], [x2, y2] = pos[b];
      const mx = (x1 + x2) / 2, my = (y1 + y2) / 2;
      const bend = Math.abs(y1 - y2) < 1 ? 9 : 0;
      return `M${x1.toFixed(2)} ${y1.toFixed(2)} Q ${(mx + (y2 - y1) * .12).toFixed(2)} ${(my + bend).toFixed(2)} ${x2.toFixed(2)} ${y2.toFixed(2)}`;
    };
    const cost = (pm) => { let c = 0; pairs.forEach(([i, k]) => { c += F[i][k] * D[pm[i]][pm[k]]; }); return c; };
    $("board").innerHTML = Array.from({ length: n }, (_, i) => `<div class="board-row"><div class="flaps" id="bf${i}"></div><div class="flaps" id="bg${i}" style="color:var(--signal)"></div><div class="st" id="bs${i}"></div></div>`).join("");
    const startCost = evs ? evs[0].cost : (hq ? hq.start_cost : null);
    put("optLbl", num(REF) ? `ÓPTIMO ${f(REF)}` : null);
    const pills = ['<span class="pill">9 QUBITS POR SUBPROBLEMA</span>'];
    if (hq && num(hq.sub_success_rate) && num(hq.shots)) pills.push(`<span class="pill">QAOA ÓPTIMO EN ${f(100 * hq.sub_success_rate)}% DE SUBPROBLEMAS (${hq.shots} SHOTS)</span>`);
    if (hq && num(hq.qaoa_p_optimal_mean) && num(hq.random_p_optimal_mean)) pills.push(`<span class="pill">P(ÓPTIMO) POR PIEZA ${f(hq.qaoa_p_optimal_mean, 3)} VS AZAR ${f(hq.random_p_optimal_mean, 3)}</span>`);
    const h8 = H.qgate_lns_qaoa_s8, r8 = H.qgate_lns_random_s8;
    const Bv = ((R.extra || {}).baselines_qaoa_s8) || null;
    if (false) pills.push(`<span class="pill n">CON 8 SHOTS: QAOA ${f(100 * h8.sub_success_rate)}% · AZAR (27 ESTADOS) ${f(100 * r8.sub_success_rate)}%`
      + (Bv ? ` · AZAR (6 PERMUTACIONES VÁLIDAS) ${f(100 * Bv.hit_k8_random_valid_6)}% · ENUMERACIÓN 100%` : "") + "</span>");
    $("hPills").innerHTML = pills.join("");
    let fact = 1; for (let i = 2; i <= n; i++) fact *= i;
    $("strip").textContent = `${n} VUELOS · ${n} PUERTAS · ${n}! = ${sp(fact)} ASIGNACIONES · SUBPROBLEMAS DE 3 VUELOS = 9 QUBITS · CADA PAR SE CUENTA UNA VEZ · DATOS QAP10 (MIPLIB) · UNIDADES SUPUESTAS`;
    const S0 = R.hybrid_seeds;
    put("replayNote", hq ? `Repetición grabada, semilla ${meta.seed}; no es el caso típico (ver 05: con solver exacto, ${S0 ? S0.hits_ref + " de " + S0.final_costs.length + " semillas llegan a " + f(REF) : "robustez"})` : null);
    let ei = 0, prev = null;
    function draw() {
      const ev = evs ? evs[ei] : { perm: final, cost: hq ? hq.final_cost : best.cost, iter: hq ? hq.iters : null, type: "end" };
      const pm = ev.perm, moved = new Set(ev.type === "move" && ev.elems ? ev.elems : []);
      pairs.forEach(([i, k]) => { const e = $(`fe${i}_${k}`); e.setAttribute("d", curve(pm[i], pm[k])); e.setAttribute("stroke-opacity", (0.12 + 0.8 * F[i][k] * D[pm[i]][pm[k]] / cmax).toFixed(3)); });
      for (let i = 0; i < n; i++) {
        const e = $(`mv${i}`);
        if (moved.has(i) && prev && prev[i] !== pm[i]) e.setAttribute("d", curve(prev[i], pm[i])); else e.removeAttribute("d");
      }
      const inv = []; pm.forEach((g, i) => { inv[g] = i; });
      inv.forEach((i, g) => { const c = $(`gc${g}`); c.textContent = V(i); c.classList.toggle("moved", moved.has(i) && !!prev && prev[i] !== pm[i]); });
      for (let i = 0; i < n; i++) {
        flapSet($(`bf${i}`), V(i)); flapSet($(`bg${i}`), P(pm[i]));
        const ch = !!prev && prev[i] !== pm[i];
        const mv = ch && moved.has(i);
        $(`bs${i}`).textContent = mv ? "MOVIDO" : (ch && ev.type === "kick" ? "PERTURBADO" : "EN POSICIÓN");
        $(`bs${i}`).classList.toggle("mv", mv);
      }
      const c = num(ev.cost) ? ev.cost : cost(pm);
      flapSet($("costFlaps"), String(Math.round(c)).padStart(3, "0"));
      const g = gap(c); put("gapLbl", g === null ? null : `GAP ${g.toFixed(1)}%`);
      if (num(startCost) && num(REF) && startCost > REF) $("costBar").style.width = (100 * Math.max(0, Math.min(1, (startCost - c) / (startCost - REF)))) + "%";
      const tot = hq ? hq.iters : null;
      put("vuelta", num(ev.iter) && num(tot) ? `VUELTA ${String(ev.iter).padStart(3, "0")} / ${tot}` : null);
      put("hIterLbl", num(ev.iter) && num(tot) ? `ITERACIÓN ${ev.iter} / ${tot}` : null);
      setTrack("hTrack", evs ? ei / Math.max(evs.length - 1, 1) : 1);
      prev = pm.slice();
    }
    draw();
    if (evs) {
      players.airport = {
        delay: 650,
        step() { if (ei >= evs.length - 1) return false; ei++; draw(); return true; },
        atEnd() { return ei >= evs.length - 1; },
        reset() { ei = 0; prev = null; draw(); },
        seek(x) { ei = Math.round(x * (evs.length - 1)); prev = null; draw(); },
      };
      bindTrack("hTrack", players.airport);
    } else hide("hProg");
  })();

  /* ---------------- 03 RESULTADO: tarjetas de embarque y comparación ---------------- */
  (function resultScene() {
    const bar = '<div class="barcode">' + [3, 1, 2, 1, 1, 3, 1, 2, 2, 1, 3, 1, 1, 2, 1, 3].map((w) => `<i style="width:${w}px"></i>`).join("") + "</div>";
    const field = (k, v) => v === null || v === undefined ? "" : `<div><div class="fk">${esc(k)}</div><div class="fv">${esc(v)}</div></div>`;
    const plane = '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#0B0B0C" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M17.8 19.2 16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.2c.4-.3.6-.7.5-1.2z"></path></svg>';
    const pass = (o) => `<article class="pass"><div class="body"><div style="display:flex;justify-content:space-between;align-items:center;gap:8px">
      <div class="k">BOARDING PASS · ${esc(o.kicker)}</div><div class="tag" style="background:${o.tagBg}">${esc(o.tag)}</div></div>
      <div class="route"><span>${esc(o.from)}</span>${plane}<span>${esc(o.to)}</span></div>
      <div class="fields">${o.fields.map(([k, v]) => field(k, v)).join("")}</div></div>
      <div class="cut"></div><div class="stub"><div style="display:flex;flex-direction:column;align-items:center;gap:2px">${o.stubV ? `<div class="fk">${esc(o.stubK)}</div><div class="sv">${esc(o.stubV)}</div>` : ""}</div>${bar}</div>
      <div class="notch" style="top:-11px"></div><div class="notch" style="bottom:-11px"></div></article>`;
    const out = [];
    const vck = (n) => valid[n] && num(valid[n].optimum) ? `${f(valid[n].optimum)} ${valid[n].ok ? "✓" : "✗"}` : null;
    const mr = data.mps_report || {};
    if (has(R.validation)) out.push(pass({ kicker: "DATOS", tag: "VALIDADO", tagBg: "#FFC629", from: "MPS", to: "F·D", stubK: "CONTROL", stubV: f(REF),
      fields: [["N = 3", vck(3)], ["N = 4", vck(4)], [`N = ${N}`, vck(N)], ["VARIABLES", sp(mr.n_cols)]] }));
    const q4 = Q["N4-xy-p1"];
    if (q4) out.push(pass({ kicker: "QAOA · N = 4", tag: "QISKIT", tagBg: "#4FE3E0", from: "AZAR", to: "QAOA", stubK: "QUBITS", stubV: num(q4.qubits) ? String(q4.qubits) : null,
      fields: [["P(VÁLIDA)", pct(q4.p_feasible)], ["AL AZAR", pct(q4.random_feasible_baseline)], ["P(ÓPTIMO)", pct(q4.p_optimal)], ["CX", num(q4.cx_count) ? String(q4.cx_count) : null]] }));
    const hq = H.qgate_lns_qaoa;
    if (hq) out.push(pass({ kicker: `HÍBRIDO · N = ${N}`, tag: "QGATE", tagBg: "#FFC629", from: "AZAR", to: "QGATE", stubK: "QUBITS", stubV: String(hq.qubits_per_subproblem || 9),
      fields: (() => { const S = R.hybrid_seeds; return [[`SEMILLA ${meta.seed} · COSTO`, f(hq.final_cost)],
               [S ? `${S.final_costs.length} SEMILLAS (SOLVER EXACTO) · LLEGAN A ${f(REF)}` : "SEMILLAS", S ? String(S.hits_ref) : null],
               ["MEDIA · MEJOR · PEOR", S ? `${f(S.mean, 1)} · ${f(S.best)} · ${f(S.worst)}` : null],
               ["GAP MEDIO", S && num(S.mean_gap_pct) ? S.mean_gap_pct.toFixed(1) + "%" : null]]; })() }));
    $("passes").innerHTML = out.join("");
    const rows = [];
    const row = (m, n, q, c, g, t, w, color, k) => rows.push(`<tr><td style="color:${color};font-weight:600">${AP(k)}${esc(m)}</td><td>${n}</td><td>${esc(q)}</td><td>${c ?? "-"}</td><td>${g === null ? "-" : g.toFixed(1) + "%"}</td><td>${t ?? "-"}</td><td style="color:var(--mute)">${esc(w)}</td></tr>`);
    const tm = (t, d = 1) => num(t) ? f(t, d) + " s" : null;
    const bf = C.brute_force, sa = C.simulated_annealing;
    if (bf) row("Fuerza bruta (exacto)", N, "0", f(bf.cost), gap(bf.cost), tm(bf.time_s), "CPU", "var(--paper)", "classic");
    if (sa) row("Simulated annealing", N, "0", f(sa.cost), gap(sa.cost), tm(sa.time_s), "CPU", "var(--paper)", "classic");
    ["N4-x-p1", "N4-xy-p1"].forEach((id) => { const q = Q[id]; if (q) row(`QAOA mixer ${q.mixer.toUpperCase()}`, q.N, String(q.qubits), f(q.best_feasible_cost), gap(q.best_feasible_cost, q.optimum), tm(q.time_s), "Qiskit Aer", "var(--qubit)", "quantum"); });
    const hw = R.hardware;
    if (hw && has(hw.experiments)) hw.experiments.forEach((e) => row(`QAOA mixer ${String(e.mixer).toUpperCase()} · hardware`, e.N, String(e.qubits),
      e.best_feasible_cost === null || e.best_feasible_cost === undefined ? null : f(e.best_feasible_cost), num(e.best_feasible_cost) ? gap(e.best_feasible_cost, e.optimum) : null,
      num(hw.usage_quantum_seconds) ? f(hw.usage_quantum_seconds) + " s QPU (job)" : null, "IBM Quantum · " + hw.backend, "var(--qubit)", "quantum"));
    if (hq) row(`QGate híbrido · semilla ${meta.seed}`, N, "9 / subproblema", f(hq.final_cost), gap(hq.final_cost), tm(hq.time_s, 0), "Qiskit Aer + CPU", "var(--signal)", "hybrid");
    const S12 = R.hybrid_seeds;
    if (false) row(`Mismo marco · ${S12.final_costs.length} semillas (solver exacto): ${S12.hits_ref} llegan a ${f(REF)}, media ${f(S12.mean, 1)}, mejor ${f(S12.best)}, peor ${f(S12.worst)}`, N, "0",
      f(S12.mean, 1) + " (media)", S12.mean_gap_pct, null, "CPU", "var(--paper)", "classic");
    const h8 = H.qgate_lns_qaoa_s8, r8 = H.qgate_lns_random_s8;
    if (false) row("QGate híbrido · 8 shots", N, "9 / subproblema", f(h8.final_cost), gap(h8.final_cost), tm(h8.time_s, 0), "Qiskit Aer + CPU", "var(--signal)", "hybrid");
    if (false) row("Control azar (27 estados con una puerta por vuelo) · 8 shots", N, "0", f(r8.final_cost), gap(r8.final_cost), tm(r8.time_s), "CPU", "var(--mute)", "classic");
    $("resRows").innerHTML = rows.join("");
  })();

  /* ---------------- detalle ---------------- */
  if (has(R.validation)) $("valRows").innerHTML = R.validation.map((v) => `<tr><td>${AP("classic")}${v.n}</td><td class="r">${f(v.optimum)}</td><td class="r">${f(v.expected) ?? "-"}</td>
    <td style="color:${v.ok ? "var(--signal)" : "var(--invalid)"}">${v.ok ? "✓" : "✗"}</td><td class="r">${f(v.time_s, v.time_s < 1 ? 3 : 1)} s</td></tr>`).join("");
  else hide("d-valid");
  (function facts() {
    const mr = data.mps_report || {}, out = [];
    if (num(mr.n_cols)) out.push(`<span>variables <b>${sp(mr.n_cols)}</b> = ${mr.n_x} x + ${sp(mr.n_y)} y</span>`);
    if (num(mr.n_rows)) out.push(`<span>restricciones <b>${sp(mr.n_rows)}</b></span>`);
    if (num(mr.y_mapped)) out.push(`<span>y mapeadas <b>${sp(mr.y_mapped)} / ${sp(mr.y_expected)}</b></span>`);
    if (num(data.factorization_residual)) out.push(`<span>residuo SVD <b>${data.factorization_residual}</b></span>`);
    if (data.index_strategy) out.push(`<span>índices <b>${esc(data.index_strategy)}</b></span>`);
    if (has(data.gate_grid)) out.push("<span>D = distancia Manhattan en una grilla de puertas</span>");
    $("facts").innerHTML = out.join("");
  })();
  function heat(id, M, rgb) {
    if (!has(M)) { hide($(id).parentElement); return; }
    const mx = Math.max(...M.flat().map(Math.abs)) || 1;
    $(id).style.gridTemplateColumns = `repeat(${M.length}, minmax(0, 1fr))`;
    $(id).innerHTML = M.map((r, i) => r.map((x, j) => `<div title="${i + 1}, ${j + 1}: ${Math.abs(x)}" style="background:${x ? `rgba(${rgb},${(0.15 + 0.85 * Math.abs(x) / mx).toFixed(3)})` : "#141518"}"></div>`).join("")).join("");
  }
  heat("heatF", data.F, "255,198,41"); heat("heatD", data.D, "79,227,224");

  (function ablation() {
    const L = (R.hybrid || []).filter((h) => h.method && h.method.startsWith("qgate_lns"));
    if (!has(L)) { hide("d-ablation"); return; }
    const lab = (h) => h.solver === "random" ? `Azar (27 estados con una puerta por vuelo) · ${h.shots} shots` : h.solver === "exact" ? "Enumeración exacta (6 opciones)" : h.label;
    const B8 = ((R.extra || {}).baselines_qaoa_s8) || null, B512 = ((R.extra || {}).baselines_qaoa) || null;
    const extraRows = [];
    [[B512, 512], [B8, 8]].forEach(([B, k]) => { if (B && num(B[`hit_k${k}_random_valid_6`])) extraRows.push(`<tr><td style="font-weight:600">${AP("classic")}Azar (6 permutaciones válidas) · ${k} muestras <span class="kick" style="letter-spacing:.04em">calculado sobre las ${B.pieces} piezas de la corrida QAOA de ${k} shots</span></td><td class="r">${k}</td><td class="r">-</td><td class="r">-</td><td class="r">${f(100 * B[`hit_k${k}_random_valid_6`])}%</td><td class="r">${B.p_opt_random_valid_6.toFixed(3)}</td><td class="r">${B.p_opt_random_states_27.toFixed(3)}</td><td class="r">-</td></tr>`); });
    $("ablRead").textContent = "QAOA concentra probabilidad respecto a su espacio de partida; en piezas de 3 vuelos aún no supera a muestrear permutaciones válidas ni a enumerar las 6 opciones.";
    $("ablRows").innerHTML = L.map((h) => {
      const pm = h.solver === "qaoa" ? h.qaoa_p_optimal_mean : h.solver === "random" ? h.random_p_optimal_mean : 1;
      return `<tr><td style="color:${h.solver === "qaoa" ? "var(--signal)" : "var(--paper)"};font-weight:600">${AP(h.solver === "qaoa" ? "hybrid" : "classic")}${esc(lab(h))}</td><td class="r">${h.shots ?? "-"}</td>
      <td class="r">${f(h.final_cost)}</td><td class="r">${num(h.gap_pct) ? h.gap_pct.toFixed(1) + "%" : "-"}</td><td class="r">${num(h.sub_success_rate) ? f(100 * h.sub_success_rate) + "%" : "-"}</td>
      <td class="r">${num(pm) ? pm.toFixed(3) : "-"}</td><td class="r">${num(h.random_p_optimal_mean) ? h.random_p_optimal_mean.toFixed(3) : "-"}</td><td class="r">${f(h.time_s, 1)} s</td></tr>`;
    }).join("") + extraRows.join("");
    const S = R.hybrid_seeds;
    if (S && has(S.final_costs)) $("seedChips").innerHTML = `<span>robustez · ${S.final_costs.length} semillas (exacto): media <b>${f(S.mean, 1)}</b></span><span>llega a ${f(REF)} en <b>${S.hits_ref}/${S.final_costs.length}</b></span>`
      + S.final_costs.map((c, i) => `<span style="${Math.abs(c - REF) < 1e-6 ? "border-color:var(--signal);color:var(--signal)" : ""}">s${S.seeds[i]} · ${f(c)}</span>`).join("");
  })();

  (function hardware() {
    const hw = R.hardware;
    if (!hw || !has(hw.experiments)) return;
    $("d-hw").classList.remove("hidden");
    const ex = hw.experiments, exy = ex.find((e) => e.mixer === "xy"), exx = ex.find((e) => e.mixer === "x");
    let lede = `HARDWARE ${hw.backend}: un solo job, un solo backend (job ${hw.job_id}${num(hw.usage_quantum_seconds) ? `, ${f(hw.usage_quantum_seconds)} s de QPU` : ""}), N=3, con los ángulos ya optimizados en el simulador.`;
    if (exy && exx && num(exy.sim_noise_feasible_fraction) && num(exx.sim_noise_feasible_fraction))
      lede += ` La simulación con 1% de ruido coincidió con el mixer XY (${pct(exy.sim_noise_feasible_fraction)} vs ${pct(exy.feasible_fraction)}) y sobreestimó el mixer X (${pct(exx.sim_noise_feasible_fraction)} vs ${pct(exx.feasible_fraction)}).`;
    if (exy && exx) lede += ` XY queda casi en su línea base de P(válida) (${pct(exy.feasible_fraction)} vs ${pct(exy.random_feasible_baseline)}); X queda ${(exx.feasible_fraction / exx.random_feasible_baseline).toFixed(2)} veces sobre la suya (${pct(exx.feasible_fraction)} vs ${pct(exx.random_feasible_baseline)}).`;
    $("hwLede").textContent = lede;
    const hro = ((R.extra || {}).hardware_random_p_optimal || {}).rows || [];
    $("hwRows").innerHTML = hw.experiments.map((e) => `<tr><td style="color:var(--qubit);font-weight:600">${AP("quantum")}${esc(e.id)}</td><td class="r">${e.qubits}</td>
      <td class="r" style="color:var(--qubit)">${pct(e.feasible_fraction) ?? "-"}</td><td class="r">${pct(e.sim_ideal_p_feasible) ?? "-"}</td><td class="r">${pct(e.sim_noise_feasible_fraction) ?? "-"}</td>
      <td class="r">${pct(e.random_feasible_baseline) ?? "-"}</td><td class="r">${pct(e.p_optimal) ?? "-"}</td>
      <td class="r">${(() => { const r = hro.find((x) => x.id === e.id); return r ? `${pct(r.random_p_optimal, 2)} (${r.ratio_hw_vs_random.toFixed(2)}×)` : "-"; })()}</td><td class="r">${f(e.best_feasible_cost) ?? "-"}${num(e.optimum) ? " (ópt " + f(e.optimum) + ")" : ""}</td>
      <td class="r">${e.depth ?? "-"}</td><td class="r">${e.two_qubit_gates ?? "-"}</td></tr>`).join("");
  })();

  (function finalStage() {
    const Fn = R.final;
    if (!Fn || !has(Fn.summary)) { hide("tabFinal"); return; }
    const m = Fn.meta || {};
    const NAME = { sa: "SA", ls: "2-swap con reinicios", exact: "bloque: enumeración", random_valid: "bloque: azar 6 válidas", exact_rand: "bloque: enumeración + desempate", qaoa: "bloque: QAOA" };
    const kindOf = (sv) => sv === "qaoa" ? "hybrid" : "classic";
    const insts = Fn.instances || [];
    const synth = insts.filter((i) => i.origen === "sintética").map((i) => i.instance);
    const V0 = Fn.verdict || {};
    const tieSet = (v) => new Set((v.ties_at_best_median || [v.best_median]).map((t) => t.split("/")[0]));
    const anyDist = synth.some((i) => V0[i] && V0[i].distinguible);
    const sets = synth.filter((i) => V0[i]).map((i) => tieSet(V0[i]));
    const wa = sets.length ? [...sets[0]].filter((x) => sets.every((st) => st.has(x))) : [];
    const union = new Set(sets.flatMap((st) => [...st]));
    const blockRed = synth.every((i) => { const a = (Fn.attribution || {})[i]; return a && a.cost_reduction_at_best_by_origin.block === 0; });
    let tail;
    if (!sets.length) tail = "";
    else if (anyDist) tail = "ver en la tabla qué método es mejor en cada N y si es distinguible.";
    else {
      tail = "ninguna diferencia es distinguible entre semillas; ";
      if (wa.includes("ls") && wa.includes("qaoa")) tail += "en N>10 la mejor mediana la comparten el 2-swap sin bloques y el híbrido con QAOA" + (wa.length > 2 ? ", junto con los otros solvers de bloque" : "");
      else if (wa.length) tail += "en N>10 la mejor mediana la comparten: " + wa.map((b) => NAME[b] || b).join(", ");
      else tail += "la mejor mediana cambia de método según N";
      tail += union.has("sa") ? "." : "; SA no la tiene.";
    }
    $("finSentence").textContent = "La memoria cuántica no crece con N; la calidad todavía no escala; " + tail +
      (blockRed ? " Los bloques QAOA no aportaron reducción de costo." : "");
    $("finMeta").textContent = "SIMULADOR (Qiskit Aer) y CPU · " + (m.seeds || []).length + " semillas · B=" + m.blocks_B +
      " iteraciones externas para todos los solvers del modo dos fases · " + m.shots + " shots por bloque para QAOA y para el azar · SA " +
      m.sa_iters + "×" + m.sa_restarts + " · " + (m.nota_tiempos || "") + " · N>10 sintéticas";
    const A = Fn.attribution || {};
    const pc = (x, d = 1) => num(x) ? (100 * x).toFixed(d) + "%" : "-";
    $("finAttr").innerHTML = insts.filter((i) => A[i.instance]).map((i) => {
      const a = A[i.instance], mv = a.moves_at_best_by_origin, rd = a.cost_reduction_at_best_by_origin;
      return "<tr><td>" + esc(i.instance) + " <span class='kick' style='letter-spacing:.04em'>" + esc(i.origen) + "</span></td><td class='r'>" + pc(a.variables_quantum_frac, 2) +
        "</td><td class='r'>" + mv.swap + " · " + mv.block + " · " + mv.kick + "</td><td class='r'>" + f(rd.swap) + " · " + f(rd.block) + " · " + f(rd.kick) +
        "</td><td class='r'>" + pc(a.frac_wall_in_qaoa_mean) + " · " + pc(a.frac_wall_in_aer_mean) + "</td></tr>";
    }).join("");
    $("finDefs").innerHTML = [
      "(i) fracción de las N² variables x que entra en el circuito: los 9 qubits de un bloque.",
      "(ii) movimientos aceptados hasta llegar a la mejor asignación, sumados en todas las semillas y los 2 selectores, por origen.",
      "(iii) reducción de costo por origen, desde la asignación inicial hasta la mejor; las perturbaciones suben el costo (exploración), por eso restan. Depende del orden de las fases: el 2-swap corre primero y se lleva las mejoras fáciles.",
      "(iv) fracción del tiempo de pared dentro de la subrutina QAOA (circuito Qiskit + simulación Aer + COBYLA clásico que la orquesta) y solo en la simulación Aer.",
      "Fuente: results/final.json · python -m qgate.final"].map((x) => "<li>" + esc(x) + "</li>").join("");
    $("finRates").innerHTML = insts.filter((i) => A[i.instance]).map((i) => {
      const r = A[i.instance].block_improve_rate_from_local_opt;
      const c = (k) => r[k] && num(r[k].rate) ? pc(r[k].rate) + " (" + r[k].blocks_improved + "/" + r[k].blocks_tried + ")" : "-";
      return "<tr><td>" + esc(i.instance) + "</td><td class='r'>" + c("exact") + "</td><td class='r'>" + c("random_valid") + "</td><td class='r'>" + c("exact_rand") + "</td><td class='r'>" + c("qaoa") + "</td></tr>";
    }).join("");
    const V = Fn.verdict || {};
    $("finRows").innerHTML = Fn.summary.map((sm) => {
      const v = V[sm.instance] || {}, key = sm.solver + "/" + (sm.select == null ? "None" : sm.select);
      const ties = v.ties_at_best_median || [v.best_median];
      const top = ties.includes(key);
      const mark = top ? (v.distinguible ? " · mejor (distinguible)" : ties.length > 1 ? " · mejor mediana (empate), no distinguible" : " · mejor mediana, no distinguible") : "";
      return "<tr><td>" + esc(sm.instance) + "</td><td>" + AP(kindOf(sm.solver)) + esc(NAME[sm.solver] || sm.solver) +
        "<span class='kick' style='letter-spacing:.04em'>" + esc(mark) + "</span></td><td>" + (sm.select ? esc(sm.select) : "-") +
        "</td><td class='r'" + (top && v.distinguible ? " style='color:var(--signal)'" : "") + ">" + f(sm.cost_median) + " [" + f(sm.cost_min) + ", " + f(sm.cost_max) + "]</td>" +
        "<td class='r'>" + f(sm.gap_vs_gl_median_pct, 1) + "%</td><td class='r'>" + f(sm.gap_vs_best_found_median_pct, 1) + "% [" + f(sm.gap_vs_best_found_min_pct, 1) + ", " + f(sm.gap_vs_best_found_max_pct, 1) + "]</td>" +
        "<td class='r'>" + f(sm.time_median_s, 1) + " s</td><td class='r'>" + f(sm.peak_mem_median_mb, 2) + " MB</td><td class='r'>" + pc(sm.feasible_rate, 0) + "</td></tr>";
    }).join("");
    const ar = Fn.angle_reuse;
    put("finReuse", ar ? "Ángulos reutilizados (" + ar.instance + ", " + ar.cold.blocks + " bloques, " + ar.shots + " shots): evaluaciones por bloque " + f(ar.cold.evals_mean, 1) +
      " en frío y " + f(ar.warm.evals_mean, 1) + " reutilizando; P(óptimo) del bloque " + ar.cold.p_optimal_mean.toFixed(3) + " vs " + ar.warm.p_optimal_mean.toFixed(3) +
      "; tiempo " + ar.cold.time_mean_s.toFixed(2) + " s vs " + ar.warm.time_mean_s.toFixed(2) + " s." : null);
  })();

  (function traceability() {
    const X = R.extra || {}, sc = X.scale_check, mr = data.mps_report || {};
    const st = [];
    if (sc) {
      st.push(`Las ${sc.assignment_rows} restricciones con lado derecho 1 y coeficientes 1 son las de asignación: sus variables son las ${sc.n_x} x.`);
      st.push(`Esas ${sc.assignment_rows} filas se parten en dos familias de ${sc.assignment_rows / 2}: vuelos y puertas; cada x está una vez en cada familia, eso da su índice (i, j).`);
      st.push(`Cada una de las ${sp(sc.n_y)} variables y aparece en filas de enlace junto a exactamente dos x (x_ij, x_kl): su coeficiente objetivo es F_ik · D_jl.`);
      st.push(`Con eso se arma el tensor T y se factoriza en F y D por SVD de rango 1: residuo ${sc.factorization_residual}.`);
      st.push(`El orden de índices se elige entre las candidatas (${sc.candidates.join(", ")}) con la que reproduce los óptimos de control ${(R.validation || []).map((v) => f(v.optimum)).join(" · ")}.`);
      st.push(`Control de escala, calculado en código: la asignación óptima cuesta ${f(sc.cost_pair_once)} contando cada par una vez (convención del archivo) y ${f(sc.cost_pair_twice)} contando cada par dos veces.`);
      $("recSteps").innerHTML = st.map((x) => `<li>${esc(x)}</li>`).join("");
    } else hide("recBox");
    const hw = R.hardware, B8 = X.baselines_qaoa_s8;
    const why = ["Las piezas de 3 vuelos tienen solo 6 opciones válidas: se pueden enumerar. QAOA se mide ahí para ver cuánto concentra probabilidad con un circuito que cabe en hardware, no porque se espere que gane."];
    if (B8) why.push(`SIMULADOR, N=10, piezas de 3 vuelos, 8 muestras: QAOA resuelve ${f(100 * (H.qgate_lns_qaoa_s8 || {}).sub_success_rate)}% de las piezas; el azar sobre las 6 permutaciones válidas, ${f(100 * B8.hit_k8_random_valid_6)}%; la enumeración, 100%.`);
    const Fw = R.final;
    if (Fw) {
      const ins = Fw.instances.map((i) => i.instance), Ns = Fw.instances.map((i) => i.N);
      const dist = ins.some((i) => (Fw.verdict[i] || {}).distinguible);
      const b0 = ins.every((i) => { const a = (Fw.attribution || {})[i]; return a && a.cost_reduction_at_best_by_origin.block === 0; });
      why.push(`La memoria cuántica no crece con N (9 qubits por pieza); la calidad todavía no escala: en la etapa 3 (${Fw.meta.seeds.length} semillas, N=${Math.min(...Ns)} a ${Math.max(...Ns)}) ` +
        (dist ? "hay diferencias distinguibles entre métodos" : "ninguna diferencia entre métodos es distinguible") + (b0 ? " y los bloques QAOA no aportaron reducción de costo" : "") + " (ver 04).");
    } else why.push(`La memoria cuántica no crece con N (9 qubits por pieza); la calidad todavía no escala: en N=16 el híbrido queda más lejos de la cota que simulated annealing (ver 07).`);
    if (hw) { const e = hw.experiments.find((x) => x.mixer === "xy"); if (e) why.push(`HARDWARE ${hw.backend}: el ruido real borra casi toda la ventaja del mixer XY (${pct(e.feasible_fraction)} válidas vs ${pct(e.random_feasible_baseline)} de su azar). Es un solo job con N=3.`); }
    window.__why = why; hide("whyBox");            /* se fusiona en la sección 08 (límites) */
    const x4 = Q["N4-xy-p1"];
    $("resNote").textContent = "Filas de QAOA: valores crudos de las muestras, sin reparación clásica. 'Mejor costo válido' es el costo C de una asignación válida, no la energía penalizada del QUBO"
      + (x4 ? ` (N=4: λ = ${f(x4.lam)} = λ0, fracción factible ${pct(x4.p_feasible)} ideal y ${pct(x4.feasible_fraction_shots)} en ${x4.shots} shots)` : "")
      + ". El híbrido produce asignaciones válidas por construcción.";
  })();

  /* gráfico de líneas SVG (sin librerías); tooltip con <title> en cada punto */
  function lineChart(el, o) {
    const W = 640, Hh = 300, l = 54, r = 16, t = 12, b = 34, iw = W - l - r, ih = Hh - t - b;
    const xs = o.x, ylog = !!o.ylog;
    const vals = o.series.flatMap((s) => s.y.filter(num));
    if (!vals.length) { hide(el.parentElement); return; }
    let y0, y1;
    if (ylog) { y0 = Math.pow(10, Math.floor(Math.log10(Math.max(Math.min(...vals), 1e-6)))); y1 = Math.pow(10, Math.ceil(Math.log10(Math.max(...vals)))); if (y1 <= y0) y1 = y0 * 10; }
    else { const lo = Math.min(...vals), hi = Math.max(...vals), padv = (hi - lo) * .08 || 1; y0 = o.ymin ?? lo - padv; y1 = o.ymax ?? hi + padv; }
    const ty = (v) => t + ih - ih * (ylog ? (Math.log10(v) - Math.log10(y0)) / (Math.log10(y1) - Math.log10(y0)) : (v - y0) / (y1 - y0));
    const tx = (i) => l + (xs.length > 1 ? iw * i / (xs.length - 1) : iw / 2);
    let s = `<svg viewBox="0 0 ${W} ${Hh}" role="img" aria-label="${esc(o.label || "")}">`;
    const ticks = ylog ? (() => { const a = []; for (let e = Math.round(Math.log10(y0)); e <= Math.round(Math.log10(y1)); e++) a.push(Math.pow(10, e)); return a; })()
                       : Array.from({ length: 5 }, (_, i) => y0 + (y1 - y0) * i / 4);
    ticks.forEach((v) => { s += `<line x1="${l}" x2="${W - r}" y1="${ty(v).toFixed(1)}" y2="${ty(v).toFixed(1)}" stroke="#2C2F35"/><text x="${l - 8}" y="${(ty(v) + 4).toFixed(1)}" text-anchor="end">${o.yfmt ? o.yfmt(v) : +v.toPrecision(3)}</text>`; });
    xs.forEach((x, i) => { s += `<text x="${tx(i).toFixed(1)}" y="${Hh - 10}" text-anchor="middle">${esc(x)}</text>`; });
    o.series.forEach((se) => {
      const pts = se.y.map((v, i) => num(v) ? [tx(i), ty(v), v, i] : null).filter(Boolean);
      s += `<polyline fill="none" stroke="${se.color}" stroke-width="2.5" ${se.dash ? 'stroke-dasharray="7 5"' : ""} points="${pts.map((p) => p[0].toFixed(1) + "," + p[1].toFixed(1)).join(" ")}"/>`;
      pts.forEach((p) => { s += `<circle cx="${p[0].toFixed(1)}" cy="${p[1].toFixed(1)}" r="5" fill="${se.color}" stroke="#141518" stroke-width="2"><title>${esc(se.name)} · ${esc(xs[p[3]])}: ${o.vfmt ? o.vfmt(p[2]) : p[2]}</title></circle>`; });
    });
    el.innerHTML = s + "</svg>";
  }
  (function lam() {
    const L = R.lambda_sweep || [];
    if (!has(L)) { hide("d-lambda"); return; }
    const facs = [...new Set(L.map((r) => r.lam_factor))].sort((a, b) => a - b);
    const ser = [];
    [["xy", "#4FE3E0"], ["x", "#FFC629"]].forEach(([m, c]) => {
      const rows = facs.map((fc) => L.find((r) => r.mixer === m && r.lam_factor === fc));
      if (!rows.some(Boolean)) return;
      ser.push({ name: `${m.toUpperCase()} · P(válida)`, color: c, y: rows.map((r) => r ? r.p_feasible : null) });
      ser.push({ name: `${m.toUpperCase()} · P(óptimo)`, color: c, dash: true, y: rows.map((r) => r ? r.p_optimal : null) });
    });
    $("lamLegend").innerHTML = '<span><i class="ln" style="background:#4FE3E0"></i>Mixer XY</span><span><i class="ln" style="background:#FFC629"></i>Mixer X</span><span>continua = P(válida) · punteada = P(óptimo)</span>';
    lineChart($("lamChart"), { label: "Barrido de lambda", x: facs.map((x) => "λ0×" + x), series: ser, ymin: 0, ymax: 1, yfmt: (v) => (100 * v).toFixed(0) + "%", vfmt: (v) => (100 * v).toFixed(1) + "%" });
  })();
  (function scale() {
    const S = R.scaling || [];
    if (!has(S)) { hide("d-scale"); return; }
    if (R.final) {                                  /* la etapa 3 reemplaza a esta corrida de 1 semilla */
      $("scTitle").textContent = "Escalamiento · día 1";
      const d1 = $("scDay1");
      d1.innerHTML = esc("Corrida del día 1: una semilla y el híbrido anterior. La medición vigente es la de la etapa 3: " + R.final.meta.seeds.length +
        " semillas, híbrido en dos fases y el mismo presupuesto para todos los métodos.") + ' <button class="goto" type="button" data-goto="final">Ver 04 ESCALA →</button>';
      d1.hidden = false;
    }
    const Ns = [...new Set(S.map((r) => r.N))].sort((a, b) => a - b);
    const lab = Ns.map((n) => { const r = S.find((x) => x.N === n); return "N=" + n + (r && r.instance !== meta.instance ? "*" : ""); });
    const M = [["simulated_annealing", "SA", "#9A9890"], ["qgate_lns_exact", "QGate exacto", "#FFC629"], ["qgate_lns_qaoa", "QGate QAOA", "#4FE3E0"]].filter(([m]) => S.some((r) => r.method === m));
    const ser = (key) => M.map(([m, name, c]) => ({ name, color: c, y: Ns.map((n) => { const r = S.find((x) => x.N === n && x.method === m); return r ? r[key] : null; }) }));
    const leg = M.map(([, name, c]) => `<span><i class="ln" style="background:${c}"></i>${name}</span>`).join("");
    $("scLeg").innerHTML = leg; $("scLeg2").innerHTML = leg;
    lineChart($("scGap"), { label: "Gap contra cota", x: lab, series: ser("gap_vs_bound_pct"), ymin: 0, yfmt: (v) => v.toFixed(0) + "%", vfmt: (v) => v.toFixed(1) + "%" });
    lineChart($("scTime"), { label: "Tiempo", x: lab, series: ser("time_s"), ylog: true, yfmt: (v) => v >= 1 ? String(v) : String(+v.toPrecision(1)), vfmt: (v) => v.toFixed(2) + " s" });
    const nm = { simulated_annealing: "SA", qgate_lns_exact: "QGate exacto", qgate_lns_qaoa: "QGate QAOA" };
    $("scRows").innerHTML = S.map((r) => `<tr><td>${r.N}</td><td>${esc(r.instance)}${r.instance !== meta.instance ? " *" : ""}</td><td style="color:${r.method.includes("qaoa") ? "var(--signal)" : "var(--paper)"}">${AP(r.method.includes("qaoa") ? "hybrid" : "classic")}${nm[r.method] || esc(r.method)}</td>
      <td class="r">${f(r.best_cost)}</td><td class="r">${f(r.lower_bound)}</td><td class="r">${f(r.gap_vs_bound_pct, 1)}%</td><td class="r">${f(r.time_s, 1)} s</td><td class="r">${f(r.peak_mem_mb, 2)} MB</td><td class="r">${r.qubits}</td></tr>`).join("");
    const Mm = meta.statevector_memory || [];
    const hb = (b) => { const u = ["B", "KiB", "MiB", "GiB", "TiB"]; let i = 0; while (b >= 1024 && i < u.length - 1) { b /= 1024; i++; } return (b % 1 ? b.toFixed(1) : b) + " " + u[i]; };
    if (has(Mm)) $("memRows").innerHTML = Mm.map((m) => `<tr><td class="r">${m.N}</td><td class="r">${m.qubits}</td><td class="r" style="color:${m.N >= 10 ? "var(--invalid)" : "var(--paper)"}">${m.bytes > 1024 ** 5 ? m.bytes.toExponential(2) + " B" : hb(m.bytes)}</td></tr>`).join("");
    else hide("memBox");
  })();
  (function repro() {
    const v = meta.versions || {};
    const ch = Object.entries(v).filter(([, val]) => val).map(([k, val]) => `<span>${esc(k)} <b>${esc(val)}</b></span>`);
    if (num(meta.seed)) ch.push(`<span>semilla <b>${meta.seed}</b></span>`);
    if (meta.generated_at) ch.push(`<span>fecha <b>${esc(meta.generated_at)}</b></span>`);
    if (num(meta.total_time_s)) ch.push(`<span>corrida <b>${(meta.total_time_s / 60).toFixed(1)} min</b></span>`);
    ch.push(`<span>simulador <b>Qiskit Aer</b>${R.hardware ? " · hardware IBM reportado aparte" : " · sin hardware real"}</span>`);
    $("versions").innerHTML = ch.join("");
    const a = meta.args || {};
    $("cmd").textContent = a.mps ? `python -m qgate.bench --mps ${a.mps}${a.quick ? " --quick" : ""} --scale ${a.scale} --seed ${a.seed}` : "";
    const L = meta.limitations || [];
    const LL = L.concat(window.__why || []);
    if (has(LL)) $("limits").innerHTML = LL.map((l) => `<li>${esc(l)}</li>`).join(""); else hide($("limits").parentElement);
    $("gen").textContent = meta.generated_at ? "· generado " + meta.generated_at : "";
  })();

  [["d-valid", ["classic"]], ["d-ablation", ["hybrid", "classic"]], ["d-hw", ["quantum"]], ["d-lambda", ["quantum"]],
   ["d-scale", ["classic", "hybrid"]]].forEach(([id, ks]) => {
    const h = document.querySelector("#" + id + " .sec-head h3"); if (h) h.insertAdjacentHTML("afterend", ks.map(AP).join(""));
  });
  [["scene-qaoa", "quantum"], ["scene-airport", "hybrid"]].forEach(([id, k]) => {
    const h = document.querySelector("#" + id + " h2"); if (h) h.insertAdjacentHTML("beforebegin", `<div>${AP(k)}</div>`);
  });
  document.querySelectorAll(".goto").forEach((b) => b.addEventListener("click", () => { showScene(b.dataset.goto); window.scrollTo({ top: 0 }); }));
  syncPlay();
  showScene("pano");
})();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "results/results.json"
    dst = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(src), "report.html")
    print(build(src, dst))
