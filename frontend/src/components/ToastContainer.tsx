import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ToastNotification } from './ToastNotification';
import { Notification } from '../types/notification';
import { speakMessage } from '../utils/voice';

interface ToastContainerProps {
  notifications: Notification[];
  onDismiss: (id: string) => void;
  voiceEnabled?: boolean;
}

export function ToastContainer({
  notifications,
  onDismiss,
  voiceEnabled = true,
}: ToastContainerProps) {
  const [displayedIds, setDisplayedIds] = useState<Set<string>>(new Set());
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(new Set());

  // Show new notifications as toasts
  useEffect(() => {
    notifications.forEach((notification) => {
      // Only show unread, non-responded notifications that haven't been displayed
      if (
        !notification.read &&
        !notification.responded &&
        !displayedIds.has(notification.id) &&
        !dismissedIds.has(notification.id)
      ) {
        setDisplayedIds((prev) => new Set([...prev, notification.id]));

        // Play voice alert
        if (voiceEnabled) {
          speakMessage(notification.message, notification.priority);
        }

        // Auto-dismiss after 5 seconds
        setTimeout(() => {
          handleDismiss(notification.id);
        }, 5000);
      }
    });
  }, [notifications, displayedIds, dismissedIds, voiceEnabled]);

  const handleDismiss = (id: string) => {
    setDismissedIds((prev) => new Set([...prev, id]));
    onDismiss(id);
  };

  // Filter notifications to show only those that should be displayed
  const toastsToShow = notifications.filter(
    (n) => displayedIds.has(n.id) && !dismissedIds.has(n.id)
  );

  return (
    <div className="fixed top-0 right-0 z-50 pointer-events-none" style={{ zIndex: 9999 }}>
      <AnimatePresence>
        {toastsToShow.map((notification, index) => (
          <motion.div
            key={notification.id}
            initial={{ x: 400, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 400, opacity: 0 }}
            transition={{
              type: 'spring',
              damping: 25,
              stiffness: 200,
              delay: index * 0.1,
            }}
            className="pointer-events-auto"
            style={{
              position: 'absolute',
              top: `${70 + index * 120}px`,
              right: '20px',
              width: '400px',
            }}
          >
            <ToastNotification
              notification={notification}
              onDismiss={() => handleDismiss(notification.id)}
            />
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}

