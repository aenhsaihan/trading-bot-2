import { Notification } from "../types/notification";

const API_BASE_URL =
  (import.meta as any).env?.VITE_API_URL || "http://localhost:8000";

export class NotificationAPI {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  async getNotifications(
    limit?: number,
    unreadOnly: boolean = false
  ): Promise<{
    notifications: Notification[];
    total: number;
    unread_count: number;
  }> {
    const params = new URLSearchParams();
    if (limit) params.append("limit", limit.toString());
    if (unreadOnly) params.append("unread_only", "true");

    const response = await fetch(`${this.baseUrl}/notifications?${params}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch notifications: ${response.statusText}`);
    }
    return response.json();
  }

  async getNotification(id: string): Promise<Notification> {
    const response = await fetch(`${this.baseUrl}/notifications/${id}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch notification: ${response.statusText}`);
    }
    return response.json();
  }

  async createNotification(data: {
    type: string;
    priority: string;
    title: string;
    message: string;
    source: string;
    symbol?: string;
    confidence_score?: number;
    urgency_score?: number;
    promise_score?: number;
    metadata?: Record<string, any>;
    actions?: string[];
  }): Promise<Notification> {
    const response = await fetch(`${this.baseUrl}/notifications`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      throw new Error(`Failed to create notification: ${response.statusText}`);
    }
    return response.json();
  }

  async markAsRead(id: string): Promise<Notification> {
    const response = await fetch(`${this.baseUrl}/notifications/${id}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ read: true }),
    });
    if (!response.ok) {
      throw new Error(`Failed to mark as read: ${response.statusText}`);
    }
    return response.json();
  }

  async respondToNotification(
    id: string,
    action: string,
    customMessage?: string
  ): Promise<Notification> {
    const params = new URLSearchParams({ action });
    if (customMessage) params.append("custom_message", customMessage);

    const response = await fetch(
      `${this.baseUrl}/notifications/${id}/respond?${params}`,
      {
        method: "POST",
      }
    );
    if (!response.ok) {
      throw new Error(`Failed to respond: ${response.statusText}`);
    }
    return response.json();
  }

  async deleteNotification(id: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/notifications/${id}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      throw new Error(`Failed to delete notification: ${response.statusText}`);
    }
  }

  async getStats(): Promise<Record<string, any>> {
    const response = await fetch(`${this.baseUrl}/notifications/stats/summary`);
    if (!response.ok) {
      throw new Error(`Failed to fetch stats: ${response.statusText}`);
    }
    return response.json();
  }

  async healthCheck(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/health`);
      return response.ok;
    } catch {
      return false;
    }
  }
}

export const notificationAPI = new NotificationAPI();

// Trading API
export interface Position {
  id: string;
  symbol: string;
  side: "long" | "short";
  amount: number;
  entry_price: number;
  current_price: number;
  pnl: number;
  pnl_percent: number;
  stop_loss?: number; // Stop loss price
  stop_loss_percent?: number; // Stop loss percentage
  trailing_stop?: number; // Trailing stop percentage
  entry_time: string;
  created_at: string;
}

export interface Balance {
  balance: number;
  currency: string;
  total_value: number;
  total_pnl: number;
  total_pnl_percent: number;
}

export interface PositionList {
  positions: Position[];
  total: number;
  total_pnl: number;
  total_pnl_percent: number;
}

export class TradingAPI {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  async getBalance(): Promise<Balance> {
    const response = await fetch(`${this.baseUrl}/trading/balance`);
    if (!response.ok) {
      throw new Error(`Failed to fetch balance: ${response.statusText}`);
    }
    return response.json();
  }

  async getPositions(): Promise<PositionList> {
    const response = await fetch(`${this.baseUrl}/trading/positions`);
    if (!response.ok) {
      throw new Error(`Failed to fetch positions: ${response.statusText}`);
    }
    return response.json();
  }

  async getPosition(positionId: string): Promise<Position> {
    // URL encode the position ID to handle special characters like '/' in symbols
    const encodedPositionId = encodeURIComponent(positionId);
    const response = await fetch(
      `${this.baseUrl}/trading/positions/${encodedPositionId}`
    );
    if (!response.ok) {
      throw new Error(`Failed to fetch position: ${response.statusText}`);
    }
    return response.json();
  }

  async openPosition(data: {
    symbol: string;
    side: "long" | "short";
    amount: number;
    stop_loss_percent?: number;
    trailing_stop_percent?: number;
  }): Promise<Position> {
    const response = await fetch(`${this.baseUrl}/trading/positions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      // Try to get detailed error message from response
      let errorMessage = response.statusText;
      try {
        const errorData = await response.json();
        if (errorData.detail) {
          if (Array.isArray(errorData.detail)) {
            errorMessage = errorData.detail
              .map((e: any) => `${e.field}: ${e.message}`)
              .join(", ");
          } else {
            errorMessage = errorData.detail;
          }
        }
      } catch {
        // If we can't parse the error, use statusText
      }
      throw new Error(`Failed to open position: ${errorMessage}`);
    }
    return response.json();
  }

  async closePosition(positionId: string): Promise<void> {
    // URL encode the position ID to handle special characters like '/' in symbols
    const encodedPositionId = encodeURIComponent(positionId);
    const response = await fetch(
      `${this.baseUrl}/trading/positions/${encodedPositionId}`,
      {
        method: "DELETE",
      }
    );
    if (!response.ok) {
      // Try to get detailed error message from response
      let errorMessage = response.statusText;
      try {
        const errorData = await response.json();
        if (errorData.detail) {
          errorMessage = errorData.detail;
        }
      } catch {
        // If we can't parse the error, use statusText
      }
      throw new Error(`Failed to close position: ${errorMessage}`);
    }
  }

  async setStopLoss(
    positionId: string,
    stopLossPercent: number
  ): Promise<Position> {
    // URL encode the position ID to handle special characters like '/' in symbols
    const encodedPositionId = encodeURIComponent(positionId);
    const response = await fetch(
      `${this.baseUrl}/trading/positions/${encodedPositionId}/stop-loss`,
      {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ stop_loss_percent: stopLossPercent }),
      }
    );
    if (!response.ok) {
      let errorMessage = response.statusText;
      try {
        const errorData = await response.json();
        if (errorData.detail) {
          errorMessage = errorData.detail;
        }
      } catch {
        // If we can't parse the error, use statusText
      }
      throw new Error(`Failed to set stop loss: ${errorMessage}`);
    }
    return response.json();
  }

  async setTrailingStop(
    positionId: string,
    trailingStopPercent: number
  ): Promise<Position> {
    // URL encode the position ID to handle special characters like '/' in symbols
    const encodedPositionId = encodeURIComponent(positionId);
    const response = await fetch(
      `${this.baseUrl}/trading/positions/${encodedPositionId}/trailing-stop`,
      {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ trailing_stop_percent: trailingStopPercent }),
      }
    );
    if (!response.ok) {
      let errorMessage = response.statusText;
      try {
        const errorData = await response.json();
        if (errorData.detail) {
          errorMessage = errorData.detail;
        }
      } catch {
        // If we can't parse the error, use statusText
      }
      throw new Error(`Failed to set trailing stop: ${errorMessage}`);
    }
    return response.json();
  }
}

export const tradingAPI = new TradingAPI();

// AI API
export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

export interface ChatContext {
  positions?: any[];
  balance?: number;
  selected_notification?: any;
}

export class AIAPI {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  async getStatus(): Promise<{ enabled: boolean; available: boolean }> {
    const response = await fetch(`${this.baseUrl}/ai/status`);
    if (!response.ok) {
      throw new Error(`Failed to fetch AI status: ${response.statusText}`);
    }
    return response.json();
  }

  async chat(
    message: string,
    conversationHistory: ChatMessage[] = [],
    context?: ChatContext
  ): Promise<string> {
    const response = await fetch(`${this.baseUrl}/ai/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message,
        conversation_history: conversationHistory,
        context,
      }),
    });
    if (!response.ok) {
      throw new Error(`Failed to chat: ${response.statusText}`);
    }
    const data = await response.json();
    return data.response;
  }

  async analyzeNotification(
    notification: any,
    context?: ChatContext
  ): Promise<string> {
    const response = await fetch(`${this.baseUrl}/ai/analyze-notification`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        notification,
        context,
      }),
    });
    if (!response.ok) {
      throw new Error(`Failed to analyze notification: ${response.statusText}`);
    }
    const data = await response.json();
    return data.analysis;
  }
}

export const aiAPI = new AIAPI();

// Voice TTS API
export class VoiceAPI {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  async synthesize(
    text: string,
    priority: string = "medium",
    voiceId?: string,
    provider?: string
  ): Promise<{ audio_base64: string; provider_used: string; format: string }> {
    // Build request body with optional provider
    const body: any = {
      text,
      priority,
    };
    if (voiceId) body.voice_id = voiceId;
    if (provider) body.provider = provider; // Allow forcing a provider for testing
    const response = await fetch(`${this.baseUrl}/voice/synthesize`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        text,
        priority,
        voice_id: voiceId,
        provider,
      }),
    });

    if (!response.ok) {
      throw new Error(`Voice synthesis failed: ${response.statusText}`);
    }

    return response.json();
  }

  async getAvailableProviders(): Promise<{
    providers: Record<string, boolean>;
    default_order: string[];
  }> {
    const response = await fetch(`${this.baseUrl}/voice/providers`);
    if (!response.ok) {
      throw new Error(`Failed to fetch providers: ${response.statusText}`);
    }
    return response.json();
  }
}

export const voiceAPI = new VoiceAPI();

// Market Data API
export interface TickerData {
  symbol: string;
  last: number;
  bid: number;
  ask: number;
  volume: number;
  timestamp: number;
}

export interface Candle {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface OHLCVData {
  symbol: string;
  timeframe: string;
  candles: Candle[];
}

export class MarketDataAPI {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  async getPrice(symbol: string): Promise<{ symbol: string; price: number }> {
    const response = await fetch(
      `${this.baseUrl}/market-data/price/${encodeURIComponent(symbol)}`
    );
    if (!response.ok) {
      throw new Error(`Failed to fetch price: ${response.statusText}`);
    }
    return response.json();
  }

  async getPrices(
    symbols: string[]
  ): Promise<{ prices: Record<string, number | null> }> {
    const response = await fetch(`${this.baseUrl}/market-data/prices`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(symbols),
    });
    if (!response.ok) {
      throw new Error(`Failed to fetch prices: ${response.statusText}`);
    }
    return response.json();
  }

  async getTicker(symbol: string): Promise<TickerData> {
    const response = await fetch(
      `${this.baseUrl}/market-data/ticker/${encodeURIComponent(symbol)}`
    );
    if (!response.ok) {
      throw new Error(`Failed to fetch ticker: ${response.statusText}`);
    }
    return response.json();
  }

  async getOHLCV(
    symbol: string,
    timeframe: string = "1h",
    limit: number = 100
  ): Promise<OHLCVData> {
    const params = new URLSearchParams({
      timeframe,
      limit: limit.toString(),
    });
    const response = await fetch(
      `${this.baseUrl}/market-data/ohlcv/${encodeURIComponent(
        symbol
      )}?${params}`
    );
    if (!response.ok) {
      throw new Error(`Failed to fetch OHLCV data: ${response.statusText}`);
    }
    return response.json();
  }
}

export const marketDataAPI = new MarketDataAPI();

// Alert API
import { Alert, AlertCreate, AlertUpdate, AlertListResponse } from "../types/alert";

export class AlertAPI {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  async getAlerts(
    symbol?: string,
    enabledOnly: boolean = false,
    triggeredOnly: boolean = false
  ): Promise<AlertListResponse> {
    const params = new URLSearchParams();
    if (symbol) params.append("symbol", symbol);
    if (enabledOnly) params.append("enabled_only", "true");
    if (triggeredOnly) params.append("triggered_only", "true");

    const response = await fetch(`${this.baseUrl}/alerts?${params}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch alerts: ${response.statusText}`);
    }
    return response.json();
  }

  async getAlert(id: string): Promise<Alert> {
    const response = await fetch(`${this.baseUrl}/alerts/${id}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch alert: ${response.statusText}`);
    }
    return response.json();
  }

  async createAlert(data: AlertCreate): Promise<Alert> {
    const response = await fetch(`${this.baseUrl}/alerts`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      let errorMessage = response.statusText;
      try {
        const errorData = await response.json();
        if (errorData.detail) {
          if (Array.isArray(errorData.detail)) {
            errorMessage = errorData.detail
              .map((e: any) => `${e.field}: ${e.message}`)
              .join(", ");
          } else {
            errorMessage = errorData.detail;
          }
        }
      } catch {
        // If we can't parse the error, use statusText
      }
      throw new Error(`Failed to create alert: ${errorMessage}`);
    }
    return response.json();
  }

  async updateAlert(id: string, data: AlertUpdate): Promise<Alert> {
    const response = await fetch(`${this.baseUrl}/alerts/${id}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      let errorMessage = response.statusText;
      try {
        const errorData = await response.json();
        if (errorData.detail) {
          errorMessage = errorData.detail;
        }
      } catch {
        // If we can't parse the error, use statusText
      }
      throw new Error(`Failed to update alert: ${errorMessage}`);
    }
    return response.json();
  }

  async deleteAlert(id: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/alerts/${id}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      throw new Error(`Failed to delete alert: ${response.statusText}`);
    }
  }

  async evaluateAlerts(): Promise<{
    evaluated: boolean;
    triggered_count: number;
    triggered_alerts: Alert[];
  }> {
    const response = await fetch(`${this.baseUrl}/alerts/evaluate`, {
      method: "POST",
    });
    if (!response.ok) {
      throw new Error(`Failed to evaluate alerts: ${response.statusText}`);
    }
    return response.json();
  }
}

export const alertAPI = new AlertAPI();

// System API
export class SystemAPI {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  async getNotificationSourcesStatus(): Promise<{
    running: boolean;
    symbols: string[];
    timeframe: string;
    check_interval: number;
    stats: any;
  }> {
    const response = await fetch(`${this.baseUrl}/system/notification-sources/status`);
    if (!response.ok) {
      throw new Error(`Failed to get notification sources status: ${response.statusText}`);
    }
    return response.json();
  }

  async startNotificationSources(): Promise<{ message: string; running: boolean }> {
    const response = await fetch(`${this.baseUrl}/system/notification-sources/start`, {
      method: "POST",
    });
    if (!response.ok) {
      throw new Error(`Failed to start notification sources: ${response.statusText}`);
    }
    return response.json();
  }

  async stopNotificationSources(): Promise<{ message: string; running: boolean }> {
    const response = await fetch(`${this.baseUrl}/system/notification-sources/stop`, {
      method: "POST",
    });
    if (!response.ok) {
      throw new Error(`Failed to stop notification sources: ${response.statusText}`);
    }
    return response.json();
  }
}

export const systemAPI = new SystemAPI();

// Price Update WebSocket (for real-time position updates)
// The usePriceUpdates hook handles WebSocket connections
// This is just for reference/documentation
