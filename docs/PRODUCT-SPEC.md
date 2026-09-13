# Especificación del producto

## 1. Objetivo

Construir una TUI en Python que convierta descargas heterogéneas en una biblioteca musical portable y verificable, sin exigir que el usuario entienda la estructura original de carpetas ni vigile MusicBrainz Picard durante el proceso.

La aplicación importa dos tipos de intención:

- **Releases:** álbumes, EP, singles, recopilaciones o discos parciales que deben conservarse como una unidad musical.
- **Playlists:** conjuntos ordenados que terminan como Tracks planos y una M3U mantenible.

## 2. Estructura de la raíz

```text
ROOT/
├── 1. Music Library/
│   ├── 1. Releases/
│   └── 2. Tracks/
├── 2. New Downloads/
│   ├── 1. Releases incoming/
│   ├── 2. Playlists incoming/
│   └── 3. Pending/
├── 3. Playlists M3U/
├── 4. Others/
└── Music Library App/
```

La app crea y verifica las carpetas. Calcula la raíz desde su propia ubicación y persiste rutas relativas. No depende del nombre del volumen.

## 3. Menú e inventario

El menú principal conserva exactamente:

```text
[1] Import Music
[2] Rebuild Playlists
[3] Exit
```

La pantalla Import Music cuenta releases, playlists, archivos y pendientes sin llamar todavía a Picard. `[R] Refresh folders` vuelve a escanear si el usuario añade descargas con la pantalla abierta. `[F] Change format` cambia FLAC, MP3 o Keep both y guarda la preferencia. `[P] Review Pending` abre la cola de revisión.

La estructura recibida puede ser `Release/archivos`, `Usuario/Release/archivos`, varios discos, archivos sueltos o niveles adicionales. Las carpetas ayudan a proponer cohortes, pero no determinan por sí solas la identidad.

## 4. Flujo de importación

### 4.1 Fases

1. Inventariar y copiar a Staging.
2. Identificar sin modificar originales.
3. Analizar cada cohorte y clasificar el resultado.
4. Presentar propuestas y resolver dudas.
5. Mostrar un plan final completo.
6. Aplicar la transacción solo al pulsar Enter.
7. Limpiar con seguridad y mostrar el informe jerárquico.

El plan final incluye cantidades automáticas, confirmadas mediante Discogs, locales, pendientes y omitidas:

```text
[Enter] Apply
[B] Review
[C] Cancel
```

Antes de `Apply` no se consume ningún original ni se cambia biblioteca, catálogo o M3U.

### 4.2 Estados de identificación

**Coincidencia alta de MusicBrainz.** El conjunto tiene coherencia de release, posiciones y metadatos. Se propone automáticamente; una anomalía de cohorte impide aceptar una coincidencia aislada.

**Varias ediciones posibles.** Se muestran alternativas con año, país, formato, sello y catálogo. El usuario puede elegir una edición, quedarse con la identidad general si es suficiente, importar localmente, enviar a Pending o reintentar.

**Coincidencia dudosa.** No se escriben etiquetas silenciosamente. Se permite reintentar, revisar candidatos, editar información, importar como release local, enviar el conjunto a Pending u omitirlo.

**Sin coincidencia.** Se conserva el release completo. El usuario puede reintentar, importar localmente, editar sus datos, dejarlo entero en Pending u omitirlo.

**Fallo de red o servicio.** Es un estado recuperable, no un fallo de integridad. Ofrece:

```text
[R] Retry this release
[C] Continue with other releases
[A] Retry all connection problems later
[S] Stop
```

El reintento puede repetirse. Si se continúa, la unidad permanece en Incoming y se procesa el resto.

**Fallo grave.** Solo se usa `FAILED` ante errores de escritura, verificación, corrupción, crash no recuperable o imposibilidad de asegurar la transacción. No deja un commit parcial.

### 4.3 Coincidencias parciales y releases incompletos

La revisión muestra por separado:

- archivos recibidos;
- pistas esperadas según la edición;
- archivos identificados;
- archivos presentes sin asociar;
- posiciones realmente ausentes.

Un release con pistas presentes sin identificar no se fragmenta automáticamente. Un release al que realmente le faltan pistas puede importarse como incompleto si el usuario lo decide. El catálogo guarda las posiciones, discos o pistas ausentes para completarlo después.

## 5. Edición antes de importar

`[E] Review or edit information` abre:

```text
[1] Album artist
[2] Release title
[3] Original release year
[4] Disc number / total discs
[5] Release type
[6] Label
[7] Catalog number
[T] Review tracks
[P] Preview destination
[S] Save proposal
[B] Back
```

Elegir un campo muestra valor actual, valor propuesto y una entrada nueva; Enter conserva el valor. `Review tracks` muestra una tabla y permite elegir una pista para editar título, artista, número de pista y disco. Todos los cambios pertenecen al plan hasta `Apply`.

Los valores obtenidos de una fuente y los cambios manuales se guardan por separado, junto con su procedencia, para no fingir que una corrección local vino de MusicBrainz o Discogs.

## 6. MusicBrainz, AcoustID y Discogs

MusicBrainz Picard 2.13.3 es el identificador principal. Los MBIDs son la identidad preferida cuando existen. Lookup tiene prioridad sobre Scan porque el fingerprint puede escoger otra edición.

Discogs es el segundo origen. La búsqueda puntúa la cohorte completa mediante títulos distintivos, orden, duraciones, número de pistas y estructura de discos. Nunca se acepta un release por la coincidencia de un único tema. Si una propuesta de Discogs cambia metadatos importantes, se muestra al usuario para confirmación.

AllMusic no forma parte del producto.

## 7. Organización de Releases

Destino:

```text
1. Releases/Album Artist [año original] Release Title/
```

- Se usa año original cuando existe; no se inventa uno desconocido.
- Various Artists y los releases multiartista conservan una sola carpeta basada en Album Artist.
- Los multidisc usan números `01-01`, `02-01`, `03-01` para evitar colisiones.
- Varias apariciones legítimas de una grabación se conservan por posición.
- Un release local sin coincidencia obtiene una identidad local estable, nunca MBIDs inventados.

### Caso de aceptación: Alan Lomax

El lote de prueba corresponde al disco 3 completo de `American Folk-Blues Train (Alan Lomax Field And Studio Recordings)`, Alan Lomax, 2003, UK, Castle Music, catálogo `CMETD 648`, caja de 3 CD. Debe importarse como disco 3 de 3, con 15 de 15 pistas presentes en ese disco y discos 1 y 2 ausentes. La aplicación no debe separar `This Train` en otro recopilatorio por una coincidencia aislada.

## 8. Tracks, deduplicación y promoción

`2. Tracks` es plano. FLAC, MP3 o Keep both expresan preferencia entre copias equivalentes; no convierten audio ni eliminan el único formato disponible. La identidad combina MBIDs, posición de release, identidad local y hashes según el caso. El tamaño del archivo no es identidad.

Si un Track ya importado pasa a formar parte de un Release, la app puede promover su audio al destino del release, adaptar las etiquetas en una copia y actualizar todas las M3U. No vacía otras posiciones legítimas que usan la misma grabación.

## 9. Playlists y M3U

Cada carpeta superior de Playlists incoming es una playlist. Si trae M3U, se conserva el orden y las repeticiones; si no, se usa el orden natural. La revisión ocurre por playlist y muestra:

- pistas recibidas e identificadas;
- pistas ya existentes en la biblioteca;
- archivos nuevos para Tracks;
- pistas sin resolver.

Opciones: reintentar, crear la playlist incompleta, mantener la playlist completa en Pending u omitirla. Una M3U incompleta contiene las pistas disponibles. El catálogo conserva orden, repeticiones y pertenencia de las pendientes. Al resolver una pista, la app actualiza atómicamente todas las M3U que la referencian.

`Rebuild Playlists` permite reconstruir una o todas. Rescanea la biblioteca y repara mediante MBID, identidad local, fingerprint o alias de ruta. Una coincidencia blanda por nombre requiere confirmación. Las líneas sin resolver se conservan y se explican.

## 10. Pending

Pending es una cola gestionada por la aplicación, no un callejón sin salida. Conserva releases completos o pistas de playlist con su contexto, propuesta, origen, motivo y pertenencias.

El usuario puede corregir etiquetas fuera de la app y volver a `Import Music > Review Pending`. Si mueve manualmente un archivo a la biblioteca, Rebuild intenta reconectarlo mediante identidad fuerte; ante una coincidencia blanda, pregunta.

## 11. Limpieza de Incoming

Después de un commit correcto:

- elimina `.DS_Store` y AppleDouble `._*`;
- mueve con el release los sidecars relevantes: carátulas, CUE, logs, TXT, PDF y libretos;
- poda carpetas vacías hasta la raíz de Incoming;
- deja cualquier archivo real desconocido y muestra un aviso.

La limpieza se registra y es recuperable. No se borra silenciosamente un archivo desconocido.

## 12. Pantallas finales

La jerarquía superior solo contiene uno de estos estados:

- `IMPORT COMPLETE`: todo lo solicitado quedó aplicado sin asuntos pendientes.
- `COMPLETE WITH WARNINGS`: existen pendientes, omisiones o residuos que requieren atención.
- `FAILED`: la integridad o el commit no pudieron garantizarse.

Después aparecen únicamente las secciones relevantes:

```text
RELEASES
✓ Albert King — Born Under a Bad Sign
  Complete · 11/11 · MusicBrainz
✓ Alan Lomax — American Folk-Blues Train…
  Disc 3 of 3 · 15/15 on disc 3 · Discogs

PLAYLISTS
✓ Fiesta — Complete · 42/42
! Warm-up — Incomplete · 11/12

LIBRARY MAINTENANCE
Duplicates resolved       2
Tracks promoted           1
Folders cleaned           4
M3U updated               3
```

Releases informa archivos añadidos a Releases. Playlists separa archivos nuevos añadidos a Tracks de pistas ya reutilizadas. Si solo hubo un flujo, se omite la otra sección. Las listas largas se paginan.

## 13. Registro y portabilidad

Los mensajes de pantalla indican qué pasó y qué acción tomar. El detalle técnico acumulativo vive en un único `Music Library App/import.log`.

La aplicación descubre Picard y comprueba su versión y arquitectura. Una futura versión Apple Silicon debe poder sustituir a la Intel sin cambiar el modelo de datos. La solución temporal para el cierre bajo Rosetta solo se elimina después de validar la versión nueva con copias.

