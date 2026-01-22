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
    --audio                Generar resumen de audio (límite diario)
    --slides               Generar presentación (límite diario)
    --infographic          Generar infografía (límite diario)
    --todo                 Generar todos los artefactos

Por defecto solo genera el informe (sin límite diario).

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
import tempfile
import logging
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from pathlib import Path

import yt_dlp
from notebooklm import NotebookLMClient

# Versión del programa
VERSION = "0.6.0"

# Variable global para modo debug
DEBUG = False


def timestamp() -> str:
    """Devuelve la hora actual formateada HH:MM:SS."""
    return datetime.now().strftime("%H:%M:%S")


def debug(mensaje: str):
    """Imprime mensaje de debug si el modo está activo."""
    if DEBUG:
        print(f"[DEBUG] {mensaje}")


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


# Mapeo de tipos de artefactos (ordenados: sin límite primero, luego por tiempo)
# Formato: (nombre_display, tiene_limite_diario)
# report: sin límite, 5-15 min
# slides: con límite, tiempo medio
# infographic: con límite, tiempo medio (comparte cuota con slides)
# audio: con límite, 10-20 min (penúltimo)
TIPOS_ARTEFACTOS = {
    'report': ('Informe', False),
    'slides': ('Presentación (Slides)', True),
    'infographic': ('Infografía', True),
    'audio': ('Resumen de Audio', True),
}

# Lista ordenada de tipos (el orden importa para generación)
ORDEN_ARTEFACTOS = ['report', 'slides', 'infographic', 'audio']


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


async def verificar_artefactos_existentes(client, notebook_id: str, idioma: str = 'es') -> dict:
    """Verifica qué artefactos ya existen en el cuaderno en el idioma especificado."""
    debug(f"Verificando artefactos en notebook: {notebook_id} (idioma: {idioma})")
    existentes = {
        'report': None,
        'audio': None,
        'slides': None,
        'infographic': None,
    }

    try:
        # Listar cada tipo de artefacto
        debug("  Buscando reports...")
        try:
            reports = await client.artifacts.list_reports(notebook_id)
            debug(f"    Reports encontrados: {len(reports) if reports else 0}")
            if reports:
                # Buscar uno en el idioma correcto
                for report in reports:
                    if artefacto_tiene_idioma(report, idioma):
                        existentes['report'] = report
                        debug(f"    Report en idioma {idioma} encontrado")
                        break
        except Exception as e:
            debug(f"    Error listando reports: {e}")

        debug("  Buscando audios...")
        try:
            audios = await client.artifacts.list_audio(notebook_id)
            debug(f"    Audios encontrados: {len(audios) if audios else 0}")
            if audios:
                for audio in audios:
                    if artefacto_tiene_idioma(audio, idioma):
                        existentes['audio'] = audio
                        debug(f"    Audio en idioma {idioma} encontrado")
                        break
        except Exception as e:
            debug(f"    Error listando audios: {e}")

        debug("  Buscando slides...")
        try:
            slides = await client.artifacts.list_slide_decks(notebook_id)
            debug(f"    Slides encontrados: {len(slides) if slides else 0}")
            if slides:
                # Slides no tienen idioma, tomar el primero
                existentes['slides'] = slides[0]
        except Exception as e:
            debug(f"    Error listando slides: {e}")

        debug("  Buscando infographics...")
        try:
            infographics = await client.artifacts.list_infographics(notebook_id)
            debug(f"    Infographics encontrados: {len(infographics) if infographics else 0}")
            if infographics:
                # Infographics no tienen idioma, tomar el primero
                existentes['infographic'] = infographics[0]
        except Exception as e:
            debug(f"    Error listando infographics: {e}")

    except Exception as e:
        print(f"  Advertencia al verificar artefactos: {e}")
        debug(f"  Excepción general: {e}")

    debug(f"Resumen artefactos: report={existentes['report'] is not None}, audio={existentes['audio'] is not None}, slides={existentes['slides'] is not None}, infographic={existentes['infographic'] is not None}")
    return existentes


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

    async def generar_y_reportar(nombre: str, tipo: str, generar_func, **kwargs):
        """Lanza generación y reporta cuando completa.

        Returns:
            Tuple (éxito: bool, limite_alcanzado: bool)
        """
        hora_inicio = timestamp()
        debug(f"  Iniciando generación de {nombre} con kwargs: {kwargs}")
        print(f"  [{hora_inicio}] → Iniciando: {nombre}")
        try:
            status = await generar_func(notebook_id, **kwargs)
            debug(f"    Status recibido: {status}")

            # Verificar si la generación falló inmediatamente
            if status and getattr(status, 'status', None) == 'failed':
                hora_fin = timestamp()

                # Verificar si es un error de límite de cuota
                if hasattr(status, 'is_rate_limited') and status.is_rate_limited:
                    print(f"  [{hora_fin}] ⚠ {nombre}: Límite diario alcanzado")
                    print(f"           Espera al día siguiente o suscríbete a NotebookLM Plus")
                    debug(f"    {nombre} rechazado por límite de cuota")
                    return (False, True)  # (no éxito, límite alcanzado)

                error_msg = getattr(status, 'error', 'Error desconocido')
                print(f"  [{hora_fin}] ✗ Rechazado: {nombre} - {error_msg}")
                debug(f"    {nombre} rechazado por la API")
                return (False, False)

            # Esperar completado si tenemos un task_id válido
            if status and getattr(status, 'task_id', None):
                debug(f"    Esperando completado de task_id: {status.task_id}")
                await client.artifacts.wait_for_completion(notebook_id, status.task_id)
            hora_fin = timestamp()
            print(f"  [{hora_fin}] ✓ Completado: {nombre}")
            debug(f"    {nombre} completado exitosamente")
            return (True, False)
        except Exception as e:
            hora_fin = timestamp()
            print(f"  [{hora_fin}] ✗ Error en {nombre}: {e}")
            debug(f"    Excepción en {nombre}: {type(e).__name__}: {e}")
            return (False, False)

    # Artefactos que comparten cuota (si uno falla por límite, saltar los demás del grupo)
    CUOTA_COMPARTIDA = {
        'slides': 'premium',      # slides e infographic comparten cuota premium
        'infographic': 'premium',
    }

    # Definir configuración de cada tipo de artefacto (mismo orden que TIPOS_ARTEFACTOS)
    CONFIG_ARTEFACTOS = {
        'report': ('Informe', client.artifacts.generate_report, {'language': idioma}),
        'slides': ('Presentación (Slides)', client.artifacts.generate_slide_deck, {'language': idioma}),
        'infographic': ('Infografía', client.artifacts.generate_infographic, {'language': idioma}),
        'audio': ('Resumen de Audio', client.artifacts.generate_audio, {'language': idioma}),
    }

    print(f"\nGenerando artefactos (idioma: {idioma}, retardo entre inicios: {retardo_entre_tareas}s)...")

    exitosos = 0
    cuotas_agotadas = set()  # Grupos de cuota que han alcanzado el límite

    for i, tipo in enumerate(faltantes):
        # Verificar si este tipo comparte cuota con uno ya agotado
        grupo_cuota = CUOTA_COMPARTIDA.get(tipo)
        if grupo_cuota and grupo_cuota in cuotas_agotadas:
            nombre = CONFIG_ARTEFACTOS[tipo][0]
            print(f"  [--:--:--] ⏭ {nombre}: Omitido (cuota compartida agotada)")
            debug(f"    Saltando {tipo} porque cuota '{grupo_cuota}' está agotada")
            continue

        # Aplicar retardo entre artefactos (excepto el primero)
        if i > 0:
            debug(f"  Esperando {retardo_entre_tareas}s antes de siguiente artefacto")
            await asyncio.sleep(retardo_entre_tareas)

        nombre, generar_func, kwargs = CONFIG_ARTEFACTOS[tipo]
        exito, limite_alcanzado = await generar_y_reportar(nombre, tipo, generar_func, **kwargs)

        if exito:
            exitosos += 1
        elif limite_alcanzado and grupo_cuota:
            # Marcar el grupo de cuota como agotado
            cuotas_agotadas.add(grupo_cuota)
            debug(f"    Cuota '{grupo_cuota}' marcada como agotada")

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
    # Por defecto, solo artefactos sin límite (report)
    if artefactos_solicitados is None:
        artefactos_solicitados = {'report'}
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
        print(f"Error: URL no válida de YouTube: {url}")
        debug(f"  Fallo: no se pudo extraer video_id de {url}")
        return False

    print(f"Video ID: {video_id}")
    print(f"Idioma para contenido: {idioma}")
    debug(f"  video_id extraído: {video_id}")

    # 2. Obtener metadatos del vídeo
    debug("PASO 2: Obtener metadatos del vídeo con yt-dlp")
    print("Obteniendo metadatos del vídeo...")
    try:
        metadatos = obtener_metadatos_video(url)
        print(f"  Título: {metadatos['titulo']}")
        print(f"  Canal: {metadatos['canal']}")
        print(f"  Fecha: {metadatos['fecha']}")
        debug(f"  Metadatos obtenidos correctamente")

        # Mostrar descripción si se solicita
        if mostrar_descripcion and metadatos.get('descripcion'):
            print("\n" + "="*60)
            print("DESCRIPCIÓN DEL VÍDEO")
            print("="*60)
            print(metadatos['descripcion'])
            print("="*60 + "\n")
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
            print(f"✓ Cuaderno ya existe: {notebook.title}")
            print(f"  ID: {notebook.id}")
            print(f"  URL: https://notebooklm.google.com/notebook/{notebook.id}")

            # Verificar artefactos existentes (considerando idioma)
            debug("PASO 4.1: Verificar artefactos existentes")
            print(f"\nVerificando artefactos existentes (idioma: {idioma})...")
            existentes = await verificar_artefactos_existentes(client, notebook.id, idioma)

            # Mostrar estado de cada artefacto
            print("\nEstado de artefactos:")
            faltantes = []
            faltantes_con_limite = []
            for tipo in ORDEN_ARTEFACTOS:
                nombre, tiene_limite = TIPOS_ARTEFACTOS[tipo]
                artefacto = existentes[tipo]
                if artefacto:
                    # Mostrar info del artefacto si está disponible
                    titulo = getattr(artefacto, 'title', None) or getattr(artefacto, 'id', 'disponible')
                    print(f"  ✓ {nombre}: {titulo}")
                else:
                    limite_hint = " (⚠ límite diario)" if tiene_limite else ""
                    print(f"  ✗ {nombre}: no disponible{limite_hint}")
                    faltantes.append(tipo)
                    if tiene_limite:
                        faltantes_con_limite.append(tipo)

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
                print("\n✓ Todos los artefactos ya están disponibles")

            # Mostrar sugerencias para artefactos faltantes no solicitados
            faltantes_no_solicitados = [t for t in faltantes if t not in artefactos_solicitados]
            if faltantes_no_solicitados:
                print("\nPara generar artefactos faltantes, usa:")
                opciones = []
                for tipo in faltantes_no_solicitados:
                    opciones.append(f"--{tipo}")
                print(f"  python main.py \"{url}\" {' '.join(opciones)}")

            # Mostrar informe si se solicita
            if mostrar_informe_flag and existentes['report']:
                await mostrar_informe(client, notebook.id)

            print("\n" + "="*50)
            print(f"  Visita NotebookLM para ver los resultados:")
            print(f"  https://notebooklm.google.com/notebook/{notebook.id}")
            return True

        # 5. Crear nuevo cuaderno
        debug("PASO 5: Crear nuevo cuaderno")
        print(f"Creando cuaderno: {nombre_cuaderno}")
        notebook = await client.notebooks.create(nombre_cuaderno)
        notebook_url = f"https://notebooklm.google.com/notebook/{notebook.id}"
        print(f"✓ Cuaderno creado (ID: {notebook.id})")
        print(f"  URL: {notebook_url}")
        debug(f"  Cuaderno creado con ID: {notebook.id}")

        # 6. Añadir vídeo como fuente y esperar a que esté lista
        debug("PASO 6: Añadir vídeo como fuente")
        print(f"Añadiendo vídeo como fuente: {url}")
        print(f"Esperando a que se procese (máx. {timeout_fuente}s)...")
        try:
            await client.sources.add_url(notebook.id, url, wait=True, wait_timeout=timeout_fuente)
            print("✓ Fuente añadida y procesada")
            debug("  Fuente añadida y lista")
        except Exception as e:
            print(f"✓ Fuente añadida (aviso al esperar: {e})")
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
    global DEBUG

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
    artefactos_group.add_argument('--audio', action='store_true',
                        help='Generar resumen de audio (⚠ límite diario)')
    artefactos_group.add_argument('--slides', action='store_true',
                        help='Generar presentación (⚠ límite diario)')
    artefactos_group.add_argument('--infographic', action='store_true',
                        help='Generar infografía (⚠ límite diario)')
    artefactos_group.add_argument('--todo', action='store_true',
                        help='Generar todos los artefactos')

    parser.add_argument('--version', '-v', action='version',
                        version=f'%(prog)s {VERSION}')

    args = parser.parse_args()

    print(f"NotebookLM YouTube Importer v{VERSION}")

    # Activar modo debug si se solicita
    if args.debug:
        DEBUG = True
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
        if args.audio:
            artefactos_solicitados.add('audio')
        if args.slides:
            artefactos_solicitados.add('slides')
        if args.infographic:
            artefactos_solicitados.add('infographic')

        # Si no se especificó ninguno, usar solo report (sin límite)
        if not artefactos_solicitados:
            artefactos_solicitados = {'report'}
            print("Nota: Por defecto solo se genera el informe. Usa --todo para todos, o --audio/--slides/etc.")

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
