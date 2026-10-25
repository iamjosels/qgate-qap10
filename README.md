# QGate · Vuelos → puertas con QAOA híbrido

**IBM Quantum Hackathon 2026 · Categoría 5.1 Industria · Reto NTT DATA QAP10 · Track A Aeropuerto**

**Demo:** https://iamjosels.github.io/qgate-qap10/ · **PPT (plantilla oficial, con fotos):** [`entrega/QGate_final.pptx`](entrega/QGate_final.pptx) ([PDF](entrega/QGate_final.pdf)) · **Descripción breve:** [`entrega/descripcion.md`](entrega/descripcion.md)

**Dashboard.** Pestañas 00 Panorama (los tres enfoques y el cuadro comparativo), 01 QAOA (con IBM Quantum real y el
barrido de λ), 02 Aeropuerto (con la ablación del solver y el escalamiento del día 1), 03 Resultado (con los datos
validados y la reproducibilidad) y 04 Escala (etapa 3: escalamiento N ≥ 14 entre semillas y cuánto es cuántico y cuánto
clásico, sección 5b). Cada número sale de `results/results.json`, `results/hardware.json`, `results/extra.json` o
`results/final.json`.

> QAOA solo no llega a 100 qubits. Como subrutina de 9 qubits, la memoria no crece con N; la calidad
> todavía no escala. Medimos cuánto aporta cada parte. No buscamos demostrar que lo cuántico
> supere a lo clásico: medimos qué funciona, qué no y por qué.

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
se duplicaran pares saldría 48, 64 y 680 (el 680 se comprueba en código con `analysis/scale_check.py`). El 340 solo se usa para medir el gap; ningún método lo recibe.
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
Quitar o duplicar una asignación cambia el costo como mucho en λ0 y viola al menos una restricción. Es un
criterio suficiente razonable (el argumento cubre una violación; no lo demostramos para inválidas con varias),
validado con un barrido λ/λ0.

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

Control de escala (`analysis/scale_check.py`): la asignación óptima cuesta 340 contando cada par una vez (convención del archivo) y 680 contando cada par dos veces.

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
| Azar sobre las 6 permutaciones válidas (sobre las 300 piezas de la corrida QAOA de 512 shots) | 512 | - | - | 100% | 0.176 | 0.039 | - |
| Azar sobre las 6 permutaciones válidas (sobre las 300 piezas de la corrida QAOA de 8 shots) | 8 | - | - | 78% | 0.180 | 0.04 | - |

*Éxito = el solver devolvió el óptimo del subproblema (sin muestra válida cuenta como fallo). Azar P(óptimo) = muestras uniformes sobre los 27 estados con una puerta por vuelo (el espacio del estado W). Las filas de azar sobre las 6 permutaciones válidas salen de `analysis/baselines.py` (`results/extra.json`): P(acierto con k muestras) = 1 - (1 - n_óptimos/6)^k, promediado sobre las piezas. Control · subproblema exacto = enumeración de las 6 opciones.*

Robustez del híbrido del día 1 (solver exacto, 300 iteraciones, semillas 7 a 18): media 354.5 (gap medio 4.3%), mejor 340, peor 374, llega a 340 en 4 de 12.

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

### Escalamiento del día 1 (una semilla; N > 10 son instancias sintéticas)

*Corrida del día 1 con el híbrido anterior. La medición vigente es la de la etapa 3 (sección 5b): 10 semillas, híbrido en dos fases y el mismo presupuesto para todos los métodos.*

*150 iteraciones del híbrido por N: no comparable con la tabla de N=10 (300). La cota Gilmore-Lawler es débil: en N=10 SA está en el óptimo y aun así marca más de 10% contra la cota.*

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

| Experimento | Qubits | Válidas en hardware | Ideal (Aer) | Aer con ruido 1% | Azar P(válida) | P(óptimo) | Azar P(óptimo) · razón | Mejor costo | Profundidad | Compuertas 2q |
|---|---|---|---|---|---|---|---|---|---|---|
| N3-x-p1 | 9 | **0.063** | 0.137 | 0.085 | 0.012 | 0.021 | 0.0039 · 5.50× | 24 (ópt 24) | 246 | 132 |
| N3-xy-p1 | 9 | **0.254** | 0.789 | 0.250 | 0.222 | 0.087 | 0.074 · 1.18× | 24 (ópt 24) | 302 | 161 |

Un solo job, un solo backend. La simulación con 1% de ruido coincidió con el mixer XY (0.250 vs 0.254) y sobreestimó el mixer X (0.085 vs 0.063). XY queda casi en su línea base de P(válida) (0.254 vs 0.222); X queda 5.35 veces sobre la suya.

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
5. **Qué aporta QAOA (SIMULADOR, piezas de 3 vuelos en N=10).** P(óptimo) medio por pieza: 0.094 con QAOA p=2 frente a 0.039 del azar sobre los 27 estados con una puerta por vuelo (2.4 veces) y 0.180 del azar sobre las 6 permutaciones válidas. Con 8 shots, QAOA resuelve el 59% de las piezas; el azar sobre 27 estados, el 29%; el azar sobre las 6 permutaciones válidas, el 78% (calculado sobre las 300 piezas de esa corrida, `results/extra.json`); la enumeración exacta, el 100%. Costo final (una sola semilla, la 7): QAOA 372, azar sobre 27 estados 390. QAOA concentra probabilidad respecto a su espacio de partida; en piezas de 3 vuelos aún no supera a muestrear permutaciones válidas ni a enumerar las 6 opciones.
6. **Robustez (híbrido del día 1).** En 12 semillas y arranques, el mismo marco con solver exacto (equivale a QAOA cuando QAOA acierta) llega a 340 en 4 y su media es 354.5 (gap medio 4.3%). El límite es el vecindario de 3 vuelos, no el solver.
7. **Tiempo.** En simulador, lo clásico gana: fuerza bruta 6.9 s y simulated annealing 13.7 s llegan a 340; el híbrido con QAOA tarda 186 s. No afirmamos superioridad de lo cuántico.
9. **Hardware real.** Una corrida N=3 (9 qubits) en ibm_kingston de IBM Quantum: N3-x-p1: 0.063 válidas (ideal 0.137, azar 0.012); N3-xy-p1: 0.254 válidas (ideal 0.789, azar 0.222).
8. **Escala.** De N=10 a N=16 el subproblema cuántico sigue en 9 qubits y la memoria pico de QGate no pasa de 0.8 MB; un QUBO directo de N=16 serían 256 qubits. Con 150 iteraciones, en N=16 el híbrido queda a 39.3% de la cota y SA a 28.8%: con N grande, 3 vuelos por paso es un vecindario chico. Las diferencias entre QAOA y el control exacto en esta tabla vienen de empates entre permutaciones óptimas del subproblema y de mejoras no óptimas que cambian la trayectoria; no son ventaja de QAOA. Esa comparación es de una sola semilla; en la etapa 3 (sección 5b, 10 semillas, N=10 a 20) ninguna diferencia entre métodos es distinguible y los bloques QAOA no aportaron reducción de costo.
<!-- FINDINGS:END -->

## 5b. Etapa 3 (final): escalamiento N ≥ 14

**Método.** Híbrido en dos fases (`qgate/twophase.py`): (1) búsqueda local 2-swap hasta un óptimo local;
(2) un bloque de 3 vuelos (9 qubits) elegido por el selector de vecindario; si el bloque mejora se vuelve a (1), si
no, se perturba desde la mejor asignación. Selector `random` (3 vuelos al azar) o `tension` (ruleta softmax sobre
tension(i) = Σ_m F[i,m]·D[π(i),π(m)], sin repetir el trío anterior). Solvers del bloque, todos con el mismo
selector, semilla, arranque y presupuesto de B iteraciones externas: enumeración de las 6 opciones, enumeración con
desempate aleatorio entre mejoras (control de diversificación), azar sobre las 6 permutaciones válidas y QAOA (p=2,
mixer XY, ángulos del bloque anterior con respaldo a arranque frío). Controles clásicos: búsqueda 2-swap con
reinicios (sin bloque) y simulated annealing (presupuesto propio). Cargador de instancias oficiales con validaciones:
`python -m qgate.loader F.npy D.npy` (también .csv, .txt, .json, .npz, QAPLIB .dat o MPS). Ejecutor:
`python -m qgate.final --sizes 14,16,20 --seeds 10 --blocks 100 --shots 8 --procs 14` (`--official` agrega una
instancia oficial; `--estimate` mide y extrapola el tiempo).

<!-- FINAL:START -->
> **La memoria cuántica no crece con N; la calidad todavía no escala; ninguna diferencia es distinguible entre semillas; en N>10 la mejor mediana la comparten el 2-swap sin bloques y el híbrido con QAOA, junto con los otros solvers de bloque; SA no la tiene.** Los bloques QAOA no aportaron reducción de costo.

SIMULADOR (Qiskit Aer) y CPU. 10 semillas (7 a 16), B=100 iteraciones externas para todos los solvers del modo dos fases, 8 shots por bloque para QAOA y para el azar, SA 50000×3. tiempos medidos con 14 procesos en paralelo; comparables entre métodos de la misma corrida. Corrida: 31.2 min. Comando: `python -m qgate.final --sizes 14,16,20 --seeds 10 --blocks 100 --shots 8 --sa-iters 50000 --procs 14 --out results/final.json`. Fuente: `results/final.json`.

**Instancias.** qap10 (oficial (qap10), N=10, cota GL 301, mejor costo encontrado 340); synthetic-14 (sintética, N=14, cota GL 548, mejor costo encontrado 664); synthetic-16 (sintética, N=16, cota GL 524, mejor costo encontrado 670); synthetic-20 (sintética, N=20, cota GL 790, mejor costo encontrado 1038). El mejor costo encontrado no es un óptimo demostrado.

### ¿Cuánto es cuántico y cuánto clásico? (híbrido QAOA en dos fases)

| Instancia | (i) Variables cuánticas 9/N² | (ii) Movimientos swap · bloque QAOA · perturbación | (iii) Reducción de costo swap · bloque · perturbación | (iv) % tiempo en QAOA · solo Aer |
|---|---|---|---|---|
| qap10 | 9.00% | 2924 · 0 · 641 | 88806 · 0 · -85734 | 96.8% · 52.0% |
| synthetic-14 | 4.59% | 5533 · 0 · 764 | 128537 · 0 · -124262 | 91.9% · 50.2% |
| synthetic-16 | 3.52% | 5369 · 0 · 631 | 126288 · 0 · -121791 | 88.4% · 46.3% |
| synthetic-20 | 2.25% | 9586 · 0 · 823 | 290889 · 0 · -282073 | 78.8% · 42.1% |

*(ii) y (iii): movimientos aceptados y reducción de costo hasta la mejor asignación, sumados en todas las semillas y los dos selectores; las perturbaciones suben el costo, por eso restan. La atribución depende del orden de las fases: el 2-swap corre primero y se lleva las mejoras fáciles. (iv): subrutina QAOA = circuito Qiskit + simulación Aer + COBYLA clásico que la orquesta.*

**(v) Tasa de mejora de los bloques k=3 desde un óptimo local 2-swap**

| Instancia | Enumeración | Azar 6 válidas | Enumeración + desempate | QAOA |
|---|---|---|---|---|
| qap10 | 0.4% (8/2000) | 0.2% (4/2000) | 0.4% (8/2000) | 0.1% (1/2000) |
| synthetic-14 | 0.1% (3/2000) | 0.2% (4/2000) | 0.1% (3/2000) | 0.1% (1/2000) |
| synthetic-16 | 0.2% (4/2000) | 0.0% (0/2000) | 0.2% (4/2000) | 0.1% (2/2000) |
| synthetic-20 | 0.1% (1/2000) | 0.0% (0/2000) | 0.1% (1/2000) | 0.1% (1/2000) |

### Escalamiento: mediana [mín, máx] entre semillas

| Instancia | Método | Selector | Costo | Gap vs cota GL | Gap vs mejor encontrado | Tiempo (s) | Memoria (MB) | Factible |
|---|---|---|---|---|---|---|---|---|
| qap10 | SA | - | 340 [340, 348] | 13.0% | 0.0% [0.0, 2.4] | 50.1 | 0.04 | 100% |
| qap10 | 2-swap con reinicios | random | 340 [340, 350] | 13.0% | 0.0% [0.0, 2.9] | 4.9 | 0.02 | 100% |
| qap10 | 2-swap con reinicios | tension | 340 [340, 350] | 13.0% | 0.0% [0.0, 2.9] | 4.5 | 0.02 | 100% |
| qap10 | Bloque: enumeración | random | 340 [340, 340] | 13.0% | 0.0% [0.0, 0.0] | 5.0 | 0.03 | 100% |
| qap10 | Bloque: enumeración | tension | 340 [340, 340] | 13.0% | 0.0% [0.0, 0.0] | 5.0 | 0.03 | 100% |
| qap10 | Bloque: azar 6 válidas | random | 340 [340, 340] | 13.0% | 0.0% [0.0, 0.0] | 5.0 | 0.02 | 100% |
| qap10 | Bloque: azar 6 válidas | tension | 340 [340, 340] | 13.0% | 0.0% [0.0, 0.0] | 5.2 | 0.03 | 100% |
| qap10 | Bloque: enumeración + desempate | random | 340 [340, 340] | 13.0% | 0.0% [0.0, 0.0] | 5.0 | 0.02 | 100% |
| qap10 | Bloque: enumeración + desempate | tension | 340 [340, 340] | 13.0% | 0.0% [0.0, 0.0] | 4.8 | 0.03 | 100% |
| qap10 | Bloque: QAOA (p=2, XY) | random | 340 [340, 340] | 13.0% | 0.0% [0.0, 0.0] | 198.7 | 1.25 | 100% |
| qap10 | Bloque: QAOA (p=2, XY) | tension | 340 [340, 340] | 13.0% | 0.0% [0.0, 0.0] | 200.4 | 1.24 | 100% |
| synthetic-14 | SA | - | 666 [665, 669] | 21.4% | 0.2% [0.2, 0.8] | 47.8 | 0.04 | 100% |
| synthetic-14 | 2-swap con reinicios | random | 665 [664, 669] | 21.4% | 0.2% [0.0, 0.8] | 13.4 | 0.02 | 100% |
| synthetic-14 | 2-swap con reinicios | tension | 665 [664, 669] | 21.4% | 0.2% [0.0, 0.8] | 13.1 | 0.02 | 100% |
| synthetic-14 | Bloque: enumeración | random | 665 [664, 666] | 21.4% | 0.2% [0.0, 0.3] | 13.6 | 0.03 | 100% |
| synthetic-14 | Bloque: enumeración | tension | 665 [664, 669] | 21.4% | 0.2% [0.0, 0.8] | 13.6 | 0.03 | 100% |
| synthetic-14 | Bloque: azar 6 válidas | random | 665 [664, 669] | 21.4% | 0.2% [0.0, 0.8] | 13.0 | 0.02 | 100% |
| synthetic-14 | Bloque: azar 6 válidas | tension | 665 [664, 669] | 21.4% | 0.2% [0.0, 0.8] | 13.9 | 0.03 | 100% |
| synthetic-14 | Bloque: enumeración + desempate | random | 665 [664, 666] | 21.4% | 0.2% [0.0, 0.3] | 13.5 | 0.02 | 100% |
| synthetic-14 | Bloque: enumeración + desempate | tension | 665 [664, 669] | 21.4% | 0.2% [0.0, 0.8] | 13.4 | 0.03 | 100% |
| synthetic-14 | Bloque: QAOA (p=2, XY) | random | 665 [664, 669] | 21.4% | 0.2% [0.0, 0.8] | 202.6 | 0.81 | 100% |
| synthetic-14 | Bloque: QAOA (p=2, XY) | tension | 665 [664, 669] | 21.4% | 0.2% [0.0, 0.8] | 208.1 | 0.81 | 100% |
| synthetic-16 | SA | - | 674 [670, 675] | 28.6% | 0.6% [0.0, 0.7] | 45.8 | 0.04 | 100% |
| synthetic-16 | 2-swap con reinicios | random | 670 [670, 670] | 27.9% | 0.0% [0.0, 0.0] | 20.0 | 0.02 | 100% |
| synthetic-16 | 2-swap con reinicios | tension | 670 [670, 670] | 27.9% | 0.0% [0.0, 0.0] | 20.1 | 0.02 | 100% |
| synthetic-16 | Bloque: enumeración | random | 670 [670, 674] | 27.9% | 0.0% [0.0, 0.6] | 20.0 | 0.03 | 100% |
| synthetic-16 | Bloque: enumeración | tension | 670 [670, 675] | 27.9% | 0.0% [0.0, 0.7] | 19.5 | 0.04 | 100% |
| synthetic-16 | Bloque: azar 6 válidas | random | 670 [670, 674] | 27.9% | 0.0% [0.0, 0.6] | 19.9 | 0.03 | 100% |
| synthetic-16 | Bloque: azar 6 válidas | tension | 670 [670, 670] | 27.9% | 0.0% [0.0, 0.0] | 20.1 | 0.04 | 100% |
| synthetic-16 | Bloque: enumeración + desempate | random | 670 [670, 674] | 27.9% | 0.0% [0.0, 0.6] | 19.7 | 0.02 | 100% |
| synthetic-16 | Bloque: enumeración + desempate | tension | 670 [670, 675] | 27.9% | 0.0% [0.0, 0.7] | 19.3 | 0.04 | 100% |
| synthetic-16 | Bloque: QAOA (p=2, XY) | random | 670 [670, 674] | 27.9% | 0.0% [0.0, 0.6] | 194.8 | 0.81 | 100% |
| synthetic-16 | Bloque: QAOA (p=2, XY) | tension | 670 [670, 675] | 27.9% | 0.0% [0.0, 0.7] | 196.2 | 0.80 | 100% |
| synthetic-20 | SA | - | 1049 [1038, 1059] | 32.8% | 1.1% [0.0, 2.0] | 46.9 | 0.05 | 100% |
| synthetic-20 | 2-swap con reinicios | random | 1040 [1038, 1058] | 31.6% | 0.2% [0.0, 1.9] | 42.6 | 0.03 | 100% |
| synthetic-20 | 2-swap con reinicios | tension | 1040 [1038, 1058] | 31.6% | 0.2% [0.0, 1.9] | 42.6 | 0.03 | 100% |
| synthetic-20 | Bloque: enumeración | random | 1044 [1038, 1056] | 32.2% | 0.6% [0.0, 1.7] | 42.6 | 0.04 | 100% |
| synthetic-20 | Bloque: enumeración | tension | 1040 [1038, 1052] | 31.6% | 0.2% [0.0, 1.3] | 42.6 | 0.04 | 100% |
| synthetic-20 | Bloque: azar 6 válidas | random | 1040 [1038, 1060] | 31.6% | 0.2% [0.0, 2.1] | 42.5 | 0.03 | 100% |
| synthetic-20 | Bloque: azar 6 válidas | tension | 1048 [1038, 1056] | 32.7% | 1.0% [0.0, 1.7] | 43.2 | 0.04 | 100% |
| synthetic-20 | Bloque: enumeración + desempate | random | 1044 [1038, 1056] | 32.2% | 0.6% [0.0, 1.7] | 42.0 | 0.03 | 100% |
| synthetic-20 | Bloque: enumeración + desempate | tension | 1040 [1038, 1052] | 31.6% | 0.2% [0.0, 1.3] | 42.1 | 0.04 | 100% |
| synthetic-20 | Bloque: QAOA (p=2, XY) | random | 1044 [1038, 1056] | 32.2% | 0.6% [0.0, 1.7] | 217.4 | 0.81 | 100% |
| synthetic-20 | Bloque: QAOA (p=2, XY) | tension | 1040 [1038, 1052] | 31.6% | 0.2% [0.0, 1.3] | 223.2 | 0.80 | 100% |

**Veredicto por instancia** (un método se marca ganador solo si su máximo queda por debajo del mínimo de todos los demás):
- synthetic-20: no distinguible; comparten la mejor mediana: Bloque: enumeración (tension); Bloque: enumeración + desempate (tension); 2-swap con reinicios (random, tension); Bloque: QAOA (p=2, XY) (tension); Bloque: azar 6 válidas (random).
- synthetic-14: no distinguible; comparten la mejor mediana: Bloque: enumeración (random, tension); Bloque: enumeración + desempate (random, tension); 2-swap con reinicios (random, tension); Bloque: QAOA (p=2, XY) (random, tension); Bloque: azar 6 válidas (random, tension).
- qap10: no distinguible; comparten la mejor mediana: Bloque: enumeración (random, tension); Bloque: enumeración + desempate (random, tension); 2-swap con reinicios (random, tension); Bloque: QAOA (p=2, XY) (random, tension); Bloque: azar 6 válidas (random, tension); SA.
- synthetic-16: no distinguible; comparten la mejor mediana: Bloque: enumeración (random, tension); Bloque: enumeración + desempate (random, tension); 2-swap con reinicios (random, tension); Bloque: QAOA (p=2, XY) (random, tension); Bloque: azar 6 válidas (random, tension).

**Ángulos reutilizados** (synthetic-20, 40 bloques, 8 shots): evaluaciones por bloque 40.0 en frío y 40.0 reutilizando (COBYLA agota el máximo de 40 en ambos); P(óptimo) del bloque 0.093 en frío y 0.128 reutilizando; tiempo por bloque 0.24 s y 0.24 s.
<!-- FINAL:END -->

## 5c. Revisión externa del organizador (25/10)

Un organizador (QuantumHub Perú) revisó el código y reportó seis puntos. Los reprodujimos el 25/10 a las 9:15,
antes de cambiar código, y corregimos lo que cupo antes de la final. Un punto figura como corregido solo si su
verificación, indicada en la última columna, pasa.

| # | Punto reportado | Reproducción (9:15) | Estado | Verificación |
|---|---|---|---|---|
| 1 | `build_report.py` incorpora `hardware.json`, `extra.json` y `final.json` sin verificar que sean de la misma instancia o corrida | Confirmado: con un coeficiente de F cambiado los incluía sin aviso | Corregido y verificado. `results/MANIFEST.json` guarda la huella de la instancia (sha256 de N, F y D) y el sha256 de cada archivo, con atestación a posteriori para los existentes. El build excluye el archivo que no corresponde, muestra un aviso visible y sale con código 2; `--allow-mismatch` lo muestra como no verificado. `hardware.json` coincide con `results.json` en el óptimo N=3 y en la P(válida) ideal de los dos mixers (no guarda los ángulos; el manifiesto registra los de `results.json`) | `python analysis/repro_fail_closed.py` |
| 2 | `final.py` descarta `best_perm` e historial; SA tampoco guarda la permutación | Confirmado: 0 de 440 corridas con permutación | Parcialmente corregido. `final.py` guarda `best_perm` de todas las corridas y la trayectoria de movimientos aceptados de las de dos fases (SA: solo `best_perm`) en `results/final_runs.json.gz`, con su sha256 en el resumen. **Corrida de verificación reducida (2026-10-25)**: semillas 7 a 11, 220 corridas, 14 procesos, 9.9 min. `verify_final.py`: 0 discrepancias y 0 no factibles. Contra lo publicado: 220 de 220 corridas con el mismo costo y 44 de 44 grupos (instancia, método, selector) con la misma mediana y rango. Las cifras publicadas de `final.json` (10 semillas) se mantienen; sus permutaciones no se conservaron | `python analysis/verify_final.py results/final_runs.json.gz --compare results/final.json` |
| 3 | `test_core.py` línea 31 compara una expresión consigo misma | Confirmado | Corregido y verificado (los cuatro tests pasan): costo recalculado en permutaciones al azar, pares dos veces = 2x, inválidas sobre el mínimo con λ0, 24/32/340 sobre el qap10 real | `python tests/test_core.py` |
| 4 | `test_quantum.py` y `test_hybrid.py` sin aserciones de factibilidad ni de costo | Confirmado (0 y 2 aserciones) | Corregido y verificado (los cuatro tests pasan): P(válida) igual a la suma de las válidas, costo de la mejor muestra recalculado, N=3 sobre el azar; permutación válida, costo recalculado, monotonía salvo perturbación y reproducibilidad | `python tests/test_quantum.py`, `python tests/test_hybrid.py` |
| 5 | `requirements.txt` con versiones abiertas | Parcial: 2 de 6 fijas | Corregido: versiones exactas de la corrida y `requirements.lock` con el cierre de dependencias. Pendiente: instalar en un clon limpio (no se alcanzó antes de la final) | `pip install -r requirements.lock` |
| 6 | `build_report.py` mezcla datos, estilos y lógica de interfaz | Confirmado | Pendiente, limitación declarada: no se separa antes de la final para no arriesgar el HTML publicado | |

Los tiempos de la corrida de verificación se midieron con 14 procesos en paralelo y no son comparables con
los publicados.

## 6. Limitaciones y cómo las manejamos

| Limitación | Cómo la manejamos |
|---|---|
| Simular 100 qubits es imposible (2^100 amplitudes) | Subproblemas de 9 qubits dentro de una búsqueda clásica: memoria constante |
| Penalidades: λ chico deja ganar inválidas, λ grande aplana el paisaje | λ0 con justificación analítica + barrido; mixer XY elimina la mitad de las penalidades |
| Ruido: con 1% despolarizante el mixer XY pierde casi toda su ventaja de factibilidad | Lo medimos y reportamos aparte (P(válida) ideal vs fracción válida en shots). En ibm_kingston (N=3) salió 25.4% válidas, en línea con el 25.0% simulado con ruido; el mismo modelo sobreestimó el mixer X (8.5% vs 6.3%) |
| Tiempo: en simulador el híbrido es más lento que simulated annealing | Lo decimos con números; en hardware no lo medimos |
| El vecindario de 3 vuelos limita la calidad final | Control exacto y varias semillas para separar el efecto del solver del de la búsqueda |
| Sin óptimo conocido para N > 10 | Comparación contra la cota Gilmore-Lawler; instancias sintéticas marcadas |
| Unidades del aeropuerto | Supuestos de negocio: qap10 es un benchmark matemático |
| Bloques de 3 vuelos: se pueden enumerar (6 opciones) | QAOA se mide por cuánta probabilidad concentra, no porque se espere que gane a la enumeración |
| QAOA dentro del híbrido corre solo en simulador | El único hardware es un job con N=3 (ibm_kingston); el híbrido no se ejecutó en hardware |
| Etapa 3: N > 10 son instancias sintéticas, sin óptimo conocido | Gap contra la cota Gilmore-Lawler (débil) y contra el mejor costo encontrado, rotulado así |
| `stall_limit` se ajustó probando semillas sobre qap10 contra el óptimo conocido | Posible sesgo a favor de qap10; declarado en `docs/DECISIONES.md` |
| Hardware: un solo job, un solo backend (ibm_kingston, N=3) | Se reporta aparte; sin repeticiones no hay barra de error |
| En piezas de 3 vuelos, muestrear las 6 permutaciones válidas o enumerarlas supera a QAOA | Medido en `analysis/baselines.py` (`results/extra.json`); QAOA se usa para medir concentración, no para ganar |
| Reparación y pulido clásicos | Se reportan aparte del resultado crudo |

Hardware real: una sola corrida N=3 (9 qubits) en ibm_kingston de IBM Quantum (job `dbefhdom94ac738rnc00`, 5 s de QPU). Todo lo demás (N=4, N=10, escalamiento) es simulador Qiskit Aer.

## 7. Reproducir

```bash
pip install -r requirements.txt
curl -L -o data/qap10.mps.gz https://miplib.zib.de/WebData/instances/qap10.mps.gz
python tests/test_core.py && python tests/test_quantum.py && python tests/test_hybrid.py && python tests/test_final.py
python -m qgate.bench --mps data/qap10.mps.gz --scale 10,12,14,16      # ~15 min, escribe results/
python -m qgate.bench --mps data/qap10.mps.gz --quick                  # versión rápida
python analysis/baselines.py --mps data/qap10.mps.gz    # líneas base de piezas y hardware -> results/extra.json
python analysis/scale_check.py --mps data/qap10.mps.gz   # control de escala 340 / 680 -> results/extra.json
pip install python-pptx
python entrega/publicar.py           # dashboard (docs/index.html), tablas del README y PPT
python dashboard/check_panorama.py   # verifica cada número del Panorama contra los JSON
python entrega/make_ppt_oficial.py "<plantilla oficial con fotos .pptx>" entrega/QGate_final.pptx
```

Etapa 3 y auditoría:

```bash
python -m qgate.final --sizes 14,16,20 --seeds 10 --blocks 100 --shots 8 --procs 14     # results/final.json
python -m qgate.final --sizes 14,16,20 --seeds 5 --out results/final_verif.json         # guarda permutaciones en final_runs.json.gz
python analysis/verify_final.py results/final_runs.json.gz --compare results/final.json  # costo recalculado de forma independiente
python analysis/make_manifest.py         # results/MANIFEST.json: huella de instancia y sha256 de cada archivo
python analysis/repro_fail_closed.py     # el dashboard no mezcla JSON de otra instancia
pip install -r requirements.lock         # versiones exactas de la corrida
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
              twophase.py (híbrido en dos fases)  final.py (etapa 3)  loader.py (instancias oficiales)  provenance.py
tests/        costo, MPS, QUBO/Ising, QAOA, híbrido y etapa 3, con aserciones sobre factibilidad y costo recalculado
dashboard/    build_report.py (reporte HTML), panorama.py (pestaña 00), check_panorama.py (verificación de números)
analysis/     baselines.py, scale_check.py, verify_final.py, make_manifest.py, repro_fail_closed.py
results/      results.json, hardware.json, extra.json, final.json, final_verif.json, final_runs.json.gz,
              verify_final.json, MANIFEST.json, PNG y report.html
docs/         DASHBOARD.md, DECISIONES.md, ESTADO.md, descripción breve, index.html (GitHub Pages)
design/       BRAND.md y logo/ (isotipo y logo completo)
scripts/      hardware.py (QAOA N = 3 en IBM Quantum real o en backend fake)
entrega/      QGate_final.pptx/.pdf (plantilla oficial con fotos), QGate.pptx, guiones, checklist, CAMBIOS.md,
              generadores de PPT y tablas
examples/     corrida sobre un MPS sintético (no es qap10)
```

## 9. Créditos

[Qiskit](https://github.com/Qiskit/qiskit) y [Qiskit Aer](https://github.com/Qiskit/qiskit-aer) (IBM),
NumPy, SciPy, Matplotlib, python-pptx; slides renderizadas con Chrome headless. Identidad visual en `design/` (BRAND.md). Datos: [MIPLIB 2017, instancia qap10](https://miplib.zib.de/instance_details_qap10.html).
Reto: NTT DATA. Organizan Quantum Hub Perú, IEEE Computer Society PUCP y NTT DATA.

## Uso de IA y herramientas

Desarrollado con asistencia de Claude Code (Anthropic), supervisada por el equipo; los cuatro integrantes pueden explicar su funcionamiento. Las decisiones técnicas y sus pruebas quedan en
`docs/DECISIONES.md`.

Créditos: Qiskit, Qiskit Aer, qiskit-ibm-runtime, NumPy, SciPy, MIPLIB 2017 (qap10), Claude Code.

Documentos del reto: ver los documentos oficiales (bases y especificación del reto) en el portal del hackathon; no se
redistribuyen en este repositorio.
