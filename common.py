"""
Módulo común con funciones y constantes compartidas entre los scripts de NotebookLM.

Usado por: main.py, ver_cuaderno.py
"""

import asyncio
import tempfile
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from rich import box

# Inicializar consola global
console = Console()

# Constantes para tipos de artefactos (StudioContentType)
STUDIO_AUDIO = 1
STUDIO_REPORT = 2
STUDIO_VIDEO = 3
STUDIO_QUIZ = 4  # También flashcards (variant distingue)
STUDIO_MIND_MAP = 5
STUDIO_INFOGRAPHIC = 7
STUDIO_SLIDE_DECK = 8
STUDIO_DATA_TABLE = 9

# Estado completado de artefacto
ARTIFACT_STATUS_COMPLETED = 3


def extraer_url_de_artefacto_raw(artifact_raw: list, artifact_type: int) -> str | None:
    """Extrae la URL de descarga de un artefacto raw según su tipo.

    Replica la lógica de extracción de notebooklm-py para cada tipo.

    Args:
        artifact_raw: Datos raw del artefacto de la API
        artifact_type: Tipo de artefacto (StudioContentType)

    Returns:
        URL de descarga o None si no está disponible
    """
    try:
        if artifact_type == STUDIO_AUDIO:
            # Audio: artifact[6][5] contiene lista de medios
            if len(artifact_raw) <= 6:
                return None
            metadata = artifact_raw[6]
            if not isinstance(metadata, list) or len(metadata) <= 5:
                return None
            media_list = metadata[5]
            if not isinstance(media_list, list) or len(media_list) == 0:
                return None
            # Buscar audio/mp4
            for item in media_list:
                if isinstance(item, list) and len(item) > 2 and item[2] == "audio/mp4":
                    return item[0]
            # Fallback: primer item
            if isinstance(media_list[0], list) and len(media_list[0]) > 0:
                return media_list[0][0]

        elif artifact_type == STUDIO_VIDEO:
            # Video: artifact[8] contiene metadatos con URLs
            if len(artifact_raw) <= 8:
                return None
            metadata = artifact_raw[8]
            if not isinstance(metadata, list):
                return None
            # Buscar lista con URLs http
            media_list = None
            for item in metadata:
                if (isinstance(item, list) and len(item) > 0 and
                    isinstance(item[0], list) and len(item[0]) > 0 and
                    isinstance(item[0][0], str) and item[0][0].startswith("http")):
                    media_list = item
                    break
            if not media_list:
                return None
            # Buscar video/mp4
            for item in media_list:
                if isinstance(item, list) and len(item) > 2 and item[2] == "video/mp4":
                    return item[0]
            # Fallback
            if isinstance(media_list[0], list) and len(media_list[0]) > 0:
                return media_list[0][0]

        elif artifact_type == STUDIO_INFOGRAPHIC:
            # Infographic: buscar al revés en el artefacto
            for item in reversed(artifact_raw):
                if not isinstance(item, list) or len(item) == 0:
                    continue
                if not isinstance(item[0], list):
                    continue
                if len(item) <= 2 or not isinstance(item[2], list) or len(item[2]) == 0:
                    continue
                content_list = item[2]
                if not isinstance(content_list[0], list) or len(content_list[0]) <= 1:
                    continue
                img_data = content_list[0][1]
                if (isinstance(img_data, list) and len(img_data) > 0 and
                    isinstance(img_data[0], str) and img_data[0].startswith("http")):
                    return img_data[0]

        elif artifact_type == STUDIO_SLIDE_DECK:
            # Slides: artifact[16][3] contiene URL del PDF
            if len(artifact_raw) <= 16:
                return None
            metadata = artifact_raw[16]
            if not isinstance(metadata, list) or len(metadata) <= 3:
                return None
            pdf_url = metadata[3]
            if isinstance(pdf_url, str) and pdf_url.startswith("http"):
                return pdf_url

    except (IndexError, TypeError):
        pass

    return None


async def obtener_urls_artefactos(client, notebook_id: str) -> dict[str, tuple[str, int]]:
    """Obtiene las URLs de descarga de los artefactos de un cuaderno.

    Args:
        client: Cliente de NotebookLM
        notebook_id: ID del cuaderno

    Returns:
        Diccionario {artifact_id: (url, artifact_type)}
    """
    urls = {}
    try:
        # Obtener datos raw de artefactos
        artifacts_raw = await client.artifacts._list_raw(notebook_id)

        for art in artifacts_raw:
            if not isinstance(art, list) or len(art) < 5:
                continue

            artifact_id = art[0]
            artifact_type = art[2]
            artifact_status = art[4]
            artifact_title = art[1] if len(art) > 1 else ""

            # Solo procesar artefactos completados
            if artifact_status != ARTIFACT_STATUS_COMPLETED:
                continue

            url = extraer_url_de_artefacto_raw(art, artifact_type)
            if url:
                # Guardar URL y tipo (el nombre se genera después con el título del Artifact)
                urls[artifact_id] = (url, artifact_type)

    except Exception as e:
        debug(f"Error obteniendo URLs de artefactos: {e}")

    return urls


def _extension_por_tipo(artifact_type: int) -> str:
    """Devuelve la extensión de archivo según el tipo de artefacto."""
    extensiones = {
        STUDIO_AUDIO: ".mp4",
        STUDIO_VIDEO: ".mp4",
        STUDIO_INFOGRAPHIC: ".png",
        STUDIO_SLIDE_DECK: ".pdf",
    }
    return extensiones.get(artifact_type, "")


def _subcomando_por_tipo(artifact_type: int) -> str:
    """Devuelve el subcomando de notebooklm download según el tipo de artefacto."""
    subcomandos = {
        STUDIO_AUDIO: "audio",
        STUDIO_VIDEO: "video",
        STUDIO_INFOGRAPHIC: "infographic",
        STUDIO_SLIDE_DECK: "slide-deck",
    }
    return subcomandos.get(artifact_type, "")


def _limpiar_nombre_archivo(titulo: str) -> str:
    """Limpia un título para usarlo como nombre de archivo."""
    if not titulo:
        return ""
    import re
    import unicodedata
    # Normalizar acentos: convertir á->a, é->e, ñ->n, etc.
    nombre = unicodedata.normalize('NFKD', titulo)
    nombre = ''.join(c for c in nombre if not unicodedata.combining(c))
    # Reemplazar caracteres no válidos, comas y espacios
    nombre = re.sub(r'[<>:"/\\|?*]', '_', nombre)
    nombre = nombre.replace(',', '_')
    nombre = nombre.replace(' ', '_')
    nombre = nombre.strip()
    # Limitar longitud
    if len(nombre) > 100:
        nombre = nombre[:100]
    return nombre

# Variable global para modo debug
DEBUG = False


def set_debug(valor: bool):
    """Activa o desactiva el modo debug."""
    global DEBUG
    DEBUG = valor


def timestamp() -> str:
    """Devuelve la hora actual formateada HH:MM:SS."""
    return datetime.now().strftime("%H:%M:%S")


def debug(mensaje: str):
    """Imprime mensaje de debug si el modo está activo."""
    if DEBUG:
        console.print(f"[dim yellow][DEBUG] {mensaje}[/dim yellow]")


# Mapeo de tipos de artefactos (ordenados: sin límite primero, luego por tiempo)
# Formato: (nombre_display, tiene_limite_diario)
# Sin límite: report, mind_map, data_table
# Con límite: slides, infographic (comparten cuota), quiz, flashcards, audio, video
TIPOS_ARTEFACTOS = {
    'report': ('Informe', False),
    'mind_map': ('Mapa Mental', False),
    'data_table': ('Tabla de Datos', False),
    'slides': ('Presentación (Slides)', True),
    'infographic': ('Infografía', True),
    'quiz': ('Cuestionario', True),
    'flashcards': ('Tarjetas Didácticas', True),
    'audio': ('Resumen de Audio', True),
    'video': ('Video', True),
}

# Lista ordenada de tipos (el orden importa para generación)
# Sin límite primero, luego con límite (video último por ser el más lento)
ORDEN_ARTEFACTOS = ['report', 'mind_map', 'data_table', 'slides', 'infographic', 'quiz', 'flashcards', 'audio', 'video']


def artefacto_tiene_idioma(artefacto, idioma: str) -> bool:
    """Verifica si un artefacto está en el idioma especificado."""
    # Intentar obtener el idioma del artefacto
    lang = getattr(artefacto, 'language', None)
    if lang:
        debug(f"      Artefacto tiene language={lang}, buscando={idioma}")
        return lang.lower().startswith(idioma.lower())

    # Si no hay atributo language, intentar detectar por título
    title = getattr(artefacto, 'title', '') or ''
    debug(f"      Artefacto sin language, título={title}")

    # Heurística: algunos títulos incluyen indicadores de idioma
    # Por ahora, si no podemos determinar el idioma, asumimos que coincide
    return True


async def verificar_artefactos_existentes(client, notebook_id: str, idioma: str = 'es') -> tuple[dict, dict]:
    """Verifica qué artefactos ya existen en el cuaderno en el idioma especificado.

    Returns:
        Tupla (existentes, urls) donde:
        - existentes: dict con listas de artefactos por tipo
        - urls: dict {artifact_id: url} con URLs de descarga
    """
    debug(f"Verificando artefactos en notebook: {notebook_id} (idioma: {idioma})")
    existentes = {
        'report': [],
        'mind_map': [],
        'data_table': [],
        'slides': [],
        'infographic': [],
        'quiz': [],
        'flashcards': [],
        'audio': [],
        'video': [],
    }
    urls = {}

    try:
        # Listar cada tipo de artefacto (con spinner visual si no hay barra de progreso externa)
        with console.status(f"[bold green]Verificando artefactos existentes ({idioma})...", spinner="dots"):
            debug("  Buscando reports...")
            try:
                reports = await client.artifacts.list_reports(notebook_id)
                debug(f"    Reports encontrados: {len(reports) if reports else 0}")
                if reports:
                    for report in reports:
                        if artefacto_tiene_idioma(report, idioma):
                            existentes['report'].append(report)
            except Exception as e:
                debug(f"    Error listando reports: {e}")

            debug("  Buscando audios...")
            try:
                audios = await client.artifacts.list_audio(notebook_id)
                debug(f"    Audios encontrados: {len(audios) if audios else 0}")
                if audios:
                    for audio in audios:
                        if artefacto_tiene_idioma(audio, idioma):
                            existentes['audio'].append(audio)
            except Exception as e:
                debug(f"    Error listando audios: {e}")

            debug("  Buscando slides...")
            try:
                slides = await client.artifacts.list_slide_decks(notebook_id)
                debug(f"    Slides encontrados: {len(slides) if slides else 0}")
                if slides:
                    existentes['slides'] = list(slides)
            except Exception as e:
                debug(f"    Error listando slides: {e}")

            debug("  Buscando infographics...")
            try:
                infographics = await client.artifacts.list_infographics(notebook_id)
                debug(f"    Infographics encontrados: {len(infographics) if infographics else 0}")
                if infographics:
                    existentes['infographic'] = list(infographics)
            except Exception as e:
                debug(f"    Error listando infographics: {e}")

            debug("  Buscando videos...")
            try:
                videos = await client.artifacts.list_video(notebook_id)
                debug(f"    Videos encontrados: {len(videos) if videos else 0}")
                if videos:
                    existentes['video'] = list(videos)
            except Exception as e:
                debug(f"    Error listando videos: {e}")

            debug("  Buscando mind_maps...")
            try:
                # Mind maps usan el método list() con tipo 5
                mind_maps = await client.artifacts.list(notebook_id, 5)
                debug(f"    Mind maps encontrados: {len(mind_maps) if mind_maps else 0}")
                if mind_maps:
                    existentes['mind_map'] = list(mind_maps)
            except Exception as e:
                debug(f"    Error listando mind_maps: {e}")

            debug("  Buscando data_tables...")
            try:
                data_tables = await client.artifacts.list_data_tables(notebook_id)
                debug(f"    Data tables encontrados: {len(data_tables) if data_tables else 0}")
                if data_tables:
                    existentes['data_table'] = list(data_tables)
            except Exception as e:
                debug(f"    Error listando data_tables: {e}")

            debug("  Buscando quizzes...")
            try:
                quizzes = await client.artifacts.list_quizzes(notebook_id)
                debug(f"    Quizzes encontrados: {len(quizzes) if quizzes else 0}")
                if quizzes:
                    existentes['quiz'] = list(quizzes)
            except Exception as e:
                debug(f"    Error listando quizzes: {e}")

            debug("  Buscando flashcards...")
            try:
                flashcards = await client.artifacts.list_flashcards(notebook_id)
                debug(f"    Flashcards encontrados: {len(flashcards) if flashcards else 0}")
                if flashcards:
                    existentes['flashcards'] = list(flashcards)
            except Exception as e:
                debug(f"    Error listando flashcards: {e}")

    except Exception as e:
        console.print(f"[bold red]⚠ Error al verificar artefactos: {e}[/bold red]")
        debug(f"  Excepción general: {e}")

    # Obtener URLs de descarga
    debug("  Obteniendo URLs de descarga...")
    try:
        urls = await obtener_urls_artefactos(client, notebook_id)
        debug(f"    URLs encontradas: {len(urls)}")
    except Exception as e:
        debug(f"    Error obteniendo URLs: {e}")

    resumen = ", ".join(f"{k}={len(v)}" for k, v in existentes.items())
    debug(f"Resumen artefactos: {resumen}")
    return existentes, urls


async def generar_artefactos(client, notebook_id: str, faltantes: list[str], idioma: str = 'es', retardo_entre_tareas: float = 3.0) -> int:
    """Genera los artefactos especificados en paralelo con retardo escalonado.
    
    Args:
        client: Cliente de NotebookLM
        notebook_id: ID del cuaderno
        faltantes: Lista de tipos de artefactos a generar
        idioma: Código de idioma para los artefactos
        retardo_entre_tareas: Segundos de retardo entre el inicio de cada tarea
        
    Returns:
        Cantidad de artefactos generados exitosamente.
    """
    debug(f"Generando artefactos faltantes: {faltantes} (idioma: {idioma}, retardo: {retardo_entre_tareas}s)")

    if not faltantes:
        debug("No hay artefactos faltantes, retornando 0")
        return 0

    # Configuración de artefactos y cuotas
    # slides e infographic comparten cuota 'premium'
    CUOTA_COMPARTIDA = {
        'slides': 'premium', 'infographic': 'premium',
    }
    # Artefactos que no devuelven GenerationStatus (no usan wait_for_completion)
    ARTEFACTOS_SINCRONOS = {'mind_map'}

    CONFIG_ARTEFACTOS = {
        'report': ('Informe', client.artifacts.generate_report, {'language': idioma}),
        'mind_map': ('Mapa Mental', client.artifacts.generate_mind_map, {}),  # No acepta language
        'data_table': ('Tabla de Datos', client.artifacts.generate_data_table, {'language': idioma}),
        'slides': ('Presentación (Slides)', client.artifacts.generate_slide_deck, {'language': idioma}),
        'infographic': ('Infografía', client.artifacts.generate_infographic, {'language': idioma}),
        'quiz': ('Cuestionario', client.artifacts.generate_quiz, {}),  # No acepta language
        'flashcards': ('Tarjetas Didácticas', client.artifacts.generate_flashcards, {}),  # No acepta language
        'audio': ('Resumen de Audio', client.artifacts.generate_audio, {'language': idioma}),
        'video': ('Video', client.artifacts.generate_video, {'language': idioma}),
    }

    exitosos = 0
    cuotas_agotadas = set()
    
    console.print(f"\n[bold cyan]Iniciando generación de {len(faltantes)} artefactos...[/bold cyan]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        
        task_total = progress.add_task("[bold]Progreso General", total=len(faltantes))
        
        for i, tipo in enumerate(faltantes):
            nombre_display, generar_func, kwargs = CONFIG_ARTEFACTOS[tipo]
            grupo_cuota = CUOTA_COMPARTIDA.get(tipo)
            
            # Verificar cuota compartida antes de empezar
            if grupo_cuota and grupo_cuota in cuotas_agotadas:
                console.print(f"[yellow]⏭ {nombre_display}: Omitido (cuota '{grupo_cuota}' agotada)[/yellow]")
                progress.advance(task_total)
                continue

            # Retardo entre tareas
            if i > 0:
                task_wait = progress.add_task(f"[dim]Esperando {retardo_entre_tareas}s...", total=retardo_entre_tareas)
                # Simular espera visual
                for _ in range(int(retardo_entre_tareas * 10)):
                    await asyncio.sleep(0.1)
                    progress.update(task_wait, advance=0.1)
                progress.update(task_wait, visible=False) # Ocultar espera al terminar

            # Tarea actual
            task_current = progress.add_task(f"Generando {nombre_display}...", total=None) # Indeterminado
            
            try:
                debug(f"  Iniciando {nombre_display}")
                resultado = await generar_func(notebook_id, **kwargs)

                # Artefactos síncronos (mind_map) devuelven dict, no GenerationStatus
                if tipo in ARTEFACTOS_SINCRONOS:
                    if resultado and resultado.get('mind_map'):
                        console.print(f"[bold green]✓ Completado: {nombre_display}[/bold green]")
                        exitosos += 1
                    else:
                        console.print(f"[red]✗ Error en {nombre_display}: No se pudo generar[/red]")
                    progress.update(task_current, completed=100, visible=False)
                    progress.advance(task_total)
                    continue

                # Check inmediato de error/cuota para artefactos asíncronos
                if resultado and getattr(resultado, 'status', None) == 'failed':
                    if hasattr(resultado, 'is_rate_limited') and resultado.is_rate_limited:
                        console.print(f"[bold red]⚠ {nombre_display}: Límite diario alcanzado[/bold red]")
                        cuotas_agotadas.add(grupo_cuota)
                        progress.update(task_current, completed=0, visible=False)
                    else:
                        error_msg = getattr(resultado, 'error', 'Error desconocido')
                        console.print(f"[red]✗ Error en {nombre_display}: {error_msg}[/red]")
                        progress.update(task_current, completed=0, visible=False)
                    progress.advance(task_total)
                    continue

                # Esperar completado
                if resultado and getattr(resultado, 'task_id', None):
                    progress.update(task_current, description=f"Procesando {nombre_display}...")
                    await client.artifacts.wait_for_completion(notebook_id, resultado.task_id)

                console.print(f"[bold green]✓ Completado: {nombre_display}[/bold green]")
                exitosos += 1
                progress.update(task_current, completed=100, visible=False)
                
            except Exception as e:
                console.print(f"[bold red]✗ Excepción en {nombre_display}: {e}[/bold red]")
                debug(f"Excepción: {e}")
                progress.update(task_current, visible=False)
            
            progress.advance(task_total)

    return exitosos


async def mostrar_informe(client, notebook_id: str):
    """Descarga y muestra el contenido del informe."""
    try:
        with console.status("[bold green]Descargando informe...", spinner="dots"):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                temp_path = f.name
            await client.artifacts.download_report(notebook_id, temp_path)
            contenido = Path(temp_path).read_text(encoding='utf-8')
            Path(temp_path).unlink(missing_ok=True)

        console.print("\n[bold]CONTENIDO DEL INFORME[/bold]", style="underline")
        console.print(contenido)
        console.print("="*60)

    except Exception as e:
        console.print(f"[bold red]✗ Error al obtener el informe: {e}[/bold red]")


def mostrar_estado_artefactos(existentes: dict, urls: dict = None, notebook_id: str = None) -> tuple[list[str], list[str]]:
    """Muestra tabla de estado de artefactos y devuelve faltantes.

    Args:
        existentes: Diccionario con listas de artefactos por tipo.
        urls: Diccionario {artifact_id: (url, artifact_type)} con URLs de descarga.
        notebook_id: ID del cuaderno para mostrar URL base.
    """
    faltantes = []
    faltantes_con_limite = []
    urls = urls or {}
    artefactos_con_url = []  # Para mostrar después de la tabla

    table = Table(title="Estado de Artefactos", box=box.ROUNDED)
    table.add_column("Artefacto", style="cyan")
    table.add_column("Estado", justify="center")
    table.add_column("Título", style="white")
    table.add_column("ID", style="dim")

    for tipo in ORDEN_ARTEFACTOS:
        nombre, tiene_limite = TIPOS_ARTEFACTOS[tipo]
        lista = existentes[tipo]

        if lista:
            # Mostrar cada artefacto en una fila separada
            for idx, art in enumerate(lista):
                art_titulo = getattr(art, 'title', None) or '-'
                art_id = getattr(art, 'id', '-')
                url_data = urls.get(art_id)

                # Guardar para mostrar URLs después (url_data es tupla (url, artifact_type))
                if url_data:
                    art_url, artifact_type = url_data
                    # Generar nombre de archivo sugerido usando el título del Artifact
                    extension = _extension_por_tipo(artifact_type)
                    nombre_limpio = _limpiar_nombre_archivo(art_titulo)
                    nombre_archivo = f"{nombre_limpio}{extension}" if nombre_limpio and nombre_limpio != '-' else None
                    artefactos_con_url.append((nombre, art_titulo, art_url, nombre_archivo, art_id, artifact_type))

                if idx == 0:
                    # Primera fila: mostrar nombre del tipo y estado
                    status = "[bold green]Disponible[/bold green]"
                    table.add_row(nombre, status, art_titulo, art_id)
                else:
                    # Filas adicionales del mismo tipo
                    table.add_row("", "", art_titulo, art_id)
        else:
            status = "[red]No disponible[/red]"
            hint = "⚠ Límite diario" if tiene_limite else "-"
            table.add_row(nombre, status, "-", hint)
            faltantes.append(tipo)
            if tiene_limite:
                faltantes_con_limite.append(tipo)

    console.print("\n", table)

    # Mostrar URL del cuaderno
    if notebook_id:
        console.print(f"\n[bold]URL del cuaderno:[/bold]")
        console.print(f"[yellow]https://notebooklm.google.com/notebook/{notebook_id}[/yellow]")

    # Mostrar URLs de descarga de artefactos
    if artefactos_con_url:
        console.print(f"\n[bold]URLs de descarga:[/bold]")
        comandos_download = []

        for nombre, titulo, url, nombre_archivo, art_id, artifact_type in artefactos_con_url:
            console.print(f"  • [bold cyan]{nombre}[/bold cyan]: [bold white reverse] {titulo} [/bold white reverse]")
            console.print(f"    [yellow]{url}[/yellow]")
            if nombre_archivo:
                console.print(f"    [dim]Guardar como: {nombre_archivo}[/dim]")
                # Generar comando notebooklm download
                subcomando = _subcomando_por_tipo(artifact_type)
                if subcomando:
                    comandos_download.append((nombre, titulo, nombre_archivo, art_id, subcomando))

        # Mostrar comandos notebooklm download
        if comandos_download and notebook_id:
            console.print(f"\n[bold]Comandos para descargar:[/bold]")
            for nombre, titulo, nombre_archivo, art_id, subcomando in comandos_download:
                console.print(f"\n# {nombre}: {titulo}")
                console.print(f'notebooklm download {subcomando} -n {notebook_id} \\')
                console.print(f'  -a {art_id} "{nombre_archivo}"')

    return faltantes, faltantes_con_limite
