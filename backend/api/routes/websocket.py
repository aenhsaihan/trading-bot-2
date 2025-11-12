"""WebSocket routes for real-time notifications"""

import sys
from pathlib import Path
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.services.notification_service import NotificationService

router = APIRouter()

# Global service instance
notification_service = NotificationService()


@router.websocket("/ws/notifications")
async def websocket_notifications(websocket: WebSocket):
    """WebSocket endpoint for real-time notification updates"""
    await websocket.accept()
    
    # Add client to service
    notification_service.add_websocket_client(websocket)
    
    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to notification stream"
        })
        
        # Keep connection alive and handle messages
        while True:
            # Wait for any message from client (ping/pong, etc.)
            data = await websocket.receive_text()
            
            # Handle ping/pong
            if data == "ping":
                await websocket.send_text("pong")
            
    except WebSocketDisconnect:
        # Client disconnected
        notification_service.remove_websocket_client(websocket)
    except Exception as e:
        # Error occurred, remove client
        notification_service.remove_websocket_client(websocket)
        raise

