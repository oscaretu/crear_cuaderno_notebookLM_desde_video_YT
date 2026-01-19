#!/usr/bin/env python3
"""
Lista todos los cuadernos disponibles en NotebookLM.

Uso:
    python listar_cuadernos.py [opciones]

Opciones de ordenación:
    --ordenar {nombre,creacion,modificacion}  Campo de ordenación (default: nombre)
    --desc                                     Orden descendente (default: ascendente)

Ejemplos:
    python listar_cuadernos.py
    python listar_cuadernos.py --ordenar creacion --desc
    python listar_cuadernos.py --ordenar modificacion

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


async def listar_cuadernos(ordenar_por: str = 'nombre', descendente: bool = False):
    """Lista todos los cuadernos con la ordenación especificada."""

    print("Conectando con NotebookLM...")
    async with await NotebookLMClient.from_storage() as client:
        print("Obteniendo lista de cuadernos...\n")
        notebooks = await client.notebooks.list()

        if not notebooks:
            print("No se encontraron cuadernos.")
            return

        # Ordenar según el criterio
        if ordenar_por == 'nombre':
            notebooks_ordenados = sorted(
                notebooks,
                key=lambda nb: (getattr(nb, 'title', '') or '').lower(),
                reverse=descendente
            )
        elif ordenar_por == 'creacion':
            notebooks_ordenados = sorted(
                notebooks,
                key=lambda nb: obtener_fecha_para_ordenar(nb, 'creacion'),
                reverse=descendente
            )
        elif ordenar_por == 'modificacion':
            notebooks_ordenados = sorted(
                notebooks,
                key=lambda nb: obtener_fecha_para_ordenar(nb, 'modificacion'),
                reverse=descendente
            )
        else:
            notebooks_ordenados = notebooks

        # Mostrar encabezado
        orden_texto = "descendente" if descendente else "ascendente"
        print(f"{'='*80}")
        print(f"CUADERNOS DISPONIBLES ({len(notebooks)} total)")
        print(f"Ordenados por: {ordenar_por} ({orden_texto})")
        print(f"{'='*80}\n")

        # Mostrar cada cuaderno
        for i, nb in enumerate(notebooks_ordenados, 1):
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
            print()

        print(f"{'='*80}")
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
  python listar_cuadernos.py --ordenar modificacion    # Menos recientes primero
  python listar_cuadernos.py --ordenar modificacion --desc  # Más recientes primero
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

    args = parser.parse_args()

    try:
        asyncio.run(listar_cuadernos(args.ordenar, args.desc))
    except Exception as e:
        print(f"\nError: {e}")
        print("\n¿Has ejecutado 'notebooklm login' para autenticarte?")


if __name__ == "__main__":
    main()
