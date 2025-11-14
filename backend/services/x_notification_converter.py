"""Convert X (Twitter) tweets to notifications"""

import sys
import re
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger
from src.notifications.notification_types import NotificationType, NotificationPriority, NotificationSource


class XNotificationConverter:
    """Convert X tweets to trading bot notifications"""
    
    # Common crypto symbols to detect in tweets
    CRYPTO_SYMBOLS = [
        "BTC", "ETH", "SOL", "BNB", "ADA", "XRP", "DOT", "DOGE", "MATIC",
        "AVAX", "LINK", "UNI", "ATOM", "ETC", "LTC", "BCH", "XLM", "ALGO",
        "VET", "FIL", "TRX", "EOS", "AAVE", "MKR", "COMP", "SNX", "SUSHI",
        "CRV", "YFI", "1INCH", "SAND", "MANA", "AXS", "ENJ", "GALA", "CHZ"
    ]
    
    # High-value accounts (can be configured later)
    HIGH_VALUE_ACCOUNTS = [
        # Add high-value account usernames here
        # Example: "elonmusk", "VitalikButerin", etc.
    ]
    
    def __init__(self):
        """Initialize converter"""
        self.logger = setup_logger(f"{__name__}.XNotificationConverter")
        
        # Build regex pattern for crypto symbols
        symbols_pattern = "|".join(self.CRYPTO_SYMBOLS)
        self.symbol_regex = re.compile(rf'\b({symbols_pattern})\b', re.IGNORECASE)
    
    def extract_symbols(self, text: str) -> List[str]:
        """
        Extract crypto symbols from tweet text
        
        Args:
            text: Tweet text
            
        Returns:
            List of detected symbols (uppercase)
        """
        matches = self.symbol_regex.findall(text)
        # Deduplicate and uppercase
        symbols = list(set([m.upper() for m in matches]))
        return symbols
    
    def determine_priority(self, tweet: Dict, author: Optional[Dict] = None) -> NotificationPriority:
        """
        Determine notification priority based on tweet and author
        
        Args:
            tweet: Tweet data
            author: Author user data
            
        Returns:
            Notification priority
        """
        # Check if author is high-value
        if author:
            username = author.get("username", "").lower()
            if username in [acc.lower() for acc in self.HIGH_VALUE_ACCOUNTS]:
                return NotificationPriority.HIGH
        
        # Check engagement metrics
        metrics = tweet.get("public_metrics", {})
        like_count = metrics.get("like_count", 0)
        retweet_count = metrics.get("retweet_count", 0)
        
        # High engagement = higher priority
        if like_count > 1000 or retweet_count > 100:
            return NotificationPriority.HIGH
        
        # Default to medium
        return NotificationPriority.MEDIUM
    
    def determine_notification_type(self, tweet: Dict, symbols: List[str]) -> NotificationType:
        """
        Determine notification type based on tweet content
        
        Args:
            tweet: Tweet data
            symbols: Detected crypto symbols
            
        Returns:
            Notification type
        """
        text = tweet.get("text", "").lower()
        
        # Check for keywords that indicate different types
        if any(keyword in text for keyword in ["breakout", "resistance", "support", "bullish", "bearish"]):
            return NotificationType.TECHNICAL_BREAKOUT
        
        if any(keyword in text for keyword in ["news", "announcement", "launch", "partnership"]):
            return NotificationType.NEWS_EVENT
        
        if any(keyword in text for keyword in ["risk", "warning", "danger", "crash", "dump"]):
            return NotificationType.RISK_ALERT
        
        # Default to social surge if symbols detected
        if symbols:
            return NotificationType.SOCIAL_SURGE
        
        # Default
        return NotificationType.NEWS_EVENT
    
    def convert_tweet_to_notification(
        self,
        tweet: Dict,
        author: Optional[Dict] = None
    ) -> Dict:
        """
        Convert tweet to notification data structure
        
        Args:
            tweet: Tweet data from X API
            author: Author user data (if available)
            
        Returns:
            Dictionary with notification data ready for NotificationService
        """
        tweet_text = tweet.get("text", "")
        tweet_id = tweet.get("id", "")
        created_at = tweet.get("created_at", "")
        
        # Extract symbols
        symbols = self.extract_symbols(tweet_text)
        symbol = symbols[0] if symbols else None
        
        # Determine priority
        priority = self.determine_priority(tweet, author)
        
        # Determine notification type
        notification_type = self.determine_notification_type(tweet, symbols)
        
        # Build title
        if author:
            author_name = author.get("name", author.get("username", "Unknown"))
            title = f"{author_name} on X"
        else:
            title = "New X Post"
        
        # Build message (full tweet text)
        message = tweet_text
        
        # Build metadata
        metadata = {
            "tweet_id": tweet_id,
            "tweet_url": f"https://twitter.com/i/web/status/{tweet_id}",
            "created_at": created_at,
            "author_id": tweet.get("author_id"),
            "symbols_detected": symbols,
            "engagement": tweet.get("public_metrics", {}),
        }
        
        if author:
            metadata["author"] = {
                "id": author.get("id"),
                "username": author.get("username"),
                "name": author.get("name"),
            }
        
        # Build notification data
        notification_data = {
            "notification_type": notification_type.value,
            "priority": priority.value,
            "title": title,
            "message": message,
            "source": NotificationSource.TWITTER.value,
            "symbol": symbol,
            "metadata": metadata,
        }
        
        self.logger.debug(f"Converted tweet {tweet_id} to notification: {title}")
        
        return notification_data


# Global converter instance
_x_notification_converter = None

def get_x_notification_converter() -> XNotificationConverter:
    """Get global X notification converter instance"""
    global _x_notification_converter
    if _x_notification_converter is None:
        _x_notification_converter = XNotificationConverter()
    return _x_notification_converter

