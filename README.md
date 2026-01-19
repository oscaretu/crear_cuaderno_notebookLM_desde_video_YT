# NotebookLM Tools

Herramientas de línea de comandos para automatizar tareas en Google NotebookLM.

## Requisitos previos

### Instalación

```bash
pip install -r requirements.txt
playwright install chromium
```

### Autenticación

Antes de usar cualquier herramienta, debes autenticarte con tu cuenta de Google:

```bash
notebooklm login
```

Se abrirá un navegador. Inicia sesión y espera a ver la página principal de NotebookLM, luego presiona ENTER en la terminal.

---

## main.py - Crear cuadernos desde vídeos de YouTube

Crea automáticamente un cuaderno en NotebookLM a partir de un vídeo de YouTube, generando:
- Informe (Study Guide)
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
| `--idioma` | Código de idioma para informe y audio | `es` |
| `--mostrar-informe` | Muestra el contenido del informe por pantalla | No |
| `--debug` | Activa trazas detalladas de ejecución | No |

### Ejemplos de uso

#### Crear cuaderno con idioma español (por defecto)

```bash
python main.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

**Salida:**
```
Nota: Usando idioma español por defecto. Usa --idioma para cambiar (ej: --idioma en)
Video ID: dQw4w9WgXcQ
Idioma para contenido: es
Obteniendo metadatos del vídeo...
  Título: Rick Astley - Never Gonna Give You Up
  Canal: Rick Astley
  Fecha: 2009-10-25
Conectando con NotebookLM...
Buscando cuaderno existente para: dQw4w9WgXcQ
Creando cuaderno: YT-dQw4w9WgXcQ - Rick Astley - Never Gonna Give You Up - 2009-10-25 - Rick Astley
✓ Cuaderno creado (ID: abc123-def456)
Añadiendo vídeo como fuente: https://www.youtube.com/watch?v=dQw4w9WgXcQ
✓ Fuente añadida
Esperando a que se procese la fuente...

Lanzando generación de artefactos en paralelo (idioma: es)...
  → Iniciando: Informe
  → Iniciando: Resumen de Audio
  → Iniciando: Presentación (Slides)
  → Iniciando: Infografía
  ✓ Completado: Informe
  ✓ Completado: Presentación (Slides)
  ✓ Completado: Infografía
  ✓ Completado: Resumen de Audio

  Artefactos generados: 4/4

==================================================
✓ Proceso completado
  Cuaderno: YT-dQw4w9WgXcQ - Rick Astley - Never Gonna Give You Up - 2009-10-25 - Rick Astley
  URL: https://notebooklm.google.com/notebook/abc123-def456
```

#### Crear cuaderno en inglés

```bash
python main.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --idioma en
```

#### Crear cuaderno y mostrar el informe

```bash
python main.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --mostrar-informe
```

**Salida adicional:**
```
============================================================
CONTENIDO DEL INFORME
============================================================
# Guía de Estudio: Rick Astley - Never Gonna Give You Up

## Resumen
Este vídeo musical presenta la icónica canción de Rick Astley...

## Puntos clave
- Lanzado en 1987
- Género: Pop, Dance
...
============================================================
```

#### Ejecutar con modo debug

```bash
python main.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --debug
```

**Salida adicional:**
```
[DEBUG] Modo DEBUG activado
[DEBUG] Argumentos: url=https://www.youtube.com/watch?v=dQw4w9WgXcQ, mostrar_informe=False, idioma=es
[DEBUG] ============================================================
[DEBUG] INICIO procesar_video()
[DEBUG]   URL: https://www.youtube.com/watch?v=dQw4w9WgXcQ
[DEBUG]   mostrar_informe: False
[DEBUG]   idioma: es
[DEBUG] ============================================================
[DEBUG] PASO 1: Validar URL y extraer video_id
[DEBUG]   video_id extraído: dQw4w9WgXcQ
[DEBUG] PASO 2: Obtener metadatos del vídeo con yt-dlp
[DEBUG] Iniciando extracción de metadatos para: https://www.youtube.com/watch?v=dQw4w9WgXcQ
...
```

#### Ejecutar sobre un cuaderno existente

Si el cuaderno ya existe, muestra el estado de los artefactos y genera los faltantes:

```bash
python main.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

**Salida:**
```
Nota: Usando idioma español por defecto. Usa --idioma para cambiar (ej: --idioma en)
Video ID: dQw4w9WgXcQ
Idioma para contenido: es
Obteniendo metadatos del vídeo...
  Título: Rick Astley - Never Gonna Give You Up
  Canal: Rick Astley
  Fecha: 2009-10-25
Conectando con NotebookLM...
Buscando cuaderno existente para: dQw4w9WgXcQ
✓ Cuaderno ya existe: YT-dQw4w9WgXcQ - Rick Astley - Never Gonna Give You Up - 2009-10-25 - Rick Astley
  ID: abc123-def456
  URL: https://notebooklm.google.com/notebook/abc123-def456

Verificando artefactos existentes (idioma: es)...

Estado de artefactos:
  ✓ Informe: Study Guide
  ✓ Resumen de Audio: Deep Dive Conversation
  ✓ Presentación (Slides): Detailed Deck
  ✗ Infografía: no disponible

Generando 1 artefacto(s) faltante(s)...

Lanzando generación de artefactos en paralelo (idioma: es)...
  → Iniciando: Infografía
  ✓ Completado: Infografía

  Artefactos generados: 1/1

==================================================
  Visita NotebookLM para ver los resultados:
  https://notebooklm.google.com/notebook/abc123-def456
```

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

### Ejemplos de uso

#### Listar por nombre (A-Z)

```bash
python listar_cuadernos.py
```

**Salida:**
```
Conectando con NotebookLM...
Obteniendo lista de cuadernos...

================================================================================
CUADERNOS DISPONIBLES (3 total)
Ordenados por: nombre (ascendente)
================================================================================

  1. Apuntes de Python
     ID: 11111111-1111-1111-1111-111111111111
     URL: https://notebooklm.google.com/notebook/11111111-1111-1111-1111-111111111111
     Creado: 2024-01-10 14:30
     Modificado: 2024-01-15 09:45

  2. Proyecto Machine Learning
     ID: 22222222-2222-2222-2222-222222222222
     URL: https://notebooklm.google.com/notebook/22222222-2222-2222-2222-222222222222
     Creado: 2024-01-05 10:00
     Modificado: 2024-01-18 16:20

  3. YT-dQw4w9WgXcQ - Rick Astley - Never Gonna Give You Up - 2009-10-25 - Rick Astley
     ID: 33333333-3333-3333-3333-333333333333
     URL: https://notebooklm.google.com/notebook/33333333-3333-3333-3333-333333333333
     Creado: 2024-01-19 08:00
     Modificado: 2024-01-19 08:15

================================================================================
Total: 3 cuaderno(s)
```

#### Listar por nombre (Z-A)

```bash
python listar_cuadernos.py --ordenar nombre --desc
```

#### Listar por fecha de creación (más antiguos primero)

```bash
python listar_cuadernos.py --ordenar creacion
```

#### Listar por fecha de creación (más recientes primero)

```bash
python listar_cuadernos.py --ordenar creacion --desc
```

**Salida:**
```
Conectando con NotebookLM...
Obteniendo lista de cuadernos...

================================================================================
CUADERNOS DISPONIBLES (3 total)
Ordenados por: creacion (descendente)
================================================================================

  1. YT-dQw4w9WgXcQ - Rick Astley - Never Gonna Give You Up - 2009-10-25 - Rick Astley
     ID: 33333333-3333-3333-3333-333333333333
     URL: https://notebooklm.google.com/notebook/33333333-3333-3333-3333-333333333333
     Creado: 2024-01-19 08:00
     Modificado: 2024-01-19 08:15

  2. Apuntes de Python
     ID: 11111111-1111-1111-1111-111111111111
     URL: https://notebooklm.google.com/notebook/11111111-1111-1111-1111-111111111111
     Creado: 2024-01-10 14:30
     Modificado: 2024-01-15 09:45

  3. Proyecto Machine Learning
     ID: 22222222-2222-2222-2222-222222222222
     URL: https://notebooklm.google.com/notebook/22222222-2222-2222-2222-222222222222
     Creado: 2024-01-05 10:00
     Modificado: 2024-01-18 16:20

================================================================================
Total: 3 cuaderno(s)
```

#### Listar por fecha de modificación (más recientes primero)

```bash
python listar_cuadernos.py --ordenar modificacion --desc
```

---

## Estructura del proyecto

```
crear_cuaderno_notebookLM_desde_video_YT/
├── main.py              # Crear cuadernos desde YouTube
├── listar_cuadernos.py  # Listar cuadernos disponibles
├── requirements.txt     # Dependencias Python
├── README.md            # Esta documentación
└── .gitignore           # Archivos ignorados por git
```

## Notas

- **Idioma**: El informe y el audio se generan en el idioma especificado (español por defecto). Las presentaciones e infografías no soportan selección de idioma.

- **Cuadernos duplicados**: El script detecta cuadernos existentes por el ID del vídeo. Si ejecutas el script dos veces con el mismo vídeo, no creará un cuaderno duplicado.

- **Artefactos en diferentes idiomas**: Si tienes un informe en inglés y ejecutas el script con `--idioma es`, se generará un nuevo informe en español.

- **Límites gratuitos de NotebookLM**:
  - 100 cuadernos máximo
  - 50 fuentes por cuaderno
  - Generación limitada de multimedia por cuaderno

## Solución de problemas

### Error de autenticación

```
Error: Missing required cookies: {'SID'}
```

Ejecuta `notebooklm login` y asegúrate de completar el proceso de autenticación.

### Error 403 Forbidden en yt-dlp

Usa `--debug` para ver detalles. Los errores 403 en algunas peticiones de yt-dlp son normales y no afectan la extracción de metadatos.
