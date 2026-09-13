# Music Library

> **Estado del proyecto (13 de septiembre de 2026):** este README explica el prototipo actual. Las pruebas reales descubrieron límites en los fallos de red, la coherencia de releases, Pending y la integración visual de Picard. El comportamiento acordado para la siguiente versión está en [`docs/PRODUCT-SPEC.md`](docs/PRODUCT-SPEC.md); empieza por [`docs/START-HERE.md`](docs/START-HERE.md).

Una app de terminal para una biblioteca portable, con interfaz verde fósforo sobre fondo negro inspirada en monitores CRT. Abre **Launch Music Library.command** con doble clic. En este Mac se usa Python y MusicBrainz Picard 2.13.3 ya instalados; no hace falta instalar paquetes de Python. Mutagen 1.47.0 está incluido en `vendor/`.

## Uso

1. Coloca los releases en `2. New Downloads/1. Releases incoming` con la estructura que traiga la descarga. La app escanea el árbol completo: funcionan `Release/archivos`, `Artista/Release/archivos`, carpetas CD1/CD2, niveles adicionales y archivos sueltos. Las carpetas solo dividen el trabajo previo; no deciden qué es un release. Picard puede separar varios releases mezclados en una carpeta y los MBIDs reúnen un mismo release repartido entre carpetas. Coloca **una carpeta por playlist** en `2. New Downloads/2. Playlists incoming`; ahí se conserva la carpeta superior como identidad de la playlist y se incluyen sus subcarpetas.
2. Abre el lanzador y elige `[1] Import Music`. La primera vez eliges FLAC, MP3 o Keep both. Se recuerda la elección; `[F] Change format` permite cambiarla antes de cualquier importación. Si añades nuevas carpetas mientras esta pantalla está abierta, pulsa `[R] Refresh folders` para volver a contar los álbumes, playlists y archivos de audio sin cerrar la app.
3. Pulsa Enter para iniciar. La pantalla IMPORTING se sustituye por IMPORT COMPLETE, COMPLETE WITH WARNINGS o FAILED. Puedes dejar el proceso trabajando. La pantalla final permanece visible con `[M] Main Menu` y `[E] Exit`.
4. Si algo queda pendiente, revisa las etiquetas con Picard y vuelve a colocar **copias corregidas** en la carpeta incoming apropiada. Si falta identificar una parte de un álbum o se mezclan distintos releases, el álbum entero va a Pending.

`[2] Rebuild Playlists` permite elegir una M3U concreta o `[A] Rebuild All`. Repara cambios de nombre/ruta usando la identidad guardada. Conserva las líneas que no puede localizar y avisa. No busca ni migra la biblioteca histórica de `Others`.

## Carpetas

```text
Music/
├── 1. Music Library/
│   ├── 1. Releases/
│   │   └── Album Artist [año original] Título/
│   │       └── Track Artist - Álbum - 01. Canción.flac
│   └── 2. Tracks/                 # sin subcarpetas
├── 2. New Downloads/
│   ├── 1. Releases incoming/
│   ├── 2. Playlists incoming/
│   └── 3. Pending/
├── 3. Playlists M3U/
├── 4. Others/
└── Music Library App/
    ├── Launch Music Library.command
    ├── Recover Originals.command
    ├── music_library.py
    ├── recover_originals.py
    ├── config.json
    ├── catalog.json               # se crea al importar/reconstruir
    ├── import.log                 # un único registro acumulativo
    ├── musiclib/                  # módulos de la aplicación
    ├── vendor/                    # Mutagen y su licencia
    ├── tests/
    ├── Recovery/                  # originales y manifiestos recuperables
    └── Staging/                   # copias de trabajo
```

La app crea/verifica las carpetas al arrancar. La raíz siempre se calcula desde su ubicación, no desde el nombre del volumen ni desde la carpeta abierta en Terminal. Para cambiar de dispositivo, cierra la app y copia **toda la raíz**, incluyendo `Music Library App`, catálogo y Recovery. Las rutas del catálogo, la recuperación y las M3U son relativas. Los registros técnicos pueden mencionar rutas absolutas de sesiones anteriores; no se usan para localizar música.

## Criterios de organización

- **Releases:** estar dentro de Releases incoming expresa que quieres guardar esos archivos en Releases, ya sean álbumes, EP, singles o recopilaciones. La forma de las carpetas no define el release y no se deduce que esté completo contando pistas. Picard decide la identidad; cada archivo identificado se agrupa por Release Group/Release MBID. Various Artists permanece en una sola carpeta gracias al campo técnico Album Artist. Solo los archivos no identificados van a Pending, sin bloquear otros releases que compartían su carpeta de descarga.
- **Año:** originaldate / originalyear antes que fecha de la edición. No inventa un año si falta.
- **Multidisc:** `01-01`, `02-01`, etc. para evitar colisiones. Dos apariciones de una grabación en distintas posiciones de un release se conservan.
- **Identidad:** Recording MBID para equivalencias de pistas; Release Group / Release MBID y posición para organizar releases. Las reediciones de un mismo release group comparten carpeta. Se conservan posiciones distintas: no se intenta inferir equivalencias entre bonus tracks o cambios de orden de ediciones.
- **FLAC / MP3:** preferencias entre copias equivalentes, no conversión ni eliminación del único formato disponible. Keep both conserva una copia por formato. Si hay varias copias del mismo formato se compara bitrate y se prefiere la existente en empate. Los descartes quedan recuperables.
- **Promoción:** un tema suelto identificado puede incorporarse a un release. Si su formato es el preferido, se aprovecha su audio y se adaptan sus etiquetas al release en una copia. Las M3U pasan a señalar el destino final. No se vacían otros releases que también contienen esa grabación.
- **Colisiones:** nombres limpios normalmente; solo se añade un sufijo si dos objetos distintos colisionan. Se controla también mayúsculas/minúsculas.
- **Playlists:** si el lote contiene M3U, se conserva su orden y sus repeticiones; si no, se usa el orden natural de los nombres de los archivos. Los archivos de una carpeta no mencionados en su M3U se importan igualmente, pero no se añaden a esa playlist. Una M3U existente nunca se sobrescribe con otra descarga de igual nombre: se crea un nombre desambiguado.
- **Otros archivos:** carátulas, CUE y documentos externos permanecen en incoming. Las carátulas embebidas se conservan. No se descarga nuevo artwork.

## Picard 2.13.3

Se ejecuta una instancia independiente con configuración aislada, sin plugins y sin mover/renombrar archivos. Solo recibe las copias de Staging. Primero usa Lookup: agrupado para álbumes y por archivo para playlists. Los singletons tienen también Lookup por archivo. Lo no resuelto se carga de nuevo, individualmente y sin agrupar, para Scan.

La secuencia incluye barreras y un segundo SAVE_MATCHED porque en la prueba real se observó que 2.13.3 podía avanzar antes de terminar una respuesta de AcoustID. No basta con que Picard salga: se comprueba la terminación del guardado, la escritura efectiva en disco y la presencia de MBIDs y etiquetas. Los fallos de red detienen el lote sin consumir originales. El reconocimiento automático puede necesitar revisión en casos ambiguos; lo no resuelto va a Pending.

Cada pasada usa un perfil temporal preparado para funcionar sin preguntas: no muestra el aviso de primera ejecución, el aviso de guardado ni la confirmación de salida. Este perfil solo se aplica a las copias de preparación y no cambia las preferencias del Picard que abres normalmente.

Después de confirmar el segundo guardado, Picard retira los archivos cargados y la app detiene esa instancia auxiliar. Esto evita un fallo intermitente de la compilación Intel de Picard durante el cierre bajo Rosetta en Macs Apple Silicon.

Se separan formatos y entradas repetidas para que SAVE_MATCHED no omita archivos que Picard ha vinculado a una misma pista. Se han usado umbrales de Lookup 0,85 por archivo y 0,80 por cluster y de coincidencia de pista 0,80.

## Recuperación

Cada importación prepara todos los archivos antes de modificar la biblioteca. Una transacción incluye música, entradas consumidas, M3U y catálogo. Guarda originales comprobados por SHA-256 y un manifiesto durable antes del primer cambio; las sustituciones de archivos y M3U son atómicas. Si se interrumpe durante el commit, la siguiente apertura restaura los cambios. Si detecta una edición externa conflictiva, se detiene para no sobrescribirla.

Para recuperar un original descartado por deduplicación, abre **Recover Originals.command**, elige una transacción y encontrarás copias con sus nombres y rutas en `4. Others/Recovered originals …`. No deshace importaciones posteriores.

**Espacio:** las copias de seguridad se conservan intencionadamente. Durante una importación puede hacer falta varias veces el tamaño del lote; Recovery aumenta con las importaciones. No se purga automáticamente. Un disco lleno puede exigir liberar espacio antes de completar una recuperación. No expulses el dispositivo mientras la app trabaja. Los Staging de intentos fallidos se conservan para diagnóstico; no son música importada.

## Portabilidad en macOS

Requiere Python **3.9+** en el Mac y Picard **2.13.3**. En el Mac donde se construyó se detectaron Python 3.13.3 y Picard 2.13.3. El lanzador reconoce Homebrew, python.org y Python del sistema cuando cumple la versión. No depende de Homebrew para leer etiquetas.

Opcionalmente, una copia de `MusicBrainz Picard.app` en `Music Library App/Tools/` tiene prioridad sobre la instalación del Mac. La app de música y sus datos son portables; no se distribuye un runtime universal de Python/Picard. Otro Mac debe tener versiones y arquitectura compatibles. Si macOS bloquea un `.command` descargado, usa clic derecho → Abrir.

## Módulos y pruebas

- `storage.py`: rutas, bloqueo exclusivo, escrituras atómicas y transacciones.
- `metadata.py`: etiquetas, normalización, identidad y retagging de promociones.
- `picard.py`: integración real con 2.13.3.
- `engine.py`: planificación, deduplicación, promoción y commit.
- `playlists.py`: M3U, pistas pendientes e identidades estables.
- `ui.py`: pantallas sucesivas y acciones del teclado.

Pruebas locales: `python3 tests/test_musiclib.py` desde la carpeta de la app (necesitan ffmpeg solo para generar audio sintético). Las pruebas reales son opt-in y reciben una ruta de música; hacen copias y verifican que los hashes de los originales no cambian. Véase `VALIDATION.md` para resultados.

Se revisaron los seis automatismos originales del dispositivo. Se reutilizaron conceptualmente normalización Unicode, nombres, prioridad de año original, preferencia de formatos y M3U relativas. Se sustituyeron rutas fijas, borrados directos y equivalencia por tamaño por el catálogo y las transacciones. Los automatismos originales no se modificaron.

Fuentes comprobadas: [CLI 2.13](https://picard-docs.musicbrainz.org/en/v2.13/appendices/command_line.html), [procesamiento por lotes](https://picard-docs.musicbrainz.org/en/v2.13/usage/command_processing.html), [código de comandos de 2.13.3](https://github.com/metabrainz/picard/blob/release-2.13.3/picard/util/remotecommands.py), [ejecutor de 2.13.3](https://github.com/metabrainz/picard/blob/release-2.13.3/picard/tagger.py). El alias LOOKUP_CLUSTERED de un ejemplo de la documentación no existe en el código de esa versión; se usa LOOKUP clustered.
