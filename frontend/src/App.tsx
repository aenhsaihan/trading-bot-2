import { useState, useEffect } from 'react';
import { useNotifications } from './hooks/useNotifications';
import { ToastContainer } from './components/ToastContainer';
import { NotificationCenter } from './components/NotificationCenter';
import { Workspace } from './components/Workspace';
import { ResizableSplitView } from './components/ResizableSplitView';
import { notificationAPI } from './services/api';
import { Notification } from './types/notification';
import { Wifi, WifiOff } from 'lucide-react';

function App() {
  const {
    notifications,
    loading,
    connected,
    markAsRead,
    respond,
    refresh,
  } = useNotifications();

  // Debug: Log notifications
  useEffect(() => {
    console.log('App: notifications updated', notifications.length, notifications);
  }, [notifications]);

  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const [apiHealth, setApiHealth] = useState<boolean>(false);
  const [selectedNotification, setSelectedNotification] = useState<Notification | null>(null);

  // Check API health
  useEffect(() => {
    const checkHealth = async () => {
      const healthy = await notificationAPI.healthCheck();
      setApiHealth(healthy);
    };
    checkHealth();
    const interval = setInterval(checkHealth, 5000);
    return () => clearInterval(interval);
  }, []);


  const handleDismiss = async (id: string) => {
    await markAsRead(id);
  };

  const handleActionRequest = (action: string, params: any) => {
    console.log('Action requested:', action, params);
    // TODO: Implement action handling in Phase 2 & 4
  };

  return (
    <div className="h-screen flex flex-col bg-gradient-to-br from-[#0f0f1e] via-[#1a1a2e] to-[#0f0f1e] overflow-hidden">
      {/* Header */}
      <header className="bg-dark-card/50 backdrop-blur-sm border-b border-gray-800 flex-shrink-0 z-40">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-white">
                ⚔️ Trading Command Center
              </h1>
              <p className="text-sm text-gray-400">
                Notification-driven tactical trading interface
              </p>
            </div>
            <div className="flex items-center gap-4">
              {/* Connection Status */}
              <div className="flex items-center gap-2 text-sm">
                {connected ? (
                  <>
                    <Wifi className="text-green-400" size={18} />
                    <span className="text-green-400">Connected</span>
                  </>
                ) : (
                  <>
                    <WifiOff className="text-red-400" size={18} />
                    <span className="text-red-400">Disconnected</span>
                  </>
                )}
              </div>

              {/* Voice Toggle */}
              <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={voiceEnabled}
                  onChange={(e) => setVoiceEnabled(e.target.checked)}
                  className="rounded"
                />
                🔊 Voice Alerts
              </label>
            </div>
          </div>
        </div>
      </header>

      {/* API Status Banner */}
      {!apiHealth && (
        <div className="bg-red-500/20 border-b border-red-500 px-6 py-2 text-center flex-shrink-0">
          <div className="text-red-400 font-medium text-sm">
            ⚠️ FastAPI backend not available. Please start the backend server.
          </div>
        </div>
      )}

      {/* Toast Notifications */}
      <ToastContainer
        notifications={notifications}
        onDismiss={handleDismiss}
        voiceEnabled={voiceEnabled}
      />

      {/* Main Content - Split View */}
      <div className="flex-1 overflow-hidden">
        <ResizableSplitView
          left={
            <Workspace
              selectedNotification={selectedNotification}
              onActionRequest={handleActionRequest}
            />
          }
          right={
            <NotificationCenter
              notifications={notifications}
              onMarkRead={markAsRead}
              onRespond={respond}
              onRefresh={refresh}
              onSelect={setSelectedNotification}
              selectedNotificationId={selectedNotification?.id}
              loading={loading}
            />
          }
          defaultLeftWidth={60}
          minLeftWidth={40}
          maxLeftWidth={80}
        />
      </div>
    </div>
  );
}

export default App;

