import { useState, useEffect } from 'react';
import { useNotifications } from './hooks/useNotifications';
import { ToastContainer } from './components/ToastContainer';
import { NotificationCenter } from './components/NotificationCenter';
import { SystemStatus } from './components/SystemStatus';
import { notificationAPI } from './services/api';
import { Wifi, WifiOff } from 'lucide-react';

function App() {
  const {
    notifications,
    loading,
    error,
    connected,
    markAsRead,
    respond,
    deleteNotification,
    refresh,
  } = useNotifications();

  // Debug: Log notifications
  useEffect(() => {
    console.log('App: notifications updated', notifications.length, notifications);
  }, [notifications]);

  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const [systemStatus, setSystemStatus] = useState<any>(null);
  const [apiHealth, setApiHealth] = useState<boolean>(false);

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

  // Get system status
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const stats = await notificationAPI.getStats();
        const unreadCount = notifications.filter((n) => !n.read).length;
        const criticalCount = notifications.filter(
          (n) => n.priority === 'critical'
        ).length;
        const highCount = notifications.filter((n) => n.priority === 'high').length;

        let status = 'ok';
        let message = '✅ All systems normal - Monitoring active';

        if (criticalCount > 0) {
          status = 'critical';
          message = `⚠️ ${criticalCount} critical alert(s) require attention`;
        } else if (highCount > 0) {
          status = 'attention';
          message = `📊 ${highCount} high-priority opportunity(ies) available`;
        } else if (unreadCount > 0) {
          status = 'active';
          message = `✅ ${unreadCount} notification(s) - All systems normal`;
        }

        setSystemStatus({
          status,
          message,
          unread_count: unreadCount,
          critical_count: criticalCount,
          high_count: highCount,
          total_notifications: notifications.length,
        });
      } catch (err) {
        console.error('Error fetching status:', err);
      }
    };

    fetchStatus();
  }, [notifications]);

  const handleDismiss = async (id: string) => {
    await markAsRead(id);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0f0f1e] via-[#1a1a2e] to-[#0f0f1e]">
      {/* Header */}
      <header className="bg-dark-card/50 backdrop-blur-sm border-b border-gray-800 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-white">
                Trading Bot Notifications
              </h1>
              <p className="text-sm text-gray-400">
                Real-time alerts and opportunities
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

      {/* Toast Notifications */}
      <ToastContainer
        notifications={notifications}
        onDismiss={handleDismiss}
        voiceEnabled={voiceEnabled}
      />

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* API Status */}
        {!apiHealth && (
          <div className="bg-red-500/20 border border-red-500 rounded-lg p-4 mb-6 text-center">
            <div className="text-red-400 font-medium">
              ⚠️ FastAPI backend not available. Please start the backend server.
            </div>
          </div>
        )}

        {/* Debug Info */}
        <div className="bg-blue-500/20 border border-blue-500 rounded-lg p-4 mb-6 text-sm">
          <div className="text-blue-300">
            <strong>Debug Info:</strong>
            <br />
            API Health: {apiHealth ? '✅ Connected' : '❌ Disconnected'}
            <br />
            WebSocket: {connected ? '✅ Connected' : '❌ Disconnected'}
            <br />
            Notifications: {notifications.length} total, {notifications.filter(n => !n.read).length} unread
            <br />
            Loading: {loading ? 'Yes' : 'No'}
            {error && <><br />Error: {error}</>}
          </div>
        </div>

        {/* System Status */}
        {systemStatus && <SystemStatus status={systemStatus} />}

        {/* Error Display */}
        {error && (
          <div className="bg-red-500/20 border border-red-500 rounded-lg p-4 mb-6">
            <div className="text-red-400">Error: {error}</div>
          </div>
        )}

        {/* Notification Center */}
        <NotificationCenter
          notifications={notifications}
          onMarkRead={markAsRead}
          onRespond={respond}
          onRefresh={refresh}
          loading={loading}
        />
      </main>
    </div>
  );
}

export default App;

