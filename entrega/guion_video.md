# Guion del video demo (60 a 90 s)

Grabar pantalla a 1080p con el dashboard (https://iamjosels.github.io/qgate-qap10/) en pantalla completa.
Voz en off en español. Los números que se ven salen de `results/results.json`.

| Tiempo | Pantalla | Voz |
|---|---|---|
| 0:00 a 0:08 | Barra superior: logo QGate, pestañas 01 / 02 / 03 | "QGate asigna vuelos de conexión a puertas de embarque con QAOA de Qiskit dentro de una búsqueda clásica." |
| 0:08 a 0:28 | Escena 01 QAOA, mixer XY, play | "Con 16 qubits hay 65 536 combinaciones y solo 24 son válidas. Mientras el optimizador ajusta los ángulos, la probabilidad se mueve hacia las válidas y hacia el óptimo." |
| 0:28 a 0:36 | Cambiar a MIXER X | "Con el mixer estándar las reglas solo se respetan por penalidad; el mixer XY deja cada vuelo en una sola puerta." |
| 0:36 a 0:58 | Escena 02 Aeropuerto en x2 | "Cada paso elige 3 vuelos, 9 qubits, y QAOA propone el cambio en cian. El tablero de salidas y el costo bajan hasta 340, el óptimo de referencia." |
| 0:58 a 1:10 | Escena 03 Resultado | "Tres tarjetas: datos verificados 24, 32 y 340; QAOA frente al azar; y el híbrido. La tabla dice dónde corrió cada cosa: todo es simulador." |
| 1:10 a 1:25 | Bajar a "¿Cuánto aporta QAOA?" | "Somos honestos: con 512 muestras el azar también resuelve piezas tan chicas. Con 8 muestras QAOA resuelve muchas más que el azar." |

Cierre en pantalla: link del repo y del dashboard.
