#!/usr/bin/env python3
"""
Extrae cookies de Google desde Firefox y genera storage_state.json para notebooklm-py.

================================================================================
¿QUÉ HACE ESTE SCRIPT?
================================================================================

Este script soluciona un problema: la librería notebooklm-py necesita cookies
de autenticación de Google para funcionar, y normalmente hay que ejecutar
"notebooklm login" que abre un navegador nuevo. Pero si ya tienes Firefox
abierto con tu sesión de Google/Gmail activa, este script extrae esas cookies
y las convierte al formato que necesita notebooklm-py.

Ventajas:
- No necesitas hacer login de nuevo
- Firefox puede seguir abierto
- Las cookies duran más porque compartes la sesión con tu navegador habitual

================================================================================
¿CÓMO FUNCIONA? (paso a paso)
================================================================================

1. LOCALIZAR EL PERFIL DE FIREFOX
   Firefox guarda los datos de cada usuario en "perfiles". Cada perfil es una
   carpeta en: C:\\Users\\<usuario>\\AppData\\Roaming\\Mozilla\\Firefox\\Profiles\\
   El script busca el perfil por defecto (o el que indiques con --perfil).

2. COPIAR LA BASE DE DATOS DE COOKIES
   Firefox guarda las cookies en un archivo SQLite llamado "cookies.sqlite".
   Como Firefox puede tener el archivo bloqueado mientras está abierto,
   el script hace una copia temporal para poder leerlo.

3. EXTRAER LAS COOKIES DE GOOGLE
   De todas las cookies en la base de datos, el script filtra solo las que:
   - Son de dominios de Google (.google.com, notebooklm.google.com, etc.)
   - Son cookies de autenticación (SID, HSID, SSID, etc.)
   Esto reduce de cientos de cookies a solo ~24 necesarias.

4. VERIFICAR QUE ESTÁN LAS COOKIES MÍNIMAS
   La librería notebooklm-py requiere al menos la cookie "SID".
   Si no está, significa que no tienes sesión activa de Google en Firefox.

5. GENERAR EL ARCHIVO JSON
   Las cookies se guardan en formato JSON compatible con Playwright
   (la herramienta que usa notebooklm-py internamente).
   El archivo se guarda en: ~/.notebooklm/storage_state.json

================================================================================
USO
================================================================================

    python extraer_cookies_firefox.py [opciones]

Ejemplos:
    python extraer_cookies_firefox.py                    # Usa perfil por defecto
    python extraer_cookies_firefox.py --listar-perfiles  # Ver perfiles disponibles
    python extraer_cookies_firefox.py --perfil Susana    # Usar perfil específico
    python extraer_cookies_firefox.py --dry-run          # Ver cookies sin escribir
    python extraer_cookies_firefox.py -o /tmp/test.json  # Guardar en otra ruta

Plataformas soportadas:
    - WSL2: Accede a Firefox instalado en Windows (via /mnt/c/)
    - Windows: PowerShell o CMD con Firefox instalado en Windows
    - Linux: Firefox instalado en Linux nativo
    - macOS: Firefox instalado en macOS

Requisitos:
    - Firefox instalado con sesión activa de Google/NotebookLM

Notas:
    - Firefox puede estar abierto (se copia la base de datos)
    - Las cookies se filtran a dominios de Google relevantes para NotebookLM
    - Se crea backup automático del archivo anterior (.json.bak)
    - La plataforma se detecta automáticamente
"""

# ==============================================================================
# IMPORTACIONES
# ==============================================================================
# Estas son las librerías de Python que necesita el script.
# Todas vienen incluidas con Python, no hay que instalar nada extra.

import argparse      # Para procesar los argumentos de línea de comandos (--perfil, --dry-run, etc.)
import json          # Para leer/escribir archivos JSON
import os            # Para operaciones del sistema operativo (rutas, permisos)
import shutil        # Para copiar archivos
import sqlite3       # Para leer la base de datos SQLite de Firefox
import sys           # Para salir del programa con código de error
import tempfile      # Para crear archivos temporales
from datetime import datetime  # Para obtener la fecha/hora actual
from pathlib import Path       # Para manejar rutas de archivos de forma moderna

VERSION = "1.0.0"

# ==============================================================================
# CONFIGURACIÓN: DOMINIOS Y COOKIES PERMITIDOS
# ==============================================================================
# Estas constantes definen qué cookies extraer de Firefox.
# Solo queremos las cookies de autenticación de Google, no todas.

# Dominios de cookies que usa notebooklm-py (definidos en su archivo auth.py)
# El punto inicial (.google.com) significa "este dominio y todos sus subdominios"
ALLOWED_DOMAINS = {
    '.google.com',              # Dominio principal de Google
    'notebooklm.google.com',    # Dominio específico de NotebookLM
    '.googleusercontent.com',   # Dominio para contenido de usuario (descargas, etc.)
}

# Dominios regionales de Google (para usuarios fuera de EEUU)
# Google usa dominios locales en cada país, y las cookies pueden estar ahí
GOOGLE_REGIONAL_SUFFIXES = {
    '.google.es',      # España
    '.google.co.uk',   # Reino Unido
    '.google.de',      # Alemania
    '.google.fr',      # Francia
    '.google.it',      # Italia
    '.google.com.mx',  # México
    '.google.com.ar',  # Argentina
    '.google.com.br',  # Brasil
}

# Nombres de cookies de autenticación de Google
# Estas son las cookies que Google usa para saber que has iniciado sesión.
# Hay varias porque Google usa diferentes mecanismos de seguridad.
AUTH_COOKIE_NAMES = {
    # Cookies principales de sesión (las más importantes)
    'SID', 'HSID', 'SSID', 'APISID', 'SAPISID',

    # Cookies seguras (versiones con prefijo __Secure-)
    # Son las mismas pero con protección adicional contra ataques
    '__Secure-1PSID', '__Secure-3PSID',
    '__Secure-1PAPISID', '__Secure-3PAPISID',
    '__Secure-1PSIDCC', '__Secure-3PSIDCC',
    '__Secure-1PSIDTS', '__Secure-3PSIDTS',
    '__Secure-1PSIDRTS', '__Secure-3PSIDRTS',

    # Cookies de sesión adicionales
    'SIDCC', 'OSID', '__Secure-OSID',

    # Cookies de cuenta (para el selector de cuentas de Google)
    'LSID', '__Host-1PLSID', '__Host-3PLSID',
    '__Host-GAPS', 'ACCOUNT_CHOOSER',

    # Otras cookies necesarias
    'NID',   # Cookie de preferencias de Google
    'AEC',   # Cookie anti-abuso
    'SOCS',  # Cookie de consentimiento
}

# Cookies mínimas requeridas para que funcione notebooklm-py
# Sin al menos SID, no hay sesión válida
REQUIRED_COOKIES = {'SID'}

# ==============================================================================
# CONFIGURACIÓN: RUTAS DE FIREFOX
# ==============================================================================

# Rutas donde Firefox guarda los perfiles según el sistema operativo
# {user} se reemplaza por el nombre de usuario

# Ruta en WSL (Linux accediendo a Windows via /mnt/c/)
FIREFOX_PROFILES_WSL = "/mnt/c/Users/{user}/AppData/Roaming/Mozilla/Firefox/Profiles"

# Ruta en Windows nativo (PowerShell, CMD)
FIREFOX_PROFILES_WINDOWS = r"C:\Users\{user}\AppData\Roaming\Mozilla\Firefox\Profiles"

# Ruta en Linux nativo (Firefox instalado en Linux)
FIREFOX_PROFILES_LINUX = "/home/{user}/.mozilla/firefox"

# Ruta en macOS
FIREFOX_PROFILES_MACOS = "/Users/{user}/Library/Application Support/Firefox/Profiles"


def detectar_plataforma() -> str:
    """
    Detecta en qué plataforma está corriendo el script.

    Returns:
        'wsl': Windows Subsystem for Linux (accediendo a Firefox de Windows)
        'windows': Windows nativo (PowerShell, CMD)
        'linux': Linux nativo
        'macos': macOS
    """
    import platform

    sistema = platform.system().lower()

    if sistema == 'linux':
        # Verificar si es WSL comprobando si existe /mnt/c/
        # WSL monta el disco C: de Windows en /mnt/c/
        if Path('/mnt/c/Windows').exists():
            return 'wsl'
        return 'linux'
    elif sistema == 'windows':
        return 'windows'
    elif sistema == 'darwin':
        return 'macos'
    else:
        # Asumir Linux si no se reconoce
        return 'linux'


def obtener_ruta_perfiles(usuario: str, plataforma: str = None) -> Path:
    """
    Obtiene la ruta al directorio de perfiles de Firefox según la plataforma.

    Args:
        usuario: Nombre de usuario
        plataforma: Forzar plataforma ('wsl', 'windows', 'linux', 'macos').
                    Si es None, se detecta automáticamente.

    Returns:
        Path al directorio de perfiles de Firefox
    """
    if plataforma is None:
        plataforma = detectar_plataforma()

    if plataforma == 'wsl':
        return Path(FIREFOX_PROFILES_WSL.format(user=usuario))
    elif plataforma == 'windows':
        return Path(FIREFOX_PROFILES_WINDOWS.format(user=usuario))
    elif plataforma == 'macos':
        return Path(FIREFOX_PROFILES_MACOS.format(user=usuario))
    else:  # linux
        return Path(FIREFOX_PROFILES_LINUX.format(user=usuario))


# ==============================================================================
# FUNCIONES AUXILIARES
# ==============================================================================

def extraer_nombre_bonito(nombre_dir: str) -> str:
    """
    Extrae el nombre 'bonito' de un directorio de perfil Firefox.

    Firefox nombra las carpetas de perfil con el formato: <hash>.<nombre>
    donde <hash> es un código aleatorio de 8 caracteres.

    Ejemplos:
        'vonalg81.default-release' -> 'default-release'
        'kyetl4dz.Susana' -> 'Susana'
        '9zudahgi.default' -> 'default'
    """
    if '.' in nombre_dir:
        # split('.', 1) divide solo en el primer punto
        # [1] toma la segunda parte (después del punto)
        return nombre_dir.split('.', 1)[1]
    return nombre_dir


def listar_perfiles_firefox(usuario: str) -> list[tuple[str, str, bool]]:
    """
    Lista los perfiles de Firefox disponibles para un usuario.

    Args:
        usuario: Nombre de usuario (ej: 'oscar')

    Returns:
        Lista de tuplas con:
        - nombre_directorio: Nombre completo de la carpeta (ej: 'vonalg81.default-release')
        - nombre_bonito: Nombre legible (ej: 'default-release')
        - es_default: True si es el perfil por defecto
    """
    # Construir la ruta al directorio de perfiles (detecta plataforma automáticamente)
    base = obtener_ruta_perfiles(usuario)

    if not base.exists():
        raise FileNotFoundError(f"No se encuentra directorio de perfiles Firefox: {base}")

    perfiles = []
    # sorted() ordena alfabéticamente, iterdir() lista el contenido del directorio
    for p in sorted(base.iterdir()):
        if p.is_dir():  # Solo directorios, ignorar archivos
            nombre_bonito = extraer_nombre_bonito(p.name)
            # Firefox marca los perfiles por defecto con 'default-release' o '.default'
            es_default = 'default-release' in p.name or p.name.endswith('.default')
            perfiles.append((p.name, nombre_bonito, es_default))

    return perfiles


def encontrar_perfil_firefox(usuario: str, nombre_perfil: str = None) -> Path:
    """
    Encuentra el perfil de Firefox a usar.

    Si se especifica nombre_perfil, busca uno que contenga ese texto.
    Si no, busca el perfil por defecto.

    Args:
        usuario: Nombre de usuario
        nombre_perfil: Texto a buscar en el nombre del perfil (opcional)

    Returns:
        Path al directorio del perfil encontrado
    """
    # Construir la ruta al directorio de perfiles (detecta plataforma automáticamente)
    base = obtener_ruta_perfiles(usuario)

    if not base.exists():
        raise FileNotFoundError(f"No se encuentra directorio de perfiles Firefox: {base}")

    perfiles = list(base.iterdir())

    if nombre_perfil:
        # Buscar perfil que contenga el texto especificado
        for p in perfiles:
            if nombre_perfil in p.name:
                return p
        raise FileNotFoundError(f"Perfil '{nombre_perfil}' no encontrado en {base}")

    # Si no se especificó perfil, buscar el por defecto
    # Prioridad 1: perfil 'default-release' (el principal en instalaciones modernas)
    for p in perfiles:
        if 'default-release' in p.name:
            return p

    # Prioridad 2: cualquier perfil con 'default' en el nombre
    for p in perfiles:
        if 'default' in p.name:
            return p

    raise FileNotFoundError(f"No se encontró perfil por defecto en {base}")


def copiar_cookies_db(perfil: Path) -> Path:
    """
    Copia la base de datos de cookies de Firefox a un archivo temporal.

    Firefox mantiene el archivo cookies.sqlite bloqueado mientras está abierto,
    por lo que no podemos leerlo directamente. La solución es copiarlo a otra
    ubicación y leer la copia.

    Args:
        perfil: Path al directorio del perfil de Firefox

    Returns:
        Path al archivo temporal con la copia de la base de datos
    """
    cookies_db = perfil / "cookies.sqlite"

    if not cookies_db.exists():
        raise FileNotFoundError(f"No se encuentra {cookies_db}")

    # Crear archivo temporal con extensión .sqlite
    temp_db = Path(tempfile.mktemp(suffix=".sqlite"))
    # copy2 preserva metadatos (fechas, permisos)
    shutil.copy2(cookies_db, temp_db)

    return temp_db


def es_dominio_permitido(host: str) -> bool:
    """
    Verifica si el dominio es relevante para NotebookLM.

    Solo incluimos cookies de los dominios estrictamente necesarios para
    evitar extraer cookies innecesarias (Gmail, YouTube, etc.).

    Args:
        host: Dominio de la cookie (ej: '.google.com', 'notebooklm.google.com')

    Returns:
        True si la cookie es de un dominio necesario para NotebookLM
    """
    # Dominios principales que necesitamos
    dominios_necesarios = {
        '.google.com',              # Cookies de sesión principales
        'notebooklm.google.com',    # Cookies específicas de NotebookLM
        'accounts.google.com',      # Cookies de autenticación
    }

    if host in dominios_necesarios:
        return True

    # También aceptar dominios regionales (para usuarios de España, UK, etc.)
    for regional in GOOGLE_REGIONAL_SUFFIXES:
        # lstrip('.') quita el punto inicial para comparar
        if host == regional.lstrip('.') or host == regional:
            return True

    return False


def es_cookie_auth(name: str) -> bool:
    """
    Verifica si la cookie es de autenticación.

    Args:
        name: Nombre de la cookie (ej: 'SID', '__Secure-1PSID')

    Returns:
        True si es una cookie de autenticación que necesitamos
    """
    return name in AUTH_COOKIE_NAMES


def extraer_cookies_google(db_path: Path) -> list[dict]:
    """
    Extrae cookies de autenticación de Google de la base de datos de Firefox.

    Este es el corazón del script. Lee la base de datos SQLite de Firefox,
    filtra solo las cookies necesarias, y las convierte al formato JSON
    que espera Playwright/notebooklm-py.

    Args:
        db_path: Path a la copia temporal de cookies.sqlite

    Returns:
        Lista de diccionarios, cada uno representando una cookie
    """
    # Diccionario para deduplicar: clave=(nombre, dominio), valor=cookie
    cookies_dict = {}

    # Conectar a la base de datos SQLite
    conn = sqlite3.connect(str(db_path))
    # row_factory=Row permite acceder a columnas por nombre (row['name'])
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Consulta SQL para obtener cookies de Google
    # ORDER BY expiry DESC = ordenar por expiración descendente (más tardía primero)
    # Esto nos permite quedarnos con la cookie más "fresca" si hay duplicados
    query = """
        SELECT name, value, host, path, expiry, isSecure, isHttpOnly, sameSite
        FROM moz_cookies
        WHERE host LIKE '%google%'
        ORDER BY expiry DESC
    """

    cursor.execute(query)

    # Procesar cada cookie encontrada
    for row in cursor.fetchall():
        host = row['host']
        name = row['name']

        # Aplicar filtros: solo dominios permitidos Y cookies de autenticación
        if not es_dominio_permitido(host):
            continue
        if not es_cookie_auth(name):
            continue

        # Deduplicar: si ya tenemos esta cookie (mismo nombre+dominio), saltar
        # Como ordenamos por expiración DESC, la primera que encontramos es la mejor
        key = (name, host)
        if key in cookies_dict:
            continue

        # Convertir el atributo sameSite de formato Firefox a formato Playwright
        # Firefox usa números: 0=None, 1=Lax, 2=Strict
        # Playwright usa strings: "None", "Lax", "Strict"
        same_site_map = {0: "None", 1: "Lax", 2: "Strict"}
        same_site = same_site_map.get(row['sameSite'], "Lax")

        # Crear diccionario con el formato que espera Playwright
        cookie = {
            "name": name,
            "value": row['value'],
            "domain": host,
            "path": row['path'],
            "expires": row['expiry'],           # Timestamp Unix de expiración
            "httpOnly": bool(row['isHttpOnly']), # ¿Solo accesible por HTTP, no JavaScript?
            "secure": bool(row['isSecure']),     # ¿Solo enviar por HTTPS?
            "sameSite": same_site,               # Política de envío cross-site
        }
        cookies_dict[key] = cookie

    conn.close()

    # Ordenar alfabéticamente por dominio y nombre para salida consistente
    cookies = sorted(cookies_dict.values(), key=lambda c: (c['domain'], c['name']))
    return cookies


def verificar_cookies_minimas(cookies: list[dict]) -> tuple[bool, list[str]]:
    """
    Verifica que estén presentes las cookies mínimas requeridas.

    Args:
        cookies: Lista de cookies extraídas

    Returns:
        Tupla con:
        - bool: True si están todas las cookies requeridas
        - list: Lista de cookies faltantes (vacía si no falta ninguna)
    """
    # Crear conjunto con los nombres de las cookies que tenemos
    nombres = {c['name'] for c in cookies}
    # Buscar cuáles de las requeridas faltan
    faltantes = [r for r in REQUIRED_COOKIES if r not in nombres]
    return len(faltantes) == 0, list(faltantes)


def generar_storage_state(cookies: list[dict], perfil_dir: str, perfil_nombre: str) -> dict:
    """
    Genera el diccionario storage_state en formato Playwright.

    El formato storage_state es el que usa Playwright para guardar el estado
    del navegador (cookies, localStorage, etc.). notebooklm-py espera este formato.

    Args:
        cookies: Lista de cookies a incluir
        perfil_dir: Nombre del directorio del perfil (para metadatos)
        perfil_nombre: Nombre bonito del perfil (para metadatos)

    Returns:
        Diccionario listo para serializar a JSON
    """
    return {
        # Metadatos informativos (no usados por notebooklm-py, solo para referencia)
        "_generated": {
            "tool": "extraer_cookies_firefox.py",
            "version": VERSION,
            "timestamp": datetime.now().isoformat(),
            "source": f"Firefox profile: {perfil_nombre} ({perfil_dir})",
            "cookies_count": len(cookies),
        },
        # Las cookies propiamente dichas
        "cookies": cookies,
        # origins se usa para localStorage, no lo necesitamos
        "origins": []
    }


# ==============================================================================
# FUNCIÓN PRINCIPAL
# ==============================================================================

def main():
    """
    Punto de entrada del script.

    Esta función:
    1. Procesa los argumentos de línea de comandos
    2. Coordina la ejecución de los pasos descritos en la documentación
    3. Maneja errores y muestra mensajes informativos
    """

    # -------------------------------------------------------------------------
    # CONFIGURAR ARGUMENTOS DE LÍNEA DE COMANDOS
    # -------------------------------------------------------------------------
    # argparse es la librería estándar de Python para procesar argumentos
    parser = argparse.ArgumentParser(
        description='Extrae cookies de Google desde Firefox para notebooklm-py',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Ejemplos:
  python extraer_cookies_firefox.py                    # Usa perfil por defecto
  python extraer_cookies_firefox.py --listar-perfiles  # Ver perfiles disponibles
  python extraer_cookies_firefox.py --perfil Susana    # Perfil específico
  python extraer_cookies_firefox.py --dry-run          # Solo muestra, no escribe
  python extraer_cookies_firefox.py -o /tmp/test.json  # Output personalizado
        '''
    )
    # Cada add_argument define una opción que el usuario puede pasar
    parser.add_argument('--usuario', '-u', default='oscar',
                        help='Usuario de Windows (default: oscar)')
    parser.add_argument('--perfil', '-p',
                        help='Nombre del perfil de Firefox. Acepta el nombre bonito (ej: Susana), '
                             'el nombre completo del directorio (ej: kyetl4dz.Susana), o cualquier '
                             'texto contenido en el nombre. Usa --listar-perfiles para ver opciones. '
                             '(default: default-release)')
    parser.add_argument('--output', '-o',
                        default=os.path.expanduser('~/.notebooklm/storage_state.json'),
                        help='Ruta de salida (default: ~/.notebooklm/storage_state.json)')
    parser.add_argument('--dry-run', '-n', action='store_true',
                        help='Solo muestra cookies, no escribe archivo')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Muestra información detallada')
    parser.add_argument('--listar-perfiles', '-l', action='store_true',
                        help='Lista los perfiles de Firefox disponibles y sale')

    # Parsear los argumentos que el usuario pasó
    args = parser.parse_args()

    # -------------------------------------------------------------------------
    # OPCIÓN: LISTAR PERFILES
    # -------------------------------------------------------------------------
    # Si el usuario pidió --listar-perfiles, mostrar la lista y salir
    if args.listar_perfiles:
        try:
            perfiles = listar_perfiles_firefox(args.usuario)
            print(f"Perfiles de Firefox para usuario '{args.usuario}':\n")
            for nombre_dir, nombre_bonito, es_default in perfiles:
                marcador = " *" if es_default else ""
                # :30 significa "ocupar 30 caracteres, rellenando con espacios"
                print(f"  {nombre_bonito:30} ({nombre_dir}){marcador}")
            print(f"\nTotal: {len(perfiles)} perfil(es)")
            print("* = perfil por defecto")
            print("\nUso: python3 extraer_cookies_firefox.py --perfil NOMBRE")
        except FileNotFoundError as e:
            print(f"Error: {e}")
            sys.exit(1)
        sys.exit(0)

    # -------------------------------------------------------------------------
    # EJECUCIÓN PRINCIPAL
    # -------------------------------------------------------------------------
    try:
        # PASO 1: Detectar plataforma y encontrar el perfil de Firefox
        # ---------------------------------------------------------------------
        plataforma = detectar_plataforma()
        print(f"Plataforma detectada: {plataforma}")
        print(f"Buscando perfil de Firefox para usuario '{args.usuario}'...")
        perfil = encontrar_perfil_firefox(args.usuario, args.perfil)
        nombre_bonito = extraer_nombre_bonito(perfil.name)
        print(f"  Perfil: {nombre_bonito} ({perfil.name})")

        # PASO 2: Copiar la base de datos de cookies
        # ---------------------------------------------------------------------
        # Copiamos porque Firefox puede tener el archivo bloqueado
        print("Copiando base de datos de cookies...")
        temp_db = copiar_cookies_db(perfil)

        try:
            # PASO 3: Extraer las cookies de Google
            # -----------------------------------------------------------------
            print("Extrayendo cookies de Google...")
            cookies = extraer_cookies_google(temp_db)
            print(f"  Cookies encontradas: {len(cookies)}")

            # Mostrar detalle si se pidió verbose o dry-run
            if args.verbose or args.dry_run:
                # Agrupar cookies por dominio para mostrar resumen
                por_dominio = {}
                for c in cookies:
                    d = c['domain']
                    if d not in por_dominio:
                        por_dominio[d] = []
                    por_dominio[d].append(c['name'])

                print("\n  Cookies por dominio:")
                for dominio, nombres in sorted(por_dominio.items()):
                    print(f"    {dominio}: {', '.join(sorted(nombres))}")

            # PASO 4: Verificar que están las cookies mínimas
            # -----------------------------------------------------------------
            ok, faltantes = verificar_cookies_minimas(cookies)
            if not ok:
                print(f"\n⚠ Faltan cookies requeridas: {', '.join(faltantes)}")
                print("  ¿Tienes sesión activa de Google en Firefox?")
                sys.exit(1)

            print("\n✓ Cookies requeridas presentes (SID, HSID, SSID)")

            # PASO 5: Generar el diccionario storage_state
            # -----------------------------------------------------------------
            storage_state = generar_storage_state(cookies, perfil.name, nombre_bonito)

            # Si es dry-run, mostrar qué se escribiría y salir
            if args.dry_run:
                print("\n[dry-run] No se escribe archivo")
                print(f"\nContenido que se escribiría en {args.output}:")
                # [:500] muestra solo los primeros 500 caracteres
                print(json.dumps(storage_state, indent=2)[:500] + "...")
            else:
                # PASO 6: Escribir el archivo JSON
                # -------------------------------------------------------------
                output_path = Path(args.output)
                # Crear directorio padre si no existe
                output_path.parent.mkdir(parents=True, exist_ok=True)

                # Hacer backup del archivo existente (por seguridad)
                if output_path.exists():
                    backup = output_path.with_suffix('.json.bak')
                    shutil.copy2(output_path, backup)
                    print(f"\n  Backup creado: {backup}")

                # Escribir el JSON con indentación para legibilidad
                with open(output_path, 'w') as f:
                    json.dump(storage_state, f, indent=2)

                # Establecer permisos restrictivos (solo el dueño puede leer/escribir)
                # 0o600 = rw------- en notación octal
                output_path.chmod(0o600)

                print(f"\n✓ Archivo generado: {output_path}")
                print(f"  Cookies: {len(cookies)}")

                print("\nPrueba la autenticación con:")
                print("  notebooklm auth check --test")

        finally:
            # LIMPIEZA: Eliminar el archivo temporal
            # -----------------------------------------------------------------
            # El bloque finally se ejecuta siempre, haya error o no
            temp_db.unlink(missing_ok=True)  # unlink = eliminar archivo

    # -------------------------------------------------------------------------
    # MANEJO DE ERRORES
    # -------------------------------------------------------------------------
    except FileNotFoundError as e:
        # Error cuando no se encuentra un archivo o directorio
        print(f"\nError: {e}")
        sys.exit(1)
    except sqlite3.Error as e:
        # Error al leer la base de datos SQLite
        print(f"\nError leyendo base de datos: {e}")
        print("¿Está Firefox ejecutándose? Intenta cerrar Firefox y reintentar.")
        sys.exit(1)
    except Exception as e:
        # Cualquier otro error inesperado
        print(f"\nError inesperado: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
