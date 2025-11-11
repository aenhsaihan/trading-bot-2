"""Historical data loader for backtesting"""

import os
import json
from pathlib import Path
from typing import List, Dict, Optional
from decimal import Decimal
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
        save: bool = True
    ) -> List[Dict]:
        """
        Fetch historical data from exchange and optionally save it.
        
        Args:
            exchange: Exchange instance
            symbol: Trading pair symbol
            timeframe: Timeframe (e.g., '1h', '1d')
            limit: Number of candles to fetch
            save: Whether to save data to file
            
        Returns:
            List of OHLCV data dictionaries
        """
        try:
            self.logger.info(f"Fetching {limit} candles of {symbol} {timeframe} from {exchange.name}")
            ohlcv_data = exchange.get_ohlcv(symbol, timeframe, limit)
            
            if save:
                self.save_data(symbol, timeframe, ohlcv_data)
            
            return ohlcv_data
        except Exception as e:
            self.logger.error(f"Error fetching data: {e}")
            return []
    
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

