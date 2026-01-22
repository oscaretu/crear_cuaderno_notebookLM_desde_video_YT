#!/bin/bash
#
# Script para configurar NOTEBOOKLM_HOME en WSL2
# Ejecutar con: source zzz_asigna_ubicacion_fichero_configuracion.inc.sh
#

echo
echo "Este fichero para ejecutar con source está pensado para ejecutar los scripts"
echo "main.py y listar_cuadernos.py desde WSL."
echo
echo "Aquí forzamos la ubicación del fichero JSON de configuración para que pueda"
echo "encontrarlo el módulo notebooklm de Python al ejecutar los scripts desde WSL."
echo
echo "Antes necesitarás generar el fichero JSON:"
echo "  1. Abre PowerShell y vete al directorio del proyecto"
echo "  2. Ejecuta: notebooklm login"
echo

# Determinar nombre de usuario (fallback si $USER está vacío)
CURRENT_USER="${USER:-${LOGNAME:-$(whoami)}}"

# Configurar NOTEBOOKLM_HOME
export NOTEBOOKLM_HOME="/mnt/c/Users/${CURRENT_USER}/.notebooklm"
echo "Exportando la variable NOTEBOOKLM_HOME..."
echo "  NOTEBOOKLM_HOME=$NOTEBOOKLM_HOME"
echo

# Verificar si el archivo existe
if [ -f "$NOTEBOOKLM_HOME/storage_state.json" ]; then
    echo "✓ Archivo de credenciales encontrado"
else
    echo "⚠ Archivo de credenciales NO encontrado en:"
    echo "  $NOTEBOOKLM_HOME/storage_state.json"
    echo
    echo "Ejecuta 'notebooklm login' desde PowerShell para generarlo."
fi
echo

echo "Recuerda que si no apuntas directamente al fichero generado desde PowerShell,"
echo "tienes que copiar ese fichero a ~/.notebooklm/storage_state.json"
echo
echo "  ┌──────────────────────┬─────────────────────────────────────────────────────┐"
echo "  │       Entorno        │               Ruta del archivo                      │"
echo "  ├──────────────────────┼─────────────────────────────────────────────────────┤"
echo "  │ Windows (PowerShell) │ C:\\Users\\${CURRENT_USER}\\.notebooklm\\storage_state.json   │"
echo "  ├──────────────────────┼─────────────────────────────────────────────────────┤"
echo "  │ WSL2 (Linux)         │ /home/${CURRENT_USER}/.notebooklm/storage_state.json        │"
echo "  └──────────────────────┴─────────────────────────────────────────────────────┘"
echo
