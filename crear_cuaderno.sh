#!/bin/bash
#
# Crear cuaderno en NotebookLM desde video de YouTube (versión Bash)
#
# Por defecto genera solo contenidos sin límites de cuota:
#   - Report (Briefing Doc)
#   - Mind Map
#
# Uso:
#   ./crear_cuaderno.sh <URL_YOUTUBE> [opciones]
#
# Opciones:
#   --audio        Generar podcast (límite diario)
#   --video        Generar video (límite diario)
#   --slides       Generar presentación (límite diario)
#   --infographic  Generar infografía (límite diario)
#   --quiz         Generar quiz (límite diario)
#   --flashcards   Generar flashcards (límite diario)
#   --todo         Generar todos los artefactos
#   --solo-limite  Solo artefactos con límite (sin report/mind-map)
#
# Requisitos:
#   - notebooklm CLI instalado y autenticado (notebooklm login)
#   - yt-dlp instalado
#   - jq instalado (para parsear JSON)
#
# Versión: 1.1.0

set -e

VERSION="1.2.0"
IDIOMA="es"

# Opciones de artefactos (0=no generar, 1=generar)
OPT_REPORT=1
OPT_MINDMAP=1
OPT_AUDIO=0
OPT_VIDEO=0
OPT_SLIDES=0
OPT_INFOGRAPHIC=0
OPT_QUIZ=0
OPT_FLASHCARDS=0

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
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

nota() {
    echo -e "${CYAN}$1${NC}"
}

timestamp() {
    date "+%H:%M:%S"
}

mostrar_ayuda() {
    cat << 'EOF'
Crear cuaderno en NotebookLM desde video de YouTube

Uso:
  ./crear_cuaderno.sh <URL_YOUTUBE> [opciones]

Opciones:
  --audio        Generar podcast (⚠ límite diario)
  --video        Generar video (⚠ límite diario)
  --slides       Generar presentación (⚠ límite diario)
  --infographic  Generar infografía (⚠ límite diario)
  --quiz         Generar quiz (⚠ límite diario)
  --flashcards   Generar flashcards (⚠ límite diario)
  --todo         Generar todos los artefactos
  --solo-limite  Solo artefactos con límite (omite report/mind-map)
  -h, --help     Mostrar esta ayuda

Por defecto genera (sin límites):
  - Report (Briefing Doc)
  - Mind Map

Ejemplos:
  ./crear_cuaderno.sh "https://www.youtube.com/watch?v=VIDEO_ID"
  ./crear_cuaderno.sh "https://www.youtube.com/watch?v=VIDEO_ID" --audio
  ./crear_cuaderno.sh "https://www.youtube.com/watch?v=VIDEO_ID" --todo
  ./crear_cuaderno.sh "https://www.youtube.com/watch?v=VIDEO_ID" --slides --infographic
EOF
    exit 0
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

# Generar un artefacto
generar_artefacto() {
    local tipo="$1"
    local nombre="$2"
    local con_limite="$3"

    echo ""
    if [ "$con_limite" = "1" ]; then
        echo "[$(timestamp)] Generando: $nombre (⚠ límite diario)"
    else
        echo "[$(timestamp)] Generando: $nombre"
    fi

    local resultado=0
    case "$tipo" in
        report)
            notebooklm generate report --language "$IDIOMA" 2>/dev/null && resultado=1
            ;;
        mind-map)
            notebooklm generate mind-map 2>/dev/null && resultado=1
            ;;
        audio)
            notebooklm generate audio --language "$IDIOMA" 2>/dev/null && resultado=1
            ;;
        video)
            notebooklm generate video --language "$IDIOMA" 2>/dev/null && resultado=1
            ;;
        slides)
            notebooklm generate slide-deck --language "$IDIOMA" 2>/dev/null && resultado=1
            ;;
        infographic)
            notebooklm generate infographic --language "$IDIOMA" 2>/dev/null && resultado=1
            ;;
        quiz)
            notebooklm generate quiz 2>/dev/null && resultado=1
            ;;
        flashcards)
            notebooklm generate flashcards 2>/dev/null && resultado=1
            ;;
    esac

    if [ "$resultado" = "1" ]; then
        info "[$(timestamp)] ✓ $nombre generado"
        return 0
    else
        if [ "$con_limite" = "1" ]; then
            warn "[$(timestamp)] ✗ $nombre: Error o límite diario alcanzado"
        else
            warn "[$(timestamp)] ✗ Error generando $nombre"
        fi
        return 1
    fi
}

# Parsear argumentos
parse_args() {
    local url=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help)
                mostrar_ayuda
                ;;
            --audio)
                OPT_AUDIO=1
                shift
                ;;
            --video)
                OPT_VIDEO=1
                shift
                ;;
            --slides)
                OPT_SLIDES=1
                shift
                ;;
            --infographic)
                OPT_INFOGRAPHIC=1
                shift
                ;;
            --quiz)
                OPT_QUIZ=1
                shift
                ;;
            --flashcards)
                OPT_FLASHCARDS=1
                shift
                ;;
            --todo)
                OPT_AUDIO=1
                OPT_VIDEO=1
                OPT_SLIDES=1
                OPT_INFOGRAPHIC=1
                OPT_QUIZ=1
                OPT_FLASHCARDS=1
                shift
                ;;
            --solo-limite)
                OPT_REPORT=0
                OPT_MINDMAP=0
                OPT_AUDIO=1
                OPT_VIDEO=1
                OPT_SLIDES=1
                OPT_INFOGRAPHIC=1
                OPT_QUIZ=1
                OPT_FLASHCARDS=1
                shift
                ;;
            -*)
                error "Opción desconocida: $1"
                ;;
            *)
                if [ -z "$url" ]; then
                    url="$1"
                else
                    error "Demasiados argumentos"
                fi
                shift
                ;;
        esac
    done

    echo "$url"
}

# Main
main() {
    # Parsear argumentos
    local url
    url=$(parse_args "$@")

    echo "NotebookLM YouTube Importer (Bash) v$VERSION"
    echo "Idioma forzado: $IDIOMA"

    # Mostrar qué se va a generar
    local artefactos_sin_limite=""
    local artefactos_con_limite=""

    [ "$OPT_REPORT" = "1" ] && artefactos_sin_limite+="report "
    [ "$OPT_MINDMAP" = "1" ] && artefactos_sin_limite+="mind-map "
    [ "$OPT_AUDIO" = "1" ] && artefactos_con_limite+="audio "
    [ "$OPT_VIDEO" = "1" ] && artefactos_con_limite+="video "
    [ "$OPT_SLIDES" = "1" ] && artefactos_con_limite+="slides "
    [ "$OPT_INFOGRAPHIC" = "1" ] && artefactos_con_limite+="infographic "
    [ "$OPT_QUIZ" = "1" ] && artefactos_con_limite+="quiz "
    [ "$OPT_FLASHCARDS" = "1" ] && artefactos_con_limite+="flashcards "

    if [ -n "$artefactos_sin_limite" ]; then
        echo "Artefactos sin límite: $artefactos_sin_limite"
    fi
    if [ -n "$artefactos_con_limite" ]; then
        warn "Artefactos con límite: $artefactos_con_limite"
        nota "  (pueden fallar si se alcanzó el límite diario)"
    fi
    echo ""

    # Verificar URL
    if [ -z "$url" ]; then
        echo "Uso: $0 <URL_YOUTUBE> [opciones]"
        echo ""
        echo "Usa --help para ver todas las opciones"
        exit 1
    fi

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

    local es_nuevo=0
    if [ -n "$notebook_id" ]; then
        info "Cuaderno encontrado: $notebook_id"
        echo "URL: https://notebooklm.google.com/notebook/$notebook_id"
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
        es_nuevo=1
    fi

    # Verificar artefactos existentes
    echo ""
    echo "Verificando artefactos existentes..."
    local artifacts_json
    artifacts_json=$(listar_artefactos "$notebook_id")

    # Definir artefactos a verificar/generar
    # Formato: tipo|nombre_mostrar|tipo_api|con_limite|opcion
    # Orden: sin límite primero, luego por tiempo de generación
    # report: sin límite, 5-15 min
    # mind-map: sin límite, instant
    # slides/infographic: con límite, tiempo medio
    # quiz/flashcards: con límite, 5-15 min
    # audio: con límite, 10-20 min (penúltimo)
    # video: con límite, 15-45 min (último)
    local ARTEFACTOS=(
        "report|Report (Briefing Doc)|Briefing Doc|0|OPT_REPORT"
        "mind-map|Mind Map|Mind Map|0|OPT_MINDMAP"
        "slides|Presentación (Slides)|Slide Deck|1|OPT_SLIDES"
        "infographic|Infografía|Infographic|1|OPT_INFOGRAPHIC"
        "quiz|Quiz|Quiz|1|OPT_QUIZ"
        "flashcards|Flashcards|Flashcards|1|OPT_FLASHCARDS"
        "audio|Audio (Podcast)|Audio Overview|1|OPT_AUDIO"
        "video|Video|Video Overview|1|OPT_VIDEO"
    )

    local faltantes=()
    local faltantes_limite=()

    echo ""
    echo "Estado de artefactos:"

    for item in "${ARTEFACTOS[@]}"; do
        IFS='|' read -r tipo nombre tipo_api con_limite opcion <<< "$item"

        # Verificar si esta opción está activa
        local activo=0
        eval "activo=\$$opcion"

        if [ "$activo" = "1" ]; then
            if existe_artefacto "$artifacts_json" "$tipo_api"; then
                info "  ✓ $nombre: disponible"
            else
                if [ "$con_limite" = "1" ]; then
                    warn "  ✗ $nombre: no disponible (⚠ límite)"
                    faltantes+=("$tipo|$nombre|$con_limite")
                else
                    warn "  ✗ $nombre: no disponible"
                    faltantes+=("$tipo|$nombre|$con_limite")
                fi
            fi
        fi
    done

    # Generar artefactos faltantes
    if [ ${#faltantes[@]} -gt 0 ]; then
        echo ""
        echo "Generando ${#faltantes[@]} artefacto(s)..."

        # Establecer contexto para generación
        notebooklm use "$notebook_id" >/dev/null 2>&1

        local exitosos=0
        local total=${#faltantes[@]}

        for item in "${faltantes[@]}"; do
            IFS='|' read -r tipo nombre con_limite <<< "$item"

            if generar_artefacto "$tipo" "$nombre" "$con_limite"; then
                ((exitosos++)) || true
            fi
        done

        echo ""
        echo "Artefactos generados: $exitosos/$total"
    else
        echo ""
        info "Todos los artefactos solicitados ya están disponibles"
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
