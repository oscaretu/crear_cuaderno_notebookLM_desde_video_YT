#!/usr/bin/env python3
"""
Aplicación para crear cuadernos en NotebookLM desde vídeos de YouTube.

Uso:
    python main.py <URL_YOUTUBE> [opciones]

Opciones:
    --mostrar-informe    Muestra el contenido del informe por pantalla
    --idioma CODIGO      Idioma para el audio (default: es)

Ejemplo:
    python main.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    python main.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --mostrar-informe

Requisitos previos:
    1. pip install -r requirements.txt
    2. playwright install chromium
    3. notebooklm login  (autenticarse con cuenta de Google)
"""

import asyncio
import sys
import re
import argparse
import tempfile
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from pathlib import Path

import yt_dlp
from notebooklm import NotebookLMClient


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
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

        # Extraer fecha de subida (formato YYYYMMDD)
        upload_date = info.get('upload_date', '')
        if upload_date:
            fecha = datetime.strptime(upload_date, '%Y%m%d').strftime('%Y-%m-%d')
        else:
            fecha = 'fecha-desconocida'

        return {
            'titulo': info.get('title', 'Sin título'),
            'canal': info.get('channel', info.get('uploader', 'Canal desconocido')),
            'fecha': fecha,
            'video_id': info.get('id', ''),
        }


def limpiar_texto(texto: str, max_length: int = 50) -> str:
    """Limpia texto para usar en nombre de cuaderno."""
    # Eliminar caracteres problemáticos
    texto = re.sub(r'[<>:"/\\|?*]', '', texto)
    # Truncar si es muy largo
    if len(texto) > max_length:
        texto = texto[:max_length].rsplit(' ', 1)[0] + '...'
    return texto.strip()


def generar_nombre_cuaderno(metadatos: dict) -> str:
    """Genera nombre del cuaderno con formato: YouTube_ID - Título - Fecha - Canal."""
    titulo = limpiar_texto(metadatos['titulo'], 60)
    canal = limpiar_texto(metadatos['canal'], 30)
    fecha = metadatos['fecha']
    video_id = metadatos['video_id']

    return f"YouTube_{video_id} - {titulo} - {fecha} - {canal}"


async def buscar_cuaderno_existente(client: NotebookLMClient, video_id: str):
    """Busca si ya existe un cuaderno para este video_id."""
    notebooks = await client.notebooks.list()
    prefijo = f"YouTube_{video_id}"
    for nb in notebooks:
        if nb.title.startswith(prefijo):
            return nb
    return None


# Mapeo de tipos de artefactos
TIPOS_ARTEFACTOS = {
    'report': 'Informe',
    'audio': 'Resumen de Audio',
    'slides': 'Presentación (Slides)',
    'infographic': 'Infografía',
}


async def verificar_artefactos_existentes(client, notebook_id: str) -> dict:
    """Verifica qué artefactos ya existen en el cuaderno. Devuelve info de cada uno."""
    existentes = {
        'report': None,
        'audio': None,
        'slides': None,
        'infographic': None,
    }

    try:
        # Listar cada tipo de artefacto
        try:
            reports = await client.artifacts.list_reports(notebook_id)
            if reports:
                existentes['report'] = reports[0]  # Tomar el primero
        except:
            pass

        try:
            audios = await client.artifacts.list_audio(notebook_id)
            if audios:
                existentes['audio'] = audios[0]
        except:
            pass

        try:
            slides = await client.artifacts.list_slide_decks(notebook_id)
            if slides:
                existentes['slides'] = slides[0]
        except:
            pass

        try:
            infographics = await client.artifacts.list_infographics(notebook_id)
            if infographics:
                existentes['infographic'] = infographics[0]
        except:
            pass

    except Exception as e:
        print(f"  Advertencia al verificar artefactos: {e}")

    return existentes


async def generar_artefactos(client, notebook_id: str, faltantes: list[str], idioma: str = 'es') -> int:
    """Genera los artefactos especificados en paralelo. Devuelve cantidad de éxitos."""

    if not faltantes:
        return 0

    async def generar_y_reportar(nombre: str, generar_func, **kwargs):
        """Lanza generación y reporta cuando completa."""
        print(f"  → Iniciando: {nombre}")
        try:
            status = await generar_func(notebook_id, **kwargs)
            if status and hasattr(status, 'task_id'):
                await client.artifacts.wait_for_completion(notebook_id, status.task_id)
            print(f"  ✓ Completado: {nombre}")
            return True
        except Exception as e:
            print(f"  ✗ Error en {nombre}: {e}")
            return False

    # Crear tareas con parámetros específicos para cada tipo
    tareas = []
    for tipo in faltantes:
        if tipo == 'report':
            tareas.append(generar_y_reportar(
                'Informe',
                client.artifacts.generate_report,
                language=idioma
            ))
        elif tipo == 'audio':
            tareas.append(generar_y_reportar(
                'Resumen de Audio',
                client.artifacts.generate_audio,
                language=idioma
            ))
        elif tipo == 'slides':
            tareas.append(generar_y_reportar(
                'Presentación (Slides)',
                client.artifacts.generate_slide_deck
            ))
        elif tipo == 'infographic':
            tareas.append(generar_y_reportar(
                'Infografía',
                client.artifacts.generate_infographic
            ))

    if not tareas:
        return 0

    print(f"\nLanzando generación de artefactos en paralelo (idioma: {idioma})...")
    resultados = await asyncio.gather(*tareas, return_exceptions=True)

    exitosos = sum(1 for r in resultados if r is True)
    return exitosos


async def mostrar_informe(client, notebook_id: str):
    """Descarga y muestra el contenido del informe."""
    try:
        # Crear archivo temporal para el informe
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            temp_path = f.name

        # Descargar el informe
        await client.artifacts.download_report(notebook_id, temp_path)

        # Leer y mostrar el contenido
        contenido = Path(temp_path).read_text(encoding='utf-8')

        print("\n" + "="*60)
        print("CONTENIDO DEL INFORME")
        print("="*60)
        print(contenido)
        print("="*60)

        # Limpiar archivo temporal
        Path(temp_path).unlink(missing_ok=True)

    except Exception as e:
        print(f"\n  ✗ Error al obtener el informe: {e}")


async def procesar_video(url: str, mostrar_informe_flag: bool = False, idioma: str = 'es'):
    """Procesa un vídeo de YouTube: crea cuaderno y genera artefactos."""

    # 1. Validar URL y extraer video_id
    video_id = extraer_video_id(url)
    if not video_id:
        print(f"Error: URL no válida de YouTube: {url}")
        return False

    print(f"Video ID: {video_id}")
    print(f"Idioma para contenido: {idioma}")

    # 2. Obtener metadatos del vídeo
    print("Obteniendo metadatos del vídeo...")
    try:
        metadatos = obtener_metadatos_video(url)
        print(f"  Título: {metadatos['titulo']}")
        print(f"  Canal: {metadatos['canal']}")
        print(f"  Fecha: {metadatos['fecha']}")
    except Exception as e:
        print(f"Error obteniendo metadatos: {e}")
        return False

    nombre_cuaderno = generar_nombre_cuaderno(metadatos)

    # 3. Conectar con NotebookLM
    print("Conectando con NotebookLM...")
    async with await NotebookLMClient.from_storage() as client:

        # 4. Verificar si ya existe el cuaderno
        print(f"Buscando cuaderno existente para: {video_id}")
        notebook = await buscar_cuaderno_existente(client, video_id)

        if notebook:
            print(f"✓ Cuaderno ya existe: {notebook.title}")
            print(f"  ID: {notebook.id}")
            print(f"  URL: https://notebooklm.google.com/notebook/{notebook.id}")

            # Verificar artefactos existentes
            print("\nVerificando artefactos existentes...")
            existentes = await verificar_artefactos_existentes(client, notebook.id)

            # Mostrar estado de cada artefacto
            print("\nEstado de artefactos:")
            faltantes = []
            for tipo, nombre in TIPOS_ARTEFACTOS.items():
                artefacto = existentes[tipo]
                if artefacto:
                    # Mostrar info del artefacto si está disponible
                    titulo = getattr(artefacto, 'title', None) or getattr(artefacto, 'id', 'disponible')
                    print(f"  ✓ {nombre}: {titulo}")
                else:
                    print(f"  ✗ {nombre}: no disponible")
                    faltantes.append(tipo)

            # Generar los faltantes
            if faltantes:
                print(f"\nGenerando {len(faltantes)} artefacto(s) faltante(s)...")
                exitosos = await generar_artefactos(client, notebook.id, faltantes, idioma)
                print(f"\n  Artefactos generados: {exitosos}/{len(faltantes)}")
            else:
                print("\n✓ Todos los artefactos ya están disponibles")

            # Mostrar informe si se solicita
            if mostrar_informe_flag and existentes['report']:
                await mostrar_informe(client, notebook.id)

            print("\n" + "="*50)
            print(f"  Visita NotebookLM para ver los resultados:")
            print(f"  https://notebooklm.google.com/notebook/{notebook.id}")
            return True

        # 5. Crear nuevo cuaderno
        print(f"Creando cuaderno: {nombre_cuaderno}")
        notebook = await client.notebooks.create(nombre_cuaderno)
        print(f"✓ Cuaderno creado (ID: {notebook.id})")

        # 6. Añadir vídeo como fuente
        print(f"Añadiendo vídeo como fuente: {url}")
        await client.sources.add_url(notebook.id, url)
        print("✓ Fuente añadida")

        # Esperar un poco para que NotebookLM procese la fuente
        print("Esperando a que se procese la fuente...")
        await asyncio.sleep(5)

        # 7. Generar todos los artefactos en paralelo
        todos_los_tipos = list(TIPOS_ARTEFACTOS.keys())
        exitosos = await generar_artefactos(client, notebook.id, todos_los_tipos, idioma)
        print(f"\n  Artefactos generados: {exitosos}/{len(todos_los_tipos)}")

        # Mostrar informe si se solicita
        if mostrar_informe_flag:
            # Esperar un poco para que el informe esté listo
            await asyncio.sleep(2)
            await mostrar_informe(client, notebook.id)

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
  python main.py "https://www.youtube.com/watch?v=VIDEO_ID" --mostrar-informe
  python main.py "https://www.youtube.com/watch?v=VIDEO_ID" --idioma en
        '''
    )
    parser.add_argument('url', help='URL del vídeo de YouTube')
    parser.add_argument('--mostrar-informe', action='store_true',
                        help='Muestra el contenido del informe por pantalla')
    parser.add_argument('--idioma', default='es',
                        help='Código de idioma para audio e informe (default: es)')

    args = parser.parse_args()

    try:
        asyncio.run(procesar_video(args.url, args.mostrar_informe, args.idioma))
    except Exception as e:
        print(f"\nError: {e}")
        print("\n¿Has ejecutado 'notebooklm login' para autenticarte?")
        sys.exit(1)


if __name__ == "__main__":
    main()
