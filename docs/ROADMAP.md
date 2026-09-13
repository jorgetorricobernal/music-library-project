# Roadmap de implementación

El orden prioriza corregir el riesgo que ya dañó la clasificación del ensayo real. Cada bloque termina con pruebas y actualización de documentación.

## Fase 0 — preservar la línea base

- [ ] Crear una copia limpia del fixture Alan Lomax reuniendo sus 15 archivos, sin modificar la evidencia actual.
- [ ] Guardar hashes, etiquetas originales y estructura esperada del fixture.
- [ ] Congelar un fixture de Albert King completo y otro deliberadamente incompleto.
- [ ] Ejecutar la suite actual y registrar la línea base antes de refactorizar.

## Fase 1 — sesión de análisis sin mutaciones

- [ ] Separar identificación, decisión y commit en estados persistentes de una `ImportSession`.
- [ ] Introducir tipos explícitos para red, sin coincidencia, parcial, dudosa y fatal.
- [ ] Construir propuestas por cohorte y bloquear coincidencias aisladas incoherentes.
- [ ] Añadir reintento por release, continuidad y reintento agrupado al final.
- [ ] Mostrar el plan final y garantizar que Cancel no cambia originales ni biblioteca.

**Salida verificable:** una caída simulada de red permite reintentar ilimitadamente; Alan Lomax permanece unido durante todo el análisis.

## Fase 2 — Picard estable y discreto

- [ ] Reutilizar una instancia auxiliar por importación.
- [ ] Procesar Scan pendiente por lotes y vaciar Picard entre cohortes.
- [ ] Probar lanzamiento en segundo plano y medir cuántas veces toma el foco.
- [ ] Detectar versión y arquitectura; aislar el cierre especial de Rosetta.
- [ ] Mantener validación de escritura real y MBIDs tras SAVE.

**Salida verificable:** una importación con varios releases no abre una ventana por canción ni genera informes de crash.

## Fase 3 — revisión, edición y Pending

- [ ] Implementar pantallas de candidatos y coincidencia parcial.
- [ ] Implementar editor de release, disco y pistas sobre el plan.
- [ ] Permitir importación local con identidad estable.
- [ ] Modelar releases multidisc incompletos y posiciones ausentes.
- [ ] Convertir Pending en cola revisable con contexto preservado.

**Salida verificable:** el usuario puede importar el disco 3 de Alan Lomax como 15/15 del disco 3, dentro de una caja 3 CD, sin MBIDs falsos.

## Fase 4 — Discogs

- [ ] Resolver D-022 y documentar configuración segura del token.
- [ ] Crear cliente con límites, errores tipados y logs sin secretos.
- [ ] Buscar candidatos por cohorte y descargar tracklists.
- [ ] Implementar puntuación de títulos, orden, duración, cantidad y discos.
- [ ] Mostrar evidencia, alternativas y confirmación.

**Salida verificable:** el fixture Alan Lomax propone Discogs release 3627442 por sus 15 pistas de disco 3; una sola pista nunca basta.

## Fase 5 — playlists pendientes y mantenimiento

- [ ] Revisar y resumir cada playlist como unidad.
- [ ] Crear M3U incompletas conservando referencias pendientes.
- [ ] Completar M3U automáticamente al resolver archivos.
- [ ] Ampliar Rebuild con MBID, identidad local, fingerprint y confirmación de coincidencias blandas.
- [ ] Conservar líneas sin resolver y explicar cada caso.

## Fase 6 — limpieza e informe final

- [ ] Clasificar y mover sidecars relevantes con su release.
- [ ] Integrar limpieza y poda en Recovery.
- [ ] Conservar archivos desconocidos con aviso.
- [ ] Implementar resumen por Releases, Playlists y Library Maintenance.
- [ ] Añadir paginación y estados finales según la especificación.

## Fase 7 — validación previa a uso real

- [ ] Ejecutar la matriz completa de `TEST-PLAN.md` con copias.
- [ ] Probar desconexión, interrupción durante commit y recuperación tras reinicio.
- [ ] Probar el traslado de la raíz a otro volumen o nombre.
- [ ] Auditar que catálogo, logs y documentación no contienen credenciales.
- [ ] Hacer una importación piloto amplia en una biblioteca de prueba nueva.
- [ ] Solo después diseñar la migración histórica como proyecto independiente.

