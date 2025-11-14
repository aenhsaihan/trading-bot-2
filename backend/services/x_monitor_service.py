"""X (Twitter) monitoring service for polling followed accounts"""

import os
import sys
import threading
import time
from pathlib import Path
from typing import List, Dict, Optional, Callable
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger
from backend.services.x_api_client import get_x_api_client
from backend.services.x_auth_service import get_x_auth_service


class XMonitorService:
    """Background service for monitoring X accounts and detecting new tweets"""
    
    def __init__(self, user_id: str = "default", poll_interval: int = 300):
        """
        Initialize X monitor service
        
        Args:
            user_id: User identifier
            poll_interval: Polling interval in seconds (default: 300 = 5 minutes)
        """
        self.logger = setup_logger(f"{__name__}.XMonitorService")
        self.user_id = user_id
        self.poll_interval = poll_interval
        
        self.api_client = get_x_api_client(user_id)
        self.auth_service = get_x_auth_service()
        
        # Track last seen tweet ID per user (for polling)
        self._last_tweet_ids: Dict[str, str] = {}
        
        # Track followed accounts
        self._followed_accounts: List[Dict] = []
        self._followed_account_ids: List[str] = []
        
        # Monitoring state
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # Callback for new tweets
        self._on_new_tweet: Optional[Callable[[Dict], None]] = None
    
    def is_connected(self) -> bool:
        """Check if X account is connected"""
        return self.auth_service.is_token_valid(self.user_id)
    
    def set_on_new_tweet_callback(self, callback: Callable[[Dict], None]):
        """
        Set callback function to be called when new tweets are detected
        
        Args:
            callback: Function that takes a tweet dict and processes it
        """
        self._on_new_tweet = callback
    
    def fetch_followed_accounts(self) -> List[Dict]:
        """
        Fetch list of accounts user is following
        
        Returns:
            List of user objects
        """
        if not self.is_connected():
            self.logger.warning("X account not connected, cannot fetch followed accounts")
            return []
        
        try:
            accounts = self.api_client.get_following(max_results=100)
            self._followed_accounts = accounts
            self._followed_account_ids = [acc["id"] for acc in accounts]
            
            self.logger.info(f"Fetched {len(accounts)} followed accounts")
            return accounts
            
        except Exception as e:
            self.logger.error(f"Error fetching followed accounts: {e}")
            return []
    
    def get_followed_accounts(self) -> List[Dict]:
        """Get cached list of followed accounts"""
        return self._followed_accounts.copy()
    
    def poll_for_new_tweets(self) -> List[Dict]:
        """
        Poll all followed accounts for new tweets
        
        Returns:
            List of new tweet dictionaries
        """
        if not self.is_connected():
            self.logger.warning("X account not connected, cannot poll for tweets")
            return []
        
        if not self._followed_account_ids:
            # Fetch followed accounts if not cached
            self.fetch_followed_accounts()
        
        if not self._followed_account_ids:
            self.logger.warning("No followed accounts to monitor")
            return []
        
        all_new_tweets = []
        
        try:
            # Get timelines for all followed accounts
            since_ids = {user_id: self._last_tweet_ids.get(user_id) for user_id in self._followed_account_ids}
            timelines = self.api_client.get_multiple_user_timelines(
                self._followed_account_ids,
                since_ids=since_ids
            )
            
            # Process new tweets
            for user_id, tweets in timelines.items():
                if tweets:
                    # Update last seen tweet ID
                    latest_tweet_id = tweets[0]["id"]  # Tweets are ordered newest first
                    self._last_tweet_ids[user_id] = latest_tweet_id
                    
                    # Add to new tweets list
                    for tweet in tweets:
                        tweet["_monitored_user_id"] = user_id
                        all_new_tweets.append(tweet)
            
            if all_new_tweets:
                self.logger.info(f"Found {len(all_new_tweets)} new tweets from {len(timelines)} accounts")
            
            return all_new_tweets
            
        except Exception as e:
            self.logger.error(f"Error polling for new tweets: {e}")
            return []
    
    def _monitoring_loop(self):
        """Background monitoring loop"""
        self.logger.info(f"Starting X monitoring loop (poll interval: {self.poll_interval}s)")
        
        while self._running:
            try:
                if not self.is_connected():
                    self.logger.warning("X account disconnected, stopping monitoring")
                    self._running = False
                    break
                
                # Poll for new tweets
                new_tweets = self.poll_for_new_tweets()
                
                # Process new tweets via callback
                if new_tweets and self._on_new_tweet:
                    for tweet in new_tweets:
                        try:
                            self._on_new_tweet(tweet)
                        except Exception as e:
                            self.logger.error(f"Error processing tweet {tweet.get('id')}: {e}")
                
                # Wait for next poll
                time.sleep(self.poll_interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                # Continue monitoring even if there's an error
                time.sleep(self.poll_interval)
    
    def start(self):
        """Start background monitoring"""
        if self._running:
            self.logger.warning("Monitoring already running")
            return
        
        if not self.is_connected():
            self.logger.error("Cannot start monitoring: X account not connected")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._thread.start()
        
        self.logger.info("X monitoring service started")
    
    def stop(self):
        """Stop background monitoring"""
        if not self._running:
            return
        
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        
        self.logger.info("X monitoring service stopped")
    
    def is_running(self) -> bool:
        """Check if monitoring is running"""
        return self._running
    
    def get_status(self) -> Dict:
        """
        Get monitoring service status
        
        Returns:
            Status dictionary
        """
        return {
            "connected": self.is_connected(),
            "running": self._running,
            "followed_accounts_count": len(self._followed_account_ids),
            "poll_interval": self.poll_interval,
            "last_tweet_ids_tracked": len(self._last_tweet_ids)
        }


# Global service instance (per user)
_x_monitor_services: Dict[str, XMonitorService] = {}

def get_x_monitor_service(user_id: str = "default", poll_interval: int = 300) -> XMonitorService:
    """Get X monitor service instance for user"""
    if user_id not in _x_monitor_services:
        _x_monitor_services[user_id] = XMonitorService(user_id=user_id, poll_interval=poll_interval)
    return _x_monitor_services[user_id]

