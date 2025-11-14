"""News monitoring API routes"""

import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.services.news_monitor import get_news_monitor
from backend.services.notification_service import NotificationService

router = APIRouter(prefix="/news", tags=["news"])

# Global service instances
news_monitor = get_news_monitor()
notification_service = NotificationService()


class NewsStatusResponse(BaseModel):
    """News monitoring status response"""
    monitoring: bool
    poll_interval: int
    categories: List[str]
    lang: str
    api_key_configured: bool
    tracked_articles_count: int


# Set up callback to create notifications when new articles arrive
def _on_new_article(notification_data: dict):
    """Callback when new article is detected"""
    try:
        notification_service.create_notification(
            notification_type=notification_data["notification_type"],
            priority=notification_data["priority"],
            title=notification_data["title"],
            message=notification_data["message"],
            source=notification_data["source"],
            symbol=notification_data.get("symbol"),
            confidence_score=notification_data.get("confidence_score"),
            urgency_score=notification_data.get("urgency_score"),
            promise_score=notification_data.get("promise_score"),
            metadata=notification_data.get("metadata", {}),
            expires_at=notification_data.get("expires_at")
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error creating notification from news: {e}", exc_info=True)


# Register callback
news_monitor.on_new_article = _on_new_article


@router.get("/status", response_model=NewsStatusResponse)
async def get_news_status():
    """Get news monitoring status"""
    status = news_monitor.get_status()
    return NewsStatusResponse(**status)


@router.post("/start")
async def start_monitoring():
    """Start news monitoring"""
    try:
        if news_monitor.is_monitoring():
            return {"success": True, "message": "News monitoring already started"}
        
        news_monitor.start()
        return {"success": True, "message": "News monitoring started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_monitoring():
    """Stop news monitoring"""
    try:
        if not news_monitor.is_monitoring():
            return {"success": True, "message": "News monitoring not running"}
        
        news_monitor.stop()
        return {"success": True, "message": "News monitoring stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

