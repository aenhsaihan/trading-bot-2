"""Metrics collection for monitoring"""

from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime
from src.utils.logger import setup_logger


class MetricsCollector:
    """Collect and track trading metrics"""
    
    def __init__(self):
        self.logger = setup_logger(f"{__name__}.MetricsCollector")
        self.metrics = {
            'open_positions': [],
            'trade_history': [],
            'signals': [],
            'performance': {
                'total_pnl': Decimal('0'),
                'win_rate': 0.0,
                'total_trades': 0
            }
        }
    
    def update_position(self, position: Dict):
        """Update position metrics"""
        symbol = position.get('symbol')
        
        # Find existing position
        existing = None
        for i, pos in enumerate(self.metrics['open_positions']):
            if pos.get('symbol') == symbol:
                existing = i
                break
        
        if existing is not None:
            self.metrics['open_positions'][existing] = position
        else:
            self.metrics['open_positions'].append(position)
    
    def remove_position(self, symbol: str):
        """Remove position from metrics"""
        self.metrics['open_positions'] = [
            p for p in self.metrics['open_positions']
            if p.get('symbol') != symbol
        ]
    
    def add_trade(self, trade: Dict):
        """Add trade to history"""
        self.metrics['trade_history'].append(trade)
        # Keep only last 100 trades
        if len(self.metrics['trade_history']) > 100:
            self.metrics['trade_history'] = self.metrics['trade_history'][-100:]
    
    def add_signal(self, signal: Dict):
        """Add signal to history"""
        self.metrics['signals'].append(signal)
        # Keep only last 50 signals
        if len(self.metrics['signals']) > 50:
            self.metrics['signals'] = self.metrics['signals'][-50:]
    
    def update_performance(self, pnl: Decimal, win_rate: float, total_trades: int):
        """Update performance metrics"""
        self.metrics['performance'] = {
            'total_pnl': pnl,
            'win_rate': win_rate,
            'total_trades': total_trades
        }
    
    def get_metrics(self) -> Dict:
        """Get all metrics"""
        return self.metrics.copy()
    
    def get_open_positions(self) -> List[Dict]:
        """Get open positions"""
        return self.metrics['open_positions'].copy()
    
    def get_recent_signals(self, limit: int = 10) -> List[Dict]:
        """Get recent signals"""
        return self.metrics['signals'][-limit:]
    
    def get_recent_trades(self, limit: int = 10) -> List[Dict]:
        """Get recent trades"""
        return self.metrics['trade_history'][-limit:]

