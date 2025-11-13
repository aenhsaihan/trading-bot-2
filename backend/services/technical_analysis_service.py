"""Technical analysis service for detecting trading signals"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.services.price_service import get_price_service
from src.utils.logger import setup_logger


class TechnicalSignal:
    """Represents a technical analysis signal"""
    
    def __init__(
        self,
        signal_type: str,
        symbol: str,
        direction: str,  # 'bullish' or 'bearish'
        confidence: float,  # 0-100
        indicators: Dict[str, Any],
        description: str,
        metadata: Optional[Dict] = None
    ):
        self.signal_type = signal_type
        self.symbol = symbol
        self.direction = direction
        self.confidence = confidence
        self.indicators = indicators
        self.description = description
        self.metadata = metadata or {}
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict:
        """Convert signal to dictionary"""
        return {
            'signal_type': self.signal_type,
            'symbol': self.symbol,
            'direction': self.direction,
            'confidence': self.confidence,
            'indicators': self.indicators,
            'description': self.description,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat()
        }


class TechnicalAnalysisService:
    """Service for technical analysis and signal detection"""
    
    def __init__(self, exchange_name: str = "binance"):
        """
        Initialize technical analysis service.
        
        Args:
            exchange_name: Exchange to use ('binance', 'coinbase', 'kraken')
        """
        self.price_service = get_price_service(exchange_name)
        self.logger = setup_logger(f"{__name__}.TechnicalAnalysisService")
        self.last_indicators = {}  # Cache last indicators per symbol
    
    def calculate_indicators(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 200
    ) -> Dict[str, Any]:
        """
        Calculate technical indicators for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Timeframe ('1m', '5m', '15m', '1h', '4h', '1d', etc.)
            limit: Number of candles to fetch
            
        Returns:
            Dictionary with calculated indicators
        """
        try:
            # Get OHLCV data
            ohlcv_data = self.price_service.get_ohlcv(symbol, timeframe, limit)
            
            if not ohlcv_data or len(ohlcv_data) < 50:
                self.logger.warning(f"Insufficient data for {symbol}: {len(ohlcv_data) if ohlcv_data else 0} candles")
                return {}
            
            # Convert to DataFrame
            df = pd.DataFrame(ohlcv_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Convert Decimal to float
            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col in df.columns:
                    df[col] = df[col].astype(float)
            
            # Calculate indicators
            indicators = {}
            
            # Price
            indicators['price'] = float(df['close'].iloc[-1])
            indicators['open'] = float(df['open'].iloc[-1])
            indicators['high'] = float(df['high'].iloc[-1])
            indicators['low'] = float(df['low'].iloc[-1])
            
            # Moving Averages
            indicators['ma_20'] = float(df['close'].rolling(window=20).mean().iloc[-1]) if len(df) >= 20 else None
            indicators['ma_50'] = float(df['close'].rolling(window=50).mean().iloc[-1]) if len(df) >= 50 else None
            indicators['ma_200'] = float(df['close'].rolling(window=200).mean().iloc[-1]) if len(df) >= 200 else None
            
            # RSI
            indicators['rsi'] = self._calculate_rsi(df['close'], period=14)
            
            # MACD
            macd_line, macd_signal = self._calculate_macd(df['close'])
            indicators['macd'] = float(macd_line.iloc[-1]) if len(macd_line) > 0 and not pd.isna(macd_line.iloc[-1]) else None
            indicators['macd_signal'] = float(macd_signal.iloc[-1]) if len(macd_signal) > 0 and not pd.isna(macd_signal.iloc[-1]) else None
            indicators['macd_histogram'] = (indicators['macd'] - indicators['macd_signal']) if indicators['macd'] and indicators['macd_signal'] else None
            
            # Bollinger Bands
            if len(df) >= 20:
                bb_period = 20
                bb_std = 2
                bb_middle = df['close'].rolling(window=bb_period).mean()
                bb_std_dev = df['close'].rolling(window=bb_period).std()
                indicators['bb_upper'] = float((bb_middle + bb_std * bb_std_dev).iloc[-1])
                indicators['bb_lower'] = float((bb_middle - bb_std * bb_std_dev).iloc[-1])
                indicators['bb_middle'] = float(bb_middle.iloc[-1])
            else:
                indicators['bb_upper'] = None
                indicators['bb_lower'] = None
                indicators['bb_middle'] = None
            
            # Volume
            indicators['volume'] = float(df['volume'].iloc[-1])
            indicators['volume_ma'] = float(df['volume'].rolling(window=20).mean().iloc[-1]) if len(df) >= 20 else None
            indicators['volume_ratio'] = (indicators['volume'] / indicators['volume_ma']) if indicators['volume_ma'] and indicators['volume_ma'] > 0 else None
            
            # Price change
            if len(df) >= 2:
                indicators['price_change'] = float(df['close'].iloc[-1] - df['close'].iloc[-2])
                indicators['price_change_pct'] = float((df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2] * 100)
            
            # Store for comparison
            self.last_indicators[symbol] = indicators.copy()
            
            return indicators
            
        except Exception as e:
            self.logger.error(f"Error calculating indicators for {symbol}: {e}", exc_info=True)
            return {}
    
    def detect_signals(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 200
    ) -> List[TechnicalSignal]:
        """
        Detect trading signals from technical analysis.
        
        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe for analysis
            limit: Number of candles to analyze
            
        Returns:
            List of detected signals
        """
        signals = []
        
        try:
            # Get current indicators
            current_indicators = self.calculate_indicators(symbol, timeframe, limit)
            
            if not current_indicators:
                return signals
            
            # Get previous indicators for comparison
            previous_indicators = self.last_indicators.get(symbol, {})
            
            # Get OHLCV for pattern detection
            ohlcv_data = self.price_service.get_ohlcv(symbol, timeframe, limit)
            if not ohlcv_data:
                return signals
            
            # 1. RSI Signals
            rsi_signals = self._detect_rsi_signals(symbol, current_indicators, previous_indicators)
            signals.extend(rsi_signals)
            
            # 2. MACD Signals
            macd_signals = self._detect_macd_signals(symbol, current_indicators, previous_indicators)
            signals.extend(macd_signals)
            
            # 3. Moving Average Crossover Signals
            ma_signals = self._detect_ma_crossover_signals(symbol, current_indicators, previous_indicators)
            signals.extend(ma_signals)
            
            # 4. Bollinger Band Signals
            bb_signals = self._detect_bollinger_signals(symbol, current_indicators, previous_indicators)
            signals.extend(bb_signals)
            
            # 5. Volume Anomaly Signals
            volume_signals = self._detect_volume_signals(symbol, current_indicators, previous_indicators)
            signals.extend(volume_signals)
            
            # 6. Breakout Signals
            breakout_signals = self._detect_breakout_signals(symbol, current_indicators, ohlcv_data)
            signals.extend(breakout_signals)
            
            # 7. Reversal Signals
            reversal_signals = self._detect_reversal_signals(symbol, current_indicators, ohlcv_data)
            signals.extend(reversal_signals)
            
        except Exception as e:
            self.logger.error(f"Error detecting signals for {symbol}: {e}", exc_info=True)
        
        return signals
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> Optional[float]:
        """Calculate RSI (Relative Strength Index)"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            rsi_value = float(rsi.iloc[-1]) if len(rsi) > 0 and not pd.isna(rsi.iloc[-1]) else None
            return rsi_value
        except Exception:
            return None
    
    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        macd_signal = macd_line.ewm(span=signal, adjust=False).mean()
        return macd_line, macd_signal
    
    def _detect_rsi_signals(
        self,
        symbol: str,
        current: Dict,
        previous: Dict
    ) -> List[TechnicalSignal]:
        """Detect RSI-based signals"""
        signals = []
        rsi = current.get('rsi')
        
        if rsi is None:
            return signals
        
        # Overbought/Oversold
        if rsi > 70:
            confidence = min(85, 50 + (rsi - 70) * 1.5)  # Higher RSI = higher confidence
            signals.append(TechnicalSignal(
                signal_type="rsi_overbought",
                symbol=symbol,
                direction="bearish",
                confidence=confidence,
                indicators=current,
                description=f"RSI overbought at {rsi:.2f} - potential reversal",
                metadata={'rsi': rsi, 'threshold': 70}
            ))
        elif rsi < 30:
            confidence = min(85, 50 + (30 - rsi) * 1.5)  # Lower RSI = higher confidence
            signals.append(TechnicalSignal(
                signal_type="rsi_oversold",
                symbol=symbol,
                direction="bullish",
                confidence=confidence,
                indicators=current,
                description=f"RSI oversold at {rsi:.2f} - potential reversal",
                metadata={'rsi': rsi, 'threshold': 30}
            ))
        
        # RSI Divergence (simplified - would need more data for full detection)
        prev_rsi = previous.get('rsi')
        if prev_rsi and abs(rsi - prev_rsi) > 10:
            if rsi < prev_rsi and current.get('price', 0) > previous.get('price', 0):
                # Bearish divergence
                signals.append(TechnicalSignal(
                    signal_type="rsi_divergence",
                    symbol=symbol,
                    direction="bearish",
                    confidence=65,
                    indicators=current,
                    description=f"RSI bearish divergence detected",
                    metadata={'rsi': rsi, 'prev_rsi': prev_rsi}
                ))
            elif rsi > prev_rsi and current.get('price', 0) < previous.get('price', 0):
                # Bullish divergence
                signals.append(TechnicalSignal(
                    signal_type="rsi_divergence",
                    symbol=symbol,
                    direction="bullish",
                    confidence=65,
                    indicators=current,
                    description=f"RSI bullish divergence detected",
                    metadata={'rsi': rsi, 'prev_rsi': prev_rsi}
                ))
        
        return signals
    
    def _detect_macd_signals(
        self,
        symbol: str,
        current: Dict,
        previous: Dict
    ) -> List[TechnicalSignal]:
        """Detect MACD-based signals"""
        signals = []
        
        macd = current.get('macd')
        macd_signal = current.get('macd_signal')
        macd_hist = current.get('macd_histogram')
        
        prev_macd = previous.get('macd')
        prev_macd_signal = previous.get('macd_signal')
        prev_macd_hist = previous.get('macd_histogram')
        
        if macd is None or macd_signal is None:
            return signals
        
        # MACD Crossover
        if prev_macd is not None and prev_macd_signal is not None:
            # Bullish crossover: MACD crosses above signal
            if prev_macd <= prev_macd_signal and macd > macd_signal:
                confidence = min(80, 60 + abs(macd - macd_signal) * 10)
                signals.append(TechnicalSignal(
                    signal_type="macd_crossover",
                    symbol=symbol,
                    direction="bullish",
                    confidence=confidence,
                    indicators=current,
                    description=f"MACD bullish crossover - MACD ({macd:.4f}) crossed above signal ({macd_signal:.4f})",
                    metadata={'macd': macd, 'macd_signal': macd_signal}
                ))
            # Bearish crossover: MACD crosses below signal
            elif prev_macd >= prev_macd_signal and macd < macd_signal:
                confidence = min(80, 60 + abs(macd - macd_signal) * 10)
                signals.append(TechnicalSignal(
                    signal_type="macd_crossover",
                    symbol=symbol,
                    direction="bearish",
                    confidence=confidence,
                    indicators=current,
                    description=f"MACD bearish crossover - MACD ({macd:.4f}) crossed below signal ({macd_signal:.4f})",
                    metadata={'macd': macd, 'macd_signal': macd_signal}
                ))
        
        # MACD Histogram momentum
        if macd_hist is not None and prev_macd_hist is not None:
            if macd_hist > 0 and prev_macd_hist < 0:
                # Histogram turned positive
                signals.append(TechnicalSignal(
                    signal_type="macd_momentum",
                    symbol=symbol,
                    direction="bullish",
                    confidence=70,
                    indicators=current,
                    description="MACD histogram turned positive - bullish momentum",
                    metadata={'macd_histogram': macd_hist}
                ))
            elif macd_hist < 0 and prev_macd_hist > 0:
                # Histogram turned negative
                signals.append(TechnicalSignal(
                    signal_type="macd_momentum",
                    symbol=symbol,
                    direction="bearish",
                    confidence=70,
                    indicators=current,
                    description="MACD histogram turned negative - bearish momentum",
                    metadata={'macd_histogram': macd_hist}
                ))
        
        return signals
    
    def _detect_ma_crossover_signals(
        self,
        symbol: str,
        current: Dict,
        previous: Dict
    ) -> List[TechnicalSignal]:
        """Detect moving average crossover signals"""
        signals = []
        
        ma_20 = current.get('ma_20')
        ma_50 = current.get('ma_50')
        ma_200 = current.get('ma_200')
        price = current.get('price')
        
        prev_ma_20 = previous.get('ma_20')
        prev_ma_50 = previous.get('ma_50')
        prev_ma_200 = previous.get('ma_200')
        
        # Golden Cross: Short MA crosses above Long MA
        if ma_20 and ma_50 and prev_ma_20 and prev_ma_50:
            if prev_ma_20 <= prev_ma_50 and ma_20 > ma_50:
                confidence = min(85, 70 + abs(ma_20 - ma_50) / price * 1000 if price else 70)
                signals.append(TechnicalSignal(
                    signal_type="golden_cross",
                    symbol=symbol,
                    direction="bullish",
                    confidence=confidence,
                    indicators=current,
                    description=f"Golden Cross: MA20 ({ma_20:.2f}) crossed above MA50 ({ma_50:.2f})",
                    metadata={'ma_20': ma_20, 'ma_50': ma_50}
                ))
            # Death Cross: Short MA crosses below Long MA
            elif prev_ma_20 >= prev_ma_50 and ma_20 < ma_50:
                confidence = min(85, 70 + abs(ma_20 - ma_50) / price * 1000 if price else 70)
                signals.append(TechnicalSignal(
                    signal_type="death_cross",
                    symbol=symbol,
                    direction="bearish",
                    confidence=confidence,
                    indicators=current,
                    description=f"Death Cross: MA20 ({ma_20:.2f}) crossed below MA50 ({ma_50:.2f})",
                    metadata={'ma_20': ma_20, 'ma_50': ma_50}
                ))
        
        # Price crossing MA200 (major trend indicator)
        if ma_200 and price and prev_ma_200:
            if price > ma_200 and previous.get('price', 0) <= prev_ma_200:
                signals.append(TechnicalSignal(
                    signal_type="price_above_ma200",
                    symbol=symbol,
                    direction="bullish",
                    confidence=75,
                    indicators=current,
                    description=f"Price crossed above MA200 ({ma_200:.2f}) - major bullish signal",
                    metadata={'price': price, 'ma_200': ma_200}
                ))
            elif price < ma_200 and previous.get('price', 0) >= prev_ma_200:
                signals.append(TechnicalSignal(
                    signal_type="price_below_ma200",
                    symbol=symbol,
                    direction="bearish",
                    confidence=75,
                    indicators=current,
                    description=f"Price crossed below MA200 ({ma_200:.2f}) - major bearish signal",
                    metadata={'price': price, 'ma_200': ma_200}
                ))
        
        return signals
    
    def _detect_bollinger_signals(
        self,
        symbol: str,
        current: Dict,
        previous: Dict
    ) -> List[TechnicalSignal]:
        """Detect Bollinger Band signals"""
        signals = []
        
        price = current.get('price')
        bb_upper = current.get('bb_upper')
        bb_lower = current.get('bb_lower')
        bb_middle = current.get('bb_middle')
        
        if not all([price, bb_upper, bb_lower, bb_middle]):
            return signals
        
        prev_price = previous.get('price')
        
        # Price touches or breaks upper band
        if price >= bb_upper:
            confidence = min(80, 60 + (price - bb_upper) / bb_upper * 100)
            signals.append(TechnicalSignal(
                signal_type="bollinger_upper_breakout",
                symbol=symbol,
                direction="bullish",
                confidence=confidence,
                indicators=current,
                description=f"Price broke above Bollinger upper band ({bb_upper:.2f})",
                metadata={'price': price, 'bb_upper': bb_upper}
            ))
        # Price touches or breaks lower band
        elif price <= bb_lower:
            confidence = min(80, 60 + (bb_lower - price) / bb_lower * 100)
            signals.append(TechnicalSignal(
                signal_type="bollinger_lower_breakout",
                symbol=symbol,
                direction="bullish",  # Oversold = potential bounce
                confidence=confidence,
                indicators=current,
                description=f"Price broke below Bollinger lower band ({bb_lower:.2f}) - potential reversal",
                metadata={'price': price, 'bb_lower': bb_lower}
            ))
        
        # Squeeze (bands narrowing) - potential volatility expansion
        if prev_price:
            prev_bb_upper = previous.get('bb_upper')
            prev_bb_lower = previous.get('bb_lower')
            if prev_bb_upper and prev_bb_lower:
                current_width = bb_upper - bb_lower
                prev_width = prev_bb_upper - prev_bb_lower
                if prev_width > 0:
                    width_ratio = current_width / prev_width
                    if width_ratio < 0.8:  # Bands narrowed by 20%+
                        signals.append(TechnicalSignal(
                            signal_type="bollinger_squeeze",
                            symbol=symbol,
                            direction="neutral",  # Direction depends on breakout
                            confidence=60,
                            indicators=current,
                            description="Bollinger Band squeeze detected - potential volatility expansion",
                            metadata={'width_ratio': width_ratio}
                        ))
        
        return signals
    
    def _detect_volume_signals(
        self,
        symbol: str,
        current: Dict,
        previous: Dict
    ) -> List[TechnicalSignal]:
        """Detect volume anomaly signals"""
        signals = []
        
        volume_ratio = current.get('volume_ratio')
        price_change_pct = current.get('price_change_pct', 0)
        
        if volume_ratio is None:
            return signals
        
        # High volume with price movement
        if volume_ratio > 2.0:  # Volume 2x average
            if price_change_pct > 2:
                confidence = min(85, 70 + volume_ratio * 5)
                signals.append(TechnicalSignal(
                    signal_type="volume_surge_bullish",
                    symbol=symbol,
                    direction="bullish",
                    confidence=confidence,
                    indicators=current,
                    description=f"High volume surge ({volume_ratio:.2f}x) with price increase ({price_change_pct:.2f}%)",
                    metadata={'volume_ratio': volume_ratio, 'price_change_pct': price_change_pct}
                ))
            elif price_change_pct < -2:
                confidence = min(85, 70 + volume_ratio * 5)
                signals.append(TechnicalSignal(
                    signal_type="volume_surge_bearish",
                    symbol=symbol,
                    direction="bearish",
                    confidence=confidence,
                    indicators=current,
                    description=f"High volume surge ({volume_ratio:.2f}x) with price decrease ({price_change_pct:.2f}%)",
                    metadata={'volume_ratio': volume_ratio, 'price_change_pct': price_change_pct}
                ))
        
        # Low volume (potential consolidation)
        elif volume_ratio < 0.5:
            signals.append(TechnicalSignal(
                signal_type="volume_drop",
                symbol=symbol,
                direction="neutral",
                confidence=50,
                indicators=current,
                description=f"Low volume ({volume_ratio:.2f}x average) - potential consolidation",
                metadata={'volume_ratio': volume_ratio}
            ))
        
        return signals
    
    def _detect_breakout_signals(
        self,
        symbol: str,
        current: Dict,
        ohlcv_data: List[Dict]
    ) -> List[TechnicalSignal]:
        """Detect price breakout signals"""
        signals = []
        
        if len(ohlcv_data) < 20:
            return signals
        
        try:
            # Convert to DataFrame
            df = pd.DataFrame(ohlcv_data)
            for col in ['open', 'high', 'low', 'close']:
                if col in df.columns:
                    df[col] = df[col].astype(float)
            
            current_price = current.get('price')
            if not current_price:
                return signals
            
            # Resistance/Support levels (simplified - using recent highs/lows)
            recent_high = float(df['high'].tail(20).max())
            recent_low = float(df['low'].tail(20).min())
            
            # Breakout above resistance
            if current_price > recent_high * 0.98:  # Within 2% of recent high
                signals.append(TechnicalSignal(
                    signal_type="resistance_breakout",
                    symbol=symbol,
                    direction="bullish",
                    confidence=75,
                    indicators=current,
                    description=f"Price breaking above recent resistance ({recent_high:.2f})",
                    metadata={'price': current_price, 'resistance': recent_high}
                ))
            
            # Breakdown below support
            if current_price < recent_low * 1.02:  # Within 2% of recent low
                signals.append(TechnicalSignal(
                    signal_type="support_breakdown",
                    symbol=symbol,
                    direction="bearish",
                    confidence=75,
                    indicators=current,
                    description=f"Price breaking below recent support ({recent_low:.2f})",
                    metadata={'price': current_price, 'support': recent_low}
                ))
            
        except Exception as e:
            self.logger.error(f"Error detecting breakouts for {symbol}: {e}")
        
        return signals
    
    def _detect_reversal_signals(
        self,
        symbol: str,
        current: Dict,
        ohlcv_data: List[Dict]
    ) -> List[TechnicalSignal]:
        """Detect price reversal signals"""
        signals = []
        
        if len(ohlcv_data) < 10:
            return signals
        
        try:
            # Convert to DataFrame
            df = pd.DataFrame(ohlcv_data)
            for col in ['open', 'high', 'low', 'close']:
                if col in df.columns:
                    df[col] = df[col].astype(float)
            
            # Look for candlestick patterns (simplified)
            recent = df.tail(5)
            
            # Hammer pattern (potential bullish reversal)
            if len(recent) >= 1:
                last = recent.iloc[-1]
                body = abs(last['close'] - last['open'])
                lower_shadow = min(last['open'], last['close']) - last['low']
                upper_shadow = last['high'] - max(last['open'], last['close'])
                
                if lower_shadow > body * 2 and upper_shadow < body * 0.5:
                    signals.append(TechnicalSignal(
                        signal_type="hammer_pattern",
                        symbol=symbol,
                        direction="bullish",
                        confidence=65,
                        indicators=current,
                        description="Hammer candlestick pattern detected - potential bullish reversal",
                        metadata={'pattern': 'hammer'}
                    ))
            
            # Doji pattern (indecision, potential reversal)
            if len(recent) >= 1:
                last = recent.iloc[-1]
                body = abs(last['close'] - last['open'])
                total_range = last['high'] - last['low']
                
                if total_range > 0 and body / total_range < 0.1:  # Small body relative to range
                    signals.append(TechnicalSignal(
                        signal_type="doji_pattern",
                        symbol=symbol,
                        direction="neutral",
                        confidence=55,
                        indicators=current,
                        description="Doji candlestick pattern detected - market indecision",
                        metadata={'pattern': 'doji'}
                    ))
            
        except Exception as e:
            self.logger.error(f"Error detecting reversals for {symbol}: {e}")
        
        return signals


