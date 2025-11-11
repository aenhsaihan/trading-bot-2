"""Main entry point for the trading bot"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.config import Config
from src.utils.logger import setup_logger
from src.exchanges.binance import BinanceExchange
from src.exchanges.coinbase import CoinbaseExchange
from src.exchanges.kraken import KrakenExchange
from src.strategies.trend_following import TrendFollowingStrategy
from src.bot import TradingBot
from src.monitoring.dashboard import main_dashboard
from src.monitoring.metrics import MetricsCollector
from src.monitoring.streaming import DataStreamer
from src.analytics.trade_db import TradeDB
from src.analytics.export import DataExporter


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Crypto Trading Bot")
    parser.add_argument("--mode", choices=["cli", "dashboard"], default="dashboard", help="Run mode")
    parser.add_argument("--symbol", default="BTC/USDT", help="Trading pair symbol")
    parser.add_argument("--exchange", default="binance", choices=["binance", "coinbase", "kraken"], help="Exchange to use")
    parser.add_argument("--paper", action="store_true", default=True, help="Use paper trading")
    parser.add_argument("--live", action="store_false", dest="paper", help="Use live trading")
    
    args = parser.parse_args()
    
    logger = setup_logger("main")
    logger.info("Starting Crypto Trading Bot")
    
    # Load configuration
    config = Config()
    is_paper_trading = args.paper or config.is_paper_trading()
    
    # Initialize exchange
    exchange_name = args.exchange.lower()
    if exchange_name == "binance":
        api_key = config.get_exchange_api_key("binance")
        api_secret = config.get_exchange_api_secret("binance")
        exchange = BinanceExchange(api_key=api_key, api_secret=api_secret, sandbox=is_paper_trading)
    elif exchange_name == "coinbase":
        api_key = config.get_exchange_api_key("coinbase")
        api_secret = config.get_exchange_api_secret("coinbase")
        exchange = CoinbaseExchange(api_key=api_key, api_secret=api_secret, sandbox=is_paper_trading)
    elif exchange_name == "kraken":
        api_key = config.get_exchange_api_key("kraken")
        api_secret = config.get_exchange_api_secret("kraken")
        exchange = KrakenExchange(api_key=api_key, api_secret=api_secret, sandbox=is_paper_trading)
    else:
        logger.error(f"Unknown exchange: {exchange_name}")
        return
    
    # Connect to exchange
    if not exchange.connect():
        logger.error("Failed to connect to exchange")
        return
    
    # Initialize strategy
    strategy_config = config.get_strategy_config()
    strategy = TrendFollowingStrategy(config=strategy_config)
    
    # Initialize bot
    bot = TradingBot(exchange, strategy, config, is_paper_trading=is_paper_trading)
    
    if args.mode == "dashboard":
        # Initialize dashboard components
        metrics_collector = MetricsCollector()
        streamer = DataStreamer(exchange, update_interval=1.0)
        trade_db = TradeDB(config.database_path)
        exporter = DataExporter(trade_db)
        
        # Start streaming
        streamer.start(args.symbol)
        
        # Run dashboard
        import streamlit.web.cli as stcli
        import streamlit as st
        
        # Note: Streamlit needs to be run differently
        # This is a placeholder - actual Streamlit app should be in a separate file
        logger.info("Starting Streamlit dashboard...")
        logger.warning("Please run: streamlit run src/monitoring/dashboard_app.py")
        
    else:
        # CLI mode
        logger.info(f"Starting bot in CLI mode for {args.symbol}")
        bot.start(args.symbol, check_interval=60)


if __name__ == "__main__":
    main()

