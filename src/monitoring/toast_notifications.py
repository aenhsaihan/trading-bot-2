"""Toast notification system - slides in from top right"""

import streamlit as st
from typing import Optional, Dict
from datetime import datetime
from src.notifications.notification_types import Notification, NotificationPriority, NotificationType


def render_toast_notification(notification: Notification, duration: int = 5000):
    """
    Render a toast notification that slides in from top right.
    
    Args:
        notification: Notification to display
        duration: Duration in milliseconds before auto-dismiss
    """
    priority_emoji = {
        NotificationPriority.CRITICAL: "🔴",
        NotificationPriority.HIGH: "🟠",
        NotificationPriority.MEDIUM: "🟡",
        NotificationPriority.LOW: "🔵",
        NotificationPriority.INFO: "⚪"
    }.get(notification.priority, "⚪")
    
    type_emoji = {
        NotificationType.COMBINED_SIGNAL: "🚀",
        NotificationType.TECHNICAL_BREAKOUT: "📈",
        NotificationType.SOCIAL_SURGE: "💬",
        NotificationType.NEWS_EVENT: "📰",
        NotificationType.RISK_ALERT: "⚠️",
        NotificationType.SYSTEM_STATUS: "✅",
        NotificationType.TRADE_EXECUTED: "💰",
        NotificationType.USER_ACTION_REQUIRED: "👤"
    }.get(notification.notification_type, "📌")
    
    priority_color = {
        NotificationPriority.CRITICAL: "#FF4444",
        NotificationPriority.HIGH: "#FF8800",
        NotificationPriority.MEDIUM: "#FFBB00",
        NotificationPriority.LOW: "#4488FF",
        NotificationPriority.INFO: "#888888"
    }.get(notification.priority, "#888888")
    
    # Generate unique ID for this notification
    toast_id = f"toast_{notification.notification_id}"
    
    # CSS and JavaScript for toast notification
    toast_html = f"""
    <style>
    @keyframes slideInRight {{
        from {{
            transform: translateX(100%);
            opacity: 0;
        }}
        to {{
            transform: translateX(0);
            opacity: 1;
        }}
    }}
    
    @keyframes slideOutRight {{
        from {{
            transform: translateX(0);
            opacity: 1;
        }}
        to {{
            transform: translateX(100%);
            opacity: 0;
        }}
    }}
    
    .toast-container {{
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        max-width: 400px;
        animation: slideInRight 0.3s ease-out;
    }}
    
    .toast-notification {{
        background: linear-gradient(135deg, #1e1e2e 0%, #2a2a3e 100%);
        border-left: 4px solid {priority_color};
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.4);
        color: #ffffff;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        cursor: pointer;
        transition: transform 0.2s, box-shadow 0.2s;
    }}
    
    .toast-notification:hover {{
        transform: translateY(-2px);
        box-shadow: 0 12px 24px rgba(0, 0, 0, 0.5);
    }}
    
    .toast-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }}
    
    .toast-title {{
        display: flex;
        align-items: center;
        gap: 8px;
        font-weight: bold;
        font-size: 16px;
    }}
    
    .toast-close {{
        background: rgba(255, 255, 255, 0.2);
        border: none;
        border-radius: 50%;
        width: 24px;
        height: 24px;
        color: #ffffff;
        cursor: pointer;
        font-size: 16px;
        line-height: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: background 0.2s;
    }}
    
    .toast-close:hover {{
        background: rgba(255, 255, 255, 0.3);
    }}
    
    .toast-message {{
        color: #cccccc;
        font-size: 14px;
        line-height: 1.5;
        margin-bottom: 8px;
    }}
    
    .toast-meta {{
        display: flex;
        gap: 12px;
        font-size: 12px;
        color: #888;
        flex-wrap: wrap;
    }}
    
    .toast-meta span {{
        color: #888;
    }}
    
    .toast-slide-out {{
        animation: slideOutRight 0.3s ease-in forwards;
    }}
    </style>
    
    <div id="{toast_id}" class="toast-container">
        <div class="toast-notification" onclick="this.parentElement.classList.add('toast-slide-out'); setTimeout(() => this.parentElement.remove(), 300);">
            <div class="toast-header">
                <div class="toast-title">
                    <span style="font-size: 20px;">{priority_emoji}</span>
                    <span style="font-size: 18px;">{type_emoji}</span>
                    <span>{notification.title}</span>
                </div>
                <button class="toast-close" onclick="event.stopPropagation(); this.closest('.toast-container').classList.add('toast-slide-out'); setTimeout(() => this.closest('.toast-container').remove(), 300);">×</button>
            </div>
            <div class="toast-message">{notification.message}</div>
            <div class="toast-meta">
                {f'<span><strong>Symbol:</strong> <span style="color: #4CAF50;">{notification.symbol}</span></span>' if notification.symbol else ''}
                {f'<span><strong>Confidence:</strong> <span style="color: #4CAF50;">{notification.confidence_score:.0f}%</span></span>' if notification.confidence_score is not None else ''}
            </div>
        </div>
    </div>
    
    <script>
    // Auto-dismiss after duration
    setTimeout(function() {{
        var toast = document.getElementById('{toast_id}');
        if (toast) {{
            toast.classList.add('toast-slide-out');
            setTimeout(function() {{
                if (toast.parentElement) {{
                    toast.remove();
                }}
            }}, 300);
        }}
    }}, {duration});
    </script>
    """
    
    st.markdown(toast_html, unsafe_allow_html=True)


def render_toast_system():
    """Render the toast notification system container (call once at top of page)"""
    # This creates a container for toast notifications
    # Toasts will be added dynamically via render_toast_notification
    pass


def check_and_show_new_notifications(
    notification_manager,
    last_notification_id: Optional[str] = None
) -> Optional[str]:
    """
    Check for new notifications and show toast for them.
    
    Args:
        notification_manager: NotificationManager instance
        last_notification_id: ID of last shown notification
        
    Returns:
        ID of newest notification (if any)
    """
    all_notifications = notification_manager.get_all()
    if not all_notifications:
        return last_notification_id
    
    # Get newest notification
    newest = all_notifications[0]  # Already sorted by priority/time
    
    # If this is a new notification, show toast
    if newest.notification_id != last_notification_id and not newest.responded:
        render_toast_notification(newest, duration=5000)
        return newest.notification_id
    
    return last_notification_id

