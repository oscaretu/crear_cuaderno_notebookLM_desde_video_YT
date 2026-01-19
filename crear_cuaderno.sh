#!/bin/bash
#
# Crear cuaderno en NotebookLM desde video de YouTube (versión Bash)
#
# Genera solo contenidos sin límites de cuota:
#   - Report (Briefing Doc)
#   - Mind Map
#
# Uso:
#   ./crear_cuaderno.sh <URL_YOUTUBE>
#
# Requisitos:
#   - notebooklm CLI instalado y autenticado (notebooklm login)
#   - yt-dlp instalado
#   - jq instalado (para parsear JSON)
#
# Versión: 1.0.0

set -e

VERSION="1.0.0"
IDIOMA="es"

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

error() {
    echo -e "${RED}Error: $1${NC}" >&2
    exit 1
}

info() {
    echo -e "${GREEN}$1${NC}"
}

warn() {
    echo -e "${YELLOW}$1${NC}"
}

timestamp() {
    date "+%H:%M:%S"
}

# Verificar dependencias
check_dependencies() {
    local missing=()

    command -v notebooklm >/dev/null 2>&1 || missing+=("notebooklm")
    command -v yt-dlp >/dev/null 2>&1 || missing+=("yt-dlp")
    command -v jq >/dev/null 2>&1 || missing+=("jq")

    if [ ${#missing[@]} -ne 0 ]; then
        error "Faltan dependencias: ${missing[*]}"
    fi
}

# Extraer video_id de URL de YouTube
extraer_video_id() {
    local url="$1"
    local video_id=""

    # Patrón: youtube.com/watch?v=VIDEO_ID
    if [[ "$url" =~ youtube\.com/watch\?v=([a-zA-Z0-9_-]+) ]]; then
        video_id="${BASH_REMATCH[1]}"
    # Patrón: youtu.be/VIDEO_ID
    elif [[ "$url" =~ youtu\.be/([a-zA-Z0-9_-]+) ]]; then
        video_id="${BASH_REMATCH[1]}"
    # Patrón: youtube.com/embed/VIDEO_ID
    elif [[ "$url" =~ youtube\.com/embed/([a-zA-Z0-9_-]+) ]]; then
        video_id="${BASH_REMATCH[1]}"
    fi

    echo "$video_id"
}

# Limpiar texto para nombre de cuaderno
limpiar_texto() {
    local texto="$1"
    local max_length="${2:-50}"

    # Eliminar caracteres problemáticos
    texto=$(echo "$texto" | sed 's/[<>:"\/\\|?*]//g')

    # Truncar si es muy largo
    if [ ${#texto} -gt "$max_length" ]; then
        texto="${texto:0:$max_length}..."
    fi

    echo "$texto"
}

# Buscar cuaderno existente por prefijo
buscar_cuaderno_existente() {
    local prefijo="$1"

    # Listar cuadernos y buscar por prefijo
    local notebooks_json
    notebooks_json=$(notebooklm list --json 2>/dev/null) || return 1

    # Buscar cuaderno que empiece con el prefijo
    echo "$notebooks_json" | jq -r --arg prefix "$prefijo" \
        '.notebooks[] | select(.title | startswith($prefix)) | .id' | head -1
}

# Listar artefactos existentes
listar_artefactos() {
    local notebook_id="$1"
    notebooklm artifact list --notebook "$notebook_id" --json 2>/dev/null || echo '{"artifacts":[]}'
}

# Verificar si existe un tipo de artefacto
existe_artefacto() {
    local artifacts_json="$1"
    local tipo="$2"

    echo "$artifacts_json" | jq -e --arg tipo "$tipo" \
        '.artifacts[] | select(.type == $tipo)' >/dev/null 2>&1
}

# Main
main() {
    echo "NotebookLM YouTube Importer (Bash) v$VERSION"
    echo "Idioma forzado: $IDIOMA"
    echo ""

    # Verificar argumentos
    if [ $# -lt 1 ]; then
        echo "Uso: $0 <URL_YOUTUBE>"
        echo ""
        echo "Ejemplo:"
        echo "  $0 \"https://www.youtube.com/watch?v=dQw4w9WgXcQ\""
        exit 1
    fi

    local url="$1"

    # Verificar dependencias
    check_dependencies

    # Extraer video_id
    local video_id
    video_id=$(extraer_video_id "$url")

    if [ -z "$video_id" ]; then
        error "No se pudo extraer el video_id de: $url"
    fi

    echo "Video ID: $video_id"

    # Obtener metadatos con yt-dlp
    echo "Obteniendo metadatos del video..."
    local titulo canal fecha

    titulo=$(yt-dlp --get-title "$url" 2>/dev/null) || titulo="Sin título"
    canal=$(yt-dlp --print "%(channel)s" "$url" 2>/dev/null) || canal="Canal desconocido"
    fecha=$(yt-dlp --print "%(upload_date)s" "$url" 2>/dev/null) || fecha=""

    # Formatear fecha (de YYYYMMDD a YYYY-MM-DD)
    if [ -n "$fecha" ] && [ ${#fecha} -eq 8 ]; then
        fecha="${fecha:0:4}-${fecha:4:2}-${fecha:6:2}"
    else
        fecha="fecha-desconocida"
    fi

    echo "  Título: $titulo"
    echo "  Canal: $canal"
    echo "  Fecha: $fecha"

    # Generar nombre del cuaderno
    local titulo_limpio canal_limpio nombre_cuaderno
    titulo_limpio=$(limpiar_texto "$titulo" 60)
    canal_limpio=$(limpiar_texto "$canal" 30)
    nombre_cuaderno="YT-${video_id} - ${titulo_limpio} - ${fecha} - ${canal_limpio}"

    echo ""
    echo "Nombre del cuaderno: $nombre_cuaderno"

    # Buscar cuaderno existente
    echo ""
    echo "Buscando cuaderno existente..."
    local notebook_id
    notebook_id=$(buscar_cuaderno_existente "YT-${video_id}")

    if [ -n "$notebook_id" ]; then
        info "Cuaderno encontrado: $notebook_id"
        echo "URL: https://notebooklm.google.com/notebook/$notebook_id"

        # Verificar artefactos existentes
        echo ""
        echo "Verificando artefactos existentes..."
        local artifacts_json
        artifacts_json=$(listar_artefactos "$notebook_id")

        # Mostrar estado
        echo ""
        echo "Estado de artefactos (sin límites de cuota):"

        local faltantes=()

        if existe_artefacto "$artifacts_json" "Briefing Doc"; then
            info "  ✓ Report (Briefing Doc): disponible"
        else
            warn "  ✗ Report (Briefing Doc): no disponible"
            faltantes+=("report")
        fi

        if existe_artefacto "$artifacts_json" "Mind Map"; then
            info "  ✓ Mind Map: disponible"
        else
            warn "  ✗ Mind Map: no disponible"
            faltantes+=("mind-map")
        fi

    else
        # Crear nuevo cuaderno
        echo "No existe, creando cuaderno..."
        local create_result
        create_result=$(notebooklm create "$nombre_cuaderno" --json) || error "No se pudo crear el cuaderno"

        notebook_id=$(echo "$create_result" | jq -r '.id')
        info "Cuaderno creado: $notebook_id"
        echo "URL: https://notebooklm.google.com/notebook/$notebook_id"

        # Establecer contexto
        notebooklm use "$notebook_id" >/dev/null 2>&1

        # Añadir fuente
        echo ""
        echo "Añadiendo video como fuente..."
        notebooklm source add "$url" || warn "Aviso al añadir fuente (puede estar procesándose)"

        info "Fuente añadida"

        # Todos los artefactos faltan
        faltantes=("report" "mind-map")
    fi

    # Generar artefactos faltantes
    if [ ${#faltantes[@]} -gt 0 ]; then
        echo ""
        echo "Generando ${#faltantes[@]} artefacto(s)..."

        # Establecer contexto para generación
        notebooklm use "$notebook_id" >/dev/null 2>&1

        for tipo in "${faltantes[@]}"; do
            echo ""
            echo "[$(timestamp)] Generando: $tipo"

            case "$tipo" in
                report)
                    if notebooklm generate report --language "$IDIOMA" 2>/dev/null; then
                        info "[$(timestamp)] ✓ Report generado"
                    else
                        warn "[$(timestamp)] ✗ Error generando report"
                    fi
                    ;;
                mind-map)
                    if notebooklm generate mind-map 2>/dev/null; then
                        info "[$(timestamp)] ✓ Mind Map generado"
                    else
                        warn "[$(timestamp)] ✗ Error generando mind-map"
                    fi
                    ;;
            esac
        done
    else
        echo ""
        info "Todos los artefactos ya están disponibles"
    fi

    # Resumen final
    echo ""
    echo "=================================================="
    info "Proceso completado"
    echo "  Cuaderno: $nombre_cuaderno"
    echo "  URL: https://notebooklm.google.com/notebook/$notebook_id"
    echo "=================================================="
}

main "$@"
