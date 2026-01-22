#
# Este script muestra la lista de cuaderno en orden cronológico inverso de creacion/modificacion
#

# Descomenta la línea siguiente para asegurarte de que se ejecuta el script de inicialización de la variable NOTEBOOKLM_HOME
# unset NOTEBOOKLM_HOME

if [ "X$NOTEBOOKLM_HOME" == "X"  ]
then
   # No se muestra el aviso porque haría que el resultado no fuese un JSON válido, y podría
   # quererse filtrar la salida con "jq".
   #
   # echo "Ejecutando script que fija la variable NOTEBOOKLM_HOME ..."
   source zzz_asigna_ubicacion_fichero_configuracion.inc.sh
fi

# OJO, se hace uso de la opción "--json", que no se menciona en la ayuda
notebooklm list --json | jq '.notebooks |= (sort_by(.created_at) | reverse)'
