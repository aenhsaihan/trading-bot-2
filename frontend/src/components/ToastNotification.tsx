import { motion, AnimatePresence } from "framer-motion";
import {
  Notification,
  NotificationPriority,
  NotificationType,
} from "../types/notification";
import { X } from "lucide-react";

interface ToastNotificationProps {
  notification: Notification;
  onDismiss: () => void;
  onClick?: () => void;
  duration?: number;
}

const priorityEmojis: Record<NotificationPriority, string> = {
  [NotificationPriority.CRITICAL]: "🔴",
  [NotificationPriority.HIGH]: "🟠",
  [NotificationPriority.MEDIUM]: "🟡",
  [NotificationPriority.LOW]: "🔵",
  [NotificationPriority.INFO]: "⚪",
};

const typeEmojis: Record<NotificationType, string> = {
  [NotificationType.COMBINED_SIGNAL]: "🚀",
  [NotificationType.TECHNICAL_BREAKOUT]: "📈",
  [NotificationType.SOCIAL_SURGE]: "💬",
  [NotificationType.NEWS_EVENT]: "📰",
  [NotificationType.RISK_ALERT]: "⚠️",
  [NotificationType.SYSTEM_STATUS]: "✅",
  [NotificationType.TRADE_EXECUTED]: "💰",
  [NotificationType.USER_ACTION_REQUIRED]: "👤",
};

const priorityColors: Record<NotificationPriority, string> = {
  [NotificationPriority.CRITICAL]: "#FF4444",
  [NotificationPriority.HIGH]: "#FF8800",
  [NotificationPriority.MEDIUM]: "#FFBB00",
  [NotificationPriority.LOW]: "#4488FF",
  [NotificationPriority.INFO]: "#888888",
};

export function ToastNotification({
  notification,
  onDismiss,
  onClick,
  duration: _duration = 5000, // Reserved for future use
}: ToastNotificationProps) {
  const priorityEmoji = priorityEmojis[notification.priority];
  const typeEmoji = typeEmojis[notification.type];
  const priorityColor = priorityColors[notification.priority];

  return (
    <AnimatePresence>
      <motion.div
        initial={{ x: 400, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        exit={{ x: 400, opacity: 0 }}
        transition={{ type: "spring", damping: 25, stiffness: 200 }}
        className="max-w-md w-full"
      >
        <div
          className="bg-gradient-to-br from-dark-card to-dark-bg rounded-xl shadow-2xl border-l-4 p-4 cursor-pointer hover:shadow-3xl transition-all duration-200 hover:-translate-y-1"
          style={{ borderLeftColor: priorityColor }}
          onClick={() => {
            onClick?.(); // Handle click (select notification and analyze)
            // Don't dismiss immediately - let the onClick handler manage dismissal
          }}
        >
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3 flex-1">
              <div className="text-2xl">{priorityEmoji}</div>
              <div className="text-xl">{typeEmoji}</div>
              <div className="flex-1 min-w-0">
                <div className="font-bold text-white text-lg mb-1">
                  {notification.title}
                </div>
                <div className="text-gray-300 text-sm mb-2">
                  {notification.message}
                </div>
                <div className="flex gap-4 text-xs text-gray-500 flex-wrap">
                  {notification.symbol && (
                    <span>
                      <strong>Symbol:</strong>{" "}
                      <span className="text-green-400">
                        {notification.symbol}
                      </span>
                    </span>
                  )}
                  {notification.confidence_score !== undefined && (
                    <span>
                      <strong>Confidence:</strong>{" "}
                      <span
                        className={
                          notification.confidence_score >= 75
                            ? "text-green-400"
                            : notification.confidence_score >= 50
                            ? "text-yellow-400"
                            : "text-red-400"
                        }
                      >
                        {notification.confidence_score}%
                      </span>
                    </span>
                  )}
                </div>
              </div>
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDismiss();
              }}
              className="text-gray-400 hover:text-white transition-colors p-1 rounded-full hover:bg-white/10 flex-shrink-0"
              aria-label="Dismiss"
            >
              <X size={20} />
            </button>
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
