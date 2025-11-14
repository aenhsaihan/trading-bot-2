"""Notification message summarization service - StarCraft-style concise messages"""

import sys
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
import hashlib
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.services.ai_service import AIService
from src.utils.logger import setup_logger


class NotificationMessageService:
    """Service for generating concise, StarCraft-style notification messages"""
    
    def __init__(self, ai_service: Optional[AIService] = None):
        """
        Initialize notification message service.
        
        Args:
            ai_service: Optional AI service instance (creates new if not provided)
        """
        self.logger = setup_logger(f"{__name__}.NotificationMessageService")
        self.ai_service = ai_service or AIService()
        
        # Simple in-memory cache (key: hash of notification data, value: summarized message)
        # In production, consider using Redis or similar
        self._cache: Dict[str, str] = {}
        self._cache_max_size = 1000  # Limit cache size
        
        # Message length targets based on priority
        self._message_lengths = {
            'critical': (10, 15),  # 10-15 words
            'high': (15, 20),      # 15-20 words
            'medium': (20, 25),    # 20-25 words
            'low': (25, 30),       # 25-30 words
            'info': (20, 30)       # 20-30 words
        }
    
    def _get_cache_key(self, notification: Dict) -> str:
        """
        Generate cache key from notification data.
        
        Args:
            notification: Notification dictionary
            
        Returns:
            Cache key string
        """
        # Use key fields that determine the message content
        cache_data = {
            'type': notification.get('type'),
            'priority': notification.get('priority'),
            'title': notification.get('title'),
            'message': notification.get('message'),
            'symbol': notification.get('symbol'),
            'confidence_score': notification.get('confidence_score'),
            'urgency_score': notification.get('urgency_score'),
            'promise_score': notification.get('promise_score')
        }
        
        # Create hash of the data
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()
    
    def _get_message_length_target(self, priority: str) -> tuple:
        """
        Get target word count range for message based on priority.
        
        Args:
            priority: Notification priority level
            
        Returns:
            Tuple of (min_words, max_words)
        """
        return self._message_lengths.get(priority.lower(), (20, 30))
    
    def _get_summarization_prompt(self, notification: Dict) -> str:
        """
        Generate AI prompt for message summarization.
        
        Args:
            notification: Notification dictionary
            
        Returns:
            Prompt string for AI
        """
        priority = notification.get('priority', 'medium').lower()
        min_words, max_words = self._get_message_length_target(priority)
        
        notification_type = notification.get('type', 'unknown')
        symbol = notification.get('symbol', '')
        symbol_text = f" for {symbol}" if symbol else ""
        
        prompt = f"""Summarize this trading notification into a concise, StarCraft-style tactical message.

TONE REQUIREMENTS:
- Stern but professional (like a military commander reporting to general)
- Calming and controlled (never panicked)
- Direct and actionable
- Get to the point quickly

NOTIFICATION DATA:
Title: {notification.get('title', 'N/A')}
Type: {notification_type}
Message: {notification.get('message', 'N/A')}
Symbol: {symbol or 'N/A'}
Confidence: {notification.get('confidence_score', 'N/A')}%
Urgency: {notification.get('urgency_score', 'N/A')}%
Priority: {priority}

REQUIREMENTS:
- Generate a message between {min_words} and {max_words} words
- Focus on the most critical information
- Include actionable insight (what to do)
- Use tactical/combat terminology appropriately
- Be concise and impactful

EXAMPLES:
- "BTC breaking resistance. High confidence. Volume surge detected."
- "Position under attack. Stop loss 0.5% away. Immediate action required."
- "Long position approaching stop loss. 1.2% remaining. Consider adjustment."

Generate ONLY the summarized message, nothing else:"""
        
        return prompt
    
    def summarize(self, notification: Dict) -> str:
        """
        Generate concise, StarCraft-style summarized message for notification.
        
        Args:
            notification: Notification dictionary (from Notification.to_dict() or API response)
            
        Returns:
            Summarized message string
        """
        # Check cache first
        cache_key = self._get_cache_key(notification)
        if cache_key in self._cache:
            self.logger.debug(f"Using cached summary for notification {notification.get('id', 'unknown')}")
            return self._cache[cache_key]
        
        # If AI service not available, fallback to simple truncation
        if not self.ai_service.is_enabled():
            self.logger.warning("AI service not available, using fallback summarization")
            return self._fallback_summarize(notification)
        
        try:
            # Generate prompt
            prompt = self._get_summarization_prompt(notification)
            
            # Call AI service
            summarized = self.ai_service.chat(
                user_message=prompt,
                conversation_history=[],
                context={'selected_notification': notification}
            )
            
            # Clean up the response (remove any extra formatting)
            summarized = summarized.strip()
            
            # Remove quotes if AI wrapped the message in them
            if (summarized.startswith('"') and summarized.endswith('"')) or \
               (summarized.startswith("'") and summarized.endswith("'")):
                summarized = summarized[1:-1]
            
            # Cache the result
            if len(self._cache) >= self._cache_max_size:
                # Remove oldest entry (simple FIFO - in production use LRU)
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
            
            self._cache[cache_key] = summarized
            
            self.logger.info(f"Generated summary for notification {notification.get('id', 'unknown')}: {summarized[:50]}...")
            return summarized
            
        except Exception as e:
            self.logger.error(f"Error generating AI summary: {e}", exc_info=True)
            # Fallback to simple summarization
            return self._fallback_summarize(notification)
    
    def _fallback_summarize(self, notification: Dict) -> str:
        """
        Fallback summarization when AI is not available.
        Simple truncation and formatting.
        
        Args:
            notification: Notification dictionary
            
        Returns:
            Fallback summarized message
        """
        priority = notification.get('priority', 'medium').lower()
        min_words, max_words = self._get_message_length_target(priority)
        
        # Use title or message, whichever is shorter
        source_text = notification.get('title', '') or notification.get('message', '')
        
        # Simple word-based truncation
        words = source_text.split()
        if len(words) > max_words:
            words = words[:max_words]
            # Add ellipsis if truncated
            if len(source_text.split()) > max_words:
                words[-1] = words[-1] + "..."
        
        symbol = notification.get('symbol', '')
        if symbol and symbol not in ' '.join(words):
            # Prepend symbol if not already in message
            return f"{symbol}: {' '.join(words)}"
        
        return ' '.join(words)
    
    def clear_cache(self):
        """Clear the summarization cache"""
        self._cache.clear()
        self.logger.info("Summarization cache cleared")
    
    def get_cache_size(self) -> int:
        """Get current cache size"""
        return len(self._cache)

