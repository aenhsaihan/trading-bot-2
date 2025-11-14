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

## Azure Neural TTS Setup (Fallback Option 1)

### Step-by-Step Guide to Get Azure TTS API Key:

1. **Sign up for Azure (if you don't have an account):**
   - Go to [Azure Portal](https://portal.azure.com/)
   - Sign up for a free account (includes $200 credit for 30 days)

2. **Create a Speech Services resource:**
   - In Azure Portal, click "Create a resource" (top left)
   - Search for "Speech" or "Speech Services"
   - Click "Create" on "Speech Services"
   - Fill in:
     - **Subscription**: Choose your subscription (free tier available)
     - **Resource Group**: Create new or use existing
     - **Region**: Choose closest to you (e.g., `eastus`, `westus2`, `westeurope`)
     - **Name**: Give it a name (e.g., "trading-bot-tts")
     - **Pricing tier**: Choose "Free F0" (5000 characters/month free) or "Standard S0" (pay-as-you-go)
   - Click "Review + create" → "Create"
   - Wait for deployment (takes ~1-2 minutes)

3. **Get your API key and region:**
   - Once deployed, click "Go to resource"
   - In the left sidebar, click "Keys and Endpoint"
   - You'll see:
     - **Key 1** or **Key 2** (either works - copy one)
     - **Location/Region** (e.g., `eastus`, `westus2`) - this is your region
   - Copy both values

4. **Add to `.env` file:**
   ```env
   AZURE_TTS_KEY=your_azure_key_here
   AZURE_TTS_REGION=your_region_here  # e.g., eastus, westus2
   AZURE_TTS_VOICE=en-US-AriaNeural  # Optional: Change voice (see below for options)
   ```
   
   **Example:**
   ```env
   AZURE_TTS_KEY=abc123def456ghi789jkl012mno345pqr678stu901vwx234yz
   AZURE_TTS_REGION=eastus
   AZURE_TTS_VOICE=en-US-AriaNeural
   ```
   
   **To find "Ada" voice (or any specific voice):**
   1. Visit: https://speech.microsoft.com/portal/voicegallery
   2. Filter by:
      - Language: English (United States) or your preferred locale
      - Gender: Female
      - Neural: Yes
   3. Search for "Ada" or browse the list
   4. Click on the voice to hear samples
   5. Copy the exact voice name (e.g., `en-US-AdaNeural` or `en-GB-AdaNeural`)
   6. Add to `.env`: `AZURE_TTS_VOICE=en-US-AdaNeural`
   
   **Popular Azure Neural Voices (Female):**
   - `en-US-AriaNeural` - Calm, professional (default)
   - `en-US-JennyNeural` - Friendly, warm
   - `en-US-MichelleNeural` - Energetic, clear
   - `en-US-NancyNeural` - Gentle, soothing
   - `en-US-SaraNeural` - Confident, articulate
   - `en-US-AnaNeural` - Young, cheerful
   - `en-US-AshleyNeural` - Mature, authoritative
   - `en-US-CoraNeural` - Warm, conversational
   - `en-US-ElizabethNeural` - Professional, clear
   - `en-US-JaneNeural` - Friendly, approachable

3. **Restart the backend server**

4. **Test it:**
   ```bash
   curl -X POST http://localhost:8000/voice/synthesize \
     -H "Content-Type: application/json" \
     -d '{"text": "Testing Azure voice", "priority": "medium", "provider": "azure"}'
   ```

## Google Cloud TTS Setup (Fallback Option 2)

### Option A: Using API Key (Simpler - Recommended for Testing)

**Step-by-Step Guide:**

1. **Sign up for Google Cloud (if you don't have an account):**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Sign up (includes $300 free credit for 90 days)
   - Accept terms and create/select a project

2. **Enable the Text-to-Speech API:**
   - In Google Cloud Console, go to "APIs & Services" → "Library"
   - Search for "Cloud Text-to-Speech API"
   - Click on it and click "Enable"
   - Wait for it to enable (takes ~30 seconds)

3. **Create an API Key:**
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "API Key"
   - Your API key will be created and displayed
   - **Important**: Click "Restrict Key" to secure it:
     - Under "API restrictions", select "Restrict key"
     - Choose "Cloud Text-to-Speech API"
     - Click "Save"
   - Copy your API key

4. **Add to `.env` file:**
   ```env
   GOOGLE_TTS_KEY=your_api_key_here
   ```
   
   **Example:**
   ```env
   GOOGLE_TTS_KEY=AIzaSyAbCdEfGhIjKlMnOpQrStUvWxYz1234567
   ```

5. **Restart the backend server**

**Note:** Google Cloud TTS free tier: 0-4 million characters/month free, then $4 per 1 million characters.

### Option B: Using Service Account (More Secure - For Production)

**Step-by-Step Guide:**

1. **Enable the Text-to-Speech API** (same as Option A, step 2)

2. **Create a Service Account:**
   - Go to "IAM & Admin" → "Service Accounts"
   - Click "Create Service Account"
   - Fill in:
     - **Service account name**: e.g., "tts-service"
     - **Service account ID**: auto-filled
   - Click "Create and Continue"
   - Under "Grant this service account access to project":
     - Select role: "Cloud Text-to-Speech API User"
   - Click "Continue" → "Done"

3. **Create and Download Key:**
   - Click on the service account you just created
   - Go to "Keys" tab
   - Click "Add Key" → "Create new key"
   - Choose "JSON" format
   - Click "Create" - JSON file will download automatically
   - **Save this file securely** (e.g., `google-tts-key.json` in your project root)

4. **Add to `.env` file:**
   ```env
   GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/google-tts-key.json
   ```
   
   **Example (Mac/Linux):**
   ```env
   GOOGLE_APPLICATION_CREDENTIALS=/Users/yourname/Documents/playground/composer/trading-bot-2/google-tts-key.json
   ```
   
   **Example (Windows):**
   ```env
   GOOGLE_APPLICATION_CREDENTIALS=C:\Users\yourname\Documents\playground\composer\trading-bot-2\google-tts-key.json
   ```

5. **Restart the backend server**

**Note:** Service account is more secure but requires the `google-cloud-texttospeech` Python library:
```bash
pip install google-cloud-texttospeech
```

4. **Test it:**
   ```bash
   curl -X POST http://localhost:8000/voice/synthesize \
     -H "Content-Type: application/json" \
     -d '{"text": "Testing Google voice", "priority": "medium", "provider": "google"}'
   ```

## Fallback Providers

If ElevenLabs is not configured, the system will automatically fallback to:
1. **Azure Neural TTS** (if `AZURE_TTS_KEY` and `AZURE_TTS_REGION` are set)
2. **Google Cloud TTS** (if `GOOGLE_APPLICATION_CREDENTIALS` or `GOOGLE_TTS_KEY` is set)
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

## Quick Reference: Where to Get API Keys

| Provider | Where to Get | Free Tier | Cost After Free Tier |
|----------|-------------|-----------|---------------------|
| **ElevenLabs** | [elevenlabs.io](https://elevenlabs.io/) → Profile → API Keys | 10,000 chars/month | $5/month for 30,000 chars |
| **Azure** | [portal.azure.com](https://portal.azure.com/) → Create Speech Services | 5,000 chars/month | $4 per 1M characters |
| **Google** | [console.cloud.google.com](https://console.cloud.google.com/) → APIs → Text-to-Speech | 0-4M chars/month | $4 per 1M characters |

## Troubleshooting

### General Issues:
- **"No TTS providers configured"**: Make sure `.env` file exists and has at least one provider key
- **"503 Service Unavailable"**: API key might be invalid, expired, or quota exceeded
- **Still using browser TTS**: Check backend logs to see if API key was loaded correctly

### Azure-Specific:
- **"Azure TTS credentials not found"**: Make sure both `AZURE_TTS_KEY` and `AZURE_TTS_REGION` are set
- **"401 Unauthorized"**: Check that your API key is correct and the Speech Services resource is active
- **Region not found**: Make sure region matches exactly (e.g., `eastus`, not `East US`)

### Google-Specific:
- **"Google TTS credentials not found"**: Set either `GOOGLE_TTS_KEY` (API key) or `GOOGLE_APPLICATION_CREDENTIALS` (service account)
- **"403 Forbidden"**: Make sure Text-to-Speech API is enabled in Google Cloud Console
- **"Service account key not found"**: Check that path in `GOOGLE_APPLICATION_CREDENTIALS` is absolute and file exists
- **"Module not found: google.cloud"**: Install with `pip install google-cloud-texttospeech` (only needed for service account method)

