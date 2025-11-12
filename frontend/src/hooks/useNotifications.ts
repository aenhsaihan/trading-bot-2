import { useState, useEffect, useCallback } from 'react';
import { Notification } from '../types/notification';
import { notificationAPI } from '../services/api';

export function useNotifications() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);

  const fetchNotifications = useCallback(async () => {
    try {
      setLoading(true);
      const data = await notificationAPI.getNotifications();
      setNotifications(data.notifications);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch notifications');
      console.error('Error fetching notifications:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchNotifications();
    
    // Set up WebSocket connection
    const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/notifications';
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('WebSocket connected');
      setConnected(true);
      // Send ping to keep connection alive
      ws.send('ping');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        // Handle connection message
        if (data.type === 'connected') {
          console.log('WebSocket:', data.message);
          return;
        }

        // Handle notification
        if (data.id && data.type) {
          const notification = data as Notification;
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
        console.error('Error parsing WebSocket message:', err);
      }
    };

    ws.onerror = (err) => {
      console.error('WebSocket error:', err);
      setConnected(false);
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setConnected(false);
      // Try to reconnect after 3 seconds
      setTimeout(() => {
        fetchNotifications();
      }, 3000);
    };

    // Ping every 30 seconds to keep connection alive
    const pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send('ping');
      }
    }, 30000);

    return () => {
      clearInterval(pingInterval);
      ws.close();
    };
  }, [fetchNotifications]);

  const markAsRead = useCallback(async (id: string) => {
    try {
      await notificationAPI.markAsRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, read: true } : n))
      );
    } catch (err) {
      console.error('Error marking as read:', err);
    }
  }, []);

  const respond = useCallback(
    async (id: string, action: string, customMessage?: string) => {
      try {
        await notificationAPI.respondToNotification(id, action, customMessage);
        setNotifications((prev) =>
          prev.map((n) =>
            n.id === id
              ? { ...n, responded: true, response_action: action }
              : n
          )
        );
      } catch (err) {
        console.error('Error responding to notification:', err);
      }
    },
    []
  );

  const deleteNotification = useCallback(async (id: string) => {
    try {
      await notificationAPI.deleteNotification(id);
      setNotifications((prev) => prev.filter((n) => n.id !== id));
    } catch (err) {
      console.error('Error deleting notification:', err);
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

