"""Base exchange interface"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from decimal import Decimal


class ExchangeBase(ABC):
    """Abstract base class for exchange implementations"""
    
    def __init__(self, name: str, api_key: Optional[str] = None, api_secret: Optional[str] = None, sandbox: bool = False):
        """
        Initialize exchange.
        
        Args:
            name: Exchange name
            api_key: API key (optional for read-only operations)
            api_secret: API secret (optional for read-only operations)
            sandbox: Use sandbox/testnet if available
        """
        self.name = name
        self.api_key = api_key
        self.api_secret = api_secret
        self.sandbox = sandbox
        self._connected = False
    
    @abstractmethod
    def connect(self) -> bool:
        """
        Connect to exchange.
        
        Returns:
            True if connection successful
        """
        pass
    
    @abstractmethod
    def get_balance(self, currency: str = "USDT") -> Decimal:
        """
        Get account balance for a currency.
        
        Args:
            currency: Currency symbol (e.g., 'USDT', 'BTC')
            
        Returns:
            Available balance
        """
        pass
    
    @abstractmethod
    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get current ticker price for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            
        Returns:
            Ticker data with 'last', 'bid', 'ask', 'volume', etc.
        """
        pass
    
    @abstractmethod
    def get_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 100, since: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get OHLCV (candlestick) data.
        
        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe (e.g., '1m', '5m', '1h', '1d')
            limit: Number of candles to retrieve
            since: Start timestamp in milliseconds (optional)
            
        Returns:
            List of OHLCV data dictionaries with 'timestamp', 'open', 'high', 'low', 'close', 'volume'
        """
        pass
    
    @abstractmethod
    def place_order(self, symbol: str, side: str, amount: Decimal, order_type: str = "market", price: Optional[Decimal] = None) -> Dict[str, Any]:
        """
        Place an order.
        
        Args:
            symbol: Trading pair symbol
            side: 'buy' or 'sell'
            amount: Order amount
            order_type: 'market' or 'limit'
            price: Limit price (required for limit orders)
            
        Returns:
            Order information with 'id', 'status', 'filled', etc.
        """
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """
        Cancel an order.
        
        Args:
            order_id: Order ID to cancel
            symbol: Trading pair symbol
            
        Returns:
            True if cancellation successful
        """
        pass
    
    @abstractmethod
    def get_order_status(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """
        Get order status.
        
        Args:
            order_id: Order ID
            symbol: Trading pair symbol
            
        Returns:
            Order status information
        """
        pass
    
    @abstractmethod
    def get_open_positions(self) -> List[Dict[str, Any]]:
        """
        Get all open positions.
        
        Returns:
            List of open positions
        """
        pass
    
    def is_connected(self) -> bool:
        """Check if exchange is connected"""
        return self._connected
    
    def disconnect(self):
        """Disconnect from exchange"""
        self._connected = False

