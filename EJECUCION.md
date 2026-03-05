# NotebookLM API - Guía de Ejecución

## Estructura del Proyecto

```
/backend/          # FastAPI - API REST
/frontend/         # React + Vite - Interfaz web
```

---

## Backend (FastAPI)

### Requisitos previos

```bash
cd backend
pip install -r requirements.txt
playwright install chromium
```

### Ejecutar el servidor

```bash
cd backend
source venv/bin/activate
python -m app.main --host 127.0.0.1 --port 8000
```

El servidor estará disponible en: **http://127.0.0.1:8000**

### Documentación de la API

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

### Endpoints disponibles

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/auth/status` | Verificar autenticación |
| GET | `/api/auth/profiles?username=xxx` | Listar perfiles Firefox |
| POST | `/api/auth/extract-cookies` | Extraer cookies de Firefox |
| POST | `/api/notebooks` | Crear cuaderno desde YouTube |
| GET | `/api/notebooks` | Listar cuadernos |
| GET | `/api/notebooks/{id}` | Ver detalles y artefactos |
| POST | `/api/notebooks/{id}/artifacts` | Generar artefactos |

---

## Frontend (React + Vite)

### Requisitos previos

```bash
cd frontend
npm install
```

### Ejecutar el servidor de desarrollo

```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 3000
```

La aplicación estará disponible en: **http://127.0.0.1:3000**

### Construir para producción

```bash
cd frontend
npm run build
```

Los archivos generados estarán en `frontend/dist/`

---

## Ejemplo de uso de la API

### 1. Verificar estado de autenticación

```bash
curl http://127.0.0.1:8000/api/auth/status
```

### 2. Extraer cookies de Firefox

```bash
curl -X POST http://127.0.0.1:8000/api/auth/extract-cookies \
  -H "Content-Type: application/json" \
  -d '{"username": "oscar", "profile": "default-release"}'
```

### 3. Crear cuaderno desde YouTube

```bash
curl -X POST http://127.0.0.1:8000/api/notebooks \
  -H "Content-Type: application/json" \
  -d '{
    "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "language": "es",
    "artifacts": ["report", "mind_map", "data_table"]
  }'
```

### 4. Listar cuadernos

```bash
curl http://127.0.0.1:8000/api/notebooks
```

### 5. Generar artefactos

```bash
curl -X POST http://127.0.0.1:8000/api/notebooks/{notebook_id}/artifacts \
  -H "Content-Type: application/json" \
  -d '{
    "artifact_types": ["audio", "slides"],
    "language": "es"
  }'
```

---

## Ejecutar tests

```bash
cd backend
source venv/bin/activate
pip install -r requirements-test.txt
PYTHONPATH=. pytest tests/ -v
```

---

## Notas

- El backend requiere autenticación de Google para funcionar con NotebookLM
- Usa el script `extraer_cookies_firefox.py` original o el endpoint `/api/auth/extract-cookies` para obtener las credenciales
- Las cookies se guardan en `~/.notebooklm/storage_state.json`
