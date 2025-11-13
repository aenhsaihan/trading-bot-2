"""System control API routes"""

import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.services.notification_source_service import get_notification_source_service

router = APIRouter(prefix="/system", tags=["system"])


class ServiceStatusResponse(BaseModel):
    """Service status response"""
    running: bool
    symbols: list[str]
    timeframe: str
    check_interval: int
    stats: dict


@router.get("/notification-sources/status", response_model=ServiceStatusResponse)
async def get_notification_sources_status():
    """Get notification source service status"""
    try:
        service = get_notification_source_service()
        status = service.get_status()
        return ServiceStatusResponse(**status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notification-sources/start")
async def start_notification_sources():
    """Start the notification source monitoring service"""
    try:
        service = get_notification_source_service()
        if service.is_running():
            return {"message": "Service is already running", "running": True}
        
        service.start()
        return {"message": "Notification source service started", "running": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notification-sources/stop")
async def stop_notification_sources():
    """Stop the notification source monitoring service"""
    try:
        service = get_notification_source_service()
        if not service.is_running():
            return {"message": "Service is not running", "running": False}
        
        service.stop()
        return {"message": "Notification source service stopped", "running": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

