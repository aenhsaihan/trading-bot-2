"""Streamlit dashboard application"""

import streamlit as st
import sys
import threading
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# App version - update this when deploying major changes
APP_VERSION = "1.3.0"
APP_BUILD_DATE = "2025-11-12"

from src.utils.config import Config
from src.exchanges.binance import BinanceExchange
from src.strategies.trend_following import TrendFollowingStrategy
from src.strategies.registry import StrategyRegistry
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
    get_pnl_color,
    render_tooltip_icon
)
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from decimal import Decimal
from datetime import datetime
import time


def initialize_bot(exchange_name: str, strategy_name: str = "trend_following"):
    """Initialize bot components with selected exchange and strategy"""
    config = Config()
    is_paper = config.is_paper_trading()
    
    # Initialize exchange based on selection
    exchange = None
    connection_error = None
    
    try:
        if exchange_name == "Binance":
            api_key = config.get_exchange_api_key("binance")
            api_secret = config.get_exchange_api_secret("binance")
            use_sandbox = is_paper and api_key is not None
            exchange = BinanceExchange(api_key=api_key, api_secret=api_secret, sandbox=use_sandbox)
            if not exchange.connect():
                connection_error = "Binance connection failed. This may be due to regional restrictions or API downtime."
        elif exchange_name == "Coinbase":
            from src.exchanges.coinbase import CoinbaseExchange
            api_key = config.get_exchange_api_key("coinbase")
            api_secret = config.get_exchange_api_secret("coinbase")
            exchange = CoinbaseExchange(api_key=api_key, api_secret=api_secret, sandbox=False)
            if not exchange.connect():
                connection_error = "Coinbase connection failed. Check your network connection or API credentials."
        elif exchange_name == "Kraken":
            from src.exchanges.kraken import KrakenExchange
            api_key = config.get_exchange_api_key("kraken")
            api_secret = config.get_exchange_api_secret("kraken")
            exchange = KrakenExchange(api_key=api_key, api_secret=api_secret, sandbox=False)
            if not exchange.connect():
                connection_error = "Kraken connection failed. Check your network connection or API credentials."
        else:
            connection_error = f"Unknown exchange: {exchange_name}"
    except Exception as e:
        connection_error = f"Error initializing {exchange_name}: {str(e)}"
        exchange = None
    
    if exchange is None or connection_error:
        return None, None, config, None, connection_error
    
    # Initialize strategy using registry
    try:
        strategy_config = config.get_strategy_config()
        strategy = StrategyRegistry.get_strategy(strategy_name, config=strategy_config)
    except Exception as e:
        connection_error = f"Error initializing strategy '{strategy_name}': {str(e)}"
        return None, None, config, None, connection_error
    
    # Initialize bot
    bot = TradingBot(exchange, strategy, config, is_paper_trading=is_paper)
    
    return bot, exchange, config, exchange_name, None


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
        
        # Initialize MA preset in session state if not exists
        if 'ma_preset' not in st.session_state:
            st.session_state.ma_preset = "Conservative (50/200)"
        
        # Use form to batch widget changes and prevent immediate reruns
        with st.form(key="strategy_params_form", clear_on_submit=False):
            ma_preset = st.selectbox(
                "MA Period Preset",
                ["Conservative (50/200)", "Moderate (20/50)", "Aggressive (10/20)", "Custom"],
                index=["Conservative (50/200)", "Moderate (20/50)", "Aggressive (10/20)", "Custom"].index(st.session_state.ma_preset) if st.session_state.ma_preset in ["Conservative (50/200)", "Moderate (20/50)", "Aggressive (10/20)", "Custom"] else 0,
                key="ma_preset_form"
            )
            
            if ma_preset == "Custom":
                # Initialize custom values if not set
                if 'custom_short_ma' not in st.session_state:
                    st.session_state.custom_short_ma = 50
                if 'custom_long_ma' not in st.session_state:
                    st.session_state.custom_long_ma = 200
                short_ma = st.number_input("Short MA Period", min_value=5, max_value=100, value=st.session_state.custom_short_ma, key="custom_short_ma_form")
                long_ma = st.number_input("Long MA Period", min_value=10, max_value=300, value=st.session_state.custom_long_ma, key="custom_long_ma_form")
            elif ma_preset == "Moderate (20/50)":
                short_ma = 20
                long_ma = 50
            elif ma_preset == "Aggressive (10/20)":
                short_ma = 10
                long_ma = 20
            else:  # Conservative
                short_ma = 50
                long_ma = 200
            
            # Initialize RSI threshold if not set
            if 'rsi_threshold' not in st.session_state:
                st.session_state.rsi_threshold = 70
            
            rsi_threshold = st.slider("RSI Overbought Threshold", min_value=60, max_value=85, value=st.session_state.rsi_threshold, key="rsi_threshold_form")
            st.caption(f"Signals rejected if RSI ≥ {rsi_threshold}")
            
            # Submit button to apply changes
            form_submitted = st.form_submit_button("Apply Parameters", use_container_width=True)
            
            if form_submitted:
                # Update session state when form is submitted
                st.session_state.ma_preset = ma_preset
                if ma_preset == "Custom":
                    st.session_state.custom_short_ma = short_ma
                    st.session_state.custom_long_ma = long_ma
                st.session_state.rsi_threshold = rsi_threshold
                st.session_state['backtest_short_ma'] = short_ma
                st.session_state['backtest_long_ma'] = long_ma
                st.session_state['backtest_rsi_threshold'] = rsi_threshold
                st.success("✅ Parameters updated!")
        
        # Display current values (read from session state)
        current_short_ma = st.session_state.get('backtest_short_ma', 50)
        current_long_ma = st.session_state.get('backtest_long_ma', 200)
        current_rsi = st.session_state.get('backtest_rsi_threshold', 70)
        st.info(f"📊 **Active Parameters:** Short MA: {current_short_ma}, Long MA: {current_long_ma}, RSI Threshold: {current_rsi}")
    
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
            
            # Use selected strategy from session state or default to trend_following
            backtest_strategy_name = st.session_state.get('selected_strategy', 'trend_following')
            strategy = StrategyRegistry.get_strategy(backtest_strategy_name, config=strategy_config)
            
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
                current_strategy = st.session_state.get('selected_strategy', 'trend_following')
                st.session_state['backtest_results'] = results
                st.session_state['backtest_ohlcv'] = ohlcv_data
                st.session_state['backtest_result_symbol'] = backtest_symbol  # Different key to avoid widget conflict
                st.session_state['backtest_result_strategy'] = current_strategy  # Track which strategy these results are for
                st.success("✅ Backtest completed!")
            except Exception as e:
                st.error(f"Error running backtest: {e}")
                import traceback
                st.code(traceback.format_exc())
    
    # Display results if available (only if they're for the current strategy)
    current_strategy = st.session_state.get('selected_strategy', 'trend_following')
    results_strategy = st.session_state.get('backtest_result_strategy', None)
    
    if 'backtest_results' in st.session_state and st.session_state.get('backtest_results'):
        # Only show results if they're for the current strategy
        if results_strategy != current_strategy:
            # Clear old results from different strategy
            if 'backtest_results' in st.session_state:
                del st.session_state.backtest_results
            if 'backtest_result_symbol' in st.session_state:
                del st.session_state.backtest_result_symbol
            if 'backtest_result_strategy' in st.session_state:
                del st.session_state.backtest_result_strategy
            if 'backtest_ohlcv' in st.session_state:
                del st.session_state.backtest_ohlcv
            if 'last_rendered_results_id' in st.session_state:
                del st.session_state.last_rendered_results_id
            # Don't display anything - results cleared
        else:
            # Display backtest results
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
            # Add CSS once at the top
            st.markdown("""
            <style>
            .tooltip-container {
                position: relative;
                display: inline-block;
            }
            .tooltip-icon {
                display: inline-block;
                width: 16px;
                height: 16px;
                line-height: 16px;
                text-align: center;
                background-color: #1f77b4;
                color: white;
                border-radius: 50%;
                font-size: 11px;
                font-weight: bold;
                cursor: help;
                vertical-align: middle;
                margin-left: 4px;
            }
            .tooltip-text {
                visibility: hidden;
                width: 250px;
                background-color: #333;
                color: #fff;
                text-align: left;
                border-radius: 6px;
                padding: 8px;
                position: absolute;
                z-index: 1000;
                bottom: 125%;
                left: 50%;
                margin-left: -125px;
                opacity: 0;
                transition: opacity 0.3s;
                font-size: 12px;
                line-height: 1.4;
                box-shadow: 0 2px 8px rgba(0,0,0,0.3);
            }
            .tooltip-container:hover .tooltip-text {
                visibility: visible;
                opacity: 1;
            }
            .tooltip-text::after {
                content: "";
                position: absolute;
                top: 100%;
                left: 50%;
                margin-left: -5px;
                border-width: 5px;
                border-style: solid;
                border-color: #333 transparent transparent transparent;
            }
            </style>
            """, unsafe_allow_html=True)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown("""
                <strong>Initial Balance</strong> <span class="tooltip-container" style="display: inline-block;">
                    <span class="tooltip-icon">ℹ</span>
                    <span class="tooltip-text">Starting capital for the backtest.</span>
                </span>
                """, unsafe_allow_html=True)
                st.metric("Initial Balance", f"${results.get('initial_balance', 0):,.2f}", label_visibility="hidden")
            with col2:
                st.markdown("""
                <strong>Final Balance</strong> <span class="tooltip-container" style="display: inline-block;">
                    <span class="tooltip-icon">ℹ</span>
                    <span class="tooltip-text">Ending capital after all trades.</span>
                </span>
                """, unsafe_allow_html=True)
                st.metric("Final Balance", f"${results.get('final_balance', 0):,.2f}", label_visibility="hidden")
            with col3:
                return_pct = results.get('total_return', 0)
                st.markdown("""
                <strong>Total Return</strong> <span class="tooltip-container" style="display: inline-block;">
                    <span class="tooltip-icon">ℹ</span>
                    <span class="tooltip-text">Percentage gain or loss from initial to final balance.</span>
                </span>
                """, unsafe_allow_html=True)
                st.metric("Total Return", f"{return_pct:.2f}%", delta=f"{return_pct:.2f}%", label_visibility="hidden")
            with col4:
                st.markdown("""
                <strong>Total Trades</strong> <span class="tooltip-container" style="display: inline-block;">
                    <span class="tooltip-icon">ℹ</span>
                    <span class="tooltip-text">Number of completed buy-sell trade pairs.</span>
                </span>
                """, unsafe_allow_html=True)
                st.metric("Total Trades", results.get('total_trades', 0), label_visibility="hidden")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                win_rate = results.get('win_rate', 0)
                st.markdown("""
                <strong>Win Rate</strong> <span class="tooltip-container" style="display: inline-block;">
                    <span class="tooltip-icon">ℹ</span>
                    <span class="tooltip-text">Percentage of trades that were profitable. Higher is better (e.g., 60% means 6 out of 10 trades made money).</span>
                </span>
                """, unsafe_allow_html=True)
                st.metric("Win Rate", f"{win_rate:.1%}", label_visibility="hidden")
            with col2:
                sharpe = results.get('sharpe_ratio', 0)
                sharpe_interpretation = ""
                if sharpe >= 2:
                    sharpe_interpretation = "🟢 Excellent"
                elif sharpe >= 1:
                    sharpe_interpretation = "🟡 Good"
                else:
                    sharpe_interpretation = "🔴 Needs improvement"
                st.markdown(f"""
                <strong>Sharpe Ratio</strong> <span class="tooltip-container" style="display: inline-block;">
                    <span class="tooltip-icon">ℹ</span>
                    <span class="tooltip-text">Measures risk-adjusted returns. Higher is better:<br/>• &lt; 1: Poor (returns don't compensate for risk)<br/>• 1-2: Good<br/>• 2-3: Very good<br/>• &gt; 3: Excellent<br/><br/>A Sharpe ratio of 2 means you're earning 2 units of return for every unit of risk. {sharpe_interpretation}</span>
                </span>
                """, unsafe_allow_html=True)
                st.metric("Sharpe Ratio", f"{sharpe:.2f}", label_visibility="hidden")
            with col3:
                total_pnl = results.get('total_pnl', 0)
                pnl_color = "🟢" if total_pnl > 0 else "🔴"
                st.markdown("""
                <strong>Total P&L</strong> <span class="tooltip-container" style="display: inline-block;">
                    <span class="tooltip-icon">ℹ</span>
                    <span class="tooltip-text">Total profit or loss from all completed trades. Green = profit, Red = loss.</span>
                </span>
                """, unsafe_allow_html=True)
                st.metric("Total P&L", f"{pnl_color} ${total_pnl:,.2f}", label_visibility="hidden")
            
            # Signal analysis
            signal_analysis = results.get('signal_analysis', {})
            if signal_analysis:
                st.divider()
                st.subheader("📊 Signal Analysis")
                col1, col2 = st.columns(2)
                with col1:
                    potential_buys = signal_analysis.get('potential_buys', 0)
                    actual_buys = len([t for t in results.get('trades', []) if t.get('type') == 'buy'])
                    st.markdown("""
                    <strong>Golden Crosses Detected</strong> <span class="tooltip-container" style="display: inline-block;">
                        <span class="tooltip-icon">ℹ</span>
                        <span class="tooltip-text">Number of bullish crossover signals detected (when short MA crosses above long MA).</span>
                    </span>
                    """, unsafe_allow_html=True)
                    st.metric("Golden Crosses Detected", potential_buys, label_visibility="hidden")
                    if potential_buys > 0:
                        conversion_rate = (actual_buys / potential_buys) * 100
                        st.markdown("""
                        <strong>Conversion Rate</strong> <span class="tooltip-container" style="display: inline-block;">
                            <span class="tooltip-icon">ℹ</span>
                            <span class="tooltip-text">Percentage of potential buy signals that became trades. Low (&lt; 50%) might mean filters are too strict. High (&gt; 80%) means most signals are acted upon. Signals can be rejected if RSI is overbought (≥ 70) at the time of the golden cross.</span>
                        </span>
                        """, unsafe_allow_html=True)
                        st.metric("Conversion Rate", f"{conversion_rate:.1f}%", label_visibility="hidden")
                        st.caption(f"✅ {actual_buys} trades executed out of {potential_buys} potential signals")
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
                        # Debug: Show all sell reasons
                        sell_trades_debug = [t for t in trades if t.get('type') == 'sell']
                        if sell_trades_debug:
                            reasons_found = [t.get('reason', 'NO_REASON') for t in sell_trades_debug]
                            unique_reasons = set(reasons_found)
                            # st.caption(f"Debug: Found {len(sell_trades_debug)} sell trades with reasons: {unique_reasons}")
                        
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
                            def format_profit_with_pct(row):
                                profit_val = row.get('profit', 0) if isinstance(row, dict) else row
                                
                                if pd.isna(profit_val) or str(profit_val) == 'None' or str(profit_val) == '':
                                    return "—"
                                try:
                                    profit_float = float(profit_val)
                                    if profit_float == 0:
                                        return "—"
                                    
                                    # Add percentage if available
                                    pct_str = ""
                                    if 'profit_pct' in display_df.columns:
                                        pct_val = row.get('profit_pct', 0) if isinstance(row, dict) else display_df.loc[display_df.index[display_df.index.get_loc(row.name) if hasattr(row, 'name') else 0], 'profit_pct']
                                        if isinstance(pct_val, (int, float)) and pct_val != 0:
                                            pct_str = f" ({'+' if pct_val > 0 else ''}{pct_val:.2f}%)"
                                    
                                    return f"${profit_float:,.2f}{pct_str}"
                                except:
                                    return "—"
                            
                            # Format profit with percentage
                            if 'profit_pct' in display_df.columns:
                                display_df['profit'] = display_df.apply(
                                    lambda row: f"${float(row['profit']):,.2f} ({'+' if row['profit_pct'] > 0 else ''}{row['profit_pct']:.2f}%)" 
                                    if pd.notna(row['profit']) and str(row['profit']) != 'None' and float(row['profit']) != 0 else "—",
                                    axis=1
                                )
                            else:
                                display_df['profit'] = display_df['profit'].apply(
                                    lambda x: f"${float(x):,.2f}" if pd.notna(x) and str(x) != 'None' and float(x) != 0 else "—"
                                )
                        
                        if 'timestamp' in display_df.columns:
                            display_df['timestamp'] = display_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
                        
                        # Format type column
                        if 'type' in display_df.columns:
                            display_df['type'] = display_df['type'].str.upper()
                        
                        # Format reason column with clearer descriptions
                        if 'reason' in display_df.columns:
                            def format_reason(x):
                                if pd.isna(x) or str(x) == 'None':
                                    return "—"
                                reason_str = str(x).replace('_', ' ').title()
                                # Make specific reasons clearer
                                if 'death cross' in reason_str.lower():
                                    return "Death Cross"
                                elif 'rsi overbought' in reason_str.lower():
                                    return "RSI Overbought"
                                elif 'stop loss' in reason_str.lower():
                                    return "Stop Loss ⛔"
                                elif 'trailing stop' in reason_str.lower():
                                    return "Trailing Stop 📊"
                                elif 'end of backtest' in reason_str.lower():
                                    return "End of Backtest"
                                elif 'golden cross' in reason_str.lower():
                                    return "Golden Cross"
                                return reason_str
                            display_df['reason'] = display_df['reason'].apply(format_reason)
                        
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
                        
                        # Show risk management summary
                        sell_trades_debug = [t for t in trades if t.get('type') == 'sell']
                        if sell_trades_debug:
                            reasons_found = [str(t.get('reason', 'NO_REASON')) for t in sell_trades_debug]
                            unique_reasons = sorted(set(reasons_found))
                            
                            # Check if stop loss or trailing stop were triggered
                            stop_loss_triggered = any('stop_loss' in str(r).lower() for r in reasons_found)
                            trailing_stop_triggered = any('trailing_stop' in str(r).lower() for r in reasons_found)
                            
                            # Get risk config
                            risk_config = config.get_risk_config() if hasattr(config, 'get_risk_config') else {}
                            # Handle both decimal (0.03) and percentage (3.0) formats
                            stop_loss_raw = risk_config.get('stop_loss_percent', 0.03)
                            stop_loss_pct = stop_loss_raw if stop_loss_raw >= 1 else stop_loss_raw * 100
                            
                            trailing_stop_raw = risk_config.get('trailing_stop_percent', 0.025)
                            trailing_stop_pct = trailing_stop_raw if trailing_stop_raw >= 1 else trailing_stop_raw * 100
                            
                            # Show risk management status
                            st.info("🛡️ **Risk Management Status:**")
                            col1, col2 = st.columns(2)
                            with col1:
                                if stop_loss_triggered:
                                    st.success(f"✅ **Stop Loss:** Triggered ({stop_loss_pct:.1f}% protection)")
                                else:
                                    st.caption(f"⚪ **Stop Loss:** Active but not triggered ({stop_loss_pct:.1f}% protection)")
                            with col2:
                                if trailing_stop_triggered:
                                    st.success(f"✅ **Trailing Stop:** Triggered ({trailing_stop_pct:.1f}% trailing)")
                                else:
                                    st.caption(f"⚪ **Trailing Stop:** Active but not triggered ({trailing_stop_pct:.1f}% trailing)")
                            
                            if not stop_loss_triggered and not trailing_stop_triggered:
                                st.caption("💡 **Note:** Stop loss and trailing stop are active on all positions, but strategy signals (death cross, RSI overbought) fired first in this backtest.")
                            
                            # Debug expander
                            with st.expander("🔍 Debug: All Sell Reasons Found", expanded=False):
                                st.write(f"**Total sell trades:** {len(sell_trades_debug)}")
                                st.write(f"**Unique reasons:** {unique_reasons}")
                                for reason in unique_reasons:
                                    count = reasons_found.count(reason)
                                    st.write(f"- `{reason}`: {count} trade(s)")
                        
                        # Group trades into buy-sell pairs for better analysis
                        buy_trades = [t for t in trades if t.get('type') == 'buy']
                        sell_trades = [t for t in trades if t.get('type') == 'sell']
                        
                        # Track which sell trades have been matched
                        matched_sells = set()
                        
                        for i, buy_trade in enumerate(buy_trades):
                            # Find corresponding sell trade (first unmatched sell after this buy)
                            sell_trade = None
                            for j, sell in enumerate(sell_trades):
                                if j not in matched_sells and sell.get('timestamp', 0) > buy_trade.get('timestamp', 0):
                                    sell_trade = sell
                                    matched_sells.add(j)
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
                                        
                                        # Entry and exit prices
                                        entry_price = float(buy_trade.get('price', 0))
                                        exit_price = float(sell_trade.get('price', 0))
                                        st.write(f"**Entry Price:** ${entry_price:,.2f}")
                                        st.write(f"**Exit Price:** ${exit_price:,.2f}")
                                        
                                        # P&L in dollars and percentage
                                        profit = float(sell_trade.get('profit', 0))
                                        profit_pct = sell_trade.get('profit_pct', 0)
                                        if profit_pct == 0 and entry_price > 0:
                                            # Calculate if not stored
                                            profit_pct = ((exit_price - entry_price) / entry_price) * 100
                                        
                                        profit_color = "🟢" if profit > 0 else "🔴"
                                        profit_symbol = "+" if profit > 0 else ""
                                        st.write(f"**P&L:** {profit_color} {profit_symbol}${profit:,.2f} ({profit_symbol}{profit_pct:.2f}%)")
                                        
                                        # Show risk management status for this trade
                                        risk_config = config.get_risk_config() if hasattr(config, 'get_risk_config') else {}
                                        
                                        # Handle both decimal (0.03) and percentage (3.0) formats
                                        stop_loss_raw = risk_config.get('stop_loss_percent', 0.03)
                                        stop_loss_pct_config = stop_loss_raw if stop_loss_raw >= 1 else stop_loss_raw * 100
                                        stop_loss_decimal = stop_loss_raw / 100 if stop_loss_raw >= 1 else stop_loss_raw
                                        
                                        trailing_stop_raw = risk_config.get('trailing_stop_percent', 0.025)
                                        trailing_stop_pct_config = trailing_stop_raw if trailing_stop_raw >= 1 else trailing_stop_raw * 100
                                        trailing_stop_decimal = trailing_stop_raw / 100 if trailing_stop_raw >= 1 else trailing_stop_raw
                                        
                                        # Calculate what stop loss and trailing stop levels would have been
                                        stop_loss_price = entry_price * (1 - stop_loss_decimal)
                                        max_price_during_trade = exit_price  # Approximate - we don't track this exactly
                                        # For trailing stop, show what it would have been at exit
                                        trailing_stop_at_exit = exit_price * (1 - trailing_stop_decimal)
                                        
                                        st.caption(f"🛡️ **Risk Protection:** Stop Loss @ ${stop_loss_price:,.2f} ({stop_loss_pct_config:.1f}%), Trailing Stop @ {trailing_stop_pct_config:.1f}%")
                                        
                                        sell_indicators = sell_trade.get('indicators', {})
                                        if sell_indicators:
                                            st.markdown("**Indicators at Exit:**")
                                            st.write(f"- Short MA: ${sell_indicators.get('short_ma', 0):,.2f}")
                                            st.write(f"- Long MA: ${sell_indicators.get('long_ma', 0):,.2f}")
                                            st.write(f"- RSI: {sell_indicators.get('rsi', 0):.1f}")
                                            st.write(f"- MACD: {sell_indicators.get('macd_line', 0):.4f}")
                                        
                                        reason = sell_trade.get('reason', 'unknown')
                                        
                                        # Get config values from results
                                        rsi_threshold = results.get('strategy_config', {}).get('rsi_overbought', 70) if isinstance(results, dict) else 70
                                        
                                        # Normalize reason string for comparison (handle None, empty strings, etc.)
                                        if reason is None:
                                            reason_str = 'unknown'
                                        else:
                                            reason_str = str(reason).lower().strip()
                                        
                                        # Display reason with clear indicators
                                        st.markdown("**Exit Reason:**")
                                        
                                        # Get risk config for display (reuse from above if available, otherwise recalculate)
                                        if 'risk_config' not in locals():
                                            risk_config = config.get_risk_config() if hasattr(config, 'get_risk_config') else {}
                                            stop_loss_raw = risk_config.get('stop_loss_percent', 0.03)
                                            stop_loss_pct_display = stop_loss_raw if stop_loss_raw >= 1 else stop_loss_raw * 100
                                            trailing_stop_raw = risk_config.get('trailing_stop_percent', 0.025)
                                            trailing_stop_pct_display = trailing_stop_raw if trailing_stop_raw >= 1 else trailing_stop_raw * 100
                                        else:
                                            stop_loss_pct_display = stop_loss_pct_config
                                            trailing_stop_pct_display = trailing_stop_pct_config
                                        
                                        # Check for stop_loss and trailing_stop FIRST (priority order)
                                        if reason_str == 'stop_loss' or 'stop_loss' in reason_str:
                                            st.error(f"🛑 **Stop Loss Triggered:** Price dropped below stop loss threshold ({stop_loss_pct_display:.1f}% loss protection)")
                                            # Show stop loss details
                                            actual_loss_pct = ((entry_price - exit_price) / entry_price) * 100
                                            st.caption(f"Actual Loss: {actual_loss_pct:.2f}% (stopped at ${exit_price:,.2f} from entry ${entry_price:,.2f})")
                                        elif reason_str == 'trailing_stop' or 'trailing_stop' in reason_str:
                                            st.warning(f"📊 **Trailing Stop Triggered:** Price reversed from peak ({trailing_stop_pct_display:.1f}% trailing stop)")
                                            # Show trailing stop details
                                            if profit_pct > 0:
                                                st.caption(f"✅ Captured {profit_pct:.2f}% profit before reversal")
                                            else:
                                                st.caption(f"⚠️ Limited loss to {abs(profit_pct):.2f}%")
                                        elif reason_str == 'death_cross':
                                            st.info("📉 **Death Cross:** Short MA crossed below Long MA (bearish signal)")
                                        elif reason_str == 'rsi_overbought':
                                            rsi_val = sell_indicators.get('rsi', 0) if sell_indicators else 0
                                            st.warning(f"⚠️ **RSI Overbought:** RSI {rsi_val:.1f} > {rsi_threshold} (selling at peak)")
                                        elif reason_str == 'strategy':
                                            st.info("📉 **Strategy Signal:** General strategy sell condition")
                                        elif reason_str == 'end_of_backtest':
                                            st.info("📅 **End of Backtest:** Position closed at end of period")
                                        else:
                                            # Show what we actually got for debugging
                                            st.warning(f"⚠️ **Unknown Reason:** '{reason}' (normalized: '{reason_str}')")
                                            st.caption(f"Debug info: reason type={type(reason).__name__}, value={repr(reason)}")
                                            # Try to display it anyway
                                            st.info(f"📉 **Sell Reason:** {str(reason).replace('_', ' ').title() if reason else 'Unknown'}")
                                        
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
    
    # Display version info in sidebar
    with st.sidebar:
        st.caption(f"📦 Version {APP_VERSION}")
        st.caption(f"🔨 Build: {APP_BUILD_DATE}")
        st.divider()
        
        # Exchange selector
        st.subheader("🔌 Exchange Connection")
        
        # Initialize selected exchange in session state
        if 'selected_exchange' not in st.session_state:
            st.session_state.selected_exchange = "Binance"
        
        # Exchange dropdown
        exchange_options = ["Binance", "Coinbase", "Kraken"]
        selected_exchange = st.selectbox(
            "Select Exchange",
            options=exchange_options,
            index=exchange_options.index(st.session_state.selected_exchange) if st.session_state.selected_exchange in exchange_options else 0,
            key="exchange_selector"
        )
        
        # Update session state if exchange changed
        if selected_exchange != st.session_state.selected_exchange:
            st.session_state.selected_exchange = selected_exchange
            # Clear cached bot/exchange when exchange changes
            if 'cached_bot' in st.session_state:
                del st.session_state.cached_bot
            if 'cached_exchange' in st.session_state:
                del st.session_state.cached_exchange
            if 'cached_config' in st.session_state:
                del st.session_state.cached_config
            # Stop streamer if running
            if 'streamer' in st.session_state and st.session_state.streamer.running:
                st.session_state.streamer.stop()
            st.rerun()
        
        st.divider()
        
        # Strategy selector
        st.subheader("📈 Trading Strategy")
        
        # Initialize selected strategy in session state
        if 'selected_strategy' not in st.session_state:
            st.session_state.selected_strategy = "trend_following"
        
        # Get available strategies (force reload by accessing registry directly)
        try:
            # Reload registry module to pick up new strategies
            import importlib
            from src.strategies import registry
            importlib.reload(registry)
            from src.strategies.registry import StrategyRegistry
        except Exception as e:
            st.warning(f"Could not reload registry: {e}")
        
        available_strategies = StrategyRegistry.get_strategy_names()
        strategy_descriptions = StrategyRegistry.list_strategies()
        
        # Create display names for dropdown
        strategy_display_names = {name: StrategyRegistry.get_display_name(name) for name in available_strategies}
        strategy_options = [strategy_display_names[name] for name in available_strategies]
        
        # Find current selection index
        current_strategy_name = st.session_state.selected_strategy
        current_index = available_strategies.index(current_strategy_name) if current_strategy_name in available_strategies else 0
        
        # Strategy dropdown
        selected_strategy_display = st.selectbox(
            "Select Strategy",
            options=strategy_options,
            index=current_index,
            key="strategy_selector"
        )
        
        # Get the strategy name from display name
        selected_strategy_name = [name for name, display in strategy_display_names.items() if display == selected_strategy_display][0]
        
        # Show strategy description
        if selected_strategy_name in strategy_descriptions:
            st.caption(strategy_descriptions[selected_strategy_name])
        
        # Update session state if strategy changed
        if selected_strategy_name != st.session_state.selected_strategy:
            st.session_state.selected_strategy = selected_strategy_name
            # Clear cached bot/exchange when strategy changes
            if 'cached_bot' in st.session_state:
                del st.session_state.cached_bot
            if 'cached_exchange' in st.session_state:
                del st.session_state.cached_exchange
            if 'cached_config' in st.session_state:
                del st.session_state.cached_config
            # Clear backtest results when strategy changes (old results are for different strategy)
            if 'backtest_results' in st.session_state:
                del st.session_state.backtest_results
            if 'backtest_result_symbol' in st.session_state:
                del st.session_state.backtest_result_symbol
            if 'backtest_result_strategy' in st.session_state:
                del st.session_state.backtest_result_strategy
            if 'backtest_ohlcv' in st.session_state:
                del st.session_state.backtest_ohlcv
            if 'last_rendered_results_id' in st.session_state:
                del st.session_state.last_rendered_results_id
            # Stop streamer if running
            if 'streamer' in st.session_state and st.session_state.streamer.running:
                st.session_state.streamer.stop()
            st.rerun()
        
        st.divider()
    
    # Show connection status at the top (before tabs)
    connection_status_container = st.container()
    
    with connection_status_container:
        # Show connecting status
        selected_strategy_name = st.session_state.get('selected_strategy', 'trend_following')
        strategy_display = StrategyRegistry.get_display_name(selected_strategy_name)
        with st.spinner(f"🔄 Connecting to {selected_exchange} with {strategy_display} strategy..."):
            try:
                bot, exchange, config, connected_exchange, connection_error = initialize_bot(selected_exchange, selected_strategy_name)
            except Exception as e:
                st.error(f"❌ **Failed to initialize bot: {e}**")
                st.stop()
        
        # Display connection status prominently at the top
        if connected_exchange:
            st.success(f"✅ **Connected to {connected_exchange}** | 📈 **Strategy: {strategy_display}**")
            st.caption(f"📡 Using {connected_exchange} API for market data")
        elif connection_error:
            st.error(f"❌ **Connection Failed: {connection_error}**")
            st.info("💡 **Tips:**")
            st.info("• Check your internet connection")
            st.info("• Some exchanges may be blocked in certain regions")
            st.info("• Try selecting a different exchange")
            st.info("• For paper trading, API keys are optional (public data only)")
            st.stop()
        else:
            st.error("❌ **Failed to connect to exchange**")
            st.stop()
    
    st.divider()
    
    # Add tabs for Live Trading and Backtesting
    tab1, tab2 = st.tabs(["📈 Live Trading", "📊 Backtesting"])
    
    # Initialize other components
    if 'metrics_collector' not in st.session_state:
        st.session_state.metrics_collector = MetricsCollector()
    
    # Initialize streamer lazily - only create it, don't start it yet
    # We'll start it conditionally based on which tab is active
    # Recreate streamer if exchange changed
    if 'streamer' not in st.session_state or 'last_exchange' not in st.session_state or st.session_state.last_exchange != connected_exchange:
        # Stop old streamer if it exists
        if 'streamer' in st.session_state and st.session_state.streamer.running:
            st.session_state.streamer.stop()
        # Use much longer update interval to avoid rate limits (30 seconds for Kraken)
        # OHLCV data is fetched even less frequently (every 6 iterations = 3 minutes)
        st.session_state.streamer = DataStreamer(exchange, update_interval=30.0)
        st.session_state.streamer_started = False  # Track if we've started it
        st.session_state.last_exchange = connected_exchange
    
    # Use query parameter or session state to track active tab
    # Streamlit tabs don't expose which one is active directly
    # We'll start streamer only when Live Trading tab content is rendered
    
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
        
        st.divider()
        
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
        
        # Fetch OHLCV on-demand for charts (not from streamer to avoid rate limits)
        ohlcv_data = None
        if latest_data:
            try:
                # Fetch OHLCV on-demand when displaying chart
                ohlcv_data = exchange.get_ohlcv(symbol, timeframe="1h", limit=100)
            except Exception as e:
                st.warning(f"Could not fetch chart data: {e}")
        
        # Main columns
        col1, col2 = st.columns([2, 1])
    
        with col1:
            # Price chart
            if ohlcv_data:
                render_price_chart(ohlcv_data)
            elif latest_data:
                st.info("📊 Chart data loading... (Price: ${:,.2f})".format(latest_data.get('price', 0)))
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
            # Fetch OHLCV on-demand for indicators (not from streamer)
            try:
                # Get current indicators using on-demand OHLCV fetch
                ohlcv_for_indicators = exchange.get_ohlcv(symbol, timeframe="1h", limit=200)
                if ohlcv_for_indicators:
                    market_data = {
                        'symbol': symbol,
                        'ohlcv': ohlcv_for_indicators,
                        'current_price': Decimal(str(latest_data.get('price', 0))) if latest_data else Decimal('0'),
                        'ticker': latest_data if latest_data else {}
                    }
                    
                    indicators = bot.strategy._calculate_indicators(ohlcv_for_indicators)
                else:
                    indicators = {}
                    market_data = {}
            except Exception as e:
                st.warning(f"Could not fetch indicator data: {e}")
                indicators = {}
                market_data = {}
            
            if indicators:
                position = bot._get_position(symbol)
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
        # Stop streamer when on Backtesting tab to avoid rate limits
        if st.session_state.get('streamer_started', False) and st.session_state.streamer.running:
            st.session_state.streamer.stop()
            st.session_state.streamer_started = False
        
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

