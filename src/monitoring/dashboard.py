"""Streamlit dashboard for real-time monitoring"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from decimal import Decimal
from typing import Dict, Optional
from datetime import datetime
import time


def get_signal_color(signal_type: str) -> str:
    """Get color for signal type"""
    if signal_type == "buy" or signal_type == "bullish":
        return "🟢"  # Green
    elif signal_type == "sell" or signal_type == "bearish":
        return "🔴"  # Red
    else:
        return "🟡"  # Yellow (hold/neutral)


def get_pnl_color(pnl: float) -> str:
    """Get color for P&L"""
    if pnl > 0:
        return "🟢"
    elif pnl < 0:
        return "🔴"
    else:
        return "🟡"


def render_mode_toggle():
    """Render trading mode toggle at top"""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### Trading Mode")
        mode = st.radio(
            "",
            options=["paper", "live"],
            format_func=lambda x: "📄 Paper Trading" if x == "paper" else "💸 Live Trading",
            horizontal=True,
            key="trading_mode_toggle"
        )
        return mode == "paper"


def render_signal_alert(signal_type: str, symbol: str, price: float, timestamp: str):
    """Render prominent signal alert"""
    color = get_signal_color(signal_type)
    
    if signal_type == "buy":
        st.success(f"## {color} BUY SIGNAL - {symbol}")
        st.info(f"Price: ${price:.2f} | Time: {timestamp}")
    elif signal_type == "sell":
        st.error(f"## {color} SELL SIGNAL - {symbol}")
        st.info(f"Price: ${price:.2f} | Time: {timestamp}")
    else:
        st.warning(f"## {color} HOLD - {symbol}")
        st.info(f"Price: ${price:.2f} | Time: {timestamp}")


def render_tooltip_icon(tooltip_text: str):
    """Render a hover tooltip icon with the given text"""
    tooltip_html = f"""
    <style>
    .tooltip-container {{
        position: relative;
        display: inline-block;
    }}
    .tooltip-icon {{
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
    }}
    .tooltip-text {{
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
    }}
    .tooltip-container:hover .tooltip-text {{
        visibility: visible;
        opacity: 1;
    }}
    .tooltip-text::after {{
        content: "";
        position: absolute;
        top: 100%;
        left: 50%;
        margin-left: -5px;
        border-width: 5px;
        border-style: solid;
        border-color: #333 transparent transparent transparent;
    }}
    </style>
    <div class="tooltip-container">
        <span class="tooltip-icon">ℹ</span>
        <span class="tooltip-text">{tooltip_text}</span>
    </div>
    """
    st.markdown(tooltip_html, unsafe_allow_html=True)


def render_performance_metrics(metrics: Dict):
    """Render performance metrics with color coding and hover tooltips"""
    st.subheader("📊 Performance Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_pnl = metrics.get('total_pnl', 0)
    win_rate = metrics.get('win_rate', 0)
    total_trades = metrics.get('total_trades', 0)
    sharpe = metrics.get('sharpe_ratio', 0)
    
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
    
    with col1:
        pnl_color = get_pnl_color(total_pnl)
        st.markdown("""
        <strong>Total P&L</strong> <span class="tooltip-container" style="display: inline-block;">
            <span class="tooltip-icon">ℹ</span>
            <span class="tooltip-text">Total profit or loss from all completed trades. Green = profit, Red = loss.</span>
        </span>
        """, unsafe_allow_html=True)
        st.metric("Total P&L", f"{pnl_color} ${total_pnl:.2f}", label_visibility="hidden")
    
    with col2:
        st.markdown("""
        <strong>Win Rate</strong> <span class="tooltip-container" style="display: inline-block;">
            <span class="tooltip-icon">ℹ</span>
            <span class="tooltip-text">Percentage of trades that were profitable. Higher is better (e.g., 60% means 6 out of 10 trades made money).</span>
        </span>
        """, unsafe_allow_html=True)
        st.metric("Win Rate", f"{win_rate:.1%}", label_visibility="hidden")
    
    with col3:
        st.markdown("""
        <strong>Total Trades</strong> <span class="tooltip-container" style="display: inline-block;">
            <span class="tooltip-icon">ℹ</span>
            <span class="tooltip-text">Number of completed buy-sell trade pairs.</span>
        </span>
        """, unsafe_allow_html=True)
        st.metric("Total Trades", total_trades, label_visibility="hidden")
    
    with col4:
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


def render_price_chart(ohlcv_data: list, indicators: Optional[Dict] = None):
    """Render price chart with indicators"""
    if not ohlcv_data:
        st.warning("No price data available")
        return
    
    df = pd.DataFrame(ohlcv_data)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1,
        row_heights=[0.7, 0.3],
        subplot_titles=('Price', 'Volume')
    )
    
    # Candlestick chart
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
    
    # Add moving averages if available
    if indicators:
        if indicators.get('short_ma'):
            fig.add_trace(
                go.Scatter(
                    x=df['timestamp'],
                    y=[indicators['short_ma']] * len(df),
                    name='Short MA',
                    line=dict(color='blue', width=1)
                ),
                row=1, col=1
            )
        
        if indicators.get('long_ma'):
            fig.add_trace(
                go.Scatter(
                    x=df['timestamp'],
                    y=[indicators['long_ma']] * len(df),
                    name='Long MA',
                    line=dict(color='orange', width=1)
                ),
                row=1, col=1
            )
    
    # Volume chart
    fig.add_trace(
        go.Bar(
            x=df['timestamp'],
            y=df['volume'],
            name='Volume',
            marker_color='lightblue'
        ),
        row=2, col=1
    )
    
    fig.update_layout(
        height=600,
        xaxis_rangeslider_visible=False,
        showlegend=True
    )
    
    st.plotly_chart(fig, width='stretch')


def render_positions(positions: list, current_prices: Dict[str, float]):
    """Render open positions with color-coded P&L"""
    st.subheader("💼 Open Positions")
    
    if not positions:
        st.info("No open positions")
        return
    
    for position in positions:
        symbol = position.get('symbol', '')
        entry_price = float(position.get('entry_price', 0))
        amount = float(position.get('amount', 0))
        current_price = current_prices.get(symbol, entry_price)
        
        pnl = (current_price - entry_price) * amount
        pnl_percent = ((current_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0
        
        pnl_color = get_pnl_color(pnl)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.write(f"**{symbol}**")
        with col2:
            st.write(f"Entry: ${entry_price:.2f}")
        with col3:
            st.write(f"Current: ${current_price:.2f}")
        with col4:
            st.write(f"{pnl_color} P&L: ${pnl:.2f} ({pnl_percent:.2f}%)")


def render_trade_history(trades: list):
    """Render trade history table"""
    st.subheader("📈 Trade History")
    
    if not trades:
        st.info("No trades yet")
        return
    
    df = pd.DataFrame(trades)
    st.dataframe(df, width='stretch')


def render_export_section(exporter, symbol: Optional[str] = None):
    """Render data export section"""
    st.subheader("📤 Export Data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        anonymize = st.checkbox("Anonymize data", value=False)
    
    with col2:
        export_format = st.selectbox("Format", ["JSON", "CSV", "Summary Report"])
    
    if st.button("Export Data"):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if export_format == "JSON":
            output_path = f"exports/report_{timestamp}.json"
            file_path = exporter.export_json(output_path, anonymize=anonymize, symbol=symbol)
            st.success(f"Exported to {file_path}")
            with open(file_path, 'r') as f:
                st.download_button("Download JSON", f.read(), file_name=f"report_{timestamp}.json", mime="application/json")
        
        elif export_format == "CSV":
            output_dir = f"exports/csv_{timestamp}"
            files = exporter.export_csv(output_dir, symbol=symbol)
            st.success(f"Exported CSV files to {output_dir}")
            for file_type, file_path in files.items():
                with open(file_path, 'r') as f:
                    st.download_button(f"Download {file_type}.csv", f.read(), file_name=f"{file_type}_{timestamp}.csv", mime="text/csv")
        
        else:  # Summary Report
            output_path = f"exports/summary_{timestamp}.md"
            file_path = exporter.export_summary_report(output_path, symbol=symbol)
            st.success(f"Exported to {file_path}")
            with open(file_path, 'r') as f:
                st.download_button("Download Report", f.read(), file_name=f"summary_{timestamp}.md", mime="text/markdown")


def main_dashboard(bot, metrics_collector, streamer, exporter, symbol: str = "BTC/USDT"):
    """Main dashboard function"""
    st.set_page_config(page_title="Crypto Trading Bot", layout="wide")
    
    st.title("🤖 Crypto Trading Bot Dashboard")
    
    # Mode toggle at top
    is_paper = render_mode_toggle()
    
    # Update bot mode if changed
    if bot.is_paper_trading != is_paper:
        bot.set_trading_mode(is_paper)
        st.rerun()
    
    # Status indicator
    status = bot.get_status()
    mode_emoji = "📄" if is_paper else "💸"
    st.info(f"{mode_emoji} Mode: {'Paper Trading' if is_paper else 'Live Trading'} | Status: {'🟢 Running' if status['running'] else '🔴 Stopped'}")
    
    # Main columns
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Get latest data
        latest_data = streamer.get_latest_data(symbol)
        
        if latest_data:
            # Price chart
            render_price_chart(latest_data.get('ohlcv', []))
            
            # Current price and signals
            current_price = latest_data.get('price', 0)
            st.metric("Current Price", f"${current_price:.2f}")
            
            # Signal display (would come from strategy)
            # This is a placeholder - in real implementation, get from bot
            st.info("🟡 Current Signal: HOLD")
        
        # Performance metrics
        metrics = metrics_collector.get_metrics()
        render_performance_metrics(metrics.get('performance', {}))
    
    with col2:
        # Controls
        st.subheader("⚙️ Controls")
        
        if st.button("▶️ Start Bot" if not status['running'] else "⏸️ Stop Bot"):
            if not status['running']:
                st.success("Bot started")
            else:
                st.warning("Bot stopped")
        
        # Settings panel with mode toggle
        with st.expander("⚙️ Settings"):
            st.radio(
                "Trading Mode",
                options=["paper", "live"],
                format_func=lambda x: "📄 Paper" if x == "paper" else "💸 Live",
                key="settings_mode"
            )
            
            st.slider("Check Interval (seconds)", 10, 300, 60)
        
        # Open positions
        positions = metrics_collector.get_open_positions()
        current_prices = {symbol: latest_data.get('price', 0)} if latest_data else {}
        render_positions(positions, current_prices)
        
        # Recent signals
        st.subheader("📡 Recent Signals")
        signals = metrics_collector.get_recent_signals(5)
        for signal in signals:
            signal_type = signal.get('signal_type', 'hold')
            color = get_signal_color(signal_type)
            st.write(f"{color} {signal_type.upper()} - {signal.get('symbol', '')} @ ${signal.get('price', 0):.2f}")
    
    # Trade history
    render_trade_history(metrics_collector.get_recent_trades(20))
    
    # Export section
    render_export_section(exporter, symbol)
    
    # Auto-refresh
    time.sleep(1)
    st.rerun()


if __name__ == "__main__":
    # This would be called from main.py with proper initialization
    st.warning("Dashboard should be run from main.py")

