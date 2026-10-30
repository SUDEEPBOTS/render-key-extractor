import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.config import Config
from app.services.db import init_db
from app.api.routes import router

BASE_DIR = Path(__file__).resolve().parent

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database on startup
    init_db()
    yield

app = FastAPI(
    title="Render Key Extractor API",
    description="Automated Render API Key extraction service with Tor IP rotation",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Include API Router
app.include_router(router)

@app.get("/", response_class=FileResponse)
async def serve_home():
    return FileResponse(str(BASE_DIR / "templates" / "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=Config.HOST, port=Config.PORT, reload=True)
