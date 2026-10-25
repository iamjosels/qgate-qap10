# Qué muestra el dashboard de QGate

Demo: https://iamjosels.github.io/qgate-qap10/ (archivo `docs/index.html`, copia de `results/report.html`,
generado por `python dashboard/build_report.py results/results.json results/report.html`).

**De dónde salen los datos.** Cada número sale de uno de estos cuatro archivos:

| Archivo | Qué contiene | Dónde se usa |
|---|---|---|
| `results/results.json` | Corrida completa del día 1 en el simulador Qiskit Aer (semilla 7, 18.5 min) | Pestañas 00 a 03 y secciones de detalle 04 a 08 |
| `results/hardware.json` | Un job en ibm_kingston de IBM Quantum (N = 3), siempre rotulado como hardware | Panorama, sección 05b y dos filas de la tabla de 03 |
| `results/extra.json` | Líneas base (azar sobre las 6 permutaciones válidas, azar de P(óptimo) del hardware) y control de escala del MPS | Secciones 04, 05 y 05b |
| `results/final.json` | Etapa 3: escalamiento con 10 semillas, híbrido en dos fases (simulador) | Pestaña 04 y fila "Escala" y frase final del Panorama |

Si en un JSON falta un dato, el elemento que lo usa se oculta: el dashboard nunca muestra un valor de
relleno. `python dashboard/check_panorama.py` verifica que cada número del Panorama esté respaldado por
`results.json`, `hardware.json` o `final.json`. Todo es simulador salvo lo que viene de `hardware.json`.

**Estructura.** Una barra superior con cinco pestañas. Cada pestaña muestra una escena y, debajo, solo
las secciones de detalle de su enfoque, para que cada dato aparezca una sola vez:

| Pestaña | Escena | Secciones de detalle debajo |
|---|---|---|
| 00 PANORAMA | Tres enfoques, un problema | (ninguna) |
| 01 QAOA | QAOA aprende a respetar las reglas | 05b IBM Quantum real · 06 Barrido de λ |
| 02 AEROPUERTO | Terminal Q · Muelle A | 05 ¿Cuánto aporta QAOA? · 07 Escalamiento · día 1 |
| 03 RESULTADO | Tres tarjetas de embarque | 04 Datos validados · 08 Reproducibilidad y límites |
| 04 ESCALA | Etapa 3 · escalamiento | (todo está en la escena) |

---

## Barra superior

| Elemento | Qué es |
|---|---|
| Logo y "QGATE" | Isotipo de `design/BRAND.md`. Cada escena tiene un rótulo de modo (por ejemplo "MODO DEMO · TRACK A AEROPUERTO" o "ETAPA 3 · ESCALAMIENTO · SIMULADOR"), pero está oculto desde la simplificación del dashboard: no se ve en ninguna pestaña. |
| Pestañas 00 a 04 | Cambian de escena. Al entrar a una escena con animación (01 y 02), empieza a reproducirse sola, salvo que el navegador pida movimiento reducido. |
| Botón play / pausa y x2 | Reproducen, detienen o duplican la velocidad de la animación. Solo aparecen en 01 y 02. |
| MIXER X / MIXER XY | Solo en 01: cambia el experimento QAOA que se muestra. |
| Pantalla completa | Pone la escena en pantalla completa, para presentar. |

---

## 00 · Panorama ("Tres enfoques, un problema")

Vista de una pantalla para presentar. Se genera en Python (`dashboard/panorama.py`) y no en JavaScript,
para que `check_panorama.py` pueda verificar cada número.

- **Flujo de arriba.** MPS qap10 → F y D (con los óptimos de control 24 · 32 · 340) → los tres enfoques →
  comparación.
- **Tres columnas**, cada una con un número grande, dos líneas de apoyo y un botón "Ver detalle →":

| Columna | Número grande | Líneas | Botón lleva a |
|---|---|---|---|
| CLÁSICO | 340: óptimo exacto en 6.9 s | SA 340 en 13.7 s; cota 301 (Gilmore-Lawler) | 03 Resultado |
| CUÁNTICO | ×112: más asignaciones válidas que el azar (QAOA mixer X, N = 4) | XY 47.7% vs 9.4% azar; ibm_kingston N = 3: X 6.3% vs 1.2% azar | 01 QAOA |
| HÍBRIDO | 9: qubits por pieza, en cualquier N | 8 muestras: QAOA 59% vs 29% azar de 27 estados; solver exacto: 340 en 4 de 12 semillas | 02 Aeropuerto |

- **Cuadro comparativo.** Seis filas por tres enfoques. Cada celda lleva una marca: ✓ ventaja, ✗ desventaja,
  ~ parcial.

| Fila | Clásico | Cuántico | Híbrido | Fuente |
|---|---|---|---|---|
| Calidad N=10 | ✓ 340, gap 0.0% | ✗ N=10: 100 qubits | ~ 340 (semilla 7); exacto 4/12 semillas | results.json |
| Tiempo | ✓ 6.9 s | ~ 19.3 s (N=4) | ✗ 186.0 s | results.json |
| Qubits | ✓ 0 | ✗ 100 (N=10) | ✓ 9 | results.json |
| Escala N=20, 10 semillas | ✓ SA 32.8% sobre la cota, 47 s | ✗ 400 qubits | ~ 31.6% sobre la cota, 223 s; no distinguible | final.json |
| Ruido | ✓ no aplica | ✗ XY 25.4% vs 22.2% azar (ibm_kingston) | ~ no medido | hardware.json |
| Garantiza óptimo | ✓ sí (fuerza bruta) | ✗ P(óptimo) 4.2% | ✗ exacto: 4/12 semillas | results.json |

  En la fila "Escala", los porcentajes son la mediana entre 10 semillas del gap contra la cota
  Gilmore-Lawler en la instancia sintética de N = 20; la columna híbrida es el híbrido en dos fases con QAOA
  y selector por tensión. "No distinguible": los rangos entre semillas se solapan.
- **Frase final.** Se calcula desde `final.json`: "De N=10 a 20: el clásico es más rápido y ninguna
  diferencia de calidad es distinguible entre semillas; los bloques QAOA no aportaron reducción de costo;
  QAOA concentra probabilidad sobre el azar; el híbrido escala en memoria, no en calidad."

---

## 01 · QAOA ("QAOA aprende a respetar las reglas")

**Qué experimento es.** QAOA sobre la subinstancia N = 4 de qap10 (primeras 4 filas y columnas de F y D),
con 16 qubits (`x_ij`, 4 vuelos × 4 puertas), p = 1 y sin ruido. Son las entradas `N4-xy-p1` y
`N4-x-p1` de `quantum` en `results.json`. Es una corrida en simulador.

**Frase de arriba.** "Con 16 qubits hay 65 536 combinaciones y solo 24 son asignaciones válidas":
2^16 bitstrings posibles, y 4! = 24 cumplen "una puerta por vuelo y un vuelo por puerta".

### Histograma (64 barras)

- **Qué es cada barra.** Una configuración fija de los 16 qubits (un bitstring). Hay 64:
  - las **24 asignaciones válidas**;
  - las **40 inválidas más probables**, al inicio o al final de la optimización.

  No están las 65 536: el resto tiene probabilidad muy baja y no se vería.
- **Altura.** La probabilidad **exacta** de esa configuración, calculada con el statevector de Aer. No es
  un conteo de shots. La escala está normalizada al máximo de toda la animación, para que las alturas se
  puedan comparar entre cuadros. Al pasar el mouse por una barra se ve su probabilidad.
- **Colores.**
  - Naranja oscuro: inválida (rompe una regla).
  - Cian: válida.
  - Amarillo: óptima, con costo 32. En N = 4 hay **2 permutaciones óptimas**, por eso hay dos barras amarillas.
- **Animación.** Cada cuadro es un paso del optimizador clásico COBYLA mientras ajusta los ángulos γ y β.
  - Se repitió de forma determinista el mismo COBYLA del mejor arranque que usó el bench.
  - Se guardaron hasta 60 cuadros: de 200 evaluaciones con mixer XY, y de 57 con mixer X (convergió antes).
  - El último cuadro corresponde a los ángulos finales, y su P(válida) es idéntica a la reportada en
    `results.json` (eso se verificó al generar los cuadros).
- **Pie del histograma.** Describe el conjunto de barras. "SHOTS 4096" es la cantidad de muestras con
  que se midió ese experimento después de optimizar; las barras no son esas muestras sino la
  probabilidad exacta.
- **Barra de progreso "EVALUACIÓN k / n".** En qué evaluación de la función objetivo (CVaR de la energía)
  va el optimizador. Se puede hacer clic para saltar.

### Tarjetas de la derecha

| Tarjeta | Qué muestra |
|---|---|
| **P(asignación válida)** (cian, grande) | Suma de la probabilidad de las 24 asignaciones válidas en el cuadro actual. Al final: 47.7% con XY y 4.1% con X. |
| "vs X% al azar con el mismo mixer" | Probabilidad de sacar una válida al azar en el espacio que genera cada mixer. Con X: 24 / 65 536 = 0.04%. Con XY: 24 / 4^4 = 9.4%, porque el estado W ya pone exactamente un 1 por fila (4^4 = 256 estados posibles). |
| **P(asignación óptima)** (amarilla) | Probabilidad de las 2 asignaciones de costo 32 en el cuadro actual. Al final: 4.2% con XY y 0.35% con X. |
| "óptimo de control N = 4: 32" | El óptimo de la subinstancia, calculado por fuerza bruta. |
| **Una fila del circuito** | Esquema, no el circuito literal: los 4 qubits del vuelo V01 (uno por puerta) y las capas que les aplica QAOA. Con XY: preparación del estado W, capa de costo (γ), mixer XY (β) y medición. Con X: Hadamard, costo (γ), rotación X (β) y medición. |
| Ondas cian | Motivo visual de la marca (lo cuántico va en cian); no representan datos. |

### Detalle 05b · IBM Quantum real

Aparece solo si existe `results/hardware.json` real; un resultado `fake` se ignora.

- **Texto de arriba.** Un solo job en un solo backend (ibm_kingston, job `dbefhdom94ac738rnc00`, 5 s de QPU),
  N = 3 (9 qubits), con los ángulos ya optimizados en el simulador. La simulación con 1% de ruido coincidió
  con el mixer XY (25.0% vs 25.4%) y sobreestimó el mixer X (8.5% vs 6.3%). XY queda casi en su línea base
  de P(válida) (25.4% vs 22.2%); X queda 5.35 veces sobre la suya (6.3% vs 1.2%).
- **Tabla.** 4 096 shots por circuito.

| Columna | Qué es | Mixer X | Mixer XY |
|---|---|---|---|
| VÁLIDAS EN HARDWARE | Fracción de muestras del hardware que son asignaciones válidas. | 6.3% | 25.4% |
| IDEAL (AER) | La misma probabilidad sin ruido, en el simulador. | 13.7% | 78.9% |
| AER CON RUIDO 1% | Predicción del simulador con ruido despolarizante. | 8.5% | 25.0% |
| AZAR P(VÁLIDA) | Muestreo uniforme en el espacio de cada mixer. | 1.2% | 22.2% |
| P(ÓPTIMO) | Fracción de muestras con costo 24. | 2.1% | 8.7% |
| AZAR P(ÓPTIMO) · RAZÓN | P(óptimo) del azar en el mismo espacio y cuántas veces lo supera el hardware (`extra.json`). | 0.39% (5.50×) | 7.41% (1.18×) |
| MEJOR COSTO | Mejor asignación válida medida. | 24 (ópt 24) | 24 (ópt 24) |
| PROFUNDIDAD / COMPUERTAS 2Q | Del circuito ya ruteado para el chip real (mucho mayores que en el simulador). | 246 / 132 | 302 / 161 |

- **Lectura.** El hardware muestrea el óptimo, pero el ruido real borra casi toda la ventaja del mixer XY. La
  simulación con 1% de ruido coincidió con XY (25.0% vs 25.4%) y sobreestimó X (8.5% vs 6.3%).

### Detalle 06 · Barrido de λ

- **Experimento.** Subinstancia N = 3, QAOA p = 1, para cada factor λ/λ0 ∈ {0.25, 0.5, 1, 2, 4}, con
  λ0 = 32 en N = 3. λ0 es el mayor aporte posible de una asignación: criterio suficiente razonable,
  validado con este barrido.
- **Eje x.** El factor λ/λ0. **Eje y.** Probabilidad, de 0 a 100%.
- **Líneas.** Continua: P(válida). Punteada: P(óptimo). Cian: mixer XY. Amarillo: mixer X. Al pasar el
  mouse por un punto se ve su valor.
- **Lectura.** Con XY, P(válida) es máxima justo en λ0 (79%): λ menor deja ganar asignaciones inválidas,
  y λ mayor aplana el paisaje de costo.

---

## 02 · Aeropuerto ("Terminal Q · Muelle A")

**Qué se reproduce.** La corrida real del híbrido QGate con QAOA en N = 10 (qap10 completo):
- semilla 7, 300 iteraciones, 512 shots por subproblema;
- entrada `qgate_lns_qaoa` de `hybrid` en `results.json`;
- es una repetición grabada, no un cálculo en vivo.

Un aviso arriba del mapa lo dice: "Repetición grabada, semilla 7; no es el caso típico (ver 05: con solver
exacto, 4 de 12 semillas llegan a 340)".

Se reproducen sus **135 eventos**, cada uno con la asignación completa en ese momento:
- 1 de inicio;
- 108 movimientos aceptados;
- 26 perturbaciones.

### Mapa del terminal

- **Posición de las puertas.** Las 10 puertas están en la grilla que reproduce exactamente la matriz D:
  - en qap10, D es la distancia Manhattan entre puertas ubicadas en filas de 4, 4 y 2;
  - el script deduce esa grilla de D y la dibuja tal cual;
  - si D no fuera una grilla, se usaría una proyección MDS.

  "Terminal Q · Muelle A" es solo el nombre de la escena: no es un aeropuerto real, las unidades son
  supuestas.
- **Letrero amarillo (P01 a P10).** La puerta.
- **Ficha debajo (V01 a V10).** El vuelo asignado a esa puerta en el evento actual.
- **Curvas amarillas.** Una por cada par de vuelos que comparten pasajeros (F > 0), dibujada entre las
  puertas donde están esos dos vuelos.
  - El **grosor** es proporcional a F, los pasajeros en conexión.
  - La **intensidad** es proporcional a F × D, lo que ese par aporta al costo.

  Una buena asignación deja las curvas gruesas cortas y apagadas.
- **Línea cian punteada y ficha con borde cian.** En un movimiento aceptado, los vuelos que cambiaron de
  puerta. La línea va de la puerta anterior a la nueva. Ese cambio es la solución que dio QAOA al
  subproblema de 3 vuelos (9 qubits), y se aceptó porque bajó el costo. Las perturbaciones son clásicas
  y no se marcan en cian.
- **Barra "ITERACIÓN k / 300".** En qué iteración del híbrido ocurrió el evento que se está mostrando.
  Se puede hacer clic para saltar.

### Tablero SALIDAS

| Columna | Qué es |
|---|---|
| VUELO | V01 a V10. |
| PUERTA | La puerta actual del vuelo. Las letras usan animación split-flap (fichas que giran). |
| ESTADO | MOVIDO (cian): cambió de puerta por QAOA en este evento. PERTURBADO: cambió por una perturbación clásica. EN POSICIÓN: no cambió. |
| "VUELTA k / 300" | Igual que la barra: la iteración del evento. |

### Costo total

| Elemento | Qué es |
|---|---|
| Número en fichas split-flap | Costo C de la asignación actual, con cada par contado una vez: C = Σ_{i<k} F_ik · D_{puerta(i), puerta(k)}. Es el costo actual, no el mejor histórico: después de una perturbación puede subir. Empieza en 486 y termina en 340. |
| "ÓPTIMO 340" | Óptimo de referencia de qap10. Solo se usa para medir; ningún método lo recibe. |
| GAP x% | 100 · (C − 340) / 340, sobre la asignación actual, que siempre es válida. |
| Barra amarilla | Cuánto se avanzó desde el costo inicial hasta 340: (486 − C) / (486 − 340). |
| Chip "9 QUBITS POR SUBPROBLEMA" | Tamaño fijo de la pieza cuántica: 3 vuelos × 3 puertas. |
| Chip "QAOA ÓPTIMO EN 100% DE SUBPROBLEMAS (512 SHOTS)" | En los 300 subproblemas, la mejor muestra de QAOA fue el óptimo de la pieza. Con 512 muestras y solo 6 asignaciones posibles por pieza, el azar también lo logra: por eso la sección 05 compara con pocas muestras. |
| Chip "P(ÓPTIMO) POR PIEZA 0.094 VS AZAR 0.039" | Probabilidad media que QAOA asigna al óptimo de cada pieza (exacta, del statevector), frente a la del azar uniforme sobre los 27 estados con una puerta por vuelo. Es la medida directa de lo que concentra QAOA (2.4 veces). |
| Franja inferior | Datos fijos del problema: 10 vuelos, 10 puertas, 10! asignaciones, piezas de 9 qubits, convención de costo, fuente de datos y que las unidades son supuestas. |

### Detalle 05 · ¿Cuánto aporta QAOA?

La ablación: el mismo híbrido con distintos solvers del subproblema, mismas iteraciones, semilla (una sola,
la 7) y arranque, cambiando solo cómo se resuelve cada pieza de 3 vuelos.

| Solver | Shots | Costo final | Gap | Piezas resueltas | P(óptimo) por pieza | Azar (27 estados) | Tiempo |
|---|---|---|---|---|---|---|---|
| QAOA | 512 | 340 | 0.0% | 100% | 0.094 | 0.039 | 186.0 s |
| Enumeración exacta (6 opciones) | - | 340 | 0.0% | 100% | 1.000 | 0.039 | 0.4 s |
| Azar (27 estados con una puerta por vuelo) | 512 | 340 | 0.0% | 100% | - | 0.039 | 0.6 s |
| QAOA | 8 | 372 | 9.4% | 59% | 0.096 | 0.040 | 208.3 s |
| Azar (27 estados con una puerta por vuelo) | 8 | 390 | 14.7% | 29% | - | 0.039 | 0.7 s |
| Azar (6 permutaciones válidas) | 512 | - | - | 100% | 0.176 | 0.039 | - |
| Azar (6 permutaciones válidas) | 8 | - | - | 78% | 0.180 | 0.040 | - |

- Las dos últimas filas salen de `extra.json`: se calculan sobre las 300 piezas de la corrida QAOA con ese
  número de shots, sin correr el híbrido completo (por eso no tienen costo ni tiempo).
- **Lectura** (texto debajo de la tabla): QAOA concentra probabilidad respecto a su espacio de partida; en
  piezas de 3 vuelos aún no supera a muestrear permutaciones válidas ni a enumerar las 6 opciones.
- **Chips de robustez.** El mismo marco con solver exacto en 12 semillas y arranques: media 354.5, llega a
  340 en 4/12. Cada chip es una semilla con su costo final; en amarillo, las que llegan a 340.

### Detalle 07 · Escalamiento · día 1

Corrida del día 1 (`results.json`): una semilla y el híbrido anterior. Un aviso con borde amarillo dice que
la medición vigente es la de la etapa 3 (10 semillas, híbrido en dos fases, mismo presupuesto para todos) y
un botón "Ver 04 ESCALA →" lleva a esa pestaña.

- **Gráfico "Gap vs cota inferior (%)".** Para N = 10, 12, 14 y 16, el porcentaje sobre la cota de
  Gilmore-Lawler de simulated annealing (gris), QGate con solver exacto (amarillo) y QGate con QAOA (cian).
  N > 10 son instancias **sintéticas** (marcadas con *) sin óptimo conocido.
- **Gráfico "Tiempo (s, escala log)".** Tiempo de pared para los mismos métodos.
- **Tabla.** N, instancia, método, costo, cota, gap contra la cota, tiempo, memoria pico (Python) y
  qubits. QGate usa 150 iteraciones por N (no comparable con 02, que usa 300).
- **Muro de memoria.** Memoria de un statevector genérico de N² qubits (16 bytes por amplitud): N = 4 es
  1 MiB, N = 10 son 2·10^31 bytes. Es la razón de usar piezas de 9 qubits.
- **Lectura.** La parte cuántica no crece (9 qubits, menos de 1 MB). En esa corrida de una semilla,
  simulated annealing ganó a QGate con QAOA en todo N, en calidad y en tiempo. Con una sola semilla no se
  puede saber si la diferencia de calidad es real: la pestaña 04 la mide con 10 semillas y no encuentra
  diferencias distinguibles.

---

## 03 · Resultado ("Tres tarjetas de embarque, una por pregunta")

### Tarjetas de embarque

| Tarjeta | Pregunta que responde | Campos |
|---|---|---|
| **DATOS · VALIDADO** (MPS → F·D) | ¿Leímos bien el archivo? | Óptimos calculados por fuerza bruta en N = 3, 4 y 10 con ✓ si coinciden con los del reto (24, 32, 340); variables del MPS (4 150). Talón: CONTROL 340. |
| **QAOA · N = 4 · QISKIT** (AZAR → QAOA) | ¿QAOA mejora al azar? | Mixer XY: P(válida) 47.7%, al azar 9.4%, P(óptimo) 4.2% y CX = 292 (compuertas de 2 qubits tras transpilar en el simulador). Talón: 16 qubits. |
| **HÍBRIDO · N = 10 · QGATE** (AZAR → QGATE) | ¿Llegamos a una buena asignación completa? | Semilla 7 · costo 340; 12 semillas (solver exacto) que llegan a 340: 4; media · mejor · peor: 354.5 · 340 · 374; gap medio 4.3%. Talón: 9 qubits. |

### Tabla comparativa

| Columna | Qué es |
|---|---|
| MÉTODO | Fuerza bruta, simulated annealing, QAOA mixer X y XY (N = 4), QAOA en hardware (N = 3, una fila por mixer) y QGate híbrido con la semilla 7. Cada fila lleva el chip de su enfoque (clásico, cuántico, híbrido). |
| N | Tamaño de la instancia de esa fila. |
| QUBITS | 0 en métodos clásicos, 16 en QAOA N = 4, 9 en hardware N = 3, "9 / subproblema" en el híbrido. |
| MEJOR COSTO VÁLIDO | Mejor asignación válida encontrada. En las filas de QAOA es la mejor entre las muestras medidas, no la más probable. |
| GAP | Contra el óptimo de **esa** instancia: 340 en N = 10, 32 en N = 4 y 24 en N = 3. |
| TIEMPO | Tiempo de pared de la corrida. En las filas de hardware es el tiempo de QPU de todo el job (5 s para los dos circuitos), marcado "(job)". |
| DÓNDE CORRIÓ | CPU, Qiskit Aer, Qiskit Aer + CPU, o IBM Quantum · ibm_kingston. |

Debajo, una nota: las filas de QAOA son valores crudos de las muestras, sin reparación clásica; "mejor
costo válido" es el costo C de una asignación válida, no la energía penalizada del QUBO.

### Detalle 04 · Datos validados

- **Tabla.** N, óptimo calculado por fuerza bruta, óptimo esperado según el reto, ✓ y tiempo de cálculo.
- **Chips.** Variables: 4 150 = 100 x + 4 050 y; 1 820 restricciones; y mapeadas: 4 050 / 4 050; residuo de
  la factorización SVD: 0; estrategia de índices usada; aviso de que D es distancia Manhattan en una grilla.
- **Mapas de calor.** Color más intenso = valor más alto; al pasar el mouse se ve el valor. F (amarillo):
  pasajeros que conectan entre cada par de vuelos. D (cian): distancia entre cada par de puertas.
- **Cómo se recuperaron los coeficientes del MPS** (desde `extra.json`, `analysis/scale_check.py`):
  1. Las 20 restricciones con lado derecho 1 y coeficientes 1 son las de asignación: sus variables son las 100 x.
  2. Esas 20 filas se parten en dos familias de 10 (vuelos y puertas); cada x está una vez en cada familia, y eso da su índice (i, j).
  3. Cada una de las 4 050 variables y aparece en filas de enlace junto a exactamente dos x: su coeficiente objetivo es F_ik · D_jl.
  4. Con eso se arma el tensor T y se factoriza en F y D por SVD de rango 1 (residuo 0).
  5. El orden de índices se elige entre las candidatas con la que reproduce 24 · 32 · 340.
  6. Control de escala: la asignación óptima cuesta 340 contando cada par una vez y 680 contándolo dos veces.
- **Qiskit hace / Clásico hace.** Qué parte del método corre en Qiskit y qué parte es clásica.

### Detalle 08 · Reproducibilidad y límites

- **Entorno.** Versiones de Python, NumPy, SciPy, Qiskit y Qiskit Aer; semilla 7, fecha y duración de la
  corrida (18.5 min); y que el hardware IBM se reporta aparte.
- **Comando.** El comando exacto para reproducir la corrida del día 1.
- **Limitaciones.** La lista que guardó el bench en `meta.limitations`, más las líneas "¿Por qué QAOA aquí?":
  las piezas de 3 vuelos se pueden enumerar; con 8 muestras QAOA resuelve 59% de las piezas, el azar sobre
  las 6 permutaciones válidas 78% y la enumeración 100%; la memoria cuántica no crece con N y la calidad
  todavía no escala (resumen de la etapa 3 desde `final.json`); en hardware el ruido borra casi toda la
  ventaja del mixer XY.

---

## 04 · Escala ("Etapa 3 · escalamiento")

Lee `results/final.json`, generado por `python -m qgate.final` (SIMULADOR Qiskit Aer y CPU). Instancias:
qap10 (oficial, N = 10) y tres sintéticas (N = 14, 16 y 20); 10 semillas (7 a 16); B = 100 iteraciones
externas y 8 shots por bloque para todos los métodos del modo dos fases. Si falta `final.json`, la pestaña
no aparece.

- **Frase de arriba.** Se calcula desde el JSON. Hoy dice: "La memoria cuántica no crece con N; la calidad
  todavía no escala; ninguna diferencia es distinguible entre semillas; en N>10 la mejor mediana la
  comparten el 2-swap sin bloques y el híbrido con QAOA, junto con los otros solvers de bloque; SA no la
  tiene. Los bloques QAOA no aportaron reducción de costo."
- **Metadatos.** Semillas, B, shots por bloque, presupuesto de SA (50 000 × 3) y nota sobre tiempos: se
  midieron con 14 procesos en paralelo y solo son comparables dentro de la misma corrida.
- **¿Cuánto es cuántico y cuánto clásico?** Una fila por instancia, para el híbrido QAOA en dos fases:

| Columna | Qué es | qap10 | N=14 | N=16 | N=20 |
|---|---|---|---|---|---|
| (i) Variables cuánticas 9/N² | Fracción de variables x que entra al circuito: los 9 qubits de un bloque | 9.00% | 4.59% | 3.52% | 2.25% |
| (ii) Movimientos swap · bloque QAOA · perturbación | Movimientos aceptados hasta la mejor asignación, por origen, sumados en todas las semillas y los 2 selectores | 2924 · 0 · 641 | 5533 · 0 · 764 | 5369 · 0 · 631 | 9586 · 0 · 823 |
| (iii) Reducción de costo swap · bloque · perturbación | Cuánto bajó el costo por origen; las perturbaciones suben el costo, por eso restan | 88806 · 0 · −85734 | 128537 · 0 · −124262 | 126288 · 0 · −121791 | 290889 · 0 · −282073 |
| (iv) % tiempo en QAOA · solo Aer | Fracción del tiempo de pared en la subrutina QAOA (circuito + Aer + COBYLA) y solo en la simulación Aer | 96.8% · 52.0% | 91.9% · 50.2% | 88.4% · 46.3% | 78.8% · 42.1% |

  La atribución depende del orden de las fases: el 2-swap corre primero y se lleva las mejoras fáciles.
- **(v) Tasa de mejora de los bloques k=3 desde un óptimo local 2-swap.** Cuántos de 2000 bloques mejoran,
  por solver: enumeración 1 a 8, azar sobre las 6 válidas 0 a 4, enumeración con desempate 1 a 8, QAOA 1 o 2.
  Desde un óptimo local 2-swap casi no quedan mejoras de 3 vuelos, para ningún solver.
- **Tabla de escalamiento.** Por instancia, método y selector: costo mediana [mín, máx] entre semillas, gap
  contra la cota Gilmore-Lawler, gap contra el mejor costo encontrado (no es un óptimo demostrado), tiempo,
  memoria y fracción factible (100% en todas). Métodos: SA, 2-swap con reinicios, y bloques de enumeración,
  azar sobre 6 válidas, enumeración + desempate y QAOA, cada uno con selector `random` y `tension`.
  - Un método se marca "mejor (distinguible)" y su costo se colorea solo si su máximo queda por debajo del
    mínimo de todos los demás. No pasó en ninguna instancia.
  - Todas las filas empatadas en la mejor mediana llevan "mejor mediana (empate), no distinguible". En qap10
    empatan todas las filas (340). En N = 14 y 16, todas salvo SA. En N = 20, seis filas: al menos una
    variante de cada método salvo SA, entre ellas el híbrido QAOA con selector por tensión (1040).
- **Ángulos reutilizados** (N = 20, 40 bloques, 8 shots): 40 evaluaciones por bloque en frío y 40
  reutilizando (COBYLA llega a su máximo en ambos); P(óptimo) del bloque 0.093 en frío y 0.128
  reutilizando; 0.24 s por bloque en ambos.
- **Lectura.** Ninguna diferencia entre métodos es distinguible entre semillas. El híbrido con QAOA empata
  con el 2-swap porque la mejora la hace el 2-swap: los bloques QAOA no aportan reducción de costo y se
  llevan entre 79% y 97% del tiempo de pared.

---

## Pie de página

Regla de colores de la marca: amarillo para la señalética y lo óptimo; cian para todo lo que sale de
Qiskit; naranja para lo inválido. Además, créditos de librerías y datos, y el link al código.

---

## Qué tener en cuenta al presentarlo

1. Las barras de la escena 01 son probabilidades exactas del simulador, no muestras.
2. La escena 02 repite una corrida grabada, con semilla 7. En 12 semillas el mismo marco con solver exacto
   llega a 340 en 4 de 12; el aviso de la escena lo dice.
3. El "100% de piezas resueltas" depende de las 512 muestras. Lo que mide el aporte de QAOA es P(óptimo)
   por pieza (0.094 contra 0.039) y la prueba con 8 shots (59% contra 29% del azar de 27 estados, y 78% del
   azar sobre las 6 permutaciones válidas).
4. Todo es simulador salvo la sección 05b, las dos filas "· hardware" de la tabla de 03 y la línea de
   ibm_kingston del Panorama.
5. La geometría del terminal es la de la matriz D de qap10, no la de un aeropuerto real.
6. La sección 07 es del día 1 (una semilla). La medición de escala que cuenta es la pestaña 04 (10
   semillas). Las instancias de N > 10 son sintéticas.
7. En la pestaña 04, "no distinguible" significa que los rangos entre semillas se solapan: ningún método se
   presenta como ganador.
