# NotebookLM Tools

Herramientas de línea de comandos para automatizar tareas en Google NotebookLM.

## Requisitos previos

### Instalación

```bash
pip install -r requirements.txt
playwright install chromium
```

Para el script Bash también necesitas:
```bash
# jq para parsear JSON
sudo apt install jq  # Linux/WSL
brew install jq      # macOS
```

### Autenticación

Antes de usar cualquier herramienta, debes autenticarte con tu cuenta de Google:

```bash
notebooklm login
```

Se abrirá un navegador. Inicia sesión y espera a ver la página principal de NotebookLM, luego presiona ENTER en la terminal.

**Nota WSL2**: Si usas WSL2, las credenciales se guardan en `~/.notebooklm/`. Si te autenticas desde PowerShell, copia las credenciales:
```bash
cp /mnt/c/Users/TU_USUARIO/.notebooklm/storage_state.json ~/.notebooklm/
```

---

## Herramientas disponibles

| Herramienta | Descripción | Lenguaje |
|-------------|-------------|----------|
| `main.py` | Crear cuadernos con todos los artefactos | Python |
| `crear_cuaderno.sh` | Crear cuadernos (versión simplificada) | Bash |
| `listar_cuadernos.py` | Listar cuadernos disponibles | Python |

---

## Límites de cuota de NotebookLM

NotebookLM tiene límites diarios para ciertos tipos de artefactos:

| Artefacto | Límite diario |
|-----------|---------------|
| Report (Briefing Doc) | Sin límite |
| Mind Map | Sin límite |
| Audio (Podcast) | **Con límite** |
| Video | **Con límite** |
| Presentación (Slides) | **Con límite** |
| Infografía | **Con límite** |
| Quiz | **Con límite** |
| Flashcards | **Con límite** |

Si alcanzas el límite, espera al día siguiente o suscríbete a NotebookLM Plus.

---

## main.py - Crear cuadernos desde vídeos de YouTube (Python)

Versión: **0.3.3**

Crea automáticamente un cuaderno en NotebookLM a partir de un vídeo de YouTube, generando:
- Informe (Briefing Doc)
- Resumen de audio (podcast)
- Presentación (slides)
- Infografía

### Uso básico

```bash
python main.py <URL_YOUTUBE>
```

### Parámetros

| Parámetro | Descripción | Default |
|-----------|-------------|---------|
| `url` | URL del vídeo de YouTube (requerido) | - |
| `--idioma` | Código de idioma para los artefactos | `es` |
| `--mostrar-informe` | Muestra el contenido del informe por pantalla | No |
| `--timeout-fuente` | Segundos máx. para esperar procesamiento de fuente | `60` |
| `--retardo` | Segundos de retardo entre inicio de cada generación | `3` |
| `--debug` | Activa trazas detalladas de ejecución | No |
| `--version`, `-v` | Muestra la versión del programa | - |

### Ejemplos de uso

```bash
# Crear cuaderno con idioma español (por defecto)
python main.py "https://www.youtube.com/watch?v=VIDEO_ID"

# Crear cuaderno en inglés
python main.py "https://www.youtube.com/watch?v=VIDEO_ID" --idioma en

# Crear cuaderno y mostrar el informe
python main.py "https://www.youtube.com/watch?v=VIDEO_ID" --mostrar-informe

# Ajustar tiempos de espera
python main.py "https://www.youtube.com/watch?v=VIDEO_ID" --timeout-fuente 90 --retardo 5

# Ejecutar con modo debug
python main.py "https://www.youtube.com/watch?v=VIDEO_ID" --debug
```

### Manejo de límites de cuota

El script detecta cuando se alcanza el límite diario y muestra un mensaje claro:

```
[12:30:45] ⚠ Presentación (Slides): Límite diario alcanzado
           Espera al día siguiente o suscríbete a NotebookLM Plus
[--:--:--] ⏭ Infografía: Omitido (cuota compartida agotada)
```

Las presentaciones e infografías comparten cuota; si una falla por límite, la otra se omite automáticamente.

---

## crear_cuaderno.sh - Crear cuadernos (Bash)

Versión: **1.1.0**

Versión simplificada en Bash que usa el CLI `notebooklm` directamente. Por defecto solo genera artefactos sin límites de cuota.

### Uso básico

```bash
./crear_cuaderno.sh <URL_YOUTUBE> [opciones]
```

### Opciones

| Opción | Descripción | Límite |
|--------|-------------|--------|
| (ninguna) | Genera Report y Mind Map | No |
| `--audio` | Añadir podcast | Sí |
| `--video` | Añadir video | Sí |
| `--slides` | Añadir presentación | Sí |
| `--infographic` | Añadir infografía | Sí |
| `--quiz` | Añadir quiz | Sí |
| `--flashcards` | Añadir flashcards | Sí |
| `--todo` | Generar todos los artefactos | Mixto |
| `--solo-limite` | Solo artefactos con límite | Sí |
| `-h`, `--help` | Mostrar ayuda | - |

### Ejemplos de uso

```bash
# Solo artefactos sin límite (report + mind-map)
./crear_cuaderno.sh "https://www.youtube.com/watch?v=VIDEO_ID"

# Añadir podcast
./crear_cuaderno.sh "https://www.youtube.com/watch?v=VIDEO_ID" --audio

# Añadir presentación e infografía
./crear_cuaderno.sh "https://www.youtube.com/watch?v=VIDEO_ID" --slides --infographic

# Generar todos los artefactos
./crear_cuaderno.sh "https://www.youtube.com/watch?v=VIDEO_ID" --todo
```

### Salida de ejemplo

```
NotebookLM YouTube Importer (Bash) v1.1.0
Idioma forzado: es
Artefactos sin límite: report mind-map
Artefactos con límite: audio
  (pueden fallar si se alcanzó el límite diario)

Video ID: dQw4w9WgXcQ
Obteniendo metadatos del video...
  Título: Rick Astley - Never Gonna Give You Up
  Canal: Rick Astley
  Fecha: 2009-10-25

Nombre del cuaderno: YT-dQw4w9WgXcQ - Rick Astley - Never Gonna Give... - 2009-10-25 - Rick Astley

Buscando cuaderno existente...
Cuaderno creado: abc123-def456
URL: https://notebooklm.google.com/notebook/abc123-def456

Añadiendo video como fuente...
Fuente añadida

Estado de artefactos:
  ✗ Report (Briefing Doc): no disponible
  ✗ Mind Map: no disponible
  ✗ Audio (Podcast): no disponible (⚠ límite)

Generando 3 artefacto(s)...

[12:30:45] Generando: Report (Briefing Doc)
[12:30:52] ✓ Report (Briefing Doc) generado

[12:30:52] Generando: Mind Map
[12:30:55] ✓ Mind Map generado

[12:30:55] Generando: Audio (Podcast) (⚠ límite diario)
[12:31:02] ✓ Audio (Podcast) generado

Artefactos generados: 3/3

==================================================
Proceso completado
  Cuaderno: YT-dQw4w9WgXcQ - Rick Astley - Never Gonna Give... - 2009-10-25 - Rick Astley
  URL: https://notebooklm.google.com/notebook/abc123-def456
==================================================
```

### Requisitos adicionales

- `notebooklm` CLI instalado y autenticado
- `yt-dlp` para metadatos del video
- `jq` para parsear JSON

---

## listar_cuadernos.py - Listar cuadernos disponibles

Muestra todos los cuadernos de tu cuenta de NotebookLM con opciones de ordenación.

### Uso básico

```bash
python listar_cuadernos.py
```

### Parámetros

| Parámetro | Descripción | Default |
|-----------|-------------|---------|
| `--ordenar` | Campo de ordenación: `nombre`, `creacion`, `modificacion` | `nombre` |
| `--desc` | Orden descendente | ascendente |
| `--idioma` | Filtrar por idioma de artefactos (ej: `es`, `en`) | ninguno |

**Nota**: La opción `--idioma` actualmente no funciona correctamente porque la API de NotebookLM no expone el idioma de los artefactos. La opción `--ordenar modificacion` tampoco funciona porque la API solo proporciona fecha de creación.

### Ejemplos de uso

```bash
# Listar por nombre (A-Z)
python listar_cuadernos.py

# Listar por nombre (Z-A)
python listar_cuadernos.py --ordenar nombre --desc

# Listar por fecha de creación (más recientes primero)
python listar_cuadernos.py --ordenar creacion --desc
```

---

## Estructura del proyecto

```
crear_cuaderno_notebookLM_desde_video_YT/
├── main.py              # Crear cuadernos desde YouTube (Python)
├── crear_cuaderno.sh    # Crear cuadernos desde YouTube (Bash)
├── listar_cuadernos.py  # Listar cuadernos disponibles
├── requirements.txt     # Dependencias Python
├── README.md            # Esta documentación
└── .gitignore           # Archivos ignorados por git
```

## Comparativa main.py vs crear_cuaderno.sh

| Aspecto | main.py | crear_cuaderno.sh |
|---------|---------|-------------------|
| Artefactos por defecto | report, audio, slides, infographic | report, mind-map |
| Límites cuota | Sí (con manejo inteligente) | Evitados por defecto |
| Idioma | Configurable (`--idioma`) | Forzado español |
| Dependencias | Python + asyncio | Bash + jq |
| Complejidad | Mayor (más funciones) | Menor (más simple) |
| Cuota compartida | Detecta y omite | No implementado |

## Notas

- **Idioma**: El informe y el audio se generan en el idioma especificado (español por defecto).

- **Cuadernos duplicados**: Los scripts detectan cuadernos existentes por el ID del vídeo (prefijo `YT-{video_id}`). Si ejecutas el script dos veces con el mismo vídeo, no creará un cuaderno duplicado.

- **Límites de NotebookLM**:
  - 100 cuadernos máximo
  - 50 fuentes por cuaderno
  - Límites diarios en generación de ciertos artefactos

## Solución de problemas

### Error de autenticación

```
Error: Missing required cookies: {'SID'}
```

Ejecuta `notebooklm login` y asegúrate de completar el proceso de autenticación.

### Error en WSL2

Si te autenticaste desde PowerShell pero ejecutas desde WSL2:
```bash
mkdir -p ~/.notebooklm
cp /mnt/c/Users/TU_USUARIO/.notebooklm/storage_state.json ~/.notebooklm/
```

### Límite diario alcanzado

```
⚠ Presentación (Slides): Límite diario alcanzado
```

Opciones:
1. Esperar al día siguiente
2. Suscribirse a NotebookLM Plus
3. Usar `crear_cuaderno.sh` sin opciones (solo genera artefactos sin límite)

### Error 403 Forbidden en yt-dlp

Usa `--debug` para ver detalles. Los errores 403 en algunas peticiones de yt-dlp son normales y no afectan la extracción de metadatos.
