"""Alert service for managing and evaluating price and indicator alerts"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from decimal import Decimal
import uuid
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.services.price_service import get_price_service
from backend.services.notification_service import NotificationService
from src.utils.logger import setup_logger


class AlertService:
    """Service for managing and evaluating alerts"""
    
    def __init__(self):
        """Initialize alert service with in-memory storage"""
        self.alerts: Dict[str, Dict] = {}  # alert_id -> alert_data
        self.price_service = get_price_service()
        self.notification_service = NotificationService()
        self.logger = setup_logger(f"{__name__}.AlertService")
        self._last_evaluated: Dict[str, float] = {}  # Track last evaluation time per alert
    
    def create_alert(
        self,
        symbol: str,
        alert_type: str,
        price_threshold: Optional[float] = None,
        price_condition: Optional[str] = None,
        indicator_name: Optional[str] = None,
        indicator_condition: Optional[str] = None,
        indicator_value: Optional[float] = None,
        enabled: bool = True,
        description: Optional[str] = None
    ) -> Dict:
        """
        Create a new alert
        
        Args:
            symbol: Trading pair symbol
            alert_type: 'price' or 'indicator'
            price_threshold: Price threshold for price alerts
            price_condition: 'above' or 'below' for price alerts
            indicator_name: Indicator name (e.g., 'RSI', 'MACD', 'MACD_crossover')
            indicator_condition: Condition for indicator alerts
            indicator_value: Threshold value for indicator alerts
            enabled: Whether alert is enabled
            description: Optional description
            
        Returns:
            Created alert dictionary
        """
        # Validate alert configuration
        if alert_type == "price":
            if price_threshold is None or price_condition is None:
                raise ValueError("Price alerts require price_threshold and price_condition")
        elif alert_type == "indicator":
            if indicator_name is None or indicator_condition is None or indicator_value is None:
                raise ValueError("Indicator alerts require indicator_name, indicator_condition, and indicator_value")
        else:
            raise ValueError(f"Invalid alert_type: {alert_type}. Must be 'price' or 'indicator'")
        
        alert_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        alert = {
            "id": alert_id,
            "symbol": symbol,
            "alert_type": alert_type,
            "price_threshold": price_threshold,
            "price_condition": price_condition,
            "indicator_name": indicator_name,
            "indicator_condition": indicator_condition,
            "indicator_value": indicator_value,
            "enabled": enabled,
            "triggered": False,
            "triggered_at": None,
            "description": description,
            "created_at": now,
            "updated_at": now
        }
        
        self.alerts[alert_id] = alert
        self.logger.info(f"Created alert {alert_id} for {symbol} ({alert_type})")
        
        return alert
    
    def get_alert(self, alert_id: str) -> Optional[Dict]:
        """Get alert by ID"""
        return self.alerts.get(alert_id)
    
    def get_all_alerts(
        self,
        symbol: Optional[str] = None,
        enabled_only: bool = False,
        triggered_only: bool = False
    ) -> List[Dict]:
        """
        Get all alerts with optional filtering
        
        Args:
            symbol: Filter by symbol
            enabled_only: Only return enabled alerts
            triggered_only: Only return triggered alerts
            
        Returns:
            List of alert dictionaries
        """
        alerts = list(self.alerts.values())
        
        if symbol:
            alerts = [a for a in alerts if a["symbol"] == symbol]
        
        if enabled_only:
            alerts = [a for a in alerts if a["enabled"]]
        
        if triggered_only:
            alerts = [a for a in alerts if a["triggered"]]
        
        # Sort by created_at descending
        alerts.sort(key=lambda x: x["created_at"], reverse=True)
        
        return alerts
    
    def update_alert(self, alert_id: str, **updates) -> Optional[Dict]:
        """
        Update an alert
        
        Args:
            alert_id: Alert ID
            **updates: Fields to update
            
        Returns:
            Updated alert dictionary or None if not found
        """
        if alert_id not in self.alerts:
            return None
        
        alert = self.alerts[alert_id]
        
        # Update allowed fields
        allowed_fields = [
            "enabled", "price_threshold", "price_condition",
            "indicator_value", "description"
        ]
        
        for field, value in updates.items():
            if field in allowed_fields:
                alert[field] = value
        
        alert["updated_at"] = datetime.utcnow().isoformat()
        
        # If re-enabling a triggered alert, reset triggered status
        if updates.get("enabled") is True and alert["triggered"]:
            alert["triggered"] = False
            alert["triggered_at"] = None
        
        self.logger.info(f"Updated alert {alert_id}")
        
        return alert
    
    def delete_alert(self, alert_id: str) -> bool:
        """Delete an alert"""
        if alert_id in self.alerts:
            del self.alerts[alert_id]
            if alert_id in self._last_evaluated:
                del self._last_evaluated[alert_id]
            self.logger.info(f"Deleted alert {alert_id}")
            return True
        return False
    
    def _calculate_indicators(self, ohlcv_data: List[Dict]) -> Dict[str, float]:
        """
        Calculate technical indicators from OHLCV data
        
        Args:
            ohlcv_data: List of OHLCV dictionaries
            
        Returns:
            Dictionary of indicator values
        """
        if len(ohlcv_data) < 14:  # Need at least 14 candles for RSI
            return {}
        
        try:
            # Convert to DataFrame
            df = pd.DataFrame(ohlcv_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Convert Decimal to float
            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col in df.columns:
                    df[col] = df[col].astype(float)
            
            indicators = {}
            
            # Calculate RSI
            if len(df) >= 14:
                rsi = self._calculate_rsi(df['close'], 14)
                indicators['RSI'] = float(rsi.iloc[-1]) if len(rsi) > 0 and not pd.isna(rsi.iloc[-1]) else None
            
            # Calculate MACD
            if len(df) >= 26:
                macd_line, macd_signal = self._calculate_macd(df['close'])
                indicators['MACD'] = float(macd_line.iloc[-1]) if len(macd_line) > 0 and not pd.isna(macd_line.iloc[-1]) else None
                indicators['MACD_signal'] = float(macd_signal.iloc[-1]) if len(macd_signal) > 0 and not pd.isna(macd_signal.iloc[-1]) else None
                
                # Check for MACD crossover
                if len(macd_line) >= 2 and len(macd_signal) >= 2:
                    prev_macd = macd_line.iloc[-2]
                    prev_signal = macd_signal.iloc[-2]
                    curr_macd = macd_line.iloc[-1]
                    curr_signal = macd_signal.iloc[-1]
                    
                    # Bullish crossover: MACD crosses above signal
                    if prev_macd <= prev_signal and curr_macd > curr_signal:
                        indicators['MACD_crossover'] = 1  # Bullish
                    # Bearish crossover: MACD crosses below signal
                    elif prev_macd >= prev_signal and curr_macd < curr_signal:
                        indicators['MACD_crossover'] = -1  # Bearish
                    else:
                        indicators['MACD_crossover'] = 0  # No crossover
            
            # Calculate Moving Averages
            if len(df) >= 50:
                ma50 = df['close'].rolling(window=50).mean()
                indicators['MA_50'] = float(ma50.iloc[-1]) if not pd.isna(ma50.iloc[-1]) else None
            
            if len(df) >= 200:
                ma200 = df['close'].rolling(window=200).mean()
                indicators['MA_200'] = float(ma200.iloc[-1]) if not pd.isna(ma200.iloc[-1]) else None
            
            return {k: v for k, v in indicators.items() if v is not None}
        except Exception as e:
            self.logger.error(f"Error calculating indicators: {e}", exc_info=True)
            return {}
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI (Relative Strength Index)"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_macd(
        self,
        prices: pd.Series,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> tuple[pd.Series, pd.Series]:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        macd_signal = macd_line.ewm(span=signal, adjust=False).mean()
        return macd_line, macd_signal
    
    def evaluate_alert(self, alert: Dict) -> bool:
        """
        Evaluate a single alert to see if it should trigger
        
        Args:
            alert: Alert dictionary
            
        Returns:
            True if alert should trigger, False otherwise
        """
        if not alert["enabled"] or alert["triggered"]:
            return False
        
        symbol = alert["symbol"]
        alert_type = alert["alert_type"]
        
        try:
            if alert_type == "price":
                return self._evaluate_price_alert(alert)
            elif alert_type == "indicator":
                return self._evaluate_indicator_alert(alert)
            else:
                self.logger.warning(f"Unknown alert type: {alert_type}")
                return False
        except Exception as e:
            self.logger.error(f"Error evaluating alert {alert['id']}: {e}", exc_info=True)
            return False
    
    def _evaluate_price_alert(self, alert: Dict) -> bool:
        """Evaluate a price alert"""
        symbol = alert["symbol"]
        threshold = alert["price_threshold"]
        condition = alert["price_condition"]
        
        try:
            price = self.price_service.get_current_price(symbol)
            if price == 0:
                return False
            
            price_float = float(price)
            
            if condition == "above":
                return price_float >= threshold
            elif condition == "below":
                return price_float <= threshold
            else:
                return False
        except Exception as e:
            self.logger.error(f"Error evaluating price alert: {e}")
            return False
    
    def _evaluate_indicator_alert(self, alert: Dict) -> bool:
        """Evaluate an indicator alert"""
        symbol = alert["symbol"]
        indicator_name = alert["indicator_name"]
        condition = alert["indicator_condition"]
        threshold = alert["indicator_value"]
        
        try:
            # Get OHLCV data for indicator calculation
            ohlcv_data = self.price_service.get_ohlcv(symbol, "1h", 200)
            if not ohlcv_data or len(ohlcv_data) < 14:
                return False
            
            indicators = self._calculate_indicators(ohlcv_data)
            
            if indicator_name not in indicators:
                return False
            
            indicator_value = indicators[indicator_name]
            
            if condition == "above":
                return indicator_value >= threshold
            elif condition == "below":
                return indicator_value <= threshold
            elif condition == "crosses_above":
                # For crossover alerts, we check if the indicator value indicates a crossover
                if indicator_name == "MACD_crossover":
                    return indicator_value == 1  # Bullish crossover
                # For other indicators, we'd need previous value - simplified for now
                return False
            elif condition == "crosses_below":
                if indicator_name == "MACD_crossover":
                    return indicator_value == -1  # Bearish crossover
                return False
            else:
                return False
        except Exception as e:
            self.logger.error(f"Error evaluating indicator alert: {e}")
            return False
    
    def evaluate_all_alerts(self) -> List[Dict]:
        """
        Evaluate all enabled, non-triggered alerts
        
        Returns:
            List of alerts that were triggered
        """
        triggered_alerts = []
        
        enabled_alerts = [a for a in self.alerts.values() if a["enabled"] and not a["triggered"]]
        
        for alert in enabled_alerts:
            if self.evaluate_alert(alert):
                # Trigger the alert
                alert["triggered"] = True
                alert["triggered_at"] = datetime.utcnow().isoformat()
                triggered_alerts.append(alert)
                
                # Create notification
                self._create_alert_notification(alert)
                
                self.logger.info(f"Alert {alert['id']} triggered for {alert['symbol']}")
        
        return triggered_alerts
    
    def _create_alert_notification(self, alert: Dict):
        """Create a notification when an alert is triggered"""
        try:
            symbol = alert["symbol"]
            alert_type = alert["alert_type"]
            
            if alert_type == "price":
                threshold = alert["price_threshold"]
                condition = alert["price_condition"]
                title = f"Price Alert: {symbol}"
                message = f"{symbol} price is {condition} ${threshold:,.2f}"
            else:  # indicator
                indicator_name = alert["indicator_name"]
                condition = alert["indicator_condition"]
                threshold = alert["indicator_value"]
                title = f"Indicator Alert: {symbol}"
                message = f"{symbol} {indicator_name} is {condition} {threshold}"
            
            if alert.get("description"):
                message += f" - {alert['description']}"
            
            notification = self.notification_service.create_notification(
                notification_type="risk_alert",
                priority="high",
                title=title,
                message=message,
                source="system",
                symbol=symbol,
                metadata={
                    "alert_id": alert["id"],
                    "alert_type": alert_type,
                    "triggered_at": alert["triggered_at"]
                }
            )
            
            # Broadcast notification via WebSocket
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is running, schedule the coroutine
                    asyncio.create_task(self.notification_service.broadcast_notification(notification))
                else:
                    loop.run_until_complete(self.notification_service.broadcast_notification(notification))
            except Exception as e:
                self.logger.warning(f"Could not broadcast notification: {e}")
            
        except Exception as e:
            self.logger.error(f"Error creating alert notification: {e}", exc_info=True)


# Global alert service instance (singleton pattern)
_alert_service: Optional[AlertService] = None


def get_alert_service() -> AlertService:
    """Get or create alert service instance"""
    global _alert_service
    if _alert_service is None:
        _alert_service = AlertService()
    return _alert_service



