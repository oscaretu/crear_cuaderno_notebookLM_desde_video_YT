from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from app.api import notebooks
from app.core.config import settings, setup_logging

# Configure logging based on debug setting
logger = setup_logging(settings.debug)

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="API para crear y gestionar cuadernos de NotebookLM desde vídeos de YouTube",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(notebooks.router, prefix="/api", tags=["NotebookLM"])


@app.get("/")
async def root():
    return {"message": "NotebookLM API", "version": settings.version}


if __name__ == "__main__":
    import uvicorn
    import argparse

    parser = argparse.ArgumentParser(description="NotebookLM API Server")
    parser.add_argument(
        "--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Port to bind (default: 8000)"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    # Override debug setting if passed as argument
    if args.debug:
        settings.debug = True
        setup_logging(True)

    uvicorn.run(app, host=args.host, port=args.port)
