import { useState, useEffect } from "react";
import { useNotifications } from "./hooks/useNotifications";
import { ToastContainer } from "./components/ToastContainer";
import { NotificationCenter } from "./components/NotificationCenter";
import { Workspace } from "./components/Workspace";
import { ResizableSplitView } from "./components/ResizableSplitView";
import { notificationAPI } from "./services/api";
import { Notification } from "./types/notification";
import { Wifi, WifiOff, Bell } from "lucide-react";

function App() {
  const { notifications, loading, connected, markAsRead, respond, refresh } =
    useNotifications();

  // Debug: Log notifications
  useEffect(() => {
    console.log(
      "App: notifications updated",
      notifications.length,
      notifications
    );
  }, [notifications]);

  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const [apiHealth, setApiHealth] = useState<boolean>(false);
  const [selectedNotification, setSelectedNotification] =
    useState<Notification | null>(null);
  const [notificationsCollapsed, setNotificationsCollapsed] = useState(() => {
    // Load collapsed state from localStorage
    const stored = localStorage.getItem("notificationsCollapsed");
    return stored ? JSON.parse(stored) : false;
  });

  // Persist collapse state to localStorage
  useEffect(() => {
    localStorage.setItem(
      "notificationsCollapsed",
      JSON.stringify(notificationsCollapsed)
    );
  }, [notificationsCollapsed]);

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

  const handleDismiss = (id: string) => {
    // Store dismissed ID in localStorage to prevent it from showing again on refresh
    // This keeps the notification unread but prevents toast spam
    const dismissedIds = JSON.parse(
      localStorage.getItem("dismissedToastIds") || "[]"
    );
    if (!dismissedIds.includes(id)) {
      dismissedIds.push(id);
      localStorage.setItem("dismissedToastIds", JSON.stringify(dismissedIds));
    }
  };

  const handleNotificationSelect = async (notification: Notification) => {
    setSelectedNotification(notification);
    // Mark as read when selected
    if (!notification.read) {
      await markAsRead(notification.id);
    }
  };

  const handleActionRequest = (action: string, params: any) => {
    console.log("Action requested:", action, params);
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
              {/* Notifications Toggle - Show when collapsed */}
              {notificationsCollapsed && (
                <button
                  onClick={() => setNotificationsCollapsed(false)}
                  className="relative px-3 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-white text-sm font-medium transition-colors flex items-center gap-2"
                  title="Show notifications panel"
                >
                  <Bell size={18} />
                  Notifications
                  {notifications.filter((n) => !n.read).length > 0 && (
                    <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                      {notifications.filter((n) => !n.read).length}
                    </span>
                  )}
                </button>
              )}

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
        onNotificationClick={handleNotificationSelect}
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
              onSelect={handleNotificationSelect}
              selectedNotificationId={selectedNotification?.id}
              loading={loading}
              onCollapse={() => setNotificationsCollapsed(true)}
            />
          }
          defaultLeftWidth={60}
          minLeftWidth={40}
          maxLeftWidth={80}
          rightCollapsed={notificationsCollapsed}
        />
      </div>
    </div>
  );
}

export default App;
