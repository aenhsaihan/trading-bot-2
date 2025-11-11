"""Base strategy interface"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from decimal import Decimal
from enum import Enum


class SignalType(Enum):
    """Trading signal types"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class StrategyBase(ABC):
    """Abstract base class for trading strategies"""
    
    def __init__(self, name: str, config: Optional[Dict] = None):
        """
        Initialize strategy.
        
        Args:
            name: Strategy name
            config: Strategy configuration dictionary
        """
        self.name = name
        self.config = config or {}
        self.signals_history = []
    
    @abstractmethod
    def should_buy(self, market_data: Dict) -> bool:
        """
        Determine if a buy signal should be generated.
        
        Args:
            market_data: Dictionary containing OHLCV data, indicators, etc.
            
        Returns:
            True if buy signal should be generated
        """
        pass
    
    @abstractmethod
    def should_sell(self, market_data: Dict, position: Dict) -> bool:
        """
        Determine if a sell signal should be generated.
        
        Args:
            market_data: Dictionary containing current market data
            position: Dictionary containing position information
            
        Returns:
            True if sell signal should be generated
        """
        pass
    
    @abstractmethod
    def calculate_position_size(self, balance: Decimal, price: Decimal, risk_percent: float) -> Decimal:
        """
        Calculate position size based on risk management.
        
        Args:
            balance: Available balance
            price: Entry price
            risk_percent: Risk percentage (e.g., 0.01 for 1%)
            
        Returns:
            Position size in base currency
        """
        pass
    
    def get_signal(self, market_data: Dict, position: Optional[Dict] = None) -> SignalType:
        """
        Get current trading signal.
        
        Args:
            market_data: Current market data
            position: Current position (if any)
            
        Returns:
            SignalType enum value
        """
        if position:
            if self.should_sell(market_data, position):
                return SignalType.SELL
        else:
            if self.should_buy(market_data):
                return SignalType.BUY
        
        return SignalType.HOLD
    
    def update_config(self, config: Dict):
        """Update strategy configuration"""
        self.config.update(config)
    
    def get_config(self) -> Dict:
        """Get current configuration"""
        return self.config.copy()

