"""Signal generator - combines signals from multiple sources and generates notifications"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.services.technical_analysis_service import TechnicalSignal, TechnicalAnalysisService
from backend.services.notification_service import NotificationService
from src.notifications.notification_types import (
    NotificationType,
    NotificationPriority,
    NotificationSource
)
from src.utils.logger import setup_logger


class CombinedSignal:
    """Represents a combined signal from multiple sources"""
    
    def __init__(
        self,
        symbol: str,
        direction: str,  # 'bullish', 'bearish', or 'neutral'
        confidence: float,  # 0-100
        urgency: float,  # 0-100
        promise: float,  # 0-100
        source_signals: List[TechnicalSignal],
        description: str,
        metadata: Optional[Dict] = None
    ):
        self.symbol = symbol
        self.direction = direction
        self.confidence = confidence
        self.urgency = urgency
        self.promise = promise
        self.source_signals = source_signals
        self.description = description
        self.metadata = metadata or {}
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict:
        """Convert combined signal to dictionary"""
        return {
            'symbol': self.symbol,
            'direction': self.direction,
            'confidence': self.confidence,
            'urgency': self.urgency,
            'promise': self.promise,
            'source_signals': [s.to_dict() for s in self.source_signals],
            'description': self.description,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat()
        }


class SignalGenerator:
    """Generates notifications from technical signals"""
    
    def __init__(self):
        """Initialize signal generator"""
        self.technical_service = TechnicalAnalysisService()
        self.notification_service = NotificationService()
        self.logger = setup_logger(f"{__name__}.SignalGenerator")
        
        # Signal history to avoid duplicate notifications
        self.recent_signals = {}  # symbol -> list of recent signal timestamps
        self.signal_cooldown = timedelta(minutes=15)  # Don't repeat same signal within 15 min
    
    def generate_notifications(
        self,
        symbols: List[str],
        timeframe: str = "1h"
    ) -> List[Dict]:
        """
        Generate notifications from signals for given symbols.
        
        Args:
            symbols: List of trading pair symbols to analyze
            timeframe: Timeframe for analysis
            
        Returns:
            List of created notification dictionaries
        """
        notifications = []
        
        for symbol in symbols:
            try:
                # Detect technical signals
                signals = self.technical_service.detect_signals(symbol, timeframe)
                
                if not signals:
                    continue
                
                # Combine signals
                combined = self._combine_signals(symbol, signals)
                
                if combined:
                    # Generate notification from combined signal
                    notification = self._create_notification_from_signal(combined)
                    if notification:
                        notifications.append(notification.to_dict())
                
            except Exception as e:
                self.logger.error(f"Error generating notifications for {symbol}: {e}", exc_info=True)
        
        return notifications
    
    def _combine_signals(
        self,
        symbol: str,
        signals: List[TechnicalSignal]
    ) -> Optional[CombinedSignal]:
        """
        Combine multiple signals into a single combined signal.
        
        Args:
            symbol: Trading pair symbol
            signals: List of detected signals
            
        Returns:
            Combined signal or None if not significant enough
        """
        if not signals:
            return None
        
        # Filter out duplicate/cooldown signals
        filtered_signals = self._filter_recent_signals(symbol, signals)
        
        if not filtered_signals:
            return None
        
        # Group signals by direction
        bullish_signals = [s for s in filtered_signals if s.direction == 'bullish']
        bearish_signals = [s for s in filtered_signals if s.direction == 'bearish']
        neutral_signals = [s for s in filtered_signals if s.direction == 'neutral']
        
        # Determine overall direction
        if len(bullish_signals) > len(bearish_signals):
            direction = 'bullish'
            primary_signals = bullish_signals
        elif len(bearish_signals) > len(bullish_signals):
            direction = 'bearish'
            primary_signals = bearish_signals
        else:
            # Mixed signals - use highest confidence
            if bullish_signals and bearish_signals:
                max_bull = max([s.confidence for s in bullish_signals])
                max_bear = max([s.confidence for s in bearish_signals])
                if max_bull > max_bear:
                    direction = 'bullish'
                    primary_signals = bullish_signals
                else:
                    direction = 'bearish'
                    primary_signals = bearish_signals
            elif neutral_signals:
                direction = 'neutral'
                primary_signals = neutral_signals
            else:
                return None  # No clear direction
        
        # Calculate combined confidence (weighted average, with bonus for multiple signals)
        if primary_signals:
            base_confidence = sum([s.confidence for s in primary_signals]) / len(primary_signals)
            # Bonus for multiple confirming signals
            signal_count_bonus = min(15, len(primary_signals) * 3)
            confidence = min(100, base_confidence + signal_count_bonus)
        else:
            confidence = 50
        
        # Calculate urgency (based on signal types and price movement)
        urgency = self._calculate_urgency(primary_signals, symbol)
        
        # Calculate promise (opportunity score)
        promise = self._calculate_promise(primary_signals, symbol, direction)
        
        # Only create notification if confidence is above threshold
        if confidence < 55:  # Minimum confidence threshold
            return None
        
        # Build description
        description = self._build_description(primary_signals, direction, symbol)
        
        # Build metadata
        metadata = {
            'signal_count': len(primary_signals),
            'signal_types': [s.signal_type for s in primary_signals],
            'indicators': primary_signals[0].indicators if primary_signals else {}
        }
        
        combined = CombinedSignal(
            symbol=symbol,
            direction=direction,
            confidence=confidence,
            urgency=urgency,
            promise=promise,
            source_signals=primary_signals,
            description=description,
            metadata=metadata
        )
        
        # Record signal to avoid duplicates
        self._record_signal(symbol, combined)
        
        return combined
    
    def _filter_recent_signals(
        self,
        symbol: str,
        signals: List[TechnicalSignal]
    ) -> List[TechnicalSignal]:
        """Filter out signals that were recently generated"""
        if symbol not in self.recent_signals:
            return signals
        
        recent_times = self.recent_signals[symbol]
        now = datetime.now()
        
        filtered = []
        for signal in signals:
            # Check if similar signal was generated recently
            is_duplicate = False
            for recent_time, recent_signal in recent_times:
                if (now - recent_time) < self.signal_cooldown:
                    # Check if same signal type
                    if signal.signal_type == recent_signal.signal_type:
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                filtered.append(signal)
        
        return filtered
    
    def _calculate_urgency(
        self,
        signals: List[TechnicalSignal],
        symbol: str
    ) -> float:
        """
        Calculate urgency score (0-100) based on signal characteristics.
        
        Higher urgency for:
        - Breakout signals
        - Volume surges
        - Strong RSI extremes
        - MACD crossovers
        """
        if not signals:
            return 50
        
        urgency_scores = []
        
        for signal in signals:
            signal_urgency = 50  # Base urgency
            
            # Breakout signals are urgent
            if 'breakout' in signal.signal_type or 'breakdown' in signal.signal_type:
                signal_urgency = 80
            
            # Volume surges are urgent
            elif 'volume' in signal.signal_type:
                signal_urgency = 75
            
            # RSI extremes are moderately urgent
            elif 'rsi' in signal.signal_type:
                rsi = signal.metadata.get('rsi', 50)
                if rsi > 75 or rsi < 25:
                    signal_urgency = 70
                else:
                    signal_urgency = 60
            
            # MACD crossovers are moderately urgent
            elif 'macd' in signal.signal_type:
                signal_urgency = 65
            
            # Moving average crossovers are less urgent
            elif 'cross' in signal.signal_type or 'ma' in signal.signal_type:
                signal_urgency = 55
            
            urgency_scores.append(signal_urgency)
        
        # Average urgency, with bonus for multiple signals
        avg_urgency = sum(urgency_scores) / len(urgency_scores) if urgency_scores else 50
        multi_signal_bonus = min(10, len(signals) * 2)
        
        return min(100, avg_urgency + multi_signal_bonus)
    
    def _calculate_promise(
        self,
        signals: List[TechnicalSignal],
        symbol: str,
        direction: str
    ) -> float:
        """
        Calculate promise/opportunity score (0-100) based on signal strength.
        
        Higher promise for:
        - High confidence signals
        - Multiple confirming signals
        - Strong technical patterns
        """
        if not signals:
            return 50
        
        # Base promise from signal confidence
        avg_confidence = sum([s.confidence for s in signals]) / len(signals)
        
        # Bonus for multiple signals
        signal_count_bonus = min(20, len(signals) * 4)
        
        # Bonus for strong patterns
        pattern_bonus = 0
        for signal in signals:
            if signal.signal_type in ['golden_cross', 'death_cross', 'resistance_breakout', 'support_breakdown']:
                pattern_bonus += 5
        
        promise = min(100, avg_confidence + signal_count_bonus + pattern_bonus)
        
        return promise
    
    def _build_description(
        self,
        signals: List[TechnicalSignal],
        direction: str,
        symbol: str
    ) -> str:
        """Build human-readable description from signals"""
        if not signals:
            return f"Technical signals detected for {symbol}"
        
        signal_descriptions = [s.description for s in signals[:3]]  # Top 3 signals
        
        if len(signals) > 3:
            return f"{direction.upper()} signals detected: {', '.join(signal_descriptions)} (+{len(signals) - 3} more)"
        else:
            return f"{direction.upper()} signals: {', '.join(signal_descriptions)}"
    
    def _record_signal(self, symbol: str, signal: CombinedSignal):
        """Record signal to avoid duplicates"""
        if symbol not in self.recent_signals:
            self.recent_signals[symbol] = []
        
        self.recent_signals[symbol].append((datetime.now(), signal))
        
        # Keep only recent signals (last hour)
        cutoff = datetime.now() - timedelta(hours=1)
        self.recent_signals[symbol] = [
            (t, s) for t, s in self.recent_signals[symbol]
            if t > cutoff
        ]
    
    def _create_notification_from_signal(
        self,
        signal: CombinedSignal
    ) -> Optional[Any]:
        """
        Create a notification from a combined signal.
        
        Args:
            signal: Combined signal to convert
            
        Returns:
            Notification object or None
        """
        try:
            # Determine notification type
            if signal.direction == 'bullish':
                if signal.confidence >= 80:
                    notif_type = NotificationType.TECHNICAL_BREAKOUT
                else:
                    notif_type = NotificationType.TECHNICAL_BREAKOUT
            elif signal.direction == 'bearish':
                notif_type = NotificationType.RISK_ALERT
            else:
                notif_type = NotificationType.TECHNICAL_BREAKOUT  # Default
            
            # Determine priority based on confidence and urgency
            if signal.confidence >= 80 and signal.urgency >= 75:
                priority = NotificationPriority.HIGH
            elif signal.confidence >= 70:
                priority = NotificationPriority.MEDIUM
            else:
                priority = NotificationPriority.LOW
            
            # Build title
            direction_emoji = "📈" if signal.direction == 'bullish' else "📉" if signal.direction == 'bearish' else "📊"
            title = f"{direction_emoji} {signal.direction.upper()} Signal: {signal.symbol}"
            
            # Build message
            message = f"{signal.description}\n\n"
            message += f"Confidence: {signal.confidence:.1f}% | "
            message += f"Urgency: {signal.urgency:.1f}% | "
            message += f"Promise: {signal.promise:.1f}%\n\n"
            message += f"Detected {len(signal.source_signals)} confirming signal(s)"
            
            # Create notification
            notification = self.notification_service.create_notification(
                notification_type=notif_type.value,
                priority=priority.value,
                title=title,
                message=message,
                source=NotificationSource.TECHNICAL.value,
                symbol=signal.symbol,
                confidence_score=signal.confidence,
                urgency_score=signal.urgency,
                promise_score=signal.promise,
                metadata=signal.metadata,
                actions=["analyze", "dismiss"]
            )
            
            self.logger.info(f"Created notification from signal: {title} (confidence: {signal.confidence:.1f}%)")
            
            return notification
            
        except Exception as e:
            self.logger.error(f"Error creating notification from signal: {e}", exc_info=True)
            return None


