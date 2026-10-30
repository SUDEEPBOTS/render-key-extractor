from datetime import datetime
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel
from typing import Optional
from starlette.concurrency import run_in_threadpool

from app.services.extractor import RenderExtractor
from app.services.tor_manager import TorManager
from app.services.db import get_recent_keys

router = APIRouter()

class ExtractRequest(BaseModel):
    url: str
    name: Optional[str] = None
    use_tor: bool = False
    rotate_before: bool = False

@router.api_route("/ping", methods=["GET", "HEAD"])
async def ping(request: Request):
    """
    Health check endpoint supporting both GET and HEAD requests.
    """
    if request.method == "HEAD":
        return Response(
            status_code=200,
            headers={
                "X-Service-Status": "healthy",
                "X-Timestamp": datetime.utcnow().isoformat() + "Z"
            }
        )
    return {
        "status": "healthy",
        "service": "render-key-extractor",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@router.api_route("/health", methods=["GET", "HEAD"])
async def health(request: Request):
    """
    Comprehensive health status endpoint supporting both GET and HEAD requests.
    """
    if request.method == "HEAD":
        return Response(status_code=200, headers={"X-Service-Status": "healthy"})
    
    tor_status = TorManager.get_status()
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "tor": tor_status
    }

@router.post("/api/extract")
async def extract_api_key(req: ExtractRequest):
    if not req.url or not req.url.strip():
        raise HTTPException(status_code=400, detail="Confirmation URL is required.")

    # Execute Playwright automation in threadpool so it doesn't block async event loop
    result = await run_in_threadpool(
        RenderExtractor.extract_from_link,
        confirm_url=req.url.strip(),
        key_name=req.name.strip() if req.name else None,
        use_tor=req.use_tor,
        rotate_before=req.rotate_before
    )

    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Key extraction failed."))

    return result

@router.get("/api/tor/status")
async def get_tor_status():
    return TorManager.get_status()

@router.post("/api/tor/rotate")
async def rotate_tor():
    result = await run_in_threadpool(TorManager.rotate_tor_identity)
    return result

@router.get("/api/history")
async def get_history(limit: int = 20):
    return get_recent_keys(limit=min(limit, 100))

@router.get("/api/download/env")
async def download_env(key: str, email: Optional[str] = None, owner_id: Optional[str] = None):
    content = f"RENDER_API_KEY={key}\n"
    if owner_id:
        content += f"RENDER_OWNER_ID={owner_id}\n"
    if email:
        content += f"RENDER_EMAIL={email}\n"
    return Response(
        content=content,
        media_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=.env"}
    )

@router.get("/api/render/services")
async def list_render_services(key: str):
    try:
        res = requests.get(
            "https://api.render.com/v1/services",
            headers={"Authorization": f"Bearer {key}"},
            timeout=10
        )
        return res.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
