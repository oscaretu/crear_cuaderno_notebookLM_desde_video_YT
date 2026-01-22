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
cp /mnt/c/Users/$USER/.notebooklm/storage_state.json ~/.notebooklm/
```

O usa el script auxiliar:
```bash
source zzz_asigna_ubicacion_fichero_configuracion.inc.sh
```

---

## Herramientas disponibles

| Herramienta | Descripción | Lenguaje |
|-------------|-------------|----------|
| `main.py` | Crear cuadernos con artefactos seleccionables | Python |
| `crear_cuaderno.sh` | Crear cuadernos (versión simplificada) | Bash |
| `listar_cuadernos.py` | Listar cuadernos disponibles | Python |
| `listar_cuadernos_como_JSON_ordenados_por_fecha.sh` | Listar cuadernos en JSON | Bash |

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

Versión: **0.6.0**

Crea automáticamente un cuaderno en NotebookLM a partir de un vídeo de YouTube. Por defecto solo genera el informe (sin límite diario).

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
| `--mostrar-descripcion` | Muestra la descripción del vídeo de YouTube | No |
| `--timeout-fuente` | Segundos máx. para esperar procesamiento de fuente | `60` |
| `--retardo` | Segundos de retardo entre inicio de cada generación | `3` |
| `--debug` | Activa trazas detalladas de ejecución | No |
| `--version`, `-v` | Muestra la versión del programa | - |

### Opciones de artefactos

| Opción | Descripción | Límite |
|--------|-------------|--------|
| (ninguna) | Solo genera report | No |
| `--report` | Generar informe | No |
| `--audio` | Generar resumen de audio | Sí |
| `--slides` | Generar presentación | Sí |
| `--infographic` | Generar infografía | Sí |
| `--todo` | Generar todos los artefactos | Mixto |

### Ejemplos de uso

```bash
# Solo informe (por defecto, sin límite)
python main.py "https://www.youtube.com/watch?v=VIDEO_ID"

# Todos los artefactos
python main.py "https://www.youtube.com/watch?v=VIDEO_ID" --todo

# Solo audio y slides
python main.py "https://www.youtube.com/watch?v=VIDEO_ID" --audio --slides

# Ver descripción del vídeo
python main.py "https://www.youtube.com/watch?v=VIDEO_ID" --mostrar-descripcion

# Crear cuaderno en inglés
python main.py "https://www.youtube.com/watch?v=VIDEO_ID" --idioma en

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

Versión: **1.3.0**

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
| `--mostrar-descripcion` | Mostrar descripción del vídeo | - |
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

# Ver descripción del vídeo
./crear_cuaderno.sh "https://www.youtube.com/watch?v=VIDEO_ID" --mostrar-descripcion
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

### Alternativa en Bash (JSON)

```bash
./listar_cuadernos_como_JSON_ordenados_por_fecha.sh
```

Devuelve la lista de cuadernos en formato JSON ordenados por fecha de creación (más recientes primero).

---

## Estructura del proyecto

```
crear_cuaderno_notebookLM_desde_video_YT/
├── main.py                                    # Crear cuadernos (Python)
├── crear_cuaderno.sh                          # Crear cuadernos (Bash)
├── listar_cuadernos.py                        # Listar cuadernos (Python)
├── listar_cuadernos_como_JSON_ordenados_por_fecha.sh  # Listar en JSON
├── zzz_asigna_ubicacion_fichero_configuracion.inc.sh  # Config WSL2
├── requirements.txt                           # Dependencias Python
├── CLAUDE.md                                  # Guía para Claude Code
├── README.md                                  # Esta documentación
└── .gitignore                                 # Archivos ignorados
```

## Comparativa main.py vs crear_cuaderno.sh

| Aspecto | main.py | crear_cuaderno.sh |
|---------|---------|-------------------|
| Artefactos por defecto | report | report, mind-map |
| Límites cuota | Evitados por defecto | Evitados por defecto |
| Idioma | Configurable (`--idioma`) | Forzado español |
| Dependencias | Python + asyncio | Bash + jq |
| Cuota compartida | Detecta y omite | No implementado |
| Orden generación | Sin límite primero, luego por tiempo | Sin límite primero, luego por tiempo |

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
source zzz_asigna_ubicacion_fichero_configuracion.inc.sh
```

O manualmente:
```bash
mkdir -p ~/.notebooklm
cp /mnt/c/Users/$USER/.notebooklm/storage_state.json ~/.notebooklm/
```

### Límite diario alcanzado

```
⚠ Presentación (Slides): Límite diario alcanzado
```

Opciones:
1. Esperar al día siguiente
2. Suscribirse a NotebookLM Plus
3. Usar los scripts sin opciones (solo genera artefactos sin límite)

### Error 403 Forbidden en yt-dlp

Usa `--debug` para ver detalles. Los errores 403 en algunas peticiones de yt-dlp son normales y no afectan la extracción de metadatos.
