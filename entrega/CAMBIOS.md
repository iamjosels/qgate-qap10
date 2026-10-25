# QGate · cambios para la final

**Etapa 3: escalamiento N ≥ 14.** Medimos qap10 (N=10, oficial) y tres instancias sintéticas (N=14, 16 y 20) con 10 semillas y el mismo presupuesto para todos los métodos: 440 corridas en simulador, todas con asignaciones válidas. Nuevo híbrido en dos fases: búsqueda 2-swap hasta un óptimo local y luego un bloque QAOA de 3 vuelos (9 qubits), con selector de vuelos por tensión y ángulos reutilizados entre bloques.

**Cuánto es cuántico y cuánto clásico.** La memoria cuántica no crece con N: siempre 9 qubits por bloque, cuando un circuito completo necesitaría 400 en N=20. La calidad todavía no escala: ningún método se distingue entre semillas. En N=20 (mediana [mín, máx]): 2-swap 1040 [1038, 1058] en 43 s, SA 1049 [1038, 1059] en 47 s, híbrido QAOA 1040 [1038, 1052] en 223 s. Los bloques QAOA aportaron 0 de la reducción de costo y consumen entre 79% y 97% del tiempo: la mejora la hace el 2-swap. Lo reportamos tal cual; no buscamos demostrar superioridad cuántica.

**Revisión externa del organizador.** Reprodujimos los seis puntos y corregimos:
1. Procedencia: `results/MANIFEST.json` con huella de la instancia y sha256 de cada archivo; el dashboard no mezcla resultados de otra instancia (falla con aviso visible).
2. Permutaciones: cada corrida guarda su permutación y su trayectoria. Una corrida de verificación (semillas 7 a 11), recalculada de forma independiente, dio 220 corridas con 0 discrepancias y 220 de 220 con el mismo costo que lo publicado.
3 y 4. Tests con aserciones reales: costo recalculado, óptimos 24, 32 y 340, factibilidad y reproducibilidad.
5. Versiones exactas en `requirements.txt` y `requirements.lock`.
Pendiente: separar `build_report.py` (punto 6) y probar la instalación en un clon limpio.

**Dashboard.** Nueva pestaña 04 Escala con la atribución cuántico/clásico; un método se marca mejor solo si su diferencia supera el rango entre semillas. Las cifras del híbrido llevan su versión ("día 1" o "etapa 3"); el Panorama usa como referencia clásica el método de mejor mediana; la pestaña 04 avisa que las permutaciones publicadas no se conservaron. Logos nuevos en el dashboard y el PPT.

**Documentos.** README (secciones 5b y 5c), DECISIONES, DASHBOARD, guion y PPT final actualizados; cada número sale de un JSON del repo.
