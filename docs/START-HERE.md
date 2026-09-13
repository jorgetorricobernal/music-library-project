# Music Library App — punto de entrada

**Actualizado:** 13 de septiembre de 2026  
**Estado:** prototipo funcional en revisión; rediseño acordado pendiente de implementación.

Esta aplicación organiza una biblioteca musical portable en un USB o SSD. Importa releases y playlists desde carpetas de entrada, usa MusicBrainz Picard para identificar copias de trabajo, conserva identidades estables y mantiene playlists M3U aunque cambien las rutas.

## Qué documento responde a cada pregunta

| Pregunta | Documento |
|---|---|
| ¿Qué funciona hoy y qué falló en las pruebas reales? | [`CURRENT-STATE.md`](CURRENT-STATE.md) |
| ¿Cómo debe comportarse el producto terminado? | [`PRODUCT-SPEC.md`](PRODUCT-SPEC.md) |
| ¿Cómo se divide el código y dónde están los riesgos técnicos? | [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| ¿Qué decisiones ya están cerradas y cuáles siguen abiertas? | [`DECISIONS.md`](DECISIONS.md) |
| ¿Qué hay que construir y en qué orden? | [`ROADMAP.md`](ROADMAP.md) |
| ¿Cómo se demuestra que cada parte funciona? | [`TEST-PLAN.md`](TEST-PLAN.md) |
| ¿Cómo continuar con otra IA sin perder contexto? | [`AI-HANDOFF.md`](AI-HANDOFF.md) |
| ¿Cómo se lanza y usa el prototipo actual? | [`../README.md`](../README.md) |
| ¿Qué pruebas ha superado el prototipo actual? | [`../VALIDATION.md`](../VALIDATION.md) |

## Regla de lectura

`PRODUCT-SPEC.md` es la fuente de verdad del comportamiento deseado. `CURRENT-STATE.md` manda cuando la pregunta es qué hace el código hoy. Una casilla del roadmap solo se marca al quedar implementada y verificada.

## Estructura del proyecto

```text
Music Library Project/
├── AGENTS.md                 # entrada para Codex y Cursor
├── CLAUDE.md                 # entrada para Claude Code
├── GEMINI.md                 # entrada para Gemini CLI
├── README.md                 # uso del prototipo actual
├── VALIDATION.md             # validación histórica del prototipo
├── docs/                     # verdad compartida por todas las IAs
├── music_library.py          # entrada Python
├── musiclib/                 # módulos de la aplicación
├── tests/                    # pruebas automáticas y pruebas reales opt-in
└── vendor/                   # Mutagen incluido
```

La carpeta `Music Library Project` es el proyecto mantenible. La carpeta hermana `Music Library Test` contiene una raíz musical de ensayo y puede acumular Staging, Recovery, catálogos y resultados deliberadamente imperfectos.

> **Seguridad al ejecutar:** el lanzador portable calcula la raíz desde su propia ubicación. La copia de `Music Library Project` se conserva como fuente y documentación; no se abre con doble clic. Ejecuta la app desde `Music Library Test/Music Library App` o usa `music_library.py --root RUTA_DE_PRUEBA` con una raíz desechable explícita.

## Principios no negociables

- La biblioteca histórica queda fuera de alcance hasta que el flujo nuevo esté probado.
- Se trabaja siempre con copias durante el desarrollo.
- Ninguna coincidencia aislada debe romper un release coherente en varios destinos.
- El usuario ve y confirma el plan completo antes de la primera mutación.
- La pérdida de conexión es recuperable y ofrece reintento.
- Los cambios de audio, catálogo y M3U son transaccionales; las M3U se escriben atómicamente.
- Las rutas persistentes son relativas a la raíz del dispositivo.
- Los errores se explican en lenguaje accionable; el detalle técnico vive en un único `import.log` junto a la app.
