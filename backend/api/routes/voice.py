"""Voice TTS API routes"""

import sys
import base64
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.services.voice_service import VoiceService, TTSProvider

router = APIRouter(prefix="/voice", tags=["voice"])

# Global service instance
voice_service = VoiceService()


class SynthesizeRequest(BaseModel):
    """Voice synthesis request"""
    text: str
    priority: str = "medium"  # critical, high, medium, low, info
    voice_id: Optional[str] = None
    provider: Optional[str] = None  # elevenlabs, azure, google


class SynthesizeResponse(BaseModel):
    """Voice synthesis response"""
    audio_base64: str  # Base64-encoded audio (MP3 format)
    provider_used: str
    format: str = "mp3"


@router.post("/synthesize", response_model=SynthesizeResponse)
async def synthesize_voice(request: SynthesizeRequest):
    """
    Synthesize speech from text using best available TTS provider.
    
    Returns base64-encoded audio that can be played in browser.
    """
    try:
        # Validate text
        if not request.text or not request.text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")
        
        # Check if any providers are available
        available_providers = [
            p for p, available in voice_service.providers.items()
            if available and p != TTSProvider.BROWSER
        ]
        
        if not available_providers:
            # No providers configured - return 503 (Service Unavailable) so frontend can fallback
            raise HTTPException(
                status_code=503,
                detail="No TTS providers configured. Please set ELEVENLABS_API_KEY, AZURE_TTS_KEY, or GOOGLE_TTS_KEY. Falling back to browser TTS."
            )
        
        # Convert provider string to enum if provided
        provider = None
        if request.provider:
            try:
                provider = TTSProvider(request.provider.lower())
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid provider: {request.provider}. Must be one of: elevenlabs, azure, google"
                )
        
        # Synthesize
        audio_bytes, provider_used = voice_service.synthesize(
            text=request.text,
            priority=request.priority,
            voice_id=request.voice_id,
            provider=provider
        )
        
        # Encode to base64 for JSON response
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        
        return SynthesizeResponse(
            audio_base64=audio_base64,
            provider_used=provider_used.value,
            format="mp3"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice synthesis failed: {str(e)}")


@router.get("/providers")
async def get_available_providers():
    """Get list of available TTS providers"""
    providers = {}
    for provider, available in voice_service.providers.items():
        if provider != TTSProvider.BROWSER:  # Browser is frontend-only
            providers[provider.value] = available
    
    return {
        "providers": providers,
        "default_order": ["elevenlabs", "azure", "google"]
    }


@router.get("/stats")
async def get_usage_stats():
    """Get usage statistics per provider"""
    return voice_service.get_usage_stats()


@router.post("/cache/clear")
async def clear_cache():
    """Clear audio cache"""
    voice_service.clear_cache()
    return {"message": "Cache cleared"}

