"""Trend following strategy implementation"""

import pandas as pd
import numpy as np
from decimal import Decimal
from typing import Dict, List, Optional
from .base import StrategyBase, SignalType
from src.utils.logger import setup_logger


class TrendFollowingStrategy(StrategyBase):
    """Trend following strategy using moving averages and momentum indicators"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize trend following strategy.
        
        Config parameters:
            short_ma_period: Short moving average period (default: 50)
            long_ma_period: Long moving average period (default: 200)
            rsi_period: RSI period (default: 14)
            rsi_overbought: RSI overbought threshold (default: 70)
            rsi_oversold: RSI oversold threshold (default: 30)
        """
        default_config = {
            'short_ma_period': 50,
            'long_ma_period': 200,
            'rsi_period': 14,
            'rsi_overbought': 70,
            'rsi_oversold': 30
        }
        
        if config:
            default_config.update(config)
        
        super().__init__("trend_following", default_config)
        self.logger = setup_logger(f"{__name__}.{self.name}")
        self.last_signals = {}  # Track last signals per symbol
    
    def _calculate_indicators(self, ohlcv_data: List[Dict]) -> Dict:
        """
        Calculate technical indicators from OHLCV data.
        
        Args:
            ohlcv_data: List of OHLCV dictionaries
            
        Returns:
            Dictionary with calculated indicators
        """
        if len(ohlcv_data) < self.config['long_ma_period']:
            return {}
        
        # Convert to DataFrame
        df = pd.DataFrame(ohlcv_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        # Convert Decimal to float
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        
        # Calculate moving averages using pandas rolling mean
        short_ma = df['close'].rolling(window=self.config['short_ma_period']).mean()
        long_ma = df['close'].rolling(window=self.config['long_ma_period']).mean()
        
        # Calculate RSI manually
        rsi = self._calculate_rsi(df['close'], self.config['rsi_period'])
        
        # Calculate MACD manually
        macd_line, macd_signal = self._calculate_macd(df['close'])
        
        # Get latest values
        latest_idx = -1
        
        indicators = {
            'short_ma': float(short_ma.iloc[latest_idx]) if not pd.isna(short_ma.iloc[latest_idx]) else None,
            'long_ma': float(long_ma.iloc[latest_idx]) if not pd.isna(long_ma.iloc[latest_idx]) else None,
            'rsi': float(rsi.iloc[latest_idx]) if len(rsi) > 0 and not pd.isna(rsi.iloc[latest_idx]) else None,
            'macd': float(macd_line.iloc[latest_idx]) if len(macd_line) > 0 and not pd.isna(macd_line.iloc[latest_idx]) else None,
            'macd_signal': float(macd_signal.iloc[latest_idx]) if len(macd_signal) > 0 and not pd.isna(macd_signal.iloc[latest_idx]) else None,
            'price': float(df['close'].iloc[latest_idx]),
            'volume': float(df['volume'].iloc[latest_idx])
        }
        
        return indicators
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI (Relative Strength Index)"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        macd_signal = macd_line.ewm(span=signal, adjust=False).mean()
        return macd_line, macd_signal
    
    def _check_crossover(self, indicators: Dict, symbol: str) -> Optional[str]:
        """
        Check for moving average crossover.
        
        Returns:
            'bullish' if golden cross, 'bearish' if death cross, None otherwise
        """
        if not indicators.get('short_ma') or not indicators.get('long_ma'):
            return None
        
        short_ma = indicators['short_ma']
        long_ma = indicators['long_ma']
        
        # Get previous signals for this symbol
        last_signal = self.last_signals.get(symbol, {})
        prev_short_ma = last_signal.get('short_ma')
        prev_long_ma = last_signal.get('long_ma')
        
        # Check for crossover
        if prev_short_ma and prev_long_ma:
            # Golden cross: short MA crosses above long MA
            if prev_short_ma <= prev_long_ma and short_ma > long_ma:
                return 'bullish'
            # Death cross: short MA crosses below long MA
            elif prev_short_ma >= prev_long_ma and short_ma < long_ma:
                return 'bearish'
        
        return None
    
    def should_buy(self, market_data: Dict) -> bool:
        """
        Determine if buy signal should be generated.
        
        Entry conditions:
        - Short MA crosses above long MA (golden cross)
        - RSI < overbought threshold
        - MACD positive (optional confirmation)
        """
        symbol = market_data.get('symbol', '')
        ohlcv_data = market_data.get('ohlcv', [])
        
        if not ohlcv_data:
            return False
        
        indicators = self._calculate_indicators(ohlcv_data)
        
        if not indicators:
            return False
        
        # Check for bullish crossover
        crossover = self._check_crossover(indicators, symbol)
        if crossover == 'bullish':
            # Additional conditions
            rsi = indicators.get('rsi')
            if rsi and rsi < self.config['rsi_overbought']:
                # Update last signals
                self.last_signals[symbol] = {
                    'short_ma': indicators['short_ma'],
                    'long_ma': indicators['long_ma'],
                    'rsi': rsi
                }
                return True
        
        # Update last signals even if no signal
        self.last_signals[symbol] = {
            'short_ma': indicators.get('short_ma'),
            'long_ma': indicators.get('long_ma'),
            'rsi': indicators.get('rsi')
        }
        
        return False
    
    def should_sell(self, market_data: Dict, position: Dict) -> bool:
        """
        Determine if sell signal should be generated.
        
        Exit conditions:
        - Short MA crosses below long MA (death cross)
        - RSI > overbought threshold
        - Stop loss triggered (handled by risk management)
        """
        symbol = market_data.get('symbol', '')
        ohlcv_data = market_data.get('ohlcv', [])
        
        if not ohlcv_data:
            return False
        
        indicators = self._calculate_indicators(ohlcv_data)
        
        if not indicators:
            return False
        
        # Check for bearish crossover
        crossover = self._check_crossover(indicators, symbol)
        if crossover == 'bearish':
            self.last_signals[symbol] = {
                'short_ma': indicators['short_ma'],
                'long_ma': indicators['long_ma'],
                'rsi': indicators.get('rsi')
            }
            return True
        
        # Check RSI overbought
        rsi = indicators.get('rsi')
        if rsi and rsi > self.config['rsi_overbought']:
            return True
        
        # Update last signals
        self.last_signals[symbol] = {
            'short_ma': indicators.get('short_ma'),
            'long_ma': indicators.get('long_ma'),
            'rsi': rsi
        }
        
        return False
    
    def calculate_position_size(self, balance: Decimal, price: Decimal, risk_percent: float) -> Decimal:
        """
        Calculate position size based on risk percentage.
        
        Args:
            balance: Available balance
            price: Entry price
            risk_percent: Risk percentage (e.g., 0.01 for 1%)
            
        Returns:
            Position size in base currency
        """
        if price <= 0:
            return Decimal('0')
        
        position_value = balance * Decimal(str(risk_percent))
        position_size = position_value / price
        
        return position_size

