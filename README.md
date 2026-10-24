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
| **QGate híbrido** | Búsqueda en vecindarios grandes: elige 3 vuelos, arma el subproblema de 9 qubits con el resto fijo (las interacciones fijas pasan a términos lineales), lo resuelve con QAOA y acepta solo si mejora; perturba desde la mejor asignación si se estanca | `hybrid.py` |
| Control exacto | El mismo marco híbrido con el subproblema resuelto por enumeración (3! = 6), mismas iteraciones, semilla y arranque | `hybrid.py` |

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

Todo sale de [`results/results.json`](results/results.json) (simulador, nunca hardware real). Tablas
generadas con `python entrega/make_tables.py`.

<!-- RESULTS:START -->
<!-- RESULTS:END -->

### Lectura de los resultados

<!-- FINDINGS:START -->
<!-- FINDINGS:END -->

## 6. Limitaciones y cómo las manejamos

| Limitación | Cómo la manejamos |
|---|---|
| Simular 100 qubits es imposible (2^100 amplitudes) | Subproblemas de 9 qubits dentro de una búsqueda clásica: memoria constante |
| Penalidades: λ chico deja ganar inválidas, λ grande aplana el paisaje | λ0 con justificación analítica + barrido; mixer XY elimina la mitad de las penalidades |
| Ruido: con 1% despolarizante el mixer XY pierde casi toda su ventaja de factibilidad | Lo medimos y reportamos aparte (P(válida) ideal vs fracción válida en shots) |
| Tiempo: en simulador el híbrido es más lento que simulated annealing | Lo decimos con números; la ganancia esperable está en hardware, no en simulación |
| El vecindario de 3 vuelos limita la calidad final | Control exacto y varias semillas para separar el efecto del solver del de la búsqueda |
| Sin óptimo conocido para N > 10 | Comparación contra la cota Gilmore-Lawler; instancias sintéticas marcadas |
| Unidades del aeropuerto | Supuestos de negocio: qap10 es un benchmark matemático |
| Reparación y pulido clásicos | Se reportan aparte del resultado crudo |

No se ejecutó en hardware IBM real (no hubo token a tiempo); todo es Qiskit Aer.

## 7. Reproducir

```bash
pip install -r requirements.txt
curl -L -o data/qap10.mps.gz https://miplib.zib.de/WebData/instances/qap10.mps.gz
python tests/test_core.py && python tests/test_quantum.py && python tests/test_hybrid.py
python -m qgate.bench --mps data/qap10.mps.gz --scale 10,12,14,16      # ~15 min, escribe results/
python -m qgate.bench --mps data/qap10.mps.gz --quick                  # versión rápida
python dashboard/build_report.py results/results.json results/report.html
python entrega/make_tables.py        # tablas del README
pip install python-pptx && python entrega/make_ppt.py                  # PPT
```

Semilla por defecto 7 (`--seed`). Versiones, argumentos, fecha y tiempos quedan en `results.json → meta`.

## 8. Estructura

```
qgate/        instance.py  mps.py  classical.py  qubo.py  quantum.py  hybrid.py  bench.py  plots.py
tests/        pruebas de costo, MPS, QUBO/Ising, QAOA e híbrido
dashboard/    build_report.py (reporte HTML autocontenido)
results/      results.json, PNG y report.html de la corrida completa
docs/         DECISIONES.md, ESTADO.md, descripción breve, bases y reto (PDF), index.html (GitHub Pages)
entrega/      QGate.pptx, guiones, checklist, generadores de PPT y tablas
examples/     corrida sobre un MPS sintético (no es qap10)
```

## 9. Créditos

[Qiskit](https://github.com/Qiskit/qiskit) y [Qiskit Aer](https://github.com/Qiskit/qiskit-aer) (IBM),
NumPy, SciPy, Matplotlib, python-pptx, Chart.js. Datos: [MIPLIB 2017, instancia qap10](https://miplib.zib.de/instance_details_qap10.html).
Reto: NTT DATA. Organizan Quantum Hub Perú, IEEE Computer Society PUCP y NTT DATA.
