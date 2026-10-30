from datetime import datetime
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel
from typing import Optional
from starlette.concurrency import run_in_threadpool

from app.services.extractor import RenderExtractor
from app.services.tor_manager import TorManager
from app.services.mail_service import MailService
from app.services.yukisbox_service import YukisboxService
from app.services.db import get_recent_keys

router = APIRouter()

class ExtractRequest(BaseModel):
    url: str
    name: Optional[str] = None
    use_tor: bool = False
    rotate_before: bool = False
    proxy_mode: Optional[str] = "residential"

class MailGenerateRequest(BaseModel):
    provider: str = "yuki"
    domain: Optional[str] = None

class YukisboxUploadRequest(BaseModel):
    keys: Optional[list] = None
    title: Optional[str] = None
    upload_all: bool = False

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
        rotate_before=req.rotate_before,
        proxy_mode=req.proxy_mode or ("tor" if req.use_tor else "residential")
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

@router.get("/api/mail/domains")
async def get_mail_domains(provider: str = "yuki"):
    domains = await run_in_threadpool(MailService.get_domains, provider=provider)
    return {"provider": provider, "domains": domains}

@router.post("/api/mail/generate")
async def generate_mail(req: Optional[MailGenerateRequest] = None):
    provider = req.provider if req else "yuki"
    domain = req.domain if req else None
    result = await run_in_threadpool(MailService.generate_credentials, domain=domain, provider=provider)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to generate mail credentials"))
    return result

@router.get("/api/mail/check")
async def check_mail(token: str, provider: str = "yuki"):
    result = await run_in_threadpool(MailService.check_render_email, token=token, provider=provider)
    return result

@router.post("/api/yukisbox/upload")
async def upload_to_yukisbox(req: YukisboxUploadRequest):
    keys_to_upload = []
    if req.keys and len(req.keys) > 0:
        keys_to_upload = req.keys
    else:
        # Fetch successful keys from database
        recent = get_recent_keys(limit=100)
        keys_to_upload = [r for r in recent if r.get("status") == "SUCCESS" and r.get("api_key")]

    if not keys_to_upload:
        raise HTTPException(status_code=400, detail="No valid Render API keys available to upload.")

    result = await run_in_threadpool(YukisboxService.upload_keys, keys_data=keys_to_upload, title=req.title)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to upload to yukisbox.com"))
    return result
