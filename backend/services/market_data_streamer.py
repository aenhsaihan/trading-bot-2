"""Market data streaming service for real-time OHLCV and ticker updates"""

import sys
import asyncio
from pathlib import Path
from typing import Dict, Set, List, Optional, Any
from decimal import Decimal
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.services.price_service import get_price_service
from backend.services.websocket_manager import get_websocket_manager
from src.utils.logger import setup_logger


class MarketDataStreamer:
    """Service for streaming real-time market data (prices, OHLCV) to WebSocket clients"""
    
    def __init__(self, update_interval: float = 5.0):  # Increased from 2.0 to 5.0 to reduce API calls and avoid rate limiting
        """
        Initialize market data streamer.
        
        Args:
            update_interval: How often to poll for updates (in seconds)
        """
        self.update_interval = update_interval
        self.price_service = get_price_service("binance")
        self.ws_manager = get_websocket_manager()
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
        self.logger = setup_logger(f"{__name__}.MarketDataStreamer")
        
        # Cache for last known prices to detect changes
        self.last_prices: Dict[str, Decimal] = {}
        self.last_tickers: Dict[str, Dict[str, Any]] = {}
        self.last_ohlcv: Dict[str, Dict[str, Any]] = {}
    
    def start_streaming(self):
        """Start the market data streaming task"""
        if self.is_running:
            self.logger.warning("Market data streaming already running")
            return
        
        self.is_running = True
        self._task = asyncio.create_task(self._streaming_loop())
        self.logger.info(f"Started market data streaming (interval: {self.update_interval}s)")
    
    def stop_streaming(self):
        """Stop the market data streaming task"""
        if not self.is_running:
            return
        
        self.is_running = False
        if self._task:
            self._task.cancel()
            self._task = None
        self.logger.info("Stopped market data streaming")
    
    async def _streaming_loop(self):
        """Main streaming loop - polls for updates and broadcasts to subscribers"""
        while self.is_running:
            try:
                # Get all subscribed symbols
                subscribed_symbols = self.ws_manager.get_all_subscriptions()
                
                if not subscribed_symbols:
                    # No subscriptions, wait a bit longer
                    await asyncio.sleep(self.update_interval * 2)
                    continue
                
                # Fetch data for all subscribed symbols
                for symbol in subscribed_symbols:
                    try:
                        await self._update_symbol_data(symbol)
                    except Exception as e:
                        self.logger.error(f"Error updating data for {symbol}: {e}", exc_info=True)
                
                # Wait before next update
                await asyncio.sleep(self.update_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in streaming loop: {e}", exc_info=True)
                await asyncio.sleep(self.update_interval)
    
    async def _update_symbol_data(self, symbol: str):
        """Update and broadcast data for a single symbol"""
        try:
            # Get current price/ticker
            current_price = self.price_service.get_current_price(symbol)
            
            if current_price and current_price > 0:
                # Check if price changed
                price_changed = symbol not in self.last_prices or self.last_prices[symbol] != current_price
                
                if price_changed or symbol not in self.last_prices:
                    # Price update
                    self.last_prices[symbol] = current_price
                    
                    # Get full ticker data
                    try:
                        ticker = self.price_service.get_ticker(symbol)
                        self.last_tickers[symbol] = ticker
                    except Exception as e:
                        self.logger.warning(f"Could not fetch ticker for {symbol}: {e}")
                        ticker = {
                            "last": float(current_price),
                            "timestamp": datetime.now().timestamp()
                        }
                    
                    # Broadcast price update
                    await self.ws_manager.broadcast(
                        {
                            "type": "price_update",
                            "symbol": symbol,
                            "price": float(current_price),
                            "ticker": {
                                "last": ticker.get("last", float(current_price)),
                                "bid": ticker.get("bid", float(current_price)),
                                "ask": ticker.get("ask", float(current_price)),
                                "volume": ticker.get("volume", 0),
                                "timestamp": ticker.get("timestamp", datetime.now().timestamp())
                            },
                            "timestamp": datetime.now().isoformat()
                        },
                        client_type="market_data",
                        symbols={symbol}
                    )
            
            # Periodically fetch OHLCV data (less frequently)
            # Check if we should update OHLCV (every 5th cycle or if not cached)
            should_update_ohlcv = (
                symbol not in self.last_ohlcv or
                (datetime.now().timestamp() - self.last_ohlcv[symbol].get("timestamp", 0)) > 30
            )
            
            if should_update_ohlcv:
                try:
                    # Get OHLCV for 1h timeframe (most common)
                    ohlcv_data = self.price_service.get_ohlcv(symbol, "1h", 100)
                    if ohlcv_data:
                        self.last_ohlcv[symbol] = {
                            "data": ohlcv_data,
                            "timestamp": datetime.now().timestamp()
                        }
                        
                        # Broadcast OHLCV update
                        await self.ws_manager.broadcast(
                            {
                                "type": "ohlcv_update",
                                "symbol": symbol,
                                "timeframe": "1h",
                                "candles": ohlcv_data[-10:],  # Last 10 candles
                                "timestamp": datetime.now().isoformat()
                            },
                            client_type="market_data",
                            symbols={symbol}
                        )
                except Exception as e:
                    self.logger.warning(f"Could not fetch OHLCV for {symbol}: {e}")
        
        except Exception as e:
            self.logger.error(f"Error updating symbol {symbol}: {e}", exc_info=True)
    
    async def get_latest_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get latest cached data for a symbol"""
        data = {
            "symbol": symbol,
            "price": None,
            "ticker": None,
            "ohlcv": None
        }
        
        if symbol in self.last_prices:
            data["price"] = float(self.last_prices[symbol])
        
        if symbol in self.last_tickers:
            data["ticker"] = self.last_tickers[symbol]
        
        if symbol in self.last_ohlcv:
            data["ohlcv"] = self.last_ohlcv[symbol].get("data", [])
        
        return data if any(data.values()) else None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get streamer statistics"""
        return {
            "is_running": self.is_running,
            "update_interval": self.update_interval,
            "monitored_symbols": len(self.last_prices),
            "subscribed_symbols": list(self.ws_manager.get_all_subscriptions())
        }


# Global market data streamer instance (singleton)
_market_data_streamer: Optional[MarketDataStreamer] = None


def get_market_data_streamer(update_interval: float = 2.0) -> MarketDataStreamer:
    """Get or create market data streamer instance"""
    global _market_data_streamer
    if _market_data_streamer is None:
        _market_data_streamer = MarketDataStreamer(update_interval)
    return _market_data_streamer


