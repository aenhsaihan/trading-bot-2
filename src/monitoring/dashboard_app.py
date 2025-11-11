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
    
    # Initialize containers for chart and table to prevent flickering (create once)
    if 'backtest_chart_container' not in st.session_state:
        st.session_state['backtest_chart_container'] = st.empty()
    if 'backtest_table_container' not in st.session_state:
        st.session_state['backtest_table_container'] = st.empty()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        backtest_symbol = st.selectbox("Symbol", ["BTC/USDT", "ETH/USDT", "BNB/USDT"], key="backtest_symbol")
    with col2:
        timeframe = st.selectbox("Timeframe", ["1h", "4h", "1d"], index=2, key="backtest_timeframe")
    with col3:
        # Calculate approximate date range based on candles
        timeframe_days = {"1h": 1/24, "4h": 1/6, "1d": 1}.get(timeframe, 1)
        max_candles = 10000
        max_days = int(max_candles * timeframe_days)
        limit = st.number_input("Candles", min_value=100, max_value=max_candles, value=1000, step=100, key="backtest_limit")
        st.caption(f"~{int(limit * timeframe_days)} days of data")
    with col4:
        # Quick presets
        preset = st.selectbox("Quick Preset", ["Custom", "1 Year", "2 Years", "5 Years", "Max"], key="backtest_preset")
        if preset != "Custom":
            preset_days = {"1 Year": 365, "2 Years": 730, "5 Years": 1825, "Max": 3650}.get(preset, 365)
            preset_candles = int(preset_days / timeframe_days)
            if preset_candles > max_candles:
                preset_candles = max_candles
            # Use preset value instead of manual input
            limit = preset_candles
            st.info(f"📅 {preset}: {preset_candles} candles")
        else:
            # Use the manual input value
            pass
    
    # Strategy parameters
    with st.expander("⚙️ Strategy Parameters (Advanced)"):
        st.write("**Current:** 50/200 MA (very conservative - few signals)")
        st.write("**Tip:** Shorter MA periods = more frequent signals but potentially more false signals")
        
        ma_preset = st.selectbox(
            "MA Period Preset",
            ["Conservative (50/200)", "Moderate (20/50)", "Aggressive (10/20)", "Custom"],
            key="ma_preset"
        )
        
        if ma_preset == "Custom":
            short_ma = st.number_input("Short MA Period", min_value=5, max_value=100, value=50, key="custom_short_ma")
            long_ma = st.number_input("Long MA Period", min_value=10, max_value=300, value=200, key="custom_long_ma")
        elif ma_preset == "Moderate (20/50)":
            short_ma = 20
            long_ma = 50
        elif ma_preset == "Aggressive (10/20)":
            short_ma = 10
            long_ma = 20
        else:  # Conservative
            short_ma = 50
            long_ma = 200
        
        rsi_threshold = st.slider("RSI Overbought Threshold", min_value=60, max_value=85, value=70, key="rsi_threshold")
        st.caption(f"Signals rejected if RSI ≥ {rsi_threshold}")
        
        # Store in session state for use in backtest
        st.session_state['backtest_short_ma'] = short_ma
        st.session_state['backtest_long_ma'] = long_ma
        st.session_state['backtest_rsi_threshold'] = rsi_threshold
    
    if st.button("🚀 Run Backtest", width='stretch'):
        # Clear previous rendered results ID when starting new backtest
        if 'last_rendered_results_id' in st.session_state:
            del st.session_state['last_rendered_results_id']
        
        with st.spinner(f"Fetching {limit} candles (this may take a moment for large datasets)..."):
            # Fetch historical data
            data_loader = DataLoader()
            ohlcv_data = data_loader.fetch_and_save(
                exchange, 
                backtest_symbol, 
                timeframe, 
                limit, 
                since=None,  # Start from earliest available
                save=False
            )
            
            if not ohlcv_data:
                st.error("Failed to fetch historical data")
                return
            
            # Run backtest with custom strategy parameters if set
            strategy_config = config.get_strategy_config().copy()
            
            # Override with user-selected parameters if available
            if 'backtest_short_ma' in st.session_state:
                strategy_config['short_ma_period'] = st.session_state['backtest_short_ma']
            if 'backtest_long_ma' in st.session_state:
                strategy_config['long_ma_period'] = st.session_state['backtest_long_ma']
            if 'backtest_rsi_threshold' in st.session_state:
                strategy_config['rsi_overbought'] = st.session_state['backtest_rsi_threshold']
            
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
            
            # Create a unique key for this results set
            results_id = str(hash(str(results.get('trades', [])) + str(results.get('initial_balance', 0))))
            
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
                
                # Show signal analysis if available
                signal_analysis = results.get('signal_analysis', {})
                if signal_analysis.get('potential_buys', 0) > 0:
                    st.warning(f"⚠️ Found {signal_analysis['potential_buys']} golden cross events, but all were rejected due to RSI being overbought (>70)")
                    if signal_analysis.get('rejected_buys'):
                        with st.expander("View rejected signals"):
                            rejected_df = pd.DataFrame(signal_analysis['rejected_buys'])
                            if 'timestamp' in rejected_df.columns:
                                rejected_df['timestamp'] = pd.to_datetime(rejected_df['timestamp'], unit='ms', errors='coerce')
                            st.dataframe(rejected_df.head(10), width='stretch')
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
            
            # Signal analysis
            signal_analysis = results.get('signal_analysis', {})
            if signal_analysis:
                st.divider()
                st.subheader("📊 Signal Analysis")
                col1, col2 = st.columns(2)
                with col1:
                    potential_buys = signal_analysis.get('potential_buys', 0)
                    actual_buys = len([t for t in results.get('trades', []) if t.get('type') == 'buy'])
                    st.metric("Golden Crosses Detected", potential_buys)
                    if potential_buys > 0:
                        conversion_rate = (actual_buys / potential_buys) * 100
                        st.metric("Conversion Rate", f"{conversion_rate:.1f}%")
                        st.caption(f"{actual_buys} trades executed out of {potential_buys} potential signals")
                with col2:
                    rejected = len(signal_analysis.get('rejected_buys', []))
                    if rejected > 0:
                        st.warning(f"⚠️ {rejected} signals rejected (RSI overbought)")
                        with st.expander("Why were signals rejected?"):
                            st.write("Signals were rejected because RSI was ≥ 70 (overbought) at the time of the golden cross.")
                            st.write("**Tip:** Consider using shorter MA periods (e.g., 20/50 instead of 50/200) for more frequent signals.")
                    else:
                        st.info("All golden crosses met RSI criteria")
            
            # Only render chart and table if results have changed
            if 'last_rendered_results_id' not in st.session_state or st.session_state.get('last_rendered_results_id') != results_id:
                st.session_state['last_rendered_results_id'] = results_id
                
                # Animated chart - render in container
                with st.session_state['backtest_chart_container'].container():
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
                        sell_times = [pd.to_datetime(t['timestamp'], unit='ms') for t in sell_trades if t.get('timestamp')]
                        sell_prices = [float(t['price']) for t in sell_trades if t.get('timestamp')]
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
                
                # Trade history table - render in container
                with st.session_state['backtest_table_container'].container():
                    st.divider()
                    st.subheader("📋 Trade History")
                    trades = results.get('trades', [])
                    if trades:
                        trades_df = pd.DataFrame(trades)
                        # Format timestamp
                        if 'timestamp' in trades_df.columns:
                            trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'], unit='ms', errors='coerce')
                        # Show only unique trades (in case of duplicates)
                        trades_df = trades_df.drop_duplicates(subset=['timestamp', 'type', 'price'], keep='first')
                        
                        # Create a more intuitive display
                        display_df = trades_df.copy()
                        
                        # Format columns for better readability
                        if 'price' in display_df.columns:
                            display_df['price'] = display_df['price'].apply(
                                lambda x: f"${float(x):,.2f}" if pd.notna(x) and str(x) != 'None' else ""
                            )
                        
                        if 'amount' in display_df.columns:
                            display_df['amount'] = display_df['amount'].apply(
                                lambda x: f"{float(x):.6f}" if pd.notna(x) and str(x) != 'None' and float(x) > 0 else ""
                            )
                        
                        if 'profit' in display_df.columns:
                            def format_profit(x):
                                if pd.isna(x) or str(x) == 'None' or str(x) == '':
                                    return "—"
                                try:
                                    val = float(x)
                                    if val == 0:
                                        return "—"
                                    return f"${val:,.2f}"
                                except:
                                    return "—"
                            display_df['profit'] = display_df['profit'].apply(format_profit)
                        
                        if 'timestamp' in display_df.columns:
                            display_df['timestamp'] = display_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
                        
                        # Format type column
                        if 'type' in display_df.columns:
                            display_df['type'] = display_df['type'].str.upper()
                        
                        # Format reason column
                        if 'reason' in display_df.columns:
                            display_df['reason'] = display_df['reason'].apply(
                                lambda x: x.replace('_', ' ').title() if pd.notna(x) and str(x) != 'None' else "—"
                            )
                        
                        # Rename columns for clarity
                        display_df = display_df.rename(columns={
                            'type': 'Action',
                            'symbol': 'Symbol',
                            'price': 'Price',
                            'timestamp': 'Date & Time',
                            'amount': 'Amount',
                            'reason': 'Reason',
                            'profit': 'P&L'
                        })
                        
                        # Reorder columns for better flow
                        column_order = ['Action', 'Symbol', 'Date & Time', 'Price', 'Amount', 'P&L', 'Reason']
                        available_columns = [col for col in column_order if col in display_df.columns]
                        display_df = display_df[available_columns]
                        
                        st.dataframe(display_df, width='stretch', hide_index=True)
                        
                        # Detailed Trade Reasoning Section
                        st.divider()
                        st.subheader("🔍 Trade Reasoning & Analysis")
                        st.write("**Understand why each trade was executed or rejected**")
                        
                        # Group trades into buy-sell pairs for better analysis
                        buy_trades = [t for t in trades if t.get('type') == 'buy']
                        sell_trades = [t for t in trades if t.get('type') == 'sell']
                        
                        for i, buy_trade in enumerate(buy_trades):
                            # Find corresponding sell trade
                            sell_trade = None
                            for sell in sell_trades:
                                if sell.get('timestamp', 0) > buy_trade.get('timestamp', 0):
                                    sell_trade = sell
                                    break
                            
                            buy_price_str = f"${float(buy_trade.get('price', 0)):,.2f}"
                            sell_price_str = f"SELL @ ${float(sell_trade.get('price', 0)):,.2f}" if sell_trade else "Still Open"
                            with st.expander(f"📊 Trade #{i+1}: {buy_trade.get('type', '').upper()} @ {buy_price_str} → {sell_price_str}", expanded=False):
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    st.markdown("**🟢 BUY Signal**")
                                    buy_time = pd.to_datetime(buy_trade.get('timestamp', 0), unit='ms')
                                    st.write(f"**Time:** {buy_time.strftime('%Y-%m-%d %H:%M:%S')}")
                                    st.write(f"**Price:** ${float(buy_trade.get('price', 0)):,.2f}")
                                    st.write(f"**Amount:** {float(buy_trade.get('amount', 0)):.6f}")
                                    
                                    buy_indicators = buy_trade.get('indicators', {})
                                    if buy_indicators:
                                        st.markdown("**Indicators at Entry:**")
                                        st.write(f"- Short MA: ${buy_indicators.get('short_ma', 0):,.2f}")
                                        st.write(f"- Long MA: ${buy_indicators.get('long_ma', 0):,.2f}")
                                        st.write(f"- RSI: {buy_indicators.get('rsi', 0):.1f}")
                                        st.write(f"- MACD: {buy_indicators.get('macd_line', 0):.4f}")
                                        
                                        # Explain why buy was triggered
                                        reason = buy_trade.get('reason', 'strategy_signal')
                                        if reason == 'golden_cross':
                                            st.success("✅ **Golden Cross Detected:** Short MA crossed above Long MA")
                                            if buy_indicators.get('rsi', 0) < 70:
                                                st.success(f"✅ **RSI Check:** {buy_indicators.get('rsi', 0):.1f} < 70 (not overbought)")
                                            else:
                                                st.warning(f"⚠️ **RSI Check:** {buy_indicators.get('rsi', 0):.1f} ≥ 70 (overbought, but trade executed)")
                                        else:
                                            st.info("✅ **Strategy Signal:** Buy conditions met")
                                    
                                if sell_trade:
                                    with col2:
                                        st.markdown("**🔴 SELL Signal**")
                                        sell_time = pd.to_datetime(sell_trade.get('timestamp', 0), unit='ms')
                                        st.write(f"**Time:** {sell_time.strftime('%Y-%m-%d %H:%M:%S')}")
                                        st.write(f"**Price:** ${float(sell_trade.get('price', 0)):,.2f}")
                                        
                                        profit = float(sell_trade.get('profit', 0))
                                        profit_color = "🟢" if profit > 0 else "🔴"
                                        st.write(f"**P&L:** {profit_color} ${profit:,.2f}")
                                        
                                        sell_indicators = sell_trade.get('indicators', {})
                                        if sell_indicators:
                                            st.markdown("**Indicators at Exit:**")
                                            st.write(f"- Short MA: ${sell_indicators.get('short_ma', 0):,.2f}")
                                            st.write(f"- Long MA: ${sell_indicators.get('long_ma', 0):,.2f}")
                                            st.write(f"- RSI: {sell_indicators.get('rsi', 0):.1f}")
                                            st.write(f"- MACD: {sell_indicators.get('macd_line', 0):.4f}")
                                        
                                        reason = sell_trade.get('reason', 'unknown')
                                        if reason == 'strategy':
                                            st.info("📉 **Strategy Signal:** Death cross or RSI overbought")
                                        elif reason == 'stop_loss':
                                            st.error("🛑 **Stop Loss:** Price dropped below stop loss threshold")
                                        elif reason == 'trailing_stop':
                                            st.warning("📊 **Trailing Stop:** Price reversed from peak")
                                        elif reason == 'end_of_backtest':
                                            st.info("📅 **End of Backtest:** Position closed at end of period")
                                        
                                        # Calculate duration
                                        duration = sell_time - buy_time
                                        st.write(f"**Duration:** {duration.days} days, {duration.seconds // 3600} hours")
                        
                        # Show rejected signals
                        signal_analysis = results.get('signal_analysis', {})
                        rejected_buys = signal_analysis.get('rejected_buys', [])
                        if rejected_buys:
                            st.divider()
                            st.subheader("❌ Rejected Buy Signals")
                            st.write(f"**{len(rejected_buys)} golden crosses were rejected due to RSI being overbought**")
                            
                            # Show first 5 rejected signals
                            for i, rejected in enumerate(rejected_buys[:5]):
                                with st.expander(f"Rejected Signal #{i+1}: RSI {rejected.get('rsi', 0):.1f} @ ${rejected.get('price', 0):,.2f}", expanded=False):
                                    reject_time = pd.to_datetime(rejected.get('timestamp', 0), unit='ms')
                                    st.write(f"**Time:** {reject_time.strftime('%Y-%m-%d %H:%M:%S')}")
                                    st.write(f"**Price:** ${rejected.get('price', 0):,.2f}")
                                    st.write(f"**RSI:** {rejected.get('rsi', 0):.1f}")
                                    st.warning(f"**Reason:** {rejected.get('reason', 'RSI too high')}")
                                    st.write("**Why rejected:** Golden cross occurred, but RSI was ≥ 70 (overbought threshold), so buy signal was rejected to avoid buying at peak.")
                            
                            if len(rejected_buys) > 5:
                                st.caption(f"... and {len(rejected_buys) - 5} more rejected signals")
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
        # Don't auto-refresh on backtesting tab to prevent flickering/repeating
    
    # Auto-refresh only on Live Trading tab (with error handling for graceful shutdown)
    # Use a session state variable to track active tab and disable refresh on backtesting tab
    if 'active_tab' not in st.session_state:
        st.session_state['active_tab'] = 'live'
    
    # Only auto-refresh if on Live Trading tab (not backtesting)
    # We detect this by checking if backtest results exist - if they do, user is likely viewing backtesting
    # But we'll use a simpler approach: disable auto-refresh entirely and let user manually refresh
    # Actually, let's keep auto-refresh but only when bot is running on live trading tab
    if st.session_state.get('bot_running', False):
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

