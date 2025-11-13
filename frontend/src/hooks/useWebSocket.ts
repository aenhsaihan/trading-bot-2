import { useState, useEffect, useRef, useCallback } from "react";

// Global connection registry to prevent duplicate connections in StrictMode
// Maps URL to active WebSocket instance
const globalConnections = new Map<string, WebSocket>();

// Connection locks to prevent race conditions during startup
// Maps URL to a promise that resolves when connection is ready
const connectionLocks = new Map<string, Promise<WebSocket>>();

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

    // Use ref to get latest URL
    const currentUrl = urlRef.current;

    // Check if there's already a global connection for this URL (StrictMode protection)
    const existingGlobalConnection = globalConnections.get(currentUrl);
    if (existingGlobalConnection) {
      const state = existingGlobalConnection.readyState;
      // Reuse if OPEN or CONNECTING (don't create duplicate)
      if (state === WebSocket.OPEN || state === WebSocket.CONNECTING) {
        console.log("WebSocket: Reusing existing global connection (StrictMode protection)", state === WebSocket.OPEN ? "OPEN" : "CONNECTING");
        wsRef.current = existingGlobalConnection;
        setStatus(state === WebSocket.OPEN ? "connected" : "connecting");
        // Don't set isConnectingRef since we're reusing
        return;
      } else {
        // Connection is closed, remove from registry
        globalConnections.delete(currentUrl);
        connectionLocks.delete(currentUrl);
      }
    }

    // Check if there's a connection in progress (race condition protection)
    const existingLock = connectionLocks.get(currentUrl);
    if (existingLock) {
      console.log("WebSocket: Waiting for existing connection attempt...");
      existingLock.then((ws) => {
        if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
          wsRef.current = ws;
          setStatus(ws.readyState === WebSocket.OPEN ? "connected" : "connecting");
        }
      }).catch(() => {
        // Connection failed, will retry
      });
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
      const ws = new WebSocket(currentUrl);
      wsRef.current = ws;
      
      // Register in global connections map (for StrictMode protection)
      globalConnections.set(currentUrl, ws);
      
      // Create connection lock promise for race condition protection
      const connectionPromise = new Promise<WebSocket>((resolve, reject) => {
        connectionLocks.set(currentUrl, connectionPromise);
        
        ws.onopen = () => {
          resolve(ws);
          connectionLocks.delete(currentUrl); // Remove lock once connected
        };
        
        ws.onerror = (error) => {
          connectionLocks.delete(currentUrl);
          globalConnections.delete(currentUrl);
          reject(error);
        };
        
        ws.onclose = () => {
          connectionLocks.delete(currentUrl);
          if (globalConnections.get(currentUrl) === ws) {
            globalConnections.delete(currentUrl);
          }
        };
      });

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
        // Remove from global connections map
        if (globalConnections.get(currentUrl) === ws) {
          globalConnections.delete(currentUrl);
        }
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
      const currentUrl = urlRef.current;
      try {
        wsRef.current.close();
      } catch (e) {
        // Ignore errors when closing
      }
      // Remove from global connections map
      if (globalConnections.get(currentUrl) === wsRef.current) {
        globalConnections.delete(currentUrl);
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
      // In StrictMode, components unmount and remount immediately
      // Don't disconnect on unmount if autoConnect is true - let the global registry handle it
      // Only disconnect if autoConnect is explicitly false
      if (!autoConnect) {
        hasAttemptedConnectRef.current = false;
        disconnect();
      } else {
        // autoConnect is true - don't disconnect on unmount (StrictMode will remount)
        // The global registry will handle connection reuse
        // Just reset the attempt flag so it can reconnect if needed
        hasAttemptedConnectRef.current = false;
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


