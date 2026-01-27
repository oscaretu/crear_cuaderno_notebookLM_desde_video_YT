#!/usr/bin/env python3
"""
Consulta y gestión de artefactos de un cuaderno existente en NotebookLM.

Acepta una URL de NotebookLM o un ID de cuaderno directamente.
Muestra los artefactos existentes y permite generar los que falten.

Uso:
    python ver_cuaderno.py <URL_O_ID> [opciones]

Opciones generales:
    --mostrar-informe      Muestra el contenido del informe por pantalla
    --idioma CODIGO        Idioma para filtrar/generar artefactos (default: es)
    --debug                Activa el modo debug con trazas detalladas

Opciones de artefactos (generar los que falten):
    --report               Generar informe (sin límite)
    --audio                Generar resumen de audio (límite diario)
    --slides               Generar presentación (límite diario)
    --infographic          Generar infografía (límite diario)
    --todo                 Generar todos los artefactos que falten

Ejemplo:
    python ver_cuaderno.py "https://notebooklm.google.com/notebook/NOTEBOOK_ID"
    python ver_cuaderno.py "NOTEBOOK_ID"
    python ver_cuaderno.py "NOTEBOOK_ID" --todo
    python ver_cuaderno.py "NOTEBOOK_ID" --audio --slides
    python ver_cuaderno.py "NOTEBOOK_ID" --mostrar-informe
    python ver_cuaderno.py "NOTEBOOK_ID" --debug

Requisitos previos:
    1. pip install -r requirements.txt
    2. playwright install chromium
    3. notebooklm login  (autenticarse con cuenta de Google)
"""

import asyncio
import sys
import argparse

from notebooklm import NotebookLMClient

from common import (
    debug, set_debug,
    TIPOS_ARTEFACTOS, ORDEN_ARTEFACTOS,
    verificar_artefactos_existentes,
    generar_artefactos,
    mostrar_informe,
    mostrar_estado_artefactos,
)

# Versión del programa
VERSION = "0.1.0"


def extraer_notebook_id(entrada: str) -> str:
    """Extrae el notebook_id de una URL de NotebookLM o lo devuelve tal cual si ya es un ID."""
    if 'notebooklm.google.com/notebook/' in entrada:
        return entrada.split('/notebook/')[-1].split('/')[0].split('?')[0]
    return entrada.strip()


async def obtener_cuaderno(client: NotebookLMClient, notebook_id: str):
    """Obtiene un cuaderno por su ID buscando en la lista de cuadernos."""
    debug(f"Buscando cuaderno con ID: {notebook_id}")
    notebooks = await client.notebooks.list()
    debug(f"Cuadernos encontrados: {len(notebooks)}")
    for nb in notebooks:
        if nb.id == notebook_id:
            debug(f"  ✓ Cuaderno encontrado: {nb.title}")
            return nb
    debug("  No se encontró el cuaderno")
    return None


async def procesar_cuaderno(notebook_id: str, mostrar_informe_flag: bool = False,
                             idioma: str = 'es', retardo: float = 3.0,
                             artefactos_solicitados: set = None):
    """Consulta un cuaderno existente y opcionalmente genera artefactos faltantes.

    Args:
        notebook_id: ID del cuaderno en NotebookLM
        mostrar_informe_flag: Si True, muestra el contenido del informe
        idioma: Código de idioma para filtrar/generar artefactos
        retardo: Segundos de retardo entre inicio de cada generación
        artefactos_solicitados: Conjunto de tipos de artefactos a generar (None = solo consultar)
    """
    debug("="*60)
    debug("INICIO procesar_cuaderno()")
    debug(f"  notebook_id: {notebook_id}")
    debug(f"  mostrar_informe: {mostrar_informe_flag}")
    debug(f"  idioma: {idioma}")
    debug(f"  retardo: {retardo}s")
    debug(f"  artefactos_solicitados: {artefactos_solicitados}")
    debug("="*60)

    # 1. Conectar con NotebookLM
    debug("PASO 1: Conectar con NotebookLM")
    print("Conectando con NotebookLM...")
    async with await NotebookLMClient.from_storage() as client:
        debug("  Conexión establecida con NotebookLM")

        # 2. Obtener el cuaderno
        debug("PASO 2: Obtener cuaderno por ID")
        notebook = await obtener_cuaderno(client, notebook_id)

        if not notebook:
            print(f"Error: No se encontró el cuaderno con ID: {notebook_id}")
            return False

        # 3. Mostrar información del cuaderno
        print(f"Cuaderno: {notebook.title}")
        print(f"  ID: {notebook.id}")
        print(f"  URL: https://notebooklm.google.com/notebook/{notebook.id}")
        created = getattr(notebook, 'created_at', None) or getattr(notebook, 'create_time', None)
        if created:
            print(f"  Creado: {created}")

        # 4. Verificar artefactos existentes
        debug("PASO 3: Verificar artefactos existentes")
        print(f"\nVerificando artefactos (idioma: {idioma})...")
        existentes = await verificar_artefactos_existentes(client, notebook.id, idioma)

        # 5. Mostrar estado de artefactos
        faltantes, faltantes_con_limite = mostrar_estado_artefactos(existentes)

        # 6. Generar artefactos si se solicitaron
        if artefactos_solicitados:
            a_generar = [t for t in faltantes if t in artefactos_solicitados]

            if a_generar:
                print(f"\nGenerando {len(a_generar)} artefacto(s)...")
                exitosos = await generar_artefactos(client, notebook.id, a_generar, idioma, retardo)
                print(f"\n  Artefactos generados: {exitosos}/{len(a_generar)}")
            elif faltantes:
                # Hay faltantes pero ninguno coincide con los solicitados
                ya_existentes = [t for t in artefactos_solicitados if t not in faltantes]
                if ya_existentes:
                    nombres = [TIPOS_ARTEFACTOS[t][0] for t in ya_existentes]
                    print(f"\n  Ya existen: {', '.join(nombres)}")
            else:
                print("\n✓ Todos los artefactos ya están disponibles")

        # 7. Mostrar sugerencias para artefactos faltantes
        faltantes_no_solicitados = [t for t in faltantes if not artefactos_solicitados or t not in artefactos_solicitados]
        if faltantes_no_solicitados:
            print("\nPara generar artefactos faltantes, usa:")
            opciones = [f"--{t}" for t in faltantes_no_solicitados]
            print(f"  python ver_cuaderno.py \"{notebook_id}\" {' '.join(opciones)}")

        # 8. Mostrar informe si se solicita
        if mostrar_informe_flag and len(existentes['report']) > 0:
            await mostrar_informe(client, notebook.id)

        print("\n" + "="*50)
        print(f"  https://notebooklm.google.com/notebook/{notebook.id}")
        return True


def main():
    parser = argparse.ArgumentParser(
        description='Consultar y gestionar artefactos de un cuaderno en NotebookLM',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Ejemplos:
  python ver_cuaderno.py "https://notebooklm.google.com/notebook/NOTEBOOK_ID"
  python ver_cuaderno.py "NOTEBOOK_ID"
  python ver_cuaderno.py "NOTEBOOK_ID" --todo
  python ver_cuaderno.py "NOTEBOOK_ID" --audio --slides
  python ver_cuaderno.py "NOTEBOOK_ID" --mostrar-informe
  python ver_cuaderno.py "NOTEBOOK_ID" --debug

Sin flags de artefactos, solo muestra el estado actual del cuaderno.
        '''
    )
    parser.add_argument('notebook', help='URL de NotebookLM o ID del cuaderno')
    parser.add_argument('--mostrar-informe', action='store_true',
                        help='Muestra el contenido del informe por pantalla')
    parser.add_argument('--idioma', default='es',
                        help='Código de idioma para filtrar/generar artefactos (default: es)')
    parser.add_argument('--retardo', type=float, default=3.0,
                        help='Segundos de retardo entre inicio de cada generación (default: 3)')
    parser.add_argument('--debug', action='store_true',
                        help='Activa el modo debug con trazas detalladas')

    # Opciones de artefactos
    artefactos_group = parser.add_argument_group('artefactos',
        'Generar artefactos faltantes. Sin estos flags, solo se consulta el estado.')
    artefactos_group.add_argument('--report', action='store_true',
                        help='Generar informe (sin límite)')
    artefactos_group.add_argument('--audio', action='store_true',
                        help='Generar resumen de audio (⚠ límite diario)')
    artefactos_group.add_argument('--slides', action='store_true',
                        help='Generar presentación (⚠ límite diario)')
    artefactos_group.add_argument('--infographic', action='store_true',
                        help='Generar infografía (⚠ límite diario)')
    artefactos_group.add_argument('--todo', action='store_true',
                        help='Generar todos los artefactos que falten')

    parser.add_argument('--version', '-v', action='version',
                        version=f'%(prog)s {VERSION}')

    args = parser.parse_args()

    print(f"NotebookLM Notebook Viewer v{VERSION}")

    # Activar modo debug
    if args.debug:
        set_debug(True)
        debug("Modo DEBUG activado")

    # Extraer notebook_id
    notebook_id = extraer_notebook_id(args.notebook)
    debug(f"Entrada: {args.notebook} → notebook_id: {notebook_id}")

    # Mostrar recordatorio de idioma por defecto
    if args.idioma == 'es':
        print("Nota: Usando idioma español por defecto. Usa --idioma para cambiar (ej: --idioma en)")

    # Determinar artefactos a generar
    artefactos_solicitados = None
    if args.todo:
        artefactos_solicitados = set(TIPOS_ARTEFACTOS.keys())
    else:
        solicitados = set()
        if args.report:
            solicitados.add('report')
        if args.audio:
            solicitados.add('audio')
        if args.slides:
            solicitados.add('slides')
        if args.infographic:
            solicitados.add('infographic')
        if solicitados:
            artefactos_solicitados = solicitados

    # Informar modo de operación
    if artefactos_solicitados:
        sin_limite = [t for t in artefactos_solicitados if not TIPOS_ARTEFACTOS[t][1]]
        con_limite = [t for t in artefactos_solicitados if TIPOS_ARTEFACTOS[t][1]]
        if sin_limite:
            print(f"Artefactos sin límite a generar: {', '.join(sin_limite)}")
        if con_limite:
            print(f"Artefactos con límite a generar: {', '.join(con_limite)} (pueden fallar si se alcanzó el límite diario)")
    else:
        print("Modo consulta: mostrando estado del cuaderno")

    try:
        asyncio.run(procesar_cuaderno(
            notebook_id,
            args.mostrar_informe,
            args.idioma,
            args.retardo,
            artefactos_solicitados
        ))
    except Exception as e:
        print(f"\nError: {e}")
        debug(f"Excepción en main: {type(e).__name__}: {e}")
        print("\n¿Has ejecutado 'notebooklm login' para autenticarte?")
        sys.exit(1)


if __name__ == "__main__":
    main()
