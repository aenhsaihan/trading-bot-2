import { useState, useEffect, useCallback, useRef } from "react";
import { Notification } from "../types/notification";
import { notificationAPI } from "../services/api";

// Global connection registry to prevent duplicate connections in StrictMode
// Maps URL to active WebSocket instance
const globalNotificationConnections = new Map<string, WebSocket>();

export function useNotifications() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);

  const fetchNotifications = useCallback(async () => {
    try {
      setLoading(true);
      console.log("Fetching notifications from API...");
      const data = await notificationAPI.getNotifications();
      console.log("Notifications fetched:", data);
      setNotifications(data.notifications);
      setError(null);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to fetch notifications"
      );
      console.error("Error fetching notifications:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    fetchNotifications();

    // Set up WebSocket connection
    const wsUrl =
      (import.meta as any).env?.VITE_WS_URL ||
      "ws://localhost:8000/ws/notifications";
    console.log("Connecting to WebSocket:", wsUrl);

    // Check if there's already a global connection for this URL (StrictMode protection)
    const existingGlobalConnection = globalNotificationConnections.get(wsUrl);
    if (existingGlobalConnection) {
      const state = existingGlobalConnection.readyState;
      // Reuse if OPEN or CONNECTING (don't create duplicate)
      if (state === WebSocket.OPEN || state === WebSocket.CONNECTING) {
        console.log("Notification WebSocket: Reusing existing global connection (StrictMode protection)", state === WebSocket.OPEN ? "OPEN" : "CONNECTING");
        wsRef.current = existingGlobalConnection;
        setConnected(state === WebSocket.OPEN);
        // Set up message handler for reused connection
        existingGlobalConnection.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            console.log("WebSocket message received:", data);

            // Handle connection message
            if (data.type === "connected") {
              console.log("WebSocket:", data.message);
              return;
            }

            // Handle notification
            if (data.id && data.type) {
              const notification = data as Notification;
              console.log("New notification via WebSocket:", notification);
              setNotifications((prev) => {
                // Check if notification already exists
                const exists = prev.some((n) => n.id === notification.id);
                if (exists) {
                  return prev.map((n) =>
                    n.id === notification.id ? notification : n
                  );
                }
                // Add new notification at the beginning
                return [notification, ...prev];
              });
            }
          } catch (err) {
            console.error("Error parsing WebSocket message:", err);
          }
        };
        // Set up ping interval for reused connection
        const pingInterval = setInterval(() => {
          if (existingGlobalConnection.readyState === WebSocket.OPEN) {
            existingGlobalConnection.send("ping");
          }
        }, 30000);
        
        // Don't create new connection, return early
        return () => {
          clearInterval(pingInterval);
          // Don't close on unmount - let global registry handle it
          wsRef.current = null;
        };
      } else {
        // Connection is closed, remove from registry
        globalNotificationConnections.delete(wsUrl);
      }
    }

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;
    
    // Register in global connections map (for StrictMode protection)
    globalNotificationConnections.set(wsUrl, ws);

    ws.onopen = () => {
      console.log("WebSocket connected");
      setConnected(true);
      // Send ping to keep connection alive
      ws.send("ping");
    };

    ws.onmessage = (event) => {
      try {
        // Handle pong
        if (event.data === "pong") {
          return;
        }
        
        const data = JSON.parse(event.data);
        console.log("WebSocket message received:", data);

        // Handle connection message
        if (data.type === "connected") {
          console.log("WebSocket:", data.message);
          return;
        }

        // Handle notification
        if (data.id && data.type) {
          const notification = data as Notification;
          console.log("New notification via WebSocket:", notification);
          setNotifications((prev) => {
            // Check if notification already exists
            const exists = prev.some((n) => n.id === notification.id);
            if (exists) {
              return prev.map((n) =>
                n.id === notification.id ? notification : n
              );
            }
            // Add new notification at the beginning
            return [notification, ...prev];
          });
        }
      } catch (err) {
        console.error("Error parsing WebSocket message:", err);
      }
    };

    ws.onerror = (err) => {
      console.error("WebSocket error:", err);
      setConnected(false);
    };

    ws.onclose = () => {
      console.log("WebSocket disconnected");
      setConnected(false);
      
      // Remove from global connections map
      if (globalNotificationConnections.get(wsUrl) === ws) {
        globalNotificationConnections.delete(wsUrl);
      }
      
      // Try to reconnect after 3 seconds
      setTimeout(() => {
        fetchNotifications();
      }, 3000);
    };

    // Ping every 30 seconds to keep connection alive
    const pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send("ping");
      }
    }, 30000);

    return () => {
      clearInterval(pingInterval);
      // Don't close WebSocket on unmount - let global registry handle reuse
      // The connection will be cleaned up when it actually closes
      wsRef.current = null; // Clear ref, but don't close connection
    };
  }, [fetchNotifications]);

  const markAsRead = useCallback(async (id: string) => {
    try {
      const updatedNotification = await notificationAPI.markAsRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? updatedNotification : n))
      );
    } catch (err) {
      console.error("Error marking as read:", err);
      // Optimistically update on error
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, read: true } : n))
      );
    }
  }, []);

  const respond = useCallback(
    async (id: string, action: string, customMessage?: string) => {
      try {
        await notificationAPI.respondToNotification(id, action, customMessage);
        setNotifications((prev) =>
          prev.map((n) =>
            n.id === id ? { ...n, responded: true, response_action: action } : n
          )
        );
      } catch (err) {
        console.error("Error responding to notification:", err);
      }
    },
    []
  );

  const deleteNotification = useCallback(async (id: string) => {
    try {
      await notificationAPI.deleteNotification(id);
      setNotifications((prev) => prev.filter((n) => n.id !== id));
    } catch (err) {
      console.error("Error deleting notification:", err);
    }
  }, []);

  return {
    notifications,
    loading,
    error,
    connected,
    markAsRead,
    respond,
    deleteNotification,
    refresh: fetchNotifications,
  };
}
