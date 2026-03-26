from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.api.chat import router as chat_router
from backend.api.services import router as services_router
from backend.config import ROOT_DIR, ensure_runtime_files, settings
from backend.utils.logger import get_logger

ensure_runtime_files()
logger = get_logger()

app = FastAPI(title="nanoclaw", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(services_router)
app.include_router(chat_router)

frontend_dir = ROOT_DIR / "frontend"
if frontend_dir.exists():
    app.mount("/css", StaticFiles(directory=frontend_dir / "css"), name="css")
    app.mount("/js", StaticFiles(directory=frontend_dir / "js"), name="js")


@app.get("/health")
async def health_check():
    return {"status": "ok", "app": "nanoclaw"}


@app.get("/")
async def root_index():
    index_file = Path(frontend_dir / "index.html")
    if not index_file.exists():
        return {"message": "nanoclaw backend is running"}
    return FileResponse(index_file)


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting nanoclaw on %s:%s", settings.api_host, settings.api_port)
    uvicorn.run("backend.main:app", host=settings.api_host, port=settings.api_port, reload=True)
