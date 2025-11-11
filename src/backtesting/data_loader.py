"""Historical data loader for backtesting"""

import os
import json
from pathlib import Path
from typing import List, Dict, Optional
from decimal import Decimal
from datetime import datetime, timedelta
import time
from src.exchanges.base import ExchangeBase
from src.utils.logger import setup_logger


class DataLoader:
    """Load and manage historical market data"""
    
    def __init__(self, data_dir: str = "data"):
        """
        Initialize data loader.
        
        Args:
            data_dir: Directory to store historical data
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logger = setup_logger(f"{__name__}.DataLoader")
    
    def fetch_and_save(
        self,
        exchange: ExchangeBase,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 1000,
        since: Optional[int] = None,
        save: bool = True
    ) -> List[Dict]:
        """
        Fetch historical data from exchange and optionally save it.
        
        Args:
            exchange: Exchange instance
            symbol: Trading pair symbol
            timeframe: Timeframe (e.g., '1h', '1d')
            limit: Number of candles to fetch (max 10000 per request)
            since: Start timestamp in milliseconds (optional)
            save: Whether to save data to file
            
        Returns:
            List of OHLCV data dictionaries
        """
        try:
            all_data = []
            max_per_request = 1000  # Most exchanges limit to 1000 per request
            
            if limit <= max_per_request:
                # Single request
                self.logger.info(f"Fetching {limit} candles of {symbol} {timeframe} from {exchange.name}")
                ohlcv_data = exchange.get_ohlcv(symbol, timeframe, limit, since=since)
                all_data = ohlcv_data
            else:
                # Multiple requests needed
                self.logger.info(f"Fetching {limit} candles of {symbol} {timeframe} (will make multiple requests)")
                
                remaining = limit
                current_since = since
                
                while remaining > 0 and len(all_data) < limit:
                    request_size = min(remaining, max_per_request)
                    
                    # Fetch batch
                    batch = exchange.get_ohlcv(symbol, timeframe, request_size, since=current_since)
                    
                    if not batch:
                        break
                    
                    all_data.extend(batch)
                    
                    # Update for next request - use last candle timestamp
                    if batch:
                        last_timestamp = batch[-1]['timestamp']
                        # Add one timeframe duration to avoid overlap
                        timeframe_ms = self._get_timeframe_ms(timeframe)
                        current_since = last_timestamp + timeframe_ms
                    
                    remaining -= len(batch)
                    
                    # Small delay to avoid rate limits
                    time.sleep(0.1)
                
                # Trim to exact limit if needed
                all_data = all_data[:limit]
            
            self.logger.info(f"Fetched {len(all_data)} candles total")
            
            if save and all_data:
                self.save_data(symbol, timeframe, all_data)
            
            return all_data
        except Exception as e:
            self.logger.error(f"Error fetching data: {e}")
            return []
    
    def _get_timeframe_ms(self, timeframe: str) -> int:
        """Convert timeframe string to milliseconds"""
        timeframe_map = {
            '1m': 60 * 1000,
            '5m': 5 * 60 * 1000,
            '15m': 15 * 60 * 1000,
            '30m': 30 * 60 * 1000,
            '1h': 60 * 60 * 1000,
            '4h': 4 * 60 * 60 * 1000,
            '1d': 24 * 60 * 60 * 1000,
            '1w': 7 * 24 * 60 * 60 * 1000,
        }
        return timeframe_map.get(timeframe, 60 * 60 * 1000)
    
    def save_data(self, symbol: str, timeframe: str, data: List[Dict]):
        """
        Save OHLCV data to file.
        
        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe
            data: List of OHLCV dictionaries
        """
        filename = f"{symbol.replace('/', '_')}_{timeframe}.json"
        filepath = self.data_dir / filename
        
        # Convert Decimal to string for JSON serialization
        serializable_data = []
        for candle in data:
            serializable_candle = {}
            for key, value in candle.items():
                if isinstance(value, Decimal):
                    serializable_candle[key] = str(value)
                else:
                    serializable_candle[key] = value
            serializable_data.append(serializable_candle)
        
        with open(filepath, 'w') as f:
            json.dump(serializable_data, f, indent=2)
        
        self.logger.info(f"Saved {len(data)} candles to {filepath}")
    
    def load_data(self, symbol: str, timeframe: str) -> List[Dict]:
        """
        Load historical data from file.
        
        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe
            
        Returns:
            List of OHLCV data dictionaries
        """
        filename = f"{symbol.replace('/', '_')}_{timeframe}.json"
        filepath = self.data_dir / filename
        
        if not filepath.exists():
            self.logger.warning(f"Data file not found: {filepath}")
            return []
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Convert string back to Decimal
            ohlcv_data = []
            for candle in data:
                ohlcv_candle = {}
                for key, value in candle.items():
                    if key in ['open', 'high', 'low', 'close', 'volume']:
                        ohlcv_candle[key] = Decimal(str(value))
                    else:
                        ohlcv_candle[key] = value
                ohlcv_data.append(ohlcv_candle)
            
            self.logger.info(f"Loaded {len(ohlcv_data)} candles from {filepath}")
            return ohlcv_data
        except Exception as e:
            self.logger.error(f"Error loading data: {e}")
            return []
    
    def data_exists(self, symbol: str, timeframe: str) -> bool:
        """Check if data file exists"""
        filename = f"{symbol.replace('/', '_')}_{timeframe}.json"
        filepath = self.data_dir / filename
        return filepath.exists()

