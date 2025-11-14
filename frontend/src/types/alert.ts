export type AlertType = "price" | "indicator";

export type PriceCondition = "above" | "below";

export type IndicatorCondition = "above" | "below" | "crosses_above" | "crosses_below";

export type IndicatorName = "RSI" | "MACD" | "MACD_crossover" | "MA_50" | "MA_200";

export interface Alert {
  id: string;
  symbol: string;
  alert_type: AlertType;
  
  // Price alert fields
  price_threshold?: number;
  price_condition?: PriceCondition;
  
  // Indicator alert fields
  indicator_name?: IndicatorName;
  indicator_condition?: IndicatorCondition;
  indicator_value?: number;
  
  // Status fields
  enabled: boolean;
  triggered: boolean;
  triggered_at?: string;
  description?: string;
  
  // Timestamps
  created_at: string;
  updated_at: string;
}

export interface AlertCreate {
  symbol: string;
  alert_type: AlertType;
  price_threshold?: number;
  price_condition?: PriceCondition;
  indicator_name?: IndicatorName;
  indicator_condition?: IndicatorCondition;
  indicator_value?: number;
  enabled?: boolean;
  description?: string;
}

export interface AlertUpdate {
  enabled?: boolean;
  price_threshold?: number;
  price_condition?: PriceCondition;
  indicator_value?: number;
  description?: string;
}

export interface AlertListResponse {
  alerts: Alert[];
  total: number;
  active: number;
  triggered: number;
}



