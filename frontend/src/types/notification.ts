export enum NotificationPriority {
  CRITICAL = 'critical',
  HIGH = 'high',
  MEDIUM = 'medium',
  LOW = 'low',
  INFO = 'info',
}

export enum NotificationType {
  COMBINED_SIGNAL = 'combined_signal',
  TECHNICAL_BREAKOUT = 'technical_breakout',
  SOCIAL_SURGE = 'social_surge',
  NEWS_EVENT = 'news_event',
  RISK_ALERT = 'risk_alert',
  SYSTEM_STATUS = 'system_status',
  TRADE_EXECUTED = 'trade_executed',
  USER_ACTION_REQUIRED = 'user_action_required',
}

export enum NotificationSource {
  TECHNICAL = 'technical',
  TWITTER = 'twitter',
  TELEGRAM = 'telegram',
  NEWS = 'news',
  REDDIT = 'reddit',
  DISCORD = 'discord',
  SYSTEM = 'system',
  COMBINED = 'combined',
}

export interface Notification {
  id: string;
  type: NotificationType;
  priority: NotificationPriority;
  title: string;
  message: string;
  source: NotificationSource;
  symbol?: string;
  confidence_score?: number;
  urgency_score?: number;
  promise_score?: number;
  metadata: Record<string, any>;
  actions: string[];
  created_at: string;
  expires_at?: string;
  read: boolean;
  responded: boolean;
  response_action?: string;
  response_at?: string;
}

