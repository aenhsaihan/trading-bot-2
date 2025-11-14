"""Market data API routes"""

import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from decimal import Decimal

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.api.models.market_data import (
    TickerResponse,
    OHLCVResponse,
    PriceResponse,
    PricesResponse
)
from backend.services.price_service import get_price_service
from backend.services.symbol_normalizer import normalize_symbol, normalize_symbols

router = APIRouter(prefix="/market-data", tags=["market-data"])


@router.get("/health")
async def health_check():
    """Check if market data service is available"""
    try:
        price_service = get_price_service()
        is_connected = price_service.is_connected()
        return {
            "status": "ok" if is_connected else "disconnected",
            "exchange": price_service.exchange_name,
            "connected": is_connected
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "connected": False
        }


@router.get("/price/{symbol:path}", response_model=PriceResponse)
async def get_price(symbol: str):
    """
    Get current price for a symbol
    
    Args:
        symbol: Trading pair symbol (e.g., 'BTC/USDT')
    """
    try:
        from urllib.parse import unquote
        symbol = unquote(symbol)
        # Normalize symbol to BASE/QUOTE format (e.g., "SHIB" -> "SHIB/USDT")
        normalized_symbol = normalize_symbol(symbol)
        price_service = get_price_service()
        if not price_service.is_connected():
            raise HTTPException(
                status_code=503,
                detail="Exchange connection not available. Please check your network connection."
            )
        
        price = price_service.get_current_price(normalized_symbol)
        if price == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Price not found for symbol: {symbol}"
            )
        
        return {"symbol": symbol, "price": float(price)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch price: {str(e)}"
        )


@router.post("/prices", response_model=PricesResponse)
async def get_prices(symbols: List[str]):
    """
    Get current prices for multiple symbols
    
    Args:
        symbols: List of trading pair symbols
    """
    try:
        price_service = get_price_service()
        if not price_service.is_connected():
            raise HTTPException(
                status_code=503,
                detail="Exchange connection not available. Please check your network connection."
            )
        
        # Normalize symbols to BASE/QUOTE format (e.g., "SHIB" -> "SHIB/USDT")
        normalized_symbols = normalize_symbols(symbols)
        prices = price_service.get_current_prices(normalized_symbols)
        
        # Return prices with original symbol keys (for backward compatibility)
        # Map normalized symbols back to original if needed
        price_map = {}
        for i, original_symbol in enumerate(symbols):
            normalized = normalized_symbols[i]
            price_map[original_symbol] = prices.get(normalized, Decimal('0'))
        return {
            "prices": {
                symbol: float(price) if price > 0 else None
                for symbol, price in prices.items()
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch prices: {str(e)}"
        )


@router.get("/ticker/{symbol:path}", response_model=TickerResponse)
async def get_ticker(symbol: str):
    """
    Get full ticker data for a symbol
    
    Args:
        symbol: Trading pair symbol
    """
    try:
        from urllib.parse import unquote
        symbol = unquote(symbol)
        # Normalize symbol to BASE/QUOTE format (e.g., "SHIB" -> "SHIB/USDT")
        normalized_symbol = normalize_symbol(symbol)
        price_service = get_price_service()
        if not price_service.is_connected():
            raise HTTPException(
                status_code=503,
                detail="Exchange connection not available. Please check your network connection."
            )
        
        ticker = price_service.get_ticker(normalized_symbol)
        if not ticker:
            raise HTTPException(
                status_code=404,
                detail=f"Ticker not found for symbol: {symbol}. The symbol may not be available on this exchange."
            )
        
        return {
            "symbol": symbol,  # Return original symbol (not normalized) for backward compatibility
            "last": float(ticker.get("last", 0)),
            "bid": float(ticker.get("bid", 0)),
            "ask": float(ticker.get("ask", 0)),
            "volume": float(ticker.get("volume", 0)),
            "timestamp": ticker.get("timestamp", 0)
        }
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        # Check if it's a connection or symbol issue
        if "not connected" in error_msg.lower():
            raise HTTPException(
                status_code=503,
                detail="Exchange connection not available. Please check your network connection."
            )
        elif "not found" in error_msg.lower() or "symbol" in error_msg.lower():
            raise HTTPException(
                status_code=404,
                detail=f"Symbol {symbol} not found on exchange. Please check the symbol format (e.g., 'BTC/USDT')."
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch ticker: {error_msg}"
            )


@router.get("/ohlcv/{symbol:path}", response_model=OHLCVResponse)
async def get_ohlcv(
    symbol: str,
    timeframe: str = Query("1h", description="Timeframe (1m, 5m, 15m, 1h, 4h, 1d, etc.)"),
    limit: int = Query(100, ge=1, le=1000, description="Number of candles to fetch")
):
    """
    Get OHLCV (candlestick) data for a symbol
    
    Args:
        symbol: Trading pair symbol
        timeframe: Timeframe for candles
        limit: Number of candles to fetch (1-1000)
    """
    try:
        from urllib.parse import unquote
        symbol = unquote(symbol)
        # Normalize symbol to BASE/QUOTE format (e.g., "SHIB" -> "SHIB/USDT")
        normalized_symbol = normalize_symbol(symbol)
        price_service = get_price_service()
        if not price_service.is_connected():
            raise HTTPException(
                status_code=503,
                detail="Exchange connection not available. Please check your network connection."
            )
        
        ohlcv_data = price_service.get_ohlcv(normalized_symbol, timeframe, limit)
        if not ohlcv_data:
            raise HTTPException(
                status_code=404,
                detail=f"OHLCV data not found for symbol: {symbol}"
            )
        
        # Convert to response format
        candles = []
        for candle in ohlcv_data:
            candles.append({
                "timestamp": candle.get("timestamp", 0),
                "open": float(candle.get("open", 0)),
                "high": float(candle.get("high", 0)),
                "low": float(candle.get("low", 0)),
                "close": float(candle.get("close", 0)),
                "volume": float(candle.get("volume", 0))
            })
        
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "candles": candles
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch OHLCV data: {str(e)}"
        )

