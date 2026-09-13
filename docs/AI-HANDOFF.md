# Continuar el proyecto con otra IA

## Por qué hay varios archivos de entrada

Cada herramienta busca contexto inicial con una convención distinta. No necesita una especificación propia: basta un archivo pequeño que la conduzca a los mismos documentos canónicos.

- Codex y muchos agentes leen `AGENTS.md`.
- Cursor puede leer `AGENTS.md`; sus modelos internos, incluidos los que cambies durante el mes, comparten ese contexto.
- Claude Code reconoce `CLAUDE.md`.
- Gemini CLI reconoce `GEMINI.md` y sus imports.
- Grok, DeepSeek u otra IA usada en una web o chat puede recibir `docs/START-HERE.md` y los archivos que este enlaza.

Así se puede cambiar de modelo sin mantener cinco copias de la especificación. El modelo importa menos que la calidad y actualidad de los documentos comunes.

## Traspaso recomendado

Entrega la carpeta `Music Library Project` completa o abre esa carpeta como proyecto. Después usa este encargo:

> Lee primero AGENTS.md y docs/START-HERE.md. Distingue el estado actual de la especificación objetivo. Revisa DECISIONS y ROADMAP antes de editar. Trabaja solo en el siguiente bloque acordado, usa copias para cualquier prueba musical, ejecuta los criterios relacionados de TEST-PLAN y actualiza CURRENT-STATE, ROADMAP, DECISIONS si corresponde y VALIDATION al terminar. No migres la biblioteca histórica.

La IA no debe lanzar la copia fuente sin argumentos: el comportamiento portable usaría la carpeta padre como raíz. Las pruebas se ejecutan con `--root` apuntando expresamente a una biblioteca temporal o a `Music Library Test`.

Para una IA de chat que no pueda recorrer carpetas, adjunta al menos:

1. `docs/START-HERE.md`;
2. `docs/PRODUCT-SPEC.md`;
3. `docs/CURRENT-STATE.md`;
4. `docs/DECISIONS.md`;
5. el bloque relevante de `docs/ROADMAP.md` y `docs/TEST-PLAN.md`;
6. los archivos de código que vaya a modificar.

## Qué debe devolver la IA

Pídele siempre:

- lista concreta de archivos cambiados;
- pruebas ejecutadas y resultado;
- criterios de aceptación cubiertos;
- riesgos o decisiones aún abiertas;
- documentación actualizada en el mismo cambio.

Si solo devuelve código sin actualizar el estado, la siguiente IA volverá a partir de información vieja.

## Control de divergencia

- El comportamiento deseado se cambia en `PRODUCT-SPEC.md`.
- Las decisiones se registran en `DECISIONS.md`.
- Lo que realmente existe se actualiza en `CURRENT-STATE.md`.
- El trabajo se marca en `ROADMAP.md` solo después de probarse.
- Los resultados van a `VALIDATION.md`.

No copies párrafos completos entre archivos de entrada de cada herramienta. Esos archivos deben seguir siendo punteros breves.

## Credenciales y datos locales

`config.json`, `catalog.json`, `import.log`, `Staging/` y `Recovery/` se excluyen de Git. El futuro token de Discogs tampoco debe compartirse con otra IA ni guardarse en Markdown. Para investigar un fallo, ofrece una versión saneada del log y copias de audio solo cuando sea imprescindible y tengas derecho a usarlas.
