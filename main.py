#!/usr/bin/env python3
"""
Aplicación para crear cuadernos en NotebookLM desde vídeos de YouTube.

Uso:
    python main.py <URL_YOUTUBE> [opciones]

Opciones generales:
    --mostrar-informe      Muestra el contenido del informe por pantalla
    --mostrar-descripcion  Muestra la descripción del vídeo de YouTube
    --idioma CODIGO        Idioma para el audio (default: es)
    --debug                Activa el modo debug con trazas detalladas

Opciones de artefactos:
    --report               Generar informe (sin límite)
    --mind-map             Generar mapa mental (sin límite)
    --data-table           Generar tabla de datos (sin límite)
    --slides               Generar presentación (límite diario)
    --infographic          Generar infografía (límite diario)
    --quiz                 Generar cuestionario (límite diario)
    --flashcards           Generar tarjetas didácticas (límite diario)
    --audio                Generar resumen de audio (límite diario)
    --video                Generar video (límite diario)
    --todo                 Generar todos los artefactos

Por defecto genera: informe, mapa mental, tabla de datos, cuestionario y tarjetas.

Ejemplo:
    python main.py "https://www.youtube.com/watch?v=VIDEO_ID"
    python main.py "https://www.youtube.com/watch?v=VIDEO_ID" --todo
    python main.py "https://www.youtube.com/watch?v=VIDEO_ID" --audio --slides
    python main.py "https://www.youtube.com/watch?v=VIDEO_ID" --mostrar-informe
    python main.py "https://www.youtube.com/watch?v=VIDEO_ID" --debug

Requisitos previos:
    1. pip install -r requirements.txt
    2. playwright install chromium
    3. notebooklm login  (autenticarse con cuenta de Google)
"""

import asyncio
import sys
import re
import argparse
from urllib.parse import urlparse, parse_qs
from datetime import datetime

import yt_dlp
from notebooklm import NotebookLMClient

from common import (
    debug, set_debug, timestamp,
    TIPOS_ARTEFACTOS, ORDEN_ARTEFACTOS,
    verificar_artefactos_existentes,
    generar_artefactos,
    mostrar_informe,
    mostrar_estado_artefactos,
    console,
)

# Versión del programa
VERSION = "0.8.0"


def extraer_video_id(url: str) -> str | None:
    """Extrae el video_id de una URL de YouTube."""
    # Patrones soportados:
    # - https://www.youtube.com/watch?v=VIDEO_ID
    # - https://youtu.be/VIDEO_ID
    # - https://www.youtube.com/embed/VIDEO_ID

    parsed = urlparse(url)

    if parsed.hostname in ('www.youtube.com', 'youtube.com'):
        if parsed.path == '/watch':
            query = parse_qs(parsed.query)
            return query.get('v', [None])[0]
        elif parsed.path.startswith('/embed/'):
            return parsed.path.split('/')[2]
    elif parsed.hostname == 'youtu.be':
        return parsed.path[1:]

    return None


def obtener_metadatos_video(url: str) -> dict:
    """Extrae metadatos del vídeo de YouTube usando yt-dlp."""
    from common import DEBUG
    debug(f"Iniciando extracción de metadatos para: {url}")

    # Configurar yt-dlp según modo debug
    if DEBUG:
        ydl_opts = {
            'quiet': False,
            'no_warnings': False,
            'extract_flat': False,
            'verbose': True,
        }
    else:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            # Ignorar errores HTTP no críticos (como 403 en algunas peticiones)
            'ignoreerrors': False,
        }

    debug(f"Opciones de yt-dlp: {ydl_opts}")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        debug("Ejecutando yt-dlp.extract_info()...")
        info = ydl.extract_info(url, download=False)
        debug(f"Extracción completada. Claves disponibles: {list(info.keys()) if info else 'None'}")

        # Extraer fecha de subida (formato YYYYMMDD)
        upload_date = info.get('upload_date', '')
        debug(f"upload_date raw: {upload_date}")
        if upload_date:
            fecha = datetime.strptime(upload_date, '%Y%m%d').strftime('%Y-%m-%d')
        else:
            fecha = 'fecha-desconocida'

        metadatos = {
            'titulo': info.get('title', 'Sin título'),
            'canal': info.get('channel', info.get('uploader', 'Canal desconocido')),
            'fecha': fecha,
            'video_id': info.get('id', ''),
            'descripcion': info.get('description', ''),
        }
        debug(f"Metadatos extraídos: {metadatos}")
        return metadatos


def limpiar_texto(texto: str, max_length: int = 50) -> str:
    """Limpia texto para usar en nombre de cuaderno."""
    # Eliminar caracteres problemáticos
    texto = re.sub(r'[<>:"/\\|?*]', '', texto)
    # Truncar si es muy largo
    if len(texto) > max_length:
        texto = texto[:max_length].rsplit(' ', 1)[0] + '...'
    return texto.strip()


def generar_nombre_cuaderno(metadatos: dict) -> str:
    """Genera nombre del cuaderno con formato: YT-ID - Título - Fecha - Canal."""
    titulo = limpiar_texto(metadatos['titulo'], 60)
    canal = limpiar_texto(metadatos['canal'], 30)
    fecha = metadatos['fecha']
    video_id = metadatos['video_id']

    return f"YT-{video_id} - {titulo} - {fecha} - {canal}"


async def buscar_cuaderno_existente(client: NotebookLMClient, video_id: str):
    """Busca si ya existe un cuaderno para este video_id."""
    debug(f"Buscando cuaderno con prefijo YT-{video_id}")
    notebooks = await client.notebooks.list()
    debug(f"Cuadernos encontrados: {len(notebooks)}")
    prefijo = f"YT-{video_id}"
    for nb in notebooks:
        debug(f"  Comparando: '{nb.title}' con prefijo '{prefijo}'")
        if nb.title.startswith(prefijo):
            debug(f"  ✓ Coincidencia encontrada: {nb.id}")
            return nb
    debug("  No se encontró cuaderno existente")
    return None


async def procesar_video(url: str, mostrar_informe_flag: bool = False, idioma: str = 'es',
                         timeout_fuente: float = 60.0, retardo: float = 3.0,
                         mostrar_descripcion: bool = False,
                         artefactos_solicitados: set = None):
    """Procesa un vídeo de YouTube: crea cuaderno y genera artefactos.

    Args:
        url: URL del vídeo de YouTube
        mostrar_informe_flag: Si True, muestra el contenido del informe
        idioma: Código de idioma para los artefactos
        timeout_fuente: Segundos máx. para esperar procesamiento de fuente
        retardo: Segundos de retardo entre inicio de cada generación
        mostrar_descripcion: Si True, muestra la descripción del vídeo
        artefactos_solicitados: Conjunto de tipos de artefactos a generar
    """
    # Por defecto: informe, mapa mental, tabla de datos, cuestionario y tarjetas
    if artefactos_solicitados is None:
        artefactos_solicitados = {'report', 'mind_map', 'data_table', 'quiz', 'flashcards'}
    debug("="*60)
    debug("INICIO procesar_video()")
    debug(f"  URL: {url}")
    debug(f"  mostrar_informe: {mostrar_informe_flag}")
    debug(f"  idioma: {idioma}")
    debug(f"  timeout_fuente: {timeout_fuente}s")
    debug(f"  retardo: {retardo}s")
    debug("="*60)

    # 1. Validar URL y extraer video_id
    debug("PASO 1: Validar URL y extraer video_id")
    video_id = extraer_video_id(url)
    if not video_id:
        console.print(f"[bold red]Error: URL no válida de YouTube: {url}[/bold red]")
        debug(f"  Fallo: no se pudo extraer video_id de {url}")
        return False

    console.print(f"Video ID: [bold]{video_id}[/bold]")
    console.print(f"Idioma para contenido: [bold]{idioma}[/bold]")
    debug(f"  video_id extraído: {video_id}")

    # 2. Obtener metadatos del vídeo
    debug("PASO 2: Obtener metadatos del vídeo con yt-dlp")
    console.print("[cyan]Obteniendo metadatos del vídeo...[/cyan]")
    try:
        metadatos = obtener_metadatos_video(url)
        console.print(f"  Título: [bold]{metadatos['titulo']}[/bold]")
        console.print(f"  Canal: [dim]{metadatos['canal']}[/dim]")
        console.print(f"  Fecha: [dim]{metadatos['fecha']}[/dim]")
        debug(f"  Metadatos obtenidos correctamente")

        # Mostrar descripción si se solicita
        if mostrar_descripcion and metadatos.get('descripcion'):
            console.print("\n" + "="*60, style="dim")
            console.print("[bold]DESCRIPCIÓN DEL VÍDEO[/bold]")
            console.print("="*60, style="dim")
            console.print(metadatos['descripcion'])
            console.print("="*60 + "\n", style="dim")
    except Exception as e:
        print(f"Error obteniendo metadatos: {e}")
        debug(f"  Excepción en metadatos: {type(e).__name__}: {e}")
        return False

    nombre_cuaderno = generar_nombre_cuaderno(metadatos)
    debug(f"  Nombre de cuaderno generado: {nombre_cuaderno}")

    # 3. Conectar con NotebookLM
    debug("PASO 3: Conectar con NotebookLM")
    print("Conectando con NotebookLM...")
    async with await NotebookLMClient.from_storage() as client:
        debug("  Conexión establecida con NotebookLM")

        # 4. Verificar si ya existe el cuaderno
        debug("PASO 4: Verificar si ya existe el cuaderno")
        print(f"Buscando cuaderno existente para: {video_id}")
        notebook = await buscar_cuaderno_existente(client, video_id)

        if notebook:
            debug("  Cuaderno encontrado, procesando como existente")
            console.print(f"[bold green]✓ Cuaderno ya existe:[/bold green] {notebook.title}")
            console.print(f"  ID: {notebook.id}")
            console.print(f"  URL: https://notebooklm.google.com/notebook/{notebook.id}")

            # Verificar artefactos existentes (considerando idioma)
            debug("PASO 4.1: Verificar artefactos existentes")
            print(f"\nVerificando artefactos existentes (idioma: {idioma})...")
            existentes, urls = await verificar_artefactos_existentes(client, notebook.id, idioma)

            # Mostrar estado de cada artefacto
            faltantes, faltantes_con_limite = mostrar_estado_artefactos(existentes, urls, notebook.id)

            # Determinar qué artefactos generar según las opciones
            a_generar = []
            for tipo in faltantes:
                if tipo in artefactos_solicitados:
                    a_generar.append(tipo)

            # Generar los solicitados que faltan
            if a_generar:
                print(f"\nGenerando {len(a_generar)} artefacto(s)...")
                exitosos = await generar_artefactos(client, notebook.id, a_generar, idioma, retardo)
                print(f"\n  Artefactos generados: {exitosos}/{len(a_generar)}")
            elif faltantes:
                # Hay faltantes pero no se solicitaron
                print(f"\n  No se generaron artefactos (no solicitados)")
            else:
                console.print("\n[green]✓ Todos los artefactos ya están disponibles[/green]")

            # Mostrar sugerencias para artefactos faltantes no solicitados
            faltantes_no_solicitados = [t for t in faltantes if t not in artefactos_solicitados]
            if faltantes_no_solicitados:
                print("\nPara generar artefactos faltantes, usa:")
                opciones = []
                for tipo in faltantes_no_solicitados:
                    opciones.append(f"--{tipo}")
                print(f"  python main.py \"{url}\" {' '.join(opciones)}")

            # Mostrar informe si se solicita
            if mostrar_informe_flag and len(existentes['report']) > 0:
                await mostrar_informe(client, notebook.id)

            print("\n" + "="*50)
            print(f"  Visita NotebookLM para ver los resultados:")
            print(f"  https://notebooklm.google.com/notebook/{notebook.id}")
            return True

        # 5. Crear nuevo cuaderno
        # 5. Crear nuevo cuaderno
        debug("PASO 5: Crear nuevo cuaderno")
        console.print(f"Creando cuaderno: [bold]{nombre_cuaderno}[/bold]")
        notebook = await client.notebooks.create(nombre_cuaderno)
        notebook_url = f"https://notebooklm.google.com/notebook/{notebook.id}"
        console.print(f"[bold green]✓ Cuaderno creado[/bold green] (ID: {notebook.id})")
        console.print(f"  URL: {notebook_url}")
        debug(f"  Cuaderno creado con ID: {notebook.id}")

        # 6. Añadir vídeo como fuente y esperar a que esté lista
        debug("PASO 6: Añadir vídeo como fuente")
        console.print(f"Añadiendo vídeo como fuente: [underline]{url}[/underline]")
        
        try:
            with console.status(f"Procesando fuente (máx. {timeout_fuente}s)...", spinner="earth"):
                await client.sources.add_url(notebook.id, url, wait=True, wait_timeout=timeout_fuente)
            console.print("[bold green]✓ Fuente añadida y procesada[/bold green]")
            debug("  Fuente añadida y lista")
        except Exception as e:
            console.print(f"[yellow]✓ Fuente añadida (aviso al esperar: {e})[/yellow]")
            debug(f"  Fuente añadida pero error en espera: {e}")

        # 7. Generar artefactos solicitados
        debug("PASO 7: Generar artefactos solicitados")
        tipos_a_generar = [t for t in ORDEN_ARTEFACTOS if t in artefactos_solicitados]
        exitosos = await generar_artefactos(client, notebook.id, tipos_a_generar, idioma, retardo)
        print(f"\n  Artefactos generados: {exitosos}/{len(tipos_a_generar)}")
        debug(f"  Artefactos exitosos: {exitosos}/{len(tipos_a_generar)}")

        # Mostrar sugerencias para artefactos no solicitados
        no_solicitados = [t for t in ORDEN_ARTEFACTOS if t not in artefactos_solicitados]
        if no_solicitados:
            print("\nPara generar otros artefactos, usa:")
            opciones = [f"--{t}" for t in no_solicitados]
            print(f"  python main.py \"{url}\" {' '.join(opciones)}")

        # Mostrar informe si se solicita
        if mostrar_informe_flag:
            debug("PASO 8: Mostrar informe (solicitado)")
            # Esperar un poco para que el informe esté listo
            await asyncio.sleep(2)
            await mostrar_informe(client, notebook.id)

        debug("="*60)
        debug("FIN procesar_video() - Completado exitosamente")
        debug("="*60)
        print("\n" + "="*50)
        print("✓ Proceso completado")
        print(f"  Cuaderno: {nombre_cuaderno}")
        print(f"  URL: https://notebooklm.google.com/notebook/{notebook.id}")

        return True


def main():
    parser = argparse.ArgumentParser(
        description='Crear cuadernos en NotebookLM desde vídeos de YouTube',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Ejemplos:
  python main.py "https://www.youtube.com/watch?v=VIDEO_ID"
  python main.py "https://www.youtube.com/watch?v=VIDEO_ID" --todo
  python main.py "https://www.youtube.com/watch?v=VIDEO_ID" --audio --slides
  python main.py "https://www.youtube.com/watch?v=VIDEO_ID" --mostrar-informe
  python main.py "https://www.youtube.com/watch?v=VIDEO_ID" --idioma en
  python main.py "https://www.youtube.com/watch?v=VIDEO_ID" --debug

Por defecto solo genera el informe (sin límite). Use --todo para todos.
        '''
    )
    parser.add_argument('url', help='URL del vídeo de YouTube')
    parser.add_argument('--mostrar-informe', action='store_true',
                        help='Muestra el contenido del informe por pantalla')
    parser.add_argument('--mostrar-descripcion', action='store_true',
                        help='Muestra la descripción del vídeo de YouTube')
    parser.add_argument('--idioma', default='es',
                        help='Código de idioma para audio e informe (default: es)')
    parser.add_argument('--timeout-fuente', type=float, default=60.0,
                        help='Segundos máx. para esperar procesamiento de fuente (default: 60)')
    parser.add_argument('--retardo', type=float, default=3.0,
                        help='Segundos de retardo entre inicio de cada generación (default: 3)')
    parser.add_argument('--debug', action='store_true',
                        help='Activa el modo debug con trazas detalladas')

    # Opciones de artefactos
    artefactos_group = parser.add_argument_group('artefactos',
        'Por defecto solo genera el informe (sin límite diario)')
    artefactos_group.add_argument('--report', action='store_true',
                        help='Generar informe (sin límite)')
    artefactos_group.add_argument('--mind-map', action='store_true',
                        help='Generar mapa mental (sin límite)')
    artefactos_group.add_argument('--data-table', action='store_true',
                        help='Generar tabla de datos (sin límite)')
    artefactos_group.add_argument('--slides', action='store_true',
                        help='Generar presentación (⚠ límite diario)')
    artefactos_group.add_argument('--infographic', action='store_true',
                        help='Generar infografía (⚠ límite diario)')
    artefactos_group.add_argument('--quiz', action='store_true',
                        help='Generar cuestionario (⚠ límite diario)')
    artefactos_group.add_argument('--flashcards', action='store_true',
                        help='Generar tarjetas didácticas (⚠ límite diario)')
    artefactos_group.add_argument('--audio', action='store_true',
                        help='Generar resumen de audio (⚠ límite diario)')
    artefactos_group.add_argument('--video', action='store_true',
                        help='Generar video (⚠ límite diario)')
    artefactos_group.add_argument('--todo', action='store_true',
                        help='Generar todos los artefactos')

    parser.add_argument('--version', '-v', action='version',
                        version=f'%(prog)s {VERSION}')

    args = parser.parse_args()

    print(f"NotebookLM YouTube Importer v{VERSION}")

    # Activar modo debug si se solicita
    if args.debug:
        set_debug(True)
        debug("Modo DEBUG activado")
        debug(f"Argumentos: url={args.url}, mostrar_informe={args.mostrar_informe}, "
              f"idioma={args.idioma}, timeout_fuente={args.timeout_fuente}, retardo={args.retardo}, "
              f"mostrar_descripcion={args.mostrar_descripcion}, todo={args.todo}")

    # Mostrar recordatorio de idioma por defecto
    if args.idioma == 'es':
        print("Nota: Usando idioma español por defecto. Usa --idioma para cambiar (ej: --idioma en)")

    # Determinar qué artefactos generar
    artefactos_solicitados = set()
    if args.todo:
        artefactos_solicitados = set(TIPOS_ARTEFACTOS.keys())
    else:
        if args.report:
            artefactos_solicitados.add('report')
        if args.mind_map:
            artefactos_solicitados.add('mind_map')
        if args.data_table:
            artefactos_solicitados.add('data_table')
        if args.slides:
            artefactos_solicitados.add('slides')
        if args.infographic:
            artefactos_solicitados.add('infographic')
        if args.quiz:
            artefactos_solicitados.add('quiz')
        if args.flashcards:
            artefactos_solicitados.add('flashcards')
        if args.audio:
            artefactos_solicitados.add('audio')
        if args.video:
            artefactos_solicitados.add('video')

        # Si no se especificó ninguno, usar conjunto por defecto
        if not artefactos_solicitados:
            artefactos_solicitados = {'report', 'mind_map', 'data_table', 'quiz', 'flashcards'}
            print("Nota: Generando artefactos por defecto (informe, mapa mental, tabla, cuestionario, tarjetas). Usa --todo para todos.")

    # Mostrar qué se va a generar
    sin_limite = [t for t in artefactos_solicitados if not TIPOS_ARTEFACTOS[t][1]]
    con_limite = [t for t in artefactos_solicitados if TIPOS_ARTEFACTOS[t][1]]
    if sin_limite:
        print(f"Artefactos sin límite: {', '.join(sin_limite)}")
    if con_limite:
        print(f"Artefactos con límite: {', '.join(con_limite)} (pueden fallar si se alcanzó el límite diario)")

    try:
        asyncio.run(procesar_video(
            args.url,
            args.mostrar_informe,
            args.idioma,
            args.timeout_fuente,
            args.retardo,
            args.mostrar_descripcion,
            artefactos_solicitados
        ))
    except Exception as e:
        print(f"\nError: {e}")
        debug(f"Excepción en main: {type(e).__name__}: {e}")
        print("\n¿Has ejecutado 'notebooklm login' para autenticarte?")
        sys.exit(1)


if __name__ == "__main__":
    main()
