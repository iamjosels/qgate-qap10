# Guion del pitch (2:30 a 3:00)

Una slide por bloque. Hablar con números, sin leer la pantalla. Todos los números salen de
`results/results.json` (simulador Qiskit Aer, no hardware real).

| Tiempo | Slide | Quién | Texto |
|---|---|---|---|
| 0:00 a 0:20 | 1 Portada | Integrante 1 | "Somos QGate. En un aeropuerto, los pasajeros en conexión caminan entre puertas. Asignamos 10 vuelos a 10 puertas para que caminen lo menos posible, usando QAOA de Qiskit dentro de una búsqueda clásica." |
| 0:20 a 0:40 | 2 Problema | Integrante 1 | "Hay 3.6 millones de asignaciones. El costo suma pasajeros por distancia, cada par una vez. A la izquierda una asignación al azar, a la derecha la nuestra: las conexiones gruesas quedan cortas. Los datos son el benchmark qap10, las unidades son supuestos." |
| 0:40 a 1:05 | 3 Datos | Integrante 2 | "El MPS viene linealizado: 4150 variables. Reconstruimos flujos y distancias sin depender de nombres y verificamos la escala: N=3 da 24, N=4 da 32 y la instancia completa 340, como pide el reto. El 340 solo lo usamos para medir el gap." |
| 1:05 a 1:30 | 4 Qiskit | Integrante 3 | "Pasamos a QUBO, luego a Ising, y corremos QAOA en Qiskit Aer. Comparamos dos ansatz: mixer X, donde todo es penalidad, y mixer XY con estado W, que deja cada vuelo en una sola puerta. En N=4, QAOA con mixer X muestrea asignaciones válidas 112 veces más que el azar." |
| 1:30 a 1:50 | 5 Límites | Integrante 3 | "N=10 completo serían 100 qubits: imposible de simular. Justificamos λ y lo validamos con un barrido. Y medimos el ruido: con 1% de ruido el mixer XY pierde casi toda su ventaja de factibilidad." |
| 1:50 a 2:25 | 6 Híbrido | Integrante 4 | "Por eso QGate usa QAOA como subrutina: elige 3 vuelos, 9 qubits, y el resto queda fijo. Llega a 340 con nuestra semilla. Y somos honestos: con 512 muestras hasta el azar resuelve piezas tan chicas. Con 8 muestras QAOA resuelve el 59% de las piezas y el azar el 29%. Eso es lo que aporta lo cuántico aquí." |
| 2:25 a 2:40 | 7 Escala | Integrante 4 | "Al crecer a N=16 seguimos con 9 qubits y memoria constante; medimos contra una cota inferior porque no hay óptimo conocido." |
| 2:40 a 3:00 | 8 Cierre | Integrante 2 | "Hoy lo cuántico aporta estructura y concentración de probabilidad en piezas pequeñas, no velocidad en simulador. El siguiente paso es hardware IBM real, piezas de 16 qubits y mitigación de errores. Gracias." |

## Preguntas probables del jurado

**¿Por qué usar cuántico si la fuerza bruta resuelve N=10 en segundos?**
No buscamos ventaja cuántica en N=10. Usamos N=10 porque tiene óptimo conocido para medir con rigor
qué aporta cada parte. El diseño de QGate es el que escala: el subproblema cuántico es de tamaño fijo.

**¿Cómo escala?**
Los qubits por paso son siempre 9 (3 vuelos × 3 puertas). Lo que crece con N es la búsqueda clásica.
Medimos N = 10, 12, 14 y 16 contra la cota Gilmore-Lawler, con tiempo y memoria pico.

**¿Corrieron en hardware real?**
No. Todo es Qiskit Aer, y lo decimos en cada resultado. Modelamos ruido despolarizante: con 1% el mixer
XY cae casi al nivel del azar. Es el primer experimento que haríamos en hardware.

**¿Cómo eligieron λ?**
λ0 es el mayor aporte posible de una sola asignación. Quitar o duplicar una asignación cambia el costo
como mucho en λ0 y viola una restricción, así que ninguna inválida le gana a la mejor válida. Lo
validamos con un barrido de λ/λ0 entre 0.25 y 4.

**¿QAOA realmente aporta en el híbrido?**
Con 512 muestras, no se distingue del azar: piezas de 3 vuelos tienen solo 6 asignaciones. Lo medimos
con una ablación: con 8 muestras QAOA resuelve muchas más piezas que el azar y llega a mejor costo.
P(óptimo) por pieza también es mayor que la del azar.

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
