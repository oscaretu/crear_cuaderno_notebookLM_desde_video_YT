#!/usr/bin/env python3
"""
Lista todos los cuadernos disponibles en NotebookLM.

Uso:
    python listar_cuadernos.py [opciones]

Opciones:
    --ordenar {nombre,creacion,modificacion}  Campo de ordenación (default: nombre)
    --desc                                     Orden descendente (default: ascendente)
    --idioma CODIGO                            Filtrar por idioma de artefactos (ej: es, en)

Ejemplos:
    python listar_cuadernos.py
    python listar_cuadernos.py --ordenar creacion --desc
    python listar_cuadernos.py --idioma es
    python listar_cuadernos.py --idioma en --ordenar modificacion --desc

Requisitos previos:
    notebooklm login  (autenticarse con cuenta de Google)
"""

import asyncio
import argparse
from datetime import datetime

from notebooklm import NotebookLMClient


def formatear_fecha(fecha) -> str:
    """Formatea una fecha para mostrar."""
    if not fecha:
        return "N/A"
    if isinstance(fecha, str):
        return fecha
    if isinstance(fecha, datetime):
        return fecha.strftime("%Y-%m-%d %H:%M")
    return str(fecha)


def obtener_fecha_para_ordenar(notebook, campo: str):
    """Obtiene el valor de fecha para ordenar."""
    if campo == 'creacion':
        valor = getattr(notebook, 'created_at', None) or getattr(notebook, 'create_time', None)
    elif campo == 'modificacion':
        valor = getattr(notebook, 'updated_at', None) or getattr(notebook, 'update_time', None)
    else:
        return None

    # Si es string, intentar parsear
    if isinstance(valor, str):
        try:
            return datetime.fromisoformat(valor.replace('Z', '+00:00'))
        except:
            return valor
    return valor or datetime.min


async def obtener_idiomas_cuaderno(client, notebook_id: str) -> dict:
    """Obtiene los idiomas de los artefactos de un cuaderno."""
    idiomas = {
        'report': [],
        'audio': [],
    }

    try:
        # Verificar reports
        try:
            reports = await client.artifacts.list_reports(notebook_id)
            if reports:
                for report in reports:
                    lang = getattr(report, 'language', None)
                    if lang and lang not in idiomas['report']:
                        idiomas['report'].append(lang)
        except:
            pass

        # Verificar audios
        try:
            audios = await client.artifacts.list_audio(notebook_id)
            if audios:
                for audio in audios:
                    lang = getattr(audio, 'language', None)
                    if lang and lang not in idiomas['audio']:
                        idiomas['audio'].append(lang)
        except:
            pass

    except:
        pass

    return idiomas


def tiene_idioma(idiomas_cuaderno: dict, idioma_filtro: str) -> bool:
    """Verifica si el cuaderno tiene artefactos en el idioma especificado."""
    idioma_lower = idioma_filtro.lower()

    # Verificar en reports
    for lang in idiomas_cuaderno.get('report', []):
        if lang and lang.lower().startswith(idioma_lower):
            return True

    # Verificar en audios
    for lang in idiomas_cuaderno.get('audio', []):
        if lang and lang.lower().startswith(idioma_lower):
            return True

    return False


def formatear_idiomas(idiomas_cuaderno: dict) -> str:
    """Formatea los idiomas para mostrar."""
    todos = set()
    for tipo, langs in idiomas_cuaderno.items():
        todos.update(langs)

    if not todos:
        return "N/A"
    return ", ".join(sorted(todos))


async def listar_cuadernos(ordenar_por: str = 'nombre', descendente: bool = False, filtro_idioma: str = None):
    """Lista todos los cuadernos con la ordenación especificada."""

    print("Conectando con NotebookLM...")
    async with await NotebookLMClient.from_storage() as client:
        print("Obteniendo lista de cuadernos...")
        notebooks = await client.notebooks.list()

        if not notebooks:
            print("No se encontraron cuadernos.")
            return

        # Si hay filtro de idioma, obtener idiomas de cada cuaderno
        notebooks_con_info = []
        if filtro_idioma:
            print(f"Filtrando por idioma: {filtro_idioma}")
            print("Verificando idiomas de artefactos (esto puede tardar)...")

            for nb in notebooks:
                nb_id = getattr(nb, 'id', None)
                if nb_id:
                    idiomas = await obtener_idiomas_cuaderno(client, nb_id)
                    if tiene_idioma(idiomas, filtro_idioma):
                        notebooks_con_info.append((nb, idiomas))
        else:
            # Sin filtro, incluir todos (sin verificar idiomas para mayor velocidad)
            notebooks_con_info = [(nb, None) for nb in notebooks]

        if not notebooks_con_info:
            print(f"\nNo se encontraron cuadernos con artefactos en idioma '{filtro_idioma}'.")
            return

        # Ordenar según el criterio
        if ordenar_por == 'nombre':
            notebooks_ordenados = sorted(
                notebooks_con_info,
                key=lambda x: (getattr(x[0], 'title', '') or '').lower(),
                reverse=descendente
            )
        elif ordenar_por == 'creacion':
            notebooks_ordenados = sorted(
                notebooks_con_info,
                key=lambda x: obtener_fecha_para_ordenar(x[0], 'creacion'),
                reverse=descendente
            )
        elif ordenar_por == 'modificacion':
            notebooks_ordenados = sorted(
                notebooks_con_info,
                key=lambda x: obtener_fecha_para_ordenar(x[0], 'modificacion'),
                reverse=descendente
            )
        else:
            notebooks_ordenados = notebooks_con_info

        # Mostrar encabezado
        orden_texto = "descendente" if descendente else "ascendente"
        print(f"\n{'='*80}")
        if filtro_idioma:
            print(f"CUADERNOS CON IDIOMA '{filtro_idioma.upper()}' ({len(notebooks_ordenados)} de {len(notebooks)} total)")
        else:
            print(f"CUADERNOS DISPONIBLES ({len(notebooks)} total)")
        print(f"Ordenados por: {ordenar_por} ({orden_texto})")
        print(f"{'='*80}\n")

        # Mostrar cada cuaderno
        for i, (nb, idiomas) in enumerate(notebooks_ordenados, 1):
            titulo = getattr(nb, 'title', 'Sin título') or 'Sin título'
            nb_id = getattr(nb, 'id', 'N/A')

            # Intentar obtener fechas
            creado = getattr(nb, 'created_at', None) or getattr(nb, 'create_time', None)
            modificado = getattr(nb, 'updated_at', None) or getattr(nb, 'update_time', None)

            print(f"{i:3}. {titulo}")
            print(f"     ID: {nb_id}")
            print(f"     URL: https://notebooklm.google.com/notebook/{nb_id}")
            if creado:
                print(f"     Creado: {formatear_fecha(creado)}")
            if modificado:
                print(f"     Modificado: {formatear_fecha(modificado)}")
            if idiomas:
                print(f"     Idiomas: {formatear_idiomas(idiomas)}")
            print()

        print(f"{'='*80}")
        if filtro_idioma:
            print(f"Total: {len(notebooks_ordenados)} cuaderno(s) con idioma '{filtro_idioma}'")
        else:
            print(f"Total: {len(notebooks)} cuaderno(s)")


def main():
    parser = argparse.ArgumentParser(
        description='Lista todos los cuadernos en NotebookLM',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Ejemplos:
  python listar_cuadernos.py                           # Por nombre A-Z
  python listar_cuadernos.py --ordenar nombre --desc   # Por nombre Z-A
  python listar_cuadernos.py --ordenar creacion        # Más antiguos primero
  python listar_cuadernos.py --ordenar creacion --desc # Más recientes primero
  python listar_cuadernos.py --idioma es               # Solo con artefactos en español
  python listar_cuadernos.py --idioma en --desc        # Solo en inglés, orden desc
        '''
    )
    parser.add_argument(
        '--ordenar',
        choices=['nombre', 'creacion', 'modificacion'],
        default='nombre',
        help='Campo por el que ordenar (default: nombre)'
    )
    parser.add_argument(
        '--desc',
        action='store_true',
        help='Orden descendente (default: ascendente)'
    )
    parser.add_argument(
        '--idioma',
        help='Filtrar por idioma de artefactos (ej: es, en)'
    )

    args = parser.parse_args()

    try:
        asyncio.run(listar_cuadernos(args.ordenar, args.desc, args.idioma))
    except Exception as e:
        print(f"\nError: {e}")
        print("\n¿Has ejecutado 'notebooklm login' para autenticarte?")


if __name__ == "__main__":
    main()
