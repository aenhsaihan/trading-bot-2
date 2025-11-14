/**
 * Voice alert system with multi-provider TTS support
 * StarCraft-style notifications with queue system to prevent stuttering
 * 
 * Uses backend TTS service (ElevenLabs/Azure/Google) with browser TTS fallback
 */

import { voiceAPI } from "../services/api";

// Voice queue system
interface QueuedMessage {
  message: string;
  priority: string;
  timestamp: number;
}

let voiceQueue: QueuedMessage[] = [];
let isSpeaking = false;
let currentAudio: HTMLAudioElement | null = null;

// Browser TTS fallback (for when backend is unavailable)
let synth: SpeechSynthesis | null = null;
let voices: SpeechSynthesisVoice[] = [];
let speechInitialized = false;
let useBackendTTS = true; // Try backend first, fallback to browser

// Initialize browser TTS (for fallback)
if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
  synth = window.speechSynthesis;
  
  const loadVoices = () => {
    voices = synth!.getVoices();
  };
  
  loadVoices();
  if (speechSynthesis.onvoiceschanged !== undefined) {
    speechSynthesis.onvoiceschanged = loadVoices;
  }
  
  // Initialize speech synthesis on first user interaction
  // This MUST happen before any speech is attempted
  const initSpeechOnInteraction = (event?: Event) => {
    if (speechInitialized) return;
    
    try {
      const testUtterance = new SpeechSynthesisUtterance('');
      testUtterance.volume = 0;
      testUtterance.rate = 0.1;
      synth!.speak(testUtterance);
      synth!.cancel();
      speechInitialized = true;
      console.log('✅ Browser TTS initialized via user interaction:', event?.type || 'unknown');
      
      // Remove all listeners once initialized
      events.forEach(eventType => {
        window.removeEventListener(eventType, initSpeechOnInteraction);
      });
    } catch (e) {
      console.warn('⚠️ Could not initialize browser TTS:', e);
    }
  };
  
  // Listen for ANY user interaction to initialize
  // Use capture phase to catch interactions early
  const events = ['click', 'keydown', 'touchstart', 'mousedown', 'pointerdown'];
  events.forEach(eventType => {
    window.addEventListener(eventType, initSpeechOnInteraction, { 
      once: false,  // Don't use once - we'll remove manually
      passive: true,
      capture: true  // Capture in capture phase for earlier handling
    });
  });
}

/**
 * Play audio from base64-encoded data
 */
function playAudioFromBase64(base64Audio: string, format: string = 'mp3'): Promise<void> {
  return new Promise((resolve, reject) => {
    try {
      // Convert base64 to blob
      const byteCharacters = atob(base64Audio);
      const byteNumbers = new Array(byteCharacters.length);
      for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
      }
      const byteArray = new Uint8Array(byteNumbers);
      const blob = new Blob([byteArray], { type: `audio/${format}` });
      
      // Create audio element and play
      const audio = new Audio(URL.createObjectURL(blob));
      currentAudio = audio;
      
      audio.onended = () => {
        URL.revokeObjectURL(audio.src);
        currentAudio = null;
        resolve();
      };
      
      audio.onerror = (error) => {
        URL.revokeObjectURL(audio.src);
        currentAudio = null;
        reject(error);
      };
      
      audio.play().catch(reject);
      
    } catch (error) {
      reject(error);
    }
  });
}

/**
 * Play message using browser TTS (fallback)
 */
function playWithBrowserTTS(message: string, priority: string): Promise<void> {
  return new Promise((resolve, reject) => {
    if (!synth) {
      reject(new Error('Browser TTS not available'));
      return;
    }
    
    // If not initialized, try to initialize now (might work if called from user interaction)
    if (!speechInitialized) {
      console.warn('⚠️ Browser TTS not initialized yet. Attempting initialization...');
      const initialized = initializeBrowserTTS();
      if (!initialized) {
        // If initialization fails, reject with a clear error
        reject(new Error('Browser TTS requires user interaction. Please interact with the page first (click, type, etc.)'));
        return;
      }
    }
    
    const utterance = new SpeechSynthesisUtterance(message);
    
    // Select voice (prefer female voices)
    const preferredVoices = ['Samantha', 'Victoria', 'Karen', 'Alex'];
    let selectedVoice = voices.find((v) =>
      preferredVoices.some((name) => v.name.includes(name))
    );
    
    if (!selectedVoice && voices.length > 0) {
      selectedVoice = voices[0];
    }
    
    if (selectedVoice) {
      utterance.voice = selectedVoice;
    }
    
    // Adjust based on priority
    if (priority === 'critical') {
      utterance.rate = 1.1;
      utterance.pitch = 1.2;
      utterance.volume = 1.0;
    } else if (priority === 'high') {
      utterance.rate = 1.0;
      utterance.pitch = 1.1;
      utterance.volume = 0.9;
    } else {
      utterance.rate = 0.95;
      utterance.pitch = 1.0;
      utterance.volume = 0.8;
    }
    
    utterance.onend = () => resolve();
    utterance.onerror = (error) => reject(error);
    
    synth.speak(utterance);
  });
}

/**
 * Process the voice queue - plays next message
 */
async function processQueue() {
  if (isSpeaking || voiceQueue.length === 0) {
    return;
  }

  // Get next message from queue
  const next = voiceQueue.shift();
  if (!next) {
    return;
  }

  isSpeaking = true;
  
  console.log('🗣️ Processing voice queue:', {
    message: next.message,
    priority: next.priority,
    useBackend: useBackendTTS
  });

  try {
    // Try backend TTS first if enabled
    if (useBackendTTS) {
      try {
        const response = await voiceAPI.synthesize(
          next.message,
          next.priority
        );
        
        console.log(`✅ Synthesized with ${response.provider_used}`);
        
        // Play audio from backend
        await playAudioFromBase64(response.audio_base64, response.format);
        
        console.log('✅ Speech ended:', next.message);
        
      } catch (backendError: any) {
        // Check if it's a 503 (no providers) or other error
        const isServiceUnavailable = backendError?.message?.includes('503') || 
                                     backendError?.message?.includes('No TTS providers');
        
        if (isServiceUnavailable) {
          console.info('ℹ️ Backend TTS not configured, using browser TTS');
          // Disable backend TTS for future messages to avoid repeated failed requests
          useBackendTTS = false;
        } else {
          console.warn('⚠️ Backend TTS failed, falling back to browser TTS:', backendError);
        }
        
        // Fallback to browser TTS
        await playWithBrowserTTS(next.message, next.priority);
      }
    } else {
      // Use browser TTS directly
      await playWithBrowserTTS(next.message, next.priority);
    }
    
  } catch (error: any) {
    console.error('❌ Voice playback error:', error);
    
    // If it's a "not-allowed" error, it means TTS needs user interaction
    // Queue the message to try again after user interacts
    if (error?.error === 'not-allowed' || error?.message?.includes('not-allowed')) {
      console.warn('⚠️ Browser TTS requires user interaction. Message will be spoken after you interact with the page.');
      // Re-queue the message at the front so it plays after user interaction
      voiceQueue.unshift(next);
    }
    // Otherwise, just log and continue - don't block the queue
  } finally {
    isSpeaking = false;
    currentAudio = null;
    
    // Small delay before next message to avoid overlap
    setTimeout(() => {
      processQueue();
    }, 200);
  }
}

/**
 * Speak a message (adds to queue)
 */
export function speakMessage(message: string, priority: string = 'info') {
  console.log('🎤 speakMessage called:', { message, priority, useBackend: useBackendTTS });
  
  if (!message || message.trim().length === 0) {
    console.warn('⚠️ Empty message, skipping speech');
    return;
  }

  // Add to queue
  const queuedMessage: QueuedMessage = {
    message: message.trim(),
    priority,
    timestamp: Date.now(),
  };
  
  console.log('📝 Adding to voice queue:', queuedMessage);

  // Critical messages go to front of queue (but don't interrupt current speech)
  if (priority === 'critical' && voiceQueue.length > 0) {
    const firstNonCriticalIndex = voiceQueue.findIndex(m => m.priority !== 'critical');
    if (firstNonCriticalIndex >= 0) {
      voiceQueue.splice(firstNonCriticalIndex, 0, queuedMessage);
    } else {
      voiceQueue.push(queuedMessage);
    }
  } else {
    voiceQueue.push(queuedMessage);
  }

  // Start processing queue if not already speaking
  processQueue();
}

/**
 * Stop current speech and clear queue
 */
export function stopSpeaking() {
  // Stop audio if playing
  if (currentAudio) {
    currentAudio.pause();
    currentAudio.currentTime = 0;
    currentAudio = null;
  }
  
  // Stop browser TTS if speaking
  if (synth) {
    synth.cancel();
  }
  
  isSpeaking = false;
  voiceQueue = [];
}

/**
 * Clear voice queue (don't interrupt current speech)
 */
export function clearVoiceQueue() {
  voiceQueue = [];
}

/**
 * Enable/disable backend TTS (fallback to browser if disabled)
 */
export function setUseBackendTTS(enabled: boolean) {
  useBackendTTS = enabled;
  console.log(`🔧 Backend TTS ${enabled ? 'enabled' : 'disabled'}`);
}

/**
 * Check if backend TTS is available
 */
export async function checkBackendTTS(): Promise<boolean> {
  try {
    const providers = await voiceAPI.getAvailableProviders();
    const hasProvider = Object.values(providers.providers).some(available => available);
    console.log('🔍 Backend TTS providers:', providers);
    
    // If no providers, disable backend TTS
    if (!hasProvider) {
      useBackendTTS = false;
      console.info('ℹ️ No backend TTS providers available, using browser TTS');
    }
    
    return hasProvider;
  } catch (error) {
    console.warn('⚠️ Could not check backend TTS availability, using browser TTS:', error);
    useBackendTTS = false;
    return false;
  }
}

/**
 * Initialize browser TTS (must be called from user interaction)
 * This can be called multiple times safely
 */
export function initializeBrowserTTS() {
  if (!synth) {
    console.warn('⚠️ Browser TTS not available');
    return false;
  }
  
  if (speechInitialized) {
    return true;  // Already initialized
  }
  
  try {
    const testUtterance = new SpeechSynthesisUtterance('');
    testUtterance.volume = 0;
    testUtterance.rate = 0.1;
    synth.speak(testUtterance);
    synth.cancel();
    speechInitialized = true;
    console.log('✅ Browser TTS initialized');
    return true;
  } catch (e) {
    console.warn('⚠️ Could not initialize browser TTS:', e);
    return false;
  }
}

/**
 * Initialize voice system - check backend availability on startup
 */
export async function initializeVoiceSystem() {
  // Check backend TTS availability
  const backendAvailable = await checkBackendTTS();
  
  if (!backendAvailable) {
    console.info('ℹ️ Using browser TTS (backend TTS not configured)');
    useBackendTTS = false;
  }
}
