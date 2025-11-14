"""Alerts REST API routes"""

import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.api.models.alerts import (
    AlertCreate,
    AlertUpdate,
    AlertResponse,
    AlertListResponse
)
from backend.services.alert_service import get_alert_service

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("", response_model=AlertResponse, status_code=201)
async def create_alert(alert_data: AlertCreate):
    """Create a new alert"""
    try:
        alert_service = get_alert_service()
        alert = alert_service.create_alert(
            symbol=alert_data.symbol,
            alert_type=alert_data.alert_type,
            price_threshold=alert_data.price_threshold,
            price_condition=alert_data.price_condition,
            indicator_name=alert_data.indicator_name,
            indicator_condition=alert_data.indicator_condition,
            indicator_value=alert_data.indicator_value,
            enabled=alert_data.enabled,
            description=alert_data.description
        )
        return AlertResponse(**alert)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create alert: {str(e)}")


@router.get("", response_model=AlertListResponse)
async def get_alerts(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    enabled_only: bool = Query(False, description="Only return enabled alerts"),
    triggered_only: bool = Query(False, description="Only return triggered alerts")
):
    """Get all alerts with optional filtering"""
    try:
        alert_service = get_alert_service()
        alerts = alert_service.get_all_alerts(
            symbol=symbol,
            enabled_only=enabled_only,
            triggered_only=triggered_only
        )
        
        active_count = sum(1 for a in alerts if a["enabled"])
        triggered_count = sum(1 for a in alerts if a["triggered"])
        
        return AlertListResponse(
            alerts=[AlertResponse(**alert) for alert in alerts],
            total=len(alerts),
            active=active_count,
            triggered=triggered_count
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get alerts: {str(e)}")


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(alert_id: str):
    """Get a specific alert by ID"""
    try:
        alert_service = get_alert_service()
        alert = alert_service.get_alert(alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
        return AlertResponse(**alert)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get alert: {str(e)}")


@router.patch("/{alert_id}", response_model=AlertResponse)
async def update_alert(alert_id: str, alert_update: AlertUpdate):
    """Update an alert"""
    try:
        alert_service = get_alert_service()
        
        # Build update dict from non-None fields
        updates = {}
        if alert_update.enabled is not None:
            updates["enabled"] = alert_update.enabled
        if alert_update.price_threshold is not None:
            updates["price_threshold"] = alert_update.price_threshold
        if alert_update.price_condition is not None:
            updates["price_condition"] = alert_update.price_condition
        if alert_update.indicator_value is not None:
            updates["indicator_value"] = alert_update.indicator_value
        if alert_update.description is not None:
            updates["description"] = alert_update.description
        
        alert = alert_service.update_alert(alert_id, **updates)
        if not alert:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
        return AlertResponse(**alert)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update alert: {str(e)}")


@router.delete("/{alert_id}", status_code=204)
async def delete_alert(alert_id: str):
    """Delete an alert"""
    try:
        alert_service = get_alert_service()
        deleted = alert_service.delete_alert(alert_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete alert: {str(e)}")


@router.post("/evaluate", status_code=200)
async def evaluate_alerts():
    """
    Manually trigger evaluation of all enabled alerts.
    This is useful for testing, but alerts should also be evaluated periodically.
    """
    try:
        alert_service = get_alert_service()
        triggered = alert_service.evaluate_all_alerts()
        return {
            "evaluated": True,
            "triggered_count": len(triggered),
            "triggered_alerts": [AlertResponse(**alert).dict() for alert in triggered]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to evaluate alerts: {str(e)}")



