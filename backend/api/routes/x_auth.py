"""X (Twitter) OAuth authentication API routes"""

import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.services.x_auth_service import get_x_auth_service
from backend.services.x_integration_service import get_x_integration_service

router = APIRouter(prefix="/x", tags=["x-twitter"])

# Global service instances
x_auth_service = get_x_auth_service()


class AuthStatusResponse(BaseModel):
    """OAuth status response"""
    connected: bool
    configured: bool
    user_id: Optional[str] = None


@router.get("/auth/status")
async def get_auth_status(user_id: str = Query(default="default", description="User identifier")):
    """
    Get X account connection status
    
    Args:
        user_id: User identifier (default: "default" for MVP)
        
    Returns:
        Connection status
    """
    configured = x_auth_service.is_configured()
    connected = x_auth_service.is_token_valid(user_id)
    
    return AuthStatusResponse(
        connected=connected,
        configured=configured,
        user_id=user_id if connected else None
    )


@router.get("/auth/authorize")
async def authorize(user_id: str = Query(default="default", description="User identifier")):
    """
    Initiate OAuth authorization flow
    
    Args:
        user_id: User identifier (default: "default" for MVP)
        
    Returns:
        Redirect to X authorization page
    """
    if not x_auth_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="X OAuth not configured. Please set X_CLIENT_ID and X_CLIENT_SECRET in .env"
        )
    
    try:
        # Generate state with user_id embedded for callback
        import secrets
        state = f"{user_id}:{secrets.token_urlsafe(24)}"
        
        auth_url, _ = x_auth_service.get_authorization_url(state=state)
        
        return RedirectResponse(url=auth_url)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initiate OAuth: {str(e)}")


@router.get("/auth/callback")
async def oauth_callback(
    code: str = Query(..., description="Authorization code"),
    state: str = Query(..., description="OAuth state"),
    error: Optional[str] = Query(None, description="OAuth error if any")
):
    """
    OAuth callback endpoint
    
    Args:
        code: Authorization code from X
        state: OAuth state (contains user_id)
        error: Error message if OAuth failed
        
    Returns:
        Redirect to frontend with success/error
    """
    if error:
        # Redirect to frontend with error
        frontend_url = "http://localhost:5173/settings?x_auth_error=" + error
        return RedirectResponse(url=frontend_url)
    
    try:
        # Extract user_id from state (format: "user_id:random_state")
        user_id = state.split(":")[0] if ":" in state else "default"
        
        # Exchange code for tokens
        tokens = x_auth_service.exchange_code_for_tokens(code, state)
        
        # Store tokens
        x_auth_service.store_user_tokens(user_id, tokens)
        
        # Redirect to frontend with success
        frontend_url = "http://localhost:5173/settings?x_auth_success=true"
        return RedirectResponse(url=frontend_url)
        
    except ValueError as e:
        # Invalid state or token exchange failed
        frontend_url = f"http://localhost:5173/settings?x_auth_error={str(e)}"
        return RedirectResponse(url=frontend_url)
    except Exception as e:
        frontend_url = f"http://localhost:5173/settings?x_auth_error=unknown_error"
        return RedirectResponse(url=frontend_url)


@router.post("/auth/disconnect")
async def disconnect(user_id: str = Query(default="default", description="User identifier")):
    """
    Disconnect X account
    
    Args:
        user_id: User identifier (default: "default" for MVP)
        
    Returns:
        Success message
    """
    x_auth_service.revoke_tokens(user_id)
    
    return {"success": True, "message": "X account disconnected"}


@router.get("/auth/token")
async def get_access_token(user_id: str = Query(default="default", description="User identifier")):
    """
    Get valid access token (for internal use by X API client)
    
    Args:
        user_id: User identifier (default: "default" for MVP)
        
    Returns:
        Access token or error
    """
    if not x_auth_service.is_token_valid(user_id):
        raise HTTPException(status_code=401, detail="X account not connected or token expired")
    
    access_token = x_auth_service.get_valid_access_token(user_id)
    
    if not access_token:
        raise HTTPException(status_code=401, detail="Failed to get valid access token")
    
    return {"access_token": access_token}


@router.get("/monitoring/status")
async def get_monitoring_status(user_id: str = Query(default="default", description="User identifier")):
    """
    Get X monitoring status
    
    Args:
        user_id: User identifier (default: "default" for MVP)
        
    Returns:
        Monitoring status
    """
    integration_service = get_x_integration_service(user_id)
    status = integration_service.get_status()
    return status


@router.get("/test/profile")
async def test_user_profile(user_id: str = Query(default="default", description="User identifier")):
    """
    Test API connection by fetching user profile
    
    Args:
        user_id: User identifier (default: "default" for MVP)
        
    Returns:
        User profile data
    """
    try:
        from backend.services.x_api_client import get_x_api_client
        api_client = get_x_api_client(user_id)
        profile = api_client.get_me()
        return {"success": True, "profile": profile}
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "error_details": traceback.format_exc()
        }


@router.get("/monitoring/accounts")
async def get_followed_accounts(user_id: str = Query(default="default", description="User identifier")):
    """
    Get list of followed accounts being monitored
    
    Args:
        user_id: User identifier (default: "default" for MVP)
        
    Returns:
        List of followed accounts
    """
    integration_service = get_x_integration_service(user_id)
    accounts = integration_service.get_followed_accounts()
    return {"accounts": accounts, "count": len(accounts)}


@router.post("/monitoring/refresh")
async def refresh_followed_accounts(user_id: str = Query(default="default", description="User identifier")):
    """
    Refresh list of followed accounts
    
    Args:
        user_id: User identifier (default: "default" for MVP)
        
    Returns:
        Updated list of followed accounts
    """
    try:
        integration_service = get_x_integration_service(user_id)
        accounts = integration_service.refresh_followed_accounts()
        return {"accounts": accounts, "count": len(accounts), "success": True}
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return {
            "accounts": [],
            "count": 0,
            "success": False,
            "error": str(e),
            "error_details": error_details
        }


@router.post("/monitoring/start")
async def start_monitoring(user_id: str = Query(default="default", description="User identifier")):
    """
    Start monitoring X accounts for new tweets
    
    Args:
        user_id: User identifier (default: "default" for MVP)
        
    Returns:
        Success status
    """
    integration_service = get_x_integration_service(user_id)
    success = integration_service.start_monitoring()
    
    if not success:
        raise HTTPException(status_code=400, detail="Cannot start monitoring: X account not connected")
    
    return {"success": True, "message": "X monitoring started"}


@router.post("/monitoring/stop")
async def stop_monitoring(user_id: str = Query(default="default", description="User identifier")):
    """
    Stop monitoring X accounts
    
    Args:
        user_id: User identifier (default: "default" for MVP)
        
    Returns:
        Success status
    """
    integration_service = get_x_integration_service(user_id)
    integration_service.stop_monitoring()
    
    return {"success": True, "message": "X monitoring stopped"}

