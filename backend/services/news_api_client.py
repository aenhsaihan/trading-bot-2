"""CryptoCompare News API client"""

import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import requests
from src.utils.logger import setup_logger

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class NewsAPIClient:
    """Client for CryptoCompare News API"""
    
    def __init__(self):
        """Initialize News API client"""
        self.logger = setup_logger(f"{__name__}.NewsAPIClient")
        
        # CryptoCompare News API base URL
        self.base_url = "https://min-api.cryptocompare.com/data/v2"
        
        # API Key (optional, but recommended for higher rate limits)
        self.api_key = os.getenv("CRYPTOCOMPARE_API_KEY", "")
        
        # Rate limit tracking
        self._rate_limits: Dict[str, Dict] = {}
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Make request to CryptoCompare News API
        
        Args:
            endpoint: API endpoint (without base URL)
            params: Query parameters
            
        Returns:
            API response JSON
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # Add API key to params if available
        if params is None:
            params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        try:
            # Try with SSL verification first
            try:
                response = requests.get(url, params=params, verify=True, timeout=30)
                response.raise_for_status()
            except requests.exceptions.SSLError as ssl_error:
                # Retry without SSL verification (for development environments)
                self.logger.warning(f"SSL verification failed, retrying without verification: {ssl_error}")
                response = requests.get(url, params=params, verify=False, timeout=30)
                response.raise_for_status()
            
            # Track rate limits from headers (if available)
            if "x-ratelimit-remaining" in response.headers:
                self._rate_limits[endpoint] = {
                    "remaining": int(response.headers.get("x-ratelimit-remaining", 0)),
                    "reset": int(response.headers.get("x-ratelimit-reset", 0))
                }
            
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                self.logger.warning("CryptoCompare API rate limit exceeded")
                raise ValueError("CryptoCompare API rate limit exceeded. Please wait before trying again.")
            else:
                self.logger.error(f"CryptoCompare API request failed: {e}")
                raise ValueError(f"CryptoCompare API request failed: {e}")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"CryptoCompare API request error: {e}")
            raise ValueError(f"CryptoCompare API request error: {e}")
    
    def get_latest_news(
        self,
        categories: Optional[List[str]] = None,
        exclude_categories: Optional[List[str]] = None,
        lang: str = "EN",
        max_items: int = 50
    ) -> List[Dict]:
        """
        Get latest crypto news articles
        
        Args:
            categories: List of categories to include (e.g., ["BTC", "ETH"])
            exclude_categories: List of categories to exclude
            lang: Language code (default: EN)
            max_items: Maximum number of items to return (default: 50, max: 200)
            
        Returns:
            List of news article objects
        """
        params = {
            "lang": lang,
            "sortOrder": "latest"  # Get latest news first
        }
        
        if categories:
            params["categories"] = ",".join(categories)
        if exclude_categories:
            params["excludeCategories"] = ",".join(exclude_categories)
        
        # Limit max items
        params["limit"] = min(max_items, 200)
        
        response = self._make_request("/news/", params)
        
        # CryptoCompare returns data in response["Data"]
        articles = response.get("Data", [])
        
        return articles
    
    def get_news_by_category(
        self,
        category: str,
        lang: str = "EN",
        max_items: int = 50
    ) -> List[Dict]:
        """
        Get news for a specific category
        
        Args:
            category: Category name (e.g., "BTC", "ETH", "General")
            lang: Language code
            max_items: Maximum number of items
            
        Returns:
            List of news article objects
        """
        return self.get_latest_news(
            categories=[category],
            lang=lang,
            max_items=max_items
        )
    
    def check_rate_limits(self) -> Dict[str, Dict]:
        """
        Get current rate limit status
        
        Returns:
            Dictionary of endpoint -> rate limit info
        """
        return self._rate_limits.copy()


# Global client instance
_news_api_client = None

def get_news_api_client() -> NewsAPIClient:
    """Get global News API client instance"""
    global _news_api_client
    if _news_api_client is None:
        _news_api_client = NewsAPIClient()
    return _news_api_client

