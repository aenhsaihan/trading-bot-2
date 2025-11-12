"""Strategy registry for managing available trading strategies"""

from typing import Dict, Type, Optional
from .base import StrategyBase
from .trend_following import TrendFollowingStrategy


class StrategyRegistry:
    """Registry for managing available trading strategies"""
    
    _strategies: Dict[str, Type[StrategyBase]] = {
        'trend_following': TrendFollowingStrategy,
    }
    
    _strategy_descriptions: Dict[str, str] = {
        'trend_following': 'Trend Following - Uses moving averages (MA) and momentum indicators (RSI, MACD) to identify and follow market trends. Best for trending markets.',
    }
    
    @classmethod
    def register(cls, name: str, strategy_class: Type[StrategyBase], description: str = ""):
        """Register a new strategy"""
        cls._strategies[name] = strategy_class
        if description:
            cls._strategy_descriptions[name] = description
    
    @classmethod
    def get_strategy(cls, name: str, config: Optional[Dict] = None) -> StrategyBase:
        """Get a strategy instance by name"""
        if name not in cls._strategies:
            raise ValueError(f"Unknown strategy: {name}. Available: {list(cls._strategies.keys())}")
        
        strategy_class = cls._strategies[name]
        return strategy_class(config=config)
    
    @classmethod
    def list_strategies(cls) -> Dict[str, str]:
        """List all available strategies with descriptions"""
        return cls._strategy_descriptions.copy()
    
    @classmethod
    def get_strategy_names(cls) -> list:
        """Get list of strategy names"""
        return list(cls._strategies.keys())
    
    @classmethod
    def get_display_name(cls, name: str) -> str:
        """Get a human-readable display name for a strategy"""
        display_names = {
            'trend_following': 'Trend Following',
        }
        return display_names.get(name, name.replace('_', ' ').title())

