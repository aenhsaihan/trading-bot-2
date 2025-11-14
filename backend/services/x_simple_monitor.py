"""Simplified X monitoring service for Free tier - uses Bearer token and manual account list"""

import os
import sys
import time
import re
from pathlib import Path
from typing import List, Dict, Optional, Callable
from datetime import datetime
from threading import Thread, Event
from src.utils.logger import setup_logger

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.services.x_api_client import XAPIClient
from backend.services.x_notification_converter import get_x_notification_converter


class XSimpleMonitor:
    """
    Simplified X monitoring service for Free tier.
    
    Uses Bearer token to fetch tweets from manually configured accounts.
    Works around Free tier limitations by not requiring OAuth or /users/:id/following endpoint.
    """
    
    def __init__(self, poll_interval: int = 300):
        """
        Initialize simple X monitor
        
        Args:
            poll_interval: How often to poll for new tweets (seconds, default: 5 minutes)
        """
        self.logger = setup_logger(f"{__name__}.XSimpleMonitor")
        self.poll_interval = poll_interval
        
        # Get Bearer token from env
        bearer_token = os.getenv("X_BEARER_TOKEN", "")
        if not bearer_token:
            self.logger.warning("X_BEARER_TOKEN not set. Monitoring will not work.")
            self.api_client = None
        else:
            # Create API client (will use Bearer token)
            self.api_client = XAPIClient(user_id="default")
        
        # Get notification converter
        self.converter = get_x_notification_converter()
        
        # Manually configured accounts to monitor (username or user_id)
        # Format: ["username1", "username2"] or ["user_id1", "user_id2"]
        # Can be set via environment variable or config
        accounts_str = os.getenv("X_MONITOR_ACCOUNTS", "")
        if accounts_str:
            self.monitored_accounts = [acc.strip() for acc in accounts_str.split(",") if acc.strip()]
        else:
            self.monitored_accounts = []
        
        # Track last seen tweet IDs per account (for deduplication)
        self.last_seen_tweets: Dict[str, Optional[str]] = {}
        
        # Callback for new tweets (will be set by integration service)
        self.on_new_tweet: Optional[Callable[[Dict], None]] = None
        
        # Monitoring state
        self._monitoring = False
        self._monitor_thread: Optional[Thread] = None
        self._stop_event = Event()
        
        # User ID cache (username -> user_id mapping)
        self._user_id_cache: Dict[str, str] = {}
    
    def add_account(self, username_or_id: str):
        """
        Add an account to monitor
        
        Args:
            username_or_id: X username (without @) or user ID
        """
        if username_or_id not in self.monitored_accounts:
            self.monitored_accounts.append(username_or_id)
            self.logger.info(f"Added account to monitor: {username_or_id}")
    
    def remove_account(self, username_or_id: str):
        """Remove an account from monitoring"""
        if username_or_id in self.monitored_accounts:
            self.monitored_accounts.remove(username_or_id)
            if username_or_id in self.last_seen_tweets:
                del self.last_seen_tweets[username_or_id]
            if username_or_id in self._user_id_cache:
                del self._user_id_cache[username_or_id]
            self.logger.info(f"Removed account from monitoring: {username_or_id}")
    
    def get_accounts(self) -> List[str]:
        """Get list of monitored accounts"""
        return self.monitored_accounts.copy()
    
    def _resolve_user_id(self, username_or_id: str) -> Optional[str]:
        """
        Resolve username to user ID (or return if already an ID)
        
        Args:
            username_or_id: Username (without @) or user ID
            
        Returns:
            User ID or None if not found
        """
        # If it's already in cache, return it
        if username_or_id in self._user_id_cache:
            return self._user_id_cache[username_or_id]
        
        # If it looks like a numeric ID, assume it's already an ID
        if username_or_id.isdigit():
            self._user_id_cache[username_or_id] = username_or_id
            return username_or_id
        
        # Try to resolve username to user ID using Bearer token
        if not self.api_client:
            return None
        
        try:
            # Use /2/users/by/username/:username endpoint
            response = self.api_client._make_request(
                "GET",
                f"/users/by/username/{username_or_id}",
                {"user.fields": "id"}
            )
            
            user_data = response.get("data", {})
            user_id = user_data.get("id")
            
            if user_id:
                self._user_id_cache[username_or_id] = user_id
                self.logger.debug(f"Resolved username {username_or_id} to user_id {user_id}")
                return user_id
        except ValueError as e:
            error_msg = str(e)
            # If rate limited, log but don't fail - will retry later
            if "rate limit" in error_msg.lower():
                self.logger.warning(f"Rate limited while resolving {username_or_id}. Will retry later: {e}")
                # Don't cache failed resolution, so we'll try again
            else:
                self.logger.warning(f"Could not resolve username {username_or_id} to user_id: {e}")
        except Exception as e:
            self.logger.warning(f"Could not resolve username {username_or_id} to user_id: {e}")
        
        return None
    
    def _fetch_tweets_for_account(self, username_or_id: str) -> List[Dict]:
        """
        Fetch recent tweets for an account
        
        Args:
            username_or_id: Username or user ID
            
        Returns:
            List of tweet objects
        """
        if not self.api_client:
            return []
        
        # Resolve to user ID
        user_id = self._resolve_user_id(username_or_id)
        if not user_id:
            # If it's a username and resolution failed (possibly rate limited), skip this cycle
            # Will retry on next poll cycle
            if not username_or_id.isdigit():
                self.logger.debug(f"Could not resolve {username_or_id} to user_id (may be rate limited). Will retry later.")
            else:
                self.logger.warning(f"Could not resolve {username_or_id} to user_id")
            return []
        
        # Get last seen tweet ID for this account
        since_id = self.last_seen_tweets.get(username_or_id)
        
        try:
            # Fetch tweets using Bearer token
            tweets = self.api_client.get_user_timeline(
                user_id=user_id,
                since_id=since_id,  # Only get tweets after last seen
                max_results=10  # Get up to 10 new tweets
            )
            
            return tweets
        except Exception as e:
            self.logger.error(f"Error fetching tweets for {username_or_id}: {e}")
            return []
    
    def _process_tweets(self, username_or_id: str, tweets: List[Dict]):
        """
        Process fetched tweets and trigger notifications
        
        Args:
            username_or_id: Account identifier
            tweets: List of tweet objects
        """
        if not tweets:
            return
        
        # Sort by created_at (newest first) and process
        sorted_tweets = sorted(
            tweets,
            key=lambda t: t.get("created_at", ""),
            reverse=True
        )
        
        new_tweets = []
        for tweet in sorted_tweets:
            tweet_id = tweet.get("id")
            
            # Skip if we've already seen this tweet
            if tweet_id == self.last_seen_tweets.get(username_or_id):
                break
            
            new_tweets.append(tweet)
        
        # Update last seen tweet ID (most recent)
        if new_tweets:
            latest_tweet_id = new_tweets[0].get("id")
            self.last_seen_tweets[username_or_id] = latest_tweet_id
        
        # Process new tweets (oldest first, so notifications appear in chronological order)
        for tweet in reversed(new_tweets):
            try:
                # Get author info from tweet
                author = tweet.get("author", {})
                
                # Convert to notification
                notification_data = self.converter.convert_tweet_to_notification(
                    tweet=tweet,
                    author=author
                )
                
                # Trigger callback
                if self.on_new_tweet:
                    self.on_new_tweet(notification_data)
                
                self.logger.info(f"Processed new tweet from {username_or_id}: {tweet.get('id')}")
            except Exception as e:
                self.logger.error(f"Error processing tweet {tweet.get('id')}: {e}", exc_info=True)
    
    def _monitor_loop(self):
        """Main monitoring loop (runs in background thread)"""
        self.logger.info(f"Starting X monitoring loop (poll interval: {self.poll_interval}s)")
        
        while not self._stop_event.is_set():
            try:
                if not self.monitored_accounts:
                    self.logger.debug("No accounts to monitor, waiting...")
                    time.sleep(10)
                    continue
                
                # Poll each account with rate limit handling
                for account in self.monitored_accounts:
                    if self._stop_event.is_set():
                        break
                    
                    try:
                        tweets = self._fetch_tweets_for_account(account)
                        if tweets:
                            self._process_tweets(account, tweets)
                    except ValueError as e:
                        error_msg = str(e)
                        # Check if it's a rate limit error
                        if "rate limit" in error_msg.lower():
                            # Extract wait time if available
                            if "reset in" in error_msg.lower():
                                try:
                                    # Try to extract seconds from error message
                                    match = re.search(r'reset in (\d+) seconds', error_msg.lower())
                                    if match:
                                        wait_seconds = int(match.group(1))
                                        self.logger.warning(f"Rate limited for {account}. Waiting {wait_seconds}s before continuing with other accounts")
                                        # Wait a bit, but not the full time (other accounts might work)
                                        time.sleep(min(wait_seconds // len(self.monitored_accounts), 30))
                                except:
                                    pass
                            self.logger.warning(f"Rate limit hit while monitoring {account}. Will retry on next poll cycle.")
                        else:
                            self.logger.error(f"Error monitoring account {account}: {e}")
                    except Exception as e:
                        self.logger.error(f"Error monitoring account {account}: {e}")
                    
                    # Delay between accounts to respect rate limits
                    # Increase delay if we have many accounts
                    delay = max(2, min(5, len(self.monitored_accounts) * 0.5))
                    time.sleep(delay)
                
                # Wait for next poll interval
                self._stop_event.wait(self.poll_interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                time.sleep(10)  # Wait a bit before retrying
        
        self.logger.info("Monitoring loop stopped")
    
    def start(self):
        """Start monitoring"""
        if self._monitoring:
            self.logger.warning("Monitoring already started")
            return
        
        if not self.api_client:
            self.logger.error("Cannot start monitoring: X_BEARER_TOKEN not configured")
            return
        
        if not self.monitored_accounts:
            self.logger.warning("No accounts configured to monitor. Set X_MONITOR_ACCOUNTS env var or use add_account()")
            return
        
        self._monitoring = True
        self._stop_event.clear()
        self._monitor_thread = Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        self.logger.info(f"Started monitoring {len(self.monitored_accounts)} accounts")
    
    def stop(self):
        """Stop monitoring"""
        if not self._monitoring:
            return
        
        self._monitoring = False
        self._stop_event.set()
        
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        
        self.logger.info("Stopped monitoring")
    
    def is_monitoring(self) -> bool:
        """Check if monitoring is active"""
        return self._monitoring
    
    def get_status(self) -> Dict:
        """Get monitoring status"""
        return {
            "monitoring": self._monitoring,
            "accounts_count": len(self.monitored_accounts),
            "accounts": self.monitored_accounts,
            "poll_interval": self.poll_interval,
            "bearer_token_configured": self.api_client is not None
        }


# Global monitor instance
_x_simple_monitor = None

def get_x_simple_monitor() -> XSimpleMonitor:
    """Get global X simple monitor instance"""
    global _x_simple_monitor
    if _x_simple_monitor is None:
        _x_simple_monitor = XSimpleMonitor()
    return _x_simple_monitor

