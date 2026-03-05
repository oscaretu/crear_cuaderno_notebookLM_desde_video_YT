from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime


class VideoMetadata(BaseModel):
    title: str
    channel: str
    upload_date: str
    video_id: str
    description: Optional[str] = None


class CreateNotebookRequest(BaseModel):
    youtube_url: str
    language: str = "es"
    artifacts: Optional[list[str]] = None
    timeout_fuente: float = 60.0
    retardo: float = 3.0


class NotebookResponse(BaseModel):
    id: str
    title: str
    url: str
    created_at: Optional[datetime] = None
    metadata: Optional[VideoMetadata] = None


class ArtifactResponse(BaseModel):
    id: str
    type: str
    title: Optional[str] = None
    status: str
    language: Optional[str] = None
    download_url: Optional[str] = None


class NotebookDetailResponse(BaseModel):
    id: str
    title: str
    url: str
    created_at: Optional[datetime] = None
    artifacts: dict[str, list[ArtifactResponse]]


class GenerateArtifactsRequest(BaseModel):
    artifact_types: list[str]
    language: str = "es"
    retardo: float = 3.0


class GenerateArtifactsResponse(BaseModel):
    notebook_id: str
    generated: int
    total: int
    message: str


class ExtractCookiesRequest(BaseModel):
    username: str = "oscar"
    profile: Optional[str] = None
    output_path: Optional[str] = None
    dry_run: bool = False


class ExtractCookiesResponse(BaseModel):
    success: bool
    message: str
    cookies_count: Optional[int] = None
    profiles: Optional[list[dict]] = None


class ProfileInfo(BaseModel):
    directory_name: str
    display_name: str
    is_default: bool


class AuthStatusResponse(BaseModel):
    authenticated: bool
    message: str
    storage_path: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    version: str
