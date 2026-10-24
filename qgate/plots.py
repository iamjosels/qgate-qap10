"""Gráficos PNG para el PPT (fondo oscuro, poco texto)."""
from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

BG, FG, AMBER, CYAN, GREY, RED = "#0a101c", "#e6edf7", "#f5b700", "#22d3ee", "#64748b", "#f87171"


def _style(ax, title):
    ax.set_facecolor(BG)
    ax.figure.set_facecolor(BG)
    for s in ax.spines.values():
        s.set_color(GREY)
    ax.tick_params(colors=FG)
    ax.yaxis.label.set_color(FG)
    ax.xaxis.label.set_color(FG)
    ax.set_title(title, color=FG, fontsize=14, loc="left", fontweight="bold")
    ax.grid(color=GREY, alpha=0.2)


def make_all(R: dict, out: str) -> None:
    qs = [q for q in R.get("quantum", []) if q.get("noise") == "none"]
    if qs:
        fig, ax = plt.subplots(figsize=(9, 4.5))
        ids = [q["id"] for q in qs]
        x = range(len(ids))
        ax.bar([i - 0.2 for i in x], [q["random_feasible_baseline"] for q in qs], 0.4,
               color=GREY, label="Azar")
        ax.bar([i + 0.2 for i in x], [q["p_feasible"] for q in qs], 0.4, color=CYAN, label="QAOA")
        ax.set_yscale("log")
        ax.set_xticks(list(x), ids, rotation=20)
        ax.set_ylabel("P(asignación válida)")
        _style(ax, "QAOA vs azar")
        ax.legend(facecolor=BG, labelcolor=FG, edgecolor=GREY)
        fig.tight_layout()
        fig.savefig(os.path.join(out, "qaoa_vs_azar.png"), dpi=160)
        plt.close(fig)

    ls = R.get("lambda_sweep", [])
    if ls:
        fig, ax = plt.subplots(figsize=(7, 4.2))
        for mixer, col in (("x", AMBER), ("xy", CYAN)):
            rows = sorted([r for r in ls if r["mixer"] == mixer], key=lambda r: r["lam_factor"])
            if rows:
                ax.plot([r["lam_factor"] for r in rows], [r["p_feasible"] for r in rows], "o-",
                        color=col, label=f"P(válida) · {mixer}")
                ax.plot([r["lam_factor"] for r in rows], [r["p_optimal"] for r in rows], "s--",
                        color=col, alpha=0.6, label=f"P(óptimo) · {mixer}")
        ax.set_xscale("log", base=2)
        ax.set_xlabel("λ / λ0")
        _style(ax, "Barrido de λ (N=3)")
        ax.legend(facecolor=BG, labelcolor=FG, edgecolor=GREY, fontsize=8)
        fig.tight_layout()
        fig.savefig(os.path.join(out, "barrido_lambda.png"), dpi=160)
        plt.close(fig)

    # mismo presupuesto de iteraciones: QAOA (grueso) y control exacto (punteado encima)
    hy = [h for h in R.get("hybrid", []) if h.get("history") and h["method"].startswith("qgate_lns")]
    if hy:
        fig, ax = plt.subplots(figsize=(8, 4.2))
        style = {"qgate_lns_qaoa": dict(color=CYAN, lw=5, alpha=0.85, zorder=2),
                 "qgate_lns_exact": dict(color=AMBER, lw=2, ls="--", zorder=3),
                 "qgate_lns_random": dict(color=GREY, lw=1.5, ls=":", zorder=3),
                 "qgate_lns_qaoa_s8": dict(color="#7fd3e6", lw=2, zorder=2),
                 "qgate_lns_random_s8": dict(color=RED, lw=2, zorder=2)}
        for h in sorted(hy, key=lambda h: h["method"] != "qgate_lns_qaoa"):
            hist = h["history"]
            ax.step([p["iter"] for p in hist], [p["best"] for p in hist], where="post",
                    label=h.get("label", h["method"]), **style.get(h["method"], dict(color=FG)))
        ref = R.get("meta", {}).get("reference_optimum")
        if ref:
            ax.axhline(ref, color=RED, ls=":", label=f"Óptimo {ref:g} (solo referencia)")
        ax.set_xlabel("iteración")
        ax.set_ylabel("mejor costo")
        _style(ax, "Convergencia N completo")
        ax.legend(facecolor=BG, labelcolor=FG, edgecolor=GREY, fontsize=8)
        fig.tight_layout()
        fig.savefig(os.path.join(out, "hibrido_convergencia.png"), dpi=160)
        plt.close(fig)

    noisy = [q for q in R.get("quantum", []) if q.get("noise") != "none"]
    if noisy:
        fig, ax = plt.subplots(figsize=(7, 4.2))
        labels, ideal, shots, rnd = [], [], [], []
        for q in noisy:
            labels.append(f"mixer {q['mixer'].upper()}")
            ideal.append(q["p_feasible"])
            shots.append(q["feasible_fraction_shots"])
            rnd.append(q["random_feasible_baseline"])
        x = range(len(labels))
        ax.bar([i - 0.27 for i in x], ideal, 0.27, color=CYAN, label="sin ruido")
        ax.bar(list(x), shots, 0.27, color=AMBER, label=noisy[0]["noise"].replace("depolarizing", "con ruido"))
        ax.bar([i + 0.27 for i in x], rnd, 0.27, color=GREY, label="azar")
        ax.set_xticks(list(x), labels)
        ax.set_ylabel("fracción válida (N=3)")
        _style(ax, "Efecto del ruido")
        ax.legend(facecolor=BG, labelcolor=FG, edgecolor=GREY, fontsize=9)
        fig.tight_layout()
        fig.savefig(os.path.join(out, "ruido.png"), dpi=160)
        plt.close(fig)

    sc = R.get("scaling", [])
    if sc:
        names = {"qgate_lns_qaoa": "QGate QAOA", "qgate_lns_exact": "QGate exacto",
                 "simulated_annealing": "SA"}
        real = R.get("meta", {}).get("instance")
        fig, axs = plt.subplots(1, 2, figsize=(11, 4.2))
        cols = {"qgate_lns_qaoa": CYAN, "qgate_lns_exact": AMBER, "simulated_annealing": GREY}
        for m in sorted({r["method"] for r in sc}):
            rows = sorted([r for r in sc if r["method"] == m], key=lambda r: r["N"])
            axs[0].plot([r["N"] for r in rows], [r["gap_vs_bound_pct"] for r in rows], "o-",
                        color=cols.get(m, FG), label=names.get(m, m))
            axs[1].plot([r["N"] for r in rows], [r["time_s"] for r in rows], "o-",
                        color=cols.get(m, FG), label=m)
        axs[0].set_ylabel("gap vs cota GL (%)")
        axs[1].set_ylabel("tiempo (s)")
        axs[1].set_yscale("log")
        ns = sorted({r["N"] for r in sc})
        tick = [f"{n}" + ("*" if any(r["N"] == n and r["instance"] != real for r in sc) else "") for n in ns]
        for a in axs:
            a.set_xticks(ns, tick)
            a.set_xlabel("N  (* sintética)")
        _style(axs[0], "Calidad vs N")
        _style(axs[1], "Tiempo vs N")
        axs[0].legend(facecolor=BG, labelcolor=FG, edgecolor=GREY, fontsize=8)
        fig.tight_layout()
        fig.savefig(os.path.join(out, "escalabilidad.png"), dpi=160)
        plt.close(fig)
    _gate_map(R, out)


def _gate_map(R: dict, out: str) -> None:
    """Mapa de puertas: aleatoria vs mejor híbrida. Grosor = pasajeros, brillo = costo del par."""
    data = R.get("data", {})
    xy, F, D = data.get("gate_xy"), data.get("F"), data.get("D")
    A = {a["label"]: a for a in R.get("assignments", [])}
    pick = [A[k] for k in ("Aleatoria", "QGate híbrido") if k in A]
    if not xy or not F or not D or len(pick) < 2:
        return
    import numpy as np
    P, F, D = np.array(xy), np.array(F), np.array(D)
    n = len(P)
    fmax = F.max() or 1
    cmax = max(F[i, k] * D[a["perm"][i], a["perm"][k]] for a in pick
               for i in range(n) for k in range(i + 1, n)) or 1
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.6))
    for ax, a in zip(axs, pick):
        perm = a["perm"]
        for i in range(n):
            for k in range(i + 1, n):
                if F[i, k] <= 0:
                    continue
                p1, p2 = P[perm[i]], P[perm[k]]
                c = F[i, k] * D[perm[i], perm[k]]
                ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=AMBER, lw=0.6 + 6 * F[i, k] / fmax,
                        alpha=0.12 + 0.85 * c / cmax, solid_capstyle="round", zorder=1)
        inv = {g: i for i, g in enumerate(perm)}
        for g, (x, y) in enumerate(P):
            ax.scatter([x], [y], s=620, color="#17233a", edgecolors=GREY, linewidths=1.5, zorder=2)
            ax.text(x, y, f"V{inv[g] + 1}", color=AMBER, ha="center", va="center", fontsize=10,
                    fontweight="bold", zorder=3)
        _style(ax, f"{a['label']} · costo {a['cost']:g}")
        ax.set_xticks([]), ax.set_yticks([])
        ax.grid(False)
        ax.set_aspect("equal", adjustable="datalim")
        ax.margins(0.12)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "mapa_puertas.png"), dpi=160)
    plt.close(fig)
