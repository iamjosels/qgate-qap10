# QGate · descripción breve

QGate asigna 10 vuelos de conexión a 10 puertas de embarque para reducir la distancia que caminan los pasajeros en tránsito (instancia MIPLIB qap10, Track A del reto NTT DATA; flujos y distancias son supuestos de negocio).
Reconstruimos el modelo cuadrático desde el MPS linealizado y verificamos la escala con los óptimos de control 24, 32 y 340.
Comparamos fuerza bruta, simulated annealing y QAOA en Qiskit con dos ansatz: mixer X con penalidades y mixer XY con estado W, que mantiene una puerta por vuelo por construcción.
Como 100 qubits no se pueden simular, QGate usa QAOA como subrutina de 9 qubits dentro de una búsqueda clásica por vecindarios: los qubits y la memoria no crecen con N.
Medimos en el simulador Qiskit Aer y en una corrida en ibm_kingston de IBM Quantum (N=3, 9 qubits: 25.4% de asignaciones válidas con mixer XY, contra 78.9% ideal y 22.2% al azar). Un dashboard web con tres escenas animadas muestra QAOA, el aeropuerto y los resultados, con sus limitaciones (ruido, tiempo).

**Uso de IA.** Desarrollado con asistencia de Claude Code (Anthropic), supervisada por el equipo; parte del motor se preparó antes de la jornada; los cuatro integrantes pueden explicar su funcionamiento.

Créditos: Qiskit, Qiskit Aer, qiskit-ibm-runtime, NumPy, SciPy, MIPLIB 2017 (qap10), Claude Code.
