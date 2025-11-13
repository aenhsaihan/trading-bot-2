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

router = APIRouter(prefix="/trading", tags=["trading"])

# Global service instance (in production, use dependency injection)
trading_service = TradingService()


@router.get("/balance", response_model=BalanceResponse)
async def get_balance():
    """Get account balance and portfolio value"""
    try:
        balance_data = trading_service.get_balance()
        return BalanceResponse(**balance_data)
    except Exception as e:
        import traceback
        error_detail = f"Failed to get balance: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)  # Log to console for debugging
        raise HTTPException(status_code=500, detail=f"Failed to get balance: {str(e)}")


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
        raise HTTPException(status_code=500, detail=f"Failed to get positions: {str(e)}")


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
            raise HTTPException(status_code=404, detail="Position not found")
        
        return PositionResponse(**position)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get position: {str(e)}")


@router.post("/positions", response_model=PositionResponse, status_code=201)
async def create_position(position_data: PositionCreate):
    """Open a new position"""
    try:
        # Additional validation
        if position_data.amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be greater than 0")
        
        if position_data.side not in ['long', 'short']:
            raise HTTPException(status_code=400, detail="Side must be 'long' or 'short'")
        
        # Validate symbol format (basic check)
        if not position_data.symbol or '/' not in position_data.symbol:
            raise HTTPException(status_code=400, detail="Symbol must be in format 'BASE/QUOTE' (e.g., 'BTC/USDT')")
        
        # Validate stop loss and trailing stop percentages
        if position_data.stop_loss_percent is not None:
            if position_data.stop_loss_percent < 0 or position_data.stop_loss_percent > 100:
                raise HTTPException(status_code=400, detail="Stop loss percentage must be between 0 and 100")
        
        if position_data.trailing_stop_percent is not None:
            if position_data.trailing_stop_percent < 0 or position_data.trailing_stop_percent > 100:
                raise HTTPException(status_code=400, detail="Trailing stop percentage must be between 0 and 100")
        
        position = trading_service.open_position(
            symbol=position_data.symbol,
            side=position_data.side,
            amount=position_data.amount,
            stop_loss_percent=position_data.stop_loss_percent,
            trailing_stop_percent=position_data.trailing_stop_percent
        )
        return PositionResponse(**position)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        error_detail = f"Failed to open position: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)  # Log to console for debugging
        raise HTTPException(status_code=500, detail=f"Failed to open position: {str(e)}")


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
        
        if not position_id or len(position_id.strip()) == 0:
            raise HTTPException(status_code=400, detail="Position ID cannot be empty")
        
        result = trading_service.close_position(position_id)
        return {"message": "Position closed successfully", "result": result}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to close position: {str(e)}")


@router.patch("/positions/{position_id:path}/stop-loss", response_model=PositionResponse)
async def set_stop_loss(position_id: str, data: StopLossUpdate):
    """
    Set stop loss for a position
    
    Note: Using :path to allow '/' in position_id
    """
    try:
        # Validate stop loss percentage
        if data.stop_loss_percent < 0 or data.stop_loss_percent > 100:
            raise HTTPException(status_code=400, detail="Stop loss percentage must be between 0 and 100")
        
        # URL decode in case it was double-encoded
        from urllib.parse import unquote
        position_id = unquote(position_id)
        
        if not position_id or len(position_id.strip()) == 0:
            raise HTTPException(status_code=400, detail="Position ID cannot be empty")
        
        position = trading_service.set_stop_loss(position_id, data.stop_loss_percent)
        return PositionResponse(**position)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set stop loss: {str(e)}")


@router.patch("/positions/{position_id:path}/trailing-stop", response_model=PositionResponse)
async def set_trailing_stop(position_id: str, data: TrailingStopUpdate):
    """
    Set trailing stop for a position
    
    Note: Using :path to allow '/' in position_id
    """
    try:
        # Validate trailing stop percentage
        if data.trailing_stop_percent < 0 or data.trailing_stop_percent > 100:
            raise HTTPException(status_code=400, detail="Trailing stop percentage must be between 0 and 100")
        
        # URL decode in case it was double-encoded
        from urllib.parse import unquote
        position_id = unquote(position_id)
        
        if not position_id or len(position_id.strip()) == 0:
            raise HTTPException(status_code=400, detail="Position ID cannot be empty")
        
        position = trading_service.set_trailing_stop(position_id, data.trailing_stop_percent)
        return PositionResponse(**position)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set trailing stop: {str(e)}")

