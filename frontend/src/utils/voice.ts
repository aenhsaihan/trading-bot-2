/**
 * Voice alert system using Web Speech API
 * StarCraft-style notifications
 */

let synth: SpeechSynthesis | null = null;
let voices: SpeechSynthesisVoice[] = [];

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

export function speakMessage(message: string, priority: string = 'info') {
  if (!synth) {
    console.warn('Speech synthesis not available');
    return;
  }

  // Cancel any ongoing speech
  synth.cancel();

  const utterance = new SpeechSynthesisUtterance(message);
  
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

  synth.speak(utterance);
}

export function stopSpeaking() {
  if (synth) {
    synth.cancel();
  }
}

