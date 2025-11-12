"""Voice alert system for notifications (StarCraft-style)"""

import pyttsx3
import threading
from typing import Optional
from src.utils.logger import setup_logger


class VoiceAlert:
    """Voice alert system with StarCraft-style notifications"""
    
    def __init__(self, enabled: bool = True):
        """
        Initialize voice alert system.
        
        Args:
            enabled: Whether voice alerts are enabled
        """
        self.enabled = enabled
        self.logger = setup_logger(f"{__name__}.VoiceAlert")
        self.engine = None
        self._lock = threading.Lock()
        
        if self.enabled:
            try:
                self.engine = pyttsx3.init()
                # Configure voice settings for StarCraft-like experience
                self._configure_voice()
            except Exception as e:
                self.logger.warning(f"Could not initialize TTS engine: {e}")
                self.enabled = False
    
    def _configure_voice(self):
        """Configure voice settings for StarCraft-like alerts"""
        if not self.engine:
            return
        
        try:
            # Set speech rate (slightly faster for urgency)
            self.engine.setProperty('rate', 180)  # Default is 200, lower = faster
            
            # Set volume (0.0 to 1.0)
            self.engine.setProperty('volume', 0.9)
            
            # Try to set a more authoritative voice
            voices = self.engine.getProperty('voices')
            if voices:
                # Prefer male voices (more StarCraft-like)
                for voice in voices:
                    if 'male' in voice.name.lower() or 'david' in voice.name.lower() or 'daniel' in voice.name.lower():
                        self.engine.setProperty('voice', voice.id)
                        break
        except Exception as e:
            self.logger.warning(f"Could not configure voice: {e}")
    
    def _get_alert_message(self, notification_type: str, priority: str, symbol: Optional[str] = None) -> str:
        """
        Generate StarCraft-style alert message.
        
        Args:
            notification_type: Type of notification
            priority: Priority level
            symbol: Trading pair symbol
            
        Returns:
            Alert message string
        """
        symbol_text = f" for {symbol}" if symbol else ""
        
        # StarCraft-style messages based on priority and type
        if priority == "critical":
            if "risk" in notification_type.lower():
                return f"Warning! Critical risk alert{symbol_text}! Immediate action required!"
            elif "combined" in notification_type.lower():
                return f"High priority opportunity{symbol_text}! Strong signals detected!"
            else:
                return f"Critical alert{symbol_text}! Attention required!"
        
        elif priority == "high":
            if "breakout" in notification_type.lower():
                return f"Technical breakout detected{symbol_text}! Opportunity available!"
            elif "surge" in notification_type.lower():
                return f"Social sentiment surge{symbol_text}! Market activity detected!"
            elif "news" in notification_type.lower():
                return f"Breaking news{symbol_text}! Market impact possible!"
            else:
                return f"High priority notification{symbol_text}!"
        
        elif priority == "medium":
            return f"Notification{symbol_text}: Moderate opportunity detected."
        
        else:
            return f"Notification{symbol_text}: Market update available."
    
    def alert(self, notification_type: str, priority: str, symbol: Optional[str] = None, custom_message: Optional[str] = None):
        """
        Play voice alert for notification.
        
        Args:
            notification_type: Type of notification
            priority: Priority level
            symbol: Trading pair symbol
            custom_message: Custom message to speak (overrides default)
        """
        if not self.enabled or not self.engine:
            return
        
        # Generate message
        message = custom_message or self._get_alert_message(notification_type, priority, symbol)
        
        # Play in background thread to avoid blocking
        def speak():
            try:
                with self._lock:
                    if self.engine:
                        self.engine.say(message)
                        self.engine.runAndWait()
            except Exception as e:
                self.logger.error(f"Error playing voice alert: {e}")
        
        thread = threading.Thread(target=speak, daemon=True)
        thread.start()
    
    def set_enabled(self, enabled: bool):
        """Enable or disable voice alerts"""
        self.enabled = enabled
        if enabled and not self.engine:
            try:
                self.engine = pyttsx3.init()
                self._configure_voice()
            except Exception as e:
                self.logger.warning(f"Could not initialize TTS engine: {e}")
                self.enabled = False

