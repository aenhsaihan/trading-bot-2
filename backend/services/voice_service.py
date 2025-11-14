"""Multi-provider Text-to-Speech service with automatic fallback

Supports:
- ElevenLabs (primary, best quality)
- Azure Neural TTS (fallback, cheaper)
- Google Cloud TTS (alternative fallback)
"""

import os
import sys
import base64
import hashlib
from pathlib import Path
from typing import Optional, Dict, Tuple
from enum import Enum

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger


class TTSProvider(Enum):
    """TTS Provider types"""
    ELEVENLABS = "elevenlabs"
    AZURE = "azure"
    GOOGLE = "google"
    BROWSER = "browser"  # Fallback, handled on frontend


class VoiceService:
    """Multi-provider TTS service with automatic fallback"""
    
    def __init__(self):
        """Initialize voice service with provider configuration"""
        self.logger = setup_logger(f"{__name__}.VoiceService")
        
        # Provider configuration
        self.providers = self._initialize_providers()
        
        # Audio cache (key: hash of text+voice+priority, value: base64 audio)
        self._audio_cache: Dict[str, bytes] = {}
        self._cache_max_size = 100  # Limit cache size
        
        # Usage tracking per provider
        self._usage_stats = {
            TTSProvider.ELEVENLABS: {"requests": 0, "chars": 0},
            TTSProvider.AZURE: {"requests": 0, "chars": 0},
            TTSProvider.GOOGLE: {"requests": 0, "chars": 0},
        }
    
    def _initialize_providers(self) -> Dict[TTSProvider, bool]:
        """Initialize and check provider availability"""
        providers = {}
        
        # Check ElevenLabs
        elevenlabs_key = os.getenv("ELEVENLABS_API_KEY")
        providers[TTSProvider.ELEVENLABS] = bool(elevenlabs_key)
        if elevenlabs_key:
            self.logger.info("ElevenLabs TTS available")
        else:
            self.logger.warning("ElevenLabs API key not found (ELEVENLABS_API_KEY)")
        
        # Check Azure
        azure_key = os.getenv("AZURE_TTS_KEY")
        azure_region = os.getenv("AZURE_TTS_REGION")
        providers[TTSProvider.AZURE] = bool(azure_key and azure_region)
        if azure_key and azure_region:
            self.logger.info("Azure Neural TTS available")
        else:
            self.logger.warning("Azure TTS credentials not found (AZURE_TTS_KEY, AZURE_TTS_REGION)")
        
        # Check Google Cloud
        google_key = os.getenv("GOOGLE_TTS_KEY")
        providers[TTSProvider.GOOGLE] = bool(google_key)
        if google_key:
            self.logger.info("Google Cloud TTS available")
        else:
            self.logger.warning("Google Cloud TTS key not found (GOOGLE_TTS_KEY)")
        
        # Browser TTS is always available (handled on frontend)
        providers[TTSProvider.BROWSER] = True
        
        return providers
    
    def _get_cache_key(self, text: str, voice_id: str, priority: str) -> str:
        """Generate cache key for audio"""
        cache_data = f"{text}|{voice_id}|{priority}"
        return hashlib.md5(cache_data.encode()).hexdigest()
    
    def _get_voice_id_for_priority(self, priority: str) -> str:
        """
        Get voice ID based on priority.
        Returns voice ID that works across providers.
        
        Args:
            priority: Notification priority (critical, high, medium, low, info)
            
        Returns:
            Voice ID string
        """
        # For now, use a default female voice
        # This will be provider-specific in actual implementation
        # ElevenLabs: "Rachel" or "Bella" (female, calm, professional)
        # Azure: "en-US-AriaNeural" (female, calm)
        # Google: "en-US-Neural2-F" (female)
        
        # Default to a calm, professional female voice
        return "default_female_calm"
    
    def synthesize(
        self,
        text: str,
        priority: str = "medium",
        voice_id: Optional[str] = None,
        provider: Optional[TTSProvider] = None
    ) -> Tuple[bytes, TTSProvider]:
        """
        Synthesize speech from text using best available provider.
        
        Args:
            text: Text to synthesize
            priority: Notification priority (affects voice selection)
            voice_id: Optional specific voice ID
            provider: Optional specific provider to use
            
        Returns:
            Tuple of (audio_bytes, provider_used)
            
        Raises:
            Exception: If all providers fail
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        # Use provided voice_id or get default for priority
        voice = voice_id or self._get_voice_id_for_priority(priority)
        
        # Check cache first
        cache_key = self._get_cache_key(text, voice, priority)
        if cache_key in self._audio_cache:
            self.logger.debug(f"Using cached audio for: {text[:50]}...")
            # Return cached audio with a dummy provider (we don't know which one was used)
            return self._audio_cache[cache_key], TTSProvider.ELEVENLABS
        
        # Try providers in order of preference
        provider_order = [
            provider if provider else TTSProvider.ELEVENLABS,
            TTSProvider.AZURE,
            TTSProvider.GOOGLE,
        ]
        
        # Remove duplicates while preserving order
        seen = set()
        provider_order = [p for p in provider_order if not (p in seen or seen.add(p))]
        
        last_error = None
        for tts_provider in provider_order:
            if not self.providers.get(tts_provider, False):
                continue
            
            try:
                audio_data = self._synthesize_with_provider(text, voice, priority, tts_provider)
                
                # Cache the result
                if len(self._audio_cache) >= self._cache_max_size:
                    # Remove oldest entry (simple FIFO)
                    oldest_key = next(iter(self._audio_cache))
                    del self._audio_cache[oldest_key]
                self._audio_cache[cache_key] = audio_data
                
                # Update usage stats
                self._usage_stats[tts_provider]["requests"] += 1
                self._usage_stats[tts_provider]["chars"] += len(text)
                
                self.logger.info(f"Successfully synthesized with {tts_provider.value}")
                return audio_data, tts_provider
                
            except Exception as e:
                self.logger.warning(f"Provider {tts_provider.value} failed: {e}")
                last_error = e
                continue
        
        # All providers failed
        raise Exception(f"All TTS providers failed. Last error: {last_error}")
    
    def _synthesize_with_provider(
        self,
        text: str,
        voice_id: str,
        priority: str,
        provider: TTSProvider
    ) -> bytes:
        """
        Synthesize speech using specific provider.
        
        Args:
            text: Text to synthesize
            voice_id: Voice ID to use
            priority: Notification priority
            provider: Provider to use
            
        Returns:
            Audio data as bytes (MP3 or WAV format)
        """
        if provider == TTSProvider.ELEVENLABS:
            return self._synthesize_elevenlabs(text, voice_id, priority)
        elif provider == TTSProvider.AZURE:
            return self._synthesize_azure(text, voice_id, priority)
        elif provider == TTSProvider.GOOGLE:
            return self._synthesize_google(text, voice_id, priority)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def _synthesize_elevenlabs(self, text: str, voice_id: str, priority: str) -> bytes:
        """Synthesize using ElevenLabs API"""
        try:
            import requests
            
            api_key = os.getenv("ELEVENLABS_API_KEY")
            if not api_key:
                raise ValueError("ELEVENLABS_API_KEY not set")
            
            # ElevenLabs voice IDs (female, calm, professional)
            # Default: "21m00Tcm4TlvDq8ikWAM" (Rachel - calm, professional)
            # Alternative: "EXAVITQu4vr4xnSDxMaL" (Bella - calm, soothing)
            elevenlabs_voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel
            
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{elevenlabs_voice_id}"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": api_key
            }
            
            data = {
                "text": text,
                "model_id": "eleven_monolingual_v1",  # Fast, high quality
                "voice_settings": {
                    "stability": 0.5,  # Balanced stability
                    "similarity_boost": 0.75,  # Good voice similarity
                    "style": 0.0,  # Neutral style
                    "use_speaker_boost": True
                }
            }
            
            response = requests.post(url, json=data, headers=headers, timeout=10)
            response.raise_for_status()
            
            return response.content
            
        except ImportError:
            raise Exception("requests library not installed. Install with: pip install requests")
        except Exception as e:
            raise Exception(f"ElevenLabs synthesis failed: {e}")
    
    def _synthesize_azure(self, text: str, voice_id: str, priority: str) -> bytes:
        """Synthesize using Azure Neural TTS"""
        try:
            import requests
            
            api_key = os.getenv("AZURE_TTS_KEY")
            region = os.getenv("AZURE_TTS_REGION")
            
            if not api_key or not region:
                raise ValueError("Azure TTS credentials not set")
            
            # Azure voice (female, calm, professional)
            # en-US-AriaNeural - calm, professional female voice
            azure_voice = "en-US-AriaNeural"
            
            url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
            
            headers = {
                "Ocp-Apim-Subscription-Key": api_key,
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": "audio-16khz-128kbitrate-mono-mp3",
                "User-Agent": "TradingBot-VoiceService"
            }
            
            # SSML for better control
            ssml = f"""<speak version='1.0' xml:lang='en-US'>
                <voice xml:lang='en-US' xml:gender='Female' name='{azure_voice}'>
                    <prosody rate='medium' pitch='medium'>
                        {text}
                    </prosody>
                </voice>
            </speak>"""
            
            response = requests.post(url, data=ssml.encode('utf-8'), headers=headers, timeout=10)
            response.raise_for_status()
            
            return response.content
            
        except ImportError:
            raise Exception("requests library not installed. Install with: pip install requests")
        except Exception as e:
            raise Exception(f"Azure synthesis failed: {e}")
    
    def _synthesize_google(self, text: str, voice_id: str, priority: str) -> bytes:
        """Synthesize using Google Cloud TTS"""
        try:
            from google.cloud import texttospeech
            
            # Initialize client
            client = texttospeech.TextToSpeechClient()
            
            # Configure voice (female, calm, professional)
            # en-US-Neural2-F - female neural voice
            voice_config = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name="en-US-Neural2-F",
                ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
            )
            
            # Configure audio
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=1.0,  # Normal speed
                pitch=0.0,  # Normal pitch
                volume_gain_db=0.0  # Normal volume
            )
            
            # Synthesize
            synthesis_input = texttospeech.SynthesisInput(text=text)
            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice_config,
                audio_config=audio_config
            )
            
            return response.audio_content
            
        except ImportError:
            raise Exception("google-cloud-texttospeech not installed. Install with: pip install google-cloud-texttospeech")
        except Exception as e:
            raise Exception(f"Google Cloud TTS synthesis failed: {e}")
    
    def get_usage_stats(self) -> Dict:
        """Get usage statistics per provider"""
        return self._usage_stats.copy()
    
    def clear_cache(self):
        """Clear audio cache"""
        self._audio_cache.clear()
        self.logger.info("Audio cache cleared")

