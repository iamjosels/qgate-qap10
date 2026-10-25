# Checklist de entrega (portal del hackathon)

La entrega en el portal la hace una persona del equipo. Completar antes de las 14:40.

| Campo | Valor |
|---|---|
| Nombre del equipo | QGate |
| Integrantes | Jose Giovanni Laura Silvera · Alex Mauricio Vargas Tapia · Stephie Zorrilla Delgado · Mayra Dayanne Saravia Camacuari |
| Categoría | 5.1 Industria · Reto NTT DATA QAP10 · Track A Aeropuerto |
| Repositorio GitHub | https://github.com/iamjosels/qgate-qap10 |
| Demo funcional | https://iamjosels.github.io/qgate-qap10/ |
| Video (opcional) | guion en `entrega/guion_video.md` |
| Descripción breve | `docs/descripcion_breve.md` |
| PPT | `entrega/QGate_final.pptx` (plantilla oficial, con fotos; PDF en `entrega/QGate_final.pdf`) |

## Verificación (24/10, 13:40)

- [x] Repo público; README renderiza en GitHub (11 tablas, sección IBM Quantum real)
- [x] Sin PDFs ni CLAUDE.md públicos (404 en GitHub)
- [x] Demo en GitHub Pages carga, las 3 escenas animan y la tabla de resultados tiene la fila de IBM Quantum
- [x] Hardware real: un job en ibm_kingston (dbefhdom94ac738rnc00), results/hardware.json con backend, job_id y métricas
- [x] Portada del PPT con los 4 nombres; ninguna slide dice "Integrante"; chip "IBM Quantum real" en Límites
- [x] entrega/QGate.pptx en GitHub es la versión nueva (mismo hash que el local)
- [x] python tests/test_core.py pasa
- [ ] Entrega en el portal (una persona del equipo) antes de las 14:40
- [ ] Repartir los bloques del guion (entrega/guion.md, columna "Quién") entre los 4 integrantes
- [ ] Los 4 integrantes en la presentación (15:00 a 16:40)

## Final, etapa 3 (25/10)

- [x] `results/final.json`: qap10 oficial y sintéticas N=14, 16 y 20, 10 semillas, mismo presupuesto para todos (SIMULADOR)
- [x] `results.json`, `hardware.json` y `extra.json` sin cambios
- [x] Dashboard: pestaña 04 Escala; fila "Escala" y frase del Panorama desde `final.json`; sección 07 rotulada "día 1"
- [x] `check_panorama.py` verifica los números del Panorama contra results.json, hardware.json y final.json
- [x] README sección 5b, DECISIONES §9, guion (bloque 7 y preguntas "¿Cuánto es cuántico?" y "¿Qué tiene de nuevo?")
- [x] PPT `entrega/QGate_final.pptx`: slide "Escala (etapa 3)" y límite de la etapa 3 en el cierre
- [ ] Repartir de nuevo el bloque 7 del guion y las respuestas nuevas entre los 4 integrantes

## Revisión externa, logos y documentos (25/10)

- [x] Seis puntos del organizador reproducidos; estado en README 5c
- [x] `results/MANIFEST.json` y dashboard fail-closed (`analysis/repro_fail_closed.py` pasa)
- [x] Corrida de verificación reducida: `analysis/verify_final.py` con 220 corridas y 0 discrepancias
- [x] Tests con aserciones reales; `requirements.txt` con versiones exactas y `requirements.lock`
- [x] Logos nuevos en dashboard, `QGate.pptx` y encabezados de `QGate_final.pptx`
- [x] Dashboard vigente: versión con logos (las variantes v3 y v4 se revirtieron)
- [x] Resumen de cambios para el jurado en `entrega/CAMBIOS.md`
- [ ] Pendiente: separar `build_report.py` y probar la instalación en un clon limpio
