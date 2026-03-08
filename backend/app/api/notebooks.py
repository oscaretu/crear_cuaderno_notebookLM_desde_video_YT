from fastapi import APIRouter, HTTPException, BackgroundTasks
import asyncio
import logging
from app.models.schemas import (
    CreateNotebookRequest,
    NotebookResponse,
    NotebookDetailResponse,
    GenerateArtifactsRequest,
    GenerateArtifactsResponse,
    ExtractCookiesRequest,
    ExtractCookiesResponse,
    AuthStatusResponse,
    HealthResponse,
    ProfileInfo,
)
from app.services import cookie_service, notebook_service
from app.core.config import settings

logger = logging.getLogger(__name__)


router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="ok", version=settings.version)


# ==================== AUTH ENDPOINTS ====================


@router.get("/auth/profiles", response_model=list[ProfileInfo])
async def list_firefox_profiles(username: str = "oscar"):
    try:
        perfiles = cookie_service.listar_perfiles(username)
        return [ProfileInfo(**p) for p in perfiles]
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auth/extract-cookies", response_model=ExtractCookiesResponse)
async def extract_cookies(request: ExtractCookiesRequest):
    try:
        result = cookie_service.extract_cookies(
            usuario=request.username,
            nombre_perfil=request.profile,
            output_path=request.output_path,
            dry_run=request.dry_run,
        )

        if result["success"]:
            return ExtractCookiesResponse(
                success=True,
                message=result["message"],
                cookies_count=result["cookies_count"],
            )
        else:
            return ExtractCookiesResponse(
                success=False,
                message=result["message"],
                cookies_count=result.get("cookies_count"),
            )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auth/status", response_model=AuthStatusResponse)
async def check_auth_status():
    # First check if cookies exist
    basic_check = cookie_service.check_auth_status()

    if not basic_check["authenticated"]:
        return AuthStatusResponse(
            authenticated=False,
            message=basic_check["message"],
            storage_path=basic_check.get("storage_path"),
        )

    # Then verify with real API call
    try:
        api_check = await cookie_service.verify_auth_with_api()
        return AuthStatusResponse(
            authenticated=api_check["authenticated"],
            message=api_check["message"],
            storage_path=basic_check.get("storage_path"),
        )
    except Exception as e:
        return AuthStatusResponse(
            authenticated=False,
            message=f"Error verificando autenticación: {str(e)[:100]}",
            storage_path=basic_check.get("storage_path"),
        )


# ==================== NOTEBOOK ENDPOINTS ====================


@router.post("/notebooks", response_model=dict)
async def create_notebook(request: CreateNotebookRequest):
    try:
        logger.info(f"Creating notebook from URL: {request.youtube_url}")

        result = await notebook_service.create_notebook_from_youtube(
            youtube_url=request.youtube_url,
            language=request.language,
            artifacts=request.artifacts,
            timeout_fuente=request.timeout_fuente,
            retardo=request.retardo,
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=400, detail=result.get("error", "Error desconocido")
            )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notebooks", response_model=list[dict])
async def list_notebooks():
    try:
        notebooks = await notebook_service.get_notebooks()
        return notebooks
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notebooks/{notebook_id}", response_model=dict)
async def get_notebook(notebook_id: str, language: str = "es"):
    try:
        logger.info(f"Getting notebook details for {notebook_id}")
        notebook = await notebook_service.get_notebook_details(notebook_id, language)
        logger.info(f"Notebook details: {notebook}")

        if not notebook:
            raise HTTPException(status_code=404, detail="Cuaderno no encontrado")

        return notebook
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting notebook {notebook_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/notebooks/{notebook_id}/artifacts", response_model=GenerateArtifactsResponse
)
async def generate_artifacts(
    notebook_id: str,
    request: GenerateArtifactsRequest,
    background_tasks: BackgroundTasks,
):
    try:
        # Start generation in background and return immediately
        def run_generation():
            import asyncio
            from notebooklm import NotebookLMClient

            async def _generate():
                try:
                    await notebook_service.generate_artifacts(
                        notebook_id=notebook_id,
                        artifact_types=request.artifact_types,
                        language=request.language,
                        retardo=request.retardo,
                    )
                except Exception as e:
                    logger.error(f"Background generation error: {e}")

            asyncio.run(_generate())

        # Add task to background
        background_tasks.add_task(run_generation)

        # Return immediately with success message
        artifact_names = {
            "report": "informe",
            "mind_map": "mapa mental",
            "data_table": "tabla de datos",
            "slides": "presentación",
            "infographic": "infografía",
            "quiz": "cuestionario",
            "flashcards": "tarjetas",
            "audio": "audio",
            "video": "video",
        }
        tipos = ", ".join([artifact_names.get(t, t) for t in request.artifact_types])

        return GenerateArtifactsResponse(
            notebook_id=notebook_id,
            generated=len(request.artifact_types),
            total=len(request.artifact_types),
            message=f"Generación iniciada para: {tipos}. La generación se realizará en background.",
        )
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        # Check if it's an auth error
        if (
            "Authentication expired" in error_msg
            or "invalid" in error_msg.lower()
            or "login" in error_msg.lower()
        ):
            raise HTTPException(
                status_code=401,
                detail="Las cookies de autenticación han expirado. Ve a la pestaña Autenticación para extraer nuevas cookies.",
            )
        raise HTTPException(status_code=500, detail=str(e))
