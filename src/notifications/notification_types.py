"""Notification types and priorities"""

from enum import Enum
from typing import Dict, Optional
from datetime import datetime


class NotificationPriority(Enum):
    """Notification priority levels"""
    CRITICAL = "critical"  # Immediate action required (risk alerts, extreme opportunities)
    HIGH = "high"  # High confidence opportunity or significant risk
    MEDIUM = "medium"  # Moderate confidence opportunity
    LOW = "low"  # Low confidence, informational
    INFO = "info"  # General information, no action needed


class NotificationType(Enum):
    """Types of notifications"""
    # Opportunity types (ordered by importance)
    COMBINED_SIGNAL = "combined_signal"  # Technical + Social alignment (highest priority)
    TECHNICAL_BREAKOUT = "technical_breakout"  # Strong technical signal
    SOCIAL_SURGE = "social_surge"  # Extreme sentiment shift
    NEWS_EVENT = "news_event"  # Major news breaking
    RISK_ALERT = "risk_alert"  # Negative signals (protect capital)
    
    # System notifications
    SYSTEM_STATUS = "system_status"  # "Everything OK" updates
    TRADE_EXECUTED = "trade_executed"  # Autonomous trade executed
    USER_ACTION_REQUIRED = "user_action_required"  # Needs user decision


class NotificationSource(Enum):
    """Source of the notification"""
    TECHNICAL = "technical"  # From technical indicators
    TWITTER = "twitter"
    TELEGRAM = "telegram"
    NEWS = "news"
    REDDIT = "reddit"
    DISCORD = "discord"
    SYSTEM = "system"  # System-generated
    COMBINED = "combined"  # Multiple sources


class Notification:
    """Represents a single notification"""
    
    def __init__(
        self,
        notification_id: str,
        notification_type: NotificationType,
        priority: NotificationPriority,
        title: str,
        message: str,
        source: NotificationSource,
        symbol: Optional[str] = None,
        confidence_score: Optional[float] = None,
        urgency_score: Optional[float] = None,
        promise_score: Optional[float] = None,
        metadata: Optional[Dict] = None,
        actions: Optional[list] = None,
        expires_at: Optional[datetime] = None
    ):
        """
        Initialize notification.
        
        Args:
            notification_id: Unique identifier
            notification_type: Type of notification
            priority: Priority level
            title: Notification title
            message: Detailed message
            source: Source of notification
            symbol: Trading pair symbol (if applicable)
            confidence_score: Confidence score (0-100)
            urgency_score: Urgency score (0-100)
            promise_score: Promise/opportunity score (0-100)
            metadata: Additional data (technical indicators, sentiment data, etc.)
            actions: Available actions (e.g., ["approve", "reject", "custom"])
            expires_at: When notification expires (for time-sensitive opportunities)
        """
        self.notification_id = notification_id
        self.notification_type = notification_type
        self.priority = priority
        self.title = title
        self.message = message
        self.source = source
        self.symbol = symbol
        self.confidence_score = confidence_score
        self.urgency_score = urgency_score
        self.promise_score = promise_score
        self.metadata = metadata or {}
        self.actions = actions or []
        self.expires_at = expires_at
        
        self.created_at = datetime.now()
        self.read = False
        self.responded = False
        self.response_action = None
        self.response_at = None
        self.summarized_message: Optional[str] = None  # AI-generated concise message
    
    def to_dict(self) -> Dict:
        """Convert notification to dictionary"""
        return {
            'id': self.notification_id,
            'type': self.notification_type.value,
            'priority': self.priority.value,
            'title': self.title,
            'message': self.message,
            'source': self.source.value,
            'symbol': self.symbol,
            'confidence_score': self.confidence_score,
            'urgency_score': self.urgency_score,
            'promise_score': self.promise_score,
            'metadata': self.metadata,
            'actions': self.actions,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'read': self.read,
            'responded': self.responded,
            'response_action': self.response_action,
            'response_at': self.response_at.isoformat() if self.response_at else None,
            'summarized_message': self.summarized_message
        }
    
    def calculate_autonomy_timeout(self, base_timeout: int = 300) -> int:
        """
        Calculate autonomous action timeout based on urgency and promise.
        
        Higher urgency + higher promise = shorter timeout (act faster)
        Lower urgency + lower promise = longer timeout (wait for user)
        
        Args:
            base_timeout: Base timeout in seconds
            
        Returns:
            Calculated timeout in seconds
        """
        if self.urgency_score is None or self.promise_score is None:
            return base_timeout
        
        # Combine urgency and promise (weighted average)
        # Higher scores = shorter timeout
        combined_score = (self.urgency_score * 0.4 + self.promise_score * 0.6) / 100
        
        # Invert: high score = low timeout
        timeout_multiplier = 1.0 - (combined_score * 0.5)  # Max 50% reduction
        
        calculated_timeout = int(base_timeout * timeout_multiplier)
        
        # Clamp between min and max
        min_timeout = 60  # 1 minute
        max_timeout = 1800  # 30 minutes
        
        return max(min_timeout, min(max_timeout, calculated_timeout))
    
    def should_act_autonomously(self, autonomy_config: Dict) -> bool:
        """
        Determine if system should act autonomously based on urgency + promise.
        
        Args:
            autonomy_config: Configuration dict with thresholds
            
        Returns:
            True if should act autonomously
        """
        if self.urgency_score is None or self.promise_score is None:
            return False
        
        # Combined score (urgency weighted less than promise)
        combined_score = (self.urgency_score * 0.4 + self.promise_score * 0.6)
        
        # Check thresholds
        if combined_score >= autonomy_config.get('full_autonomy_threshold', 90):
            return True
        elif combined_score >= autonomy_config.get('high_autonomy_threshold', 75):
            return True  # Will act after timeout
        elif combined_score >= autonomy_config.get('medium_autonomy_threshold', 60):
            return True  # Will act after longer timeout
        elif combined_score >= autonomy_config.get('low_autonomy_threshold', 45):
            return True  # Will act after very long timeout
        
        return False

