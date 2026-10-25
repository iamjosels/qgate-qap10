# QGate · Guía de marca para implementar

Concepto: **gate = puerta de embarque + compuerta cuántica.** Señalética de aeropuerto real
(amarillo aviación sobre negro, pictogramas, tableros split-flap) cruzada con lenguaje cuántico
(cian para todo lo que sale de Qiskit). Nada de degradados morados, glassmorphism ni emojis.

Los mockups de referencia están en esta carpeta (`*.dc.html`). Son HTML con estilos inline:
úsalos como referencia visual exacta de layout, tamaños y colores. Los valores entre corchetes
(`[00.0]%`, `[000]`, `[backend]`) se reemplazan con datos reales de `results/results.json`. Nunca inventar números.

## Tokens

| Token | Hex | Uso |
|---|---|---|
| `--ink` (Pista) | `#0B0B0C` | fondo de página |
| `--board` (Tablero) | `#141518` | paneles y tarjetas |
| `--flap` (Ficha) | `#1E2024` | fichas split-flap |
| `--line` | `#2C2F35` | bordes y separadores |
| `--signal` (Señal) | `#FFC629` | acento principal: señalética, óptimo, lo que importa |
| `--qubit` | `#4FE3E0` | todo dato que sale de Qiskit (QAOA, circuitos, probabilidades) |
| `--invalid` | `#FF6B3D` | reglas rotas, asignaciones inválidas (`#7A3A26` en barras de histograma) |
| `--paper` (Papel) | `#F4F1E8` | texto principal y fondo de boarding pass |
| `--mute` | `#9A9890` | texto secundario sobre negro |
| `--ink-2` | `#55534D` | texto secundario sobre papel |

Regla de color: amarillo = señalética y lo óptimo; cian = cuántico; naranja = inválido. Nunca mezclar roles.

## Tipografía (Google Fonts)

- **Barlow Condensed 700/800**: titulares, códigos de puerta (P07), números grandes. Mayúsculas.
- **IBM Plex Sans 400/500/600**: texto corrido (la familia de IBM, guiño al jurado).
- **IBM Plex Mono 400/500/600**: datos, tablero split-flap, etiquetas pequeñas con tracking 0.12 a 0.16em, código.

## Logo

Vigente (25/10): `design/logo/qgate_icono.png` (isotipo: puerta de embarque amarilla `#FFC629` con un avión
en el dintel y una esfera de Bloch cian `#4FE3E0`) y `design/logo/qgate_logo_completo.png` (isotipo + "QGATE"
en amarillo), ambos sobre fondo `#0B0B0C`. Versiones reducidas en la misma carpeta (96, 64 y 36 px; logo de
360 px). Se usan en la barra del dashboard, el favicon, el chip HÍBRIDO, la portada del PPT y los encabezados.

Anterior (solo referencia de los mockups): cuadrado amarillo con una "Q" negra cuya cola es una flecha de
señalética; wordmark en ficha split-flap con "Q" amarilla + "GATE" en Barlow Condensed 800 (`Main.dc.html`).

## Componentes

- **Ficha split-flap**: fondo `--flap`, radio 4 a 6 px, línea de 2 px color `--ink` cruzando al centro,
  letra en Plex Mono 600. Animación al cambiar: la mitad superior gira hacia abajo (rotateX) en 180 a 250 ms, escalonada por ficha.
- **Letrero de puerta**: fondo `--signal`, texto `--ink` en Barlow Condensed 800 ("P01".."P10").
- **Chip de vuelo**: fondo `--flap`, borde 2 px (`--line` normal, `--qubit` si acaba de moverse por QAOA).
- **Boarding pass**: fondo `--paper`, radio 14, divisor punteado vertical, dos muescas circulares color
  `--ink` en el divisor, talón con código de barras de franjas. Ver `Results.dc.html`.
- **Pictogramas**: trazo 2 px, esquinas redondeadas, sobre baldosa amarilla (cuántico: baldosa negra con borde cian).
- **Patrón de interferencia**: 3 ondas finas cian con opacidades 1 / 0.55 / 0.3, solo como textura en secciones cuánticas.

## Pantallas del modo demo (dashboard)

1. `Qaoa.dc.html` · Escena 01 QAOA: histograma animado por frames (inválidas naranja oscuro, válidas cian,
   óptima amarillo), contadores P(válida) y P(óptimo) vs azar, tira del circuito de una fila (W, COSTO γ, XY β), toggle mixer X / XY.
2. `Demo.dc.html` · Escena 02 Aeropuerto: mapa "Terminal Q" con 10 letreros de puerta y chips de vuelo,
   arcos de flujo amarillos con grosor = pasajeros (F), el cambio propuesto por QAOA en cian punteado;
   tablero SALIDAS split-flap (vuelo, puerta, estado MOVIDO/EN POSICIÓN), contador de costo en fichas, gap vs 340, chips "9 qubits por subproblema".
3. `Results.dc.html` · Escena 03 Resultado: tres boarding passes (Datos, QAOA, Híbrido) + tabla comparativa con columna "dónde corrió" (CPU, Qiskit Aer, IBM Quantum real).

Navegación entre escenas con pestañas 01/02/03 arriba; botón play/pausa, velocidad x2 y pantalla completa.
Responsive: en pantallas angostas las columnas se apilan.

## Slides

`Slide.dc.html` (portada) y `SlideContent.dc.html` (contenido): 16:9, fondo `--ink`, encabezado con número
en letrero amarillo + título Barlow, máximo una idea por slide, números enormes, casi sin texto.
Exportar el PPT con este estilo (python-pptx: mismos colores y fuentes; si Barlow/Plex no están, embeber o usar PNGs).
