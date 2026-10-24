# Guion del video demo (60 a 90 s)

Grabar pantalla a 1080p. Voz en off en español. Sin música fuerte.

| Tiempo | Pantalla | Voz |
|---|---|---|
| 0:00 a 0:08 | Dashboard, hero con KPIs | "QGate asigna vuelos de conexión a puertas de embarque usando QAOA en Qiskit dentro de una búsqueda clásica." |
| 0:08 a 0:20 | Sección Datos validados: tarjetas 24 · 32 · 340 y heatmaps | "Leímos el MPS de MIPLIB, reconstruimos flujos y distancias y verificamos la escala con los óptimos de control." |
| 0:20 a 0:35 | Mapa de puertas: clic en Aleatoria, luego en QGate híbrido | "El grosor es la cantidad de pasajeros que conectan. Con la asignación de QGate las conexiones gruesas quedan cortas y el costo baja." |
| 0:35 a 0:48 | QAOA vs azar: pasar el mouse por las barras de N=4 | "QAOA muestrea asignaciones válidas muy por encima del azar. El mixer XY con estado W respeta una puerta por vuelo." |
| 0:48 a 0:60 | Híbrido: curvas QAOA y control exacto superpuestas | "Cada paso resuelve un subproblema de 9 qubits. QAOA encontró el óptimo de cada pieza, por eso su curva coincide con el control exacto." |
| 0:60 a 0:72 | Terminal: `python -m qgate.bench --mps data/qap10.mps.gz --quick` corriendo | "Todo se reproduce con un comando: versiones, semillas y resultados quedan en results.json." |
| 0:72 a 0:85 | Escalabilidad y limitaciones | "Al crecer N seguimos usando 9 qubits. Medimos también lo que no funciona: el ruido y el tiempo en simulador." |

Cierre en pantalla: link del repo y del dashboard.
