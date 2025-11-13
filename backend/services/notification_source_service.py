"""Background service for continuously monitoring and generating notifications from technical analysis"""

import sys
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
import threading
import time

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.services.signal_generator import SignalGenerator
from backend.services.notification_service import NotificationService
from backend.services.price_service import get_price_service
from src.utils.logger import setup_logger


class NotificationSourceService:
    """Background service that continuously monitors markets and generates notifications"""
    
    def __init__(
        self,
        symbols: Optional[List[str]] = None,
        timeframe: str = "1h",
        check_interval: int = 300,  # Check every 5 minutes
        exchange_name: str = "binance"
    ):
        """
        Initialize notification source service.
        
        Args:
            symbols: List of symbols to monitor (default: popular pairs)
            timeframe: Timeframe for analysis
            check_interval: Interval between checks in seconds
            exchange_name: Exchange to use
        """
        self.symbols = symbols or [
            "BTC/USDT",
            "ETH/USDT",
            "BNB/USDT",
            "SOL/USDT",
            "ADA/USDT",
            "XRP/USDT",
            "DOT/USDT",
            "DOGE/USDT"
        ]
        self.timeframe = timeframe
        self.check_interval = check_interval
        self.exchange_name = exchange_name
        
        self.signal_generator = SignalGenerator()
        self.notification_service = NotificationService()
        self.price_service = get_price_service(exchange_name)
        self.logger = setup_logger(f"{__name__}.NotificationSourceService")
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_check: Dict[str, datetime] = {}  # Track last check per symbol
        
        # Statistics
        self.stats = {
            'total_checks': 0,
            'signals_detected': 0,
            'notifications_created': 0,
            'errors': 0,
            'start_time': None
        }
    
    def start(self):
        """Start the background monitoring service"""
        if self._running:
            self.logger.warning("Service is already running")
            return
        
        self._running = True
        self.stats['start_time'] = datetime.now()
        
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        
        self.logger.info(
            f"NotificationSourceService started - monitoring {len(self.symbols)} symbols "
            f"every {self.check_interval} seconds"
        )
    
    def stop(self):
        """Stop the background monitoring service"""
        if not self._running:
            return
        
        self._running = False
        
        if self._thread:
            self._thread.join(timeout=10)
        
        self.logger.info("NotificationSourceService stopped")
    
    def is_running(self) -> bool:
        """Check if service is running"""
        return self._running
    
    def _run_loop(self):
        """Main monitoring loop (runs in background thread)"""
        self.logger.info("Starting monitoring loop...")
        
        while self._running:
            try:
                # Check each symbol
                for symbol in self.symbols:
                    if not self._running:
                        break
                    
                    try:
                        self._check_symbol(symbol)
                    except Exception as e:
                        self.logger.error(f"Error checking {symbol}: {e}", exc_info=True)
                        self.stats['errors'] += 1
                    
                    # Small delay between symbols to avoid rate limiting
                    time.sleep(1)
                
                self.stats['total_checks'] += 1
                
                # Wait for next check interval
                time.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                self.stats['errors'] += 1
                time.sleep(60)  # Wait 1 minute before retrying
    
    def _check_symbol(self, symbol: str):
        """
        Check a single symbol for signals and generate notifications.
        
        Args:
            symbol: Trading pair symbol to check
        """
        try:
            # Verify exchange is connected
            if not self.price_service.is_connected():
                self.logger.warning(f"Exchange not connected, skipping {symbol}")
                return
            
            # Check if we should skip (too soon since last check)
            last_check = self._last_check.get(symbol)
            if last_check:
                time_since_check = datetime.now() - last_check
                if time_since_check.total_seconds() < self.check_interval:
                    return  # Skip if checked recently
            
            self.logger.debug(f"Checking {symbol} for signals...")
            
            # Generate notifications from signals
            notifications = self.signal_generator.generate_notifications(
                symbols=[symbol],
                timeframe=self.timeframe
            )
            
            # Update statistics
            if notifications:
                self.stats['signals_detected'] += len(notifications)
                self.stats['notifications_created'] += len(notifications)
                self.logger.info(f"Generated {len(notifications)} notification(s) for {symbol}")
            
            # Broadcast notifications via WebSocket
            for notif_dict in notifications:
                try:
                    # Get the actual notification object
                    notif_id = notif_dict.get('id')
                    if notif_id:
                        notification = self.notification_service.get_notification(notif_id)
                        if notification:
                            # Broadcast via WebSocket (async, but we're in sync context)
                            # We'll need to handle this differently
                            asyncio.run(self.notification_service.broadcast_notification(notification))
                except Exception as e:
                    self.logger.error(f"Error broadcasting notification: {e}")
            
            # Update last check time
            self._last_check[symbol] = datetime.now()
            
        except Exception as e:
            self.logger.error(f"Error checking symbol {symbol}: {e}", exc_info=True)
            raise
    
    def add_symbol(self, symbol: str):
        """Add a symbol to monitor"""
        if symbol not in self.symbols:
            self.symbols.append(symbol)
            self.logger.info(f"Added {symbol} to monitoring list")
    
    def remove_symbol(self, symbol: str):
        """Remove a symbol from monitoring"""
        if symbol in self.symbols:
            self.symbols.remove(symbol)
            if symbol in self._last_check:
                del self._last_check[symbol]
            self.logger.info(f"Removed {symbol} from monitoring list")
    
    def get_stats(self) -> Dict:
        """Get service statistics"""
        uptime = None
        if self.stats['start_time']:
            uptime = (datetime.now() - self.stats['start_time']).total_seconds()
        
        return {
            **self.stats,
            'uptime_seconds': uptime,
            'symbols_monitored': len(self.symbols),
            'check_interval': self.check_interval,
            'running': self._running
        }
    
    def get_status(self) -> Dict:
        """Get service status"""
        return {
            'running': self._running,
            'symbols': self.symbols,
            'timeframe': self.timeframe,
            'check_interval': self.check_interval,
            'stats': self.get_stats()
        }


# Global service instance
_notification_source_service: Optional[NotificationSourceService] = None


def get_notification_source_service(
    symbols: Optional[List[str]] = None,
    timeframe: str = "1h",
    check_interval: int = 300,
    exchange_name: str = "binance"
) -> NotificationSourceService:
    """
    Get or create notification source service instance (singleton).
    
    Args:
        symbols: List of symbols to monitor
        timeframe: Timeframe for analysis
        check_interval: Interval between checks in seconds
        exchange_name: Exchange to use
        
    Returns:
        NotificationSourceService instance
    """
    global _notification_source_service
    
    if _notification_source_service is None:
        _notification_source_service = NotificationSourceService(
            symbols=symbols,
            timeframe=timeframe,
            check_interval=check_interval,
            exchange_name=exchange_name
        )
    elif symbols and set(symbols) != set(_notification_source_service.symbols):
        # Update symbols if different
        _notification_source_service.symbols = symbols
    
    return _notification_source_service

