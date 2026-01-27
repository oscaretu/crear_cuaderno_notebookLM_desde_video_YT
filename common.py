"""
Módulo común con funciones y constantes compartidas entre los scripts de NotebookLM.

Usado por: main.py, ver_cuaderno.py
"""

import asyncio
import tempfile
from datetime import datetime
from pathlib import Path


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
        print(f"[DEBUG] {mensaje}")


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
        'report': [],
        'audio': [],
        'slides': [],
        'infographic': [],
    }

    try:
        # Listar cada tipo de artefacto
        debug("  Buscando reports...")
        try:
            reports = await client.artifacts.list_reports(notebook_id)
            debug(f"    Reports encontrados: {len(reports) if reports else 0}")
            if reports:
                # Buscar todos los que coincidan con el idioma
                for report in reports:
                    if artefacto_tiene_idioma(report, idioma):
                        existentes['report'].append(report)
                        debug(f"    Report en idioma {idioma} encontrado")
                debug(f"    Reports en idioma {idioma}: {len(existentes['report'])}")
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
                        debug(f"    Audio en idioma {idioma} encontrado")
                debug(f"    Audios en idioma {idioma}: {len(existentes['audio'])}")
        except Exception as e:
            debug(f"    Error listando audios: {e}")

        debug("  Buscando slides...")
        try:
            slides = await client.artifacts.list_slide_decks(notebook_id)
            debug(f"    Slides encontrados: {len(slides) if slides else 0}")
            if slides:
                # Slides no tienen idioma, guardar todos
                existentes['slides'] = list(slides)
        except Exception as e:
            debug(f"    Error listando slides: {e}")

        debug("  Buscando infographics...")
        try:
            infographics = await client.artifacts.list_infographics(notebook_id)
            debug(f"    Infographics encontrados: {len(infographics) if infographics else 0}")
            if infographics:
                # Infographics no tienen idioma, guardar todos
                existentes['infographic'] = list(infographics)
        except Exception as e:
            debug(f"    Error listando infographics: {e}")

    except Exception as e:
        print(f"  Advertencia al verificar artefactos: {e}")
        debug(f"  Excepción general: {e}")

    debug(f"Resumen artefactos: report={len(existentes['report'])}, audio={len(existentes['audio'])}, slides={len(existentes['slides'])}, infographic={len(existentes['infographic'])}")
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


def mostrar_estado_artefactos(existentes: dict) -> tuple[list[str], list[str]]:
    """Muestra el estado de los artefactos existentes y devuelve los faltantes.

    Args:
        existentes: Diccionario con listas de artefactos por tipo.

    Returns:
        Tupla (faltantes, faltantes_con_limite) con los tipos que no existen.
    """
    print("\nEstado de artefactos:")
    faltantes = []
    faltantes_con_limite = []
    for tipo in ORDEN_ARTEFACTOS:
        nombre, tiene_limite = TIPOS_ARTEFACTOS[tipo]
        lista = existentes[tipo]
        if lista:
            total = len(lista)
            for idx, artefacto in enumerate(lista, 1):
                titulo = getattr(artefacto, 'title', None) or getattr(artefacto, 'id', 'disponible')
                if total > 1:
                    print(f"  ✓ {nombre} ({idx} de {total}): {titulo}")
                else:
                    print(f"  ✓ {nombre}: {titulo}")
        else:
            limite_hint = " (⚠ límite diario)" if tiene_limite else ""
            print(f"  ✗ {nombre}: no disponible{limite_hint}")
            faltantes.append(tipo)
            if tiene_limite:
                faltantes_con_limite.append(tipo)
    return faltantes, faltantes_con_limite
