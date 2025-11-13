import { useState, useEffect } from "react";
import {
  TrendingUp,
  TrendingDown,
  BarChart3,
  Activity,
  Zap,
  Target,
} from "lucide-react";
import { Notification } from "../types/notification";
import { marketDataAPI, OHLCVData } from "../services/api";

interface Indicator {
  name: string;
  value: number;
  change: number;
  trend: "up" | "down" | "neutral";
}

interface MarketData {
  symbol: string;
  price: number;
  change24h: number;
  changePercent24h: number;
  volume24h: number;
  high24h: number;
  low24h: number;
}

interface MarketIntelligenceProps {
  selectedNotification?: Notification | null;
  onAnalyzeInCommandCenter?: (symbol: string) => void;
  onOpenPosition?: (symbol: string) => void;
}

export function MarketIntelligence({
  selectedNotification,
  onAnalyzeInCommandCenter,
  onOpenPosition,
}: MarketIntelligenceProps) {
  const [symbol, setSymbol] = useState<string>(() => {
    // Load saved symbol from localStorage, default to BTC/USDT
    const saved = localStorage.getItem("marketIntelligenceSymbol");
    return saved || "BTC/USDT";
  });
  const [timeframe, setTimeframe] = useState<string>(() => {
    // Load saved timeframe from localStorage, default to 1h
    const saved = localStorage.getItem("marketIntelligenceTimeframe");
    return saved || "1h";
  });
  const [marketData, setMarketData] = useState<MarketData | null>(null);
  const [indicators, setIndicators] = useState<Indicator[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ohlcvData, setOhlcvData] = useState<OHLCVData | null>(null);

  // Persist symbol to localStorage when it changes
  useEffect(() => {
    localStorage.setItem("marketIntelligenceSymbol", symbol);
  }, [symbol]);

  // Persist timeframe to localStorage when it changes
  useEffect(() => {
    localStorage.setItem("marketIntelligenceTimeframe", timeframe);
  }, [timeframe]);

  // Update symbol when notification is selected
  useEffect(() => {
    if (selectedNotification?.symbol) {
      setSymbol(selectedNotification.symbol);
    }
  }, [selectedNotification]);

  // Fetch real market data
  useEffect(() => {
    const fetchMarketData = async () => {
      setLoading(true);
      setError(null);
      
      try {
        // Fetch ticker data for current price and 24h stats
        const ticker = await marketDataAPI.getTicker(symbol);
        
        // Fetch OHLCV data for chart and indicators
        const ohlcv = await marketDataAPI.getOHLCV(symbol, timeframe, 100);
        setOhlcvData(ohlcv);
        
        // Calculate 24h change from OHLCV data
        const candles = ohlcv.candles;
        if (candles.length >= 2) {
          const currentPrice = ticker.last;
          const previousPrice = candles[candles.length - 2].close;
          const change24h = currentPrice - previousPrice;
          const changePercent24h = (change24h / previousPrice) * 100;
          
          // Calculate 24h high/low from candles
          const last24hCandles = candles.slice(-24); // Assuming 1h timeframe
          const high24h = Math.max(...last24hCandles.map(c => c.high));
          const low24h = Math.min(...last24hCandles.map(c => c.low));
          const volume24h = last24hCandles.reduce((sum, c) => sum + c.volume, 0);
          
          setMarketData({
            symbol: symbol,
            price: currentPrice,
            change24h: change24h,
            changePercent24h: changePercent24h,
            volume24h: volume24h,
            high24h: high24h,
            low24h: low24h,
          });
          
          // Calculate simple indicators from OHLCV data
          const closes = candles.map(c => c.close);
          const currentClose = closes[closes.length - 1];
          
          // Simple Moving Averages
          const ma50 = closes.slice(-50).reduce((a, b) => a + b, 0) / Math.min(50, closes.length);
          const ma200 = closes.slice(-200).reduce((a, b) => a + b, 0) / Math.min(200, closes.length);
          
          // Simple RSI calculation (simplified)
          const gains = closes.slice(-14).map((c, i) => i > 0 && c > closes[i - 1] ? c - closes[i - 1] : 0);
          const losses = closes.slice(-14).map((c, i) => i > 0 && c < closes[i - 1] ? closes[i - 1] - c : 0);
          const avgGain = gains.reduce((a, b) => a + b, 0) / 14;
          const avgLoss = losses.reduce((a, b) => a + b, 0) / 14;
          const rs = avgGain / (avgLoss || 1);
          const rsi = 100 - (100 / (1 + rs));
          
          // Simple MACD (simplified)
          const ema12 = closes.slice(-12).reduce((a, b) => a + b, 0) / Math.min(12, closes.length);
          const ema26 = closes.slice(-26).reduce((a, b) => a + b, 0) / Math.min(26, closes.length);
          const macd = ema12 - ema26;
          
          // Bollinger Bands (simplified)
          const stdDev = Math.sqrt(
            closes.slice(-20).reduce((sum, c) => {
              const mean = closes.slice(-20).reduce((a, b) => a + b, 0) / 20;
              return sum + Math.pow(c - mean, 2);
            }, 0) / 20
          );
          const bbMiddle = closes.slice(-20).reduce((a, b) => a + b, 0) / 20;
          const bbUpper = bbMiddle + (2 * stdDev);
          const bbLower = bbMiddle - (2 * stdDev);
          
          setIndicators([
            { name: "RSI (14)", value: rsi, change: rsi - 50, trend: rsi > 50 ? "up" : "down" },
            { name: "MACD", value: macd, change: macd, trend: macd > 0 ? "up" : "down" },
            { name: "MA (50)", value: ma50, change: ma50 - currentClose, trend: ma50 > currentClose ? "up" : "down" },
            { name: "MA (200)", value: ma200, change: ma200 - currentClose, trend: ma200 > currentClose ? "up" : "down" },
            { name: "Bollinger Upper", value: bbUpper, change: bbUpper - currentClose, trend: "up" },
            { name: "Bollinger Lower", value: bbLower, change: currentClose - bbLower, trend: "down" },
            { name: "Volume", value: volume24h, change: 0, trend: "neutral" },
          ]);
        } else {
          // Fallback if not enough data
          setMarketData({
            symbol: symbol,
            price: ticker.last,
            change24h: 0,
            changePercent24h: 0,
            volume24h: ticker.volume,
            high24h: ticker.last,
            low24h: ticker.last,
          });
        }
      } catch (err) {
        console.error("Error fetching market data:", err);
        setError(err instanceof Error ? err.message : "Failed to fetch market data");
        // Keep previous data on error
      } finally {
        setLoading(false);
      }
    };

    if (symbol) {
      fetchMarketData();
    }
  }, [symbol, timeframe]);

  const timeframes = ["1m", "5m", "15m", "1h", "4h", "1d", "1w"];

  // Popular trading pairs (same as War Room)
  const tradingPairs = [
    // Major coins
    "BTC/USDT",
    "ETH/USDT",
    "BNB/USDT",
    // High volatility
    "SOL/USDT",
    "DOGE/USDT",
    "ADA/USDT",
    // Active markets
    "MATIC/USDT",
    "AVAX/USDT",
    "XRP/USDT",
    // DeFi tokens
    "DOT/USDT",
    "LINK/USDT",
    "UNI/USDT",
    // Additional popular pairs
    "ATOM/USDT",
    "ALGO/USDT",
    "LTC/USDT",
    "BCH/USDT",
    "ETC/USDT",
    "XLM/USDT",
    "FIL/USDT",
    "AAVE/USDT",
    "SUSHI/USDT",
    "COMP/USDT",
  ];

  return (
    <div className="flex flex-col h-full bg-gradient-to-br from-[#0a0a1a] to-[#1a1a2e]">
      {/* Header */}
      <div className="bg-dark-card/50 border-b border-gray-800 p-4 flex-shrink-0">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-3 h-3 bg-purple-500 rounded-full" />
          <h2 className="text-xl font-bold text-white">
            📊 Market Intelligence
          </h2>
          <span className="text-xs text-gray-400 ml-auto">
            Real-time Analysis
          </span>
        </div>

        {/* Symbol & Timeframe Selector */}
        <div className="flex items-center gap-3">
          <div className="flex-1">
            <label className="text-xs text-gray-400 mb-1 block">Symbol</label>
            <select
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              className="w-full bg-dark-bg border border-gray-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-purple-500"
            >
              {tradingPairs.map((pair) => (
                <option key={pair} value={pair}>
                  {pair}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">
              Timeframe
            </label>
            <select
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value)}
              className="bg-dark-bg border border-gray-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-purple-500"
            >
              {timeframes.map((tf) => (
                <option key={tf} value={tf}>
                  {tf}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-500/20 border border-red-500 rounded-lg p-3 mb-4">
          <div className="text-red-400 text-sm">
            ⚠️ {error}
          </div>
        </div>
      )}

      {/* Loading State */}
      {loading && !marketData && (
        <div className="text-center py-12 text-gray-400">
          Loading market data...
        </div>
      )}

      {/* Market Data Summary */}
      {marketData && (
        <div className="p-4 border-b border-gray-800 bg-dark-card/30">
          <div className="grid grid-cols-4 gap-3">
            <div>
              <div className="text-xs text-gray-400 mb-1">Price</div>
              <div className="text-lg font-bold text-white">
                $
                {marketData.price.toLocaleString(undefined, {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-400 mb-1">24h Change</div>
              <div
                className={`text-lg font-bold flex items-center gap-1 ${
                  marketData.changePercent24h >= 0
                    ? "text-green-400"
                    : "text-red-400"
                }`}
              >
                {marketData.changePercent24h >= 0 ? (
                  <TrendingUp size={16} />
                ) : (
                  <TrendingDown size={16} />
                )}
                {marketData.changePercent24h >= 0 ? "+" : ""}
                {marketData.changePercent24h.toFixed(2)}%
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-400 mb-1">24h High</div>
              <div className="text-lg font-bold text-green-400">
                $
                {marketData.high24h.toLocaleString(undefined, {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-400 mb-1">24h Low</div>
              <div className="text-lg font-bold text-red-400">
                $
                {marketData.low24h.toLocaleString(undefined, {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {/* Quick Actions - Full width above both chart and indicators */}
        <div className="bg-dark-card rounded-lg p-4 border border-gray-700 mb-4">
          <h3 className="text-sm font-semibold text-white mb-3">
            Quick Actions
          </h3>
          <div className="grid grid-cols-3 gap-2">
            <button
              onClick={() => onAnalyzeInCommandCenter?.(symbol)}
              className="px-3 py-2 bg-blue-600 hover:bg-blue-700 rounded text-sm font-medium text-white transition-colors"
            >
              Analyze in Command Center
            </button>
            <button
              onClick={() => onOpenPosition?.(symbol)}
              className="px-3 py-2 bg-green-600 hover:bg-green-700 rounded text-sm font-medium text-white transition-colors"
            >
              Open Position
            </button>
            <button className="px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm font-medium text-white transition-colors">
              Set Alert
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Chart Area - Left Column (2/3 width) */}
          <div className="lg:col-span-2 space-y-4">
            {/* Chart Placeholder */}
            <div className="bg-dark-card rounded-lg p-4 border border-gray-700 h-96 flex flex-col">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <BarChart3 size={18} />
                  Price Chart
                </h3>
                <div className="flex gap-2">
                  <button className="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 rounded text-white">
                    Candles
                  </button>
                  <button className="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 rounded text-white">
                    Line
                  </button>
                  <button className="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 rounded text-white">
                    Area
                  </button>
                </div>
              </div>
              <div className="flex-1 bg-dark-bg rounded border border-gray-800 flex items-center justify-center">
                <div className="text-center text-gray-500">
                  <BarChart3 size={48} className="mx-auto mb-2 opacity-50" />
                  <div className="text-sm">Chart Integration Ready</div>
                  <div className="text-xs mt-1">
                    Ready for TradingView, Chart.js, or custom charting library
                  </div>
                </div>
              </div>
            </div>

            {/* Volume Chart */}
            <div className="bg-dark-card rounded-lg p-4 border border-gray-700 h-32">
              <h3 className="text-sm font-semibold text-white mb-2 flex items-center gap-2">
                <Activity size={16} />
                Volume
              </h3>
              <div className="h-full bg-dark-bg rounded border border-gray-800 flex items-center justify-center">
                <div className="text-center text-gray-500 text-xs">
                  Volume chart placeholder
                </div>
              </div>
            </div>
          </div>

          {/* Indicators & Analysis - Right Column (1/3 width) */}
          <div className="space-y-4">
            {/* Technical Indicators */}
            <div className="bg-dark-card rounded-lg p-4 border border-gray-700">
              <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                <Zap size={16} />
                Technical Indicators
              </h3>
              <div className="space-y-2">
                {indicators.map((indicator, idx) => (
                  <div
                    key={idx}
                    className="bg-dark-bg rounded p-2 border border-gray-800"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-gray-400">
                        {indicator.name}
                      </span>
                      <span
                        className={`text-xs flex items-center gap-1 ${
                          indicator.trend === "up"
                            ? "text-green-400"
                            : indicator.trend === "down"
                            ? "text-red-400"
                            : "text-gray-400"
                        }`}
                      >
                        {indicator.trend === "up" ? (
                          <TrendingUp size={12} />
                        ) : indicator.trend === "down" ? (
                          <TrendingDown size={12} />
                        ) : null}
                        {indicator.change >= 0 ? "+" : ""}
                        {indicator.change.toFixed(2)}
                      </span>
                    </div>
                    <div className="text-sm font-bold text-white">
                      {indicator.value.toLocaleString(undefined, {
                        minimumFractionDigits: indicator.value < 1000 ? 2 : 0,
                        maximumFractionDigits: indicator.value < 1000 ? 2 : 0,
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Signal Analysis */}
            <div className="bg-dark-card rounded-lg p-4 border border-gray-700">
              <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                <Target size={16} />
                Signal Analysis
              </h3>
              <div className="space-y-2">
                <div className="bg-dark-bg rounded p-3 border border-gray-800">
                  <div className="text-xs text-gray-400 mb-1">
                    Overall Signal
                  </div>
                  <div className="text-lg font-bold text-yellow-400">HOLD</div>
                  <div className="text-xs text-gray-500 mt-1">
                    Neutral momentum
                  </div>
                </div>
                <div className="bg-dark-bg rounded p-3 border border-gray-800">
                  <div className="text-xs text-gray-400 mb-1">Confidence</div>
                  <div className="text-lg font-bold text-white">65%</div>
                </div>
                <div className="bg-dark-bg rounded p-3 border border-gray-800">
                  <div className="text-xs text-gray-400 mb-1">Risk Level</div>
                  <div className="text-lg font-bold text-green-400">MEDIUM</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
