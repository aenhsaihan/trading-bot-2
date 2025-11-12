"""Priority queue for notifications"""

import heapq
from typing import List, Optional
from datetime import datetime
from .notification_types import Notification, NotificationPriority


class NotificationQueue:
    """Priority queue for managing notifications by priority and timestamp"""
    
    # Priority weights (higher = more urgent)
    PRIORITY_WEIGHTS = {
        NotificationPriority.CRITICAL: 1000,
        NotificationPriority.HIGH: 500,
        NotificationPriority.MEDIUM: 200,
        NotificationPriority.LOW: 100,
        NotificationPriority.INFO: 50
    }
    
    def __init__(self):
        """Initialize notification queue"""
        self._queue: List[tuple] = []  # Min-heap: (priority_weight, timestamp, notification)
        self._notifications: dict = {}  # notification_id -> notification
        self._counter = 0  # For stable sorting when priorities are equal
    
    def add(self, notification: Notification):
        """
        Add notification to queue.
        
        Args:
            notification: Notification to add
        """
        priority_weight = self.PRIORITY_WEIGHTS.get(notification.priority, 0)
        # Use negative timestamp for min-heap (newer = higher priority when same weight)
        timestamp = -notification.created_at.timestamp()
        
        # Add counter to ensure stable ordering
        entry = (priority_weight, timestamp, self._counter, notification)
        heapq.heappush(self._queue, entry)
        
        self._notifications[notification.notification_id] = notification
        self._counter += 1
    
    def pop(self) -> Optional[Notification]:
        """
        Pop highest priority notification.
        
        Returns:
            Highest priority notification or None if queue is empty
        """
        if not self._queue:
            return None
        
        _, _, _, notification = heapq.heappop(self._queue)
        self._notifications.pop(notification.notification_id, None)
        return notification
    
    def peek(self) -> Optional[Notification]:
        """
        Peek at highest priority notification without removing it.
        
        Returns:
            Highest priority notification or None if queue is empty
        """
        if not self._queue:
            return None
        
        _, _, _, notification = self._queue[0]
        return notification
    
    def get_all(self, limit: Optional[int] = None) -> List[Notification]:
        """
        Get all notifications sorted by priority (highest first).
        
        Args:
            limit: Maximum number of notifications to return
            
        Returns:
            List of notifications sorted by priority
        """
        # Create a copy to avoid modifying the heap
        queue_copy = self._queue.copy()
        notifications = []
        
        while queue_copy and (limit is None or len(notifications) < limit):
            _, _, _, notification = heapq.heappop(queue_copy)
            notifications.append(notification)
        
        return notifications
    
    def get_by_priority(self, priority: NotificationPriority) -> List[Notification]:
        """
        Get all notifications of a specific priority.
        
        Args:
            priority: Priority level to filter by
            
        Returns:
            List of notifications with the specified priority
        """
        return [
            notification
            for notification in self._notifications.values()
            if notification.priority == priority
        ]
    
    def get_unread(self) -> List[Notification]:
        """Get all unread notifications"""
        return [
            notification
            for notification in self._notifications.values()
            if not notification.read
        ]
    
    def mark_read(self, notification_id: str):
        """Mark a notification as read"""
        if notification_id in self._notifications:
            self._notifications[notification_id].read = True
    
    def remove(self, notification_id: str) -> bool:
        """
        Remove a notification from the queue.
        
        Args:
            notification_id: ID of notification to remove
            
        Returns:
            True if removed, False if not found
        """
        if notification_id not in self._notifications:
            return False
        
        # Rebuild queue without the removed notification
        notification = self._notifications.pop(notification_id)
        self._queue = [
            entry for entry in self._queue
            if entry[3].notification_id != notification_id
        ]
        heapq.heapify(self._queue)
        
        return True
    
    def size(self) -> int:
        """Get queue size"""
        return len(self._queue)
    
    def clear(self):
        """Clear all notifications"""
        self._queue.clear()
        self._notifications.clear()
        self._counter = 0

