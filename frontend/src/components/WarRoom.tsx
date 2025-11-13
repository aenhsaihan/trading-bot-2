import { useState, useEffect, useMemo, useCallback } from 'react';
import { TrendingUp, TrendingDown, DollarSign, Target, Shield } from 'lucide-react';
import { Notification, NotificationType } from '../types/notification';
import { tradingAPI, Position as APIPosition, Balance } from '../services/api';
import { usePriceUpdates } from '../hooks/usePriceUpdates';

interface Position {
  id: string;
  symbol: string;
  side: 'long' | 'short';
  amount: number;
  entryPrice: number;
  currentPrice: number;
  pnl: number;
  pnlPercent: number;
  stopLoss?: number;  // Stop loss price
  stopLossPercent?: number;  // Stop loss percentage
  trailingStop?: number;  // Trailing stop percentage
}

interface WarRoomProps {
  selectedNotification?: Notification | null;
  prefillSymbol?: string | null;
  onOpenPosition?: (symbol: string, side: 'long' | 'short', amount: number) => void;
  onClosePosition?: (positionId: string) => void;
  onSetStopLoss?: (positionId: string, stopLoss: number) => void;
  onSetTrailingStop?: (positionId: string, trailingStop: number) => void;
}

export function WarRoom({
  selectedNotification,
  prefillSymbol,
  onOpenPosition,
  onClosePosition,
  onSetStopLoss,
  onSetTrailingStop,
}: WarRoomProps) {
  const [positions, setPositions] = useState<Position[]>([]);
  const [balance, setBalance] = useState<number>(10000);
  const [totalPnl, setTotalPnl] = useState<number>(0);
  const [totalPnlPercent, setTotalPnlPercent] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [showOrderForm, setShowOrderForm] = useState(false);
  const [orderForm, setOrderForm] = useState({
    symbol: 'BTC/USDT',
    side: 'long' as 'long' | 'short',
    amount: '',
    stopLoss: '',
    trailingStop: '',
  });

  // Popular trading pairs
  const tradingPairs = [
    // Major coins
    'BTC/USDT',
    'ETH/USDT',
    'BNB/USDT',
    // High volatility
    'SOL/USDT',
    'DOGE/USDT',
    'ADA/USDT',
    // Active markets
    'MATIC/USDT',
    'AVAX/USDT',
    'XRP/USDT',
    // DeFi tokens
    'DOT/USDT',
    'LINK/USDT',
    'UNI/USDT',
    // Additional popular pairs
    'ATOM/USDT',
    'ALGO/USDT',
    'LTC/USDT',
    'BCH/USDT',
    'ETC/USDT',
    'XLM/USDT',
    'FIL/USDT',
    'AAVE/USDT',
    'SUSHI/USDT',
    'COMP/USDT',
  ];

  // Get symbols from positions for price monitoring
  const positionSymbols = useMemo(() => {
    return positions.map(p => p.symbol);
  }, [positions]);

  // Memoize the price update callback to prevent unnecessary re-renders
  const handlePriceUpdate = useCallback((prices: Record<string, number>) => {
    // Update positions with live prices
    setPositions(prev => prev.map(pos => {
      const livePrice = prices[pos.symbol];
      if (livePrice && livePrice !== pos.currentPrice) {
        // Recalculate P&L with live price
        const priceDiff = livePrice - pos.entryPrice;
        const pnl = pos.side === 'long' 
          ? priceDiff * pos.amount
          : -priceDiff * pos.amount;
        const pnlPercent = (pnl / (pos.entryPrice * pos.amount)) * 100;
        
        return {
          ...pos,
          currentPrice: livePrice,
          pnl,
          pnlPercent,
        };
      }
      return pos;
    }));
  }, []);

  // Real-time price updates via WebSocket
  const { prices: livePrices, isConnected: priceWsConnected } = usePriceUpdates({
    symbols: positionSymbols,
    onPriceUpdate: handlePriceUpdate,
  });

  // Fetch positions and balance on mount and periodically (fallback/refresh)
  const fetchData = async () => {
    try {
      setLoading(true);
      const [balanceData, positionsData] = await Promise.all([
        tradingAPI.getBalance(),
        tradingAPI.getPositions(),
      ]);
      
      setBalance(balanceData.balance);
      setTotalPnl(balanceData.total_pnl);
      setTotalPnlPercent(balanceData.total_pnl_percent);
      
      // Map API positions to component Position format
      // Use live prices if available, otherwise use API prices
      const mappedPositions: Position[] = positionsData.positions.map((pos: APIPosition) => {
        const livePrice = livePrices[pos.symbol];
        const currentPrice = livePrice || pos.current_price;
        
        // Recalculate P&L if using live price
        let pnl = pos.pnl;
        let pnlPercent = pos.pnl_percent;
        if (livePrice && livePrice !== pos.current_price) {
          const priceDiff = currentPrice - pos.entry_price;
          pnl = pos.side === 'long' 
            ? priceDiff * pos.amount
            : -priceDiff * pos.amount;
          pnlPercent = (pnl / (pos.entry_price * pos.amount)) * 100;
        }
        
        return {
          id: pos.id,
          symbol: pos.symbol,
          side: pos.side as 'long' | 'short',
          amount: pos.amount,
          entryPrice: pos.entry_price,
          currentPrice,
          pnl,
          pnlPercent,
          stopLoss: pos.stop_loss,
          stopLossPercent: pos.stop_loss_percent,
          trailingStop: pos.trailing_stop,
        };
      });
      
      setPositions(mappedPositions);
    } catch (error) {
      console.error('Failed to fetch trading data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    
    // Refresh data every 30 seconds (reduced frequency since we have WebSocket updates)
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (selectedNotification?.symbol) {
      // Determine side based on notification type
      // Technical breakouts and combined signals are typically bullish (long)
      // Risk alerts might be bearish (short)
      let suggestedSide: 'long' | 'short' = 'long';
      if (
        selectedNotification.type === NotificationType.RISK_ALERT ||
        (selectedNotification.metadata?.side === 'short')
      ) {
        suggestedSide = 'short';
      } else if (selectedNotification.metadata?.side === 'long') {
        suggestedSide = 'long';
      }

      setOrderForm((prev) => ({
        ...prev,
        symbol: selectedNotification.symbol || '',
        side: suggestedSide,
      }));
      setShowOrderForm(true);
    }
  }, [selectedNotification]);

  useEffect(() => {
    if (prefillSymbol) {
      setOrderForm((prev) => ({
        ...prev,
        symbol: prefillSymbol,
      }));
      setShowOrderForm(true);
    }
  }, [prefillSymbol]);

  const handleOpenPosition = async () => {
    if (!orderForm.symbol || !orderForm.amount) return;

    const amount = parseFloat(orderForm.amount);
    if (isNaN(amount) || amount <= 0) return;

    try {
      // Parse stop loss and trailing stop, only include if valid numbers
      const stopLossPercent = orderForm.stopLoss 
        ? (isNaN(parseFloat(orderForm.stopLoss)) ? undefined : parseFloat(orderForm.stopLoss))
        : undefined;
      const trailingStopPercent = orderForm.trailingStop
        ? (isNaN(parseFloat(orderForm.trailingStop)) ? undefined : parseFloat(orderForm.trailingStop))
        : undefined;

      const position = await tradingAPI.openPosition({
        symbol: orderForm.symbol,
        side: orderForm.side,
        amount: amount,
        stop_loss_percent: stopLossPercent,
        trailing_stop_percent: trailingStopPercent,
      });

      // Map API position to component format
      const newPosition: Position = {
        id: position.id,
        symbol: position.symbol,
        side: position.side as 'long' | 'short',
        amount: position.amount,
        entryPrice: position.entry_price,
        currentPrice: position.current_price,
        pnl: position.pnl,
        pnlPercent: position.pnl_percent,
        stopLoss: position.stop_loss,
        trailingStop: position.trailing_stop,
      };

      // Refresh data to get updated balance
      await fetchData();

      // Call callback
      if (onOpenPosition) {
        onOpenPosition(orderForm.symbol, orderForm.side, amount);
      }

      // Reset form
      setOrderForm({
        symbol: 'BTC/USDT',
        side: 'long',
        amount: '',
        stopLoss: '',
        trailingStop: '',
      });
      setShowOrderForm(false);
    } catch (error) {
      console.error('Failed to open position:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      alert(`Failed to open position: ${errorMessage}`);
    }
  };

  const handleClosePosition = async (positionId: string) => {
    try {
      await tradingAPI.closePosition(positionId);
      
      // Refresh data to get updated positions and balance
      await fetchData();
      
      // Call callback
      if (onClosePosition) {
        onClosePosition(positionId);
      }
    } catch (error) {
      console.error('Failed to close position:', error);
      alert(`Failed to close position: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const handleSetStopLoss = async (positionId: string, stopLossPercent: number) => {
    try {
      await tradingAPI.setStopLoss(positionId, stopLossPercent);
      await fetchData();
      
      if (onSetStopLoss) {
        onSetStopLoss(positionId, stopLossPercent);
      }
    } catch (error) {
      console.error('Failed to set stop loss:', error);
      alert(`Failed to set stop loss: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const handleSetTrailingStop = async (positionId: string, trailingStopPercent: number) => {
    try {
      await tradingAPI.setTrailingStop(positionId, trailingStopPercent);
      await fetchData();
      
      if (onSetTrailingStop) {
        onSetTrailingStop(positionId, trailingStopPercent);
      }
    } catch (error) {
      console.error('Failed to set trailing stop:', error);
      alert(`Failed to set trailing stop: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  return (
    <div className="flex flex-col h-full bg-gradient-to-br from-[#0a0a1a] to-[#1a1a2e]">
      {/* Header */}
      <div className="bg-dark-card/50 border-b border-gray-800 p-4">
        <div className="flex items-center gap-3">
          <div className="w-3 h-3 bg-green-500 rounded-full" />
          <h2 className="text-xl font-bold text-white">🎯 War Room</h2>
          <span className="text-xs text-gray-400 ml-auto">Tactical Operations</span>
        </div>
        <div className="mt-2 text-xs text-yellow-400/70 bg-yellow-400/10 border border-yellow-400/20 rounded px-2 py-1 inline-block">
          ⚠️ Using mock prices for development
        </div>
      </div>

      {/* Balance & Stats */}
      <div className="p-4 border-b border-gray-800">
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-dark-card rounded-lg p-3 border border-gray-700">
            <div className="text-xs text-gray-400 mb-1">Balance</div>
            <div className="flex items-center gap-2">
              <DollarSign size={16} className="text-green-400" />
              <span className="text-lg font-bold text-white">
                ${balance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            </div>
          </div>
          <div className="bg-dark-card rounded-lg p-3 border border-gray-700">
            <div className="text-xs text-gray-400 mb-1">Total P&L</div>
            <div className={`flex items-center gap-2 ${totalPnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {totalPnl >= 0 ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
              <span className="text-lg font-bold">
                ${totalPnl.toFixed(2)} ({totalPnlPercent.toFixed(2)}%)
              </span>
            </div>
          </div>
          <div className="bg-dark-card rounded-lg p-3 border border-gray-700">
            <div className="text-xs text-gray-400 mb-1">Open Positions</div>
            <div className="text-lg font-bold text-white">{positions.length}</div>
            {priceWsConnected && (
              <div className="text-xs text-green-400 mt-1 flex items-center gap-1">
                <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                Live
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="p-4 border-b border-gray-800">
        <button
          onClick={() => setShowOrderForm(!showOrderForm)}
          className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-white font-medium transition-colors"
        >
          {showOrderForm ? 'Hide' : 'Open New Position'}
        </button>
      </div>

      {/* Order Form */}
      {showOrderForm && (
        <div className="p-4 border-b border-gray-800 bg-dark-card/30">
          <h3 className="text-sm font-semibold text-white mb-3">New Position</h3>
          <div className="space-y-3">
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Symbol</label>
              <select
                value={orderForm.symbol}
                onChange={(e) => setOrderForm({ ...orderForm, symbol: e.target.value })}
                className="w-full bg-dark-bg border border-gray-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
              >
                {tradingPairs.map((pair) => (
                  <option key={pair} value={pair}>
                    {pair}
                  </option>
                ))}
              </select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-gray-400 mb-1 block">Side</label>
                <select
                  value={orderForm.side}
                  onChange={(e) => setOrderForm({ ...orderForm, side: e.target.value as 'long' | 'short' })}
                  className="w-full bg-dark-bg border border-gray-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                >
                  <option value="long">Long</option>
                  <option value="short">Short</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">Amount</label>
                <input
                  type="number"
                  value={orderForm.amount}
                  onChange={(e) => setOrderForm({ ...orderForm, amount: e.target.value })}
                  placeholder="0.1"
                  step="0.01"
                  className="w-full bg-dark-bg border border-gray-700 rounded-lg px-3 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-gray-400 mb-1 block">Stop Loss (%)</label>
                <input
                  type="number"
                  value={orderForm.stopLoss}
                  onChange={(e) => setOrderForm({ ...orderForm, stopLoss: e.target.value })}
                  placeholder="3.0"
                  step="0.1"
                  className="w-full bg-dark-bg border border-gray-700 rounded-lg px-3 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">Trailing Stop (%)</label>
                <input
                  type="number"
                  value={orderForm.trailingStop}
                  onChange={(e) => setOrderForm({ ...orderForm, trailingStop: e.target.value })}
                  placeholder="2.5"
                  step="0.1"
                  className="w-full bg-dark-bg border border-gray-700 rounded-lg px-3 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>
            <button
              onClick={handleOpenPosition}
              className="w-full px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg text-white font-medium transition-colors"
            >
              Execute Order
            </button>
          </div>
        </div>
      )}

      {/* Positions List */}
      <div className="flex-1 overflow-y-auto p-4">
        <h3 className="text-sm font-semibold text-white mb-3">Open Positions</h3>
        {loading ? (
          <div className="text-center py-8 text-gray-500">
            <div>Loading positions...</div>
          </div>
        ) : positions.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <Target size={48} className="mx-auto mb-2 opacity-50" />
            <div>No open positions</div>
            <div className="text-xs mt-1">Open a position to start trading</div>
          </div>
        ) : (
          <div className="space-y-3">
            {positions.map((position) => {
              const isProfit = position.pnl >= 0;
              const pnlIntensity = Math.min(Math.abs(position.pnlPercent) / 10, 1); // 0-1 scale
              
              return (
              <div
                key={position.id}
                className={`bg-dark-card rounded-lg p-4 border transition-all duration-300 ${
                  isProfit 
                    ? `border-green-500/30 ${pnlIntensity > 0.5 ? 'ring-1 ring-green-500/20' : ''}` 
                    : `border-red-500/30 ${pnlIntensity > 0.5 ? 'ring-1 ring-red-500/20' : ''}`
                }`}
              >
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-bold text-white">{position.symbol}</span>
                      <span
                        className={`text-xs px-2 py-0.5 rounded ${
                          position.side === 'long'
                            ? 'bg-green-500/20 text-green-400'
                            : 'bg-red-500/20 text-red-400'
                        }`}
                      >
                        {position.side.toUpperCase()}
                      </span>
                    </div>
                    <div className="text-xs text-gray-400 space-y-0.5">
                      <div>
                        {position.amount} @ Entry: ${position.entryPrice.toLocaleString()}
                      </div>
                      <div className="text-gray-500">
                        Current: ${position.currentPrice.toLocaleString()}
                      </div>
                    </div>
                  </div>
                  <div className={`text-right ${isProfit ? 'text-green-400' : 'text-red-400'}`}>
                    <div className="font-bold flex items-center justify-end gap-1">
                      {isProfit ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
                      {position.pnl >= 0 ? '+' : ''}${position.pnl.toFixed(2)}
                    </div>
                    <div className={`text-xs ${isProfit ? 'text-green-300' : 'text-red-300'}`}>
                      {position.pnlPercent >= 0 ? '+' : ''}
                      {position.pnlPercent.toFixed(2)}%
                    </div>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2 mt-3 pt-3 border-t border-gray-700">
                  {position.stopLoss && (
                    <div className="flex items-center gap-2 text-xs">
                      <Shield size={14} className="text-yellow-400" />
                      <span className="text-gray-400">Stop Loss:</span>
                      <span className="text-white">${position.stopLoss.toLocaleString()}</span>
                    </div>
                  )}
                  {position.trailingStop && (
                    <div className="flex items-center gap-2 text-xs">
                      <Target size={14} className="text-blue-400" />
                      <span className="text-gray-400">Trailing:</span>
                      <span className="text-white">{position.trailingStop}%</span>
                    </div>
                  )}
                </div>
                <div className="flex gap-2 mt-3">
                  <button
                    onClick={() => {
                      const percent = prompt('Enter stop loss percentage (0 to remove):', position.stopLossPercent ? String(position.stopLossPercent) : '3.0');
                      if (percent !== null) {
                        const stopLossPercent = parseFloat(percent);
                        if (!isNaN(stopLossPercent) && stopLossPercent >= 0) {
                          handleSetStopLoss(position.id, stopLossPercent);
                        }
                      }
                    }}
                    className="flex-1 px-3 py-1.5 bg-yellow-600/20 hover:bg-yellow-600/30 text-yellow-400 rounded text-xs font-medium transition-colors"
                  >
                    Set Stop Loss
                  </button>
                  <button
                    onClick={() => {
                      const percent = prompt('Enter trailing stop percentage (0 to remove):', position.trailingStop ? String(position.trailingStop) : '2.5');
                      if (percent !== null) {
                        const trailingStopPercent = parseFloat(percent);
                        if (!isNaN(trailingStopPercent) && trailingStopPercent >= 0) {
                          handleSetTrailingStop(position.id, trailingStopPercent);
                        }
                      }
                    }}
                    className="flex-1 px-3 py-1.5 bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 rounded text-xs font-medium transition-colors"
                  >
                    Set Trailing
                  </button>
                  <button
                    onClick={() => handleClosePosition(position.id)}
                    className="flex-1 px-3 py-1.5 bg-red-600/20 hover:bg-red-600/30 text-red-400 rounded text-xs font-medium transition-colors"
                  >
                    Close
                  </button>
                </div>
              </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

