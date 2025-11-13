/**
 * Singleton WebSocket manager to prevent connection leaks
 * Ensures only ONE connection per URL, shared across all components
 */

type WebSocketStatus = "connecting" | "connected" | "disconnected" | "error";

interface WebSocketCallbacks {
  onMessage?: (data: any) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
}

class WebSocketSingleton {
  private connections = new Map<string, WebSocket>();
  private callbacks = new Map<string, Set<WebSocketCallbacks>>();
  private statuses = new Map<string, WebSocketStatus>();
  private pingIntervals = new Map<string, ReturnType<typeof setInterval>>();

  connect(url: string, callbacks: WebSocketCallbacks = {}): WebSocket | null {
    // If connection exists and is open or connecting, reuse it
    const existing = this.connections.get(url);
    if (existing) {
      const state = existing.readyState;
      if (state === WebSocket.OPEN || state === WebSocket.CONNECTING) {
        console.log(`WebSocket: Reusing existing connection to ${url}`, state === WebSocket.OPEN ? "OPEN" : "CONNECTING");
        // Add callbacks to the set
        if (!this.callbacks.has(url)) {
          this.callbacks.set(url, new Set());
        }
        this.callbacks.get(url)!.add(callbacks);
        return existing;
      } else {
        // Connection is closed, remove it
        this.connections.delete(url);
        this.statuses.delete(url);
        const interval = this.pingIntervals.get(url);
        if (interval) {
          clearInterval(interval);
          this.pingIntervals.delete(url);
        }
      }
    }

    // Create new connection
    console.log(`WebSocket: Creating new connection to ${url}`);
    const ws = new WebSocket(url);
    this.connections.set(url, ws);
    this.statuses.set(url, "connecting");

    // Initialize callbacks set
    if (!this.callbacks.has(url)) {
      this.callbacks.set(url, new Set());
    }
    this.callbacks.get(url)!.add(callbacks);

    ws.onopen = () => {
      console.log(`WebSocket: Connected to ${url}`);
      this.statuses.set(url, "connected");
      
      // Notify all callbacks
      this.callbacks.get(url)?.forEach(cb => cb.onConnect?.());

      // Start ping interval
      const interval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send("ping");
        }
      }, 30000);
      this.pingIntervals.set(url, interval);
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
          data = event.data;
        }

        // Notify all callbacks
        this.callbacks.get(url)?.forEach(cb => cb.onMessage?.(data));
      } catch (err) {
        console.error("Error processing WebSocket message:", err);
      }
    };

    ws.onerror = (error) => {
      console.error(`WebSocket error for ${url}:`, error);
      this.statuses.set(url, "error");
      this.callbacks.get(url)?.forEach(cb => cb.onError?.(error));
    };

    ws.onclose = () => {
      console.log(`WebSocket: Disconnected from ${url}`);
      this.statuses.set(url, "disconnected");
      
      // Cleanup
      const interval = this.pingIntervals.get(url);
      if (interval) {
        clearInterval(interval);
        this.pingIntervals.delete(url);
      }
      
      // Notify all callbacks
      this.callbacks.get(url)?.forEach(cb => cb.onDisconnect?.());
      
      // Remove connection (but keep callbacks in case of reconnect)
      this.connections.delete(url);
    };

    return ws;
  }

  disconnect(url: string, callbacks: WebSocketCallbacks): void {
    // Remove callbacks
    const callbackSet = this.callbacks.get(url);
    if (callbackSet) {
      callbackSet.delete(callbacks);
      
      // If no more callbacks, close the connection
      if (callbackSet.size === 0) {
        const ws = this.connections.get(url);
        if (ws) {
          console.log(`WebSocket: Closing connection to ${url} (no more callbacks)`);
          ws.close();
          this.connections.delete(url);
          this.statuses.delete(url);
          const interval = this.pingIntervals.get(url);
          if (interval) {
            clearInterval(interval);
            this.pingIntervals.delete(url);
          }
        }
        this.callbacks.delete(url);
      }
    }
  }

  getStatus(url: string): WebSocketStatus {
    return this.statuses.get(url) || "disconnected";
  }

  getConnection(url: string): WebSocket | undefined {
    return this.connections.get(url);
  }
}

// Export singleton instance
export const websocketSingleton = new WebSocketSingleton();

