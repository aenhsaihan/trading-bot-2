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
from src.backtesting.engine import BacktestEngine
from src.backtesting.data_loader import DataLoader
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
from plotly.subplots import make_subplots
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


def render_backtest_view(bot, exchange, config):
    """Render backtesting view with animated execution"""
    st.header("📊 Backtesting - Historical Performance")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        backtest_symbol = st.selectbox("Symbol", ["BTC/USDT", "ETH/USDT", "BNB/USDT"], key="backtest_symbol")
    with col2:
        timeframe = st.selectbox("Timeframe", ["1h", "4h", "1d"], index=0, key="backtest_timeframe")
    with col3:
        limit = st.number_input("Candles", min_value=100, max_value=2000, value=500, step=100, key="backtest_limit")
    
    if st.button("🚀 Run Backtest", width='stretch'):
        with st.spinner("Running backtest..."):
            # Fetch historical data
            data_loader = DataLoader()
            ohlcv_data = data_loader.fetch_and_save(
                exchange, 
                backtest_symbol, 
                timeframe, 
                limit, 
                save=False
            )
            
            if not ohlcv_data:
                st.error("Failed to fetch historical data")
                return
            
            # Run backtest
            strategy_config = config.get_strategy_config()
            strategy = TrendFollowingStrategy(config=strategy_config)
            
            risk_config = config.get_risk_config()
            backtest_engine = BacktestEngine(
                strategy=strategy,
                initial_balance=Decimal('10000'),
                stop_loss_percent=risk_config.get('stop_loss_percent', 0.03),
                trailing_stop_percent=risk_config.get('trailing_stop_percent', 0.025)
            )
            
            try:
                results = backtest_engine.run(
                    ohlcv_data,
                    backtest_symbol,
                    position_size_percent=risk_config.get('position_size_percent', 0.01)
                )
                
                # Store results in session state for animation (use different keys to avoid widget conflicts)
                st.session_state['backtest_results'] = results
                st.session_state['backtest_ohlcv'] = ohlcv_data
                st.session_state['backtest_result_symbol'] = backtest_symbol  # Different key to avoid widget conflict
                st.success("✅ Backtest completed!")
            except Exception as e:
                st.error(f"Error running backtest: {e}")
                import traceback
                st.code(traceback.format_exc())
    
    # Display results if available
    if 'backtest_results' in st.session_state and st.session_state.get('backtest_results'):
        try:
            results = st.session_state['backtest_results']
            ohlcv_data = st.session_state['backtest_ohlcv']
            symbol = st.session_state.get('backtest_result_symbol', backtest_symbol)
            
            # Validate results structure
            if not isinstance(results, dict):
                st.error(f"Invalid backtest results format. Got: {type(results)}")
                st.json({})
                return
            
            # Handle case where no trades were executed (backtest returns minimal dict)
            if 'initial_balance' not in results:
                # This happens when no trades were executed - show message and basic info
                st.info("ℹ️ No trades were executed during this backtest period. The strategy didn't find any buy signals.")
                st.metric("Total Trades", results.get('total_trades', 0))
                st.metric("Total P&L", f"${results.get('total_pnl', 0):,.2f}")
                return
            
            # Performance metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Initial Balance", f"${results.get('initial_balance', 0):,.2f}")
            with col2:
                st.metric("Final Balance", f"${results.get('final_balance', 0):,.2f}")
            with col3:
                return_pct = results.get('total_return', 0)
                st.metric("Total Return", f"{return_pct:.2f}%", delta=f"{return_pct:.2f}%")
            with col4:
                st.metric("Total Trades", results.get('total_trades', 0))
            
            col1, col2, col3 = st.columns(3)
            with col1:
                win_rate = results.get('win_rate', 0)
                st.metric("Win Rate", f"{win_rate:.1%}")
            with col2:
                st.metric("Sharpe Ratio", f"{results.get('sharpe_ratio', 0):.2f}")
            with col3:
                total_pnl = results.get('total_pnl', 0)
                pnl_color = "🟢" if total_pnl > 0 else "🔴"
                st.metric("Total P&L", f"{pnl_color} ${total_pnl:,.2f}")
            
            # Animated chart
            st.subheader("📈 Animated Execution")
            
            # Prepare data for animation
            df = pd.DataFrame(ohlcv_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Create figure with subplots
            fig = make_subplots(
                rows=2,
                cols=1,
                shared_xaxes=True,
                vertical_spacing=0.1,
                row_heights=[0.7, 0.3],
                subplot_titles=('Price & Trades', 'Equity Curve')
            )
            
            # Price candlestick
            fig.add_trace(
                go.Candlestick(
                    x=df['timestamp'],
                    open=df['open'],
                    high=df['high'],
                    low=df['low'],
                    close=df['close'],
                    name='Price'
                ),
                row=1, col=1
            )
            
            # Mark buy trades
            buy_trades = [t for t in results.get('trades', []) if t.get('type') == 'buy']
            if buy_trades:
                buy_times = [pd.to_datetime(t['timestamp'], unit='ms') for t in buy_trades if t.get('timestamp')]
                buy_prices = [float(t['price']) for t in buy_trades]
                if buy_times:
                    fig.add_trace(
                        go.Scatter(
                            x=buy_times,
                            y=buy_prices,
                            mode='markers',
                            marker=dict(symbol='triangle-up', size=15, color='green'),
                            name='Buy',
                            showlegend=True
                        ),
                        row=1, col=1
                    )
            
            # Mark sell trades
            sell_trades = [t for t in results.get('trades', []) if t.get('type') == 'sell']
            if sell_trades:
                sell_times = [pd.to_datetime(t.get('timestamp', 0), unit='ms') if t.get('timestamp') else df['timestamp'].iloc[-1] for t in sell_trades]
                sell_prices = [float(t['price']) for t in sell_trades]
                if sell_times:
                    fig.add_trace(
                        go.Scatter(
                            x=sell_times,
                            y=sell_prices,
                            mode='markers',
                            marker=dict(symbol='triangle-down', size=15, color='red'),
                            name='Sell',
                            showlegend=True
                        ),
                        row=1, col=1
                    )
            
            # Equity curve
            equity_curve = results.get('equity_curve', [])
            if equity_curve:
                equity_df = pd.DataFrame(equity_curve)
                equity_df['timestamp'] = pd.to_datetime(equity_df['timestamp'], unit='ms')
                fig.add_trace(
                    go.Scatter(
                        x=equity_df['timestamp'],
                        y=equity_df['equity'],
                        mode='lines',
                        name='Equity',
                        line=dict(color='blue', width=2)
                    ),
                    row=2, col=1
                )
            
            fig.update_layout(
                height=800,
                xaxis_rangeslider_visible=False,
                showlegend=True,
                title=f"Backtest Results: {symbol}"
            )
            
            st.plotly_chart(fig, width='stretch')
            
            # Trade history table
            st.subheader("📋 Trade History")
            trades = results.get('trades', [])
            if trades:
                trades_df = pd.DataFrame(trades)
                # Format timestamp
                if 'timestamp' in trades_df.columns:
                    trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'], unit='ms', errors='coerce')
                st.dataframe(trades_df, width='stretch')
            else:
                st.info("No trades executed during backtest")
        except Exception as e:
            st.error(f"Error displaying backtest results: {e}")
            import traceback
            st.code(traceback.format_exc())


def main():
    """Main dashboard application"""
    st.set_page_config(page_title="Crypto Trading Bot", layout="wide", initial_sidebar_state="expanded")
    
    st.title("🤖 Crypto Trading Bot Dashboard")
    
    # Add tabs for Live Trading and Backtesting
    tab1, tab2 = st.tabs(["📈 Live Trading", "📊 Backtesting"])
    
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
                        # Use bot.running instead of st.session_state (not accessible from threads)
                        while bot.running:
                            try:
                                # Run one iteration of trading loop (this handles all signal detection and trading)
                                bot._trading_loop(symbol)
                                
                                # Update metrics with current positions
                                # Note: We can't access st.session_state from thread, so we'll update via bot's logger
                                positions = bot.positions
                                if positions:
                                    bot.logger.info(f"Open positions: {list(positions.keys())}")
                                
                                time.sleep(check_interval)
                            except Exception as e:
                                import traceback
                                error_msg = f"Error in bot loop: {e}\n{traceback.format_exc()}"
                                bot.logger.error(error_msg)
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
    
    # Tab content
    with tab1:
        # Sync bot state with session state (for UI)
        st.session_state.bot_running = bot.running
        
        # Update metrics from bot positions (read from main thread)
        if bot.running:
            positions = bot.positions
            for pos_symbol, pos_data in positions.items():
                st.session_state.metrics_collector.update_position({
                    'symbol': pos_symbol,
                    'entry_price': float(pos_data.get('entry_price', 0)),
                    'amount': float(pos_data.get('amount', 0))
                })
        
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
            # Current Signal Analysis (real-time)
            st.subheader("🔍 Current Signal Analysis")
            if latest_data and latest_data.get('ohlcv'):
                try:
                    # Get current indicators
                    ohlcv_data = latest_data['ohlcv']
                    market_data = {
                        'symbol': symbol,
                        'ohlcv': ohlcv_data,
                        'current_price': Decimal(str(latest_data.get('price', 0))),
                        'ticker': latest_data
                    }
                    
                    indicators = bot.strategy._calculate_indicators(ohlcv_data)
                    position = bot._get_position(symbol)
                    
                    if indicators:
                        # Display current indicator values
                        short_ma = indicators.get('short_ma', 0)
                        long_ma = indicators.get('long_ma', 0)
                        rsi = indicators.get('rsi', 0)
                        macd_line = indicators.get('macd_line', 0)
                        macd_signal = indicators.get('macd_signal', 0)
                        
                        # Determine current signal
                        if position:
                            should_sell = bot.strategy.should_sell(market_data, position)
                            current_signal = "SELL" if should_sell else "HOLD"
                            signal_color = "🔴" if should_sell else "🟡"
                        else:
                            should_buy = bot.strategy.should_buy(market_data)
                            current_signal = "BUY" if should_buy else "HOLD"
                            signal_color = "🟢" if should_buy else "🟡"
                        
                        st.markdown(f"### {signal_color} **{current_signal}**")
                        
                        # Show indicator values
                        col_ind1, col_ind2 = st.columns(2)
                        with col_ind1:
                            st.metric("Short MA", f"${short_ma:.2f}")
                            st.metric("RSI", f"{rsi:.1f}")
                        with col_ind2:
                            st.metric("Long MA", f"${long_ma:.2f}")
                            st.metric("MACD", f"{macd_line:.4f}")
                        
                        # Show why it's holding (if not trading)
                        if current_signal == "HOLD":
                            reasons = []
                            if position:
                                if short_ma >= long_ma:
                                    reasons.append("✓ Short MA above Long MA (bullish)")
                                else:
                                    reasons.append("✗ Short MA below Long MA (bearish)")
                                if rsi < 70:
                                    reasons.append("✓ RSI not overbought")
                                else:
                                    reasons.append("✗ RSI overbought")
                            else:
                                if short_ma > long_ma:
                                    reasons.append("✓ Short MA above Long MA")
                                else:
                                    reasons.append("✗ Waiting for golden cross (Short MA > Long MA)")
                                if rsi < 70:
                                    reasons.append("✓ RSI not overbought")
                                else:
                                    reasons.append("✗ RSI too high")
                                if macd_line > macd_signal:
                                    reasons.append("✓ MACD bullish")
                                else:
                                    reasons.append("✗ MACD not bullish")
                            
                            with st.expander("Why HOLD?"):
                                for reason in reasons:
                                    st.write(reason)
                        
                        # Show next check time
                        if bot.running:
                            st.caption(f"⏱️ Next check in ~30 seconds")
                    else:
                        st.info("Calculating indicators...")
                except Exception as e:
                    st.warning(f"Error analyzing signals: {e}")
            
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
    
    with tab2:
        # Backtesting view
        render_backtest_view(bot, exchange, config)
    
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

