"""Bot manager for handling multiple trading bot instances"""

import threading
import time
import uuid
from typing import Dict, List, Optional
from decimal import Decimal
from src.bot import TradingBot
from src.exchanges.base import ExchangeBase
from src.strategies.base import StrategyBase
from src.utils.config import Config
from src.utils.logger import setup_logger


class BotInstance:
    """Represents a single bot instance with its configuration and state"""
    
    def __init__(
        self,
        bot_id: str,
        name: str,
        exchange: ExchangeBase,
        strategy: StrategyBase,
        symbol: str,
        config: Config,
        is_paper_trading: bool = True
    ):
        self.bot_id = bot_id
        self.name = name
        self.exchange = exchange
        self.strategy = strategy
        self.symbol = symbol
        self.config = config
        self.is_paper_trading = is_paper_trading
        
        # Initialize bot
        self.bot = TradingBot(exchange, strategy, config, is_paper_trading=is_paper_trading)
        
        # State
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.created_at = time.time()
        self.last_update = time.time()
        
        # Performance tracking
        self.total_trades = 0
        self.total_pnl = Decimal('0')
        self.start_balance = Decimal('10000')  # Default paper trading balance
        
        self.logger = setup_logger(f"{__name__}.BotInstance.{bot_id}")
    
    def start(self, check_interval: int = 30):
        """Start the bot instance"""
        if self.running:
            self.logger.warning(f"Bot {self.name} is already running")
            return False
        
        if not self.exchange.is_connected():
            self.logger.error(f"Exchange not connected for bot {self.name}")
            return False
        
        self.running = True
        
        def run_bot_loop():
            """Run bot trading loop in background"""
            try:
                while self.running:
                    try:
                        self.bot._trading_loop(self.symbol)
                        self.last_update = time.time()
                        
                        # Update performance metrics
                        if hasattr(self.bot, 'paper_trading') and self.bot.paper_trading:
                            # Track trades from paper trading
                            trades = self.bot.paper_trading.get_trade_history()
                            self.total_trades = len(trades)
                            if trades:
                                self.total_pnl = sum(Decimal(str(t.get('profit', 0))) for t in trades)
                        
                        time.sleep(check_interval)
                    except Exception as e:
                        self.logger.error(f"Error in bot loop for {self.name}: {e}")
                        time.sleep(check_interval)
            except Exception as e:
                self.logger.error(f"Fatal error in bot thread for {self.name}: {e}")
            finally:
                self.running = False
        
        self.thread = threading.Thread(target=run_bot_loop, daemon=True, name=f"Bot-{self.bot_id}")
        self.thread.start()
        self.logger.info(f"Bot {self.name} started")
        return True
    
    def stop(self):
        """Stop the bot instance"""
        if not self.running:
            return False
        
        self.running = False
        self.bot.stop()
        
        if self.thread and self.thread.is_alive():
            # Wait a bit for thread to finish
            self.thread.join(timeout=2.0)
        
        self.logger.info(f"Bot {self.name} stopped")
        return True
    
    def get_status(self) -> Dict:
        """Get current status of the bot"""
        current_balance = self.start_balance
        if hasattr(self.bot, 'paper_trading') and self.bot.paper_trading:
            current_balance = self.bot.paper_trading.get_balance()
        
        return_pct = 0
        if self.start_balance > 0:
            return_pct = float((current_balance - self.start_balance) / self.start_balance * 100)
        
        return {
            'bot_id': self.bot_id,
            'name': self.name,
            'symbol': self.symbol,
            'strategy': self.strategy.name,
            'exchange': self.exchange.name,
            'running': self.running,
            'balance': float(current_balance),
            'total_trades': self.total_trades,
            'total_pnl': float(self.total_pnl),
            'return_pct': return_pct,
            'positions': len(self.bot.positions) if hasattr(self.bot, 'positions') else 0,
            'created_at': self.created_at,
            'last_update': self.last_update
        }


class BotManager:
    """Manages multiple trading bot instances"""
    
    def __init__(self):
        self.bots: Dict[str, BotInstance] = {}
        self.logger = setup_logger(f"{__name__}.BotManager")
    
    def create_bot(
        self,
        name: str,
        exchange: ExchangeBase,
        strategy: StrategyBase,
        symbol: str,
        config: Config,
        is_paper_trading: bool = True
    ) -> str:
        """Create a new bot instance"""
        bot_id = str(uuid.uuid4())[:8]  # Short ID
        
        bot_instance = BotInstance(
            bot_id=bot_id,
            name=name,
            exchange=exchange,
            strategy=strategy,
            symbol=symbol,
            config=config,
            is_paper_trading=is_paper_trading
        )
        
        self.bots[bot_id] = bot_instance
        self.logger.info(f"Created bot: {name} (ID: {bot_id})")
        return bot_id
    
    def get_bot(self, bot_id: str) -> Optional[BotInstance]:
        """Get a bot instance by ID"""
        return self.bots.get(bot_id)
    
    def start_bot(self, bot_id: str, check_interval: int = 30) -> bool:
        """Start a bot instance"""
        bot = self.get_bot(bot_id)
        if not bot:
            self.logger.error(f"Bot {bot_id} not found")
            return False
        return bot.start(check_interval)
    
    def stop_bot(self, bot_id: str) -> bool:
        """Stop a bot instance"""
        bot = self.get_bot(bot_id)
        if not bot:
            return False
        return bot.stop()
    
    def delete_bot(self, bot_id: str) -> bool:
        """Delete a bot instance"""
        bot = self.get_bot(bot_id)
        if not bot:
            return False
        
        # Stop bot if running
        if bot.running:
            bot.stop()
        
        del self.bots[bot_id]
        self.logger.info(f"Deleted bot: {bot.name} (ID: {bot_id})")
        return True
    
    def get_all_bots(self) -> List[BotInstance]:
        """Get all bot instances"""
        return list(self.bots.values())
    
    def get_all_statuses(self) -> List[Dict]:
        """Get status of all bots"""
        return [bot.get_status() for bot in self.bots.values()]
    
    def stop_all(self):
        """Stop all bots"""
        for bot in self.bots.values():
            if bot.running:
                bot.stop()
    
    def get_running_count(self) -> int:
        """Get count of running bots"""
        return sum(1 for bot in self.bots.values() if bot.running)

