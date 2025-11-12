"""Mean reversion strategy implementation"""

import pandas as pd
import numpy as np
from decimal import Decimal
from typing import Dict, List, Optional
from .base import StrategyBase
from src.utils.logger import setup_logger


class MeanReversionStrategy(StrategyBase):
    """Mean reversion strategy - buys when oversold, sells when overbought"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize mean reversion strategy.
        
        Config parameters:
            rsi_period: RSI period (default: 14)
            rsi_oversold: RSI oversold threshold - buy signal (default: 30)
            rsi_overbought: RSI overbought threshold - sell signal (default: 70)
            bb_period: Bollinger Bands period (default: 20)
            bb_std: Bollinger Bands standard deviation (default: 2.0)
            ma_period: Moving average period for trend filter (default: 50)
        """
        default_config = {
            'rsi_period': 14,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'bb_period': 20,
            'bb_std': 2.0,
            'ma_period': 50  # Trend filter - only trade mean reversion in range-bound markets
        }
        
        if config:
            default_config.update(config)
        
        super().__init__("mean_reversion", default_config)
        self.logger = setup_logger(f"{__name__}.{self.name}")
        self.last_signals = {}  # Track last signals per symbol
    
    def _calculate_indicators(self, ohlcv_data: List[Dict]) -> Dict:
        """Calculate technical indicators from OHLCV data"""
        if len(ohlcv_data) < max(self.config['bb_period'], self.config['ma_period']):
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
        
        # Calculate Bollinger Bands
        ma = df['close'].rolling(window=self.config['bb_period']).mean()
        std = df['close'].rolling(window=self.config['bb_period']).std()
        bb_upper = ma + (std * self.config['bb_std'])
        bb_lower = ma - (std * self.config['bb_std'])
        
        # Calculate trend filter (moving average)
        trend_ma = df['close'].rolling(window=self.config['ma_period']).mean()
        
        # Get latest values
        latest_idx = -1
        
        indicators = {
            'rsi': float(rsi.iloc[latest_idx]) if len(rsi) > 0 and not pd.isna(rsi.iloc[latest_idx]) else None,
            'bb_upper': float(bb_upper.iloc[latest_idx]) if not pd.isna(bb_upper.iloc[latest_idx]) else None,
            'bb_lower': float(bb_lower.iloc[latest_idx]) if not pd.isna(bb_lower.iloc[latest_idx]) else None,
            'bb_middle': float(ma.iloc[latest_idx]) if not pd.isna(ma.iloc[latest_idx]) else None,
            'trend_ma': float(trend_ma.iloc[latest_idx]) if not pd.isna(trend_ma.iloc[latest_idx]) else None,
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
    
    def _is_range_bound(self, indicators: Dict) -> bool:
        """Check if market is range-bound (suitable for mean reversion)"""
        price = indicators.get('price')
        trend_ma = indicators.get('trend_ma')
        
        if not price or not trend_ma:
            return False
        
        # If price is close to trend MA, market is likely range-bound
        # If price is far from trend MA, market is trending (not good for mean reversion)
        deviation = abs(price - trend_ma) / trend_ma
        return deviation < 0.05  # Within 5% of trend MA
    
    def should_buy(self, market_data: Dict) -> bool:
        """
        Determine if buy signal should be generated.
        
        Entry conditions:
        - RSI < oversold threshold (e.g., < 30)
        - Price touches or goes below lower Bollinger Band
        - Market is range-bound (not in strong trend)
        """
        symbol = market_data.get('symbol', '')
        ohlcv_data = market_data.get('ohlcv', [])
        
        if not ohlcv_data:
            return False
        
        indicators = self._calculate_indicators(ohlcv_data)
        
        if not indicators:
            return False
        
        # Check if market is range-bound (mean reversion works best in ranges)
        if not self._is_range_bound(indicators):
            return False
        
        price = indicators.get('price')
        rsi = indicators.get('rsi')
        bb_lower = indicators.get('bb_lower')
        
        # Buy signal: RSI oversold AND price at or below lower Bollinger Band
        buy_signal = False
        
        if rsi is not None and rsi < self.config['rsi_oversold']:
            if bb_lower and price <= bb_lower:
                buy_signal = True
        
        # Update last signals
        self.last_signals[symbol] = {
            'rsi': rsi,
            'price': price,
            'bb_lower': bb_lower
        }
        
        return buy_signal
    
    def should_sell(self, market_data: Dict, position: Dict) -> bool:
        """
        Determine if sell signal should be generated.
        
        Exit conditions:
        - RSI > overbought threshold (e.g., > 70)
        - Price touches or goes above upper Bollinger Band
        - Price returns to mean (Bollinger Band middle)
        """
        symbol = market_data.get('symbol', '')
        ohlcv_data = market_data.get('ohlcv', [])
        
        if not ohlcv_data:
            return False
        
        indicators = self._calculate_indicators(ohlcv_data)
        
        if not indicators:
            return False
        
        price = indicators.get('price')
        rsi = indicators.get('rsi')
        bb_upper = indicators.get('bb_upper')
        bb_middle = indicators.get('bb_middle')
        entry_price = Decimal(str(position.get('entry_price', 0)))
        
        # Sell signal conditions
        sell_signal = False
        
        # Condition 1: RSI overbought AND price at or above upper Bollinger Band
        if rsi is not None and rsi > self.config['rsi_overbought']:
            if bb_upper and price >= bb_upper:
                sell_signal = True
        
        # Condition 2: Price returns to mean (profit taking)
        if bb_middle and entry_price > 0:
            # If we bought below the mean and price returns to mean, take profit
            if float(entry_price) < bb_middle and price >= bb_middle:
                sell_signal = True
        
        # Update last signals
        self.last_signals[symbol] = {
            'rsi': rsi,
            'price': price,
            'bb_upper': bb_upper
        }
        
        return sell_signal
    
    def calculate_position_size(self, balance: Decimal, price: Decimal, risk_percent: float) -> Decimal:
        """Calculate position size based on risk percentage"""
        if price <= 0:
            return Decimal('0')
        
        position_value = balance * Decimal(str(risk_percent))
        position_size = position_value / price
        
        return position_size

