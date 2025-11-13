import { useState } from 'react';
import { MessageSquare, Target, BarChart3 } from 'lucide-react';
import { CommandCenter } from './CommandCenter';
import { WarRoom } from './WarRoom';
import { MarketIntelligence } from './MarketIntelligence';
import { Notification } from '../types/notification';

interface WorkspaceProps {
  selectedNotification?: Notification | null;
  onActionRequest?: (action: string, params: any) => void;
}

type Tab = 'command' | 'warroom' | 'intelligence';

export function Workspace({ selectedNotification, onActionRequest }: WorkspaceProps) {
  const [activeTab, setActiveTab] = useState<Tab>('command');

  return (
    <div className="flex flex-col h-full bg-gradient-to-br from-[#0f0f1e] via-[#1a1a2e] to-[#0f0f1e]">
      {/* Tabs */}
      <div className="flex border-b border-gray-800 bg-dark-card/30">
        <button
          onClick={() => setActiveTab('command')}
          className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 font-medium transition-colors ${
            activeTab === 'command'
              ? 'bg-dark-card text-white border-b-2 border-blue-500'
              : 'text-gray-400 hover:text-white hover:bg-dark-card/50'
          }`}
        >
          <MessageSquare size={18} />
          Command Center
        </button>
        <button
          onClick={() => setActiveTab('warroom')}
          className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 font-medium transition-colors ${
            activeTab === 'warroom'
              ? 'bg-dark-card text-white border-b-2 border-green-500'
              : 'text-gray-400 hover:text-white hover:bg-dark-card/50'
          }`}
        >
          <Target size={18} />
          War Room
        </button>
        <button
          onClick={() => setActiveTab('intelligence')}
          className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 font-medium transition-colors ${
            activeTab === 'intelligence'
              ? 'bg-dark-card text-white border-b-2 border-purple-500'
              : 'text-gray-400 hover:text-white hover:bg-dark-card/50'
          }`}
        >
          <BarChart3 size={18} />
          Market Intelligence
        </button>
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'command' && (
          <CommandCenter
            selectedNotification={selectedNotification}
            onActionRequest={onActionRequest}
          />
        )}
        {activeTab === 'warroom' && (
          <WarRoom
            selectedNotification={selectedNotification}
            onOpenPosition={(symbol, side, amount) => {
              console.log('Open position:', { symbol, side, amount });
              onActionRequest?.('open_position', { symbol, side, amount });
            }}
            onClosePosition={(positionId) => {
              console.log('Close position:', positionId);
              onActionRequest?.('close_position', { positionId });
            }}
            onSetStopLoss={(positionId, stopLoss) => {
              console.log('Set stop loss:', { positionId, stopLoss });
              onActionRequest?.('set_stop_loss', { positionId, stopLoss });
            }}
            onSetTrailingStop={(positionId, trailingStop) => {
              console.log('Set trailing stop:', { positionId, trailingStop });
              onActionRequest?.('set_trailing_stop', { positionId, trailingStop });
            }}
          />
        )}
        {activeTab === 'intelligence' && (
          <MarketIntelligence selectedNotification={selectedNotification} />
        )}
      </div>
    </div>
  );
}

