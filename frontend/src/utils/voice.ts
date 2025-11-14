/**
 * Voice alert system using Web Speech API
 * StarCraft-style notifications with queue system to prevent stuttering
 */

let synth: SpeechSynthesis | null = null;
let voices: SpeechSynthesisVoice[] = [];

// Voice queue system
interface QueuedMessage {
  message: string;
  priority: string;
  timestamp: number;
}

let voiceQueue: QueuedMessage[] = [];
let isSpeaking = false;
let currentUtterance: SpeechSynthesisUtterance | null = null;
let speechInitialized = false; // Track if speech has been initialized via user interaction

// Initialize speech synthesis
if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
  synth = window.speechSynthesis;
  
  // Load voices
  const loadVoices = () => {
    voices = synth!.getVoices();
  };
  
  loadVoices();
  if (speechSynthesis.onvoiceschanged !== undefined) {
    speechSynthesis.onvoiceschanged = loadVoices;
  }
  
  // Initialize speech synthesis on first user interaction
  // Browsers require user interaction before allowing speech synthesis
  const initSpeechOnInteraction = () => {
    if (speechInitialized) return;
    
    // Try to speak a silent utterance to "unlock" speech synthesis
    // This must happen in response to a user interaction
    try {
      const testUtterance = new SpeechSynthesisUtterance('');
      testUtterance.volume = 0;
      testUtterance.rate = 0.1;
      synth!.speak(testUtterance);
      synth!.cancel(); // Immediately cancel it
      speechInitialized = true;
      console.log('✅ Speech synthesis initialized via user interaction');
    } catch (e) {
      console.warn('⚠️ Could not initialize speech synthesis:', e);
    }
  };
  
  // Listen for user interactions to initialize speech
  const events = ['click', 'keydown', 'touchstart'];
  events.forEach(eventType => {
    window.addEventListener(eventType, initSpeechOnInteraction, { once: true, passive: true });
  });
}

function processQueue() {
  if (isSpeaking || voiceQueue.length === 0 || !synth) {
    return;
  }

  // Get next message from queue
  const next = voiceQueue.shift();
  if (!next) {
    return;
  }

  isSpeaking = true;
  const utterance = new SpeechSynthesisUtterance(next.message);
  currentUtterance = utterance;
  
  console.log('🗣️ Processing voice queue:', {
    message: next.message,
    priority: next.priority,
    availableVoices: voices.length
  });
  
  // Adjust voice based on priority
  // Try to find a good voice (prefer female voices for "sexy" sound)
  const preferredVoices = ['Samantha', 'Victoria', 'Karen', 'Alex'];
  let selectedVoice = voices.find((v) =>
    preferredVoices.some((name) => v.name.includes(name))
  );
  
  if (!selectedVoice && voices.length > 0) {
    selectedVoice = voices[0]; // Fallback to first available
  }
  
  if (selectedVoice) {
    utterance.voice = selectedVoice;
    console.log('✅ Selected voice:', selectedVoice.name);
  } else {
    console.warn('⚠️ No voice selected, using default');
  }

  // Adjust rate and pitch based on priority
  if (next.priority === 'critical') {
    utterance.rate = 1.1;
    utterance.pitch = 1.2;
    utterance.volume = 1.0;
  } else if (next.priority === 'high') {
    utterance.rate = 1.0;
    utterance.pitch = 1.1;
    utterance.volume = 0.9;
  } else {
    utterance.rate = 0.95;
    utterance.pitch = 1.0;
    utterance.volume = 0.8;
  }

  // Event handlers
  utterance.onstart = () => {
    console.log('✅ Speech started:', next.message);
  };
  
  utterance.onend = () => {
    console.log('✅ Speech ended:', next.message);
    isSpeaking = false;
    currentUtterance = null;
    // Small delay before next message to avoid overlap
    setTimeout(() => {
      processQueue();
    }, 200);
  };

  utterance.onerror = (error) => {
    console.error('❌ Speech synthesis error:', error);
    isSpeaking = false;
    currentUtterance = null;
    // Continue with next message even on error
    setTimeout(() => {
      processQueue();
    }, 200);
  };

  console.log('🎙️ Calling synth.speak()...');
  synth.speak(utterance);
}

export function speakMessage(message: string, priority: string = 'info') {
  console.log('🎤 speakMessage called:', { message, priority, synthAvailable: !!synth, speechInitialized });
  
  if (!synth) {
    console.warn('⚠️ Speech synthesis not available');
    return;
  }

  if (!message || message.trim().length === 0) {
    console.warn('⚠️ Empty message, skipping speech');
    return;
  }
  
  // If speech hasn't been initialized yet, try to initialize it now
  // This might work if called from a user interaction handler
  if (!speechInitialized) {
    console.warn('⚠️ Speech synthesis not initialized yet. Attempting to initialize...');
    try {
      const testUtterance = new SpeechSynthesisUtterance('');
      testUtterance.volume = 0;
      testUtterance.rate = 0.1;
      synth.speak(testUtterance);
      synth.cancel();
      speechInitialized = true;
      console.log('✅ Speech synthesis initialized');
    } catch (e) {
      console.warn('⚠️ Could not initialize speech synthesis. User interaction required.');
      // Still add to queue - it might work if user interacts
    }
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
    // Find first non-critical message and insert before it
    const firstNonCriticalIndex = voiceQueue.findIndex(m => m.priority !== 'critical');
    if (firstNonCriticalIndex >= 0) {
      voiceQueue.splice(firstNonCriticalIndex, 0, queuedMessage);
    } else {
      // All are critical, just add to end
      voiceQueue.push(queuedMessage);
    }
  } else {
    // Normal priority, add to end
    voiceQueue.push(queuedMessage);
  }

  // Start processing queue if not already speaking
  processQueue();
}

export function stopSpeaking() {
  if (synth) {
    synth.cancel();
    isSpeaking = false;
    currentUtterance = null;
    voiceQueue = []; // Clear queue when stopped
  }
}

export function clearVoiceQueue() {
  voiceQueue = [];
  // Don't interrupt current speech, just clear queue
}

