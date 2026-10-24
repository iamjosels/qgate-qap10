"""Gráficos PNG para el PPT (fondo oscuro, poco texto)."""
from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

BG, FG, AMBER, CYAN, GREY, RED = "#0b1220", "#e6edf7", "#f5b700", "#22d3ee", "#64748b", "#f87171"


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

    hy = [h for h in R.get("hybrid", []) if h.get("history")]
    if hy:
        fig, ax = plt.subplots(figsize=(8, 4.2))
        cols = {"qgate_lns_qaoa": CYAN, "qgate_lns_exact": AMBER, "simulated_annealing": GREY}
        for h in hy:
            hist = h["history"]
            ax.plot([p["t"] for p in hist], [p["best"] for p in hist],
                    color=cols.get(h["method"], FG), label=h.get("label", h["method"]), lw=2)
        ref = R.get("meta", {}).get("reference_optimum")
        if ref:
            ax.axhline(ref, color=RED, ls=":", label=f"Óptimo {ref:g}")
        ax.set_xlabel("tiempo (s)")
        ax.set_ylabel("mejor costo")
        _style(ax, "Convergencia N completo")
        ax.legend(facecolor=BG, labelcolor=FG, edgecolor=GREY, fontsize=8)
        fig.tight_layout()
        fig.savefig(os.path.join(out, "hibrido_convergencia.png"), dpi=160)
        plt.close(fig)

    sc = R.get("scaling", [])
    if sc:
        fig, axs = plt.subplots(1, 2, figsize=(11, 4.2))
        cols = {"qgate_lns_qaoa": CYAN, "qgate_lns_exact": AMBER, "simulated_annealing": GREY}
        for m in sorted({r["method"] for r in sc}):
            rows = sorted([r for r in sc if r["method"] == m], key=lambda r: r["N"])
            axs[0].plot([r["N"] for r in rows], [r["gap_vs_bound_pct"] for r in rows], "o-",
                        color=cols.get(m, FG), label=m)
            axs[1].plot([r["N"] for r in rows], [r["time_s"] for r in rows], "o-",
                        color=cols.get(m, FG), label=m)
        axs[0].set_ylabel("gap vs cota GL (%)")
        axs[1].set_ylabel("tiempo (s)")
        axs[1].set_yscale("log")
        _style(axs[0], "Calidad vs N")
        _style(axs[1], "Tiempo vs N")
        axs[0].legend(facecolor=BG, labelcolor=FG, edgecolor=GREY, fontsize=8)
        fig.tight_layout()
        fig.savefig(os.path.join(out, "escalabilidad.png"), dpi=160)
        plt.close(fig)
