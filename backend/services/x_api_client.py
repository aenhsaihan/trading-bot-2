"""X (Twitter) API client for fetching tweets and user data"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from urllib.parse import unquote
import requests
from src.utils.logger import setup_logger

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.services.x_auth_service import get_x_auth_service


class XAPIClient:
    """Client for interacting with X (Twitter) API v2"""
    
    def __init__(self, user_id: str = "default"):
        """
        Initialize X API client
        
        Args:
            user_id: User identifier for token lookup
        """
        self.logger = setup_logger(f"{__name__}.XAPIClient")
        self.user_id = user_id
        self.auth_service = get_x_auth_service()
        
        # X API v2 base URL
        self.base_url = "https://api.twitter.com/2"
        
        # API Key and Secret (Consumer Keys - for OAuth 1.0a or some endpoints)
        self.api_key = os.getenv("X_API_KEY")
        self.api_secret = os.getenv("X_API_SECRET")
        
        # Bearer token (for read-only endpoints, fallback)
        # URL decode the bearer token if it's URL-encoded
        bearer_token_raw = os.getenv("X_BEARER_TOKEN", "")
        if bearer_token_raw:
            self.bearer_token = unquote(bearer_token_raw)
        else:
            self.bearer_token = None
        
        # Rate limit tracking (simple in-memory for MVP)
        self._rate_limits: Dict[str, Dict] = {}
    
    def _get_access_token(self) -> Optional[str]:
        """Get valid access token (OAuth 2.0)"""
        return self.auth_service.get_valid_access_token(self.user_id)
    
    def _get_bearer_token(self) -> Optional[str]:
        """Get Bearer token (for read-only endpoints)"""
        return self.bearer_token if self.bearer_token else None
    
    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Make authenticated request to X API
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            params: Query parameters
            
        Returns:
            API response JSON
        """
        # Try OAuth 2.0 access token first (for user-specific endpoints)
        # Fallback to Bearer token for read-only endpoints
        access_token = self._get_access_token()
        bearer_token = self._get_bearer_token()
        
        if not access_token and not bearer_token:
            raise ValueError("X account not connected and no Bearer token configured. Please connect your X account or set X_BEARER_TOKEN in .env")
        
        # Use OAuth token if available (for user-specific endpoints), otherwise Bearer token
        token_to_use = access_token if access_token else bearer_token
        token_type = "OAuth 2.0" if access_token else "Bearer"
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {token_to_use}",
            "Content-Type": "application/json"
        }
        
        # Add API Key to headers if available (some endpoints might need it)
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        
        self.logger.debug(f"Using {token_type} token for {endpoint}")
        
        try:
            # Try with SSL verification first
            try:
                if method.upper() == "GET":
                    response = requests.get(url, headers=headers, params=params, verify=True, timeout=30)
                elif method.upper() == "POST":
                    response = requests.post(url, headers=headers, json=params, verify=True, timeout=30)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                response.raise_for_status()
            except requests.exceptions.SSLError as ssl_error:
                # Retry without SSL verification (for development environments)
                self.logger.warning(f"SSL verification failed, retrying without verification: {ssl_error}")
                if method.upper() == "GET":
                    response = requests.get(url, headers=headers, params=params, verify=False, timeout=30)
                elif method.upper() == "POST":
                    response = requests.post(url, headers=headers, json=params, verify=False, timeout=30)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                response.raise_for_status()
            
            # Track rate limits from headers
            if "x-rate-limit-remaining" in response.headers:
                self._rate_limits[endpoint] = {
                    "remaining": int(response.headers.get("x-rate-limit-remaining", 0)),
                    "reset": int(response.headers.get("x-rate-limit-reset", 0))
                }
            
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                self.logger.error("X API authentication failed. Token may be expired.")
                raise ValueError("X authentication expired. Please reconnect your account.")
            elif e.response.status_code == 429:
                self.logger.warning("X API rate limit exceeded")
                raise ValueError("X API rate limit exceeded. Please wait before trying again.")
            else:
                self.logger.error(f"X API request failed: {e}")
                raise ValueError(f"X API request failed: {e}")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"X API request error: {e}")
            raise ValueError(f"X API request error: {e}")
    
    def get_me(self) -> Dict:
        """
        Get authenticated user's profile
        
        Returns:
            User profile data
        """
        response = self._make_request("GET", "/users/me", {
            "user.fields": "id,name,username,description,public_metrics"
        })
        return response.get("data", {})
    
    def get_following(self, user_id: Optional[str] = None, max_results: int = 100) -> List[Dict]:
        """
        Get list of accounts user is following
        
        Args:
            user_id: User ID (default: authenticated user)
            max_results: Maximum number of results (default: 100)
            
        Returns:
            List of user objects
        """
        if not user_id:
            # Get authenticated user's ID
            me = self.get_me()
            user_id = me.get("id")
            self.logger.info(f"Authenticated user ID: {user_id}")
        
        if not user_id:
            raise ValueError("Could not determine user ID")
        
        all_following = []
        next_token = None
        
        try:
            while len(all_following) < max_results:
                params = {
                    "max_results": min(100, max_results - len(all_following)),
                    "user.fields": "id,name,username,description,public_metrics"
                }
                
                if next_token:
                    params["pagination_token"] = next_token
                
                self.logger.info(f"Fetching following for user {user_id} with params: {params}")
                response = self._make_request("GET", f"/users/{user_id}/following", params)
                
                self.logger.info(f"API response keys: {list(response.keys())}")
                self.logger.info(f"API response: {response}")
                
                following = response.get("data", [])
                if following:
                    all_following.extend(following)
                    self.logger.info(f"Got {len(following)} accounts in this batch")
                else:
                    self.logger.warning(f"No accounts in response. Full response: {response}")
                
                # Check for next page
                meta = response.get("meta", {})
                next_token = meta.get("next_token")
                
                # If no data and no next_token, break (might be empty list or error)
                if not following and not next_token:
                    self.logger.warning("No accounts found and no pagination token. Breaking.")
                    break
                
                if not next_token or len(all_following) >= max_results:
                    break
        except Exception as e:
            self.logger.error(f"Error in get_following: {e}", exc_info=True)
            raise
        
        self.logger.info(f"Fetched {len(all_following)} followed accounts total")
        return all_following[:max_results]
    
    def get_user_timeline(self, user_id: str, since_id: Optional[str] = None, max_results: int = 10) -> List[Dict]:
        """
        Get user's recent tweets (timeline)
        
        Args:
            user_id: User ID to fetch timeline for
            since_id: Only return tweets after this tweet ID (for polling)
            max_results: Maximum number of tweets (default: 10, max: 100)
            
        Returns:
            List of tweet objects
        """
        params = {
            "max_results": min(max_results, 100),
            "tweet.fields": "id,text,created_at,author_id,public_metrics,conversation_id",
            "expansions": "author_id",
            "user.fields": "id,name,username"
        }
        
        if since_id:
            params["since_id"] = since_id
        
        response = self._make_request("GET", f"/users/{user_id}/tweets", params)
        
        tweets = response.get("data", [])
        
        # Include author info from expansions
        users = {user["id"]: user for user in response.get("includes", {}).get("users", [])}
        for tweet in tweets:
            author_id = tweet.get("author_id")
            if author_id and author_id in users:
                tweet["author"] = users[author_id]
        
        return tweets
    
    def get_multiple_user_timelines(self, user_ids: List[str], since_ids: Optional[Dict[str, str]] = None) -> Dict[str, List[Dict]]:
        """
        Get timelines for multiple users (for monitoring followed accounts)
        
        Args:
            user_ids: List of user IDs to fetch timelines for
            since_ids: Dictionary mapping user_id -> last_seen_tweet_id (for polling)
            
        Returns:
            Dictionary mapping user_id -> list of new tweets
        """
        if since_ids is None:
            since_ids = {}
        
        all_tweets = {}
        
        for user_id in user_ids:
            try:
                since_id = since_ids.get(user_id)
                tweets = self.get_user_timeline(user_id, since_id=since_id, max_results=10)
                all_tweets[user_id] = tweets
                
                # Small delay to respect rate limits
                import time
                time.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Error fetching timeline for user {user_id}: {e}")
                all_tweets[user_id] = []
        
        return all_tweets
    
    def check_rate_limits(self) -> Dict[str, Dict]:
        """
        Get current rate limit status
        
        Returns:
            Dictionary of endpoint -> rate limit info
        """
        return self._rate_limits.copy()


# Global client instance (per user)
_x_api_clients: Dict[str, XAPIClient] = {}

def get_x_api_client(user_id: str = "default") -> XAPIClient:
    """Get X API client instance for user"""
    if user_id not in _x_api_clients:
        _x_api_clients[user_id] = XAPIClient(user_id=user_id)
    return _x_api_clients[user_id]

