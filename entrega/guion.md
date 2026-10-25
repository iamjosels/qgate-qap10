# Guion del pitch (2:30 a 3:00)

Una slide por bloque. Hablar con números, sin leer la pantalla. Todos los números salen de
`results/results.json` (simulador Qiskit Aer), `results/hardware.json` (una corrida N=3 en ibm_kingston de IBM Quantum)
y `results/final.json` (etapa 3: escalamiento con 10 semillas, simulador).

| Tiempo | Slide | Quién | Texto |
|---|---|---|---|
| 0:00 a 0:20 | 1 Portada | Integrante 1 | "Somos QGate. En un aeropuerto, los pasajeros en conexión caminan entre puertas. Asignamos 10 vuelos a 10 puertas para que caminen lo menos posible, usando QAOA de Qiskit dentro de una búsqueda clásica." |
| 0:20 a 0:40 | 2 Problema | Integrante 1 | "Hay 3.6 millones de asignaciones. El costo suma pasajeros por distancia, cada par una vez. A la izquierda una asignación al azar, a la derecha la nuestra: las conexiones gruesas quedan cortas. Los datos son el benchmark qap10, las unidades son supuestos." |
| 0:40 a 1:05 | 3 Datos | Integrante 2 | "El MPS viene linealizado: 4150 variables. Reconstruimos flujos y distancias sin depender de nombres y verificamos la escala: N=3 da 24, N=4 da 32 y la instancia completa 340, como pide el reto. El 340 solo lo usamos para medir el gap." |
| 1:05 a 1:30 | 4 Qiskit | Integrante 3 | "Pasamos a QUBO, luego a Ising, y corremos QAOA en Qiskit Aer. Comparamos dos ansatz: mixer X, donde todo es penalidad, y mixer XY con estado W, que deja cada vuelo en una sola puerta. En N=4, QAOA con mixer X muestrea asignaciones válidas 112 veces más que el azar." |
| 1:30 a 1:50 | 5 Límites | Integrante 3 | "N=10 completo serían 100 qubits: imposible de simular. Justificamos λ y lo validamos con un barrido. Y medimos el ruido: con 1% de ruido el mixer XY pierde casi toda su ventaja de factibilidad." |
| 1:50 a 2:25 | 6 Híbrido | Integrante 4 | "Por eso QGate usa QAOA como subrutina: elige 3 vuelos, 9 qubits, y el resto queda fijo. Llega a 340 con nuestra semilla. Y somos honestos: con 512 muestras hasta el azar resuelve piezas tan chicas. Con 8 muestras QAOA resuelve el 59% de las piezas, contra 29% del azar sobre los 27 estados de su espacio. Pero el azar sobre las 6 permutaciones válidas llegaría a 78% y enumerar las 6 opciones, a 100%: QAOA concentra probabilidad respecto a su espacio de partida, pero en piezas de 3 vuelos aún no supera a esas alternativas." |
| 2:25 a 2:40 | 7 Escala | Integrante 4 | "Para la final medimos de N=10 a N=20 con 10 semillas y el mismo presupuesto para todos. La memoria cuántica no crece: siempre 9 qubits. La calidad todavía no escala: ninguna diferencia entre métodos es distinguible, y los bloques QAOA no aportaron reducción de costo aunque se llevan entre 79% y 97% del tiempo." |
| 2:40 a 3:00 | 8 Cierre | Integrante 2 | "Hoy lo cuántico aporta estructura y concentración de probabilidad en piezas pequeñas, no velocidad. Lo medimos en el simulador Qiskit Aer y en una corrida en ibm_kingston de IBM Quantum: en N=3 con mixer XY salieron 25% de asignaciones válidas, contra 79% ideal y 22% al azar. El siguiente paso es mitigación de errores y piezas de 16 qubits. Gracias." |

## Preguntas probables del jurado

**¿Por qué usar cuántico si la fuerza bruta resuelve N=10 en segundos?**
No buscamos ventaja cuántica en N=10. Usamos N=10 porque tiene óptimo conocido para medir con rigor
qué aporta cada parte. Lo que no crece con N es la memoria cuántica, porque el subproblema es de tamaño fijo; la
calidad todavía no escala (etapa 3).

**¿Cómo escala?**
Los qubits por paso son siempre 9 (3 vuelos × 3 puertas). Lo que crece con N es la búsqueda clásica.
En la etapa 3 medimos qap10 (N=10) y sintéticas de N=14, 16 y 20 con 10 semillas, contra la cota Gilmore-Lawler y
contra el mejor costo encontrado. En N=20: SA mediana 1049 [1038, 1059] en 47 s; híbrido con QAOA 1040 [1038, 1052]
en 223 s. Los rangos se solapan: no distinguible. Las instancias de N > 10 son sintéticas.

**¿Cuánto es cuántico y cuánto clásico?**
Variables que entran al circuito: 9/N², de 9.00% en N=10 a 2.25% en N=20. Movimientos aceptados hasta la mejor
asignación: todos del 2-swap y de la perturbación; 0 de los bloques QAOA, y 0 de reducción de costo. Tiempo dentro de
QAOA: 97% en N=10 y 79% en N=20. No es un problema solo de QAOA: desde un óptimo local 2-swap, incluso enumerar las 6
opciones del bloque mejora apenas 1 a 8 de 2000 bloques (QAOA, 1 o 2). Por eso, en N>10, el híbrido con QAOA empata la
mejor mediana con el 2-swap sin bloques: la mejora la hace el 2-swap. La atribución depende del orden de las fases: el
2-swap corre primero y se lleva las mejoras fáciles.

**¿Qué tiene de nuevo el híbrido?**
Tres cosas, medidas con el mismo presupuesto para todos: un selector por tensión (elige los vuelos que más costo
generan), dos fases (2-swap hasta óptimo local y luego un bloque de 3 vuelos) y ángulos reutilizados entre bloques con
respaldo en frío. Resultado honesto: el selector por tensión no se distingue del azar; reutilizar ángulos sube P(óptimo)
del bloque de 0.093 a 0.128 y P(válida) de 0.50 a 0.71 con el mismo tiempo, pero no ahorra evaluaciones (40 en ambos,
COBYLA llega a su máximo).

**¿Corrieron en hardware real?**
Sí, una vez y solo N=3 (9 qubits): un job en ibm_kingston de IBM Quantum, 4096 shots por circuito, 5 s de
QPU, con los ángulos optimizados en el simulador. Mixer XY: 25.4% válidas (ideal 78.9%, azar
22.2%); mixer X: 6.3% (ideal 13.7%, azar 1.2%). Ambos muestrearon el óptimo
24. El ruido real borró casi toda la ventaja de XY, como predijo nuestra simulación con 1% de ruido
(25.0%). Todo lo demás (N=4, N=10 y escalamiento) es simulador.

**¿Cómo eligieron λ?**
λ0 es el mayor aporte posible de una sola asignación. Quitar o duplicar una asignación cambia el costo
como mucho en λ0 y viola una restricción: es un criterio suficiente razonable, no una garantía. Lo
validamos con un barrido de λ/λ0 entre 0.25 y 4.

**¿QAOA realmente aporta en el híbrido? / ¿Por qué QAOA si enumerar gana? / ¿Qué azar?**
Hay que decir qué azar. Frente a los 27 estados que genera su estado inicial (una puerta por vuelo), QAOA concentra
probabilidad: P(óptimo) por pieza 0.094 contra 0.039, y con 8 muestras resuelve 59% de las piezas contra 29%. Frente a
muestrear las 6 permutaciones válidas (78% con 8 muestras) o enumerarlas (100%), todavía no gana:
las piezas de 3 vuelos son tan chicas que enumerar es trivial. Medimos QAOA ahí para ver cuánto concentra con un
circuito que cabe en hardware, no porque esperemos que gane (SIMULADOR, N=10, `results/extra.json`).

**¿Qué usó la IA?**
Desarrollado con asistencia de Claude Code (Anthropic), supervisada por el equipo; parte del motor se preparó antes de
la jornada; los cuatro integrantes pueden explicar su funcionamiento.

**¿Por qué el híbrido no siempre llega a 340?**
El límite es el vecindario de 3 vuelos, no QAOA: con el solver exacto en el mismo marco, en varias
semillas, llega a 340 solo en una parte. Mejorarlo es trabajo clásico (vecindarios más grandes,
reinicios), o más qubits (k=4, 16 qubits).

**¿Cómo leyeron el MPS?**
Las filas con rhs 1 y coeficientes 1 son de asignación y dan las x. Cada variable y aparece junto a dos
x y su coeficiente es F·D. Armamos el tensor, factorizamos por SVD con residuo 0 y elegimos el orden de
índices que reproduce 24 y 32.

**¿Qué hizo cada uno?**
Completar: modelo y lectura del MPS · QAOA y Qiskit · híbrido y escalamiento · dashboard, PPT y pitch.

**Frase de respaldo.** "Con piezas de 3 vuelos, enumerar las 6 opciones o muestrear permutaciones válidas supera a
QAOA, y lo medimos. Lo que aporta QAOA es concentrar probabilidad respecto a su espacio de partida; en hardware real
el ruido borra casi toda la ventaja del mixer XY. El clásico es más rápido y, de N=10 a N=20, ninguna diferencia de
calidad es distinguible entre semillas; la memoria del componente cuántico sí es constante."

**¿4 de 12 semillas es con QAOA?** No: con el solver exacto en cada vecindario, 4 de 12 semillas llegan a 340; el
QAOA lo corrimos con la semilla 7. Cada corrida con QAOA tarda unos 186 s, así que 12 semillas serían unos 37 min.
