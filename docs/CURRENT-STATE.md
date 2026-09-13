# Estado actual del prototipo

**Corte:** 13 de septiembre de 2026. Este documento describe el código existente, no la especificación final.

## Implementado y comprobado

- TUI Python verde fósforo con menú principal `[1] Import Music`, `[2] Rebuild Playlists`, `[3] Exit`.
- Creación y verificación de la estructura portable mediante rutas relativas.
- Política FLAC, MP3 o Keep both, preguntada la primera vez y guardada en `config.json`.
- Recarga manual del inventario con `[R] Refresh folders`.
- Lectura y escritura de metadatos con Mutagen incluido en `vendor/`.
- Catálogo con archivos, alias de rutas e identidades MusicBrainz cuando existen.
- Deduplicación por identidad y formato, promoción de Tracks a Releases y reparación de M3U.
- Transacciones con manifiestos y copias SHA-256 en `Recovery`; recuperación al arrancar y rechazo de conflictos externos.
- Escritura atómica de archivos de estado y M3U.
- Protección contra enlaces simbólicos que escapen de la raíz y bloqueo de dos importaciones simultáneas.
- 34 pruebas automáticas del núcleo y pruebas reales controladas con Picard 2.13.3.

## Cómo funciona hoy

`Library.inventory()` recorre Incoming a cualquier profundidad. Cada carpeta padre inmediata con audio forma inicialmente un lote. `Engine.run()` copia el lote a Staging, ejecuta Picard, calcula destinos, deduplicaciones, promociones, pendientes y M3U, y aplica un único commit recuperable.

La integración de Picard abre una instancia auxiliar por Lookup y otra por cada Scan individual no resuelto. Usa un perfil temporal sin plugins, sin mover ni renombrar, guarda solo copias de Staging y mata el proceso después de retirar los archivos. Este cierre evita un fallo observado en Picard Intel bajo Rosetta.

Hoy, los archivos sin identificación fiable se envían individualmente a Pending. Una excepción durante la identificación cancela el lote completo. El resumen final muestra contadores planos de archivos.

## Problemas demostrados por las pruebas reales

1. **Un fallo temporal de MusicBrainz se presenta como `FAILED`.** Los originales permanecen intactos, pero la interfaz no distingue red, coincidencia incierta y fallo de integridad ni ofrece reintento local.
2. **Picard ocupa el primer plano repetidamente.** La estrategia por archivo abre y cierra muchas ventanas y hace difícil seguir usando el Mac.
3. **Una coincidencia aislada puede fragmentar un release.** En la prueba de Alan Lomax, `This Train` terminó dentro de un recopilatorio de Various Artists mientras las otras 14 pistas fueron a Pending.
4. **Pending puede crear un bucle manual.** Corregir y volver a Incoming repite el mismo proceso; no existe aún una cola de revisión dentro de la app.
5. **No se representa bien un multidisc incompleto.** El caso Alan Lomax era realmente el disco 3 completo de una caja de tres discos.
6. **El resumen final no informa por release o playlist.** El usuario ve pistas importadas, pero no qué unidades se completaron.
7. **Incoming conserva residuos.** Quedan carpetas vacías, metadatos de Finder y archivos auxiliares; no existe una política completa para mover sidecars y limpiar con seguridad.
8. **No hay edición interactiva del plan.** La interfaz todavía no permite corregir año, título, disco o pistas antes del commit.
9. **No existe consulta a Discogs.** El fallback está diseñado, pero faltan integración, puntuación por cohorte y decisión sobre credenciales.

## Estado de la biblioteca externa de prueba

La raíz `/Volumes/Music/Music Library Test` es una evidencia de prueba, no una biblioteca aprobada. En el último inventario contenía:

- 21 archivos en Releases: 9 de Barker, 11 de Albert King y `This Train` situado en un release incorrecto.
- 14 pistas de Alan Lomax en Pending.
- restos de Staging y varias transacciones de Recovery de intentos anteriores.
- 1 M3U.

Albert King acabó identificado correctamente en un segundo intento. El conjunto de Alan Lomax debe recomponerse desde copias, conservando y verificando hashes, antes de usarlo para validar el nuevo flujo.

## Lectura honesta de `README.md` y `VALIDATION.md`

Esos archivos documentan la versión construida y las pruebas que superó. Las afirmaciones sobre identificación universal, separación automática de releases y envío de pistas sueltas a Pending no son la conducta final aceptada. La especificación nueva está en `PRODUCT-SPEC.md`.

