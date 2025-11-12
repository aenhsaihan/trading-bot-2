"""API client for FastAPI notification backend"""

import requests
from typing import Optional, Dict, List
import streamlit as st


class NotificationAPIClient:
    """Client for interacting with FastAPI notification backend"""
    
    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize API client.
        
        Args:
            base_url: Base URL of FastAPI backend. If None, tries to get from
                     Streamlit secrets or defaults to localhost
        """
        if base_url is None:
            # Try to get from Streamlit secrets
            try:
                base_url = st.secrets.get("api", {}).get("url", "http://localhost:8000")
            except (AttributeError, FileNotFoundError):
                # Fallback to localhost if secrets not available
                base_url = "http://localhost:8000"
        
        self.base_url = base_url.rstrip("/")
        self.notifications_url = f"{self.base_url}/notifications"
        self.websocket_url = f"{self.base_url.replace('http', 'ws')}/ws/notifications"
    
    def create_notification(
        self,
        notification_type: str,
        priority: str,
        title: str,
        message: str,
        source: str,
        symbol: Optional[str] = None,
        confidence_score: Optional[float] = None,
        urgency_score: Optional[float] = None,
        promise_score: Optional[float] = None,
        metadata: Optional[Dict] = None,
        actions: Optional[List[str]] = None
    ) -> Optional[Dict]:
        """Create a new notification via API"""
        try:
            response = requests.post(
                self.notifications_url,
                json={
                    "type": notification_type,
                    "priority": priority,
                    "title": title,
                    "message": message,
                    "source": source,
                    "symbol": symbol,
                    "confidence_score": confidence_score,
                    "urgency_score": urgency_score,
                    "promise_score": promise_score,
                    "metadata": metadata or {},
                    "actions": actions or []
                },
                timeout=5
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"Failed to create notification: {e}")
            return None
    
    def get_notifications(self, limit: Optional[int] = None, unread_only: bool = False) -> List[Dict]:
        """Get all notifications from API"""
        try:
            params = {}
            if limit:
                params["limit"] = limit
            if unread_only:
                params["unread_only"] = "true"
            
            response = requests.get(self.notifications_url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            return data.get("notifications", [])
        except requests.exceptions.RequestException as e:
            st.warning(f"Failed to fetch notifications: {e}")
            return []
    
    def get_notification(self, notification_id: str) -> Optional[Dict]:
        """Get a specific notification"""
        try:
            response = requests.get(
                f"{self.notifications_url}/{notification_id}",
                timeout=5
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException:
            return None
    
    def mark_as_read(self, notification_id: str) -> bool:
        """Mark notification as read"""
        try:
            response = requests.patch(
                f"{self.notifications_url}/{notification_id}",
                json={"read": True},
                timeout=5
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException:
            return False
    
    def respond_to_notification(self, notification_id: str, action: str, custom_message: Optional[str] = None) -> bool:
        """Respond to a notification"""
        try:
            params = {"action": action}
            if custom_message:
                params["custom_message"] = custom_message
            
            response = requests.post(
                f"{self.notifications_url}/{notification_id}/respond",
                params=params,
                timeout=5
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException:
            return False
    
    def delete_notification(self, notification_id: str) -> bool:
        """Delete a notification"""
        try:
            response = requests.delete(
                f"{self.notifications_url}/{notification_id}",
                timeout=5
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException:
            return False
    
    def get_stats(self) -> Optional[Dict]:
        """Get notification statistics"""
        try:
            response = requests.get(
                f"{self.notifications_url}/stats/summary",
                timeout=5
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException:
            return None
    
    def health_check(self) -> bool:
        """Check if API is available"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=2)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

