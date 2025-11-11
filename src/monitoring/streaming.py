"""Real-time data streaming for dashboard"""

import time
import threading
from typing import Dict, Optional, Callable
from decimal import Decimal
from src.exchanges.base import ExchangeBase
from src.utils.logger import setup_logger


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
    
    def subscribe(self, callback: Callable):
        """Subscribe to data updates"""
        self.callbacks.append(callback)
    
    def start(self, symbol: str):
        """Start streaming data"""
        if self.running:
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
        """Main streaming loop"""
        while self.running:
            try:
                # Get ticker data
                ticker = self.exchange.get_ticker(symbol)
                
                # Get recent OHLCV
                ohlcv = self.exchange.get_ohlcv(symbol, timeframe="1h", limit=100)
                
                data = {
                    'symbol': symbol,
                    'price': float(ticker['last']),
                    'bid': float(ticker['bid']),
                    'ask': float(ticker['ask']),
                    'volume': float(ticker['volume']),
                    'timestamp': ticker['timestamp'],
                    'ohlcv': ohlcv[-10:] if ohlcv else []  # Last 10 candles
                }
                
                self.latest_data[symbol] = data
                
                # Notify callbacks
                for callback in self.callbacks:
                    try:
                        callback(data)
                    except Exception as e:
                        self.logger.error(f"Error in callback: {e}")
                
                time.sleep(self.update_interval)
            
            except Exception as e:
                self.logger.error(f"Error in stream loop: {e}")
                time.sleep(self.update_interval)
    
    def get_latest_data(self, symbol: str) -> Optional[Dict]:
        """Get latest data for symbol"""
        return self.latest_data.get(symbol)

