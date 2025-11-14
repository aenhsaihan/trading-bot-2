"""News monitoring service - polls CryptoCompare News API"""

import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Optional, Callable
from datetime import datetime
from threading import Thread, Event
from src.utils.logger import setup_logger

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.services.news_api_client import get_news_api_client
from backend.services.news_notification_converter import get_news_notification_converter


class NewsMonitor:
    """
    News monitoring service that polls CryptoCompare News API.
    
    Monitors crypto news and converts articles to notifications.
    """
    
    def __init__(self, poll_interval: int = 300):
        """
        Initialize news monitor
        
        Args:
            poll_interval: How often to poll for new news (seconds, default: 5 minutes)
        """
        self.logger = setup_logger(f"{__name__}.NewsMonitor")
        self.poll_interval = poll_interval
        
        # Get API client
        self.api_client = get_news_api_client()
        
        # Get notification converter
        self.converter = get_news_notification_converter()
        
        # Categories to monitor (can be configured via env var)
        categories_str = os.getenv("NEWS_CATEGORIES", "")
        if categories_str:
            self.monitored_categories = [cat.strip() for cat in categories_str.split(",") if cat.strip()]
        else:
            # Default: monitor all categories
            self.monitored_categories = []
        
        # Language preference
        self.lang = os.getenv("NEWS_LANG", "EN")
        
        # Track last seen article IDs (for deduplication)
        self.last_seen_articles: List[str] = []
        self.max_tracked_articles = 100  # Keep last 100 article IDs
        
        # Callback for new articles (will be set by integration)
        self.on_new_article: Optional[Callable[[Dict], None]] = None
        
        # Monitoring state
        self._monitoring = False
        self._monitor_thread: Optional[Thread] = None
        self._stop_event = Event()
    
    def start(self):
        """Start monitoring"""
        if self._monitoring:
            self.logger.warning("News monitoring already started")
            return
        
        self._monitoring = True
        self._stop_event.clear()
        self._monitor_thread = Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        
        categories_str = ", ".join(self.monitored_categories) if self.monitored_categories else "all categories"
        self.logger.info(f"Started news monitoring (poll interval: {self.poll_interval}s, categories: {categories_str})")
    
    def stop(self):
        """Stop monitoring"""
        if not self._monitoring:
            return
        
        self._monitoring = False
        self._stop_event.set()
        
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        
        self.logger.info("Stopped news monitoring")
    
    def is_monitoring(self) -> bool:
        """Check if monitoring is active"""
        return self._monitoring
    
    def get_status(self) -> Dict:
        """Get monitoring status"""
        return {
            "monitoring": self._monitoring,
            "poll_interval": self.poll_interval,
            "categories": self.monitored_categories,
            "lang": self.lang,
            "api_key_configured": bool(self.api_client.api_key),
            "tracked_articles_count": len(self.last_seen_articles)
        }
    
    def _fetch_latest_news(self, max_items: int = 50) -> List[Dict]:
        """
        Fetch latest news articles
        
        Args:
            max_items: Maximum number of articles to fetch
            
        Returns:
            List of news article objects
        """
        try:
            if self.monitored_categories:
                # Fetch news for specific categories
                all_articles = []
                for category in self.monitored_categories:
                    try:
                        articles = self.api_client.get_news_by_category(
                            category=category,
                            lang=self.lang,
                            max_items=max_items
                        )
                        all_articles.extend(articles)
                    except Exception as e:
                        self.logger.error(f"Error fetching news for category {category}: {e}")
                
                # Remove duplicates by article ID
                seen_ids = set()
                unique_articles = []
                for article in all_articles:
                    article_id = article.get("id", "")
                    if article_id and article_id not in seen_ids:
                        seen_ids.add(article_id)
                        unique_articles.append(article)
                
                return unique_articles
            else:
                # Fetch all latest news
                return self.api_client.get_latest_news(
                    lang=self.lang,
                    max_items=max_items
                )
        except Exception as e:
            self.logger.error(f"Error fetching news: {e}")
            return []
    
    def _process_articles(self, articles: List[Dict]):
        """
        Process fetched articles and trigger notifications
        
        Args:
            articles: List of news article objects
        """
        if not articles:
            return
        
        # Sort by published_on (newest first)
        sorted_articles = sorted(
            articles,
            key=lambda a: a.get("published_on", 0),
            reverse=True
        )
        
        new_articles = []
        for article in sorted_articles:
            article_id = article.get("id", "")
            
            # Skip if we've already seen this article
            if article_id in self.last_seen_articles:
                continue
            
            new_articles.append(article)
        
        # Update last seen articles list
        for article in new_articles:
            article_id = article.get("id", "")
            if article_id:
                self.last_seen_articles.append(article_id)
        
        # Keep only last N article IDs
        if len(self.last_seen_articles) > self.max_tracked_articles:
            self.last_seen_articles = self.last_seen_articles[-self.max_tracked_articles:]
        
        # Process new articles (oldest first, so notifications appear in chronological order)
        for article in reversed(new_articles):
            try:
                # Convert to notification
                notification_data = self.converter.convert_news_to_notification(article)
                
                # Trigger callback
                if self.on_new_article:
                    self.on_new_article(notification_data)
                
                self.logger.info(f"Processed new article: {article.get('title', 'N/A')[:50]}...")
            except Exception as e:
                self.logger.error(f"Error processing article {article.get('id', 'unknown')}: {e}", exc_info=True)
    
    def _monitor_loop(self):
        """Main monitoring loop (runs in background thread)"""
        self.logger.info(f"Starting news monitoring loop (poll interval: {self.poll_interval}s)")
        
        while not self._stop_event.is_set():
            try:
                # Fetch latest news
                articles = self._fetch_latest_news(max_items=50)
                
                if articles:
                    self._process_articles(articles)
                
                # Wait for next poll interval
                self._stop_event.wait(self.poll_interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                time.sleep(10)  # Wait a bit before retrying
        
        self.logger.info("News monitoring loop stopped")


# Global monitor instance
_news_monitor = None

def get_news_monitor() -> NewsMonitor:
    """Get global news monitor instance"""
    global _news_monitor
    if _news_monitor is None:
        _news_monitor = NewsMonitor()
    return _news_monitor

