"""Pydantic models for trading API"""

from pydantic import BaseModel, Field
from typing import Optional, List
from decimal import Decimal
from datetime import datetime


class PositionResponse(BaseModel):
    """Position response model"""
    id: str
    symbol: str
    side: str  # 'long' or 'short'
    amount: float
    entry_price: float
    current_price: float
    pnl: float
    pnl_percent: float
    stop_loss: Optional[float] = None  # Stop loss price
    stop_loss_percent: Optional[float] = None  # Stop loss percentage
    trailing_stop: Optional[float] = None  # Trailing stop percentage
    entry_time: str
    created_at: str


class PositionCreate(BaseModel):
    """Create position request model"""
    symbol: str
    side: str = Field(default="long", pattern="^(long|short)$")
    amount: float = Field(gt=0, description="Position amount")
    stop_loss_percent: Optional[float] = Field(None, ge=0, le=100, description="Stop loss percentage")
    trailing_stop_percent: Optional[float] = Field(None, ge=0, le=100, description="Trailing stop percentage")


class PositionUpdate(BaseModel):
    """Update position request model"""
    stop_loss_percent: Optional[float] = Field(None, ge=0, le=100)
    trailing_stop_percent: Optional[float] = Field(None, ge=0, le=100)


class StopLossUpdate(BaseModel):
    """Stop loss update request model"""
    stop_loss_percent: float = Field(ge=0, le=100, description="Stop loss percentage")


class TrailingStopUpdate(BaseModel):
    """Trailing stop update request model"""
    trailing_stop_percent: float = Field(ge=0, le=100, description="Trailing stop percentage")


class BalanceResponse(BaseModel):
    """Balance response model"""
    balance: float
    currency: str = "USDT"
    total_value: float
    total_pnl: float
    total_pnl_percent: float


class PositionListResponse(BaseModel):
    """List of positions response"""
    positions: List[PositionResponse]
    total: int
    total_pnl: float
    total_pnl_percent: float

