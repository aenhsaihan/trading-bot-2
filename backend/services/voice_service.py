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
        
        # Check Google Cloud (supports both service account and API key)
        google_creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        google_key = os.getenv("GOOGLE_TTS_KEY")
        providers[TTSProvider.GOOGLE] = bool(google_creds or google_key)
        if google_creds or google_key:
            method = "service account" if google_creds else "API key"
            self.logger.info(f"Google Cloud TTS available ({method})")
        else:
            self.logger.warning("Google Cloud TTS credentials not found (GOOGLE_APPLICATION_CREDENTIALS or GOOGLE_TTS_KEY)")
        
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
            # Map generic voice IDs to ElevenLabs-specific IDs
            if voice_id and voice_id not in ["default_female_calm", "default"]:
                elevenlabs_voice_id = voice_id
            else:
                # Use default ElevenLabs voice (Rachel - calm, professional)
                elevenlabs_voice_id = "21m00Tcm4TlvDq8ikWAM"
            
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{elevenlabs_voice_id}"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": api_key
            }
            
            # Match the JavaScript SDK format
            data = {
                "text": text,
                "model_id": "eleven_multilingual_v2",  # Updated to match SDK example
                "voice_settings": {
                    "stability": 0.5,  # Balanced stability
                    "similarity_boost": 0.75,  # Good voice similarity
                    "style": 0.0,  # Neutral style
                    "use_speaker_boost": True
                }
            }
            
            # output_format as query parameter (matches SDK behavior)
            params = {
                "output_format": "mp3_44100_128"  # MP3, 44.1kHz, 128kbps - matches SDK example
            }
            
            self.logger.debug(f"Calling ElevenLabs API: voice_id={elevenlabs_voice_id}, model=eleven_multilingual_v2")
            
            # Try with SSL verification first
            try:
                response = requests.post(url, json=data, headers=headers, params=params, timeout=30, verify=True)
            except requests.exceptions.SSLError as ssl_error:
                # If SSL verification fails, try without verification (development mode)
                self.logger.warning(f"SSL verification failed, retrying without verification (development mode): {ssl_error}")
                response = requests.post(url, json=data, headers=headers, params=params, timeout=30, verify=False)
            
            # Better error handling
            if response.status_code != 200:
                error_detail = response.text
                self.logger.error(f"ElevenLabs API error {response.status_code}: {error_detail}")
                raise Exception(f"ElevenLabs API returned {response.status_code}: {error_detail}")
            
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
            # Available voices: en-US-AriaNeural, en-US-JennyNeural, en-US-MichelleNeural, 
            # en-US-NancyNeural, en-US-SaraNeural, en-US-AnaNeural, en-US-AshleyNeural
            # For "Ada" voice, try: en-US-AdaNeural (if available) or check Azure portal for exact name
            # Default: en-US-AriaNeural (calm, professional female voice)
            azure_voice = os.getenv("AZURE_TTS_VOICE", "en-US-AriaNeural")
            
            # If voice_id is provided and looks like an Azure voice name, use it
            if voice_id and voice_id.startswith("en-"):
                azure_voice = voice_id
            
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
            
            # Try with SSL verification first
            try:
                response = requests.post(url, data=ssml.encode('utf-8'), headers=headers, timeout=30, verify=True)
            except requests.exceptions.SSLError as ssl_error:
                # If SSL verification fails, try without verification (development mode)
                self.logger.warning(f"SSL verification failed, retrying without verification (development mode): {ssl_error}")
                response = requests.post(url, data=ssml.encode('utf-8'), headers=headers, timeout=30, verify=False)
            
            if response.status_code != 200:
                error_detail = response.text
                self.logger.error(f"Azure TTS API error {response.status_code}: {error_detail}")
                raise Exception(f"Azure TTS API returned {response.status_code}: {error_detail}")
            
            return response.content
            
        except ImportError:
            raise Exception("requests library not installed. Install with: pip install requests")
        except Exception as e:
            raise Exception(f"Azure synthesis failed: {e}")
    
    def _synthesize_google(self, text: str, voice_id: str, priority: str) -> bytes:
        """Synthesize using Google Cloud TTS"""
        try:
            from google.cloud import texttospeech
            import os
            
            # Google Cloud TTS can use:
            # 1. Service account JSON file (GOOGLE_APPLICATION_CREDENTIALS env var)
            # 2. API key (GOOGLE_TTS_KEY env var) - but this requires REST API, not client library
            # For now, we'll use the client library which requires service account
            
            # Check if credentials are set
            google_creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            if not google_creds:
                # Try alternative: use API key with REST API
                api_key = os.getenv("GOOGLE_TTS_KEY")
                if api_key:
                    return self._synthesize_google_rest(text, voice_id, priority, api_key)
                raise ValueError("Google TTS credentials not set. Set GOOGLE_APPLICATION_CREDENTIALS or GOOGLE_TTS_KEY")
            
            # Initialize client with service account
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
            # If client library not available, try REST API
            api_key = os.getenv("GOOGLE_TTS_KEY")
            if api_key:
                return self._synthesize_google_rest(text, voice_id, priority, api_key)
            raise Exception("google-cloud-texttospeech library not installed. Install with: pip install google-cloud-texttospeech, or set GOOGLE_TTS_KEY for REST API")
        except Exception as e:
            # If client library fails, try REST API as fallback
            api_key = os.getenv("GOOGLE_TTS_KEY")
            if api_key:
                self.logger.warning(f"Google Cloud client library failed, trying REST API: {e}")
                return self._synthesize_google_rest(text, voice_id, priority, api_key)
            raise Exception(f"Google synthesis failed: {e}")
    
    def _synthesize_google_rest(self, text: str, voice_id: str, priority: str, api_key: str) -> bytes:
        """Synthesize using Google Cloud TTS REST API (alternative to client library)"""
        try:
            import requests
            import base64
            
            # Google Cloud TTS REST API endpoint
            url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={api_key}"
            
            # Voice configuration (female, calm, professional)
            voice_name = "en-US-Neural2-F"  # Female neural voice
            
            data = {
                "input": {"text": text},
                "voice": {
                    "languageCode": "en-US",
                    "name": voice_name,
                    "ssmlGender": "FEMALE"
                },
                "audioConfig": {
                    "audioEncoding": "MP3",
                    "speakingRate": 1.0,
                    "pitch": 0.0,
                    "volumeGainDb": 0.0
                }
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            # Try with SSL verification first
            try:
                response = requests.post(url, json=data, headers=headers, timeout=30, verify=True)
            except requests.exceptions.SSLError as ssl_error:
                # If SSL verification fails, try without verification (development mode)
                self.logger.warning(f"SSL verification failed, retrying without verification (development mode): {ssl_error}")
                response = requests.post(url, json=data, headers=headers, timeout=30, verify=False)
            
            if response.status_code != 200:
                error_detail = response.text
                self.logger.error(f"Google TTS API error {response.status_code}: {error_detail}")
                raise Exception(f"Google TTS API returned {response.status_code}: {error_detail}")
            
            # Response contains base64-encoded audio
            audio_base64 = response.json().get("audioContent")
            if not audio_base64:
                raise Exception("No audio content in Google TTS response")
            
            return base64.b64decode(audio_base64)
            
        except ImportError:
            raise Exception("requests library not installed. Install with: pip install requests")
        except Exception as e:
            raise Exception(f"Google REST API synthesis failed: {e}")
    
    def get_usage_stats(self) -> Dict:
        """Get usage statistics per provider"""
        return self._usage_stats.copy()
    
    def clear_cache(self):
        """Clear audio cache"""
        self._audio_cache.clear()
        self.logger.info("Audio cache cleared")

