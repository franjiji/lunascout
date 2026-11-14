# LunaScout — Plan de trabajo con agentes

Proyecto: **LunaScout**, NASA Space Apps Challenge 2026, challenge *Lunar Landing Site Navigator*.
Idea: una nave nunca aterriza en el punto exacto. LunaScout evalúa **toda la elipse de aterrizaje**: para cada punto calcula luz solar, visibilidad de la Tierra y pendiente con relieve real (LOLA) y efemérides reales (JPL Horizons). Devuelve la **probabilidad de que la misión sobreviva**, la **tolerancia a atrasos** y **sitios cercanos mejores**. Es una sola pantalla y los cálculos son en vivo.

**Plazo de entrega:** domingo 15/11 a las 23:59 (hora del evento local). Envíen una versión básica el domingo a la tarde y después la mejoran: solo cuenta el último envío.

---

## Archivos de esta carpeta

| Archivo | Para quién | Modelo | Esfuerzo |
|---|---|---|---|
| `01_CONTRACT.md` | **Todos los agentes** (adjuntarlo siempre) | — | — |
| `02_AGENT_EPHEMERIS.md` | Agente de efemérides (Horizons) | Claude Sonnet 5.5 | medium |
| `03_AGENT_TERRAIN_ENGINE.md` | Agente del motor de terreno y análisis | **Claude Fable 5.2** (alternativa: Opus 5.5) | high |
| `04_AGENT_API_DEPLOY.md` | Agente de API FastAPI y deploy | Claude Sonnet 5.5 | medium |
| `05_AGENT_FRONTEND.md` | Agente de la interfaz web | Claude Sonnet 5.5 (Opus 5.5 si se traba) | high |
| `06_AGENT_VALIDATION.md` | Agente validador (independiente) | Claude Opus 5.5 | high |
| `07_AGENT_SUBMISSION.md` | Agente de entrega (textos, video, README) | Claude Sonnet 5.5 | medium |

**Cómo usar cada prompt:** abran un chat o sesión de Claude Code nuevo con el modelo y el esfuerzo indicados. Peguen el contenido del prompt y **adjunten `01_CONTRACT.md`**. Si el agente trabaja sobre código, denle acceso a la carpeta del repo.

---

## Orden y dependencias

```
            ┌─ 02 Efemérides (Sonnet) ─────┐
01 Contrato ┼─ 03 Motor de terreno (Fable) ┼─→ 06 Validación (Opus) ─→ 07 Entrega (Sonnet)
 (listo)    ├─ 04 API + deploy (Sonnet) ───┤        ▲
            └─ 05 Interfaz (Sonnet) ───────┘        │
                                         (07 puede arrancar textos en paralelo)
```

- **02, 03, 04 y 05 arrancan YA y en paralelo.** El contrato define cómo se conectan.
- 04 y 05 trabajan con `fixtures/sample_response.json` hasta que el motor (03) esté listo.
- 03 necesita el archivo de efemérides de 02 para el análisis completo, pero puede empezar con el DEM y el horizonte.
- 06 arranca cuando haya resultados reales (domingo a la mañana).
- 07 arranca el domingo con borradores y cierra con los datos validados por 06.

## Reparto de personas (cada uno supervisa su agente)

| Persona | Supervisa | Además |
|---|---|---|
| A | 03 Motor de terreno | Es el núcleo técnico: tiene que entender el algoritmo para defenderlo |
| B | 02 Efemérides → luego 04 API + deploy | Reclamar **Google Cloud** y el **dominio gratis (GoDaddy/Porkbun)** HOY |
| C | 05 Interfaz | Responsable del look final |
| D | 06 Validación + 07 Entrega | **Responsable del video demo** (la guía pide designar una persona) |

## Cronograma sugerido

| Cuándo | Hito |
|---|---|
| Sáb 17:00 | Repo creado en GitHub; contrato en `CONTRACT.md`; reclamar Google Cloud y el dominio |
| Sáb 20:00 | Efemérides 2025–2028 generadas y verificadas. Horizonte de 1 punto calculado. Interfaz mostrando el fixture |
| Sáb noche | Precálculo de la grilla de horizontes corriendo (puede tardar, déjenlo toda la noche) |
| Dom 11:00 | `analyze()` real funcionando local; API sirviendo datos reales |
| Dom 14:00 | Deploy en Cloud Run + frontend publicado con dominio; pedir clasificación FortiGuard |
| Dom 16:00 | Validación (caso Athena) lista; correcciones |
| Dom 19:00 | **Primer envío "Submit for Judging"** con versión básica |
| Dom 21:00 | Video de ≤30 s con subtítulos en inglés (o 7 slides) |
| Dom 23:00 | Envío final. Probar todos los links en ventana privada |

## Estructura del repo (crear antes de lanzar agentes)

```
lunascout/
├── CONTRACT.md                 ← copia de 01_CONTRACT.md
├── README.md
├── data/
│   ├── raw/                    ← DEM GeoTIFF (NO subir a git, en .gitignore)
│   ├── ephemeris/              ← salida de 02
│   └── derived/                ← grilla de horizontes, hillshade (salida de 03)
├── engine/                     ← paquete Python (02 + 03)
│   ├── __init__.py
│   ├── geo.py  ephemeris.py  terrain.py  horizon.py  analyze.py
│   └── tests/
├── scripts/                    ← fetch_ephemeris.py, prepare_dem.py, precompute_horizons.py
├── api/                        ← FastAPI (04)
├── web/                        ← interfaz (05)
├── fixtures/sample_response.json
└── docs/                       ← validation.md (06), submission/ (07)
```

**Regla de ramas:** cada agente trabaja en su carpeta y en su rama (`feat/ephemeris`, `feat/engine`, `feat/api`, `feat/web`). Se mergea a `main` por pull request. **Nadie cambia el contrato sin avisar a todos y actualizar `CONTRACT.md`.**

---

## Reglas de la guía de Space Apps que TODOS deben respetar

1. **Todo el contenido en inglés:** interfaz, README y textos de la entrega. El video puede estar en español con subtítulos en inglés.
2. **Declarar el uso de IA:** cada archivo de código generado con IA lleva un encabezado tipo `# Developed with assistance from Claude (Anthropic) — reviewed by the LunaScout team`, y el README tiene una sección "Use of AI". Las imágenes generadas con IA llevan marca de agua visible.
3. **La idea es del equipo.** La IA acelera la implementación. Cada persona debe entender y poder explicar lo que hizo su agente.
4. **Prohibido:** logos, insignias o parches de NASA en material generado; imágenes, videos o voces de menores de 18.
5. **Usar datos de NASA** (Horizons, LOLA/PGDA) y declararlos. Listar todas las librerías y fuentes.
6. **Links públicos sin login** (app, repo, video). Probarlos en ventana privada.
7. **Nunca presentar datos de ejemplo como reales.** Lo que sea de ejemplo se rotula "Sample data".
8. Demo: **≤30 s** de video o **≤7 slides**. Si se pasan, quedan fuera de la evaluación global.

## Global Offers a usar
- **Google Cloud ($300 / 90 días):** hostear la API en Cloud Run con 1 instancia siempre encendida (sin "cold start" para los jueces).
- **Dominio gratis + SSL (GoDaddy Registry vía Porkbun):** URL profesional para el link final.
