"""Simplified X monitoring API routes for Free tier"""

import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.services.x_simple_monitor import get_x_simple_monitor
from backend.services.notification_service import NotificationService

router = APIRouter(prefix="/x/simple", tags=["x-simple"])

# Global service instances
x_monitor = get_x_simple_monitor()
notification_service = NotificationService()


class MonitorStatusResponse(BaseModel):
    """Monitoring status response"""
    monitoring: bool
    accounts_count: int
    accounts: List[str]
    poll_interval: int
    bearer_token_configured: bool


class AddAccountRequest(BaseModel):
    """Request to add account"""
    username_or_id: str


class AccountsResponse(BaseModel):
    """Accounts list response"""
    accounts: List[str]
    count: int


# Set up callback to create notifications when new tweets arrive
def _on_new_tweet(notification_data: dict):
    """Callback when new tweet is detected"""
    try:
        notification_service.create_notification(
            notification_type=notification_data["notification_type"],
            priority=notification_data["priority"],
            title=notification_data["title"],
            message=notification_data["message"],
            source=notification_data["source"],
            symbol=notification_data.get("symbol"),
            metadata=notification_data.get("metadata", {})
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error creating notification from tweet: {e}", exc_info=True)


# Register callback
x_monitor.on_new_tweet = _on_new_tweet


@router.get("/status", response_model=MonitorStatusResponse)
async def get_monitor_status():
    """Get monitoring status"""
    status = x_monitor.get_status()
    return MonitorStatusResponse(**status)


@router.get("/accounts", response_model=AccountsResponse)
async def get_accounts():
    """Get list of monitored accounts"""
    accounts = x_monitor.get_accounts()
    return AccountsResponse(accounts=accounts, count=len(accounts))


@router.post("/accounts/add")
async def add_account(request: AddAccountRequest):
    """Add an account to monitor"""
    try:
        x_monitor.add_account(request.username_or_id)
        return {"success": True, "message": f"Added account: {request.username_or_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/accounts/{username_or_id}")
async def remove_account(username_or_id: str):
    """Remove an account from monitoring"""
    try:
        x_monitor.remove_account(username_or_id)
        return {"success": True, "message": f"Removed account: {username_or_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start")
async def start_monitoring():
    """Start monitoring"""
    try:
        if x_monitor.is_monitoring():
            return {"success": True, "message": "Monitoring already started"}
        
        x_monitor.start()
        return {"success": True, "message": "Monitoring started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_monitoring():
    """Stop monitoring"""
    try:
        if not x_monitor.is_monitoring():
            return {"success": True, "message": "Monitoring not running"}
        
        x_monitor.stop()
        return {"success": True, "message": "Monitoring stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

