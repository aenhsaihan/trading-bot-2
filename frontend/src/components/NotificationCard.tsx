import { Notification, NotificationPriority, NotificationType } from '../types/notification';
import { Check, Clock } from 'lucide-react';

interface NotificationCardProps {
  notification: Notification;
  onMarkRead: (id: string) => void;
  onRespond: (id: string, action: string) => void;
  onSelect?: (notification: Notification) => void;
  isSelected?: boolean;
}

const priorityEmojis: Record<NotificationPriority, string> = {
  [NotificationPriority.CRITICAL]: '🔴',
  [NotificationPriority.HIGH]: '🟠',
  [NotificationPriority.MEDIUM]: '🟡',
  [NotificationPriority.LOW]: '🔵',
  [NotificationPriority.INFO]: '⚪',
};

const typeEmojis: Record<NotificationType, string> = {
  [NotificationType.COMBINED_SIGNAL]: '🚀',
  [NotificationType.TECHNICAL_BREAKOUT]: '📈',
  [NotificationType.SOCIAL_SURGE]: '💬',
  [NotificationType.NEWS_EVENT]: '📰',
  [NotificationType.RISK_ALERT]: '⚠️',
  [NotificationType.SYSTEM_STATUS]: '✅',
  [NotificationType.TRADE_EXECUTED]: '💰',
  [NotificationType.USER_ACTION_REQUIRED]: '👤',
};

const priorityColors: Record<NotificationPriority, string> = {
  [NotificationPriority.CRITICAL]: '#FF4444',
  [NotificationPriority.HIGH]: '#FF8800',
  [NotificationPriority.MEDIUM]: '#FFBB00',
  [NotificationPriority.LOW]: '#4488FF',
  [NotificationPriority.INFO]: '#888888',
};

function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
}

export function NotificationCard({
  notification,
  onMarkRead,
  onRespond,
  onSelect,
  isSelected = false,
}: NotificationCardProps) {
  const priorityEmoji = priorityEmojis[notification.priority];
  const typeEmoji = typeEmojis[notification.type];
  const priorityColor = priorityColors[notification.priority];

  return (
    <div
      className={`bg-gradient-to-br from-dark-card to-dark-bg rounded-xl p-4 mb-4 border-l-4 shadow-lg hover:shadow-xl transition-all duration-200 cursor-pointer ${
        isSelected ? 'ring-2 ring-blue-500' : ''
      } ${notification.read ? 'opacity-75' : ''}`}
      style={{ borderLeftColor: priorityColor }}
      onClick={() => onSelect?.(notification)}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{priorityEmoji}</span>
          <span className="text-xl">{typeEmoji}</span>
          <h3 className="font-bold text-white text-lg">{notification.title}</h3>
        </div>
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <Clock size={12} />
          {formatTimeAgo(notification.created_at)}
        </div>
      </div>

      <p className="text-gray-300 text-sm mb-3">{notification.message}</p>

      <div className="flex gap-4 text-xs text-gray-500 mb-3 flex-wrap">
        {notification.symbol && (
          <span>
            <strong>Symbol:</strong>{' '}
            <span className="text-green-400">{notification.symbol}</span>
          </span>
        )}
        {notification.confidence_score !== undefined && (
          <span>
            <strong>Confidence:</strong>{' '}
            <span
              className={
                notification.confidence_score >= 75
                  ? 'text-green-400'
                  : notification.confidence_score >= 50
                  ? 'text-yellow-400'
                  : 'text-red-400'
              }
            >
              {notification.confidence_score}%
            </span>
          </span>
        )}
        {notification.urgency_score !== undefined && (
          <span>
            <strong>Urgency:</strong>{' '}
            <span className="text-orange-400">{notification.urgency_score}%</span>
          </span>
        )}
        {notification.promise_score !== undefined && (
          <span>
            <strong>Promise:</strong>{' '}
            <span className="text-green-400">{notification.promise_score}%</span>
          </span>
        )}
      </div>

      {notification.actions.length > 0 && !notification.responded && (
        <div className="flex gap-2 mt-3" onClick={(e) => e.stopPropagation()}>
          {notification.actions.map((action) => (
            <button
              key={action}
              onClick={() => onRespond(notification.id, action.toLowerCase())}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                action.toLowerCase() === 'approve' || action.toLowerCase() === 'buy'
                  ? 'bg-green-600 hover:bg-green-700 text-white'
                  : action.toLowerCase() === 'reject'
                  ? 'bg-red-600 hover:bg-red-700 text-white'
                  : 'bg-gray-700 hover:bg-gray-600 text-white'
              }`}
            >
              {action}
            </button>
          ))}
        </div>
      )}

      {notification.responded && (
        <div className="mt-3 text-sm text-gray-400">
          ✓ Responded: {notification.response_action}
        </div>
      )}

      {!notification.read && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onMarkRead(notification.id);
          }}
          className="mt-2 text-xs text-gray-500 hover:text-gray-300 flex items-center gap-1"
        >
          <Check size={12} />
          Mark as read
        </button>
      )}
    </div>
  );
}

