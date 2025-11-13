import { useState, useEffect, useRef, useCallback } from "react";
import {
  TrendingUp,
  TrendingDown,
  BarChart3,
  Activity,
  Zap,
  Target,
  Wifi,
  WifiOff,
} from "lucide-react";
import { Notification } from "../types/notification";
import { marketDataAPI, OHLCVData } from "../services/api";
import { PriceChart } from "./PriceChart";
import { useMarketDataStream, PriceUpdate, OHLCVUpdate } from "../hooks/useMarketDataStream";
import { AlertManager } from "./AlertManager";

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
  const [chartType, setChartType] = useState<"candles" | "line" | "area">(
    "candles"
  );
  const [streamingEnabled, setStreamingEnabled] = useState(true);
  const [showAlertManager, setShowAlertManager] = useState(false);

  // Memoize callbacks to prevent unnecessary re-renders
  const handlePriceUpdate = useCallback((update: PriceUpdate) => {
    // Update market data with streaming price
    setMarketData((prev) => {
      if (!prev || prev.symbol !== update.symbol) return prev;
      return {
        ...prev,
        price: update.price,
      };
    });
  }, []);

  const handleOHLCVUpdate = useCallback((update: OHLCVUpdate) => {
    // Update OHLCV data if timeframe matches
    if (update.timeframe === timeframe && update.symbol === symbol) {
      setOhlcvData((prev) => {
        if (!prev || prev.symbol !== update.symbol) return prev;
        
        // Merge new candles with existing ones, then sort by timestamp
        const merged = [...prev.candles, ...update.candles];
        // Remove duplicates by timestamp and sort
        const uniqueCandles = Array.from(
          new Map(merged.map(c => [c.timestamp, c])).values()
        ).sort((a, b) => a.timestamp - b.timestamp);
        
        return {
          ...prev,
          candles: uniqueCandles.slice(-100), // Keep last 100 candles
        };
      });
    }
  }, [timeframe, symbol]);

  // Market data streaming hook
  const {
    status: streamStatus,
    latestPrice,
    latestTicker,
    latestOHLCV,
    subscribe,
    unsubscribe,
  } = useMarketDataStream({
    symbols: streamingEnabled ? [symbol] : [],
    autoConnect: streamingEnabled,
    onPriceUpdate: handlePriceUpdate,
    onOHLCVUpdate: handleOHLCVUpdate,
  });

  // Track previous symbol to handle subscription changes
  const prevSymbolRef = useRef(symbol);
  
  // Update subscription when symbol changes
  useEffect(() => {
    if (streamingEnabled && streamStatus === "connected") {
      if (prevSymbolRef.current !== symbol) {
        unsubscribe(prevSymbolRef.current);
        subscribe(symbol);
        prevSymbolRef.current = symbol;
      }
    }
  }, [symbol, streamingEnabled, streamStatus, subscribe, unsubscribe]);

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
          const high24h = Math.max(...last24hCandles.map((c) => c.high));
          const low24h = Math.min(...last24hCandles.map((c) => c.low));
          const volume24h = last24hCandles.reduce(
            (sum, c) => sum + c.volume,
            0
          );

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
          const closes = candles.map((c) => c.close);
          const currentClose = closes[closes.length - 1];

          // Simple Moving Averages
          const ma50 =
            closes.slice(-50).reduce((a, b) => a + b, 0) /
            Math.min(50, closes.length);
          const ma200 =
            closes.slice(-200).reduce((a, b) => a + b, 0) /
            Math.min(200, closes.length);

          // Simple RSI calculation (simplified)
          const gains = closes
            .slice(-14)
            .map((c, i) =>
              i > 0 && c > closes[i - 1] ? c - closes[i - 1] : 0
            );
          const losses = closes
            .slice(-14)
            .map((c, i) =>
              i > 0 && c < closes[i - 1] ? closes[i - 1] - c : 0
            );
          const avgGain = gains.reduce((a, b) => a + b, 0) / 14;
          const avgLoss = losses.reduce((a, b) => a + b, 0) / 14;
          const rs = avgGain / (avgLoss || 1);
          const rsi = 100 - 100 / (1 + rs);

          // Simple MACD (simplified)
          const ema12 =
            closes.slice(-12).reduce((a, b) => a + b, 0) /
            Math.min(12, closes.length);
          const ema26 =
            closes.slice(-26).reduce((a, b) => a + b, 0) /
            Math.min(26, closes.length);
          const macd = ema12 - ema26;

          // Bollinger Bands (simplified)
          const stdDev = Math.sqrt(
            closes.slice(-20).reduce((sum, c) => {
              const mean = closes.slice(-20).reduce((a, b) => a + b, 0) / 20;
              return sum + Math.pow(c - mean, 2);
            }, 0) / 20
          );
          const bbMiddle = closes.slice(-20).reduce((a, b) => a + b, 0) / 20;
          const bbUpper = bbMiddle + 2 * stdDev;
          const bbLower = bbMiddle - 2 * stdDev;

          setIndicators([
            {
              name: "RSI (14)",
              value: rsi,
              change: rsi - 50,
              trend: rsi > 50 ? "up" : "down",
            },
            {
              name: "MACD",
              value: macd,
              change: macd,
              trend: macd > 0 ? "up" : "down",
            },
            {
              name: "MA (50)",
              value: ma50,
              change: ma50 - currentClose,
              trend: ma50 > currentClose ? "up" : "down",
            },
            {
              name: "MA (200)",
              value: ma200,
              change: ma200 - currentClose,
              trend: ma200 > currentClose ? "up" : "down",
            },
            {
              name: "Bollinger Upper",
              value: bbUpper,
              change: bbUpper - currentClose,
              trend: "up",
            },
            {
              name: "Bollinger Lower",
              value: bbLower,
              change: currentClose - bbLower,
              trend: "down",
            },
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
        setError(
          err instanceof Error ? err.message : "Failed to fetch market data"
        );
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
          <div className="text-red-400 text-sm">⚠️ {error}</div>
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
            <button
              onClick={() => setShowAlertManager(true)}
              className="px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm font-medium text-white transition-colors"
            >
              Set Alert
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Chart Area - Left Column (2/3 width) */}
          <div className="lg:col-span-2 space-y-4">
            {/* Price Chart */}
            <div className="bg-dark-card rounded-lg p-4 border border-gray-700 flex flex-col">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <BarChart3 size={18} />
                  Price Chart
                </h3>
                <div className="flex gap-2">
                  <button
                    onClick={() => setChartType("candles")}
                    className={`px-2 py-1 text-xs rounded text-white transition-colors ${
                      chartType === "candles"
                        ? "bg-blue-600 hover:bg-blue-700"
                        : "bg-gray-700 hover:bg-gray-600"
                    }`}
                  >
                    Candles
                  </button>
                  <button
                    onClick={() => setChartType("line")}
                    className={`px-2 py-1 text-xs rounded text-white transition-colors ${
                      chartType === "line"
                        ? "bg-blue-600 hover:bg-blue-700"
                        : "bg-gray-700 hover:bg-gray-600"
                    }`}
                  >
                    Line
                  </button>
                  <button
                    onClick={() => setChartType("area")}
                    className={`px-2 py-1 text-xs rounded text-white transition-colors ${
                      chartType === "area"
                        ? "bg-blue-600 hover:bg-blue-700"
                        : "bg-gray-700 hover:bg-gray-600"
                    }`}
                  >
                    Area
                  </button>
                </div>
              </div>
              <div className="bg-dark-bg rounded border border-gray-800 min-h-[400px]">
                {loading ? (
                  <div className="flex items-center justify-center h-96 text-gray-500">
                    <div className="text-center">
                      <div className="text-sm">Loading chart data...</div>
                    </div>
                  </div>
                ) : ohlcvData &&
                  ohlcvData.candles &&
                  ohlcvData.candles.length > 0 ? (
                  <PriceChart
                    candles={ohlcvData.candles}
                    symbol={symbol}
                    chartType={chartType}
                    height={400}
                  />
                ) : error ? (
                  <div className="flex items-center justify-center h-96 text-red-400">
                    <div className="text-center">
                      <div className="text-sm">Error: {error}</div>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center justify-center h-96 text-gray-500">
                    <div className="text-center">
                      <BarChart3
                        size={48}
                        className="mx-auto mb-2 opacity-50"
                      />
                      <div className="text-sm">No chart data available</div>
                      {ohlcvData && (
                        <div className="text-xs mt-2 text-gray-600">
                          Debug: ohlcvData exists but candles array is empty or
                          missing
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Volume Chart */}
            <div className="bg-dark-card rounded-lg p-4 border border-gray-700">
              <h3 className="text-sm font-semibold text-white mb-2 flex items-center gap-2">
                <Activity size={16} />
                Volume
              </h3>
              <div className="h-32 bg-dark-bg rounded border border-gray-800 flex items-center justify-center">
                {ohlcvData && ohlcvData.candles.length > 0 ? (
                  <div className="w-full h-full p-2">
                    <div className="grid grid-cols-10 gap-1 h-full">
                      {ohlcvData.candles.slice(-10).map((candle, idx) => {
                        const maxVolume = Math.max(
                          ...ohlcvData.candles.slice(-10).map((c) => c.volume)
                        );
                        const heightPercent = (candle.volume / maxVolume) * 100;
                        return (
                          <div
                            key={idx}
                            className="flex items-end justify-center"
                            title={`Volume: ${candle.volume.toLocaleString()}`}
                          >
                            <div
                              className="w-full bg-blue-500/50 rounded-t transition-all hover:bg-blue-500"
                              style={{ height: `${heightPercent}%` }}
                            />
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ) : (
                  <div className="text-center text-gray-500 text-xs">
                    Volume chart placeholder
                  </div>
                )}
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

      {/* Alert Manager Modal */}
      {showAlertManager && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-dark-card rounded-lg border border-gray-700 w-full max-w-2xl max-h-[90vh] overflow-y-auto m-4">
            <div className="sticky top-0 bg-dark-card border-b border-gray-700 p-4 flex items-center justify-between">
              <h2 className="text-xl font-bold text-white">Create Alert</h2>
              <button
                onClick={() => setShowAlertManager(false)}
                className="text-gray-400 hover:text-white"
              >
                ✕
              </button>
            </div>
            <div className="p-4">
              <AlertManager
                symbol={symbol}
                onAlertCreated={() => {
                  setShowAlertManager(false);
                }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
