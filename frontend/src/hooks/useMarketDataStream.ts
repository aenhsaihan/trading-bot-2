import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { useWebSocket, WebSocketStatus } from "./useWebSocket";

export interface PriceUpdate {
  type: "price_update";
  symbol: string;
  price: number;
  ticker: {
    last: number;
    bid: number;
    ask: number;
    volume: number;
    timestamp: number;
  };
  timestamp: string;
}

export interface OHLCVUpdate {
  type: "ohlcv_update";
  symbol: string;
  timeframe: string;
  candles: Array<{
    timestamp: number;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
  }>;
  timestamp: string;
}

export type MarketDataMessage = PriceUpdate | OHLCVUpdate;

export interface UseMarketDataStreamOptions {
  symbols?: string[];
  autoConnect?: boolean;
  onPriceUpdate?: (update: PriceUpdate) => void;
  onOHLCVUpdate?: (update: OHLCVUpdate) => void;
}

export interface UseMarketDataStreamReturn {
  status: WebSocketStatus;
  subscribe: (symbols: string | string[]) => void;
  unsubscribe: (symbols: string | string[]) => void;
  latestPrice: Record<string, number>;
  latestTicker: Record<string, PriceUpdate["ticker"]>;
  latestOHLCV: Record<string, OHLCVUpdate["candles"]>;
  subscriptions: string[];
  connect: () => void;
  disconnect: () => void;
}

/**
 * Hook for streaming market data (prices, OHLCV) via WebSocket
 */
export function useMarketDataStream(
  options: UseMarketDataStreamOptions = {}
): UseMarketDataStreamReturn {
  const {
    symbols = [],
    autoConnect = true,
    onPriceUpdate,
    onOHLCVUpdate,
  } = options;

  const [latestPrice, setLatestPrice] = useState<Record<string, number>>({});
  const [latestTicker, setLatestTicker] = useState<
    Record<string, PriceUpdate["ticker"]>
  >({});
  const [latestOHLCV, setLatestOHLCV] = useState<
    Record<string, OHLCVUpdate["candles"]>
  >({});
  const [subscriptions, setSubscriptions] = useState<string[]>([]);

  // Use refs to avoid recreating callbacks
  const symbolsRef = useRef(symbols);
  const onPriceUpdateRef = useRef(onPriceUpdate);
  const onOHLCVUpdateRef = useRef(onOHLCVUpdate);
  const subscribeRef = useRef<((symbols: string | string[]) => void) | null>(null);

  // Update refs when they change
  useEffect(() => {
    symbolsRef.current = symbols;
    onPriceUpdateRef.current = onPriceUpdate;
    onOHLCVUpdateRef.current = onOHLCVUpdate;
  }, [symbols, onPriceUpdate, onOHLCVUpdate]);

  // Memoize the WebSocket URL to prevent unnecessary reconnections
  const wsUrl = useMemo(() => {
    return (import.meta as any).env?.VITE_WS_URL?.replace("http://", "ws://").replace("https://", "wss://") ||
      "ws://localhost:8000/ws/market-data";
  }, []); // Only calculate once

  // Memoize autoConnect to prevent unnecessary reconnections
  const autoConnectMemo = useMemo(() => autoConnect, [autoConnect]);

  const { status, send, connect, disconnect, lastMessage } = useWebSocket({
    url: wsUrl,
    autoConnect: autoConnectMemo,
    onMessage: (data: any) => {
      // Handle connection message
      if (data.type === "connected") {
        console.log("Market data stream connected:", data.message);
        // Subscribe to initial symbols if provided (using ref)
        if (symbolsRef.current.length > 0 && subscribeRef.current) {
          subscribeRef.current(symbolsRef.current);
        }
        return;
      }

      // Handle subscription confirmation
      if (data.type === "subscribed" || data.type === "subscriptions") {
        setSubscriptions(data.symbols || []);
        return;
      }

      // Handle price updates
      if (data.type === "price_update") {
        const update = data as PriceUpdate;
        setLatestPrice((prev) => ({
          ...prev,
          [update.symbol]: update.price,
        }));
        setLatestTicker((prev) => ({
          ...prev,
          [update.symbol]: update.ticker,
        }));
        // Use ref to avoid stale closure
        onPriceUpdateRef.current?.(update);
      }

      // Handle OHLCV updates
      if (data.type === "ohlcv_update") {
        const update = data as OHLCVUpdate;
        setLatestOHLCV((prev) => ({
          ...prev,
          [update.symbol]: update.candles,
        }));
        // Use ref to avoid stale closure
        onOHLCVUpdateRef.current?.(update);
      }
    },
    onConnect: () => {
      console.log("Market data WebSocket connected");
    },
    onDisconnect: () => {
      console.log("Market data WebSocket disconnected");
    },
  });

  const subscribe = useCallback(
    (symbolsToSubscribe: string | string[]) => {
      const symbolArray = Array.isArray(symbolsToSubscribe)
        ? symbolsToSubscribe
        : [symbolsToSubscribe];

      send({
        type: "subscribe",
        symbols: symbolArray,
      });
    },
    [send]
  );

  // Store subscribe function in ref so onMessage can use it
  useEffect(() => {
    subscribeRef.current = subscribe;
  }, [subscribe]);

  const unsubscribe = useCallback(
    (symbolsToUnsubscribe: string | string[]) => {
      const symbolArray = Array.isArray(symbolsToUnsubscribe)
        ? symbolsToUnsubscribe
        : [symbolsToUnsubscribe];

      send({
        type: "unsubscribe",
        symbols: symbolArray,
      });
    },
    [send]
  );

  // Subscribe to initial symbols when connected (using refs)
  useEffect(() => {
    if (status === "connected" && symbolsRef.current.length > 0) {
      subscribe(symbolsRef.current);
    }
  }, [status, subscribe]);

  // Cleanup subscriptions on unmount
  useEffect(() => {
    return () => {
      if (subscriptions.length > 0) {
        unsubscribe(subscriptions);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run on unmount

  return {
    status,
    subscribe,
    unsubscribe,
    latestPrice,
    latestTicker,
    latestOHLCV,
    subscriptions,
    connect,
    disconnect,
  };
}


