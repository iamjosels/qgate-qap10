# QGate · descripción breve

QGate asigna 10 vuelos de conexión a 10 puertas de embarque para reducir la distancia que caminan los pasajeros en tránsito (instancia MIPLIB qap10, Track A del reto NTT DATA; flujos y distancias son supuestos de negocio).
Reconstruimos el modelo cuadrático desde el MPS linealizado y verificamos la escala con los óptimos de control 24, 32 y 340.
Comparamos fuerza bruta, simulated annealing y QAOA en Qiskit con dos ansatz: mixer X con penalidades y mixer XY con estado W, que mantiene una puerta por vuelo por construcción.
Como 100 qubits no se pueden simular, QGate usa QAOA como subrutina de 9 qubits dentro de una búsqueda clásica por vecindarios: los qubits y la memoria no crecen con N.
Un dashboard web muestra el mapa de puertas, QAOA frente al azar, el barrido de λ, la convergencia del híbrido, el escalamiento y las limitaciones medidas (ruido, tiempo).
