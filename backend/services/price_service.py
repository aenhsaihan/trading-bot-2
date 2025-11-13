"""Price service for fetching real market data from exchanges"""

import sys
from pathlib import Path
from decimal import Decimal
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.exchanges.binance import BinanceExchange
from src.exchanges.coinbase import CoinbaseExchange
from src.exchanges.kraken import KrakenExchange
from src.utils.config import Config
from src.utils.logger import setup_logger


class PriceService:
    """Service for fetching real market prices from exchanges"""
    
    def __init__(self, exchange_name: str = "binance"):
        """
        Initialize price service.
        
        Args:
            exchange_name: Exchange to use ('binance', 'coinbase', 'kraken')
                          Defaults to 'binance' for public data access
        """
        self.exchange_name = exchange_name.lower()
        self.exchange = None
        self.config = Config()
        self.logger = setup_logger(f"{__name__}.PriceService")
        self._initialize_exchange()
    
    def _initialize_exchange(self):
        """Initialize exchange connection (public data only, no API keys needed)"""
        try:
            if self.exchange_name == "binance":
                # Binance allows public data without API keys
                self.exchange = BinanceExchange(api_key=None, api_secret=None, sandbox=False)
            elif self.exchange_name == "coinbase":
                self.exchange = CoinbaseExchange(api_key=None, api_secret=None, sandbox=False)
            elif self.exchange_name == "kraken":
                self.exchange = KrakenExchange(api_key=None, api_secret=None, sandbox=False)
            else:
                self.logger.warning(f"Unknown exchange: {self.exchange_name}, defaulting to Binance")
                self.exchange = BinanceExchange(api_key=None, api_secret=None, sandbox=False)
                self.exchange_name = "binance"
            
            # Connect to exchange (public endpoints don't require authentication)
            if not self.exchange.connect():
                self.logger.error(f"Failed to connect to {self.exchange_name}. Check network connection and exchange availability.")
                self.exchange = None
            else:
                self.logger.info(f"PriceService initialized with {self.exchange_name} - Connected: {self.exchange.is_connected()}")
        except Exception as e:
            self.logger.error(f"Error initializing exchange {self.exchange_name}: {e}", exc_info=True)
            self.exchange = None
    
    def get_current_price(self, symbol: str) -> Decimal:
        """
        Get current price for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            
        Returns:
            Current price as Decimal
        """
        if not self.exchange or not self.exchange.is_connected():
            self.logger.warning("Exchange not connected, returning 0")
            return Decimal('0')
        
        try:
            ticker = self.exchange.get_ticker(symbol)
            price = ticker.get('last', Decimal('0'))
            if price == 0:
                self.logger.warning(f"Got zero price for {symbol}, exchange may not have this symbol")
            return price
        except Exception as e:
            self.logger.error(f"Error fetching price for {symbol}: {e}")
            # Return 0 on error - caller should handle this
            return Decimal('0')
    
    def get_current_prices(self, symbols: List[str]) -> Dict[str, Decimal]:
        """
        Get current prices for multiple symbols.
        
        Args:
            symbols: List of trading pair symbols
            
        Returns:
            Dictionary mapping symbol to price
        """
        prices = {}
        for symbol in symbols:
            prices[symbol] = self.get_current_price(symbol)
        return prices
    
    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get full ticker data for a symbol.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Ticker data dictionary
        """
        if not self.exchange or not self.exchange.is_connected():
            self.logger.warning("Exchange not connected")
            raise Exception("Exchange not connected")
        
        try:
            ticker = self.exchange.get_ticker(symbol)
            if not ticker:
                raise Exception(f"Ticker data not found for {symbol}")
            return ticker
        except Exception as e:
            self.logger.error(f"Error fetching ticker for {symbol}: {e}")
            raise
    
    def get_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get OHLCV (candlestick) data for a symbol.
        
        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe ('1m', '5m', '15m', '1h', '4h', '1d', etc.)
            limit: Number of candles to fetch
            
        Returns:
            List of OHLCV dictionaries
        """
        if not self.exchange:
            return []
        
        try:
            return self.exchange.get_ohlcv(symbol, timeframe, limit)
        except Exception as e:
            self.logger.error(f"Error fetching OHLCV for {symbol}: {e}")
            return []
    
    def is_connected(self) -> bool:
        """Check if exchange is connected"""
        return self.exchange is not None and self.exchange.is_connected()


# Global price service instance (singleton pattern)
_price_service: Optional[PriceService] = None


def get_price_service(exchange_name: str = "binance") -> PriceService:
    """
    Get or create price service instance.
    
    Args:
        exchange_name: Exchange to use (default: 'binance')
        
    Returns:
        PriceService instance
    """
    global _price_service
    if _price_service is None or _price_service.exchange_name != exchange_name:
        _price_service = PriceService(exchange_name)
    return _price_service

