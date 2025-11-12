"""Real-time data streaming for dashboard"""

import time
import threading
from typing import Dict, Optional, Callable
from decimal import Decimal
from src.exchanges.base import ExchangeBase
from src.utils.logger import setup_logger

# Global lock to prevent duplicate streamer starts across Streamlit reruns
_streamer_lock = threading.Lock()


class DataStreamer:
    """Stream real-time market data"""
    
    def __init__(self, exchange: ExchangeBase, update_interval: float = 1.0):
        """
        Initialize data streamer.
        
        Args:
            exchange: Exchange instance
            update_interval: Update interval in seconds
        """
        self.exchange = exchange
        self.update_interval = update_interval
        self.logger = setup_logger(f"{__name__}.DataStreamer")
        self.running = False
        self.thread = None
        self.callbacks = []
        self.latest_data = {}
        self._start_lock = threading.Lock()  # Per-instance lock
    
    def subscribe(self, callback: Callable):
        """Subscribe to data updates"""
        self.callbacks.append(callback)
    
    def start(self, symbol: str):
        """Start streaming data with thread-safe duplicate prevention"""
        # Use both global and instance locks to prevent duplicates
        with _streamer_lock:
            with self._start_lock:
                if self.running:
                    self.logger.debug(f"Streamer already running for {symbol}, skipping start")
                    return
                
                # Double-check to prevent race conditions
                if self.thread and self.thread.is_alive():
                    self.logger.debug(f"Streamer thread already alive for {symbol}, skipping start")
                    return
                
                self.running = True
                self.thread = threading.Thread(target=self._stream_loop, args=(symbol,), daemon=True)
                self.thread.start()
                self.logger.info(f"Started streaming data for {symbol}")
    
    def stop(self):
        """Stop streaming data"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        self.logger.info("Stopped streaming data")
    
    def _stream_loop(self, symbol: str):
        """Main streaming loop with exponential backoff for rate limiting"""
        consecutive_errors = 0
        max_backoff = 60  # Maximum backoff time in seconds
        ohlcv_fetch_counter = 0  # Counter to fetch OHLCV less frequently
        
        while self.running:
            try:
                # Get ticker data (lightweight, fast)
                ticker = self.exchange.get_ticker(symbol)
                
                # Only fetch OHLCV every 6th iteration (every 60 seconds with 10s interval)
                # This reduces API calls significantly while still providing chart data
                ohlcv = []
                ohlcv_fetch_counter += 1
                if ohlcv_fetch_counter >= 6:
                    try:
                        ohlcv = self.exchange.get_ohlcv(symbol, timeframe="1h", limit=10)
                        ohlcv_fetch_counter = 0  # Reset counter
                    except Exception as ohlcv_error:
                        # If OHLCV fetch fails, continue with ticker data only
                        self.logger.debug(f"OHLCV fetch failed (non-critical): {ohlcv_error}")
                        ohlcv = []
                
                data = {
                    'symbol': symbol,
                    'price': float(ticker['last']),
                    'bid': float(ticker['bid']),
                    'ask': float(ticker['ask']),
                    'volume': float(ticker['volume']),
                    'timestamp': ticker['timestamp'],
                    'ohlcv': ohlcv[-10:] if ohlcv else []  # Last 10 candles (may be empty)
                }
                
                self.latest_data[symbol] = data
                
                # Reset error counter on success
                consecutive_errors = 0
                
                # Notify callbacks
                for callback in self.callbacks:
                    try:
                        callback(data)
                    except Exception as e:
                        self.logger.error(f"Error in callback: {e}")
                
                time.sleep(self.update_interval)
            
            except Exception as e:
                error_str = str(e).lower()
                
                # Check for rate limiting errors
                is_rate_limit = (
                    'too many requests' in error_str or
                    'rate limit' in error_str or
                    '429' in error_str or
                    'egeneral:too many requests' in error_str
                )
                
                if is_rate_limit:
                    consecutive_errors += 1
                    # Exponential backoff: 2^errors seconds, capped at max_backoff
                    backoff_time = min(2 ** consecutive_errors, max_backoff)
                    self.logger.warning(f"Rate limited. Backing off for {backoff_time}s (attempt {consecutive_errors})")
                    time.sleep(backoff_time)
                    # Reset OHLCV counter on rate limit to avoid immediate retry
                    ohlcv_fetch_counter = 0
                else:
                    # For other errors, use normal interval
                    self.logger.error(f"Error in stream loop: {e}")
                    consecutive_errors = min(consecutive_errors + 1, 5)  # Cap at 5 for non-rate-limit errors
                    time.sleep(self.update_interval)
    
    def get_latest_data(self, symbol: str) -> Optional[Dict]:
        """Get latest data for symbol"""
        return self.latest_data.get(symbol)

