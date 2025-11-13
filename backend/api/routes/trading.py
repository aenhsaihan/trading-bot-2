"""Trading REST API routes"""

import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.api.models.trading import (
    PositionResponse,
    PositionCreate,
    PositionUpdate,
    PositionListResponse,
    BalanceResponse,
    StopLossUpdate,
    TrailingStopUpdate
)
from backend.services.trading_service import TradingService
from src.utils.logger import setup_logger

router = APIRouter(prefix="/trading", tags=["trading"])

# Global service instance (in production, use dependency injection)
trading_service = TradingService()

# Setup logger for this module
logger = setup_logger(f"{__name__}.TradingRoutes")


@router.get("/balance", response_model=BalanceResponse)
async def get_balance():
    """Get account balance and portfolio value"""
    try:
        balance_data = trading_service.get_balance()
        return BalanceResponse(**balance_data)
    except Exception as e:
        logger.error(f"Failed to get balance: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail="Failed to retrieve account balance. Please try again later."
        )


@router.get("/positions", response_model=PositionListResponse)
async def get_positions():
    """Get all open positions"""
    try:
        positions = trading_service.get_positions()
        total_pnl = sum(p['pnl'] for p in positions)
        total_pnl_percent = sum(p['pnl_percent'] for p in positions) / len(positions) if positions else 0
        
        return PositionListResponse(
            positions=[PositionResponse(**p) for p in positions],
            total=len(positions),
            total_pnl=total_pnl,
            total_pnl_percent=total_pnl_percent
        )
    except Exception as e:
        logger.error(f"Failed to get positions: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail="Failed to retrieve positions. Please try again later."
        )


@router.get("/positions/{position_id:path}", response_model=PositionResponse)
async def get_position(position_id: str):
    """
    Get a specific position
    
    Note: Using :path to allow '/' in position_id
    """
    try:
        # URL decode in case it was double-encoded
        from urllib.parse import unquote
        position_id = unquote(position_id)
        positions = trading_service.get_positions()
        position = next((p for p in positions if p['id'] == position_id), None)
        
        if not position:
            raise HTTPException(
                status_code=404, 
                detail=f"Position '{position_id}' not found. It may have been closed or never existed."
            )
        
        return PositionResponse(**position)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get position {position_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail="Failed to retrieve position. Please try again later."
        )


@router.post("/positions", response_model=PositionResponse, status_code=201)
async def create_position(position_data: PositionCreate):
    """Open a new position"""
    try:
        logger.info(f"Opening {position_data.side} position: {position_data.amount} {position_data.symbol}")
        position = trading_service.open_position(
            symbol=position_data.symbol,
            side=position_data.side,
            amount=position_data.amount,
            stop_loss_percent=position_data.stop_loss_percent,
            trailing_stop_percent=position_data.trailing_stop_percent
        )
        logger.info(f"Successfully opened position: {position['id']}")
        return PositionResponse(**position)
    except ValueError as e:
        error_msg = str(e)
        logger.warning(f"Validation error opening position: {error_msg}")
        raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        logger.error(f"Failed to open position: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail="Failed to open position. Please try again later."
        )


@router.delete("/positions/{position_id:path}")
async def close_position(position_id: str):
    """
    Close a position
    
    Note: Using :path to allow '/' in position_id
    """
    try:
        # URL decode in case it was double-encoded
        from urllib.parse import unquote
        position_id = unquote(position_id)
        logger.info(f"Closing position: {position_id}")
        result = trading_service.close_position(position_id)
        logger.info(f"Successfully closed position: {position_id}")
        return {"message": "Position closed successfully", "result": result}
    except ValueError as e:
        error_msg = str(e)
        logger.warning(f"Error closing position {position_id}: {error_msg}")
        raise HTTPException(status_code=404, detail=error_msg)
    except Exception as e:
        logger.error(f"Failed to close position {position_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail="Failed to close position. Please try again later."
        )


@router.patch("/positions/{position_id:path}/stop-loss", response_model=PositionResponse)
async def set_stop_loss(position_id: str, data: StopLossUpdate):
    """
    Set stop loss for a position
    
    Note: Using :path to allow '/' in position_id
    """
    try:
        # URL decode in case it was double-encoded
        from urllib.parse import unquote
        position_id = unquote(position_id)
        logger.info(f"Setting stop loss for position {position_id}: {data.stop_loss_percent}%")
        position = trading_service.set_stop_loss(position_id, data.stop_loss_percent)
        return PositionResponse(**position)
    except ValueError as e:
        error_msg = str(e)
        logger.warning(f"Error setting stop loss for {position_id}: {error_msg}")
        raise HTTPException(status_code=404, detail=error_msg)
    except Exception as e:
        logger.error(f"Failed to set stop loss for {position_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail="Failed to set stop loss. Please try again later."
        )


@router.patch("/positions/{position_id:path}/trailing-stop", response_model=PositionResponse)
async def set_trailing_stop(position_id: str, data: TrailingStopUpdate):
    """
    Set trailing stop for a position
    
    Note: Using :path to allow '/' in position_id
    """
    try:
        # URL decode in case it was double-encoded
        from urllib.parse import unquote
        position_id = unquote(position_id)
        logger.info(f"Setting trailing stop for position {position_id}: {data.trailing_stop_percent}%")
        position = trading_service.set_trailing_stop(position_id, data.trailing_stop_percent)
        return PositionResponse(**position)
    except ValueError as e:
        error_msg = str(e)
        logger.warning(f"Error setting trailing stop for {position_id}: {error_msg}")
        raise HTTPException(status_code=404, detail=error_msg)
    except Exception as e:
        logger.error(f"Failed to set trailing stop for {position_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail="Failed to set trailing stop. Please try again later."
        )

