import { useState, useEffect, useRef, useCallback } from "react";

export type WebSocketStatus = "connecting" | "connected" | "disconnected" | "error";

export interface UseWebSocketOptions {
  url: string;
  reconnectInterval?: number;
  reconnectAttempts?: number;
  onMessage?: (data: any) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
  autoConnect?: boolean;
}

export interface UseWebSocketReturn {
  status: WebSocketStatus;
  send: (data: string | object) => void;
  connect: () => void;
  disconnect: () => void;
  lastMessage: any;
  error: Event | null;
}

/**
 * Reusable WebSocket hook with automatic reconnection
 */
export function useWebSocket(options: UseWebSocketOptions): UseWebSocketReturn {
  const {
    url,
    reconnectInterval = 3000,
    reconnectAttempts = Infinity,
    onMessage,
    onConnect,
    onDisconnect,
    onError,
    autoConnect = true,
  } = options;

  const [status, setStatus] = useState<WebSocketStatus>("disconnected");
  const [lastMessage, setLastMessage] = useState<any>(null);
  const [error, setError] = useState<Event | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectCountRef = useRef(0);
  const shouldReconnectRef = useRef(true);
  const pingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const isConnectingRef = useRef(false); // Lock to prevent multiple simultaneous connection attempts
  
  // Use refs for callbacks to avoid recreating connect function
  const onMessageRef = useRef(onMessage);
  const onConnectRef = useRef(onConnect);
  const onDisconnectRef = useRef(onDisconnect);
  const onErrorRef = useRef(onError);
  const reconnectIntervalRef = useRef(reconnectInterval);
  const reconnectAttemptsRef = useRef(reconnectAttempts);
  const urlRef = useRef(url); // Store URL in ref to prevent unnecessary reconnections

  // Update refs when they change
  useEffect(() => {
    onMessageRef.current = onMessage;
    onConnectRef.current = onConnect;
    onDisconnectRef.current = onDisconnect;
    onErrorRef.current = onError;
    reconnectIntervalRef.current = reconnectInterval;
    reconnectAttemptsRef.current = reconnectAttempts;
    urlRef.current = url; // Update URL ref
  }, [onMessage, onConnect, onDisconnect, onError, reconnectInterval, reconnectAttempts, url]);

  const connect = useCallback(() => {
    // Prevent multiple simultaneous connection attempts
    if (isConnectingRef.current) {
      console.log("WebSocket: Connection already in progress, skipping...");
      return;
    }

    // If already connected, don't reconnect
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      console.log("WebSocket: Already connected, skipping...");
      return;
    }

    // Close existing connection if any (including CONNECTING state)
    if (wsRef.current) {
      const currentState = wsRef.current.readyState;
      if (currentState === WebSocket.OPEN || currentState === WebSocket.CONNECTING) {
        // Close existing connection before creating new one
        try {
          wsRef.current.close();
        } catch (e) {
          // Ignore errors when closing
        }
        wsRef.current = null;
      }
    }

    isConnectingRef.current = true;
    shouldReconnectRef.current = true;
    setStatus("connecting");

    try {
      // Use ref to get latest URL without recreating function
      const currentUrl = urlRef.current;
      const ws = new WebSocket(currentUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log("WebSocket connected:", currentUrl);
        isConnectingRef.current = false; // Release connection lock
        setStatus("connected");
        setError(null);
        reconnectCountRef.current = 0;
        onConnectRef.current?.();

        // Start ping interval (every 30 seconds)
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send("ping");
          }
        }, 30000);
      };

      ws.onmessage = (event) => {
        try {
          // Handle pong
          if (event.data === "pong") {
            return;
          }

          // Try to parse as JSON
          let data: any;
          try {
            data = JSON.parse(event.data);
          } catch {
            // Not JSON, use raw data
            data = event.data;
          }

          setLastMessage(data);
          onMessageRef.current?.(data);
        } catch (err) {
          console.error("Error processing WebSocket message:", err);
        }
      };

      ws.onerror = (event) => {
        console.error("WebSocket error:", event);
        setError(event);
        setStatus("error");
        onErrorRef.current?.(event);
      };

      ws.onclose = () => {
        console.log("WebSocket disconnected:", currentUrl);
        isConnectingRef.current = false; // Release connection lock
        setStatus("disconnected");
        onDisconnectRef.current?.();

        // Clear ping interval
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }

        // Attempt reconnection (using refs)
        const interval = reconnectIntervalRef.current;
        const attempts = reconnectAttemptsRef.current;
        if (shouldReconnectRef.current && reconnectCountRef.current < attempts) {
          reconnectCountRef.current += 1;
          console.log(
            `Attempting to reconnect (${reconnectCountRef.current}/${attempts})...`
          );

          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, interval);
        } else if (reconnectCountRef.current >= attempts) {
          console.log("Max reconnection attempts reached");
          setStatus("error");
        }
      };
    } catch (err) {
      console.error("Error creating WebSocket:", err);
      isConnectingRef.current = false; // Release connection lock on error
      setStatus("error");
    }
  }, []); // No dependencies - use refs for all values to prevent unnecessary reconnections

  const disconnect = useCallback(() => {
    shouldReconnectRef.current = false;
    isConnectingRef.current = false; // Release connection lock

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }

    if (wsRef.current) {
      try {
        wsRef.current.close();
      } catch (e) {
        // Ignore errors when closing
      }
      wsRef.current = null;
    }

    setStatus("disconnected");
  }, []);

  const send = useCallback((data: string | object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const message = typeof data === "string" ? data : JSON.stringify(data);
      wsRef.current.send(message);
    } else {
      console.warn("WebSocket is not connected. Cannot send message.");
    }
  }, []);

  // Track if we've already attempted to connect to prevent multiple connections
  const hasAttemptedConnectRef = useRef(false);
  const lastAutoConnectRef = useRef(autoConnect);

  // Auto-connect on mount if enabled
  useEffect(() => {
    // Only connect if:
    // 1. autoConnect is true
    // 2. autoConnect changed from false to true (or is initial mount)
    // 3. We haven't already attempted to connect for this autoConnect value
    // 4. We're not already connected
    const autoConnectChanged = lastAutoConnectRef.current !== autoConnect;
    lastAutoConnectRef.current = autoConnect;

    if (autoConnect && (autoConnectChanged || !hasAttemptedConnectRef.current) && wsRef.current?.readyState !== WebSocket.OPEN) {
      if (!isConnectingRef.current) {
        hasAttemptedConnectRef.current = true;
        connect();
      }
    } else if (!autoConnect && wsRef.current?.readyState === WebSocket.OPEN) {
      // If autoConnect changed to false, disconnect
      disconnect();
      hasAttemptedConnectRef.current = false;
    }

    return () => {
      // Only disconnect on unmount if autoConnect is false or we're explicitly disconnecting
      // Don't disconnect if autoConnect is true and component is just re-rendering
      if (!autoConnect) {
        hasAttemptedConnectRef.current = false;
        disconnect();
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoConnect]); // Only depend on autoConnect - connect/disconnect are stable

  return {
    status,
    send,
    connect,
    disconnect,
    lastMessage,
    error,
  };
}


