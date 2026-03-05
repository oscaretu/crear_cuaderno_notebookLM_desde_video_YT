import os
import json
import shutil
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.core.config import settings


FIREFOX_PROFILES_WSL = "/mnt/c/Users/{user}/AppData/Roaming/Mozilla/Firefox/Profiles"
FIREFOX_PROFILES_WINDOWS = r"C:\Users\{user}\AppData\Roaming\Mozilla\Firefox\Profiles"
FIREFOX_PROFILES_LINUX = "/home/{user}/.mozilla/firefox"
FIREFOX_PROFILES_MACOS = "/Users/{user}/Library/Application Support/Firefox/Profiles"

ALLOWED_DOMAINS = {
    ".google.com",
    "notebooklm.google.com",
    ".googleusercontent.com",
}

GOOGLE_REGIONAL_SUFFIXES = {
    ".google.es",
    ".google.co.uk",
    ".google.de",
    ".google.fr",
    ".google.it",
    ".google.com.mx",
    ".google.com.ar",
    ".google.com.br",
}

AUTH_COOKIE_NAMES = {
    "SID",
    "HSID",
    "SSID",
    "APISID",
    "SAPISID",
    "__Secure-1PSID",
    "__Secure-3PSID",
    "__Secure-1PAPISID",
    "__Secure-3PAPISID",
    "__Secure-1PSIDCC",
    "__Secure-3PSIDCC",
    "__Secure-1PSIDTS",
    "__Secure-3PSIDTS",
    "__Secure-1PSIDRTS",
    "__Secure-3PSIDRTS",
    "SIDCC",
    "OSID",
    "__Secure-OSID",
    "LSID",
    "__Host-1PLSID",
    "__Host-3PLSID",
    "__Host-GAPS",
    "ACCOUNT_CHOOSER",
    "NID",
    "AEC",
    "SOCS",
}

REQUIRED_COOKIES = {"SID"}


def detectar_plataforma() -> str:
    import platform

    sistema = platform.system().lower()
    if sistema == "linux":
        if Path("/mnt/c/Windows").exists():
            return "wsl"
        return "linux"
    elif sistema == "windows":
        return "windows"
    elif sistema == "darwin":
        return "macos"
    return "linux"


def obtener_ruta_perfiles(usuario: str, plataforma: str = None) -> Path:
    if plataforma is None:
        plataforma = detectar_plataforma()

    if plataforma == "wsl":
        return Path(FIREFOX_PROFILES_WSL.format(user=usuario))
    elif plataforma == "windows":
        return Path(FIREFOX_PROFILES_WINDOWS.format(user=usuario))
    elif plataforma == "macos":
        return Path(FIREFOX_PROFILES_MACOS.format(user=usuario))
    else:
        return Path(FIREFOX_PROFILES_LINUX.format(user=usuario))


def extraer_nombre_bonito(nombre_dir: str) -> str:
    if "." in nombre_dir:
        return nombre_dir.split(".", 1)[1]
    return nombre_dir


def listar_perfiles(usuario: str) -> list[dict]:
    base = obtener_ruta_perfiles(usuario)
    if not base.exists():
        raise FileNotFoundError(
            f"No se encuentra directorio de perfiles Firefox: {base}"
        )

    perfiles = []
    for p in sorted(base.iterdir()):
        if p.is_dir():
            nombre_bonito = extraer_nombre_bonito(p.name)
            es_default = "default-release" in p.name or p.name.endswith(".default")
            perfiles.append(
                {
                    "directory_name": p.name,
                    "display_name": nombre_bonito,
                    "is_default": es_default,
                }
            )
    return perfiles


def encontrar_perfil(usuario: str, nombre_perfil: str = None) -> Path:
    base = obtener_ruta_perfiles(usuario)
    if not base.exists():
        raise FileNotFoundError(
            f"No se encuentra directorio de perfiles Firefox: {base}"
        )

    perfiles = list(base.iterdir())

    if nombre_perfil:
        for p in perfiles:
            if nombre_perfil in p.name:
                return p
        raise FileNotFoundError(f"Perfil '{nombre_perfil}' no encontrado")

    for p in perfiles:
        if "default-release" in p.name:
            return p
    for p in perfiles:
        if "default" in p.name:
            return p
    raise FileNotFoundError(f"No se encontró perfil por defecto")


def copiar_cookies_db(perfil: Path) -> Path:
    cookies_db = perfil / "cookies.sqlite"
    if not cookies_db.exists():
        raise FileNotFoundError(f"No se encuentra {cookies_db}")
    temp_db = Path(tempfile.mktemp(suffix=".sqlite"))
    shutil.copy2(cookies_db, temp_db)
    return temp_db


def es_dominio_permitido(host: str) -> bool:
    dominios_necesarios = {
        ".google.com",
        "notebooklm.google.com",
        "accounts.google.com",
    }
    if host in dominios_necesarios:
        return True
    # Handle subdomains like www.google.com
    if host.endswith(".google.com") and host != ".google.com":
        return True
    for regional in GOOGLE_REGIONAL_SUFFIXES:
        if host == regional.lstrip(".") or host == regional:
            return True
        if host.endswith(regional.lstrip(".")):
            return True
    return False


def es_cookie_auth(name: str) -> bool:
    return name in AUTH_COOKIE_NAMES


def extraer_cookies_google(db_path: Path) -> list[dict]:
    cookies_dict = {}
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = """
        SELECT name, value, host, path, expiry, isSecure, isHttpOnly, sameSite
        FROM moz_cookies
        WHERE host LIKE '%google%'
        ORDER BY expiry DESC
    """

    cursor.execute(query)

    for row in cursor.fetchall():
        host = row["host"]
        name = row["name"]

        if not es_dominio_permitido(host):
            continue
        if not es_cookie_auth(name):
            continue

        key = (name, host)
        if key in cookies_dict:
            continue

        same_site_map = {0: "None", 1: "Lax", 2: "Strict"}
        same_site = same_site_map.get(row["sameSite"], "Lax")

        cookie = {
            "name": name,
            "value": row["value"],
            "domain": host,
            "path": row["path"],
            "expires": row["expiry"],
            "httpOnly": bool(row["isHttpOnly"]),
            "secure": bool(row["isSecure"]),
            "sameSite": same_site,
        }
        cookies_dict[key] = cookie

    conn.close()
    cookies = sorted(cookies_dict.values(), key=lambda c: (c["domain"], c["name"]))
    return cookies


def verificar_cookies_minimas(cookies: list[dict]) -> tuple[bool, list[str]]:
    nombres = {c["name"] for c in cookies}
    faltantes = [r for r in REQUIRED_COOKIES if r not in nombres]
    return len(faltantes) == 0, list(faltantes)


def generar_storage_state(
    cookies: list[dict], perfil_dir: str, perfil_nombre: str
) -> dict:
    return {
        "_generated": {
            "tool": "NotebookLM API",
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat(),
            "source": f"Firefox profile: {perfil_nombre} ({perfil_dir})",
            "cookies_count": len(cookies),
        },
        "cookies": cookies,
        "origins": [],
    }


def extract_cookies(
    usuario: str,
    nombre_perfil: str = None,
    output_path: str = None,
    dry_run: bool = False,
) -> dict:
    plataforma = detectar_plataforma()
    perfil = encontrar_perfil(usuario, nombre_perfil)
    nombre_bonito = extraer_nombre_bonito(perfil.name)

    temp_db = copiar_cookies_db(perfil)

    try:
        cookies = extraer_cookies_google(temp_db)

        ok, faltantes = verificar_cookies_minimas(cookies)
        if not ok:
            return {
                "success": False,
                "message": f"Faltan cookies requeridas: {', '.join(faltantes)}",
                "cookies_count": len(cookies),
            }

        if dry_run:
            return {
                "success": True,
                "message": f"Dry run: {len(cookies)} cookies encontradas",
                "cookies_count": len(cookies),
            }

        storage_state = generar_storage_state(cookies, perfil.name, nombre_bonito)

        if output_path is None:
            output_path = str(settings.storage_state_path)

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        if output.exists():
            backup = output.with_suffix(".json.bak")
            shutil.copy2(output, backup)

        with open(output, "w") as f:
            json.dump(storage_state, f, indent=2)

        output.chmod(0o600)

        return {
            "success": True,
            "message": f"Cookies extraídas correctamente: {len(cookies)} cookies",
            "cookies_count": len(cookies),
        }

    finally:
        temp_db.unlink(missing_ok=True)


def check_auth_status() -> dict:
    storage_path = settings.storage_state_path

    if not storage_path.exists():
        return {
            "authenticated": False,
            "message": "No autenticado. Extrae cookies primero.",
            "storage_path": str(storage_path),
        }

    try:
        with open(storage_path, "r") as f:
            data = json.load(f)

        cookies = data.get("cookies", [])
        has_sid = any(c.get("name") == "SID" for c in cookies)

        if has_sid:
            return {
                "authenticated": True,
                "message": "Autenticado correctamente",
                "storage_path": str(storage_path),
            }
        else:
            return {
                "authenticated": False,
                "message": "Cookies inválidas",
                "storage_path": str(storage_path),
            }
    except Exception as e:
        return {
            "authenticated": False,
            "message": f"Error al verificar: {str(e)}",
            "storage_path": str(storage_path),
        }
