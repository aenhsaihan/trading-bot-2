"""Pydantic models for market data API"""

from pydantic import BaseModel
from typing import List, Optional, Dict


class PriceResponse(BaseModel):
    """Single price response"""
    symbol: str
    price: float


class PricesResponse(BaseModel):
    """Multiple prices response"""
    prices: Dict[str, Optional[float]]


class TickerResponse(BaseModel):
    """Ticker data response"""
    symbol: str
    last: float
    bid: float
    ask: float
    volume: float
    timestamp: int


class Candle(BaseModel):
    """OHLCV candle data"""
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float


class OHLCVResponse(BaseModel):
    """OHLCV data response"""
    symbol: str
    timeframe: str
    candles: List[Candle]

