# QGate · Vuelos → puertas con QAOA híbrido

**IBM Quantum Hackathon 2026 · Categoría 5.1 Industria · Reto NTT DATA QAP10 · Track A Aeropuerto**

**Demo:** https://iamjosels.github.io/qgate-qap10/ · **PPT:** [`entrega/QGate.pptx`](entrega/QGate.pptx) · **Descripción breve:** [`docs/descripcion_breve.md`](docs/descripcion_breve.md)

> QAOA solo no llega a 100 qubits. Usado como subrutina de tamaño fijo (9 qubits) dentro de una búsqueda
> clásica, sí escala, y medimos con números cuánto aporta cada parte. No buscamos demostrar ventaja
> cuántica: medimos qué funciona, qué no y por qué.

## 1. Problema (Track A)

Un aeropuerto asigna 10 vuelos de conexión a 10 puertas de embarque. `F[i][k]` son los pasajeros que
conectan entre los vuelos `i` y `k`; `D[j][l]` es la distancia entre las puertas `j` y `l`. Queremos que
los vuelos que comparten muchos pasajeros queden en puertas cercanas.

Los datos son la instancia **qap10 de MIPLIB 2017**, un benchmark matemático: pasajeros y distancias son
**supuestos de negocio**, no mediciones de un aeropuerto real.

## 2. Modelo

`x_ij = 1` si el vuelo `i` va a la puerta `j`.

```
min  C(x) = Σ_{i<k} Σ_{j≠l} F_ik · D_jl · x_ij · x_kl        (cada par se cuenta una vez)
s.a. Σ_j x_ij = 1  ∀i      Σ_i x_ij = 1  ∀j      x_ij ∈ {0,1}
```

Hay 10! = 3 628 800 asignaciones válidas. Para Qiskit las restricciones entran como penalidad QUBO

```
H(x) = C(x) + λ Σ_i (Σ_j x_ij − 1)² + λ Σ_j (Σ_i x_ij − 1)²
```

y con `x = (1 − Z)/2` se obtiene un Hamiltoniano de Ising. **La energía penalizada H no es el costo C de
una asignación**: todos los costos reportados son C sobre asignaciones válidas, y el gap es
`gap(%) = 100 · (C − 340) / 340`, solo sobre asignaciones válidas.

## 3. Cómo leímos el MPS y verificamos la escala

`qgate/mps.py` reconstruye el costo **sin depender de los nombres** de las variables:

1. Las filas con rhs = 1 y coeficientes 1 son las de asignación: sus variables son las 100 `x`.
   Se separan en dos familias de 10 filas (vuelos y puertas).
2. Las otras 4050 variables `y` linealizan los productos: cada `y` aparece en filas de enlace junto a
   exactamente dos `x` (`x_ij`, `x_kl`), y su coeficiente objetivo es `F_ik · D_jl`.
3. Con eso se arma el tensor `T[i,j,k,l]` y se factoriza en `F` y `D` por SVD de rango 1. Residuo: 0.
4. Solo existen `y` para pares `i < k`: la convención del archivo cuenta cada par una vez.
5. "Primeras N filas y columnas" depende del orden de índices: se prueban las candidatas
   (`orden_columnas`, `orden_filas`) y se elige la que reproduce los óptimos de control.

Resultado: **N = 3 → 24, N = 4 → 32, N = 10 → 340**, idénticos a los del enunciado (ver tabla abajo). Si
se duplicaran pares saldría 48, 64 y 680. El 340 solo se usa para medir el gap; ningún método lo recibe.
Detalle en [`docs/DECISIONES.md`](docs/DECISIONES.md).

## 4. Métodos

| Método | Qué es | Dónde |
|---|---|---|
| Fuerza bruta | Enumera las 10! permutaciones en bloques (sin guardarlas) | `classical.py` |
| Simulated annealing | Swaps con delta O(N), varios reinicios | `classical.py` |
| Cota Gilmore-Lawler | Cota inferior (para N sin óptimo conocido) | `classical.py` |
| QAOA mixer X | QAOA estándar: estado `|+⟩`, todas las restricciones como penalidad | `quantum.py` |
| QAOA mixer XY | Quantum Alternating Operator Ansatz: estado W por fila y mixer XY en anillo; cada vuelo queda en una sola puerta por construcción, solo las columnas se penalizan | `quantum.py` |
| **QGate híbrido** | Búsqueda en vecindarios grandes: elige 3 vuelos, arma el subproblema de 9 qubits con el resto fijo (las interacciones fijas pasan a términos lineales), lo resuelve con QAOA (mixer XY, p=2) y acepta solo si mejora estrictamente; perturba desde la mejor asignación si se estanca | `hybrid.py` |
| Control exacto | El mismo marco híbrido con el subproblema resuelto por enumeración (3! = 6), mismas iteraciones, semilla y arranque | `hybrid.py` |
| Control azar | El mismo marco con muestras uniformes sobre los estados con una puerta por vuelo, con el mismo número de shots que QAOA (512 y 8). Separa el aporte de QAOA del aporte del muestreo | `hybrid.py` |

### Qué hace Qiskit y qué es clásico

| Qiskit (Aer) | Clásico (NumPy/SciPy) |
|---|---|
| Construye el circuito QAOA parametrizado (costo Ising + mixer X o XY + estado W) | Lee el MPS, reconstruye F y D |
| Simula el statevector exacto para optimizar los ángulos | Arma el QUBO, elige λ, pasa a Ising |
| Muestrea con shots, con y sin ruido despolarizante | COBYLA optimiza los ángulos (objetivo CVaR) |
| Transpila y cuenta profundidad y compuertas CX | Elige vecindarios, acepta movimientos, perturba |
| Resuelve cada subproblema de 9 qubits del híbrido | Fuerza bruta, SA y cota como referencias |

**λ.** `λ0 = max_ij ( L_ij + Σ_{k≠i} max_{l≠j} T[i,j,k,l] )`, el mayor aporte posible de una asignación.
Quitar o duplicar una asignación cambia el costo como mucho en λ0 y viola al menos una restricción, así
que con λ ≥ λ0 ninguna asignación inválida le gana a la mejor válida. Se valida con un barrido λ/λ0.

## 5. Resultados

Todo sale de [`results/results.json`](results/results.json) (simulador Qiskit Aer) y de [`results/hardware.json`](results/hardware.json) (una corrida N=3 en ibm_kingston de IBM Quantum, reportada aparte). Tablas
generadas con `python entrega/make_tables.py`.

<!-- RESULTS:START -->
### Validación de escala

| N | Óptimo calculado | Esperado | OK | Tiempo (s) |
|---|---|---|---|---|
| 3 | 24 | 24 | sí | 0.000 |
| 4 | 32 | 32 | sí | 0.000 |
| 10 | 340 | 340 | sí | 6.948 |

### Instancia completa N = 10 (gap solo sobre asignaciones válidas)

| Método | Costo | Gap vs 340 (%) | Tiempo (s) | Notas |
|---|---|---|---|---|
| Fuerza bruta (10! permutaciones) | 340 | 0.0 | 6.9 | 1 óptimo(s) |
| Simulated annealing | 340 | 0.0 | 13.7 | clásico puro |
| Cota Gilmore-Lawler | 301 (cota inferior) | - | 0.005 | no es una asignación |
| **QGate híbrido (QAOA p=2, 9 qubits, 512 shots)** crudo | **340** | 0.0 | 186.0 | 300 iteraciones, 300 subproblemas |
| QGate híbrido + pulido 2-swap (clásico) | 340 | 0.0 | - | reportado aparte del crudo |
| QGate con subproblema exacto (control) | 340 | 0.0 | 0.44 | mismo presupuesto, semilla y arranque |
| Asignación aleatoria | 536 | 57.6 | - | referencia |

### Ablación del solver del subproblema (mismas iteraciones, semilla y arranque)

| Solver | Shots | Costo final | Gap (%) | Éxito en subproblemas | P(óptimo) medio por subproblema | Azar P(óptimo) | Tiempo (s) |
|---|---|---|---|---|---|---|---|
| QGate · QAOA (512 shots) | 512 | 340 | 0.0 | 100% | 0.094 | 0.039 | 186.0 |
| Control · subproblema exacto | - | 340 | 0.0 | 100% | 1.000 | 0.039 | 0.4 |
| Control · azar (512 shots) | 512 | 340 | 0.0 | 100% | 0.039 | 0.039 | 0.6 |
| QGate · QAOA (8 shots) | 8 | 372 | 9.4 | 59% | 0.096 | 0.04 | 208.3 |
| Control · azar (8 shots) | 8 | 390 | 14.7 | 29% | 0.039 | 0.039 | 0.7 |

*Éxito = el solver devolvió el óptimo del subproblema (sin muestra válida cuenta como fallo). Azar = muestras uniformes sobre los estados con una puerta por vuelo (el mismo espacio que el estado W).*

Robustez (solver exacto, 300 iteraciones, semillas 7 a 18): media 354.5 (gap medio 4.3%), mejor 340, peor 374, llega a 340 en 4 de 12.

### QAOA en subinstancias (Qiskit Aer)

| Experimento | Qubits | Mixer | p | Ruido | P(válida) ideal | Válidas en shots | Azar | P(óptimo) | Mejor costo | Ratio medio | Tiempo (s) | CX | Profundidad |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| N3-x-p1 | 9 | X | 1 | none | 0.137 | 0.144 | 0.012 | 0.047 | 24 (ópt 24) | 0.904 | 1.0 | 72 | 53 |
| N3-x-p2 | 9 | X | 2 | none | 0.307 | 0.313 | 0.012 | 0.102 | 24 (ópt 24) | 0.899 | 3.2 | 144 | 85 |
| N3-xy-p1 | 9 | XY | 1 | none | 0.789 | 0.775 | 0.222 | 0.266 | 24 (ópt 24) | 0.899 | 3.4 | 126 | 98 |
| N3-xy-p2 | 9 | XY | 2 | none | 0.623 | 0.612 | 0.222 | 0.185 | 24 (ópt 24) | 0.896 | 7.7 | 234 | 163 |
| N4-xy-p1 | 16 | XY | 1 | none | 0.477 | 0.475 | 0.094 | 0.042 | 32 (ópt 32) | 0.690 | 19.3 | 292 | 143 |
| N4-x-p1 | 16 | X | 1 | none | 0.041 | 0.041 | 0.00037 | 0.0035 | 32 (ópt 32) | 0.684 | 7.5 | 192 | 86 |
| N4-xy-p2 | 16 | XY | 2 | none | 0.475 | 0.474 | 0.094 | 0.042 | 32 (ópt 32) | 0.688 | 55.5 | 548 | 237 |
| N3-x-p1-noise0.01 | 9 | X | 1 | desp. 0.01 | 0.137 | 0.085 | 0.012 | 0.047 | 24 (ópt 24) | 0.906 | 1.0 | 72 | 53 |
| N3-xy-p1-noise0.01 | 9 | XY | 1 | desp. 0.01 | 0.789 | 0.250 | 0.222 | 0.266 | 24 (ópt 24) | 0.897 | 3.2 | 126 | 98 |

*Ratio medio = óptimo / costo medio de las muestras válidas. Azar: para mixer X es la fracción de bitstrings válidos; para XY, la fracción válida entre estados con una puerta por vuelo.*

### Barrido de λ (N = 3, p = 1)

| Mixer | λ0×0.25 | λ0×0.5 | λ0×1 | λ0×2 | λ0×4 |
|---|---|---|---|---|---|
| X P(válida) / P(óptimo) | 0.02 / 0.0082 | 0.076 / 0.027 | 0.137 / 0.047 | 0.255 / 0.082 | 0.243 / 0.079 |
| XY P(válida) / P(óptimo) | 0.241 / 0.119 | 0.557 / 0.230 | 0.789 / 0.266 | 0.361 / 0.115 | 0.364 / 0.116 |

### Escalamiento (N > 10 son instancias sintéticas)

| N | Instancia | Método | Costo | Cota GL | Gap vs cota (%) | Tiempo (s) | Memoria pico (MB) | Qubits |
|---|---|---|---|---|---|---|---|---|
| 10 | qap10 | SA | 340 | 301 | 13.0 | 23.31 | 0.04 | 0 |
| 10 | qap10 | QGate exacto | 374 | 301 | 24.3 | 0.28 | 0.05 | 0 |
| 10 | qap10 | QGate QAOA | 362 | 301 | 20.3 | 107.20 | 0.84 | 9 |
| 12 | synthetic-12 | SA | 362 | 302 | 19.9 | 23.87 | 0.04 | 0 |
| 12 | synthetic-12 | QGate exacto | 380 | 302 | 25.8 | 0.29 | 0.04 | 0 |
| 12 | synthetic-12 | QGate QAOA | 380 | 302 | 25.8 | 126.56 | 0.82 | 9 |
| 14 | synthetic-14 | SA | 665 | 548 | 21.4 | 22.96 | 0.04 | 0 |
| 14 | synthetic-14 | QGate exacto | 729 | 548 | 33.0 | 0.24 | 0.04 | 0 |
| 14 | synthetic-14 | QGate QAOA | 697 | 548 | 27.2 | 124.20 | 0.84 | 9 |
| 16 | synthetic-16 | SA | 675 | 524 | 28.8 | 23.40 | 0.04 | 0 |
| 16 | synthetic-16 | QGate exacto | 730 | 524 | 39.3 | 0.40 | 0.04 | 0 |
| 16 | synthetic-16 | QGate QAOA | 730 | 524 | 39.3 | 124.79 | 0.82 | 9 |

### IBM Quantum real · ibm_kingston (job `dbefhdom94ac738rnc00`)

| Experimento | Qubits | Válidas en hardware | Ideal (Aer) | Aer con ruido 1% | Azar | P(óptimo) | Mejor costo | Profundidad | Compuertas 2q |
|---|---|---|---|---|---|---|---|---|---|
| N3-x-p1 | 9 | **0.063** | 0.137 | 0.085 | 0.012 | 0.021 | 24 (ópt 24) | 246 | 132 |
| N3-xy-p1 | 9 | **0.254** | 0.789 | 0.250 | 0.222 | 0.087 | 24 (ópt 24) | 302 | 161 |

*4096 shots por circuito, ángulos optimizados en el simulador, circuito transpilado para ibm_kingston; 5 s de QPU. Resultado de hardware, separado del resto (simulador).*

### Memoria de un statevector genérico (16 bytes por amplitud)

| N | Qubits (N²) | Memoria |
|---|---|---|
| 3 | 9 | 8 KiB |
| 4 | 16 | 1 MiB |
| 5 | 25 | 512 MiB |
| 10 | 100 | 2.03e+31 B |
| 14 | 196 | 1.61e+60 B |

*Generado 2026-10-24T12:19:42 · semilla 7 · Python 3.14.7, Qiskit 2.6.1, Qiskit Aer 0.18.0, NumPy 2.5.4, SciPy 1.18.1 · corrida total 18.5 min.*
<!-- RESULTS:END -->

### Lectura de los resultados

<!-- FINDINGS:START -->
1. **Datos.** La reconstrucción del MPS reproduce los óptimos de control: N=3 → 24, N=4 → 32, N=10 → 340.
2. **QAOA directo (N=4, 16 qubits).** Con mixer X, P(válida) = 0.041 frente a 0.00037 del azar (112 veces). Con mixer XY + estado W, 0.477 frente a 0.094 (azar sobre estados con una puerta por vuelo). El mejor costo muestreado es el óptimo (32) en ambos, pero P(óptimo) es baja (0.0035 y 0.042): QAOA p=1 concentra poco.
3. **Ruido.** Con ruido despolarizante de 1%, la fracción válida del mixer XY cae de 0.789 a 0.250 (su azar es 0.222); la del mixer X, de 0.137 a 0.085. La ventaja estructural de XY es frágil al ruido.
4. **Híbrido N=10.** Con la semilla 7, QGate con QAOA (512 shots) termina en **340** (gap 0.0%) en 186 s. El control exacto termina en 340 y el azar con las mismas 512 muestras en 340: con piezas de 3 vuelos (6 asignaciones) y 512 muestras, el azar también encuentra el óptimo de cada pieza.
5. **Qué aporta QAOA (SIMULADOR, piezas de 3 vuelos en N=10).** P(óptimo) medio por pieza: 0.094 con QAOA p=2 frente a 0.039 del azar sobre los 27 estados con una puerta por vuelo (2.4 veces) y 0.180 del azar sobre las 6 permutaciones válidas. Con 8 shots, QAOA resuelve el 59% de las piezas; el azar sobre 27 estados, el 29%; el azar sobre las 6 permutaciones válidas, el 78% (calculado sobre las 300 piezas de esa corrida, `results/extra.json`); la enumeración exacta, el 100%. Costo final: QAOA 372, azar sobre 27 estados 390. QAOA concentra probabilidad respecto a su espacio de partida; en piezas de 3 vuelos aún no supera a muestrear permutaciones válidas ni a enumerar las 6 opciones.
6. **Robustez.** En 12 semillas y arranques, el mismo marco con solver exacto (equivale a QAOA cuando QAOA acierta) llega a 340 en 4 y su media es 354.5 (gap medio 4.3%). El límite es el vecindario de 3 vuelos, no el solver.
7. **Tiempo.** En simulador, lo clásico gana: fuerza bruta 6.9 s y simulated annealing 13.7 s llegan a 340; el híbrido con QAOA tarda 186 s. No afirmamos ventaja cuántica.
9. **Hardware real.** Una corrida N=3 (9 qubits) en ibm_kingston de IBM Quantum: N3-x-p1: 0.063 válidas (ideal 0.137, azar 0.012); N3-xy-p1: 0.254 válidas (ideal 0.789, azar 0.222).
8. **Escala.** De N=10 a N=16 el subproblema cuántico sigue en 9 qubits y la memoria pico de QGate no pasa de 0.8 MB; un QUBO directo de N=16 serían 256 qubits. Con 150 iteraciones, en N=16 el híbrido queda a 39.3% de la cota y SA a 28.8%: con N grande, 3 vuelos por paso es un vecindario chico. Las diferencias entre QAOA y el control exacto en esta tabla vienen de empates entre permutaciones óptimas del subproblema y de mejoras no óptimas que cambian la trayectoria; no son ventaja de QAOA.
<!-- FINDINGS:END -->

## 6. Limitaciones y cómo las manejamos

| Limitación | Cómo la manejamos |
|---|---|
| Simular 100 qubits es imposible (2^100 amplitudes) | Subproblemas de 9 qubits dentro de una búsqueda clásica: memoria constante |
| Penalidades: λ chico deja ganar inválidas, λ grande aplana el paisaje | λ0 con justificación analítica + barrido; mixer XY elimina la mitad de las penalidades |
| Ruido: con 1% despolarizante el mixer XY pierde casi toda su ventaja de factibilidad | Lo medimos y reportamos aparte (P(válida) ideal vs fracción válida en shots). En ibm_kingston (N=3) salió 25.4% válidas, en línea con el 25.0% simulado con ruido |
| Tiempo: en simulador el híbrido es más lento que simulated annealing | Lo decimos con números; la ganancia esperable está en hardware, no en simulación |
| El vecindario de 3 vuelos limita la calidad final | Control exacto y varias semillas para separar el efecto del solver del de la búsqueda |
| Sin óptimo conocido para N > 10 | Comparación contra la cota Gilmore-Lawler; instancias sintéticas marcadas |
| Unidades del aeropuerto | Supuestos de negocio: qap10 es un benchmark matemático |
| `stall_limit` se ajustó probando semillas sobre qap10 contra el óptimo conocido | Posible sesgo a favor de qap10; declarado en `docs/DECISIONES.md` |
| Hardware: un solo job, un solo backend (ibm_kingston, N=3) | Se reporta aparte; sin repeticiones no hay barra de error |
| En piezas de 3 vuelos, muestrear las 6 permutaciones válidas o enumerarlas supera a QAOA | Medido en `analysis/baselines.py` (`results/extra.json`); QAOA se usa para medir concentración, no para ganar |
| Reparación y pulido clásicos | Se reportan aparte del resultado crudo |

Hardware real: una sola corrida N=3 (9 qubits) en ibm_kingston de IBM Quantum (job `dbefhdom94ac738rnc00`, 5 s de QPU). Todo lo demás (N=4, N=10, escalamiento) es simulador Qiskit Aer.

## 7. Reproducir

```bash
pip install -r requirements.txt
curl -L -o data/qap10.mps.gz https://miplib.zib.de/WebData/instances/qap10.mps.gz
python tests/test_core.py && python tests/test_quantum.py && python tests/test_hybrid.py
python -m qgate.bench --mps data/qap10.mps.gz --scale 10,12,14,16      # ~15 min, escribe results/
python -m qgate.bench --mps data/qap10.mps.gz --quick                  # versión rápida
pip install python-pptx
python entrega/publicar.py           # dashboard (docs/index.html), tablas del README y PPT
```

**Hardware real de IBM Quantum (opcional).** Con la cuenta guardada una vez en la máquina
(`QiskitRuntimeService.save_account`, la API key nunca va al repo), `scripts/hardware.py` reconstruye los circuitos
QAOA de N = 3 con los ángulos ya optimizados en el simulador, comprueba que su distribución ideal coincide con
`results.json` y los envía en un solo job a la QPU menos ocupada:

```bash
pip install qiskit-ibm-runtime
python scripts/hardware.py check            # credenciales y QPUs disponibles
python scripts/hardware.py submit           # un job, 2 circuitos x 4096 shots (segundos de QPU)
python scripts/hardware.py fetch            # cuando termina: results/hardware.json
python entrega/publicar.py                  # agrega la fila de hardware al dashboard y al PPT
python scripts/hardware.py submit --fake    # misma prueba en local con el modelo de ruido de una QPU IBM
```

Un resultado de `--fake` se guarda aparte (`results/hardware_fake.json`) y nunca se presenta como hardware real.

Semilla por defecto 7 (`--seed`). Versiones, argumentos, fecha y tiempos quedan en `results.json → meta`.

## 8. Estructura

```
qgate/        instance.py  mps.py  classical.py  qubo.py  quantum.py  hybrid.py  bench.py  plots.py
tests/        pruebas de costo, MPS, QUBO/Ising, QAOA e híbrido
dashboard/    build_report.py (reporte HTML autocontenido)
results/      results.json, PNG y report.html de la corrida completa
docs/         DECISIONES.md, ESTADO.md, descripción breve, index.html (GitHub Pages)
scripts/      hardware.py (QAOA N = 3 en IBM Quantum real o en backend fake)
entrega/      QGate.pptx, guiones, checklist, generadores de PPT y tablas
examples/     corrida sobre un MPS sintético (no es qap10)
```

## 9. Créditos

[Qiskit](https://github.com/Qiskit/qiskit) y [Qiskit Aer](https://github.com/Qiskit/qiskit-aer) (IBM),
NumPy, SciPy, Matplotlib, python-pptx; slides renderizadas con Chrome headless. Identidad visual en `design/` (BRAND.md). Datos: [MIPLIB 2017, instancia qap10](https://miplib.zib.de/instance_details_qap10.html).
Reto: NTT DATA. Organizan Quantum Hub Perú, IEEE Computer Society PUCP y NTT DATA.

## Uso de IA y herramientas

Desarrollado con asistencia de Claude Code (Anthropic), supervisada por el equipo; parte del motor se preparó antes de
la jornada; los cuatro integrantes pueden explicar su funcionamiento. Las decisiones técnicas y sus pruebas quedan en
`docs/DECISIONES.md`.

Créditos: Qiskit, Qiskit Aer, qiskit-ibm-runtime, NumPy, SciPy, MIPLIB 2017 (qap10), Claude Code.

Documentos del reto: ver los documentos oficiales (bases y especificación del reto) en el portal del hackathon; no se
redistribuyen en este repositorio.