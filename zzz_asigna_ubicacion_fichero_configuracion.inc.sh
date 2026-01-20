echo
echo Este fichero para ejecutar con source está pensado para ejecutar los script main.py y 
echo listar_cuadernos.py desde WSL.
echo
echo Aquí forzamos la ubicación del fichero JSON de configuración para que pueda encontrarlo
echo el módulo notebooklm de Python al ejecutar los scripts desde WSL.
echo
echo Antes necesitarás generar el fichero JSON
echo 'Abre PowerShell y vete a "C:\Users\oscar\Downloads\crear_cuaderno_notebookLM_desde_video_YT"' 
echo 'Luego ejecuta "notebooklm login"'
echo
echo Exportando la variable NOTEBOOKLM_HOME... 
export NOTEBOOKLM_HOME="/mnt/c/Users/oscar/.notebooklm"
echo NOTEBOOKLM_HOME=$NOTEBOOKLM_HOME
echo
echo Recuerda que si no apuntas directamente al fichero generado desde la ventana de PowerShell
echo tienes que copiar ese fichero a /home/oscar/.notebooklm/storage_state.json
echo
echo '  ┌──────────────────────┬───────────────────────────────────────────────┐'
echo '  │       Entorno        │               Ruta del archivo                │'
echo '  ├──────────────────────┼───────────────────────────────────────────────┤'
echo '  │ Windows (PowerShell) │ C:\Users\oscar\.notebooklm\storage_state.json │'
echo '  ├──────────────────────┼───────────────────────────────────────────────┤'
echo '  │ WSL2 (Linux)         │ /home/oscar/.notebooklm/storage_state.json    │'
echo '  └──────────────────────┴───────────────────────────────────────────────┘'
echo

