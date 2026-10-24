# CLAUDE.md · Proyecto QGate (IBM Quantum Hackathon 2026, reto NTT DATA QAP10)

Este archivo es la fuente de verdad del proyecto. Léelo completo antes de hacer cualquier cosa.
Trabaja de forma autónoma, en español, con commits frecuentes. **El plazo es duro: hoy sábado
24 de octubre de 2026, todo debe estar listo y entregado antes de las 14:40 (hora de Lima).**
La presentación del equipo es entre 15:00 y 16:40 y deben estar los 4 integrantes.

---

## 1. Documentos fuente (leer primero)

Están en `docs/` (o en la raíz del proyecto si el equipo los dejó ahí):

- `BASES_DE_PARTICIPACION.pdf` (bases generales del hackathon: categorías, entregables, rúbrica general).
- `Reto_NTT_DATA.pdf` (especificación técnica del reto QAP10: modelo, etapas, qué mostrar, rúbrica del reto).

Si hay contradicción entre este archivo y los PDF, mandan los PDF. Si algo es ambiguo, toma la
lectura más razonable, déjala escrita en `docs/DECISIONES.md` y sigue.

---

## 2. Decisión tomada

- **Categoría:** 5.1 Industria (reto sorpresa de NTT DATA).
- **Reto:** QAP10, asignación cuadrática de 10 elementos a 10 ubicaciones (MIPLIB `qap10`).
- **Contexto industrial:** **Track A, aeropuerto**: 10 vuelos de conexión a 10 puertas de embarque.
  F[i][k] = pasajeros que conectan entre vuelos i y k. D[j][l] = distancia entre puertas j y l.
  Las unidades son supuestos (qap10 es un benchmark matemático, no un aeropuerto real). Decirlo siempre.
- **Nombre del proyecto:** **QGate**.
- **Tesis del pitch:** "QAOA solo no llega a 100 qubits. Usado como subrutina de tamaño fijo
  dentro de una búsqueda clásica, sí escala, y medimos con números cuánto aporta cada parte."
- **No se busca demostrar ventaja cuántica.** Se busca medir qué funciona, qué no y por qué (lo pide el reto).

---

## 3. Rúbricas (optimizar para esto)

### 3.1 Rúbrica del reto NTT DATA (100 pts)
| Criterio | Pts | Cómo lo cubrimos |
|---|---|---|
| Modelo matemático, lectura de datos y factibilidad | 25 | Parser del MPS que reconstruye T sin depender de nombres; validación 24/32/340; factibilidad verificada en cada resultado |
| Uso pertinente de Qiskit y justificación del método | 30 | QAOA estándar (mixer X) vs Quantum Alternating Operator Ansatz (mixer XY por fila + estado W); barrido de λ; ruido; QAOA como subrutina en el híbrido. Explicar qué hace Qiskit y qué es clásico |
| Calidad de las asignaciones y comparación clásica | 20 | Exacto (fuerza bruta 10!), simulated annealing, cota de Gilmore-Lawler, gap % solo sobre soluciones válidas |
| Rigor experimental: tiempo, límites y escalamiento | 15 | Tiempos, memoria pico, qubits, escalamiento N=10 a 16+, semillas, versiones |
| Claridad y sentido operativo del resultado | 10 | Dashboard con mapa de puertas, narrativa del aeropuerto, PPT con poco texto |

### 3.2 Rúbrica general de las bases (100 pts; la fila de 20% del reto depende de la categoría)
Innovación/validación/potencial 25 (incluye **estrategia para abordar errores o limitaciones**, resaltado en amarillo en el PDF),
Uso de Qiskit y claridad del pitch 25, Reto de la categoría 20, Rigor técnico y reproducibilidad 15,
Calidad de la solución y arquitectura 15. "Usar Qiskit por sí solo no garantiza puntaje alto: se valora pertinencia y justificación".

---

## 4. Reglas duras del reto (no romper ninguna)

1. **Convención de costo: cada par se cuenta UNA vez.** `C = sum_{i<k} F_ik * D_{pi(i) pi(k)}`.
   Si sale 48, 64 o 680 se está duplicando.
2. **Óptimos de control:** subinstancia con las primeras N filas y columnas: N=3 → **24**, N=4 → **32**.
   Instancia completa N=10 → **340**.
3. **El 340 solo se usa para evaluar (gap), nunca como punto de partida** de ningún método.
4. **Si se repara una solución con un método clásico, reportar el resultado crudo y el corregido.**
5. **La energía penalizada del QUBO no es el costo de una asignación factible.** Si se reportan ambas, etiquetarlas.
6. **gap(%) = 100 * (C - 340) / 340, solo sobre soluciones válidas.**
7. **Qiskit debe usarse de forma sustantiva** (construir, representar, simular o evaluar). Aclarar qué hace Qiskit y qué es clásico.
8. **λ debe justificarse** y debe comprobarse la factibilidad de los resultados.
9. Explicar cómo se recuperaron los coeficientes del MPS y cómo se verificó la escala (slide dedicada).
10. Reconocer librerías y fuentes (Qiskit, Qiskit Aer, NumPy, SciPy, MIPLIB) en README y PPT.
11. **Nunca inventar números.** Todo número del PPT, README o dashboard sale de `results/results.json`.
    Resultados de simulador nunca se presentan como de hardware real.
12. En textos para humanos (README, PPT, descripción): sin guiones largos (—), prosa directa, poco texto en slides.

### Qué debe mostrar el equipo al terminar el Día 1 (sección 6 del reto)
- Modelo y datos: instancia, variables, función de costo, restricciones y reducción realizada.
- Baseline clásico: método, asignación, costo y tiempo.
- Componente Qiskit: qué se ejecutó, tamaño, configuración y resultados.
- Comparación: mejor costo factible, fracción factible de muestras, tiempo total y límites del método.
- Reproducibilidad: código, versiones, semillas y parámetros.
- Si Qiskit no mejora al clásico, **explicar qué ocurrió** (es lo esperado y se valora).

---

## 5. Estado actual del código (ya hecho y probado en sandbox)

Python 3.11+ (probado en 3.13), Qiskit 2.6.1, Qiskit Aer 0.18.0, NumPy 2.x, SciPy 1.x.

```
qgate/
  instance.py   QAPInstance: tensor T simétrico (convención par una vez), cost, cost_batch, cost_x,
                subinstance(n), from_FD(F, D, convention), synthetic(n), from_qaplib, from_matrices_file
  mps.py        read_mps (gz o texto), recover_qap(path) -> Recovery(instance, candidates, report),
                write_linearized_mps (genera un MPS sintético con la MISMA estructura, para tests)
  classical.py  brute_force (10! en ~6 s), swap_delta O(N), local_search (2-swap), simulated_annealing,
                gilmore_lawler_bound (generalizada a T arbitrario), random_assignment
  qubo.py       build_qubo(inst, lam) con penalidades, lambda_auto, to_ising, to_sparse_pauli_op,
                energies_all, feasible_mask, bitstring_to_x (ojo little-endian), repair (asignación lineal)
  quantum.py    build_qaoa_circuit (mixer "x" o "xy" con estado W por fila), run_qaoa (optimiza con
                COBYLA sobre CVaR o media usando probabilidades exactas de Aer, luego muestrea con shots;
                opción de ruido despolarizante), circuit_stats (profundidad, CX), solve_subproblem_qaoa
  hybrid.py     build_subproblem (k elementos con el resto fijo; interacciones fijas como términos lineales),
                qgate_lns (búsqueda en vecindarios grandes, solver "qaoa" o "exact" de control,
                perturbación tipo iterated local search, memoria pico, tasa de éxito de QAOA por subproblema)
  bench.py      orquestador: python -m qgate.bench --mps data/qap10.mps.gz  -> results/results.json + PNGs
  plots.py      PNG oscuros para el PPT (qaoa_vs_azar, barrido_lambda, hibrido_convergencia, escalabilidad)
tests/          test_core.py, test_quantum.py, test_hybrid.py (todos pasan)
dashboard/      sample_results.json (mock con el esquema). build_report.py ESTÁ PENDIENTE (ver P2)
examples/sintetico/  resultados de una corrida rápida sobre un MPS SINTÉTICO (no son qap10, no usarlos en el PPT)
```

### Cómo reconstruye el MPS (clave para explicar al jurado)
- 4150 variables = 100 x_ij + 4050 y (45 pares i<k por 90 pares ordenados j≠l). 1820 filas = 20 de asignación + 1800 de enlace.
  Mi MPS sintético reproduce exactamente esos conteos.
- Filas de asignación: rhs = 1 y coeficientes = 1 → sus variables son las x. Se separan en dos familias (elementos y ubicaciones).
- Cada y aparece en filas de enlace junto a exactamente dos x (x_ij y x_kl) → su coeficiente objetivo es F_ik·D_jl.
- Se arma T y se factoriza en F y D por SVD de rango 1 (se reporta el residuo).
- El orden de índices importa para "primeras N filas y columnas": se prueban candidatas
  (`nombres`, `orden_columnas`, `orden_filas`) y el bench elige la que reproduce 24 y 32.

### Resultados de prueba (instancia SINTÉTICA, solo para saber que todo corre)
- Fuerza bruta N=10: ~6 s. SA llega al óptimo en ~3 s.
- QAOA N=3 mixer X p=1: P(válida) 0.16 vs azar 0.012. Mixer XY: 0.30 vs 0.22.
- QAOA N=4 mixer X: 0.029 vs 0.0004 (~70x). Mixer XY: 0.20 a 0.42 vs 0.094.
- Híbrido: QAOA resolvió el 100% de los subproblemas de 3 vuelos de forma óptima; la calidad final
  del híbrido la limita la estrategia de vecindario, no el componente cuántico (mensaje honesto para el pitch).
- Subproblema QAOA: ~0.12 s; iteración del híbrido con QAOA: ~0.3 a 0.4 s.

---

## 6. Plan de trabajo (ejecutar en orden, con timebox)

### P0 · Datos reales y validación (objetivo: 12:15)
1. `pip install -r requirements.txt` y correr `python tests/test_core.py` (debe pasar).
2. Descargar `qap10.mps.gz` a `data/`:
   - Intento 1: `curl -L -o data/qap10.mps.gz https://miplib.zib.de/WebData/instances/qap10.mps.gz`
   - Intento 2: abrir https://miplib.zib.de/instance_details_qap10.html en Chrome y descargar desde ahí.
   - Si no hay forma, pedir el archivo al equipo y seguir con lo demás mientras tanto.
3. Validar: `python -c "from qgate.mps import recover_qap; r=recover_qap('data/qap10.mps.gz'); print(r.report)"`
   y luego `python -m qgate.bench --mps data/qap10.mps.gz --quick --scale 10 --hybrid-iters 40`.
   Debe dar N=3 → 24, N=4 → 32, N=10 → 340.
4. **Si ninguna candidata da 24/32**, depurar en este orden:
   a) imprimir 20 líneas de ROWS y COLUMNS del MPS para ver la nomenclatura real;
   b) revisar si las x tienen números en el nombre en otro formato y ajustar la candidata `nombres`;
   c) revisar si hay y para ambos órdenes (i<k y i>k): entonces los costos salen duplicados → dividir;
   d) revisar si el objetivo tiene constante o sentido MAX;
   e) probar todas las combinaciones de orden de familias (A/B) y orientación;
   f) si a las 12:30 sigue sin cuadrar, avisar al usuario para preguntar a la organización.
   Documentar lo encontrado en `docs/DECISIONES.md` (esto alimenta la slide "cómo verificamos la escala").
5. Crear el repo público en GitHub en la cuenta personal **iamjosels** (NO usar `prestigecreations`,
   que es para clientes). Nombre sugerido: `qgate-qap10`. Primer commit con lo que hay.

### P1 · Mejoras del motor y corrida completa (objetivo: 13:15)
Arreglar primero, en este orden (cada cambio con su test rápido):
1. `bench.py`: el híbrido con solver exacto corre `H*3` iteraciones y el de QAOA `H`. **Comparación injusta**:
   usar el mismo número de iteraciones y la misma semilla y arranque para ambos. Igual en la sección de escalamiento.
2. `hybrid.py`: en la perturbación, reiniciar desde `best_perm` (no desde la actual) y subir `stall_limit`
   a ~25. Probar con solver exacto (rápido) en 2 o 3 semillas y quedarse con la mejor configuración.
   Objetivo: que el híbrido llegue a 340 o muy cerca en N=10.
3. `bench.py`: en el log de QAOA mostrar también `feasible_fraction_shots` (con ruido cambia; `p_feasible` es la ideal).
4. Agregar a `results.json` → `data.gate_xy`: coordenadas 2D de las puertas obtenidas de D con MDS clásico
   (numpy, eigendescomposición de la matriz de distancias doblemente centrada). Sirve para el mapa del dashboard.
5. Correr la versión completa: `python -m qgate.bench --mps data/qap10.mps.gz --scale 10,12,14,16`
   (estimado 10 a 15 min). Si se pasa de tiempo, usar `--quick`.
6. Opcional solo si sobra tiempo y el usuario da un token de IBM Quantum: correr N=3 en hardware real
   con `qiskit-ibm-runtime` (SamplerV2). Enviar el job temprano, la cola puede tardar. Reportar
   siempre separado del simulador.

### P2 · Dashboard demo (objetivo: 13:45)
Construir `dashboard/build_report.py` (solo stdlib) que lee `results/results.json` y escribe
`results/report.html` autocontenido (JSON embebido en `<script id="data" type="application/json">`),
Chart.js solo desde `https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js`, fuentes solo de Google Fonts.
`bench.py` ya lo llama automáticamente si existe. Probar con `dashboard/sample_results.json`.
- Estética: tablero de salidas de aeropuerto, fondo navy/charcoal, acentos ámbar, cian para lo cuántico,
  Inter o Space Grotesk + JetBrains Mono para números. Variables CSS. Responsive hasta 380 px sin scroll horizontal.
  Moderno, visual, estilizado. Muy poco texto: etiquetas cortas, números grandes, gráficos.
- Secciones (cada una se oculta si falta su dato):
  1. Hero: "QGate", "Vuelos → puertas con QAOA híbrido", KPIs (mejor costo híbrido y gap vs 340, óptimo exacto,
     mejor ratio de aproximación QAOA en N=4, qubits por subproblema = 9), badge "Track A · Aeropuerto".
  2. Datos validados: tabla de `validation` (24/32/340 con check), heatmaps de F y D, estrategia de índices y residuo.
  3. Mapa de puertas (SVG): puertas en `data.gate_xy`, vuelo asignado a cada puerta, curvas entre puertas cuyo
     grosor es el flujo F. Botones para alternar entre `assignments` (Aleatoria, Clásico exacto, QGate híbrido)
     mostrando el costo de cada una: que se vea cómo las líneas gruesas se acortan.
  4. QAOA vs azar: barras log de `p_feasible` vs `random_feasible_baseline` por experimento + tabla
     (N, qubits, mixer, p, P(válida), P(óptimo), mejor costo, ratio, tiempo, CX).
  5. Barrido de λ: P(válida) y P(óptimo) vs λ/λ0 por mixer.
  6. Híbrido: curvas de `hybrid[*].history` (mejor costo vs iteración o tiempo) con línea de referencia en 340.
  7. Escalabilidad: gap vs cota GL y tiempo vs N por método (marcar instancias sintéticas).
  8. Reproducibilidad y limitaciones: versiones, semilla, fecha, `meta.limitations`.
- Publicarlo en GitHub Pages (carpeta `docs/` del repo o rama `gh-pages`) para tener **link de demo funcional**.

### P3 · Material de entrega (objetivo: 14:15)
1. `README.md` completo: problema, Track A, modelo (con la fórmula), cómo se leyó el MPS y se validó
   24/32/340, métodos (clásico, QAOA X vs XY, híbrido), tabla de resultados (generada desde results.json),
   limitaciones, cómo reproducir (comandos, versiones, semillas), créditos de librerías y MIPLIB, link al dashboard.
2. `docs/descripcion_breve.md`: 4 a 6 líneas (problema, solución, funcionalidades) para el portal de entrega.
3. PPT (`entrega/QGate.pptx`, con python-pptx o la herramienta disponible), **muy poco texto, palabras clave e imágenes**,
   fondo oscuro coherente con el dashboard. Pitch de 2:30 a 3:00 min. Estructura sugerida (8 slides):
   1. QGate · "Vuelos → puertas" (portada, nombres de los 4 integrantes).
   2. Problema: 10 vuelos, 10 puertas, 10! = 3.6 M asignaciones; pasajeros caminando (supuesto).
   3. Datos: MPS → F y D, validación 24 · 32 · 340 (la slide de "verificamos la escala").
   4. Qiskit: QUBO → Ising → QAOA; mixer X vs mixer XY (gráfico qaoa_vs_azar.png).
   5. Límites y cómo los manejamos: tabla de memoria (16 qubits = 1 MiB; 100 qubits imposible), λ (barrido_lambda.png), ruido.
   6. Híbrido QGate: subproblemas de 9 qubits, tasa de éxito de QAOA, convergencia a 340 (hibrido_convergencia.png).
   7. Escala: N = 10 → 16, qubits constantes, gap vs cota (escalabilidad.png).
   8. Cierre: qué aporta lo cuántico hoy, qué falta, potencial (hardware, k mayor, warm start).
4. Guion del pitch en `entrega/guion.md` (~350 palabras, con tiempos por bloque) y lista de preguntas probables
   del jurado con respuesta corta (por qué cuántico, cómo escala, hardware real, cómo se eligió λ, qué hizo cada uno).
5. Guion de video demo de 60 a 90 s (`entrega/guion_video.md`) mostrando el dashboard y una corrida del bench.

### P4 · Cierre (objetivo: 14:30)
- Verificar que el repo es público, que el README renderiza, que el link de Pages abre en incógnito.
- Dejar en `entrega/CHECKLIST.md` los campos del portal: nombre del equipo, integrantes, link GitHub,
  link demo o video, descripción breve, PPT. La entrega en el portal la hace una persona del equipo.

---

## 7. Comandos útiles

```bash
pip install -r requirements.txt
python tests/test_core.py && python tests/test_quantum.py && python tests/test_hybrid.py
python -m qgate.bench --synthetic 10 --quick --scale 10,14 --hybrid-iters 60 --out results_demo   # sin datos reales
python -m qgate.bench --mps data/qap10.mps.gz --quick                                              # real, rápido
python -m qgate.bench --mps data/qap10.mps.gz --scale 10,12,14,16                                  # real, completo
python -m qgate.bench --mps data/qap10.mps.gz --scale-files inst14.dat --qaplib-convention pair_once
python dashboard/build_report.py results/results.json results/report.html
```

---

## 8. Reglas de trabajo para Claude Code

- Autonomía total dentro de este plan. No pedir confirmación para pasos rutinarios. Preguntar solo si
  algo bloquea (por ejemplo, los datos no cuadran con 24/32 a las 12:30, o falta un token).
- Respetar los timeboxes. Si una mejora se come el tiempo, se corta y se documenta como limitación.
  Un resultado sólido en N=3/4 + N=10 validado vale más que una extensión a medias.
- Commits pequeños y frecuentes con mensajes claros. Nunca dejar el repo roto.
- Probar cada cambio (los tests existentes y una corrida corta del bench).
- Código modular y limpio; mantener la separación de módulos actual.
- Honestidad: si QAOA no mejora al clásico, decirlo y explicar por qué (factibilidad, profundidad, paisaje con penalidades, simulación limitada).
- Al terminar cada fase, escribir una línea de estado en `docs/ESTADO.md` (hora, qué quedó, qué falta).
