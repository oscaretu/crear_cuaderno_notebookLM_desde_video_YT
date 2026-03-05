import pytest
import tempfile
import sqlite3
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.services import cookie_service


class TestExtraerNombreBonito:
    """Tests para la funcion extraer_nombre_bonito"""

    def test_default_release(self):
        assert (
            cookie_service.extraer_nombre_bonito("vonalg81.default-release")
            == "default-release"
        )

    def test_named_profile(self):
        assert cookie_service.extraer_nombre_bonito("kyetl4dz.Susana") == "Susana"

    def test_simple_default(self):
        assert cookie_service.extraer_nombre_bonito("9zudahgi.default") == "default"

    def test_no_dot(self):
        assert cookie_service.extraer_nombre_bonito("perfil") == "perfil"


class TestEsDominioPermitido:
    """Tests para la funcion es_dominio_permitido"""

    def test_google_com(self):
        assert cookie_service.es_dominio_permitido(".google.com") is True

    def test_google_www(self):
        assert cookie_service.es_dominio_permitido("www.google.com") is True

    def test_notebooklm_google(self):
        assert cookie_service.es_dominio_permitido("notebooklm.google.com") is True

    def test_google_es(self):
        assert cookie_service.es_dominio_permitido("google.es") is True

    def test_google_co_uk(self):
        assert cookie_service.es_dominio_permitido("google.co.uk") is True

    def test_google_com_br(self):
        assert cookie_service.es_dominio_permitido("google.com.br") is True

    def test_facebook_com(self):
        assert cookie_service.es_dominio_permitido("facebook.com") is False

    def test_twitter_com(self):
        assert cookie_service.es_dominio_permitido("twitter.com") is False


class TestEsCookieAuth:
    """Tests para la funcion es_cookie_auth"""

    def test_sid(self):
        assert cookie_service.es_cookie_auth("SID") is True

    def test_hsid(self):
        assert cookie_service.es_cookie_auth("HSID") is True

    def test_secure_1psid(self):
        assert cookie_service.es_cookie_auth("__Secure-1PSID") is True

    def test_secure_3psid(self):
        assert cookie_service.es_cookie_auth("__Secure-3PSID") is True

    def test_sapisid(self):
        assert cookie_service.es_cookie_auth("SAPISID") is True

    def test_nid(self):
        assert cookie_service.es_cookie_auth("NID") is True

    def test_aec(self):
        assert cookie_service.es_cookie_auth("AEC") is True

    def test_random_cookie(self):
        assert cookie_service.es_cookie_auth("random_cookie") is False

    def test_session(self):
        assert cookie_service.es_cookie_auth("session_id") is False


class TestVerificarCookiesMinimas:
    """Tests para la funcion verificar_cookies_minimas"""

    def test_con_sid(self):
        cookies = [{"name": "SID", "value": "test"}]
        ok, faltantes = cookie_service.verificar_cookies_minimas(cookies)
        assert ok is True
        assert faltantes == []

    def test_sin_sid(self):
        cookies = [{"name": "HSID", "value": "test"}]
        ok, faltantes = cookie_service.verificar_cookies_minimas(cookies)
        assert ok is False
        assert faltantes == ["SID"]

    def test_varias_cookies_con_sid(self):
        cookies = [
            {"name": "SID", "value": "test"},
            {"name": "HSID", "value": "test"},
            {"name": "SSID", "value": "test"},
        ]
        ok, faltantes = cookie_service.verificar_cookies_minimas(cookies)
        assert ok is True
        assert faltantes == []

    def test_lista_vacia(self):
        cookies = []
        ok, faltantes = cookie_service.verificar_cookies_minimas(cookies)
        assert ok is False
        assert faltantes == ["SID"]


class TestGenerarStorageState:
    """Tests para la funcion generar_storage_state"""

    def test_estructura_basica(self):
        cookies = [{"name": "SID", "value": "test", "domain": ".google.com"}]
        result = cookie_service.generar_storage_state(cookies, "perfil.test", "test")

        assert "_generated" in result
        assert "cookies" in result
        assert "origins" in result
        assert result["origins"] == []

    def test_metadata_generated(self):
        cookies = [{"name": "SID", "value": "test"}]
        result = cookie_service.generar_storage_state(cookies, "perfil.test", "test")

        assert result["_generated"]["tool"] == "NotebookLM API"
        assert result["_generated"]["version"] == "1.0.0"
        assert result["_generated"]["cookies_count"] == 1
        assert "Firefox profile: test (perfil.test)" in result["_generated"]["source"]

    def test_cookies_incluidos(self):
        cookies = [
            {"name": "SID", "value": "abc123"},
            {"name": "HSID", "value": "def456"},
        ]
        result = cookie_service.generar_storage_state(cookies, "perfil.test", "test")

        assert len(result["cookies"]) == 2
        assert result["cookies"][0]["name"] == "SID"


class TestDetectarPlataforma:
    """Tests para la funcion detectar_plataforma"""

    @patch("platform.system")
    def test_linux_sin_wsl(self, mock_system):
        with patch("pathlib.Path.exists", return_value=False):
            mock_system.return_value = "linux"
            result = cookie_service.detectar_plataforma()
            assert result == "linux"

    @patch("platform.system")
    def test_wsl(self, mock_system):
        with patch("pathlib.Path.exists", return_value=True):
            mock_system.return_value = "linux"
            result = cookie_service.detectar_plataforma()
            assert result == "wsl"

    @patch("platform.system")
    def test_windows(self, mock_system):
        mock_system.return_value = "windows"
        result = cookie_service.detectar_plataforma()
        assert result == "windows"

    @patch("platform.system")
    def test_macos(self, mock_system):
        mock_system.return_value = "darwin"
        result = cookie_service.detectar_plataforma()
        assert result == "macos"


class TestObtenerRutaPerfiles:
    """Tests para la funcion obtener_ruta_perfiles"""

    def test_linux(self):
        result = cookie_service.obtener_ruta_perfiles("oscar", "linux")
        assert str(result) == "/home/oscar/.mozilla/firefox"

    def test_windows(self):
        result = cookie_service.obtener_ruta_perfiles("oscar", "windows")
        assert "Users\\oscar" in str(result)
        assert "AppData" in str(result)

    def test_macos(self):
        result = cookie_service.obtener_ruta_perfiles("oscar", "macos")
        assert (
            str(result) == "/Users/oscar/Library/Application Support/Firefox/Profiles"
        )


class TestCheckAuthStatus:
    """Tests para la funcion check_auth_status"""

    @patch("app.services.cookie_service.settings")
    def test_no_authenticado_sin_archivo(self, mock_settings):
        mock_settings.storage_state_path = Path("/no/existe.json")
        result = cookie_service.check_auth_status()

        assert result["authenticated"] is False
        assert "No autenticado" in result["message"]

    @patch("app.services.cookie_service.settings")
    def test_autenticado_con_sid(self, mock_settings):
        mock_settings.storage_state_path = Path("/tmp/test.json")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(
                {
                    "cookies": [
                        {"name": "SID", "value": "test"},
                        {"name": "HSID", "value": "test"},
                    ],
                    "origins": [],
                },
                f,
            )
            temp_path = f.name

        try:
            with patch("app.services.cookie_service.settings") as mock_settings:
                mock_settings.storage_state_path = Path(temp_path)
                result = cookie_service.check_auth_status()

                assert result["authenticated"] is True
                assert "Autenticado" in result["message"]
        finally:
            Path(temp_path).unlink(missing_ok=True)

    @patch("app.services.cookie_service.settings")
    def test_no_autenticado_sin_sid(self, mock_settings):
        mock_settings.storage_state_path = Path("/tmp/test.json")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(
                {"cookies": [{"name": "HSID", "value": "test"}], "origins": []}, f
            )
            temp_path = f.name

        try:
            with patch("app.services.cookie_service.settings") as mock_settings:
                mock_settings.storage_state_path = Path(temp_path)
                result = cookie_service.check_auth_status()

                assert result["authenticated"] is False
                assert "inválidas" in result["message"]
        finally:
            Path(temp_path).unlink(missing_ok=True)
