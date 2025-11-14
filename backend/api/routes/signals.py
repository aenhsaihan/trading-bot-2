"""Signals REST API routes"""

import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.services.notification_source_service import get_notification_source_service
from backend.services.signal_generator import SignalGenerator
from backend.services.technical_analysis_service import TechnicalAnalysisService

router = APIRouter(prefix="/signals", tags=["signals"])


class SignalResponse(BaseModel):
    """Signal response model"""
    signal_type: str
    symbol: str
    direction: str
    confidence: float
    indicators: dict
    description: str
    metadata: dict
    timestamp: str


class CombinedSignalResponse(BaseModel):
    """Combined signal response model"""
    symbol: str
    direction: str
    confidence: float
    urgency: float
    promise: float
    source_signals: List[dict]
    description: str
    metadata: dict
    timestamp: str


class SignalListResponse(BaseModel):
    """List of signals response"""
    signals: List[SignalResponse]
    total: int


class ServiceStatusResponse(BaseModel):
    """Service status response"""
    running: bool
    symbols: List[str]
    timeframe: str
    check_interval: int
    stats: dict


@router.get("", response_model=SignalListResponse)
async def get_signals(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    timeframe: str = Query("1h", description="Timeframe for analysis")
):
    """
    Get current technical signals for monitored symbols.
    
    Args:
        symbol: Optional symbol to filter by (if not provided, returns signals for all monitored symbols)
        timeframe: Timeframe for analysis (default: "1h")
    
    Returns:
        List of detected signals
    """
    try:
        technical_service = TechnicalAnalysisService()
        
        # Get symbols to check
        notification_service = get_notification_source_service()
        symbols_to_check = [symbol] if symbol else notification_service.symbols
        
        all_signals = []
        for sym in symbols_to_check:
            try:
                signals = technical_service.detect_signals(sym, timeframe)
                for signal in signals:
                    all_signals.append(SignalResponse(
                        signal_type=signal.signal_type,
                        symbol=signal.symbol,
                        direction=signal.direction,
                        confidence=signal.confidence,
                        indicators=signal.indicators,
                        description=signal.description,
                        metadata=signal.metadata,
                        timestamp=signal.timestamp.isoformat()
                    ))
            except Exception as e:
                # Log error but continue with other symbols
                continue
        
        return SignalListResponse(
            signals=all_signals,
            total=len(all_signals)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get signals: {str(e)}")


@router.post("/generate", status_code=200)
async def generate_signals(
    symbols: Optional[List[str]] = None,
    timeframe: str = "1h"
):
    """
    Manually trigger signal generation and notification creation.
    
    Args:
        symbols: Optional list of symbols to generate signals for (default: all monitored symbols)
        timeframe: Timeframe for analysis (default: "1h")
    
    Returns:
        Information about generated notifications
    """
    try:
        signal_generator = SignalGenerator()
        notification_service = get_notification_source_service()
        
        # Use provided symbols or default to monitored symbols
        symbols_to_check = symbols or notification_service.symbols
        
        # Generate notifications from signals
        notifications = signal_generator.generate_notifications(
            symbols=symbols_to_check,
            timeframe=timeframe
        )
        
        return {
            "generated": True,
            "symbols_checked": symbols_to_check,
            "notifications_created": len(notifications),
            "notifications": notifications
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate signals: {str(e)}")


@router.get("/status", response_model=ServiceStatusResponse)
async def get_service_status():
    """
    Get the status of the notification source monitoring service.
    
    Returns:
        Service status including running state, monitored symbols, and statistics
    """
    try:
        notification_service = get_notification_source_service()
        status = notification_service.get_status()
        
        return ServiceStatusResponse(
            running=status['running'],
            symbols=status['symbols'],
            timeframe=status['timeframe'],
            check_interval=status['check_interval'],
            stats=status['stats']
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get service status: {str(e)}")


@router.post("/start", status_code=200)
async def start_service():
    """Manually start the notification source monitoring service"""
    try:
        notification_service = get_notification_source_service()
        if notification_service.is_running():
            return {
                "status": "already_running",
                "message": "Service is already running"
            }
        
        notification_service.start()
        return {
            "status": "started",
            "message": "Notification source service started successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start service: {str(e)}")


@router.post("/stop", status_code=200)
async def stop_service():
    """Manually stop the notification source monitoring service"""
    try:
        notification_service = get_notification_source_service()
        if not notification_service.is_running():
            return {
                "status": "already_stopped",
                "message": "Service is already stopped"
            }
        
        notification_service.stop()
        return {
            "status": "stopped",
            "message": "Notification source service stopped successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop service: {str(e)}")


