import asyncio
import re
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from typing import Optional

import yt_dlp
from notebooklm import NotebookLMClient

from app.core.config import settings


STUDIO_AUDIO = 1
STUDIO_REPORT = 2
STUDIO_VIDEO = 3
STUDIO_QUIZ = 4
STUDIO_MIND_MAP = 5
STUDIO_INFOGRAPHIC = 7
STUDIO_SLIDE_DECK = 8
STUDIO_DATA_TABLE = 9
ARTIFACT_STATUS_COMPLETED = 3

TIPOS_ARTEFACTOS = {
    "report": ("Informe", False),
    "mind_map": ("Mapa Mental", False),
    "data_table": ("Tabla de Datos", False),
    "slides": ("Presentación (Slides)", True),
    "infographic": ("Infografía", True),
    "quiz": ("Cuestionario", True),
    "flashcards": ("Tarjetas Didácticas", True),
    "audio": ("Resumen de Audio", True),
    "video": ("Video", True),
}

ORDEN_ARTEFACTOS = [
    "report",
    "mind_map",
    "data_table",
    "slides",
    "infographic",
    "quiz",
    "flashcards",
    "audio",
    "video",
]

DEFAULT_ARTIFACTS = {"report", "mind_map", "data_table", "quiz", "flashcards"}


def extraer_video_id(url: str) -> Optional[str]:
    parsed = urlparse(url)
    if parsed.hostname in ("www.youtube.com", "youtube.com"):
        if parsed.path == "/watch":
            query = parse_qs(parsed.query)
            return query.get("v", [None])[0]
        elif parsed.path.startswith("/embed/"):
            return parsed.path.split("/")[2]
    elif parsed.hostname == "youtu.be":
        return parsed.path[1:]
    return None


def obtener_metadatos_video(url: str) -> dict:
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "ignoreerrors": False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

        upload_date = info.get("upload_date", "")
        if upload_date:
            fecha = datetime.strptime(upload_date, "%Y%m%d").strftime("%Y-%m-%d")
        else:
            fecha = "fecha-desconocida"

        return {
            "title": info.get("title", "Sin título"),
            "channel": info.get("channel", info.get("uploader", "Canal desconocido")),
            "upload_date": fecha,
            "video_id": info.get("id", ""),
            "description": info.get("description", ""),
        }


def limpiar_texto(texto: str, max_length: int = 50) -> str:
    texto = re.sub(r'[<>:"/\\|?*]', "", texto)
    if len(texto) > max_length:
        texto = texto[:max_length].rsplit(" ", 1)[0] + "..."
    return texto.strip()


def generar_nombre_cuaderno(metadatos: dict) -> str:
    titulo = limpiar_texto(metadatos["title"], 60)
    canal = limpiar_texto(metadatos["channel"], 30)
    fecha = metadatos["upload_date"]
    video_id = metadatos["video_id"]
    return f"YT-{video_id} - {titulo} - {fecha} - {canal}"


def extraer_url_artefacto_raw(artifact_raw: list, artifact_type: int) -> Optional[str]:
    try:
        if artifact_type == STUDIO_AUDIO:
            if len(artifact_raw) <= 6:
                return None
            metadata = artifact_raw[6]
            if not isinstance(metadata, list) or len(metadata) <= 5:
                return None
            media_list = metadata[5]
            if not isinstance(media_list, list) or len(media_list) == 0:
                return None
            for item in media_list:
                if isinstance(item, list) and len(item) > 2 and item[2] == "audio/mp4":
                    return item[0]
            if isinstance(media_list[0], list) and len(media_list[0]) > 0:
                return media_list[0][0]

        elif artifact_type == STUDIO_VIDEO:
            if len(artifact_raw) <= 8:
                return None
            metadata = artifact_raw[8]
            if not isinstance(metadata, list):
                return None
            media_list = None
            for item in metadata:
                if (
                    isinstance(item, list)
                    and len(item) > 0
                    and isinstance(item[0], list)
                    and len(item[0]) > 0
                    and isinstance(item[0][0], str)
                    and item[0][0].startswith("http")
                ):
                    media_list = item
                    break
            if not media_list:
                return None
            for item in media_list:
                if isinstance(item, list) and len(item) > 2 and item[2] == "video/mp4":
                    return item[0]
            if isinstance(media_list[0], list) and len(media_list[0]) > 0:
                return media_list[0][0]

        elif artifact_type == STUDIO_INFOGRAPHIC:
            for item in reversed(artifact_raw):
                if not isinstance(item, list) or len(item) == 0:
                    continue
                if not isinstance(item[0], list):
                    continue
                if len(item) <= 2 or not isinstance(item[2], list) or len(item[2]) == 0:
                    continue
                content_list = item[2]
                if not isinstance(content_list[0], list) or len(content_list[0]) <= 1:
                    continue
                img_data = content_list[0][1]
                if (
                    isinstance(img_data, list)
                    and len(img_data) > 0
                    and isinstance(img_data[0], str)
                    and img_data[0].startswith("http")
                ):
                    return img_data[0]

        elif artifact_type == STUDIO_SLIDE_DECK:
            if len(artifact_raw) <= 16:
                return None
            metadata = artifact_raw[16]
            if not isinstance(metadata, list) or len(metadata) <= 3:
                return None
            pdf_url = metadata[3]
            if isinstance(pdf_url, str) and pdf_url.startswith("http"):
                return pdf_url

    except (IndexError, TypeError):
        pass

    return None


async def obtener_urls_artefactos(client, notebook_id: str) -> dict:
    urls = {}
    try:
        artifacts_raw = await client.artifacts._list_raw(notebook_id)

        for art in artifacts_raw:
            if not isinstance(art, list) or len(art) < 5:
                continue

            artifact_id = art[0]
            artifact_type = art[2]
            artifact_status = art[4]

            if artifact_status != ARTIFACT_STATUS_COMPLETED:
                continue

            url = extraer_url_artefacto_raw(art, artifact_type)
            if url:
                urls[artifact_id] = (url, artifact_type)

    except Exception:
        pass

    return urls


async def verificar_artefactos_existentes(
    client, notebook_id: str, idioma: str = "es"
) -> tuple[dict, dict]:
    existentes = {tipo: [] for tipo in TIPOS_ARTEFACTOS.keys()}
    urls = {}

    try:
        # Reports
        try:
            reports = await client.artifacts.list_reports(notebook_id)
            if reports:
                existentes["report"] = list(reports)
        except Exception:
            pass

        # Audios
        try:
            audios = await client.artifacts.list_audio(notebook_id)
            if audios:
                existentes["audio"] = list(audios)
        except Exception:
            pass

        # Slides
        try:
            slides = await client.artifacts.list_slide_decks(notebook_id)
            if slides:
                existentes["slides"] = list(slides)
        except Exception:
            pass

        # Infographics
        try:
            infographics = await client.artifacts.list_infographics(notebook_id)
            if infographics:
                existentes["infographic"] = list(infographics)
        except Exception:
            pass

        # Videos
        try:
            videos = await client.artifacts.list_video(notebook_id)
            if videos:
                existentes["video"] = list(videos)
        except Exception:
            pass

        # Mind maps
        try:
            mind_maps = await client.artifacts.list(notebook_id, 5)
            if mind_maps:
                existentes["mind_map"] = list(mind_maps)
        except Exception:
            pass

        # Data tables
        try:
            data_tables = await client.artifacts.list_data_tables(notebook_id)
            if data_tables:
                existentes["data_table"] = list(data_tables)
        except Exception:
            pass

        # Quizzes
        try:
            quizzes = await client.artifacts.list_quizzes(notebook_id)
            if quizzes:
                existentes["quiz"] = list(quizzes)
        except Exception:
            pass

        # Flashcards
        try:
            flashcards = await client.artifacts.list_flashcards(notebook_id)
            if flashcards:
                existentes["flashcards"] = list(flashcards)
        except Exception:
            pass

    except Exception:
        pass

    # URLs de descarga
    try:
        urls = await obtener_urls_artefactos(client, notebook_id)
    except Exception:
        pass

    return existentes, urls


async def generar_artefactos(
    client, notebook_id: str, faltantes: list, idioma: str = "es", retardo: float = 3.0
) -> int:
    if not faltantes:
        return 0

    CUOTA_COMPARTIDA = {"slides": "premium", "infographic": "premium"}
    ARTEFACTOS_SINCRONOS = {"mind_map"}

    CONFIG_ARTEFACTOS = {
        "report": (client.artifacts.generate_report, {"language": idioma}),
        "mind_map": (client.artifacts.generate_mind_map, {}),
        "data_table": (client.artifacts.generate_data_table, {"language": idioma}),
        "slides": (client.artifacts.generate_slide_deck, {"language": idioma}),
        "infographic": (client.artifacts.generate_infographic, {"language": idioma}),
        "quiz": (client.artifacts.generate_quiz, {}),
        "flashcards": (client.artifacts.generate_flashcards, {}),
        "audio": (client.artifacts.generate_audio, {"language": idioma}),
        "video": (client.artifacts.generate_video, {"language": idioma}),
    }

    exitosos = 0
    cuotas_agotadas = set()

    for i, tipo in enumerate(faltantes):
        generar_func, kwargs = CONFIG_ARTEFACTOS[tipo]
        grupo_cuota = CUOTA_COMPARTIDA.get(tipo)

        if grupo_cuota and grupo_cuota in cuotas_agotadas:
            continue

        if i > 0:
            await asyncio.sleep(retardo)

        try:
            resultado = await generar_func(notebook_id, **kwargs)

            if tipo in ARTEFACTOS_SINCRONOS:
                if resultado and resultado.get("mind_map"):
                    exitosos += 1
                continue

            if resultado and getattr(resultado, "status", None) == "failed":
                if hasattr(resultado, "is_rate_limited") and resultado.is_rate_limited:
                    cuotas_agotadas.add(grupo_cuota)
                continue

            if resultado and getattr(resultado, "task_id", None):
                await client.artifacts.wait_for_completion(
                    notebook_id, resultado.task_id
                )

            exitosos += 1

        except Exception:
            pass

    return exitosos


async def buscar_cuaderno_existente(client: NotebookLMClient, video_id: str):
    notebooks = await client.notebooks.list()
    prefijo = f"YT-{video_id}"
    for nb in notebooks:
        if nb.title.startswith(prefijo):
            return nb
    return None


async def create_notebook_from_youtube(
    youtube_url: str,
    language: str = "es",
    artifacts: Optional[list] = None,
    timeout_fuente: float = 60.0,
    retardo: float = 3.0,
) -> dict:
    video_id = extraer_video_id(youtube_url)
    if not video_id:
        return {"success": False, "error": "URL de YouTube inválida"}

    metadatos = obtener_metadatos_video(youtube_url)
    nombre_cuaderno = generar_nombre_cuaderno(metadatos)

    if artifacts is None:
        artifacts = list(DEFAULT_ARTIFACTS)

    async with await NotebookLMClient.from_storage() as client:
        notebook = await buscar_cuaderno_existente(client, video_id)

        if notebook:
            existentes, urls = await verificar_artefactos_existentes(
                client, notebook.id, language
            )

            faltantes = [
                t
                for t in artifacts
                if t in TIPOS_ARTEFACTOS and len(existentes.get(t, [])) == 0
            ]

            if faltantes:
                await generar_artefactos(
                    client, notebook.id, faltantes, language, retardo
                )

            existentes_final, urls_final = await verificar_artefactos_existentes(
                client, notebook.id, language
            )

            return {
                "success": True,
                "notebook": {
                    "id": notebook.id,
                    "title": notebook.title,
                    "url": f"https://notebooklm.google.com/notebook/{notebook.id}",
                    "is_existing": True,
                },
                "metadata": metadatos,
                "artifacts": existentes_final,
            }

        notebook = await client.notebooks.create(nombre_cuaderno)

        try:
            await client.sources.add_url(
                notebook.id, youtube_url, wait=True, wait_timeout=timeout_fuente
            )
        except Exception:
            pass

        tipos_a_generar = [t for t in ORDEN_ARTEFACTOS if t in artifacts]
        await generar_artefactos(
            client, notebook.id, tipos_a_generar, language, retardo
        )

        existentes, urls = await verificar_artefactos_existentes(
            client, notebook.id, language
        )

        return {
            "success": True,
            "notebook": {
                "id": notebook.id,
                "title": notebook.title,
                "url": f"https://notebooklm.google.com/notebook/{notebook.id}",
                "is_existing": False,
            },
            "metadata": metadatos,
            "artifacts": existentes,
        }


async def get_notebooks() -> list[dict]:
    async with await NotebookLMClient.from_storage() as client:
        notebooks = await client.notebooks.list()
        return [
            {
                "id": nb.id,
                "title": nb.title,
                "url": f"https://notebooklm.google.com/notebook/{nb.id}",
                "created_at": getattr(nb, "created_at", None)
                or getattr(nb, "create_time", None),
            }
            for nb in notebooks
        ]


async def get_notebook_details(
    notebook_id: str, language: str = "es"
) -> Optional[dict]:
    async with await NotebookLMClient.from_storage() as client:
        notebooks = await client.notebooks.list()

        notebook = None
        for nb in notebooks:
            if nb.id == notebook_id:
                notebook = nb
                break

        if not notebook:
            return None

        existentes, urls = await verificar_artefactos_existentes(
            client, notebook_id, language
        )

        return {
            "id": notebook.id,
            "title": notebook.title,
            "url": f"https://notebooklm.google.com/notebook/{notebook.id}",
            "created_at": getattr(notebook, "created_at", None)
            or getattr(notebook, "create_time", None),
            "artifacts": existentes,
            "artifact_urls": urls,
        }


async def generate_artifacts(
    notebook_id: str, artifact_types: list, language: str = "es", retardo: float = 3.0
) -> dict:
    async with await NotebookLMClient.from_storage() as client:
        notebooks = await client.notebooks.list()

        notebook = None
        for nb in notebooks:
            if nb.id == notebook_id:
                notebook = nb
                break

        if not notebook:
            return {"success": False, "error": "Cuaderno no encontrado"}

        existentes, _ = await verificar_artefactos_existentes(
            client, notebook_id, language
        )

        faltantes = [
            t
            for t in artifact_types
            if t in TIPOS_ARTEFACTOS and len(existentes.get(t, [])) == 0
        ]

        if not faltantes:
            return {
                "success": True,
                "message": "Todos los artefactos solicitados ya existen",
                "generated": 0,
                "total": len(artifact_types),
            }

        exitosos = await generar_artefactos(
            client, notebook_id, faltantes, language, retardo
        )

        return {
            "success": True,
            "message": f"Generados {exitosos} de {len(faltantes)} artefactos",
            "generated": exitosos,
            "total": len(faltantes),
        }
