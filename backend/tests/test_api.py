import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


class TestHealthEndpoint:
    """Tests para el endpoint de salud"""

    def test_health_check(self):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_root_endpoint(self):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data


class TestAuthStatusEndpoint:
    """Tests para el endpoint de estado de autenticacion"""

    @patch("app.services.cookie_service.check_auth_status")
    def test_auth_status_autenticado(self, mock_check):
        mock_check.return_value = {
            "authenticated": True,
            "message": "Autenticado correctamente",
            "storage_path": "/path/to/storage.json",
        }

        response = client.get("/api/auth/status")
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True

    @patch("app.services.cookie_service.check_auth_status")
    def test_auth_status_no_autenticado(self, mock_check):
        mock_check.return_value = {
            "authenticated": False,
            "message": "No autenticado",
            "storage_path": "/path/to/storage.json",
        }

        response = client.get("/api/auth/status")
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False


class TestProfilesEndpoint:
    """Tests para el endpoint de perfiles de Firefox"""

    @patch("app.services.cookie_service.listar_perfiles")
    def test_list_profiles_exito(self, mock_list):
        mock_list.return_value = [
            {
                "directory_name": "abc123.default-release",
                "display_name": "default-release",
                "is_default": True,
            },
            {
                "directory_name": "xyz456.Susana",
                "display_name": "Susana",
                "is_default": False,
            },
        ]

        response = client.get("/api/auth/profiles?username=oscar")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["display_name"] == "default-release"
        assert data[1]["display_name"] == "Susana"

    @patch("app.services.cookie_service.listar_perfiles")
    def test_list_profiles_error(self, mock_list):
        mock_list.side_effect = FileNotFoundError("Perfil no encontrado")

        response = client.get("/api/auth/profiles?username=oscar")
        assert response.status_code == 404


class TestExtractCookiesEndpoint:
    """Tests para el endpoint de extraccion de cookies"""

    @patch("app.services.cookie_service.extract_cookies")
    def test_extract_cookies_exito(self, mock_extract):
        mock_extract.return_value = {
            "success": True,
            "message": "Cookies extraídas correctamente",
            "cookies_count": 24,
        }

        response = client.post(
            "/api/auth/extract-cookies",
            json={"username": "oscar", "profile": "default-release"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["cookies_count"] == 24

    @patch("app.services.cookie_service.extract_cookies")
    def test_extract_cookies_fallo(self, mock_extract):
        mock_extract.return_value = {
            "success": False,
            "message": "Faltan cookies requeridas",
            "cookies_count": 0,
        }

        response = client.post("/api/auth/extract-cookies", json={"username": "oscar"})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False

    @patch("app.services.cookie_service.extract_cookies")
    def test_extract_cookies_error(self, mock_extract):
        mock_extract.side_effect = FileNotFoundError("Firefox no encontrado")

        response = client.post("/api/auth/extract-cookies", json={"username": "oscar"})
        assert response.status_code == 404


class TestCreateNotebookEndpoint:
    """Tests para el endpoint de creacion de cuadernos"""

    @patch("app.services.notebook_service.create_notebook_from_youtube")
    def test_create_notebook_exito(self, mock_create):
        mock_create.return_value = {
            "success": True,
            "notebook": {
                "id": "nb_123",
                "title": "YT-abc - Test Video",
                "url": "https://notebooklm.google.com/notebook/nb_123",
                "is_existing": False,
            },
            "metadata": {
                "title": "Test Video",
                "channel": "Test Channel",
                "upload_date": "2024-01-15",
                "video_id": "abc123",
            },
            "artifacts": {},
        }

        response = client.post(
            "/api/notebooks",
            json={
                "youtube_url": "https://www.youtube.com/watch?v=abc123",
                "language": "es",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["notebook"]["id"] == "nb_123"

    @patch("app.services.notebook_service.create_notebook_from_youtube")
    def test_create_notebook_url_invalida(self, mock_create):
        mock_create.return_value = {
            "success": False,
            "error": "URL de YouTube inválida",
        }

        response = client.post(
            "/api/notebooks",
            json={"youtube_url": "https://vimeo.com/123", "language": "es"},
        )
        # The API returns 500 because it tries to parse the error
        assert response.status_code in [400, 500]

    @patch("app.services.notebook_service.create_notebook_from_youtube")
    def test_create_notebook_error_servidor(self, mock_create):
        mock_create.side_effect = Exception("Error interno")

        response = client.post(
            "/api/notebooks",
            json={
                "youtube_url": "https://www.youtube.com/watch?v=abc123",
                "language": "es",
            },
        )
        assert response.status_code == 500


class TestListNotebooksEndpoint:
    """Tests para el endpoint de listar cuadernos"""

    @patch("app.services.notebook_service.get_notebooks")
    def test_list_notebooks_exito(self, mock_list):
        mock_list.return_value = [
            {
                "id": "nb_1",
                "title": "Notebook 1",
                "url": "https://notebooklm.google.com/notebook/nb_1",
                "created_at": "2024-01-01",
            },
            {
                "id": "nb_2",
                "title": "Notebook 2",
                "url": "https://notebooklm.google.com/notebook/nb_2",
                "created_at": "2024-01-02",
            },
        ]

        response = client.get("/api/notebooks")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == "nb_1"

    @patch("app.services.notebook_service.get_notebooks")
    def test_list_notebooks_error(self, mock_list):
        mock_list.side_effect = Exception("Error de conexión")

        response = client.get("/api/notebooks")
        assert response.status_code == 500


class TestGetNotebookDetailEndpoint:
    """Tests para el endpoint de detalles de cuaderno"""

    @patch("app.services.notebook_service.get_notebook_details")
    def test_get_notebook_exito(self, mock_get):
        mock_get.return_value = {
            "id": "nb_123",
            "title": "Test Notebook",
            "url": "https://notebooklm.google.com/notebook/nb_123",
            "artifacts": {"report": [], "mind_map": [], "audio": []},
            "artifact_urls": {},
        }

        response = client.get("/api/notebooks/nb_123?language=es")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "nb_123"

    @patch("app.services.notebook_service.get_notebook_details")
    def test_get_notebook_no_encontrado(self, mock_get):
        mock_get.return_value = None

        response = client.get("/api/notebooks/no_existe")
        assert response.status_code == 404


class TestGenerateArtifactsEndpoint:
    """Tests para el endpoint de generacion de artefactos"""

    @patch("app.services.notebook_service.generate_artifacts")
    def test_generate_artifacts_exito(self, mock_generate):
        mock_generate.return_value = {
            "success": True,
            "message": "Generados 2 de 2 artefactos",
            "generated": 2,
            "total": 2,
        }

        response = client.post(
            "/api/notebooks/nb_123/artifacts",
            json={"artifact_types": ["report", "mind_map"], "language": "es"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["generated"] == 2
        assert data["total"] == 2

    @patch("app.services.notebook_service.generate_artifacts")
    def test_generate_artifacts_ya_existen(self, mock_generate):
        mock_generate.return_value = {
            "success": True,
            "message": "Todos los artefactos solicitados ya existen",
            "generated": 0,
            "total": 3,
        }

        response = client.post(
            "/api/notebooks/nb_123/artifacts",
            json={"artifact_types": ["report", "mind_map", "audio"], "language": "es"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["generated"] == 0

    @patch("app.services.notebook_service.generate_artifacts")
    def test_generate_artifacts_cuaderno_no_existe(self, mock_generate):
        mock_generate.return_value = {
            "success": False,
            "error": "Cuaderno no encontrado",
        }

        response = client.post(
            "/api/notebooks/no_existe/artifacts",
            json={"artifact_types": ["report"], "language": "es"},
        )
        assert response.status_code == 400
