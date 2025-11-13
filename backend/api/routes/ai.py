"""AI REST API routes"""

import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException
from typing import Optional, List, Dict
from pydantic import BaseModel

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.services.ai_service import AIService

router = APIRouter(prefix="/ai", tags=["ai"])

# Global service instance (in production, use dependency injection)
ai_service = AIService()


class ChatRequest(BaseModel):
    """Chat request model"""
    message: str
    conversation_history: Optional[List[Dict[str, str]]] = []
    context: Optional[Dict] = None


class AnalyzeNotificationRequest(BaseModel):
    """Analyze notification request model"""
    notification: Dict
    context: Optional[Dict] = None


@router.get("/status")
async def get_ai_status():
    """Get AI service status"""
    return {
        "enabled": ai_service.is_enabled(),
        "available": ai_service.enabled,
        "provider": getattr(ai_service, 'provider', 'none')
    }


@router.post("/chat")
async def chat(request: ChatRequest):
    """Chat with AI assistant"""
    try:
        # Run synchronous OpenAI call in thread pool to avoid blocking
        import asyncio
        response = await asyncio.to_thread(
            ai_service.chat,
            request.message,
            request.conversation_history or [],
            request.context
        )
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process chat: {str(e)}")


@router.post("/analyze-notification")
async def analyze_notification(request: AnalyzeNotificationRequest):
    """Analyze a notification"""
    try:
        # Run synchronous OpenAI call in thread pool to avoid blocking
        import asyncio
        analysis = await asyncio.to_thread(
            ai_service.analyze_notification,
            request.notification,
            request.context
        )
        return {"analysis": analysis}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze notification: {str(e)}")

