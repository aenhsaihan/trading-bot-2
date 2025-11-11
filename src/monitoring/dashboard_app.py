"""Streamlit dashboard application"""

import streamlit as st
import sys
import threading
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.config import Config
from src.exchanges.binance import BinanceExchange
from src.strategies.trend_following import TrendFollowingStrategy
from src.bot import TradingBot
from src.monitoring.metrics import MetricsCollector
from src.monitoring.streaming import DataStreamer
from src.analytics.trade_db import TradeDB
from src.analytics.export import DataExporter
from src.monitoring.dashboard import (
    render_mode_toggle,
    render_signal_alert,
    render_performance_metrics,
    render_price_chart,
    render_positions,
    render_trade_history,
    render_export_section,
    get_signal_color,
    get_pnl_color
)
import plotly.graph_objects as go
import pandas as pd
from decimal import Decimal
from datetime import datetime
import time


@st.cache_resource
def initialize_bot():
    """Initialize bot components (cached)"""
    config = Config()
    is_paper = config.is_paper_trading()
    
    # Initialize exchange (using Binance as default)
    api_key = config.get_exchange_api_key("binance")
    api_secret = config.get_exchange_api_secret("binance")
    # For paper trading without API keys, don't use sandbox (use public API)
    use_sandbox = is_paper and api_key is not None
    exchange = BinanceExchange(api_key=api_key, api_secret=api_secret, sandbox=use_sandbox)
    
    if not exchange.connect():
        st.error("Failed to connect to exchange. Trying public API without sandbox...")
        exchange = BinanceExchange(api_key=None, api_secret=None, sandbox=False)
        if not exchange.connect():
            st.error("Failed to connect to Binance. Please check your internet connection.")
            st.stop()
    
    # Initialize strategy
    strategy_config = config.get_strategy_config()
    strategy = TrendFollowingStrategy(config=strategy_config)
    
    # Initialize bot
    bot = TradingBot(exchange, strategy, config, is_paper_trading=is_paper)
    
    return bot, exchange, config


def main():
    """Main dashboard application"""
    st.set_page_config(page_title="Crypto Trading Bot", layout="wide", initial_sidebar_state="expanded")
    
    st.title("🤖 Crypto Trading Bot Dashboard")
    
    # Initialize components
    try:
        bot, exchange, config = initialize_bot()
    except Exception as e:
        st.error(f"Failed to initialize bot: {e}")
        st.stop()
    
    # Initialize other components
    if 'metrics_collector' not in st.session_state:
        st.session_state.metrics_collector = MetricsCollector()
    
    if 'streamer' not in st.session_state:
        st.session_state.streamer = DataStreamer(exchange, update_interval=2.0)
        st.session_state.streamer.start("BTC/USDT")
    
    if 'trade_db' not in st.session_state:
        st.session_state.trade_db = TradeDB(config.database_path)
    
    if 'exporter' not in st.session_state:
        st.session_state.exporter = DataExporter(st.session_state.trade_db)
    
    # Initialize bot_running state
    if 'bot_running' not in st.session_state:
        st.session_state.bot_running = False
    
    # Initialize bot thread
    if 'bot_thread' not in st.session_state:
        st.session_state.bot_thread = None
    
    # Register cleanup handler for graceful shutdown
    import atexit
    def cleanup():
        if 'streamer' in st.session_state:
            st.session_state.streamer.stop()
        if 'bot' in st.session_state:
            bot.stop()
    atexit.register(cleanup)
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # Mode toggle in sidebar
        mode_option = st.radio(
            "Trading Mode",
            options=["paper", "live"],
            format_func=lambda x: "📄 Paper Trading" if x == "paper" else "💸 Live Trading",
            index=0 if bot.is_paper_trading else 1,
            key="sidebar_mode"
        )
        
        if (mode_option == "paper") != bot.is_paper_trading:
            bot.set_trading_mode(mode_option == "paper")
            st.rerun()
        
        st.divider()
        
        # Symbol selection
        symbol = st.selectbox("Trading Pair", ["BTC/USDT", "ETH/USDT", "BNB/USDT"], index=0)
        
        # Bot controls
        st.subheader("Bot Controls")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("▶️ Start", width='stretch', disabled=st.session_state.bot_running):
                st.session_state.bot_running = True
                bot.running = True
                # Start bot thread if not already running
                if st.session_state.bot_thread is None or not st.session_state.bot_thread.is_alive():
                    def run_bot_loop():
                        """Run bot trading loop in background"""
                        check_interval = 30  # Check every 30 seconds
                        while st.session_state.bot_running and bot.running:
                            try:
                                # Run one iteration of trading loop (this handles all signal detection and trading)
                                bot._trading_loop(symbol)
                                
                                # Update metrics with current positions
                                positions = bot.positions
                                for pos_symbol, pos_data in positions.items():
                                    st.session_state.metrics_collector.update_position({
                                        'symbol': pos_symbol,
                                        'entry_price': float(pos_data.get('entry_price', 0)),
                                        'amount': float(pos_data.get('amount', 0))
                                    })
                                
                                time.sleep(check_interval)
                            except Exception as e:
                                import traceback
                                error_msg = f"Error in bot loop: {e}\n{traceback.format_exc()}"
                                print(error_msg)  # Print to console for debugging
                                time.sleep(check_interval)
                    
                    st.session_state.bot_thread = threading.Thread(target=run_bot_loop, daemon=True)
                    st.session_state.bot_thread.start()
                    st.success("✅ Bot started!")
                    st.rerun()
        with col2:
            if st.button("⏸️ Stop", width='stretch', disabled=not st.session_state.bot_running):
                st.session_state.bot_running = False
                bot.running = False
                bot.stop()
                st.warning("⏸️ Bot stopped")
                st.rerun()
        
        # Bot status indicator
        if st.session_state.bot_running:
            st.success("🟢 Bot is running")
        else:
            st.info("⚪ Bot is stopped")
    
    # Main content
    # Mode indicator at top
    mode_emoji = "📄" if bot.is_paper_trading else "💸"
    mode_text = "Paper Trading" if bot.is_paper_trading else "Live Trading"
    st.info(f"{mode_emoji} **{mode_text}** Mode | Exchange: {exchange.name}")
    
    # Get latest data
    latest_data = st.session_state.streamer.get_latest_data(symbol)
    
    # Main columns
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Price chart
        if latest_data and latest_data.get('ohlcv'):
            render_price_chart(latest_data['ohlcv'])
        else:
            st.warning("Loading price data...")
        
        # Current price display
        if latest_data:
            current_price = latest_data.get('price', 0)
            col_price1, col_price2, col_price3 = st.columns(3)
            with col_price1:
                st.metric("Current Price", f"${current_price:.2f}")
            with col_price2:
                st.metric("Bid", f"${latest_data.get('bid', 0):.2f}")
            with col_price3:
                st.metric("Ask", f"${latest_data.get('ask', 0):.2f}")
    
    with col2:
        # Performance metrics
        metrics = st.session_state.metrics_collector.get_metrics()
        render_performance_metrics(metrics.get('performance', {}))
        
        # Open positions
        positions = st.session_state.metrics_collector.get_open_positions()
        current_prices = {symbol: latest_data.get('price', 0)} if latest_data else {}
        render_positions(positions, current_prices)
        
        # Recent signals
        st.subheader("📡 Recent Signals")
        signals = st.session_state.metrics_collector.get_recent_signals(5)
        if signals:
            for signal in reversed(signals[-5:]):
                signal_type = signal.get('signal_type', 'hold')
                color = get_signal_color(signal_type)
                st.write(f"{color} **{signal_type.upper()}** - {signal.get('symbol', '')} @ ${signal.get('price', 0):.2f}")
        else:
            st.info("No signals yet")
    
    # Trade history
    st.divider()
    render_trade_history(st.session_state.metrics_collector.get_recent_trades(20))
    
    # Export section
    st.divider()
    render_export_section(st.session_state.exporter, symbol)
    
    # Auto-refresh (with error handling for graceful shutdown)
    try:
        time.sleep(2)
        st.rerun()
    except (KeyboardInterrupt, SystemExit):
        # Clean shutdown
        if 'streamer' in st.session_state:
            st.session_state.streamer.stop()
        raise


if __name__ == "__main__":
    main()

