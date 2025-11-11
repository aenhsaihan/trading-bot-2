"""Trade database for storing trading data"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from decimal import Decimal
from src.utils.logger import setup_logger


class TradeDB:
    """SQLite database for storing trades and performance data"""
    
    def __init__(self, db_path: str = "data/trades.db"):
        """
        Initialize trade database.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = setup_logger(f"{__name__}.TradeDB")
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Trades table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                amount REAL NOT NULL,
                price REAL NOT NULL,
                timestamp TEXT NOT NULL,
                exchange TEXT,
                order_type TEXT,
                status TEXT,
                pnl REAL,
                entry_price REAL,
                exit_price REAL,
                reason TEXT,
                market_data TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Signals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                price REAL NOT NULL,
                timestamp TEXT NOT NULL,
                indicators TEXT,
                strategy TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Risk events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS risk_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position_id TEXT,
                event_type TEXT NOT NULL,
                price REAL NOT NULL,
                timestamp TEXT NOT NULL,
                details TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time TEXT NOT NULL,
                end_time TEXT,
                mode TEXT NOT NULL,
                exchange TEXT,
                strategy TEXT,
                config TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        self.logger.info(f"Database initialized at {self.db_path}")
    
    def save_trade(self, trade: Dict):
        """Save a trade to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO trades (
                id, symbol, side, amount, price, timestamp,
                exchange, order_type, status, pnl, entry_price,
                exit_price, reason, market_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trade.get('id'),
            trade.get('symbol'),
            trade.get('side'),
            float(trade.get('amount', 0)),
            float(trade.get('price', 0)),
            trade.get('timestamp', datetime.utcnow().isoformat()),
            trade.get('exchange'),
            trade.get('order_type'),
            trade.get('status'),
            float(trade.get('pnl', 0)),
            float(trade.get('entry_price', 0)),
            float(trade.get('exit_price', 0)),
            trade.get('reason'),
            json.dumps(trade.get('market_data', {}))
        ))
        
        conn.commit()
        conn.close()
    
    def save_signal(self, signal: Dict):
        """Save a trading signal"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO signals (
                symbol, signal_type, price, timestamp, indicators, strategy
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            signal.get('symbol'),
            signal.get('signal_type'),
            float(signal.get('price', 0)),
            signal.get('timestamp', datetime.utcnow().isoformat()),
            json.dumps(signal.get('indicators', {})),
            signal.get('strategy')
        ))
        
        conn.commit()
        conn.close()
    
    def save_risk_event(self, event: Dict):
        """Save a risk management event"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO risk_events (
                position_id, event_type, price, timestamp, details
            ) VALUES (?, ?, ?, ?, ?)
        ''', (
            event.get('position_id'),
            event.get('event_type'),
            float(event.get('price', 0)),
            event.get('timestamp', datetime.utcnow().isoformat()),
            json.dumps(event.get('details', {}))
        ))
        
        conn.commit()
        conn.close()
    
    def get_trades(self, symbol: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Get trades from database"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if symbol:
            cursor.execute('''
                SELECT * FROM trades WHERE symbol = ? ORDER BY timestamp DESC LIMIT ?
            ''', (symbol, limit))
        else:
            cursor.execute('''
                SELECT * FROM trades ORDER BY timestamp DESC LIMIT ?
            ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        trades = []
        for row in rows:
            trade = dict(row)
            if trade.get('market_data'):
                trade['market_data'] = json.loads(trade['market_data'])
            trades.append(trade)
        
        return trades
    
    def get_signals(self, symbol: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Get signals from database"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if symbol:
            cursor.execute('''
                SELECT * FROM signals WHERE symbol = ? ORDER BY timestamp DESC LIMIT ?
            ''', (symbol, limit))
        else:
            cursor.execute('''
                SELECT * FROM signals ORDER BY timestamp DESC LIMIT ?
            ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        signals = []
        for row in rows:
            signal = dict(row)
            if signal.get('indicators'):
                signal['indicators'] = json.loads(signal['indicators'])
            signals.append(signal)
        
        return signals
    
    def get_risk_events(self, limit: int = 100) -> List[Dict]:
        """Get risk events from database"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM risk_events ORDER BY timestamp DESC LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        events = []
        for row in rows:
            event = dict(row)
            if event.get('details'):
                event['details'] = json.loads(event['details'])
            events.append(event)
        
        return events

