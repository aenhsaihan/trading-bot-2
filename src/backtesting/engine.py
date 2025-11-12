"""Backtesting engine"""

from decimal import Decimal
from typing import Dict, List, Optional
from datetime import datetime
from src.strategies.base import StrategyBase
from src.risk.stop_loss import StopLoss
from src.risk.trailing_stop import TrailingStopLoss
from src.utils.paper_trading import PaperTrading
from src.utils.logger import setup_logger


class BacktestEngine:
    """Backtesting engine for strategy evaluation"""
    
    def __init__(
        self,
        strategy: StrategyBase,
        initial_balance: Decimal = Decimal('10000'),
        stop_loss_percent: float = 0.03,
        trailing_stop_percent: float = 0.025
    ):
        """
        Initialize backtesting engine.
        
        Args:
            strategy: Trading strategy instance
            initial_balance: Starting balance
            stop_loss_percent: Stop loss percentage
            trailing_stop_percent: Trailing stop percentage
        """
        self.strategy = strategy
        self.initial_balance = initial_balance
        self.stop_loss = StopLoss(stop_loss_percent)
        self.trailing_stop = TrailingStopLoss(trailing_stop_percent)
        self.paper_trading = PaperTrading(initial_balance)
        self.logger = setup_logger(f"{__name__}.BacktestEngine")
        
        self.trades = []
        self.equity_curve = []
        self.signal_analysis = {
            'potential_buys': 0,
            'potential_sells': 0,
            'rejected_buys': [],
            'rejected_sells': []
        }
    
    def run(
        self,
        ohlcv_data: List[Dict],
        symbol: str,
        position_size_percent: float = 0.01,
        progress_callback: Optional[callable] = None
    ) -> Dict:
        """
        Run backtest on historical data.
        
        Args:
            ohlcv_data: Historical OHLCV data
            symbol: Trading pair symbol
            position_size_percent: Position size as percentage of balance
            progress_callback: Optional callback function(current, total) called periodically
            
        Returns:
            Backtest results dictionary
        """
        self.logger.info(f"Starting backtest for {symbol} with {len(ohlcv_data)} candles")
        
        current_position = None
        position_id = None
        total_candles = len(ohlcv_data)
        
        # Process each candle
        for i in range(total_candles):
            # Call progress callback every 10 candles or at start/end
            if progress_callback and (i == 0 or i % 10 == 0 or i == total_candles - 1):
                try:
                    progress_callback(i + 1, total_candles)
                except Exception as e:
                    # Don't let progress callback errors break the backtest
                    self.logger.debug(f"Progress callback error: {e}")
            candle = ohlcv_data[i]
            current_price = candle['close']
            timestamp = candle['timestamp']
            
            # Get historical data up to current point
            historical_data = ohlcv_data[:i+1]
            
            market_data = {
                'symbol': symbol,
                'ohlcv': historical_data,
                'current_price': current_price,
                'timestamp': timestamp
            }
            
            # Update trailing stop if position exists
            if current_position:
                self.trailing_stop.update(position_id, current_price)
                
                # Calculate indicators for sell decisions
                sell_indicators = self.strategy._calculate_indicators(historical_data) if hasattr(self.strategy, '_calculate_indicators') else {}
                
                # Check trailing stop
                if self.trailing_stop.should_trigger(position_id, current_price):
                    self.logger.info(f"Trailing stop triggered at {current_price}")
                    self._close_position(symbol, current_price, 'trailing_stop', timestamp, sell_indicators)
                    current_position = None
                    position_id = None
                    continue
                
                # Check regular stop loss
                if self.stop_loss.should_trigger(
                    current_price,
                    current_position['entry_price'],
                    'long'
                ):
                    self.logger.info(f"Stop loss triggered at {current_price}")
                    self._close_position(symbol, current_price, 'stop_loss', timestamp, sell_indicators)
                    current_position = None
                    position_id = None
                    continue
                
                # Check strategy sell signal
                if self.strategy.should_sell(market_data, current_position):
                    # Determine specific reason for sell by checking indicators directly
                    sell_reason = 'strategy'
                    if sell_indicators:
                        short_ma = sell_indicators.get('short_ma')
                        long_ma = sell_indicators.get('long_ma')
                        rsi = sell_indicators.get('rsi', 0)
                        
                        # Check for death cross: short MA below long MA (and was above before)
                        # We check if short MA < long MA, which indicates bearish crossover
                        if short_ma and long_ma and short_ma < long_ma:
                            # Check previous state to confirm it was a crossover
                            last_signal = self.strategy.last_signals.get(symbol, {})
                            prev_short_ma = last_signal.get('short_ma')
                            prev_long_ma = last_signal.get('long_ma')
                            if prev_short_ma and prev_long_ma and prev_short_ma >= prev_long_ma:
                                sell_reason = 'death_cross'
                        
                        # Check for RSI overbought (only if not death cross)
                        if sell_reason == 'strategy' and rsi > self.strategy.config.get('rsi_overbought', 70):
                            sell_reason = 'rsi_overbought'
                    
                    self.logger.info(f"Strategy sell signal at {current_price}: {sell_reason}")
                    self._close_position(symbol, current_price, sell_reason, timestamp, sell_indicators)
                    current_position = None
                    position_id = None
                    continue
            
            # Check for buy signal
            if not current_position:
                # Analyze potential buy signals
                indicators = self.strategy._calculate_indicators(historical_data) if hasattr(self.strategy, '_calculate_indicators') else {}
                crossover = self.strategy._check_crossover(indicators, symbol) if hasattr(self.strategy, '_check_crossover') else None
                
                if crossover == 'bullish':
                    self.signal_analysis['potential_buys'] += 1
                    rsi = indicators.get('rsi', 0) if indicators else 0
                    if rsi >= self.strategy.config.get('rsi_overbought', 70):
                        self.signal_analysis['rejected_buys'].append({
                            'timestamp': timestamp,
                            'reason': f'RSI too high ({rsi:.1f} >= 70)',
                            'rsi': rsi,
                            'price': float(current_price)
                        })
                
                if self.strategy.should_buy(market_data):
                    balance = self.paper_trading.get_balance()
                    position_size = self.strategy.calculate_position_size(
                        balance,
                        current_price,
                        position_size_percent
                    )
                    
                    if self.paper_trading.can_afford(position_size, current_price):
                        result = self.paper_trading.buy(symbol, position_size, current_price)
                        
                        if result['success']:
                            position_id = f"{symbol}_{timestamp}"
                            current_position = {
                                'symbol': symbol,
                                'amount': position_size,
                                'entry_price': current_price,
                                'entry_time': timestamp,
                                'side': 'long'
                            }
                            
                            # Initialize trailing stop
                            self.trailing_stop.initialize_position(
                                position_id,
                                current_price,
                                'long'
                            )
                            
                            # Capture indicator values for trade reasoning
                            trade_indicators = {}
                            if indicators:
                                trade_indicators = {
                                    'short_ma': float(indicators.get('short_ma', 0)) if indicators.get('short_ma') is not None else 0,
                                    'long_ma': float(indicators.get('long_ma', 0)) if indicators.get('long_ma') is not None else 0,
                                    'rsi': float(indicators.get('rsi', 0)) if indicators.get('rsi') is not None else 0,
                                    'macd_line': float(indicators.get('macd', 0)) if indicators.get('macd') is not None else 0,
                                    'macd_signal': float(indicators.get('macd_signal', 0)) if indicators.get('macd_signal') is not None else 0
                                }
                            
                            self.trades.append({
                                'type': 'buy',
                                'symbol': symbol,
                                'price': current_price,
                                'timestamp': timestamp,
                                'amount': position_size,
                                'indicators': trade_indicators,
                                'reason': 'golden_cross' if crossover == 'bullish' else 'strategy_signal'
                            })
            
            # Record equity
            current_prices = {symbol: current_price}
            total_value = self.paper_trading.get_total_value(current_prices)
            self.equity_curve.append({
                'timestamp': timestamp,
                'equity': float(total_value),
                'balance': float(self.paper_trading.get_balance())
            })
        
        # Close any remaining positions
        if current_position:
            final_price = ohlcv_data[-1]['close']
            final_timestamp = ohlcv_data[-1]['timestamp']
            final_indicators = self.strategy._calculate_indicators(ohlcv_data) if hasattr(self.strategy, '_calculate_indicators') else {}
            self._close_position(symbol, final_price, 'end_of_backtest', final_timestamp, final_indicators)
        
        return self._calculate_results(symbol)
    
    def _close_position(self, symbol: str, price: Decimal, reason: str, timestamp: int, indicators: Optional[Dict] = None):
        """Close current position"""
        position = self.paper_trading.get_position(symbol)
        if position:
            # Store amount before sell() modifies the position
            sold_amount = position['amount']
            result = self.paper_trading.sell(symbol, sold_amount, price)
            
            if result['success']:
                # Capture indicator values for trade reasoning
                trade_indicators = {}
                if indicators:
                    trade_indicators = {
                        'short_ma': float(indicators.get('short_ma', 0)) if indicators.get('short_ma') is not None else 0,
                        'long_ma': float(indicators.get('long_ma', 0)) if indicators.get('long_ma') is not None else 0,
                        'rsi': float(indicators.get('rsi', 0)) if indicators.get('rsi') is not None else 0,
                        'macd_line': float(indicators.get('macd', 0)) if indicators.get('macd') is not None else 0,
                        'macd_signal': float(indicators.get('macd_signal', 0)) if indicators.get('macd_signal') is not None else 0
                    }
                
                # Calculate percentage return
                entry_price = position.get('entry_price', Decimal('0'))
                exit_price = price
                profit_pct = 0
                if entry_price > 0:
                    profit_pct = float((exit_price - entry_price) / entry_price * 100)
                
                # Use the amount from the trade result, which has the correct sold amount
                self.trades.append({
                    'type': 'sell',
                    'symbol': symbol,
                    'price': price,
                    'entry_price': entry_price,  # Store entry price for percentage calculation
                    'timestamp': timestamp,
                    'amount': result['trade'].get('amount', sold_amount),
                    'reason': reason,
                    'profit': result['trade'].get('profit', Decimal('0')),
                    'profit_pct': profit_pct,
                    'indicators': trade_indicators
                })
    
    def _calculate_results(self, symbol: str) -> Dict:
        """Calculate backtest performance metrics"""
        if not self.trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'sharpe_ratio': 0
            }
        
        # Calculate P&L
        buy_trades = [t for t in self.trades if t['type'] == 'buy']
        sell_trades = [t for t in self.trades if t['type'] == 'sell']
        
        total_pnl = Decimal('0')
        winning_trades = 0
        losing_trades = 0
        
        for sell_trade in sell_trades:
            # Find corresponding buy trade
            buy_trade = None
            for buy in buy_trades:
                if buy['symbol'] == sell_trade['symbol'] and buy['timestamp'] < sell_trade.get('timestamp', 0):
                    buy_trade = buy
                    break
            
            if buy_trade:
                profit = sell_trade.get('profit', Decimal('0'))
                total_pnl += profit
                
                if profit > 0:
                    winning_trades += 1
                else:
                    losing_trades += 1
        
        total_trades = len(sell_trades)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # Calculate Sharpe ratio (simplified)
        if len(self.equity_curve) > 1:
            returns = []
            for i in range(1, len(self.equity_curve)):
                prev_equity = self.equity_curve[i-1]['equity']
                curr_equity = self.equity_curve[i]['equity']
                if prev_equity > 0:
                    returns.append((curr_equity - prev_equity) / prev_equity)
            
            if returns:
                avg_return = sum(returns) / len(returns)
                variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
                std_dev = variance ** 0.5
                sharpe_ratio = (avg_return / std_dev) * (252 ** 0.5) if std_dev > 0 else 0
            else:
                sharpe_ratio = 0
        else:
            sharpe_ratio = 0
        
        final_balance = self.paper_trading.get_balance()
        total_return = ((final_balance - self.initial_balance) / self.initial_balance) * 100
        
        result = {
            'symbol': symbol,
            'initial_balance': float(self.initial_balance),
            'final_balance': float(final_balance),
            'total_return': float(total_return),
            'total_pnl': float(total_pnl),
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'sharpe_ratio': sharpe_ratio,
            'trades': self.trades,
            'equity_curve': self.equity_curve,
            'signal_analysis': self.signal_analysis
        }
        
        return result

