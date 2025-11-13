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

  // When speech ends, process next in queue
  utterance.onend = () => {
    isSpeaking = false;
    currentUtterance = null;
    // Small delay before next message to avoid overlap
    setTimeout(() => {
      processQueue();
    }, 200);
  };

  utterance.onerror = () => {
    isSpeaking = false;
    currentUtterance = null;
    // Continue with next message even on error
    setTimeout(() => {
      processQueue();
    }, 200);
  };

  synth.speak(utterance);
}

export function speakMessage(message: string, priority: string = 'info') {
  if (!synth) {
    console.warn('Speech synthesis not available');
    return;
  }

  // Add to queue
  const queuedMessage: QueuedMessage = {
    message,
    priority,
    timestamp: Date.now(),
  };

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

