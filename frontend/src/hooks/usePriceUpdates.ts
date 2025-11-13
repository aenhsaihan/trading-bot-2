import { useEffect, useState, useRef, useCallback } from "react";

// Global connection registry to prevent duplicate connections in StrictMode
// Maps URL to active WebSocket instance
const globalPriceConnections = new Map<string, WebSocket>();

interface PriceUpdate {
  type: "price_update";
  timestamp: string;
  prices: Record<string, number>;
}

interface UsePriceUpdatesOptions {
  symbols?: string[];
  onPriceUpdate?: (prices: Record<string, number>) => void;
  reconnectInterval?: number;
}

export function usePriceUpdates(options: UsePriceUpdatesOptions = {}) {
  const { symbols = [], onPriceUpdate, reconnectInterval = 5000 } = options;
  const [prices, setPrices] = useState<Record<string, number>>({});
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(
    null
  );
  const symbolsRef = useRef<string[]>(symbols);
  const onPriceUpdateRef = useRef(onPriceUpdate);
  const reconnectIntervalRef = useRef(reconnectInterval);

  // Update refs when they change (without causing re-renders)
  useEffect(() => {
    symbolsRef.current = symbols;
    onPriceUpdateRef.current = onPriceUpdate;
    reconnectIntervalRef.current = reconnectInterval;
  }, [symbols, onPriceUpdate, reconnectInterval]);

  const connect = useCallback(() => {
    const apiUrl =
      (import.meta as any).env?.VITE_API_URL || "http://localhost:8000";
    const wsUrl = apiUrl
      .replace("http://", "ws://")
      .replace("https://", "wss://");
    const fullUrl = `${wsUrl}/ws/prices`;

    // Check if there's already a global connection for this URL (StrictMode protection)
    const existingGlobalConnection = globalPriceConnections.get(fullUrl);
    if (existingGlobalConnection) {
      const state = existingGlobalConnection.readyState;
      // Reuse if OPEN or CONNECTING (don't create duplicate)
      if (state === WebSocket.OPEN || state === WebSocket.CONNECTING) {
        console.log("Price WebSocket: Reusing existing global connection (StrictMode protection)", state === WebSocket.OPEN ? "OPEN" : "CONNECTING");
        wsRef.current = existingGlobalConnection;
        setIsConnected(state === WebSocket.OPEN);
        // Subscribe to symbols if provided
        if (symbolsRef.current.length > 0 && state === WebSocket.OPEN) {
          existingGlobalConnection.send(`subscribe:${JSON.stringify(symbolsRef.current)}`);
        }
        return;
      } else {
        // Connection is closed, remove from registry
        globalPriceConnections.delete(fullUrl);
      }
    }

    // Close existing connection if any
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    // Clear any pending reconnect
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    const ws = new WebSocket(fullUrl);
    
    // Register in global connections map (for StrictMode protection)
    globalPriceConnections.set(fullUrl, ws);

    ws.onopen = () => {
      console.log("Price update WebSocket connected");
      setIsConnected(true);
      setError(null);

      // Subscribe to symbols if provided
      if (symbolsRef.current.length > 0) {
        ws.send(`subscribe:${JSON.stringify(symbolsRef.current)}`);
      }
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === "connected") {
          console.log("Price update WebSocket: Connected", data);
          // Subscribe to symbols if provided
          if (symbolsRef.current.length > 0) {
            ws.send(`subscribe:${JSON.stringify(symbolsRef.current)}`);
          }
        } else if (data.type === "price_update") {
          const update = data as PriceUpdate;
          setPrices((prev) => {
            const updated = { ...prev, ...update.prices };
            // Call callback if provided (using ref to avoid stale closure)
            if (onPriceUpdateRef.current) {
              onPriceUpdateRef.current(updated);
            }
            return updated;
          });
        } else if (data.type === "subscribed") {
          console.log(
            "Price update WebSocket: Subscribed to symbols",
            data.symbols
          );
        }
      } catch (err) {
        console.error("Error parsing price update message:", err);
      }
    };

    ws.onerror = (error) => {
      console.error("Price update WebSocket error:", error);
      setError("WebSocket connection error");
      setIsConnected(false);
    };

    ws.onclose = () => {
      console.log("Price update WebSocket disconnected");
      setIsConnected(false);
      
      // Remove from global connections map
      if (globalPriceConnections.get(fullUrl) === ws) {
        globalPriceConnections.delete(fullUrl);
      }

      // Attempt to reconnect after delay (using ref to get latest value)
      const interval = reconnectIntervalRef.current;
      if (interval > 0) {
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log("Attempting to reconnect price update WebSocket...");
          connect();
        }, interval);
      }
    };

    wsRef.current = ws;
  }, []); // Empty deps - function is stable, uses refs for values

  // Track if we've already connected to prevent multiple connections
  const hasConnectedRef = useRef(false);

  // Connect only once on mount
  useEffect(() => {
    // Only connect if we haven't already connected
    if (!hasConnectedRef.current && wsRef.current?.readyState !== WebSocket.OPEN) {
      hasConnectedRef.current = true;
      connect();
    }

    return () => {
      // In StrictMode, components unmount and remount immediately
      // Don't disconnect on unmount - let the global registry handle it
      // Only cleanup reconnect timeout, but keep connection alive
      hasConnectedRef.current = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      // Don't close WebSocket on unmount - let global registry handle reuse
      // The connection will be cleaned up when it actually closes
      wsRef.current = null; // Clear ref, but don't close connection
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run on mount

  // Update subscription when symbols change
  useEffect(() => {
    if (
      wsRef.current &&
      wsRef.current.readyState === WebSocket.OPEN &&
      symbols.length > 0
    ) {
      wsRef.current.send(`subscribe:${JSON.stringify(symbols)}`);
    }
  }, [symbols]);

  return {
    prices,
    isConnected,
    error,
    reconnect: connect,
  };
}
