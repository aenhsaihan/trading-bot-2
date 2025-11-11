"""Main trading bot orchestrator"""

import time
from decimal import Decimal
from typing import Dict, List, Optional
from src.exchanges.base import ExchangeBase
from src.strategies.base import StrategyBase
from src.risk.stop_loss import StopLoss
from src.risk.trailing_stop import TrailingStopLoss
from src.utils.order_manager import OrderManager
from src.utils.paper_trading import PaperTrading
from src.utils.config import Config
from src.utils.logger import setup_logger


class TradingBot:
    """Main trading bot orchestrator"""
    
    def __init__(
        self,
        exchange: ExchangeBase,
        strategy: StrategyBase,
        config: Config,
        is_paper_trading: bool = True
    ):
        """
        Initialize trading bot.
        
        Args:
            exchange: Exchange instance
            strategy: Trading strategy instance
            config: Configuration instance
            is_paper_trading: Whether to use paper trading mode
        """
        self.exchange = exchange
        self.strategy = strategy
        self.config = config
        self.is_paper_trading = is_paper_trading
        
        # Risk management
        risk_config = config.get_risk_config()
        self.stop_loss = StopLoss(risk_config.get('stop_loss_percent', 0.03))
        self.trailing_stop = TrailingStopLoss(risk_config.get('trailing_stop_percent', 0.025))
        
        # Order management
        self.order_manager = OrderManager(is_paper_trading=is_paper_trading)
        
        # Paper trading
        if is_paper_trading:
            self.paper_trading = PaperTrading(Decimal('10000'))
        
        self.logger = setup_logger(f"{__name__}.TradingBot")
        self.running = False
        self.positions = {}
    
    def start(self, symbol: str, check_interval: int = 60):
        """
        Start the trading bot.
        
        Args:
            symbol: Trading pair symbol to trade
            check_interval: Interval between checks in seconds
        """
        if not self.exchange.is_connected():
            self.logger.error("Exchange not connected")
            return
        
        self.running = True
        self.logger.info(f"Starting bot in {'paper' if self.is_paper_trading else 'live'} trading mode for {symbol}")
        
        try:
            while self.running:
                self._trading_loop(symbol)
                time.sleep(check_interval)
        except KeyboardInterrupt:
            self.logger.info("Bot stopped by user")
            self.stop()
        except Exception as e:
            self.logger.error(f"Error in trading loop: {e}")
            self.stop()
    
    def stop(self):
        """Stop the trading bot"""
        self.running = False
        self.logger.info("Bot stopped")
    
    def _trading_loop(self, symbol: str):
        """Main trading loop"""
        try:
            # Get current market data
            ticker = self.exchange.get_ticker(symbol)
            current_price = ticker['last']
            
            # Get OHLCV data for strategy
            ohlcv_data = self.exchange.get_ohlcv(symbol, timeframe="1h", limit=200)
            
            if not ohlcv_data:
                self.logger.warning(f"No OHLCV data for {symbol}")
                return
            
            market_data = {
                'symbol': symbol,
                'ohlcv': ohlcv_data,
                'current_price': current_price,
                'ticker': ticker
            }
            
            # Check existing positions
            position = self._get_position(symbol)
            
            if position:
                # Update trailing stop
                position_id = position.get('id', symbol)
                self.trailing_stop.update(position_id, current_price)
                
                # Check stop loss and trailing stop
                if self._check_exit_conditions(symbol, position, current_price):
                    return
                
                # Check strategy sell signal
                if self.strategy.should_sell(market_data, position):
                    self.logger.info(f"Strategy sell signal for {symbol}")
                    self._close_position(symbol, current_price, 'strategy')
                    return
            else:
                # Check for buy signal
                if self.strategy.should_buy(market_data):
                    self.logger.info(f"Strategy buy signal for {symbol}")
                    self._open_position(symbol, current_price, market_data)
        
        except Exception as e:
            self.logger.error(f"Error in trading loop: {e}")
    
    def _get_position(self, symbol: str) -> Optional[Dict]:
        """Get current position for symbol"""
        if self.is_paper_trading:
            return self.paper_trading.get_position(symbol)
        else:
            # Get from exchange
            positions = self.exchange.get_open_positions()
            for pos in positions:
                if pos.get('symbol') == symbol:
                    return pos
        return None
    
    def _check_exit_conditions(self, symbol: str, position: Dict, current_price: Decimal) -> bool:
        """Check if position should be closed due to stop loss"""
        position_id = position.get('id', symbol)
        entry_price = Decimal(str(position.get('entry_price', current_price)))
        
        # Check trailing stop
        if self.trailing_stop.should_trigger(position_id, current_price):
            self.logger.info(f"Trailing stop triggered for {symbol} at {current_price}")
            self._close_position(symbol, current_price, 'trailing_stop')
            return True
        
        # Check regular stop loss
        if self.stop_loss.should_trigger(current_price, entry_price, 'long'):
            self.logger.info(f"Stop loss triggered for {symbol} at {current_price}")
            self._close_position(symbol, current_price, 'stop_loss')
            return True
        
        return False
    
    def _open_position(self, symbol: str, price: Decimal, market_data: Dict):
        """Open a new position"""
        try:
            # Calculate position size
            if self.is_paper_trading:
                balance = self.paper_trading.get_balance()
            else:
                balance = self.exchange.get_balance()
            
            risk_config = self.config.get_risk_config()
            position_size_percent = risk_config.get('position_size_percent', 0.01)
            
            position_size = self.strategy.calculate_position_size(
                balance,
                price,
                position_size_percent
            )
            
            if self.is_paper_trading:
                result = self.paper_trading.buy(symbol, position_size, price)
                if result['success']:
                    position_id = f"{symbol}_{int(time.time())}"
                    self.trailing_stop.initialize_position(position_id, price, 'long')
                    self.positions[symbol] = {
                        'id': position_id,
                        'symbol': symbol,
                        'amount': position_size,
                        'entry_price': price
                    }
            else:
                # Live trading
                order = self.exchange.place_order(
                    symbol=symbol,
                    side='buy',
                    amount=position_size,
                    order_type='market'
                )
                
                if order['status'] == 'filled':
                    position_id = f"{symbol}_{order['id']}"
                    self.trailing_stop.initialize_position(position_id, price, 'long')
                    self.positions[symbol] = {
                        'id': position_id,
                        'symbol': symbol,
                        'amount': order['filled'],
                        'entry_price': price
                    }
        
        except Exception as e:
            self.logger.error(f"Error opening position: {e}")
    
    def _close_position(self, symbol: str, price: Decimal, reason: str):
        """Close a position"""
        try:
            if self.is_paper_trading:
                position = self.paper_trading.get_position(symbol)
                if position:
                    self.paper_trading.sell(symbol, position['amount'], price)
                    position_id = self.positions.get(symbol, {}).get('id')
                    if position_id:
                        self.trailing_stop.remove_position(position_id)
                    if symbol in self.positions:
                        del self.positions[symbol]
            else:
                # Live trading
                position = self._get_position(symbol)
                if position:
                    order = self.exchange.place_order(
                        symbol=symbol,
                        side='sell',
                        amount=Decimal(str(position.get('amount', 0))),
                        order_type='market'
                    )
                    
                    position_id = self.positions.get(symbol, {}).get('id')
                    if position_id:
                        self.trailing_stop.remove_position(position_id)
                    if symbol in self.positions:
                        del self.positions[symbol]
        
        except Exception as e:
            self.logger.error(f"Error closing position: {e}")
    
    def get_status(self) -> Dict:
        """Get bot status"""
        return {
            'running': self.running,
            'mode': 'paper' if self.is_paper_trading else 'live',
            'positions': len(self.positions),
            'exchange': self.exchange.name if self.exchange.is_connected() else None
        }
    
    def set_trading_mode(self, is_paper_trading: bool):
        """Switch between paper and live trading"""
        self.is_paper_trading = is_paper_trading
        self.order_manager.is_paper_trading = is_paper_trading
        self.logger.info(f"Switched to {'paper' if is_paper_trading else 'live'} trading mode")

