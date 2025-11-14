"""Convert CryptoCompare news articles to notifications"""

import sys
import re
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime
from src.utils.logger import setup_logger

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.notifications.notification_types import NotificationType, NotificationPriority, NotificationSource


class NewsNotificationConverter:
    """Convert news articles to notifications"""
    
    # Common crypto symbols to detect in news
    CRYPTO_SYMBOLS = [
        "BTC", "ETH", "BNB", "SOL", "ADA", "XRP", "DOT", "DOGE", "MATIC",
        "AVAX", "LINK", "UNI", "ATOM", "ETC", "LTC", "BCH", "XLM", "ALGO",
        "FIL", "TRX", "EOS", "AAVE", "MKR", "COMP", "YFI", "SNX", "SUSHI",
        "SHIB", "PEPE", "FLOKI", "WIF", "BONK", "ARB", "OP", "APT", "SUI",
        "TIA", "INJ", "SEI", "RUNE", "NEAR", "FTM", "ICP", "HBAR", "VET"
    ]
    
    # Coin name to symbol mapping (for detecting coin names in text)
    COIN_NAME_TO_SYMBOL = {
        "bitcoin": "BTC",
        "ethereum": "ETH",
        "binance coin": "BNB",
        "binance": "BNB",
        "solana": "SOL",
        "cardano": "ADA",
        "ripple": "XRP",
        "polkadot": "DOT",
        "dogecoin": "DOGE",
        "polygon": "MATIC",
        "avalanche": "AVAX",
        "chainlink": "LINK",
        "uniswap": "UNI",
        "cosmos": "ATOM",
        "ethereum classic": "ETC",
        "litecoin": "LTC",
        "bitcoin cash": "BCH",
        "stellar": "XLM",
        "algorand": "ALGO",
        "filecoin": "FIL",
        "tron": "TRX",
        "eos": "EOS",
        "aave": "AAVE",
        "maker": "MKR",
        "compound": "COMP",
        "yearn finance": "YFI",
        "synthetix": "SNX",
        "sushi": "SUSHI",
        "shiba inu": "SHIB",
        "pepe": "PEPE",
        "floki": "FLOKI",
        "dogwifhat": "WIF",
        "bonk": "BONK",
        "arbitrum": "ARB",
        "optimism": "OP",
        "aptos": "APT",
        "sui": "SUI",
        "celestia": "TIA",
        "injective": "INJ",
        "sei": "SEI",
        "thorchain": "RUNE",
        "near": "NEAR",
        "fantom": "FTM",
        "internet computer": "ICP",
        "hedera": "HBAR",
        "vechain": "VET"
    }
    
    # Keywords that indicate high priority news
    HIGH_PRIORITY_KEYWORDS = [
        "hack", "exploit", "security breach", "regulation", "ban", "approval",
        "etf", "adoption", "partnership", "listing", "delisting", "crash",
        "surge", "rally", "breakthrough", "milestone", "launch", "mainnet"
    ]
    
    # Keywords that indicate medium priority
    MEDIUM_PRIORITY_KEYWORDS = [
        "update", "announcement", "feature", "upgrade", "fork", "airdrop",
        "integration", "collaboration", "roadmap", "development"
    ]
    
    def __init__(self):
        """Initialize news notification converter"""
        self.logger = setup_logger(f"{__name__}.NewsNotificationConverter")
    
    def extract_symbols(self, text: str) -> List[str]:
        """
        Extract crypto symbols from news text
        
        Args:
            text: News article text (title + body)
            
        Returns:
            List of detected symbols
        """
        text_upper = text.upper()
        text_lower = text.lower()
        detected_symbols = []
        seen_symbols = set()
        
        # First, check for symbol abbreviations (BTC, ETH, etc.)
        for symbol in self.CRYPTO_SYMBOLS:
            # Look for symbol as whole word (not part of another word)
            pattern = r'\b' + re.escape(symbol) + r'\b'
            if re.search(pattern, text_upper):
                if symbol not in seen_symbols:
                    detected_symbols.append(symbol)
                    seen_symbols.add(symbol)
        
        # Then, check for coin names (Bitcoin, Ethereum, Shiba Inu, etc.)
        for coin_name, symbol in self.COIN_NAME_TO_SYMBOL.items():
            # Look for coin name as whole word or phrase
            # Handle multi-word names like "Shiba Inu"
            if ' ' in coin_name:
                # Multi-word: look for the phrase
                pattern = r'\b' + re.escape(coin_name) + r'\b'
            else:
                # Single word: look for whole word
                pattern = r'\b' + re.escape(coin_name) + r'\b'
            
            if re.search(pattern, text_lower):
                if symbol not in seen_symbols:
                    detected_symbols.append(symbol)
                    seen_symbols.add(symbol)
        
        return detected_symbols
    
    def determine_priority(self, article: Dict) -> NotificationPriority:
        """
        Determine notification priority based on article content
        
        Args:
            article: News article object
            
        Returns:
            Notification priority
        """
        # Combine title and body for analysis
        title = article.get("title", "").lower()
        body = article.get("body", "").lower()
        combined_text = f"{title} {body}"
        
        # Check for high priority keywords
        for keyword in self.HIGH_PRIORITY_KEYWORDS:
            if keyword.lower() in combined_text:
                return NotificationPriority.HIGH
        
        # Check for medium priority keywords
        for keyword in self.MEDIUM_PRIORITY_KEYWORDS:
            if keyword.lower() in combined_text:
                return NotificationPriority.MEDIUM
        
        # Check categories - some categories are more important
        categories = article.get("categories", "")
        if isinstance(categories, str):
            categories = categories.split("|") if categories else []
        
        # High priority categories
        high_priority_categories = ["BTC", "ETH", "Regulation", "Security"]
        if any(cat in categories for cat in high_priority_categories):
            return NotificationPriority.HIGH
        
        # Default to medium (news is generally important)
        return NotificationPriority.MEDIUM
    
    def convert_news_to_notification(self, article: Dict) -> Dict:
        """
        Convert a news article to notification data
        
        Args:
            article: News article object from CryptoCompare API
            
        Returns:
            Dictionary with notification data
        """
        title = article.get("title", "Crypto News")
        body = article.get("body", "")
        url = article.get("url", "")
        source = article.get("source", "CryptoCompare")
        published_on = article.get("published_on", 0)
        
        # Extract symbols from title and body
        symbols = self.extract_symbols(f"{title} {body}")
        primary_symbol = symbols[0] if symbols else None
        
        # Determine priority
        priority = self.determine_priority(article)
        
        # Create notification message
        # Truncate body if too long
        message_body = body[:500] + "..." if len(body) > 500 else body
        message = f"{message_body}\n\nSource: {source}"
        if url:
            message += f"\nRead more: {url}"
        
        # Calculate scores based on priority and content
        confidence_score = 70.0  # News is generally reliable
        urgency_score = 60.0 if priority == NotificationPriority.HIGH else 40.0
        promise_score = 50.0  # News can indicate opportunities
        
        # Adjust scores based on keywords
        combined_text = f"{title} {body}".lower()
        if any(kw in combined_text for kw in ["surge", "rally", "breakthrough", "adoption"]):
            promise_score = 70.0
        if any(kw in combined_text for kw in ["hack", "exploit", "crash", "ban"]):
            urgency_score = 80.0
            promise_score = 30.0  # Negative news
        
        # Parse published time
        expires_at = None
        if published_on:
            try:
                # CryptoCompare uses Unix timestamp
                published_dt = datetime.fromtimestamp(published_on)
                # News expires after 24 hours
                from datetime import timedelta
                expires_at = published_dt + timedelta(hours=24)
            except (ValueError, OSError):
                pass
        
        # Build metadata
        metadata = {
            "article_id": article.get("id", ""),
            "url": url,
            "source": source,
            "published_on": published_on,
            "categories": article.get("categories", ""),
            "tags": article.get("tags", ""),
            "image_url": article.get("imageurl", ""),
            "detected_symbols": symbols
        }
        
        return {
            "notification_type": NotificationType.NEWS_EVENT.value,
            "priority": priority.value,
            "title": title,
            "message": message,
            "source": NotificationSource.NEWS.value,
            "symbol": primary_symbol,
            "confidence_score": confidence_score,
            "urgency_score": urgency_score,
            "promise_score": promise_score,
            "metadata": metadata,
            "expires_at": expires_at.isoformat() if expires_at else None
        }


# Global converter instance
_news_converter = None

def get_news_notification_converter() -> NewsNotificationConverter:
    """Get global news notification converter instance"""
    global _news_converter
    if _news_converter is None:
        _news_converter = NewsNotificationConverter()
    return _news_converter

