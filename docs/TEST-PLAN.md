# Plan de pruebas y criterios de aceptación

## Reglas de ensayo

- Usar copias, nunca el único ejemplar.
- Calcular hashes antes y después de cada prueba real.
- Mantener la biblioteca histórica fuera de la raíz de prueba.
- No marcar un escenario como aprobado por una captura o una impresión manual; registrar resultado y evidencia reproducible.
- Las pruebas de servicios externos son opt-in y deben tolerar indisponibilidad sin confundirla con un fallo funcional.

## Matriz mínima

| Área | Escenario | Resultado esperado |
|---|---|---|
| Inventario | `Usuario/Release/archivos`, niveles arbitrarios y CD1/CD2 | cuenta todos los audios sin llamar a Picard; Refresh refleja cambios |
| Red | MusicBrainz indisponible | mensaje accionable, Retry repetible, Continue conserva Incoming |
| Cohorte | una pista encuentra otro recopilatorio | no se separa del release si el resto de la cohorte contradice el resultado |
| Completo | Albert King, 11 archivos y edición de 11 | 11/11, un release, MusicBrainz, sin pendientes |
| Parcial técnico | 11 recibidos, 9 asociados y 2 sin asociar | muestra 9 identificados, 2 presentes sin asociar y 0 ausentes |
| Incompleto real | edición de 11 con solo 9 archivos | muestra cuáles faltan y permite importar 9/11 si se confirma |
| Multidisc | solo disco 3 de una caja de 3 | guarda disco 3, posiciones `03-xx`, registra discos 1 y 2 ausentes |
| Discogs | Alan Lomax, 15 pistas del disco 3 | candidato 3627442 de alta coherencia; confirmación; ningún singleton separado |
| Sin match | release propio o raro | edición local posible; identidad estable sin MBID inventado |
| Edición | cambiar año, título, disco y una pista | preview correcto; Cancel no escribe; Apply conserva procedencia y override |
| Various Artists | varios artistas de pista | una carpeta basada en Album Artist |
| Formato | FLAC, MP3, Keep both y fallback | preferencia consistente sin convertir ni perder formato único |
| Promoción | Track ya usado por M3U pasa a Release | archivo promovido, catálogo y M3U apuntan al destino final |
| Playlist | orden y tema repetido | M3U conserva orden y repetición |
| Playlist parcial | 11/12 y crear incompleta | M3U de 11, referencia pendiente guardada, pasa a 12/12 al resolver |
| Rebuild | ruta renombrada | repara por identidad fuerte; nombre ambiguo pide confirmación |
| Limpieza | Finder metadata y carpetas vacías | elimina residuos conocidos y poda; archivo desconocido queda con aviso |
| Crash | interrupción en cada frontera del commit | recuperación idempotente; no queda biblioteca parcial |
| Conflicto | archivo editado después del manifiesto | se detiene y no sobrescribe la edición externa |
| Portabilidad | mover toda la raíz | catálogo, Recovery y M3U siguen funcionando con rutas relativas |
| Picard UI | importación de varios releases | como máximo una instancia auxiliar por sesión; no toma foco por pista |
| Informe | sesión mixta | estado superior único y secciones separadas de Releases y Playlists |

## Pruebas de regresión existentes

La suite actual cubre metadatos, formatos, deduplicación, promoción, compilaciones, multidisc, M3U, colisiones, symlinks, bloqueos, transacciones, recuperación, portabilidad, Refresh y color TUI. Debe seguir pasando durante la refactorización, salvo tests que codifiquen el comportamiento sustituido de enviar cada archivo sin resolver a Pending. Esos tests se reemplazan por pruebas de cohorte y cola de revisión.

## Prueba de compatibilidad con Picard nuevo

Cuando exista una versión Apple Silicon estable:

1. detectar binario, versión y arquitectura;
2. repetir Lookup de release, Lookup de playlist y Scan con copias;
3. comprobar guardado efectivo y MBIDs;
4. ejecutar varias sesiones consecutivas y revisar informes de crash;
5. probar cierre normal y cierre especial por separado;
6. retirar el workaround de Rosetta únicamente si el cierre normal supera la matriz.

El cambio de Picard no requiere migrar catálogo ni biblioteca si el adaptador mantiene el mismo contrato.

## Registro de resultados

Cada bloque implementado debe añadir a `VALIDATION.md` fecha, versión de Python/Picard, fixtures utilizados, pruebas pasadas o fallidas y limitaciones. No se incluyen tokens ni rutas privadas innecesarias en los logs que se compartan.

