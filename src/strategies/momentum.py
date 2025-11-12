"""Momentum strategy implementation"""

import pandas as pd
import numpy as np
from decimal import Decimal
from typing import Dict, List, Optional
from .base import StrategyBase
from src.utils.logger import setup_logger


class MomentumStrategy(StrategyBase):
    """Momentum strategy - buys on strong momentum, sells when momentum weakens"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize momentum strategy.
        
        Config parameters:
            rsi_period: RSI period (default: 14)
            rsi_buy_threshold: RSI threshold for buy signal (default: 55)
            rsi_sell_threshold: RSI threshold for sell signal (default: 45)
            macd_fast: MACD fast period (default: 12)
            macd_slow: MACD slow period (default: 26)
            macd_signal: MACD signal period (default: 9)
            volume_ma_period: Volume moving average period (default: 20)
            min_volume_multiplier: Minimum volume multiplier vs average (default: 1.2)
        """
        default_config = {
            'rsi_period': 14,
            'rsi_buy_threshold': 55,  # Buy when RSI is rising and above 55
            'rsi_sell_threshold': 45,  # Sell when RSI falls below 45
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            'volume_ma_period': 20,
            'min_volume_multiplier': 1.2  # Volume must be 1.2x average for confirmation
        }
        
        if config:
            default_config.update(config)
        
        super().__init__("momentum", default_config)
        self.logger = setup_logger(f"{__name__}.{self.name}")
        self.last_signals = {}  # Track last signals per symbol
    
    def _calculate_indicators(self, ohlcv_data: List[Dict]) -> Dict:
        """Calculate technical indicators from OHLCV data"""
        if len(ohlcv_data) < max(self.config['macd_slow'], self.config['volume_ma_period']):
            return {}
        
        # Convert to DataFrame
        df = pd.DataFrame(ohlcv_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        # Convert Decimal to float
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        
        # Calculate RSI
        rsi = self._calculate_rsi(df['close'], self.config['rsi_period'])
        
        # Calculate MACD
        macd_line, macd_signal = self._calculate_macd(
            df['close'],
            self.config['macd_fast'],
            self.config['macd_slow'],
            self.config['macd_signal']
        )
        
        # Calculate volume moving average
        volume_ma = df['volume'].rolling(window=self.config['volume_ma_period']).mean()
        
        # Get latest values
        latest_idx = -1
        
        indicators = {
            'rsi': float(rsi.iloc[latest_idx]) if len(rsi) > 0 and not pd.isna(rsi.iloc[latest_idx]) else None,
            'macd': float(macd_line.iloc[latest_idx]) if len(macd_line) > 0 and not pd.isna(macd_line.iloc[latest_idx]) else None,
            'macd_signal': float(macd_signal.iloc[latest_idx]) if len(macd_signal) > 0 and not pd.isna(macd_signal.iloc[latest_idx]) else None,
            'volume': float(df['volume'].iloc[latest_idx]),
            'volume_ma': float(volume_ma.iloc[latest_idx]) if not pd.isna(volume_ma.iloc[latest_idx]) else None,
            'price': float(df['close'].iloc[latest_idx])
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
    
    def _check_momentum_strength(self, indicators: Dict, symbol: str) -> bool:
        """Check if momentum is strong enough for entry"""
        rsi = indicators.get('rsi')
        macd = indicators.get('macd')
        macd_signal = indicators.get('macd_signal')
        volume = indicators.get('volume')
        volume_ma = indicators.get('volume_ma')
        
        # Get previous RSI for momentum direction
        last_signal = self.last_signals.get(symbol, {})
        prev_rsi = last_signal.get('rsi')
        
        # Check conditions
        conditions_met = 0
        
        # Condition 1: RSI is rising and above buy threshold
        if rsi and rsi > self.config['rsi_buy_threshold']:
            if prev_rsi is None or rsi > prev_rsi:  # RSI is rising
                conditions_met += 1
        
        # Condition 2: MACD bullish (MACD line above signal line)
        if macd is not None and macd_signal is not None and macd > macd_signal:
            conditions_met += 1
        
        # Condition 3: Volume confirmation (volume above average)
        if volume_ma and volume > (volume_ma * self.config['min_volume_multiplier']):
            conditions_met += 1
        
        # Need at least 2 out of 3 conditions
        return conditions_met >= 2
    
    def should_buy(self, market_data: Dict) -> bool:
        """
        Determine if buy signal should be generated.
        
        Entry conditions:
        - RSI is rising and above buy threshold (e.g., > 55)
        - MACD bullish (MACD line > signal line)
        - Volume above average (confirmation)
        """
        symbol = market_data.get('symbol', '')
        ohlcv_data = market_data.get('ohlcv', [])
        
        if not ohlcv_data:
            return False
        
        indicators = self._calculate_indicators(ohlcv_data)
        
        if not indicators:
            return False
        
        # Check momentum strength
        buy_signal = self._check_momentum_strength(indicators, symbol)
        
        # Update last signals
        self.last_signals[symbol] = {
            'rsi': indicators.get('rsi'),
            'macd': indicators.get('macd'),
            'macd_signal': indicators.get('macd_signal'),
            'volume': indicators.get('volume')
        }
        
        return buy_signal
    
    def should_sell(self, market_data: Dict, position: Dict) -> bool:
        """
        Determine if sell signal should be generated.
        
        Exit conditions:
        - RSI falls below sell threshold (e.g., < 45)
        - MACD bearish (MACD line crosses below signal line)
        - Momentum weakens significantly
        """
        symbol = market_data.get('symbol', '')
        ohlcv_data = market_data.get('ohlcv', [])
        
        if not ohlcv_data:
            return False
        
        indicators = self._calculate_indicators(ohlcv_data)
        
        if not indicators:
            return False
        
        rsi = indicators.get('rsi')
        macd = indicators.get('macd')
        macd_signal = indicators.get('macd_signal')
        
        # Get previous values for crossover detection
        last_signal = self.last_signals.get(symbol, {})
        prev_macd = last_signal.get('macd')
        prev_macd_signal = last_signal.get('macd_signal')
        
        sell_signal = False
        
        # Condition 1: RSI falls below sell threshold
        if rsi and rsi < self.config['rsi_sell_threshold']:
            sell_signal = True
        
        # Condition 2: MACD bearish crossover (MACD crosses below signal)
        if (macd is not None and macd_signal is not None and 
            prev_macd is not None and prev_macd_signal is not None):
            if prev_macd >= prev_macd_signal and macd < macd_signal:
                sell_signal = True
        
        # Condition 3: MACD already bearish and getting worse
        if macd is not None and macd_signal is not None and macd < macd_signal:
            if prev_macd is not None and macd < prev_macd:  # MACD getting more negative
                sell_signal = True
        
        # Update last signals
        self.last_signals[symbol] = {
            'rsi': rsi,
            'macd': macd,
            'macd_signal': macd_signal,
            'volume': indicators.get('volume')
        }
        
        return sell_signal
    
    def calculate_position_size(self, balance: Decimal, price: Decimal, risk_percent: float) -> Decimal:
        """Calculate position size based on risk percentage"""
        if price <= 0:
            return Decimal('0')
        
        position_value = balance * Decimal(str(risk_percent))
        position_size = position_value / price
        
        return position_size

