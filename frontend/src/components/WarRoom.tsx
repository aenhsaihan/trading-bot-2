import { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, DollarSign, Target, Shield } from 'lucide-react';
import { Notification } from '../types/notification';

interface Position {
  id: string;
  symbol: string;
  side: 'long' | 'short';
  amount: number;
  entryPrice: number;
  currentPrice: number;
  pnl: number;
  pnlPercent: number;
  stopLoss?: number;
  trailingStop?: number;
}

interface WarRoomProps {
  selectedNotification?: Notification | null;
  onOpenPosition?: (symbol: string, side: 'long' | 'short', amount: number) => void;
  onClosePosition?: (positionId: string) => void;
  onSetStopLoss?: (positionId: string, stopLoss: number) => void;
  onSetTrailingStop?: (positionId: string, trailingStop: number) => void;
}

export function WarRoom({
  selectedNotification,
  onOpenPosition,
  onClosePosition,
  onSetStopLoss,
  onSetTrailingStop,
}: WarRoomProps) {
  const [positions, setPositions] = useState<Position[]>([]);
  const [balance] = useState<number>(10000); // TODO: Fetch from API in Phase 2
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

  // TODO: Replace with actual API call in Phase 2
  // Positions are now managed via handleOpenPosition and handleClosePosition
  // Removed mock data - positions start empty and are added when orders are executed

  useEffect(() => {
    if (selectedNotification?.symbol) {
      setOrderForm((prev) => ({
        ...prev,
        symbol: selectedNotification.symbol || '',
      }));
      setShowOrderForm(true);
    }
  }, [selectedNotification]);

  const handleOpenPosition = () => {
    if (!orderForm.symbol || !orderForm.amount) return;

    const amount = parseFloat(orderForm.amount);
    if (isNaN(amount) || amount <= 0) return;

    // Mock entry price (TODO: Get real price from API in Phase 2)
    // For now, use a mock price based on symbol
    const mockPrices: Record<string, number> = {
      'BTC/USDT': 46500,
      'ETH/USDT': 2500,
      'BNB/USDT': 320,
      'SOL/USDT': 100,
      'DOGE/USDT': 0.08,
      'ADA/USDT': 0.5,
      'MATIC/USDT': 0.8,
      'AVAX/USDT': 35,
      'XRP/USDT': 0.6,
      'DOT/USDT': 7,
      'LINK/USDT': 15,
      'UNI/USDT': 6,
      'ATOM/USDT': 10,
      'ALGO/USDT': 0.2,
      'LTC/USDT': 70,
      'BCH/USDT': 250,
      'ETC/USDT': 20,
      'XLM/USDT': 0.12,
      'FIL/USDT': 5,
      'AAVE/USDT': 90,
      'SUSHI/USDT': 1.5,
      'COMP/USDT': 50,
    };
    const entryPrice = mockPrices[orderForm.symbol] || 1000;
    const currentPrice = entryPrice; // New position, so current = entry

    // Create new position
    const newPosition: Position = {
      id: `${orderForm.symbol}_${Date.now()}`,
      symbol: orderForm.symbol,
      side: orderForm.side,
      amount: amount,
      entryPrice: entryPrice,
      currentPrice: currentPrice,
      pnl: 0, // New position has no P&L yet
      pnlPercent: 0,
      stopLoss: orderForm.stopLoss ? entryPrice * (1 - parseFloat(orderForm.stopLoss) / 100) : undefined,
      trailingStop: orderForm.trailingStop ? parseFloat(orderForm.trailingStop) : undefined,
    };

    // Add position to state
    setPositions((prev) => [...prev, newPosition]);

    // Call callback for API integration (Phase 2)
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
  };

  const handleClosePosition = (positionId: string) => {
    // Remove position from state
    setPositions((prev) => prev.filter((p) => p.id !== positionId));
    
    // Call callback for API integration (Phase 2)
    if (onClosePosition) {
      onClosePosition(positionId);
    }
  };

  const totalPnl = positions.reduce((sum, pos) => sum + pos.pnl, 0);
  const totalPnlPercent = balance > 0 ? (totalPnl / balance) * 100 : 0;

  return (
    <div className="flex flex-col h-full bg-gradient-to-br from-[#0a0a1a] to-[#1a1a2e]">
      {/* Header */}
      <div className="bg-dark-card/50 border-b border-gray-800 p-4">
        <div className="flex items-center gap-3">
          <div className="w-3 h-3 bg-green-500 rounded-full" />
          <h2 className="text-xl font-bold text-white">🎯 War Room</h2>
          <span className="text-xs text-gray-400 ml-auto">Tactical Operations</span>
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
        {positions.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <Target size={48} className="mx-auto mb-2 opacity-50" />
            <div>No open positions</div>
            <div className="text-xs mt-1">Open a position to start trading</div>
          </div>
        ) : (
          <div className="space-y-3">
            {positions.map((position) => (
              <div
                key={position.id}
                className="bg-dark-card rounded-lg p-4 border border-gray-700"
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
                    <div className="text-xs text-gray-400">
                      {position.amount} @ ${position.entryPrice.toLocaleString()}
                    </div>
                  </div>
                  <div className={`text-right ${position.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    <div className="font-bold">
                      {position.pnl >= 0 ? '+' : ''}${position.pnl.toFixed(2)}
                    </div>
                    <div className="text-xs">
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
                    onClick={() => onSetStopLoss?.(position.id, position.entryPrice * 0.97)}
                    className="flex-1 px-3 py-1.5 bg-yellow-600/20 hover:bg-yellow-600/30 text-yellow-400 rounded text-xs font-medium transition-colors"
                  >
                    Set Stop Loss
                  </button>
                  <button
                    onClick={() => onSetTrailingStop?.(position.id, 2.5)}
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
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

