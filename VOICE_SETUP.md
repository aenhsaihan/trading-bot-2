# Voice TTS Setup Guide

## ElevenLabs Setup (Recommended - Best Quality)

1. **Get your API key:**
   - Sign up at [ElevenLabs](https://elevenlabs.io/)
   - Go to your profile → API Keys
   - Copy your API key

2. **Add to `.env` file:**
   Create a `.env` file in the project root (if it doesn't exist) and add:
   ```env
   ELEVENLABS_API_KEY=your_api_key_here
   ```

3. **Restart the backend server:**
   ```bash
   # Stop the current server (Ctrl+C) and restart
   python backend/run.py
   ```

4. **Test it:**
   - Open the frontend
   - Create a notification
   - The voice should use ElevenLabs (check console for "Synthesized with elevenlabs")

## Available Voice IDs

The service uses these ElevenLabs voices by default:
- **Rachel** (`21m00Tcm4TlvDq8ikWAM`) - Calm, professional (default)
- **Bella** (`EXAVITQu4vr4xnSDxMaL`) - Calm, soothing

You can change the voice in `backend/services/voice_service.py` line 229.

## Fallback Providers

If ElevenLabs is not configured, the system will automatically fallback to:
1. **Azure Neural TTS** (if `AZURE_TTS_KEY` and `AZURE_TTS_REGION` are set)
2. **Google Cloud TTS** (if `GOOGLE_TTS_KEY` is set)
3. **Browser TTS** (always available, lowest quality)

## Testing

1. **Check provider status:**
   ```bash
   curl http://localhost:8000/voice/providers
   ```
   Should return: `{"providers":{"elevenlabs":true,"azure":false,"google":false},...}`

2. **Test synthesis:**
   ```bash
   curl -X POST http://localhost:8000/voice/synthesize \
     -H "Content-Type: application/json" \
     -d '{"text": "Testing ElevenLabs voice", "priority": "medium"}'
   ```

3. **In the app:**
   - Toggle voice alerts on
   - Create a notification
   - Check browser console for "Synthesized with elevenlabs"

## Troubleshooting

- **"No TTS providers configured"**: Make sure `.env` file exists and has `ELEVENLABS_API_KEY`
- **"503 Service Unavailable"**: API key might be invalid or expired
- **Still using browser TTS**: Check backend logs to see if API key was loaded correctly

