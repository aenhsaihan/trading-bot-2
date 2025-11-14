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
        HTML page with success/error message, or redirect to frontend if available
    """
    from fastapi.responses import HTMLResponse
    
    if error:
        # Try to redirect to frontend, fallback to error page
        try:
            import requests
            response = requests.get("http://localhost:5173", timeout=1)
            if response.status_code == 200:
                frontend_url = f"http://localhost:5173/settings?x_auth_error={error}"
                return RedirectResponse(url=frontend_url)
        except:
            pass
        
        # Fallback: Show error page
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>X Connection Error</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                .error {{ color: #d32f2f; }}
                .success {{ color: #2e7d32; }}
            </style>
        </head>
        <body>
            <h1 class="error">❌ X Connection Failed</h1>
            <p>Error: {error}</p>
            <p><a href="/x/auth/authorize">Try again</a></p>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)
    
    try:
        # Extract user_id from state (format: "user_id:random_state")
        user_id = state.split(":")[0] if ":" in state else "default"
        
        # Exchange code for tokens
        tokens = x_auth_service.exchange_code_for_tokens(code, state)
        
        # Store tokens
        x_auth_service.store_user_tokens(user_id, tokens)
        
        # Try to redirect to frontend, fallback to success page
        try:
            import requests
            response = requests.get("http://localhost:5173", timeout=1)
            if response.status_code == 200:
                frontend_url = "http://localhost:5173/settings?x_auth_success=true"
                return RedirectResponse(url=frontend_url)
        except:
            pass
        
        # Fallback: Show success page
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>X Connected Successfully</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f5f5f5; }
                .container { background: white; padding: 40px; border-radius: 10px; max-width: 500px; margin: 0 auto; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                .success { color: #2e7d32; font-size: 48px; margin-bottom: 20px; }
                h1 { color: #2e7d32; margin: 0; }
                p { color: #666; margin: 20px 0; }
                .info { background: #e3f2fd; padding: 15px; border-radius: 5px; margin: 20px 0; text-align: left; }
                .info code { background: #fff; padding: 2px 6px; border-radius: 3px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success">✅</div>
                <h1>X Account Connected!</h1>
                <p>Your X account has been successfully connected to the trading bot.</p>
                <div class="info">
                    <strong>Next steps:</strong><br>
                    1. Start monitoring: <code>curl -X POST http://localhost:8000/x/monitoring/start</code><br>
                    2. View followed accounts: <code>curl http://localhost:8000/x/monitoring/accounts</code><br>
                    3. Check status: <code>curl http://localhost:8000/x/monitoring/status</code>
                </div>
                <p><a href="/x/auth/authorize" style="color: #1976d2;">Reconnect</a> | <a href="/x/auth/status" style="color: #1976d2;">Check Status</a></p>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)
        
    except ValueError as e:
        # Invalid state or token exchange failed
        try:
            import requests
            response = requests.get("http://localhost:5173", timeout=1)
            if response.status_code == 200:
                frontend_url = f"http://localhost:5173/settings?x_auth_error={str(e)}"
                return RedirectResponse(url=frontend_url)
        except:
            pass
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>X Connection Error</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                .error {{ color: #d32f2f; }}
            </style>
        </head>
        <body>
            <h1 class="error">❌ Connection Failed</h1>
            <p>{str(e)}</p>
            <p><a href="/x/auth/authorize">Try again</a></p>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)
    except Exception as e:
        try:
            import requests
            response = requests.get("http://localhost:5173", timeout=1)
            if response.status_code == 200:
                frontend_url = "http://localhost:5173/settings?x_auth_error=unknown_error"
                return RedirectResponse(url=frontend_url)
        except:
            pass
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>X Connection Error</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                .error {{ color: #d32f2f; }}
            </style>
        </head>
        <body>
            <h1 class="error">❌ Unknown Error</h1>
            <p>An unexpected error occurred: {str(e)}</p>
            <p><a href="/x/auth/authorize">Try again</a></p>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)


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


@router.get("/test/following")
async def test_following(user_id: str = Query(default="default", description="User identifier")):
    """
    Test fetching followed accounts with detailed response
    
    Args:
        user_id: User identifier (default: "default" for MVP)
        
    Returns:
        Raw API response for debugging
    """
    try:
        from backend.services.x_api_client import get_x_api_client
        api_client = get_x_api_client(user_id)
        
        # Get user ID first
        me = api_client.get_me()
        user_id_for_api = me.get("id")
        
        # Make direct API call to see raw response
        import requests
        access_token = api_client._get_access_token()
        url = f"https://api.twitter.com/2/users/{user_id_for_api}/following"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        params = {
            "max_results": 10,
            "user.fields": "id,name,username,description,public_metrics"
        }
        
        # Try with SSL retry
        try:
            response = requests.get(url, headers=headers, params=params, verify=True, timeout=30)
        except requests.exceptions.SSLError:
            response = requests.get(url, headers=headers, params=params, verify=False, timeout=30)
        
        return {
            "success": True,
            "status_code": response.status_code,
            "response": response.json(),
            "user_id": user_id_for_api,
            "user_profile": me
        }
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

