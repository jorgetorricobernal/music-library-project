# Contrato de trabajo para asistentes de IA

Este archivo es la entrada breve para Codex, Cursor y cualquier agente que reconozca `AGENTS.md`. La información canónica vive en `docs/`; no dupliques aquí la especificación.

## Antes de trabajar

1. Lee [`docs/START-HERE.md`](docs/START-HERE.md).
2. Distingue siempre entre **estado actual** y **comportamiento acordado**:
   - [`docs/CURRENT-STATE.md`](docs/CURRENT-STATE.md) describe lo que hace hoy el prototipo.
   - [`docs/PRODUCT-SPEC.md`](docs/PRODUCT-SPEC.md) define el producto que se debe construir.
3. Consulta [`docs/DECISIONS.md`](docs/DECISIONS.md) antes de cambiar una decisión de producto o arquitectura.
4. Usa [`docs/ROADMAP.md`](docs/ROADMAP.md) para elegir el siguiente bloque de trabajo y [`docs/TEST-PLAN.md`](docs/TEST-PLAN.md) para validarlo.

## Reglas del proyecto

- El código fuente y la documentación viven en `Music Library Project`. `Music Library Test` es una biblioteca desechable para pruebas con copias.
- No ejecutes el lanzador de la copia fuente: por diseño calcula la biblioteca desde su carpeta padre. Para pruebas usa la copia situada dentro de `Music Library Test` o invoca Python con `--root` apuntando expresamente a una raíz desechable.
- No migres ni modifiques la biblioteca musical histórica.
- Nunca pruebes con el único ejemplar de un archivo. Conserva y comprueba hashes de los originales.
- Las operaciones que cambian audio, catálogo o M3U deben ser atómicas y recuperables.
- Un fallo de red o una identificación incierta no debe consumir archivos de Incoming ni convertirse en `FAILED` si la integridad sigue intacta.
- En el flujo de Releases, la unidad de decisión es el release completo. No fragmentes un conjunto coherente por coincidencias aisladas de pistas.
- No aceptes silenciosamente una coincidencia de Discogs o una propuesta dudosa. La especificación define cuándo pedir confirmación.
- Usa `Release` en la interfaz, los nombres de carpeta y la documentación. Puede ser un álbum, EP, single o recopilación.
- No guardes tokens o credenciales en el repositorio ni en documentación versionable.

## Al terminar un cambio

- Ejecuta las pruebas relacionadas y registra el resultado real.
- Actualiza `CURRENT-STATE.md`, `ROADMAP.md` y, si hubo una decisión nueva, `DECISIONS.md`.
- No marques una función como implementada por estar diseñada o parcialmente programada.
- Resume qué cambió, cómo se comprobó y qué limitaciones continúan abiertas.
