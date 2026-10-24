# Qué muestra el dashboard de QGate

Demo: https://iamjosels.github.io/qgate-qap10/ (archivo `docs/index.html`, generado por
`dashboard/build_report.py`).

**De dónde salen los datos.** Todo número sale de `results/results.json` (corrida completa en el
simulador Qiskit Aer, semilla 7). Lo único que no es simulador es lo que viene de
`results/hardware.json`: una corrida en ibm_kingston de IBM Quantum, que siempre aparece rotulada como
hardware. Los valores citados abajo son los de la corrida actual. Si en el JSON falta un dato, el
elemento que lo usa se oculta: el dashboard nunca muestra un valor de relleno.

La página tiene una barra superior, tres escenas animadas (pestañas 01, 02 y 03) y, debajo, secciones
de detalle numeradas del 04 al 08.

---

## Barra superior

| Elemento | Qué es |
|---|---|
| Logo y "QGATE" | Isotipo de `design/BRAND.md`. El texto gris de al lado indica la escena activa. |
| Pestañas 01 QAOA · 02 AEROPUERTO · 03 RESULTADO | Cambian de escena. Al entrar a una escena con animación, empieza a reproducirse sola (salvo que el navegador pida movimiento reducido). |
| Botón play / pausa | Reproduce o detiene la animación de la escena actual. Se oculta en la escena 03, que es estática. |
| x2 | Duplica la velocidad de la animación. |
| MIXER X / MIXER XY | Solo en la escena 01: cambia el experimento QAOA que se muestra. |
| Pantalla completa | Pone las escenas en pantalla completa, para presentar. |

---

## Escena 01 · QAOA ("QAOA aprende a respetar las reglas")

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

---

## Escena 02 · Aeropuerto ("Terminal Q · Muelle A")

**Qué se reproduce.** La corrida real del híbrido QGate con QAOA en N = 10 (qap10 completo):
- semilla 7, 300 iteraciones, 512 shots por subproblema;
- entrada `qgate_lns_qaoa` de `hybrid`;
- es una repetición grabada, no un cálculo en vivo.

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
| Chip "QAOA ÓPTIMO EN 100% DE SUBPROBLEMAS (512 SHOTS)" | En los 300 subproblemas, la mejor muestra de QAOA fue el óptimo de la pieza. Con 512 muestras y solo 6 asignaciones posibles por pieza, el azar también lo logra, por eso están los dos chips siguientes. |
| Chip "P(ÓPTIMO) POR PIEZA 0.094 VS AZAR 0.039" | Probabilidad media que QAOA asigna al óptimo de cada pieza (exacta, del statevector), frente a la del azar uniforme sobre estados con una puerta por vuelo. Es la medida directa de lo que aporta QAOA (2.4 veces). |
| Chip "CON 8 SHOTS: QAOA 59% · AZAR 29%" | El mismo híbrido con solo 8 muestras por pieza: QAOA resuelve el 59% de los subproblemas y el azar el 29%. |
| Franja inferior | Datos fijos del problema: 10 vuelos, 10 puertas, 10! asignaciones, piezas de 9 qubits, convención de costo, fuente de datos y que las unidades son supuestas. |

---

## Escena 03 · Resultado ("Tres tarjetas de embarque, una por pregunta")

### Tarjetas de embarque

| Tarjeta | Pregunta que responde | Campos |
|---|---|---|
| **DATOS · VALIDADO** (MPS → F·D) | ¿Leímos bien el archivo? | Óptimos calculados por fuerza bruta en N = 3, 4 y 10 con ✓ si coinciden con los del reto (24, 32, 340); variables del MPS (4 150). Talón: CONTROL 340. |
| **QAOA · N = 4 · QISKIT** (AZAR → QAOA) | ¿QAOA mejora al azar? | Experimento con mixer XY: P(válida) 47.7%, al azar 9.4%, P(óptimo) 4.2% y CX = 292, que son las compuertas de 2 qubits tras transpilar en el simulador. Talón: 16 qubits. |
| **HÍBRIDO · N = 10 · QGATE** (AZAR → QGATE) | ¿Llegamos a una buena asignación completa? | Costo final 340, gap 0.0%, QAOA óptimo en el 100% de las piezas con 512 shots, tiempo 186 s. Talón: 9 qubits. |

### Tabla comparativa

| Columna | Qué es |
|---|---|
| MÉTODO | Fuerza bruta, simulated annealing, QAOA mixer X y XY (N = 4), QAOA en hardware (N = 3, una fila por mixer), QGate híbrido con 512 shots, QGate con 8 shots y control al azar con 8 shots. |
| N | Tamaño de la instancia de esa fila. |
| QUBITS | 0 en métodos clásicos, 16 en QAOA N = 4, 9 en hardware N = 3, "9 / subproblema" en el híbrido. |
| MEJOR COSTO VÁLIDO | Mejor asignación válida encontrada. En las filas de QAOA es la mejor entre las muestras medidas, no la más probable. |
| GAP | Contra el óptimo de **esa** instancia: 340 en N = 10, 32 en N = 4 y 24 en N = 3. |
| TIEMPO | Tiempo de pared en la CPU de la corrida. En las filas de hardware es el tiempo de QPU de todo el job (5 s para los dos circuitos), marcado "(job)". |
| DÓNDE CORRIÓ | CPU, Qiskit Aer, Qiskit Aer + CPU, o IBM Quantum · ibm_kingston. |

---

## Secciones de detalle (debajo de las escenas)

### 04 · Datos validados

- **Tabla.** N, óptimo calculado por fuerza bruta, óptimo esperado según el reto, ✓ y tiempo de cálculo.
- **Chips.** Datos de la lectura del MPS:
  - variables: 4 150 = 100 x + 4 050 y;
  - 1 820 restricciones;
  - y mapeadas: 4 050 / 4 050;
  - residuo de la factorización F·D: 0;
  - estrategia de índices usada;
  - aviso de que D es distancia Manhattan en una grilla.
- **Mapas de calor.** Color más intenso = valor más alto; al pasar el mouse se ve el valor.
  - F (amarillo): pasajeros que conectan entre cada par de vuelos.
  - D (cian): distancia entre cada par de puertas.
- **Qiskit hace / Clásico hace.** Qué parte del método corre en Qiskit y qué parte es clásica.

### 05 · ¿Cuánto aporta QAOA?

La ablación: el mismo híbrido, con las mismas iteraciones, semilla y arranque, cambiando solo cómo se
resuelve cada pieza de 3 vuelos.

| Columna | Qué es |
|---|---|
| SOLVER | QAOA con 512 shots, solver exacto (enumera las 6 opciones), azar con 512 shots, QAOA con 8 shots y azar con 8 shots. |
| SHOTS | Muestras por pieza. |
| COSTO FINAL / GAP | Resultado del híbrido completo (crudo, sin pulido). |
| PIEZAS RESUELTAS | Porcentaje de subproblemas en que el solver devolvió el óptimo de la pieza. |
| P(ÓPTIMO) POR PIEZA | Probabilidad media de muestrear el óptimo de una pieza: la de QAOA (exacta), la del azar, o 1 para el solver exacto. |
| AZAR | Referencia: probabilidad del óptimo con muestreo uniforme. |
| TIEMPO | Tiempo de pared del híbrido completo. |

Los chips de abajo muestran la robustez: el mismo marco con solver exacto en 12 semillas y arranques.
- Llega a 340 en 4 de 12, con media 354.5.
- Cada chip es una semilla con su costo final; en amarillo, las que llegan a 340.

### 05b · IBM Quantum real

Aparece solo si existe `results/hardware.json` real; un resultado `fake` se ignora. Es un job en
ibm_kingston con los ángulos ya optimizados en el simulador, 4 096 shots por circuito, N = 3 (9 qubits).

| Columna | Qué es | Mixer X | Mixer XY |
|---|---|---|---|
| VÁLIDAS EN HARDWARE | Fracción de muestras del hardware que son asignaciones válidas. | 6.3% | 25.4% |
| IDEAL (AER) | La misma probabilidad sin ruido, en el simulador. | 13.7% | 78.9% |
| AER CON RUIDO 1% | Predicción del simulador con ruido despolarizante. | 8.5% | 25.0% |
| AZAR | Muestreo uniforme. | 1.2% | 22.2% |
| P(ÓPTIMO) | Fracción de muestras con costo 24. | 2.1% | 8.7% |
| MEJOR COSTO | Mejor asignación válida medida. | 24 | 24 |
| PROFUNDIDAD / COMPUERTAS 2Q | Del circuito ya ruteado para el chip real (mucho mayores que en el simulador). | 246 / 132 | 302 / 161 |

Lectura: el hardware muestrea el óptimo, pero el ruido real borra casi toda la ventaja del mixer XY, tal
como predijo el simulador con 1% de ruido.

### 06 · Barrido de λ

- **Experimento.** Subinstancia N = 3, QAOA p = 1, para cada factor λ/λ0 ∈ {0.25, 0.5, 1, 2, 4}, con
  λ0 = 32 en N = 3.
- **Eje x.** El factor λ/λ0.
- **Eje y.** Probabilidad, de 0 a 100%.
- **Líneas.**
  - Continua: P(válida).
  - Punteada: P(óptimo).
  - Cian: mixer XY.
  - Amarillo: mixer X.

  Al pasar el mouse por un punto se ve su valor.
- **Lectura.** Con XY, P(válida) es máxima justo en λ0 (79%): λ menor deja ganar asignaciones inválidas,
  y λ mayor aplana el paisaje de costo.

### 07 · Escalamiento

- **Gráfico "Gap vs cota inferior".** Para N = 10, 12, 14 y 16, el porcentaje sobre la cota de
  Gilmore-Lawler de:
  - simulated annealing (gris);
  - QGate con solver exacto (amarillo);
  - QGate con QAOA (cian).

  N > 10 son instancias **sintéticas** (marcadas con *) sin óptimo conocido. Por eso se compara contra
  una cota inferior: un gap de 0 sería imposible de alcanzar en general.
- **Gráfico "Tiempo".** Tiempo de pared en escala logarítmica para los mismos métodos.
- **Tabla.** N, instancia, método, costo, cota, gap contra la cota, tiempo, memoria pico (Python) y
  qubits. QGate usa 150 iteraciones por N.
- **Muro de memoria.** Memoria de un statevector genérico de N² qubits (16 bytes por amplitud): N = 4 es
  1 MiB, N = 10 son 2·10^31 bytes. Es la razón de usar piezas de 9 qubits.
- **Lectura.** La parte cuántica no crece (9 qubits, menos de 1 MB). Frente a QGate con QAOA, simulated
  annealing gana en todo N, tanto en calidad como en tiempo. QGate con solver exacto es el más rápido,
  pero queda peor en calidad.

### 08 · Reproducibilidad y límites

- **Entorno.** Versiones de Python, NumPy, SciPy, Qiskit y Qiskit Aer; semilla, fecha y duración de la
  corrida; y si hubo hardware.
- **Comando.** El comando exacto para reproducir la corrida.
- **Limitaciones.** La lista que guardó el bench en `meta.limitations`, con la línea de hardware ya
  actualizada.

### Pie de página

Regla de colores de la marca:
- amarillo: señalética y lo óptimo;
- cian: todo lo que sale de Qiskit;
- naranja: inválido.

Además, créditos de librerías y datos, y el link al código.

---

## Qué tener en cuenta al presentarlo

1. Las barras de la escena 01 son probabilidades exactas del simulador, no muestras.
2. La escena 02 repite una corrida grabada, con semilla 7. En 12 semillas el mismo método llega a 340 en
   4 de 12, y la escena no muestra esa variación.
3. El "100% de piezas resueltas" depende de las 512 muestras. Lo que mide el aporte de QAOA es
   P(óptimo) por pieza (0.094 contra 0.039) y la prueba con 8 shots (59% contra 29%).
4. Todo es simulador salvo la sección 05b y las dos filas "· hardware" de la tabla de la escena 03.
5. La geometría del terminal es la de la matriz D de qap10, no la de un aeropuerto real.
