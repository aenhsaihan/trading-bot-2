"""Notification UI components for Streamlit"""

import streamlit as st
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from src.notifications.notification_types import (
    Notification,
    NotificationPriority,
    NotificationType,
    NotificationSource
)


def get_priority_emoji(priority: NotificationPriority) -> str:
    """Get emoji for priority level"""
    emoji_map = {
        NotificationPriority.CRITICAL: "🔴",
        NotificationPriority.HIGH: "🟠",
        NotificationPriority.MEDIUM: "🟡",
        NotificationPriority.LOW: "🔵",
        NotificationPriority.INFO: "⚪"
    }
    return emoji_map.get(priority, "⚪")


def get_priority_color(priority: NotificationPriority) -> str:
    """Get color for priority level"""
    color_map = {
        NotificationPriority.CRITICAL: "#FF4444",  # Red
        NotificationPriority.HIGH: "#FF8800",  # Orange
        NotificationPriority.MEDIUM: "#FFBB00",  # Yellow
        NotificationPriority.LOW: "#4488FF",  # Blue
        NotificationPriority.INFO: "#888888"  # Gray
    }
    return color_map.get(priority, "#888888")


def get_type_emoji(notification_type: NotificationType) -> str:
    """Get emoji for notification type"""
    emoji_map = {
        NotificationType.COMBINED_SIGNAL: "🚀",
        NotificationType.TECHNICAL_BREAKOUT: "📈",
        NotificationType.SOCIAL_SURGE: "💬",
        NotificationType.NEWS_EVENT: "📰",
        NotificationType.RISK_ALERT: "⚠️",
        NotificationType.SYSTEM_STATUS: "✅",
        NotificationType.TRADE_EXECUTED: "💰",
        NotificationType.USER_ACTION_REQUIRED: "👤"
    }
    return emoji_map.get(notification_type, "📌")


def format_time_ago(timestamp: datetime) -> str:
    """Format timestamp as relative time"""
    now = datetime.now()
    delta = now - timestamp
    
    if delta.total_seconds() < 60:
        return "just now"
    elif delta.total_seconds() < 3600:
        minutes = int(delta.total_seconds() / 60)
        return f"{minutes}m ago"
    elif delta.total_seconds() < 86400:
        hours = int(delta.total_seconds() / 3600)
        return f"{hours}h ago"
    else:
        days = int(delta.total_seconds() / 86400)
        return f"{days}d ago"


def render_notification_card(notification: Notification, key_suffix: str = ""):
    """
    Render a single notification card with modern, sexy design.
    
    Args:
        notification: Notification to render
        key_suffix: Suffix for Streamlit widget keys
    """
    priority_emoji = get_priority_emoji(notification.priority)
    priority_color = get_priority_color(notification.priority)
    type_emoji = get_type_emoji(notification.notification_type)
    
    # Card styling
    card_style = f"""
    <div style="
        border-left: 4px solid {priority_color};
        background: linear-gradient(135deg, #1e1e2e 0%, #2a2a3e 100%);
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        transition: transform 0.2s;
    ">
    """
    
    # Header row
    header_html = f"""
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
        <div style="display: flex; align-items: center; gap: 8px;">
            <span style="font-size: 20px;">{priority_emoji}</span>
            <span style="font-size: 18px;">{type_emoji}</span>
            <strong style="color: #ffffff; font-size: 16px;">{notification.title}</strong>
        </div>
        <span style="color: #888; font-size: 12px;">{format_time_ago(notification.created_at)}</span>
    </div>
    """
    
    # Message
    message_html = f"""
    <div style="color: #cccccc; font-size: 14px; margin-bottom: 12px; line-height: 1.5;">
        {notification.message}
    </div>
    """
    
    # Metadata row (symbol, scores)
    metadata_html = ""
    if notification.symbol:
        metadata_html += f"""
        <div style="display: flex; gap: 16px; margin-bottom: 8px; flex-wrap: wrap;">
            <span style="color: #888; font-size: 12px;">
                <strong>Symbol:</strong> <span style="color: #4CAF50;">{notification.symbol}</span>
            </span>
        """
        
        if notification.confidence_score is not None:
            confidence_color = "#4CAF50" if notification.confidence_score >= 75 else "#FF9800" if notification.confidence_score >= 50 else "#F44336"
            metadata_html += f"""
            <span style="color: #888; font-size: 12px;">
                <strong>Confidence:</strong> <span style="color: {confidence_color};">{notification.confidence_score:.0f}%</span>
            </span>
            """
        
        if notification.urgency_score is not None:
            urgency_color = "#F44336" if notification.urgency_score >= 75 else "#FF9800" if notification.urgency_score >= 50 else "#4CAF50"
            metadata_html += f"""
            <span style="color: #888; font-size: 12px;">
                <strong>Urgency:</strong> <span style="color: {urgency_color};">{notification.urgency_score:.0f}%</span>
            </span>
            """
        
        if notification.promise_score is not None:
            promise_color = "#4CAF50" if notification.promise_score >= 75 else "#FF9800" if notification.promise_score >= 50 else "#888"
            metadata_html += f"""
            <span style="color: #888; font-size: 12px;">
                <strong>Promise:</strong> <span style="color: {promise_color};">{notification.promise_score:.0f}%</span>
            </span>
            """
        
        metadata_html += "</div>"
    
    # Actions row
    actions_html = ""
    if notification.actions:
        actions_html = f"""
        <div style="display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap;">
        """
        for action in notification.actions:
            action_color = "#4CAF50" if action.lower() in ["approve", "buy"] else "#F44336" if action.lower() in ["reject", "sell"] else "#2196F3"
            actions_html += f"""
            <button style="
                background: {action_color};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                cursor: pointer;
                font-weight: 500;
            ">{action.title()}</button>
            """
        actions_html += "</div>"
    
    # Close card
    card_html = card_style + header_html + message_html + metadata_html + actions_html + "</div>"
    
    st.markdown(card_html, unsafe_allow_html=True)
    
    # Add action buttons (Streamlit buttons for actual functionality)
    if notification.actions:
        cols = st.columns(len(notification.actions))
        for idx, action in enumerate(notification.actions):
            with cols[idx]:
                button_key = f"action_{notification.notification_id}_{action}_{key_suffix}"
                button_color = "primary" if action.lower() in ["approve", "buy"] else "secondary"
                if st.button(action.title(), key=button_key, type=button_color):
                    return action, notification.notification_id
    
    return None, None


def render_notification_center(
    notifications: List[Notification],
    title: str = "🔔 Notification Center",
    max_display: int = 10,
    show_unread_only: bool = False
):
    """
    Render the notification center with modern, sexy design.
    
    Args:
        notifications: List of notifications to display
        title: Center title
        max_display: Maximum notifications to display
        show_unread_only: Only show unread notifications
    """
    st.markdown(f"## {title}")
    
    # Filter notifications
    display_notifications = notifications
    if show_unread_only:
        display_notifications = [n for n in notifications if not n.read]
    
    # Limit display
    display_notifications = display_notifications[:max_display]
    
    if not display_notifications:
        st.info("✨ No notifications - Everything is calm and monitored.")
        return
    
    # Stats bar
    unread_count = len([n for n in notifications if not n.read])
    critical_count = len([n for n in notifications if n.priority == NotificationPriority.CRITICAL])
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total", len(notifications))
    with col2:
        st.metric("Unread", unread_count, delta=None)
    with col3:
        st.metric("Critical", critical_count, delta=None)
    
    st.divider()
    
    # Render notifications
    for notification in display_notifications:
        action, notif_id = render_notification_card(notification)
        if action and notif_id:
            return action, notif_id
    
    return None, None


def render_system_status_indicator(status: Dict):
    """
    Render the "Everything OK" system status indicator.
    
    Args:
        status: Status dictionary from NotificationManager.get_system_status()
    """
    status_type = status.get('status', 'ok')
    message = status.get('message', '✅ All systems normal')
    
    # Status colors
    color_map = {
        'critical': '#FF4444',
        'attention': '#FF8800',
        'active': '#4CAF50',
        'ok': '#4CAF50'
    }
    
    color = color_map.get(status_type, '#4CAF50')
    
    status_html = f"""
    <div style="
        background: linear-gradient(135deg, {color}15 0%, {color}05 100%);
        border: 2px solid {color};
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 16px;
        text-align: center;
    ">
        <div style="font-size: 24px; margin-bottom: 8px;">
            {message}
        </div>
        <div style="color: #888; font-size: 12px;">
            Monitoring {status.get('total_notifications', 0)} signals • Always watching, always listening
        </div>
    </div>
    """
    
    st.markdown(status_html, unsafe_allow_html=True)


def render_notification_badge(count: int, priority: Optional[NotificationPriority] = None):
    """
    Render a notification badge (for sidebar or header).
    
    Args:
        count: Number of notifications
        priority: Optional priority filter
    """
    if count == 0:
        return
    
    badge_color = "#FF4444" if priority == NotificationPriority.CRITICAL else "#FF8800"
    
    badge_html = f"""
    <span style="
        background: {badge_color};
        color: white;
        border-radius: 12px;
        padding: 2px 8px;
        font-size: 11px;
        font-weight: bold;
        margin-left: 8px;
    ">{count}</span>
    """
    
    st.markdown(badge_html, unsafe_allow_html=True)

