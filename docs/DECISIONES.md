# Decisiones y verificaciones

Registro de lecturas del reto y decisiones técnicas. Los números salen de corridas reales sobre
`data/qap10.mps.gz` (MIPLIB) y quedan en `results/results.json`.

## 1. Lectura del MPS y verificación de la escala (24 / 32 / 340)

**Archivo.** `qap10.mps.gz` descargado de `https://miplib.zib.de/WebData/instances/qap10.mps.gz`
(82 641 bytes, 24/10/2026).

**Estructura encontrada.**

| Dato | Valor |
|---|---|
| Variables (columnas) | 4150 = 100 x + 4050 y |
| Restricciones | 1820 = 20 de asignación + 1800 de enlace, todas de igualdad |
| Sentido del objetivo | MIN, constante 0 |
| Términos lineales en x | 0 |
| Nombres | `X001..X100` (asignación), filas `NX01..NX20` (asignación), filas de enlace `CxxAyyy` |

**Cómo se reconstruye el costo sin depender de los nombres.**

1. Las filas de asignación tienen rhs = 1 y todos sus coeficientes son 1: sus variables son las 100 x.
   Esas 20 filas se separan en dos familias de 10 (elementos y ubicaciones), cada x aparece una vez
   en cada familia.
2. Cada variable y aparece en filas de enlace junto a exactamente dos x (`x_ij` y `x_kl`). Su
   coeficiente en el objetivo es `F_ik · D_jl`.
3. Con eso se arma el tensor `T[i,j,k,l]` (4050 de 4050 y mapeadas, ninguna sin asignar) y se
   factoriza en F y D por SVD de rango 1. **Residuo de la factorización: 0.0** (el modelo es
   Koopmans-Beckmann exacto).
4. Solo hay y para pares i < k, así que cada par se cuenta una vez: no hay que dividir por 2.

**Orden de índices.** "Primeras N filas y columnas" depende de qué fila es el elemento 1, 2, ...
Se probaron las candidatas que permite el archivo (`orden_columnas`: orden de aparición de las x;
`orden_filas`: orden de las filas de asignación). La candidata `nombres` no aplica porque los
nombres `X001..X100` no traen el par (i, j) explícito. **Ambas candidatas reproducen los óptimos
de control**, y el bench usa la primera (`orden_columnas`).

| Control | Óptimo calculado (fuerza bruta) | Esperado | OK |
|---|---|---|---|
| N = 3 | 24 | 24 | sí |
| N = 4 | 32 | 32 | sí |
| N = 10 | 340 (3 628 800 permutaciones, un único óptimo) | 340 | sí |

Conclusión: la escala es la correcta (si se duplicaran pares saldría 48 / 64 / 680).

## 2. Uso del 340

El 340 solo se usa para calcular el gap y para la tabla de validación. Ningún método lo recibe
como dato de entrada ni como punto de partida: el híbrido arranca de una permutación aleatoria
(semilla + 100) y SA de permutaciones aleatorias.

## 3. Comparación justa del híbrido

El borrador original corría el híbrido con solver exacto con 3 veces más iteraciones que el de QAOA.
Se corrigió: ambos usan **el mismo número de iteraciones, la misma semilla y el mismo arranque**,
tanto en N = 10 como en la prueba de escalamiento. Así la diferencia entre ambos mide solo cuánto
pierde (o no) QAOA al resolver cada subproblema.

**Empates.** En la primera corrida completa, con la misma semilla, el híbrido QAOA terminó en 378 y el
exacto en 340 aunque QAOA resolvió el 100% de los subproblemas al óptimo. La causa: el solver exacto
devuelve la identidad cuando la asignación actual ya es óptima (no se mueve), mientras que QAOA puede
devolver otra permutación del mismo costo, que se aceptaba como movimiento lateral. Eso cambiaba la
trayectoria por azar, no por calidad. Se corrigió: ambos aceptan solo mejoras estrictas
(`sideways=False`). Con eso las trayectorias QAOA y exacta coinciden paso a paso mientras QAOA
encuentre el óptimo del subproblema, y cualquier diferencia final se atribuye a fallos de QAOA.

## 4. Parámetros del híbrido (perturbación)

Se probó con solver exacto (rápido) sobre qap10 real, 8 y luego 12 semillas:

| Iteraciones | stall_limit | kick | adaptativo | media | llega a 340 |
|---|---|---|---|---|---|
| 300 | 10 | 2 | no | 360.2 | 2/8 |
| 300 | 25 | 2 | no | 352.0 | 2/8 |
| 500 | 10 | 3 | no | 352.3 | 4/12 |
| 500 | 10 | 3 | sí | **349.3** | **5/12** |

Se eligió `stall_limit = 10`, `kick_swaps = 3` y perturbación adaptativa (cada kick sin mejora suma
un swap, hasta N/2), reiniciando siempre desde la mejor asignación conocida. Subir `stall_limit` a 25,
como sugería el plan, no mejoró en estas pruebas. La ganancia es modesta: el límite está en el
vecindario de 3 elementos, no en la perturbación.

## 5. λ (penalidad)

`lambda_auto` fija λ0 = máxima contribución posible de una sola asignación `x_ij = 1`:
`max_ij ( L_ij + sum_{k != i} max_{l != j} T[i,j,k,l] )`. Quitar o duplicar una asignación cambia el
costo como mucho en λ0 y viola al menos una restricción (penalidad >= λ), así que con λ >= λ0 ninguna
asignación inválida puede ganarle a la mejor válida por bajar costo. Se valida con un barrido
λ/λ0 ∈ {0.25, 0.5, 1, 2, 4} con P(válida) y P(óptimo) para ambos mixers: λ chico deja ganar
inválidas, λ grande aplana el paisaje del costo.

## 6. Ruido

`p_feasible` es la probabilidad ideal (distribución exacta del statevector). Con ruido despolarizante
solo cambian las muestras, por eso el log y el JSON reportan también `feasible_fraction_shots`.
Todo es simulador (Qiskit Aer); nada se presenta como hardware real.

## 7. Entorno

Windows 11, Python 3.14.7, Qiskit 2.6.1, Qiskit Aer 0.18.0, NumPy 2.5.4, SciPy 1.18.1. La consola de
Windows usa cp1252: el bench fuerza UTF-8 en stdout para poder imprimir λ.

## 8. Límites declarados (revisión externa, 24/10)

- **Posible sesgo en `stall_limit`.** Los parámetros de perturbación del híbrido (`stall_limit = 10`,
  `kick_swaps = 3`, adaptativo) se ajustaron probando semillas sobre qap10 y comparando con el óptimo
  conocido 340. Eso puede favorecer a qap10; en instancias nuevas no hay garantía.
- **N > 10 son instancias sintéticas** (generadas con semilla), sin óptimo conocido: se comparan contra
  la cota de Gilmore-Lawler.
- **Hardware: un solo job, un solo backend** (ibm_kingston, N=3, 4096 shots por circuito). No hay
  repeticiones ni otros backends; no se puede estimar la variación entre corridas.
- **Línea base de las piezas** (`analysis/baselines.py`, `results/extra.json`): con 8 muestras, el azar
  sobre las 6 permutaciones válidas acierta más piezas que QAOA, y enumerar las 6 acierta todas.
- **Control de escala** (`analysis/scale_check.py`): la asignación óptima cuesta 340 con cada par una vez y
  680 con cada par dos veces.

## 9. Etapa 3 (final): decisiones de diseño

- **Selector de vecindario.** Antes (`qgate_lns`, `select="mixed"`): iteraciones pares al azar e impares por ruleta
  ponderada por la contribución de cada vuelo, sin control de repetición. Ahora (`qgate/twophase.py`): `random` o
  `tension`, con ruleta softmax sobre la tensión normalizada y sin repetir el trío del bloque anterior. El mismo
  selector se aplica a todos los solvers.
- **Dos fases.** 2-swap de mejor mejora hasta óptimo local, luego un bloque k=3. Así el bloque solo puede aportar
  movimientos que el 2-swap no encuentra (3-ciclos). Cada movimiento aceptado se registra con su origen (swap, bloque,
  perturbación) y su reducción de costo; la atribución depende de este orden.
- **Ángulos reutilizados.** COBYLA arranca desde los ángulos del bloque anterior; si la distribución resultante queda
  por debajo del azar en P(válida) se repite en frío. El criterio no usa el óptimo del bloque.
- **Presupuesto idéntico.** Todos los solvers del modo dos fases usan B iteraciones externas, la misma semilla, el
  mismo arranque y el mismo selector; QAOA y el azar sobre permutaciones válidas usan el mismo número de muestras.
  SA es la referencia clásica con su propio presupuesto (declarado en `results/final.json`).
- **Ganador.** Un método se marca como mejor solo si su máximo entre semillas queda por debajo del mínimo de todos
  los demás; si no, "no distinguible".
- **Tiempos.** Se miden con varios procesos en paralelo (una corrida por proceso, Aer con un hilo); son comparables
  entre métodos de la misma corrida, no con tiempos de otras máquinas.

## 10. Revisión externa del organizador (25/10)

- Se reprodujeron los seis puntos antes de cambiar código (25/10, 9:15); el detalle y la evidencia están en la
  sección 5c del README.
- El plazo se extendió a las 9:50. Como el límite de lanzamiento de la corrida completa ya había pasado, se lanzó
  la **corrida de verificación reducida** (semillas 7 a 11, mismas instancias, B, shots y presupuestos)
  en `results/final_verif.json` y `results/final_runs.json.gz`, sin tocar `results/final.json`.
- Las cifras publicadas de `final.json` (10 semillas) siguen vigentes; sus permutaciones no se conservaron (nota
  visible en el README y en la pestaña 04). La corrida reducida sirve para auditar el método con permutaciones.
- Procedencia: un JSON auxiliar entra al dashboard solo si `results/MANIFEST.json` lo atesta para la misma instancia.
  Para los archivos ya publicados la atestación es a posteriori (calculada el 25/10, sin modificar su contenido).
- El refactor de `build_report.py` (punto 6) queda pendiente a propósito.
