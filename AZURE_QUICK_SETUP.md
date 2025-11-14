# Quick Azure TTS Setup Guide

## You Found Your Region! ✅

From your URL `https://eastus.stt.speech.microsoft.com`, I can see your region is: **`eastus`**

## Now Get Your API Key:

1. **Go to Azure Portal:**
   - Visit: https://portal.azure.com/
   - Sign in to your account

2. **Find Your Speech Services Resource:**
   - In the search bar at the top, type "Speech" or "Speech Services"
   - Click on your Speech Services resource (the one you created)

3. **Get Your API Key:**
   - In the left sidebar, click **"Keys and Endpoint"**
   - You'll see two keys: **Key 1** and **Key 2** (either one works)
   - Copy one of the keys (it will look like: `abc123def456ghi789jkl012mno345pqr678`)

4. **Add to Your `.env` File:**
   ```env
   AZURE_TTS_KEY=your_copied_key_here
   AZURE_TTS_REGION=eastus
   ```

   **Example:**
   ```env
   AZURE_TTS_KEY=abc123def456ghi789jkl012mno345pqr678stu901vwx234yz
   AZURE_TTS_REGION=eastus
   ```

5. **Restart Your Backend:**
   ```bash
   # Stop current server (Ctrl+C) and restart
   python backend/run.py
   ```

6. **Test It:**
   ```bash
   # Check if Azure is detected
   curl http://localhost:8000/voice/providers
   
   # Test Azure TTS
   curl -X POST http://localhost:8000/voice/synthesize \
     -H "Content-Type: application/json" \
     -d '{"text": "Testing Azure voice", "priority": "medium", "provider": "azure"}'
   ```

## Visual Guide:

1. Azure Portal → Search "Speech" → Click your resource
2. Left sidebar → "Keys and Endpoint"
3. Copy **Key 1** or **Key 2**
4. Copy the **Location/Region** (you already have: `eastus`)

That's it! Once you add both to `.env` and restart, Azure TTS will be available.

