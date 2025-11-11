"""Performance analytics and metrics calculation"""

from typing import Dict, List
from decimal import Decimal
from src.utils.logger import setup_logger


class PerformanceAnalytics:
    """Calculate trading performance metrics"""
    
    def __init__(self):
        self.logger = setup_logger(f"{__name__}.PerformanceAnalytics")
    
    def calculate_metrics(self, trades: List[Dict]) -> Dict:
        """
        Calculate performance metrics from trades.
        
        Args:
            trades: List of trade dictionaries
            
        Returns:
            Dictionary with performance metrics
        """
        if not trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'average_win': 0,
                'average_loss': 0,
                'sharpe_ratio': 0
            }
        
        # Separate buy and sell trades
        buy_trades = [t for t in trades if t.get('side') == 'buy']
        sell_trades = [t for t in trades if t.get('side') == 'sell']
        
        # Calculate P&L
        total_pnl = Decimal('0')
        winning_trades = 0
        losing_trades = 0
        win_amounts = []
        loss_amounts = []
        
        for sell_trade in sell_trades:
            pnl = Decimal(str(sell_trade.get('pnl', 0)))
            total_pnl += pnl
            
            if pnl > 0:
                winning_trades += 1
                win_amounts.append(float(pnl))
            elif pnl < 0:
                losing_trades += 1
                loss_amounts.append(float(pnl))
        
        total_trades = len(sell_trades)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        average_win = sum(win_amounts) / len(win_amounts) if win_amounts else 0
        average_loss = sum(loss_amounts) / len(loss_amounts) if loss_amounts else 0
        
        # Calculate Sharpe ratio (simplified)
        returns = [float(t.get('pnl', 0)) for t in sell_trades if t.get('pnl') is not None]
        sharpe_ratio = self._calculate_sharpe_ratio(returns)
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_pnl': float(total_pnl),
            'average_win': average_win,
            'average_loss': average_loss,
            'sharpe_ratio': sharpe_ratio,
            'profit_factor': abs(sum(win_amounts) / sum(loss_amounts)) if loss_amounts and sum(loss_amounts) != 0 else 0
        }
    
    def _calculate_sharpe_ratio(self, returns: List[float]) -> float:
        """Calculate Sharpe ratio"""
        if not returns or len(returns) < 2:
            return 0.0
        
        avg_return = sum(returns) / len(returns)
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        std_dev = variance ** 0.5
        
        if std_dev == 0:
            return 0.0
        
        # Annualized Sharpe ratio (assuming daily returns)
        sharpe = (avg_return / std_dev) * (252 ** 0.5)
        return sharpe
    
    def calculate_drawdown(self, equity_curve: List[Dict]) -> Dict:
        """
        Calculate maximum drawdown.
        
        Args:
            equity_curve: List of {'timestamp': ..., 'equity': ...} dictionaries
            
        Returns:
            Drawdown metrics
        """
        if not equity_curve:
            return {'max_drawdown': 0, 'max_drawdown_percent': 0}
        
        equities = [e['equity'] for e in equity_curve]
        peak = equities[0]
        max_drawdown = 0
        max_drawdown_percent = 0
        
        for equity in equities:
            if equity > peak:
                peak = equity
            
            drawdown = peak - equity
            drawdown_percent = (drawdown / peak) * 100 if peak > 0 else 0
            
            if drawdown > max_drawdown:
                max_drawdown = drawdown
                max_drawdown_percent = drawdown_percent
        
        return {
            'max_drawdown': max_drawdown,
            'max_drawdown_percent': max_drawdown_percent
        }
    
    def analyze_by_exchange(self, trades: List[Dict]) -> Dict:
        """Analyze performance by exchange"""
        exchange_stats = {}
        
        for trade in trades:
            exchange = trade.get('exchange', 'unknown')
            if exchange not in exchange_stats:
                exchange_stats[exchange] = {
                    'trades': 0,
                    'pnl': Decimal('0')
                }
            
            exchange_stats[exchange]['trades'] += 1
            exchange_stats[exchange]['pnl'] += Decimal(str(trade.get('pnl', 0)))
        
        # Convert to float for JSON serialization
        result = {}
        for exchange, stats in exchange_stats.items():
            result[exchange] = {
                'trades': stats['trades'],
                'pnl': float(stats['pnl'])
            }
        
        return result
    
    def analyze_by_symbol(self, trades: List[Dict]) -> Dict:
        """Analyze performance by trading symbol"""
        symbol_stats = {}
        
        for trade in trades:
            symbol = trade.get('symbol', 'unknown')
            if symbol not in symbol_stats:
                symbol_stats[symbol] = {
                    'trades': 0,
                    'pnl': Decimal('0')
                }
            
            symbol_stats[symbol]['trades'] += 1
            symbol_stats[symbol]['pnl'] += Decimal(str(trade.get('pnl', 0)))
        
        # Convert to float for JSON serialization
        result = {}
        for symbol, stats in symbol_stats.items():
            result[symbol] = {
                'trades': stats['trades'],
                'pnl': float(stats['pnl'])
            }
        
        return result

