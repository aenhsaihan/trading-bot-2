import { useEffect, useState, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ToastNotification } from "./ToastNotification";
import { Notification } from "../types/notification";
import { speakMessage, getIsSpeaking } from "../utils/voice";

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
  // Queue of notifications waiting to be shown
  const [toastQueue, setToastQueue] = useState<Notification[]>([]);
  
  // Currently displayed toast (only one at a time)
  const [currentToast, setCurrentToast] = useState<Notification | null>(null);
  
  // Track which notifications have been processed
  const [processedIds, setProcessedIds] = useState<Set<string>>(new Set());
  
  // Track dismissed IDs (to avoid re-showing)
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(() => {
    const stored = localStorage.getItem("dismissedToastIds");
    return new Set(stored ? JSON.parse(stored) : []);
  });
  
  // Track if voice is speaking (polling)
  const voiceCheckIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const [isVoiceSpeaking, setIsVoiceSpeaking] = useState(false);
  
  // Ref to store auto-dismiss timer (so it persists across re-renders)
  const autoDismissTimerRef = useRef<NodeJS.Timeout | null>(null);
  // Ref to track which toast the timer is for (to prevent clearing wrong timer)
  const timerToastIdRef = useRef<string | null>(null);
  
  // Rate limiting: track last notification time and cooldown
  const lastNotificationTimeRef = useRef<number>(0);
  const cooldownTimerRef = useRef<NodeJS.Timeout | null>(null);
  const [cooldownTrigger, setCooldownTrigger] = useState(0); // Trigger to re-run effect after cooldown
  
  // Cooldown durations (in milliseconds) based on priority
  const COOLDOWN_DURATIONS = {
    critical: 0,      // No cooldown - can show immediately
    high: 3000,       // 3 seconds between high priority
    medium: 5000,     // 5 seconds between medium priority
    low: 8000,        // 8 seconds between low priority
    info: 10000,      // 10 seconds between info notifications
  };

  // Define handleDismiss before useEffects that use it
  const handleDismiss = useCallback((id: string) => {
    console.log("ToastContainer: Dismissing toast:", id);
    
    // Clear auto-dismiss timer if this toast is being dismissed
    if (autoDismissTimerRef.current && timerToastIdRef.current === id) {
      clearTimeout(autoDismissTimerRef.current);
      autoDismissTimerRef.current = null;
      timerToastIdRef.current = null;
    }
    
    // Add to dismissed IDs
    setDismissedIds((prev) => {
      const updated = new Set([...prev, id]);
      localStorage.setItem(
        "dismissedToastIds",
        JSON.stringify(Array.from(updated))
      );
      return updated;
    });
    
    // Clear current toast (this will trigger next toast to show)
    setCurrentToast((prev) => {
      if (prev?.id === id) {
        return null;
      }
      return prev;
    });
    
    // Call parent dismiss handler
    onDismiss(id);
  }, [onDismiss]);

  // Poll voice speaking status more frequently for better synchronization
  useEffect(() => {
    voiceCheckIntervalRef.current = setInterval(() => {
      const speaking = getIsSpeaking();
      setIsVoiceSpeaking(speaking);
    }, 50); // Check every 50ms for better responsiveness

    return () => {
      if (voiceCheckIntervalRef.current) {
        clearInterval(voiceCheckIntervalRef.current);
      }
    };
  }, []);

  // Process new notifications - add to queue
  useEffect(() => {
    const newNotifications = notifications.filter(
      (notification) =>
        !notification.read &&
        !notification.responded &&
        !processedIds.has(notification.id) &&
        !dismissedIds.has(notification.id)
    );

    if (newNotifications.length > 0) {
      console.log("ToastContainer: New notifications to queue:", newNotifications.length);
      
      // Mark as processed
      setProcessedIds((prev) => {
        const updated = new Set(prev);
        newNotifications.forEach((n) => updated.add(n.id));
        return updated;
      });

      // Sort notifications by priority (critical first, then by timestamp)
      const priorityOrder = { critical: 0, high: 1, medium: 2, low: 3, info: 4 };
      const sortedNotifications = [...newNotifications].sort((a, b) => {
        const priorityDiff = (priorityOrder[a.priority as keyof typeof priorityOrder] || 99) - 
                            (priorityOrder[b.priority as keyof typeof priorityOrder] || 99);
        if (priorityDiff !== 0) return priorityDiff;
        // If same priority, older notifications first
        return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
      });
      
      // Add to queue (maintaining priority order)
      setToastQueue((prev) => {
        const combined = [...prev, ...sortedNotifications];
        // Re-sort the entire queue to maintain priority order
        return combined.sort((a, b) => {
          const priorityDiff = (priorityOrder[a.priority as keyof typeof priorityOrder] || 99) - 
                              (priorityOrder[b.priority as keyof typeof priorityOrder] || 99);
          if (priorityDiff !== 0) return priorityDiff;
          return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
        });
      });
    }
  }, [notifications, processedIds, dismissedIds]);

  // Process queue - show next toast when current is dismissed and voice is not speaking
  useEffect(() => {
    // Don't show new toast if queue is empty
    if (toastQueue.length === 0) {
      return;
    }
    
    // Get next toast from queue (already sorted by priority)
    const nextToast = toastQueue[0];
    const isCritical = nextToast.priority === 'critical';
    const currentIsCritical = currentToast?.priority === 'critical';
    
    // Critical notifications can interrupt non-critical toasts
    if (currentToast) {
      if (isCritical && !currentIsCritical) {
        // Critical notification interrupting non-critical - dismiss current toast
        console.log("🚨 Critical notification interrupting non-critical toast");
        handleDismiss(currentToast.id);
        // Will re-run after currentToast is cleared
        return;
      } else {
        // Normal case: wait for current toast to be dismissed
        return;
      }
    }

    // Double-check voice status right before showing (in case polling is slightly behind)
    // Critical notifications can interrupt even if voice is speaking (but we still wait for voice to finish)
    const actuallySpeaking = getIsSpeaking();
    if (actuallySpeaking || isVoiceSpeaking) {
      if (toastQueue.length > 0) {
        console.log("ToastContainer: Waiting for voice to finish before showing next toast", {
          isVoiceSpeaking,
          actuallySpeaking,
          nextPriority: nextToast.priority,
          isCritical
        });
      }
      return;
    }
    
    // Check cooldown (critical notifications skip cooldown)
    const now = Date.now();
    const timeSinceLastNotification = now - lastNotificationTimeRef.current;
    const cooldownDuration = COOLDOWN_DURATIONS[nextToast.priority as keyof typeof COOLDOWN_DURATIONS] || COOLDOWN_DURATIONS.info;
    const isInCooldown = !isCritical && timeSinceLastNotification < cooldownDuration;
    
    if (isInCooldown) {
      const remainingCooldown = cooldownDuration - timeSinceLastNotification;
      console.log(`⏳ Notification cooldown active: ${remainingCooldown}ms remaining for ${nextToast.priority} priority`);
      
      // Set a timer to retry after cooldown
      if (cooldownTimerRef.current) {
        clearTimeout(cooldownTimerRef.current);
      }
      cooldownTimerRef.current = setTimeout(() => {
        cooldownTimerRef.current = null;
        // Trigger re-evaluation by updating state
        setCooldownTrigger(Date.now());
      }, remainingCooldown);
      
      return;
    }
    
    // Clear any existing cooldown timer
    if (cooldownTimerRef.current) {
      clearTimeout(cooldownTimerRef.current);
      cooldownTimerRef.current = null;
    }
    
    console.log("ToastContainer: Showing next toast from queue:", {
      id: nextToast.id,
      priority: nextToast.priority,
      timeSinceLast: timeSinceLastNotification,
      skippedCooldown: isCritical
    });
    
    setCurrentToast(nextToast);
    setToastQueue((prev) => prev.slice(1)); // Remove from queue
    
    // Update last notification time for rate limiting
    lastNotificationTimeRef.current = now;

    // Play voice alert when toast appears (not before)
    if (voiceEnabled) {
      // Prefer summarized_message, but only if it exists and is not empty
      // If no summary, use title (which is usually concise) instead of long message
      let messageToSpeak: string;
      if (nextToast.summarized_message && nextToast.summarized_message.trim().length > 0) {
        messageToSpeak = nextToast.summarized_message;
      } else {
        // Fallback to title (usually short and sweet) instead of long message
        messageToSpeak = nextToast.title;
      }
      
      console.log("🎤 Speaking message when toast appears:", {
        hasSummarized: !!(nextToast.summarized_message && nextToast.summarized_message.trim().length > 0),
        usingTitle: messageToSpeak === nextToast.title,
        messageToSpeak,
        priority: nextToast.priority,
        notificationId: nextToast.id
      });
      speakMessage(messageToSpeak, nextToast.priority);
    } else {
      console.log("🔇 Voice disabled, skipping speech");
    }
  }, [currentToast, isVoiceSpeaking, toastQueue, voiceEnabled, handleDismiss, cooldownTrigger]);

  // Separate effect to set up auto-dismiss timer when a toast is shown
  // This effect only depends on currentToast, so it won't re-run when isVoiceSpeaking changes
  useEffect(() => {
    if (!currentToast) {
      // No toast showing, clear any existing timer
      if (autoDismissTimerRef.current) {
        clearTimeout(autoDismissTimerRef.current);
        autoDismissTimerRef.current = null;
        timerToastIdRef.current = null;
      }
      return;
    }

    // Clear any existing auto-dismiss timer (only if it's for a different toast)
    if (autoDismissTimerRef.current && timerToastIdRef.current !== currentToast.id) {
      console.log("ToastContainer: Clearing timer for previous toast:", timerToastIdRef.current);
      clearTimeout(autoDismissTimerRef.current);
      autoDismissTimerRef.current = null;
      timerToastIdRef.current = null;
    }

    // Only set timer if we don't already have one for this toast
    if (!autoDismissTimerRef.current || timerToastIdRef.current !== currentToast.id) {
      console.log("ToastContainer: Setting auto-dismiss timer for toast:", currentToast.id);
      // Auto-dismiss after 5 seconds
      timerToastIdRef.current = currentToast.id;
      autoDismissTimerRef.current = setTimeout(() => {
        console.log("ToastContainer: Auto-dismissing toast:", currentToast.id);
        // Only dismiss if this is still the current toast
        if (timerToastIdRef.current === currentToast.id) {
          handleDismiss(currentToast.id);
        }
        autoDismissTimerRef.current = null;
        timerToastIdRef.current = null;
      }, 5000);
    }

    // Cleanup: clear timer when toast changes or component unmounts
    return () => {
      // Only clear if this toast is being replaced or removed
      if (timerToastIdRef.current === currentToast.id) {
        clearTimeout(autoDismissTimerRef.current!);
        autoDismissTimerRef.current = null;
        timerToastIdRef.current = null;
      }
    };
  }, [currentToast, handleDismiss]);

  // Cleanup timers on unmount
  useEffect(() => {
    return () => {
      if (cooldownTimerRef.current) {
        clearTimeout(cooldownTimerRef.current);
      }
    };
  }, []);

  return (
    <div
      className="fixed top-0 right-0 z-50 pointer-events-none"
      style={{ zIndex: 9999 }}
    >
      <AnimatePresence mode="wait">
        {currentToast && (
          <motion.div
            key={currentToast.id}
            initial={{ x: 400, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 400, opacity: 0 }}
            transition={{
              type: "spring",
              damping: 25,
              stiffness: 200,
            }}
            className="pointer-events-auto"
            style={{
              position: "absolute",
              top: "70px",
              right: "20px",
              width: "400px",
            }}
          >
            <ToastNotification
              notification={currentToast}
              onDismiss={() => {
                handleDismiss(currentToast.id);
              }}
              onClick={() => {
                // Handle click: select notification and analyze
                onNotificationClick?.(currentToast);
                // Dismiss toast after a short delay to allow the click to register
                setTimeout(() => {
                  handleDismiss(currentToast.id);
                }, 100);
              }}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
