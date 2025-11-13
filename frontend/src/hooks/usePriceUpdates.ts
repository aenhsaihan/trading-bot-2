import { useEffect, useState, useRef, useCallback } from "react";

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

    const apiUrl =
      (import.meta as any).env?.VITE_API_URL || "http://localhost:8000";
    const wsUrl = apiUrl
      .replace("http://", "ws://")
      .replace("https://", "wss://");
    const ws = new WebSocket(`${wsUrl}/ws/prices`);

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
      // Cleanup on unmount
      hasConnectedRef.current = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      if (wsRef.current) {
        try {
          wsRef.current.close();
        } catch (e) {
          // Ignore errors when closing
        }
        wsRef.current = null;
      }
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
