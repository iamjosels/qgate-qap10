"""Sección del README para la etapa 3 (final), generada desde results/final.json."""
from __future__ import annotations

NAME = {"sa": "SA", "ls": "2-swap con reinicios", "exact": "Bloque: enumeración", "random_valid": "Bloque: azar 6 válidas",
        "exact_rand": "Bloque: enumeración + desempate", "qaoa": "Bloque: QAOA (p=2, XY)"}


def g(x, d=0):
    return "-" if x is None else f"{x:.{d}f}"


def pc(x, d=1):
    return "-" if x is None else f"{100 * x:.{d}f}%"


def final_md(F: dict) -> str:
    m = F["meta"]
    out = [f"SIMULADOR (Qiskit Aer) y CPU. {len(m['seeds'])} semillas ({m['seeds'][0]} a {m['seeds'][-1]}), B={m['blocks_B']} iteraciones "
           f"externas para todos los solvers del modo dos fases, {m['shots']} shots por bloque para QAOA y para el azar, SA "
           f"{m['sa_iters']}×{m['sa_restarts']}. {m['nota_tiempos']}. Corrida: {g(m['wall_s'] / 60, 1)} min. Comando: `{m['command']}`. "
           f"Fuente: `results/final.json`."]
    synth = [i["instance"] for i in F["instances"] if i["origen"] == "sintética"]
    bests = [F["verdict"][i]["best_median"].split("/")[0] for i in synth if i in F["verdict"]]
    dist = any(F["verdict"][i]["distinguible"] for i in synth if i in F["verdict"])
    block0 = all(F["attribution"].get(i, {}).get("cost_reduction_at_best_by_origin", {}).get("block", 1) == 0 for i in synth)
    if bests and all(b == "sa" for b in bests):
        tail = "el clásico (SA) gana en todas las instancias sintéticas."
    elif bests and all(b != "qaoa" for b in bests):
        tail = ("la mejor mediana en N>10 es de un método clásico (" + ", ".join(sorted({NAME.get(b, b) for b in bests})) + ")"
                + ("." if dist else " y ninguna diferencia es distinguible entre semillas; SA no tiene la mejor mediana en N>10."))
    else:
        tail = "ver en la tabla qué método tiene la mejor mediana en cada N y si es distinguible."
    out.insert(0, "> **La memoria cuántica no crece con N; la calidad todavía no escala; " + tail + "**"
               + (" Los bloques QAOA no aportaron reducción de costo." if block0 else "") + "\n")
    out.append("\n**Instancias.** " + "; ".join(f"{i['instance']} ({i['origen']}, N={i['N']}, cota GL {g(i['gl_bound'])}, mejor costo encontrado {g(i['best_found'])})"
                                             for i in F["instances"]) + ". El mejor costo encontrado no es un óptimo demostrado.")
    out.append("\n### ¿Cuánto es cuántico y cuánto clásico? (híbrido QAOA en dos fases)\n")
    out.append("| Instancia | (i) Variables cuánticas 9/N² | (ii) Movimientos swap · bloque QAOA · perturbación | (iii) Reducción de costo swap · bloque · perturbación | (iv) % tiempo en QAOA · solo Aer |")
    out.append("|---|---|---|---|---|")
    for i in F["instances"]:
        a = F["attribution"].get(i["instance"])
        if not a:
            continue
        mv, rd = a["moves_at_best_by_origin"], a["cost_reduction_at_best_by_origin"]
        out.append(f"| {i['instance']} | {pc(a['variables_quantum_frac'])} | {mv['swap']} · {mv['block']} · {mv['kick']} | "
                   f"{g(rd['swap'])} · {g(rd['block'])} · {g(rd['kick'])} | {pc(a['frac_wall_in_qaoa_mean'])} · {pc(a['frac_wall_in_aer_mean'])} |")
    out.append("\n*(ii) y (iii): movimientos aceptados y reducción de costo hasta la mejor asignación, sumados en todas las semillas y los dos "
               "selectores; las perturbaciones suben el costo, por eso restan. La atribución depende del orden de las fases: el 2-swap corre "
               "primero y se lleva las mejoras fáciles. (iv): subrutina QAOA = circuito Qiskit + simulación Aer + COBYLA clásico que la orquesta.*")
    out.append("\n**(v) Tasa de mejora de los bloques k=3 desde un óptimo local 2-swap**\n")
    out.append("| Instancia | Enumeración | Azar 6 válidas | Enumeración + desempate | QAOA |\n|---|---|---|---|---|")
    for i in F["instances"]:
        a = F["attribution"].get(i["instance"])
        if not a:
            continue
        r = a["block_improve_rate_from_local_opt"]
        c = lambda k: f"{pc(r[k]['rate'])} ({r[k]['blocks_improved']}/{r[k]['blocks_tried']})" if r.get(k) and r[k]["rate"] is not None else "-"  # noqa: E731
        out.append(f"| {i['instance']} | {c('exact')} | {c('random_valid')} | {c('exact_rand')} | {c('qaoa')} |")
    out.append("\n### Escalamiento: mediana [mín, máx] entre semillas\n")
    out.append("| Instancia | Método | Selector | Costo | Gap vs cota GL | Gap vs mejor encontrado | Tiempo (s) | Memoria (MB) | Factible |")
    out.append("|---|---|---|---|---|---|---|---|---|")
    for s in F["summary"]:
        out.append(f"| {s['instance']} | {NAME.get(s['solver'], s['solver'])} | {s['select'] or '-'} | {g(s['cost_median'])} [{g(s['cost_min'])}, {g(s['cost_max'])}] | "
                   f"{g(s['gap_vs_gl_median_pct'], 1)}% | {g(s['gap_vs_best_found_median_pct'], 1)}% [{g(s['gap_vs_best_found_min_pct'], 1)}, {g(s['gap_vs_best_found_max_pct'], 1)}] | "
                   f"{g(s['time_median_s'], 1)} | {g(s['peak_mem_median_mb'], 2)} | {pc(s['feasible_rate'], 0)} |")
    out.append("\n**Veredicto por instancia** (un método se marca ganador solo si su máximo queda por debajo del mínimo de todos los demás):")
    for inst, v in F["verdict"].items():
        out.append(f"- {inst}: mejor mediana {v['best_median']} ({'distinguible' if v['distinguible'] else 'no distinguible'}); empatados en esa mediana: {', '.join(v['ties_at_best_median'])}.")
    ar = F.get("angle_reuse")
    if ar:
        out.append(f"\n**Ángulos reutilizados** ({ar['instance']}, {ar['cold']['blocks']} bloques, {ar['shots']} shots): evaluaciones por bloque "
                   f"{g(ar['cold']['evals_mean'], 1)} en frío y {g(ar['warm']['evals_mean'], 1)} reutilizando (COBYLA agota el máximo de 40 en ambos); "
                   f"P(óptimo) del bloque {ar['cold']['p_optimal_mean']:.3f} en frío y {ar['warm']['p_optimal_mean']:.3f} reutilizando; tiempo por bloque "
                   f"{ar['cold']['time_mean_s']:.2f} s y {ar['warm']['time_mean_s']:.2f} s.")
    return "\n".join(out)
