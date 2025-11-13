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

    shouldReconnectRef.current = true;
    setStatus("connecting");

    try {
      // Use ref to get latest URL without recreating function
      const currentUrl = urlRef.current;
      const ws = new WebSocket(currentUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log("WebSocket connected:", currentUrl);
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
      setStatus("error");
    }
  }, []); // No dependencies - use refs for all values to prevent unnecessary reconnections

  const disconnect = useCallback(() => {
    shouldReconnectRef.current = false;

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
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

  // Track autoConnect in ref to detect changes
  const autoConnectRef = useRef(autoConnect);
  useEffect(() => {
    autoConnectRef.current = autoConnect;
  }, [autoConnect]);

  // Auto-connect on mount if enabled
  useEffect(() => {
    // Only connect if autoConnect is true and we're not already connected
    if (autoConnectRef.current && wsRef.current?.readyState !== WebSocket.OPEN) {
      connect();
    }

    return () => {
      // Cleanup: disconnect when component unmounts
      disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run once on mount - use refs for values

  return {
    status,
    send,
    connect,
    disconnect,
    lastMessage,
    error,
  };
}


