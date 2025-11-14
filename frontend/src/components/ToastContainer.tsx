import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ToastNotification } from "./ToastNotification";
import { Notification } from "../types/notification";
import { speakMessage } from "../utils/voice";

interface ToastContainerProps {
  notifications: Notification[];
  onDismiss: (id: string) => void;
  onNotificationClick?: (notification: Notification) => void;
  voiceEnabled?: boolean;
}

export function ToastContainer({
  notifications,
  onDismiss,
  onNotificationClick,
  voiceEnabled = true,
}: ToastContainerProps) {
  const [displayedIds, setDisplayedIds] = useState<Set<string>>(new Set());
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(() => {
    // Load previously dismissed IDs from localStorage
    const stored = localStorage.getItem("dismissedToastIds");
    return new Set(stored ? JSON.parse(stored) : []);
  });

  // Show new notifications as toasts
  useEffect(() => {
    console.log("ToastContainer: notifications changed", notifications.length);
    notifications.forEach((notification) => {
      // Only show unread, non-responded notifications that haven't been displayed
      if (
        !notification.read &&
        !notification.responded &&
        !displayedIds.has(notification.id) &&
        !dismissedIds.has(notification.id)
      ) {
        console.log(
          "Showing toast for notification:",
          notification.id,
          notification.title
        );
        setDisplayedIds((prev) => new Set([...prev, notification.id]));

        // Play voice alert
        // Use summarized_message if available (AI-generated concise version), otherwise fall back to message
        if (voiceEnabled) {
          const messageToSpeak = notification.summarized_message || notification.message;
          console.log("🎤 Speaking message:", {
            hasSummarized: !!notification.summarized_message,
            messageToSpeak,
            priority: notification.priority,
            notificationId: notification.id
          });
          speakMessage(messageToSpeak, notification.priority);
        } else {
          console.log("🔇 Voice disabled, skipping speech");
        }

        // Auto-dismiss after 5 seconds
        setTimeout(() => {
          handleDismiss(notification.id);
        }, 5000);
      }
    });
  }, [notifications, displayedIds, dismissedIds, voiceEnabled]);

  const handleDismiss = (id: string) => {
    setDismissedIds((prev) => {
      const updated = new Set([...prev, id]);
      // Also update localStorage
      localStorage.setItem(
        "dismissedToastIds",
        JSON.stringify(Array.from(updated))
      );
      return updated;
    });
    onDismiss(id);
  };

  // Filter notifications to show only those that should be displayed
  const toastsToShow = notifications.filter(
    (n) => displayedIds.has(n.id) && !dismissedIds.has(n.id)
  );

  return (
    <div
      className="fixed top-0 right-0 z-50 pointer-events-none"
      style={{ zIndex: 9999 }}
    >
      <AnimatePresence>
        {toastsToShow.map((notification, index) => (
          <motion.div
            key={notification.id}
            initial={{ x: 400, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 400, opacity: 0 }}
            transition={{
              type: "spring",
              damping: 25,
              stiffness: 200,
              delay: index * 0.1,
            }}
            className="pointer-events-auto"
            style={{
              position: "absolute",
              top: `${70 + index * 120}px`,
              right: "20px",
              width: "400px",
            }}
          >
            <ToastNotification
              notification={notification}
              onDismiss={() => {
                handleDismiss(notification.id);
              }}
              onClick={() => {
                // Handle click: select notification and analyze
                onNotificationClick?.(notification);
                // Dismiss toast after a short delay to allow the click to register
                setTimeout(() => {
                  handleDismiss(notification.id);
                }, 100);
              }}
            />
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
