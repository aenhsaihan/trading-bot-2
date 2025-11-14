"""X (Twitter) OAuth authentication service"""

import os
import secrets
import hashlib
import base64
import sys
from pathlib import Path
from typing import Optional, Dict
from urllib.parse import urlencode, parse_qs
import requests
from src.utils.logger import setup_logger

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class XAuthService:
    """Service for handling X (Twitter) OAuth 2.0 authentication"""
    
    def __init__(self):
        """Initialize X auth service"""
        self.logger = setup_logger(f"{__name__}.XAuthService")
        
        # X API credentials from environment
        self.client_id = os.getenv("X_CLIENT_ID")
        self.client_secret = os.getenv("X_CLIENT_SECRET")
        self.redirect_uri = os.getenv("X_REDIRECT_URI", "http://localhost:8000/api/x/callback")
        
        # X OAuth endpoints
        self.authorize_url = "https://twitter.com/i/oauth2/authorize"
        self.token_url = "https://api.twitter.com/2/oauth2/token"
        
        # In-memory storage for OAuth state and tokens (in production, use database)
        self._oauth_states: Dict[str, str] = {}  # state -> code_verifier
        self._user_tokens: Dict[str, Dict] = {}  # user_id -> {access_token, refresh_token, expires_at}
        
        if not self.client_id or not self.client_secret:
            self.logger.warning("X OAuth credentials not configured. Set X_CLIENT_ID and X_CLIENT_SECRET in .env")
    
    def is_configured(self) -> bool:
        """Check if OAuth credentials are configured"""
        return bool(self.client_id and self.client_secret)
    
    def generate_oauth_state(self) -> tuple[str, str]:
        """
        Generate OAuth 2.0 PKCE code verifier and challenge
        
        Returns:
            (code_verifier, code_challenge) tuple
        """
        # Generate code verifier (random string)
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        
        # Generate code challenge (SHA256 hash of verifier)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')
        
        return code_verifier, code_challenge
    
    def get_authorization_url(self, state: Optional[str] = None) -> tuple[str, str]:
        """
        Generate X OAuth authorization URL
        
        Args:
            state: Optional OAuth state for CSRF protection
            
        Returns:
            (authorization_url, state) tuple
        """
        if not self.is_configured():
            raise ValueError("X OAuth credentials not configured")
        
        # Generate PKCE code verifier and challenge
        code_verifier, code_challenge = self.generate_oauth_state()
        
        # Generate state if not provided
        if not state:
            state = secrets.token_urlsafe(32)
        
        # Store code verifier for later use
        self._oauth_states[state] = code_verifier
        
        # Build authorization URL
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "tweet.read users.read follows.read offline.access",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256"
        }
        
        auth_url = f"{self.authorize_url}?{urlencode(params)}"
        
        self.logger.info(f"Generated OAuth authorization URL with state: {state[:8]}...")
        
        return auth_url, state
    
    def exchange_code_for_tokens(self, code: str, state: str) -> Dict:
        """
        Exchange authorization code for access token
        
        Args:
            code: Authorization code from OAuth callback
            state: OAuth state for verification
            
        Returns:
            Dictionary with access_token, refresh_token, expires_in, etc.
        """
        if not self.is_configured():
            raise ValueError("X OAuth credentials not configured")
        
        # Verify state
        if state not in self._oauth_states:
            raise ValueError("Invalid OAuth state")
        
        code_verifier = self._oauth_states[state]
        
        # Exchange code for tokens
        token_data = {
            "code": code,
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "code_verifier": code_verifier
        }
        
        # Basic auth header
        auth_header = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode('utf-8')
        ).decode('utf-8')
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {auth_header}"
        }
        
        try:
            # Try with SSL verification first
            try:
                response = requests.post(self.token_url, data=token_data, headers=headers, verify=True, timeout=30)
                response.raise_for_status()
            except requests.exceptions.SSLError as ssl_error:
                # Retry without SSL verification (for development environments)
                self.logger.warning(f"SSL verification failed, retrying without verification: {ssl_error}")
                response = requests.post(self.token_url, data=token_data, headers=headers, verify=False, timeout=30)
                response.raise_for_status()
            
            token_response = response.json()
            
            # Clean up state
            del self._oauth_states[state]
            
            self.logger.info("Successfully exchanged code for tokens")
            
            return token_response
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error exchanging code for tokens: {e}")
            if hasattr(e, 'response') and e.response is not None:
                self.logger.error(f"Response status: {e.response.status_code}")
                self.logger.error(f"Response text: {e.response.text}")
            raise ValueError(f"Failed to exchange code for tokens: {e}")
    
    def refresh_access_token(self, refresh_token: str) -> Dict:
        """
        Refresh access token using refresh token
        
        Args:
            refresh_token: Refresh token from previous OAuth flow
            
        Returns:
            Dictionary with new access_token, refresh_token, expires_in, etc.
        """
        if not self.is_configured():
            raise ValueError("X OAuth credentials not configured")
        
        token_data = {
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "client_id": self.client_id
        }
        
        # Basic auth header
        auth_header = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode('utf-8')
        ).decode('utf-8')
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {auth_header}"
        }
        
        try:
            # Try with SSL verification first
            try:
                response = requests.post(self.token_url, data=token_data, headers=headers, verify=True, timeout=30)
                response.raise_for_status()
            except requests.exceptions.SSLError as ssl_error:
                # Retry without SSL verification (for development environments)
                self.logger.warning(f"SSL verification failed, retrying without verification: {ssl_error}")
                response = requests.post(self.token_url, data=token_data, headers=headers, verify=False, timeout=30)
                response.raise_for_status()
            
            token_response = response.json()
            
            self.logger.info("Successfully refreshed access token")
            
            return token_response
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error refreshing access token: {e}")
            if hasattr(e, 'response') and e.response is not None:
                self.logger.error(f"Response status: {e.response.status_code}")
                self.logger.error(f"Response text: {e.response.text}")
            raise ValueError(f"Failed to refresh access token: {e}")
    
    def store_user_tokens(self, user_id: str, tokens: Dict):
        """
        Store user tokens (in-memory for MVP, use database in production)
        
        Args:
            user_id: User identifier
            tokens: Token dictionary with access_token, refresh_token, expires_in
        """
        import time
        
        self._user_tokens[user_id] = {
            "access_token": tokens.get("access_token"),
            "refresh_token": tokens.get("refresh_token"),
            "expires_at": time.time() + tokens.get("expires_in", 7200),  # Default 2 hours
            "token_type": tokens.get("token_type", "bearer")
        }
        
        self.logger.info(f"Stored tokens for user: {user_id[:8]}...")
    
    def get_user_tokens(self, user_id: str) -> Optional[Dict]:
        """
        Get stored user tokens
        
        Args:
            user_id: User identifier
            
        Returns:
            Token dictionary or None if not found
        """
        return self._user_tokens.get(user_id)
    
    def is_token_valid(self, user_id: str) -> bool:
        """
        Check if user's access token is still valid
        
        Args:
            user_id: User identifier
            
        Returns:
            True if token exists and is not expired
        """
        tokens = self.get_user_tokens(user_id)
        if not tokens:
            return False
        
        import time
        return time.time() < tokens.get("expires_at", 0)
    
    def get_valid_access_token(self, user_id: str) -> Optional[str]:
        """
        Get valid access token, refreshing if necessary
        
        Args:
            user_id: User identifier
            
        Returns:
            Access token or None if unavailable
        """
        tokens = self.get_user_tokens(user_id)
        if not tokens:
            return None
        
        import time
        
        # Check if token is expired
        if time.time() >= tokens.get("expires_at", 0):
            # Try to refresh
            refresh_token = tokens.get("refresh_token")
            if refresh_token:
                try:
                    new_tokens = self.refresh_access_token(refresh_token)
                    self.store_user_tokens(user_id, new_tokens)
                    return new_tokens.get("access_token")
                except Exception as e:
                    self.logger.error(f"Failed to refresh token for user {user_id}: {e}")
                    return None
        
        return tokens.get("access_token")
    
    def revoke_tokens(self, user_id: str):
        """
        Revoke and remove user tokens
        
        Args:
            user_id: User identifier
        """
        if user_id in self._user_tokens:
            del self._user_tokens[user_id]
            self.logger.info(f"Revoked tokens for user: {user_id[:8]}...")


# Global service instance
_x_auth_service = None

def get_x_auth_service() -> XAuthService:
    """Get global X auth service instance"""
    global _x_auth_service
    if _x_auth_service is None:
        _x_auth_service = XAuthService()
    return _x_auth_service

