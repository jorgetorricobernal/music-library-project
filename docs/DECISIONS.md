# Registro de decisiones

**Estados:** `ACEPTADA`, `ABIERTA`, `SUSTITUIDA`.

| ID | Estado | Decisión y motivo |
|---|---|---|
| D-001 | ACEPTADA | Usar `Release` en lugar de `Album` en interfaz y carpetas porque también se importan EP, singles y recopilaciones. |
| D-002 | ACEPTADA | Numerar las carpetas visibles con número, punto y espacio. `Music Library App` queda sin numerar. |
| D-003 | ACEPTADA | Inferir la intención por `Releases incoming` o `Playlists incoming`; no volver a preguntarla al importar. |
| D-004 | ACEPTADA | La estructura interna de una descarga es arbitraria. Se inventaría sin llamar a Picard y se reescanea con `[R]`. |
| D-005 | ACEPTADA | Preguntar la política de formato una sola vez, recordarla y permitir cambiarla desde Import. |
| D-006 | ACEPTADA | MusicBrainz/Picard es la primera fuente y los MBIDs son identidad preferida cuando existen. Lookup precede a Scan. |
| D-007 | ACEPTADA | Evaluar la coherencia de un release completo. Una coincidencia aislada no puede fragmentar la cohorte. |
| D-008 | ACEPTADA | Un fallo de red ofrece reintentos y continuidad; mantiene el material en Incoming. `FAILED` queda reservado para fallos de integridad. |
| D-009 | ACEPTADA | Pending será una cola revisable dentro de la app y conservará el contexto de release o playlist. |
| D-010 | ACEPTADA | Permitir releases incompletos y registrar discos o posiciones ausentes. |
| D-011 | ACEPTADA | Usar Discogs como segunda fuente y excluir AllMusic. Puntuar la secuencia completa y confirmar cambios importantes. |
| D-012 | ACEPTADA | Conservar Various Artists y multiartist como un solo release mediante Album Artist. |
| D-013 | ACEPTADA | Numerar multidisc como `disc-track` con dos dígitos para evitar colisiones. |
| D-014 | ACEPTADA | Tracks permanece plano; promoción y cambios de ruta actualizan M3U automáticamente. |
| D-015 | ACEPTADA | Las playlists se revisan y resumen como unidades, igual que los releases, conservando orden y repeticiones. |
| D-016 | ACEPTADA | La pantalla final separa estado, Releases, Playlists y Library Maintenance. No usa un contador ambiguo de tracks global. |
| D-017 | ACEPTADA | Antes de mutar se puede editar release, disco y pistas; los cambios se aplican solo con la confirmación final. |
| D-018 | ACEPTADA | Limpiar residuos conocidos y carpetas vacías después del commit; conservar y avisar sobre archivos desconocidos. |
| D-019 | ACEPTADA | Reutilizar una instancia auxiliar de Picard por importación y reducir el robo de foco. Mantener aislado el workaround Rosetta. |
| D-020 | ACEPTADA | Mantener documentación neutral en `docs/` y adaptadores finos para cada IA, evitando especificaciones duplicadas. |
| D-021 | ACEPTADA | Separar proyecto fuente (`Music Library Project`) y biblioteca desechable (`Music Library Test`). |
| D-022 | ABIERTA | Elegir cómo autenticar Discogs: token en Llavero de macOS, configuración portable no versionada u otra opción. Debe equilibrar portabilidad y secreto. |
| D-023 | ABIERTA | Determinar mediante prueba si Picard 2.13.3 puede ejecutarse totalmente oculto en macOS sin perder fiabilidad. |
| D-024 | ABIERTA | Definir el umbral exacto de confianza para candidatos de MusicBrainz y Discogs con un corpus de releases reales. |
| D-025 | ABIERTA | Decidir el formato visual final de paginación para informes y listas largas dentro de la TUI. |

## Cómo añadir una decisión

Añade una fila con contexto suficiente para que otra persona pueda mantenerla. Si una decisión cambia, marca la anterior `SUSTITUIDA` y enlaza el nuevo ID; no borres el historial.

