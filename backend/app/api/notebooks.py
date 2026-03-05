from fastapi import APIRouter, HTTPException
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
    result = cookie_service.check_auth_status()
    return AuthStatusResponse(
        authenticated=result["authenticated"],
        message=result["message"],
        storage_path=result.get("storage_path"),
    )


# ==================== NOTEBOOK ENDPOINTS ====================


@router.post("/notebooks", response_model=dict)
async def create_notebook(request: CreateNotebookRequest):
    try:
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
        notebook = await notebook_service.get_notebook_details(notebook_id, language)

        if not notebook:
            raise HTTPException(status_code=404, detail="Cuaderno no encontrado")

        return notebook
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/notebooks/{notebook_id}/artifacts", response_model=GenerateArtifactsResponse
)
async def generate_artifacts(notebook_id: str, request: GenerateArtifactsRequest):
    try:
        result = await notebook_service.generate_artifacts(
            notebook_id=notebook_id,
            artifact_types=request.artifact_types,
            language=request.language,
            retardo=request.retardo,
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=400, detail=result.get("error", "Error desconocido")
            )

        return GenerateArtifactsResponse(
            notebook_id=notebook_id,
            generated=result["generated"],
            total=result["total"],
            message=result["message"],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
