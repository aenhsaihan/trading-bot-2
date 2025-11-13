import { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, BarChart3, Activity, Zap, Target } from 'lucide-react';
import { Notification } from '../types/notification';

interface Indicator {
  name: string;
  value: number;
  change: number;
  trend: 'up' | 'down' | 'neutral';
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
}

export function MarketIntelligence({ selectedNotification }: MarketIntelligenceProps) {
  const [symbol, setSymbol] = useState<string>('BTC/USDT');
  const [timeframe, setTimeframe] = useState<string>('1h');
  const [marketData, setMarketData] = useState<MarketData | null>(null);
  const [indicators, setIndicators] = useState<Indicator[]>([]);
  // const [loading, setLoading] = useState(false); // TODO: Use when implementing real API calls

  // Update symbol when notification is selected
  useEffect(() => {
    if (selectedNotification?.symbol) {
      setSymbol(selectedNotification.symbol);
    }
  }, [selectedNotification]);

  // TODO: Replace with actual API call in Phase 2
  useEffect(() => {
    // Mock market data
    setMarketData({
      symbol: symbol,
      price: 46500,
      change24h: 1250,
      changePercent24h: 2.76,
      volume24h: 2500000000,
      high24h: 47000,
      low24h: 45200,
    });

    // Mock indicators
    setIndicators([
      { name: 'RSI (14)', value: 58.5, change: 2.3, trend: 'up' },
      { name: 'MACD', value: 125.8, change: -5.2, trend: 'down' },
      { name: 'MA (50)', value: 45800, change: 200, trend: 'up' },
      { name: 'MA (200)', value: 44500, change: 150, trend: 'up' },
      { name: 'Bollinger Upper', value: 47500, change: 300, trend: 'up' },
      { name: 'Bollinger Lower', value: 43500, change: -200, trend: 'down' },
      { name: 'Volume', value: 2500000000, change: 5.5, trend: 'up' },
    ]);
  }, [symbol, timeframe]);

  const timeframes = ['1m', '5m', '15m', '1h', '4h', '1d', '1w'];

  return (
    <div className="flex flex-col h-full bg-gradient-to-br from-[#0a0a1a] to-[#1a1a2e]">
      {/* Header */}
      <div className="bg-dark-card/50 border-b border-gray-800 p-4 flex-shrink-0">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-3 h-3 bg-purple-500 rounded-full" />
          <h2 className="text-xl font-bold text-white">📊 Market Intelligence</h2>
          <span className="text-xs text-gray-400 ml-auto">Real-time Analysis</span>
        </div>

        {/* Symbol & Timeframe Selector */}
        <div className="flex items-center gap-3">
          <div className="flex-1">
            <label className="text-xs text-gray-400 mb-1 block">Symbol</label>
            <input
              type="text"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              placeholder="BTC/USDT"
              className="w-full bg-dark-bg border border-gray-700 rounded-lg px-3 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
            />
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Timeframe</label>
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

      {/* Market Data Summary */}
      {marketData && (
        <div className="p-4 border-b border-gray-800 bg-dark-card/30">
          <div className="grid grid-cols-4 gap-3">
            <div>
              <div className="text-xs text-gray-400 mb-1">Price</div>
              <div className="text-lg font-bold text-white">
                ${marketData.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-400 mb-1">24h Change</div>
              <div
                className={`text-lg font-bold flex items-center gap-1 ${
                  marketData.changePercent24h >= 0 ? 'text-green-400' : 'text-red-400'
                }`}
              >
                {marketData.changePercent24h >= 0 ? (
                  <TrendingUp size={16} />
                ) : (
                  <TrendingDown size={16} />
                )}
                {marketData.changePercent24h >= 0 ? '+' : ''}
                {marketData.changePercent24h.toFixed(2)}%
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-400 mb-1">24h High</div>
              <div className="text-lg font-bold text-green-400">
                ${marketData.high24h.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-400 mb-1">24h Low</div>
              <div className="text-lg font-bold text-red-400">
                ${marketData.low24h.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto p-4">
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
                      <span className="text-xs text-gray-400">{indicator.name}</span>
                      <span
                        className={`text-xs flex items-center gap-1 ${
                          indicator.trend === 'up'
                            ? 'text-green-400'
                            : indicator.trend === 'down'
                            ? 'text-red-400'
                            : 'text-gray-400'
                        }`}
                      >
                        {indicator.trend === 'up' ? (
                          <TrendingUp size={12} />
                        ) : indicator.trend === 'down' ? (
                          <TrendingDown size={12} />
                        ) : null}
                        {indicator.change >= 0 ? '+' : ''}
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
                  <div className="text-xs text-gray-400 mb-1">Overall Signal</div>
                  <div className="text-lg font-bold text-yellow-400">HOLD</div>
                  <div className="text-xs text-gray-500 mt-1">Neutral momentum</div>
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

            {/* Quick Actions */}
            <div className="bg-dark-card rounded-lg p-4 border border-gray-700">
              <h3 className="text-sm font-semibold text-white mb-3">Quick Actions</h3>
              <div className="space-y-2">
                <button className="w-full px-3 py-2 bg-blue-600 hover:bg-blue-700 rounded text-sm font-medium text-white transition-colors">
                  Analyze in Command Center
                </button>
                <button className="w-full px-3 py-2 bg-green-600 hover:bg-green-700 rounded text-sm font-medium text-white transition-colors">
                  Open Position
                </button>
                <button className="w-full px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm font-medium text-white transition-colors">
                  Set Alert
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

