# Crypto Trading Bot

A comprehensive cryptocurrency trading bot with trend-following strategy, risk management, backtesting, and real-time monitoring dashboard.

## Features

- **Multi-Exchange Support**: Binance, Coinbase Pro, Kraken (CEX) and Uniswap (DEX)
- **Trend Following Strategy**: Moving average crossover with RSI and MACD indicators
- **Risk Management**: Stop loss and trailing stop loss protection
- **Paper Trading**: Test strategies without real money
- **Live Trading**: Execute real trades on exchanges
- **Backtesting**: Test strategies on historical data
- **Real-Time Dashboard**: Streamlit dashboard with color-coded signals and metrics
- **Data Export**: Export trading data for analysis and sharing

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd trading-bot-2
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env and add your API keys
```

4. Configure strategy parameters in `config/strategy.yaml`

## Configuration

### Environment Variables (.env)

```env
# Exchange API Keys
BINANCE_API_KEY=your_binance_api_key
BINANCE_API_SECRET=your_binance_api_secret
COINBASE_API_KEY=your_coinbase_api_key
COINBASE_API_SECRET=your_coinbase_api_secret
KRAKEN_API_KEY=your_kraken_api_key
KRAKEN_API_SECRET=your_kraken_api_secret

# Trading Mode
TRADING_MODE=paper  # or 'live'

# Database
DATABASE_PATH=data/trades.db

# Logging
LOG_LEVEL=INFO
LOG_DIR=logs
```

### Strategy Configuration (config/strategy.yaml)

```yaml
trend_following:
  short_ma_period: 50      # Short moving average period
  long_ma_period: 200      # Long moving average period
  rsi_period: 14           # RSI period
  rsi_overbought: 70       # RSI overbought threshold
  rsi_oversold: 30         # RSI oversold threshold

risk_management:
  stop_loss_percent: 3.0           # Stop loss percentage (3%)
  trailing_stop_percent: 2.5      # Trailing stop percentage (2.5%)
  position_size_percent: 1.0       # Position size as % of balance (1%)
  max_positions: 5                  # Maximum concurrent positions
```

## Usage

### Dashboard Mode (Recommended)

Launch the Streamlit dashboard:

```bash
streamlit run src/monitoring/dashboard_app.py
```

The dashboard provides:
- **Trading Mode Toggle**: Switch between 📄 Paper and 💸 Live trading
- **Real-Time Price Charts**: Candlestick charts with indicators
- **Color-Coded Signals**: 🟢 Bullish, 🟡 Neutral, 🔴 Bearish
- **Performance Metrics**: P&L, win rate, Sharpe ratio
- **Open Positions**: View and monitor positions
- **Trade History**: Complete trade log
- **Data Export**: Export JSON, CSV, or summary reports

### CLI Mode

Run the bot from command line:

```bash
python main.py --mode cli --symbol BTC/USDT --exchange binance --paper
```

Options:
- `--mode`: `cli` or `dashboard` (default: dashboard)
- `--symbol`: Trading pair (default: BTC/USDT)
- `--exchange`: `binance`, `coinbase`, or `kraken` (default: binance)
- `--paper`: Use paper trading (default)
- `--live`: Use live trading

### Backtesting

Run backtests on historical data:

```python
from src.backtesting.data_loader import DataLoader
from src.backtesting.engine import BacktestEngine
from src.strategies.trend_following import TrendFollowingStrategy
from src.exchanges.binance import BinanceExchange

# Initialize components
exchange = BinanceExchange()
exchange.connect()
data_loader = DataLoader()

# Fetch historical data
ohlcv_data = data_loader.fetch_and_save(exchange, "BTC/USDT", "1h", limit=1000)

# Run backtest
strategy = TrendFollowingStrategy()
engine = BacktestEngine(strategy)
results = engine.run(ohlcv_data, "BTC/USDT")

print(f"Total Return: {results['total_return']:.2f}%")
print(f"Win Rate: {results['win_rate']:.2%}")
print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
```

## Trading Strategy

### Trend Following Strategy

The bot uses a trend-following strategy based on:

1. **Moving Average Crossover**:
   - Buy signal: Short MA crosses above Long MA (Golden Cross)
   - Sell signal: Short MA crosses below Long MA (Death Cross)

2. **RSI Indicator**:
   - Entry: RSI < 70 (not overbought)
   - Exit: RSI > 70 (overbought)

3. **MACD**: Additional momentum confirmation

### Risk Management

- **Stop Loss**: Fixed percentage below entry price (default: 3%)
- **Trailing Stop Loss**: Dynamic stop that trails price upward (default: 2.5%)
- **Position Sizing**: Risk a fixed percentage per trade (default: 1%)

## Dashboard Features

### Color-Coded Signals

- 🟢 **Green**: Bullish signals, positive P&L, upward trends
- 🟡 **Yellow**: Neutral signals, break-even, sideways movement
- 🔴 **Red**: Bearish signals, negative P&L, downward trends

### Real-Time Updates

- Sub-second price updates via WebSocket
- Automatic signal change detection
- Prominent alerts for crossover events
- Visual feedback for signal transitions

### Data Export

Export trading data in multiple formats:
- **JSON**: Comprehensive report with all data
- **CSV**: Separate files for trades, signals, performance
- **Summary Report**: Human-readable markdown report

Options:
- Anonymize data before export
- Filter by symbol
- Include market context data

## Project Structure

```
trading-bot-2/
├── src/
│   ├── exchanges/          # Exchange integrations
│   ├── strategies/         # Trading strategies
│   ├── risk/               # Risk management
│   ├── backtesting/        # Backtesting engine
│   ├── monitoring/         # Dashboard and monitoring
│   ├── analytics/          # Data analysis and export
│   ├── utils/             # Utilities
│   └── bot.py             # Main bot orchestrator
├── config/                # Configuration files
├── data/                  # Data storage
├── logs/                  # Application logs
├── tests/                 # Unit tests
└── main.py               # Entry point
```

## Safety Features

- **Paper Trading Mode**: Test without real money
- **API Key Security**: Environment variable storage
- **Rate Limiting**: Prevents exchange API bans
- **Error Handling**: Robust error handling and retry logic
- **Emergency Stop**: Stop bot immediately if needed

## Important Notes

⚠️ **Warning**: Trading cryptocurrencies involves risk. Always:
- Start with paper trading
- Test thoroughly with backtesting
- Use small position sizes initially
- Never risk more than you can afford to lose
- Keep API keys secure and use read-only keys when possible

## Development

### Running Tests

```bash
pytest tests/
```

### Adding New Strategies

1. Create a new strategy class inheriting from `StrategyBase`
2. Implement `should_buy()`, `should_sell()`, and `calculate_position_size()`
3. Add configuration in `config/strategy.yaml`

### Adding New Exchanges

1. Create exchange class inheriting from `ExchangeBase`
2. Implement required methods
3. Add to exchange factory in `main.py`

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]

## Support

For issues and questions, please open an issue on GitHub.

