# Validación — 13 de septiembre de 2026

> Esta validación corresponde al prototipo actual. Los escenarios de aceptación del rediseño —reintentos de red, revisión por release, Discogs, Pending gestionado y resumen jerárquico— están definidos en [`docs/TEST-PLAN.md`](docs/TEST-PLAN.md) y aún no deben considerarse implementados.

## Resultado

34 pruebas automáticas superadas en macOS con Python 3.13.3, Mutagen 1.47.0 y audio sintético FLAC, MP3 y M4A. Se usó ffmpeg únicamente para generar las muestras de prueba.

Cobertura: lectura/escritura de etiquetas; preferencia FLAC/MP3/Keep both y fallback; pistas planas; recopilatorios y multidisc; repetición de una grabación en posiciones distintas; promoción y retagging del formato preferido; conservación de ambos formatos después de promoción; dos playlists compartiendo tema; orden y repeticiones de M3U de entrada; colisiones reales; pendientes; reconstrucción de una playlist o todas; cambio manual de nombre y traslado de la raíz; exportación de originales; bloqueo de un segundo escritor; cambios externos; interrupción en cada frontera del commit, recuperación idempotente y rechazo de sobrescritura ante conflicto.

## Pruebas con Picard real 2.13.3

Se verificó el ejecutable instalado (`picard-run --version`). Se ejecutaron instancias separadas sin plugins y con configuración independiente. La versión final de la secuencia se probó con tres copias de «Poa Alpina», de Biosphere:

| Prueba | Preparación | Resultado |
|---|---|---|
| Lookup de álbum | Se retiraron MBIDs/AcoustID de una copia, se mantuvieron etiquetas descriptivas | Identificado y guardado |
| Lookup de playlist | Misma preparación en otra copia | Identificado y guardado |
| Scan | Se retiraron además artista, álbum, título y posición | Identificado y guardado |

Las tres devolvieron Recording MBID `5cf0ca2e-df73-4109-9e5c-0b98bfd04adf` y el mismo Release Group. Scan eligió una edición diferente (13 pistas frente a 11); por ello se usa Lookup antes de Scan. Véase `tests/picard-results.json`.

Durante iteraciones anteriores se detectaron y corrigieron: el alias inexistente LOOKUP_CLUSTERED, el caso de álbum de una sola pista que no forma cluster, la omisión de archivos agrupados por SCAN y la carrera entre la respuesta de AcoustID y SAVE_MATCHED. Se añadió una secuencia con PAUSE y segundo guardado, seguida de comprobación de escritura real y lectura de MBIDs. La compilación x86_64 de Picard sufría además un fallo intermitente de PyQt/SIP al finalizar bajo Rosetta, después de guardar. Ahora Picard retira primero los archivos cargados y la app finaliza directamente el proceso auxiliar ya inactivo, sin invocar esa fase defectuosa.

El cierre corregido se comprobó en seis procesos reales consecutivos —dos series completas de Lookup de release, Lookup de playlist y Scan—. Todos guardaron las etiquetas y MBIDs esperados, terminaron de retirar los archivos y no generaron ningún nuevo informe de fallo de macOS.

El perfil temporal que usa cada pasada desactiva el aviso inicial, el aviso de guardado y la confirmación de salida de Picard. Así la integración no requiere clics y no modifica las preferencias del perfil habitual del usuario.

## Importación completa con música real

1. Copia de una pista de Amotik a playlist incoming, importación, copia del lote a Releases incoming, promoción automática y rebuild. Correcto.
2. Una pista de «Utility», de Barker, importada como playlist; después las **nueve pistas** del release copiadas a Releases incoming. Resultado: nueve pistas en Releases, un duplicado resuelto, un tema promovido y una M3U actualizada. Rebuild: una entrada comprobada, cero sin resolver. **Hashes de los originales sin cambios.** Véase `tests/live-results.json`.

La biblioteca de demostración procede de esta segunda prueba. Su contenido son copias. No se ejecutó ninguna migración histórica.

## Alcance de las comprobaciones

- Compilaciones, multidisc, fallos de escritura y cortes durante el commit: pruebas automatizadas controladas. No se expulsó físicamente el dispositivo durante una escritura.
- Lookup/Scan: servicios MusicBrainz/AcoustID reales, con sus posibles ambigüedades y fallos de red. No es una garantía de acierto universal sobre cualquier música.
- Se prueba portabilidad de rutas al cambiar la raíz; no se empaqueta ni se prueba un runtime universal para todos los modelos de Mac.
- Las preferencias de formato no convierten audio. Recovery conserva los originales y requiere espacio disponible.

Comprobación del dispositivo externo: se corrigió la exclusión de archivos auxiliares AppleDouble (`._*.m3u`) generados por macOS en exFAT y se añadió una prueba específica.

La interfaz verde fósforo usa color ANSI de 24 bits únicamente cuando se ejecuta en una terminal interactiva. Se comprobó que aplica primer plano verde y fondo negro, y que las ejecuciones no interactivas continúan produciendo texto sin códigos de color.

La pantalla previa a la importación permite volver a escanear las carpetas con `[R] Refresh folders`; una prueba funcional comprueba que el recuento cambia sin reiniciar la app. La detección de álbumes recorre cualquier profundidad. Las carpetas dividen el trabajo, pero los MBIDs separan releases mezclados y reúnen un release repartido entre carpetas. Las pistas no identificadas no bloquean otros discos del mismo directorio.
