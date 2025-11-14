import { useState, useEffect } from "react";
import { useNotifications } from "./hooks/useNotifications";
import { ToastContainer } from "./components/ToastContainer";
import { NotificationCenter } from "./components/NotificationCenter";
import { Workspace } from "./components/Workspace";
import { ResizableSplitView } from "./components/ResizableSplitView";
import { notificationAPI, systemAPI } from "./services/api";
import { Notification } from "./types/notification";
import { Wifi, WifiOff, Bell } from "lucide-react";
import { initializeVoiceSystem, initializeBrowserTTS } from "./utils/voice";

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

  const [voiceEnabled, setVoiceEnabled] = useState(() => {
    // Check if voice was enabled previously
    const stored = localStorage.getItem("voiceEnabled");
    return stored ? JSON.parse(stored) : true;
  });
  const [apiHealth, setApiHealth] = useState<boolean>(false);
  const [autoSignalsEnabled, setAutoSignalsEnabled] = useState(false);
  const [autoSignalsLoading, setAutoSignalsLoading] = useState(false);
  const [selectedNotification, setSelectedNotification] =
    useState<Notification | null>(null);
  const [requestedAction, setRequestedAction] = useState<
    "openPosition" | "analyze" | null
  >(null);
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

  // Persist voice enabled state
  useEffect(() => {
    localStorage.setItem("voiceEnabled", JSON.stringify(voiceEnabled));
    // If voice is enabled, try to initialize TTS immediately
    if (voiceEnabled) {
      initializeBrowserTTS();
    }
  }, [voiceEnabled]);

  // Initialize voice system on mount
  useEffect(() => {
    initializeVoiceSystem();
  }, []);

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

  // Check notification sources status
  useEffect(() => {
    const checkStatus = async () => {
      if (!apiHealth) return;
      try {
        const status = await systemAPI.getNotificationSourcesStatus();
        setAutoSignalsEnabled(status.running);
      } catch (e) {
        // Service might not be available, that's okay
        console.debug("Could not check notification sources status:", e);
      }
    };
    checkStatus();
    const interval = setInterval(checkStatus, 10000); // Check every 10 seconds
    return () => clearInterval(interval);
  }, [apiHealth]);

  const handleToggleAutoSignals = async (enabled: boolean) => {
    setAutoSignalsLoading(true);
    try {
      if (enabled) {
        await systemAPI.startNotificationSources();
        setAutoSignalsEnabled(true);
      } else {
        await systemAPI.stopNotificationSources();
        setAutoSignalsEnabled(false);
      }
    } catch (e) {
      console.error("Failed to toggle auto signals:", e);
      // Revert on error
      setAutoSignalsEnabled(!enabled);
    } finally {
      setAutoSignalsLoading(false);
    }
  };

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
    console.log("App: Notification selected", notification.id, notification.title);
    setSelectedNotification(notification);
    // Switch to Command Center and trigger analysis when notification is clicked
    setRequestedAction("analyze");
    // Mark as read when selected
    if (!notification.read) {
      await markAsRead(notification.id);
    }
  };

  const handleActionRequest = (action: string, params: any) => {
    console.log("Action requested:", action, params);
    // TODO: Implement action handling in Phase 2 & 4
  };

  const handleOpenPosition = (notification: Notification) => {
    // Set the notification as selected and request War Room action
    setSelectedNotification(notification);
    setRequestedAction("openPosition");
  };

  const handleDismissNotification = (id: string) => {
    // Archive the notification (remove from view, store in archived state)
    const archivedIds = JSON.parse(
      localStorage.getItem("archivedNotificationIds") || "[]"
    );
    if (!archivedIds.includes(id)) {
      archivedIds.push(id);
      localStorage.setItem(
        "archivedNotificationIds",
        JSON.stringify(archivedIds)
      );
    }
    // Clear selection if this notification is currently selected
    if (selectedNotification?.id === id) {
      setSelectedNotification(null);
    }
    // Also mark as read
    markAsRead(id);
  };

  // Initialize browser TTS on any user interaction with the app
  useEffect(() => {
    const handleUserInteraction = () => {
      initializeBrowserTTS();
    };
    
    // Listen for any interaction
    const events = ['click', 'keydown', 'touchstart', 'mousedown'];
    events.forEach(eventType => {
      document.addEventListener(eventType, handleUserInteraction, { once: true, passive: true });
    });
    
    return () => {
      events.forEach(eventType => {
        document.removeEventListener(eventType, handleUserInteraction);
      });
    };
  }, []);

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
                  onChange={(e) => {
                    setVoiceEnabled(e.target.checked);
                    // Initialize browser TTS on toggle (user interaction)
                    if (e.target.checked) {
                      initializeBrowserTTS();
                    }
                  }}
                  className="rounded"
                />
                🔊 Voice Alerts
              </label>

              {/* Auto Signals Toggle */}
              <label 
                className={`flex items-center gap-2 text-sm text-gray-300 cursor-pointer ${autoSignalsLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
                title="Automatically monitor markets and generate notifications from technical signals"
              >
                <input
                  type="checkbox"
                  checked={autoSignalsEnabled}
                  onChange={(e) => handleToggleAutoSignals(e.target.checked)}
                  disabled={autoSignalsLoading || !apiHealth}
                  className="rounded"
                />
                {autoSignalsLoading ? '⏳' : '🤖'} Auto Signals
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
              requestedAction={requestedAction}
              onActionHandled={() => setRequestedAction(null)}
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
              onOpenPosition={handleOpenPosition}
              onDismiss={handleDismissNotification}
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
