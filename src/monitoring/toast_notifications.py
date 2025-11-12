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
    
    # CSS and JavaScript for toast notification - inject styles and handlers once globally
    if not hasattr(render_toast_notification, '_styles_injected'):
        st.markdown("""
    <style>
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
    
    .toast-container {
        position: fixed !important;
        top: 70px !important;
        right: 20px !important;
        z-index: 9999 !important;
        max-width: 400px !important;
        animation: slideInRight 0.3s ease-out !important;
    }
    
    .toast-notification {
        background: linear-gradient(135deg, #1e1e2e 0%, #2a2a3e 100%) !important;
        border-left: 4px solid var(--priority-color) !important;
        border-radius: 12px !important;
        padding: 16px !important;
        margin-bottom: 12px !important;
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.4) !important;
        color: #ffffff !important;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        cursor: pointer !important;
        transition: transform 0.2s, box-shadow 0.2s !important;
    }
    
    .toast-notification:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 12px 24px rgba(0, 0, 0, 0.5) !important;
    }
    
    .toast-header {
        display: flex !important;
        justify-content: space-between !important;
        align-items: center !important;
        margin-bottom: 8px !important;
    }
    
    .toast-title {
        display: flex !important;
        align-items: center !important;
        gap: 8px !important;
        font-weight: bold !important;
        font-size: 16px !important;
        color: #ffffff !important;
    }
    
    .toast-close {
        background: rgba(255, 255, 255, 0.2) !important;
        border: none !important;
        border-radius: 50% !important;
        width: 24px !important;
        height: 24px !important;
        color: #ffffff !important;
        cursor: pointer !important;
        font-size: 16px !important;
        line-height: 1 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        transition: background 0.2s !important;
    }
    
    .toast-close:hover {
        background: rgba(255, 255, 255, 0.3) !important;
    }
    
    .toast-message {
        color: #cccccc !important;
        font-size: 14px !important;
        line-height: 1.5 !important;
        margin-bottom: 8px !important;
    }
    
    .toast-meta {
        display: flex !important;
        gap: 12px !important;
        font-size: 12px !important;
        color: #888 !important;
        flex-wrap: wrap !important;
    }
    
    .toast-meta span {
        color: #888 !important;
    }
    
    .toast-slide-out {
        animation: slideOutRight 0.3s ease-in forwards !important;
    }
    </style>
    <script>
    // Global event delegation for toast dismissals - ensure it runs after DOM is ready
    (function() {
        function setupToastHandlers() {
            // Remove old listeners to avoid duplicates
            document.removeEventListener('click', handleToastClick);
            document.addEventListener('click', handleToastClick);
        }
        
        function handleToastClick(e) {
            // Handle close button clicks
            if (e.target && e.target.classList.contains('toast-close')) {
                e.stopPropagation();
                e.preventDefault();
                var container = e.target.closest('.toast-container');
                if (container) {
                    container.classList.add('toast-slide-out');
                    setTimeout(function() {
                        if (container.parentElement) {
                            container.remove();
                        }
                    }, 300);
                }
                return false;
            }
            // Handle toast card clicks (but not if clicking on close button)
            if (e.target && (e.target.classList.contains('toast-notification') || e.target.closest('.toast-notification'))) {
                if (!e.target.classList.contains('toast-close') && !e.target.closest('.toast-close')) {
                    var container = e.target.closest('.toast-container');
                    if (container) {
                        container.classList.add('toast-slide-out');
                        setTimeout(function() {
                            if (container.parentElement) {
                                container.remove();
                            }
                        }, 300);
                    }
                }
            }
        }
        
        // Setup handlers when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', setupToastHandlers);
        } else {
            setupToastHandlers();
        }
        
        // Also setup on next tick to catch dynamically added elements
        setTimeout(setupToastHandlers, 100);
    })();
    </script>
    """, unsafe_allow_html=True)
        render_toast_notification._styles_injected = True
    
    # Escape HTML in notification content to prevent XSS
    import html
    safe_title = html.escape(str(notification.title))
    safe_message = html.escape(str(notification.message))
    safe_symbol = html.escape(str(notification.symbol)) if notification.symbol else ""
    
    # Build metadata HTML
    meta_html = ""
    if notification.symbol:
        meta_html += f'<span><strong>Symbol:</strong> <span style="color: #4CAF50 !important;">{safe_symbol}</span></span>'
    if notification.confidence_score is not None:
        meta_html += f'<span><strong>Confidence:</strong> <span style="color: #4CAF50 !important;">{notification.confidence_score:.0f}%</span></span>'
    
    # Check if this toast should be dismissed (Python-based dismissal tracking)
    dismissed_toasts = st.session_state.get('dismissed_toasts', set())
    if notification.notification_id in dismissed_toasts:
        return  # Don't render dismissed toasts
    
    # Check if auto-dismiss time has passed
    import time
    toast_timestamps = st.session_state.get('toast_timestamps', {})
    if notification.notification_id not in toast_timestamps:
        toast_timestamps[notification.notification_id] = time.time()
        st.session_state.toast_timestamps = toast_timestamps
    
    elapsed = time.time() - toast_timestamps.get(notification.notification_id, time.time())
    if elapsed * 1000 >= duration:
        # Auto-dismiss by adding to dismissed set
        dismissed_toasts.add(notification.notification_id)
        st.session_state.dismissed_toasts = dismissed_toasts
        return
    
    # HTML for the toast notification with integrated close button
    # The close button will be handled via Streamlit button below, styled to match
    toast_html = f'''
    <div id="{toast_id}" class="toast-container" style="--priority-color: {priority_color};" data-toast-id="{toast_id}">
        <div class="toast-notification" id="toast-notif-{toast_id}" style="border-left-color: {priority_color} !important;">
            <div class="toast-header">
                <div class="toast-title">
                    <span style="font-size: 20px;">{priority_emoji}</span>
                    <span style="font-size: 18px;">{type_emoji}</span>
                    <span style="color: #ffffff !important;">{safe_title}</span>
                </div>
            </div>
            <div class="toast-message">{safe_message}</div>
            <div class="toast-meta">{meta_html}</div>
        </div>
    </div>
    '''
    
    st.markdown(toast_html, unsafe_allow_html=True)
    
    # Add Streamlit button styled to look like close button, positioned absolutely
    # Use columns to position it in top right
    with st.container():
        # Create a container with relative positioning for the button
        st.markdown(f'''
        <div style="position: relative; margin-top: -60px; margin-bottom: 20px;">
            <div style="position: absolute; top: 0; right: 20px; z-index: 10000;">
        ''', unsafe_allow_html=True)
        
        # Check if dismiss button was clicked
        dismiss_key = f"dismiss_{toast_id}"
        if dismiss_key not in st.session_state:
            st.session_state[dismiss_key] = False
        
        if st.button("×", key=dismiss_key, help="Dismiss notification", 
                    use_container_width=False):
            dismissed_toasts.add(notification.notification_id)
            st.session_state.dismissed_toasts = dismissed_toasts
            st.session_state[dismiss_key] = True
            st.rerun()
        
        st.markdown('</div></div>', unsafe_allow_html=True)
        
        # Also add CSS to style the button
        st.markdown(f'''
        <style>
        button[key="{dismiss_key}"] {{
            background: rgba(255, 255, 255, 0.2) !important;
            border: none !important;
            border-radius: 50% !important;
            width: 24px !important;
            height: 24px !important;
            color: #ffffff !important;
            font-size: 16px !important;
            line-height: 1 !important;
            padding: 0 !important;
            margin: 0 !important;
        }}
        button[key="{dismiss_key}"]:hover {{
            background: rgba(255, 255, 255, 0.3) !important;
        }}
        </style>
        ''', unsafe_allow_html=True)


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
    
    # Check if dismissed
    dismissed_toasts = st.session_state.get('dismissed_toasts', set())
    if newest.notification_id in dismissed_toasts:
        return last_notification_id
    
    # If this is a new notification, show toast
    if newest.notification_id != last_notification_id and not newest.responded:
        render_toast_notification(newest, duration=5000)
        return newest.notification_id
    
    return last_notification_id

