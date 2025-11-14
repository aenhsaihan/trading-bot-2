"""X integration service that ties monitoring, conversion, and notifications together"""

import sys
from pathlib import Path
from typing import Dict, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger
from backend.services.x_monitor_service import get_x_monitor_service
from backend.services.x_notification_converter import get_x_notification_converter
from backend.services.notification_service import NotificationService
from backend.services.x_api_client import get_x_api_client


class XIntegrationService:
    """Service that integrates X monitoring with notification system"""
    
    def __init__(self, user_id: str = "default", poll_interval: int = 300):
        """
        Initialize X integration service
        
        Args:
            user_id: User identifier
            poll_interval: Polling interval in seconds
        """
        self.logger = setup_logger(f"{__name__}.XIntegrationService")
        self.user_id = user_id
        
        # Initialize services
        self.monitor_service = get_x_monitor_service(user_id, poll_interval)
        self.converter = get_x_notification_converter()
        self.notification_service = NotificationService()
        self.api_client = get_x_api_client(user_id)
        
        # Set up callback for new tweets
        self.monitor_service.set_on_new_tweet_callback(self._on_new_tweet)
    
    def _on_new_tweet(self, tweet: Dict):
        """
        Callback when new tweet is detected
        
        Args:
            tweet: Tweet data from X API
        """
        try:
            # Get author info if available
            author_id = tweet.get("author_id") or tweet.get("_monitored_user_id")
            author = None
            
            if author_id:
                # Try to get author from tweet data or fetch it
                # (Author info should be in tweet["author"] if included in API response)
                author = tweet.get("author")
                
                # If not in tweet, try to get from followed accounts
                if not author:
                    followed_accounts = self.monitor_service.get_followed_accounts()
                    author = next(
                        (acc for acc in followed_accounts if acc.get("id") == author_id),
                        None
                    )
            
            # Convert tweet to notification
            notification_data = self.converter.convert_tweet_to_notification(tweet, author)
            
            # Create notification via NotificationService
            notification = self.notification_service.create_notification(
                notification_type=notification_data["notification_type"],
                priority=notification_data["priority"],
                title=notification_data["title"],
                message=notification_data["message"],
                source=notification_data["source"],
                symbol=notification_data.get("symbol"),
                metadata=notification_data.get("metadata"),
            )
            
            # Broadcast via WebSocket (NotificationService handles this)
            self.notification_service.broadcast_notification(notification)
            
            self.logger.info(f"Created notification from X tweet: {notification.title}")
            
        except Exception as e:
            self.logger.error(f"Error processing new tweet: {e}", exc_info=True)
    
    def start_monitoring(self):
        """Start monitoring X accounts"""
        if not self.monitor_service.is_connected():
            self.logger.error("Cannot start monitoring: X account not connected")
            return False
        
        # Fetch followed accounts first
        self.monitor_service.fetch_followed_accounts()
        
        # Start monitoring
        self.monitor_service.start()
        
        self.logger.info("X monitoring started")
        return True
    
    def stop_monitoring(self):
        """Stop monitoring X accounts"""
        self.monitor_service.stop()
        self.logger.info("X monitoring stopped")
    
    def get_status(self) -> Dict:
        """Get integration service status"""
        monitor_status = self.monitor_service.get_status()
        
        return {
            "connected": monitor_status["connected"],
            "monitoring": monitor_status["running"],
            "followed_accounts": len(monitor_status.get("followed_accounts_count", 0)),
            "poll_interval": monitor_status.get("poll_interval", 300),
        }
    
    def get_followed_accounts(self) -> list:
        """Get list of followed accounts"""
        return self.monitor_service.get_followed_accounts()
    
    def refresh_followed_accounts(self) -> list:
        """Refresh and return list of followed accounts"""
        return self.monitor_service.fetch_followed_accounts()


# Global service instance (per user)
_x_integration_services: Dict[str, XIntegrationService] = {}

def get_x_integration_service(user_id: str = "default", poll_interval: int = 300) -> XIntegrationService:
    """Get X integration service instance for user"""
    if user_id not in _x_integration_services:
        _x_integration_services[user_id] = XIntegrationService(user_id=user_id, poll_interval=poll_interval)
    return _x_integration_services[user_id]

