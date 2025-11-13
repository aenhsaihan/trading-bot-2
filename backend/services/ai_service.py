"""AI service for trading assistant with battle/combat mode tone"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

# Add project root to path
# ai_service.py is at: backend/services/ai_service.py
# So project root is: backend/services/ -> backend/ -> project_root
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file, override=True)  # override=True to ensure it loads
        print(f"[AIService] Loaded .env from {env_file.absolute()}")
    else:
        print(f"[AIService] .env file not found at {env_file.absolute()}")
except ImportError:
    pass  # python-dotenv not installed, skip
except Exception as e:
    print(f"[AIService] Error loading .env: {e}")

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("Warning: OpenAI package not installed. Install with: pip install openai")

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    print("Warning: Groq package not installed. Install with: pip install groq")

from src.utils.logger import setup_logger


class AIService:
    """AI service for tactical trading analysis"""
    
    def __init__(
        self,
        provider: str = "groq",  # Default to Groq (free)
        openai_key: Optional[str] = None,
        groq_key: Optional[str] = None
    ):
        """
        Initialize AI service.
        
        Args:
            provider: AI provider to use ("openai" or "groq"). Defaults to "groq" (free).
            openai_key: OpenAI API key (or set OPENAI_API_KEY env var)
            groq_key: Groq API key (or set GROQ_API_KEY env var)
        """
        self.logger = setup_logger(f"{__name__}.AIService")
        self.provider = provider.lower()
        
        # Try Groq first (free tier available)
        if self.provider == "groq" or self.provider == "auto":
            self.groq_key = groq_key or os.getenv("GROQ_API_KEY")
            if GROQ_AVAILABLE and self.groq_key:
                try:
                    # For development: disable SSL verification to avoid certificate issues
                    # In production, you should fix SSL certificates instead
                    import httpx
                    self.client = Groq(
                        api_key=self.groq_key,
                        http_client=httpx.Client(
                            verify=False,  # Disable SSL verification for development
                            timeout=30.0
                        )
                    )
                    self.enabled = True
                    self.provider = "groq"
                    # Use a reliable free model (llama-3.1-70b-versatile was decommissioned)
                    # Will auto-fallback to other models if this one fails
                    self.model = "llama-3.1-8b-instant"  # Reliable free, fast model
                    self.logger.info("AI Service initialized with Groq (free tier, SSL verification disabled for development)")
                except Exception as e:
                    self.logger.error(f"Failed to initialize Groq client: {e}")
                    self.client = None
                    self.enabled = False
            elif self.provider == "groq":
                self.client = None
                self.enabled = False
                if not GROQ_AVAILABLE:
                    self.logger.warning("Groq package not installed. Install with: pip install groq")
                elif not self.groq_key:
                    self.logger.warning("Groq API key not found. Set GROQ_API_KEY env var. Falling back to OpenAI if available.")
                    # Fall back to OpenAI if Groq not configured
                    self.provider = "openai"
        
        # Try OpenAI as fallback or if explicitly requested
        if (self.provider == "openai" or (self.provider == "auto" and not self.enabled)):
            self.openai_key = openai_key or os.getenv("OPENAI_API_KEY")
            if OPENAI_AVAILABLE and self.openai_key:
                self.client = OpenAI(api_key=self.openai_key)
                self.enabled = True
                self.provider = "openai"
                self.model = "gpt-4o-mini"  # Cost-effective model
                self.logger.info("AI Service initialized with OpenAI")
            elif self.provider == "openai":
                self.client = None
                self.enabled = False
                if not OPENAI_AVAILABLE:
                    self.logger.warning("OpenAI package not installed. Install with: pip install openai")
                elif not self.openai_key:
                    self.logger.warning("OpenAI API key not found. Set OPENAI_API_KEY env var.")
        
        if not self.enabled:
            self.logger.warning("AI Service disabled. No API keys configured. Set GROQ_API_KEY (free) or OPENAI_API_KEY env var.")
    
    def _get_system_prompt(self, context: Optional[Dict] = None) -> str:
        """
        Get system prompt with battle/combat mode tone.
        
        Args:
            context: Optional context about current positions, market state, etc.
            
        Returns:
            System prompt string
        """
        base_prompt = """You are a tactical trading AI assistant operating in BATTLE MODE. Your role is to provide decisive, professional analysis and prompt quick, informed decisions.

TONE & STYLE:
- Stern but professional (like a military commander)
- Direct and actionable
- No fluff, no hesitation
- Prompt for fast decisions when opportunities arise
- Warn clearly about risks
- Use tactical/combat terminology appropriately

CAPABILITIES:
- Analyze trading signals and notifications
- Assess risk and opportunity
- Provide tactical recommendations
- Execute agreed-upon trading operations
- Learn from user decisions

COMMUNICATION STYLE:
- Start critical alerts with urgency indicators (⚠️, 🚨, ⚔️)
- Use clear, concise language
- Provide actionable recommendations
- Ask for confirmation before executing trades
- Report back on executed operations

Remember: Time is money in trading. Be decisive, be clear, be professional."""
        
        if context:
            context_str = "\n\nCURRENT CONTEXT:\n"
            if context.get('positions'):
                context_str += f"- Open Positions: {len(context['positions'])} positions\n"
            if context.get('balance'):
                context_str += f"- Account Balance: ${context['balance']:,.2f}\n"
            if context.get('selected_notification'):
                notif = context['selected_notification']
                context_str += f"- Analyzing Notification: {notif.get('title', 'N/A')}\n"
                context_str += f"  Type: {notif.get('type', 'N/A')}\n"
                context_str += f"  Symbol: {notif.get('symbol', 'N/A')}\n"
                context_str += f"  Confidence: {notif.get('confidence_score', 'N/A')}%\n"
            
            base_prompt += context_str
        
        return base_prompt
    
    def analyze_notification(
        self,
        notification: Dict,
        context: Optional[Dict] = None
    ) -> str:
        """
        Analyze a notification and provide tactical assessment.
        
        Args:
            notification: Notification data
            context: Additional context (positions, balance, etc.)
            
        Returns:
            AI analysis text
        """
        if not self.enabled:
            return "⚠️ AI Service not available. Please configure OpenAI API key."
        
        try:
            system_prompt = self._get_system_prompt(context)
            
            user_prompt = f"""Analyze this trading notification and provide tactical assessment:

TITLE: {notification.get('title', 'N/A')}
TYPE: {notification.get('type', 'N/A')}
MESSAGE: {notification.get('message', 'N/A')}
SYMBOL: {notification.get('symbol', 'N/A')}
CONFIDENCE: {notification.get('confidence_score', 'N/A')}%
URGENCY: {notification.get('urgency_score', 'N/A')}%
PRIORITY: {notification.get('priority', 'N/A')}

Provide:
1. Signal assessment (is this actionable?)
2. Risk analysis
3. Recommended action (if any)
4. Position sizing suggestion (if opening position)
5. Stop loss/trailing stop recommendations

Be direct and tactical. Prompt for decision if action is recommended."""
            
            # Try different models if one fails (some may be decommissioned)
            models_to_try = [self.model, "llama-3.1-8b-instant", "mixtral-8x7b-32768"]
            
            for model in models_to_try:
                try:
                    response = self.client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.7,
                        max_tokens=500
                    )
                    # If successful, update self.model for future calls
                    if model != self.model:
                        self.model = model
                        self.logger.info(f"Switched to model: {model}")
                    return response.choices[0].message.content
                except Exception as model_error:
                    # If model is decommissioned or not available, try next one
                    if "decommissioned" in str(model_error).lower() or "model" in str(model_error).lower():
                        self.logger.warning(f"Model {model} not available, trying next model...")
                        continue
                    # If SSL error, try recreating client without SSL verification
                    elif "CERTIFICATE_VERIFY_FAILED" in str(model_error) or "SSL" in str(model_error):
                        self.logger.warning("SSL verification failed, retrying without verification (development mode)")
                        import httpx
                        self.client = Groq(
                            api_key=self.groq_key,
                            http_client=httpx.Client(verify=False, timeout=30.0)
                        )
                        # Retry with same model
                        try:
                            response = self.client.chat.completions.create(
                                model=model,
                                messages=[
                                    {"role": "system", "content": system_prompt},
                                    {"role": "user", "content": user_prompt}
                                ],
                                temperature=0.7,
                                max_tokens=500
                            )
                            if model != self.model:
                                self.model = model
                            return response.choices[0].message.content
                        except:
                            continue
                    else:
                        # Other errors, try next model
                        continue
            
            # If all models failed, raise the last error
            raise Exception("All models failed. Last error may be in logs.")
            
        except Exception as e:
            self.logger.error(f"Error in AI analysis: {e}", exc_info=True)
            return f"⚠️ Error analyzing notification: {str(e)}"
    
    def chat(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        context: Optional[Dict] = None
    ) -> str:
        """
        Chat with AI assistant.
        
        Args:
            user_message: User's message
            conversation_history: Previous messages in format [{"role": "user|assistant", "content": "..."}]
            context: Additional context (positions, balance, notifications, etc.)
            
        Returns:
            AI response text
        """
        if not self.enabled:
            return "⚠️ AI Service not available. Please configure OpenAI API key."
        
        try:
            system_prompt = self._get_system_prompt(context)
            
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            # Add conversation history
            messages.extend(conversation_history)
            
            # Add current user message
            messages.append({"role": "user", "content": user_message})
            
            # Try different models if one fails (some may be decommissioned)
            models_to_try = [self.model, "llama-3.1-8b-instant", "mixtral-8x7b-32768"]
            
            for model in models_to_try:
                try:
                    response = self.client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=0.7,
                        max_tokens=500
                    )
                    # If successful, update self.model for future calls
                    if model != self.model:
                        self.model = model
                        self.logger.info(f"Switched to model: {model}")
                    return response.choices[0].message.content
                except Exception as model_error:
                    # If model is decommissioned or not available, try next one
                    if "decommissioned" in str(model_error).lower() or ("model" in str(model_error).lower() and "invalid" in str(model_error).lower()):
                        self.logger.warning(f"Model {model} not available, trying next model...")
                        continue
                    # If SSL error, try recreating client without SSL verification
                    elif "CERTIFICATE_VERIFY_FAILED" in str(model_error) or "SSL" in str(model_error) or "certificate" in str(model_error).lower():
                        self.logger.warning("SSL verification failed, retrying without verification (development mode)")
                        import httpx
                        if self.provider == "groq":
                            self.client = Groq(
                                api_key=self.groq_key,
                                http_client=httpx.Client(verify=False, timeout=30.0)
                            )
                        # Retry with same model
                        try:
                            response = self.client.chat.completions.create(
                                model=model,
                                messages=messages,
                                temperature=0.7,
                                max_tokens=500
                            )
                            if model != self.model:
                                self.model = model
                            return response.choices[0].message.content
                        except:
                            continue
                    else:
                        # Other errors, try next model
                        continue
            
            # If all models failed, raise the last error
            raise Exception("All models failed. Last error may be in logs.")
            
        except Exception as e:
            self.logger.error(f"Error in AI chat: {e}", exc_info=True)
            return f"⚠️ Error processing message: {str(e)}"
    
    def is_enabled(self) -> bool:
        """Check if AI service is enabled"""
        return self.enabled

