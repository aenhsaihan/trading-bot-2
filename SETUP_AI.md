# AI Service Setup Guide

## Quick Setup with Groq (Free)

### 1. Get Your Free Groq API Key

1. Go to https://console.groq.com/
2. Sign up for a free account (no credit card required)
3. Create an API key
4. Copy your API key

### 2. Set Your API Key

**Option A: Using .env file (Recommended)**

Create a `.env` file in the project root:

```bash
cd /Users/anar_enhsaihan/Documents/playground/composer/trading-bot-2
echo "GROQ_API_KEY=your_actual_api_key_here" > .env
```

Replace `your_actual_api_key_here` with your actual Groq API key.

**Option B: Export in Terminal (Temporary)**

```bash
export GROQ_API_KEY='your_actual_api_key_here'
```

This only works for the current terminal session. To make it permanent, add it to your `~/.zshrc` or `~/.bashrc`:

```bash
echo 'export GROQ_API_KEY="your_actual_api_key_here"' >> ~/.zshrc
source ~/.zshrc
```

### 3. Install Dependencies

The `groq` package should already be installed. If not:

```bash
pip install groq
# or if using venv:
source venv/bin/activate
pip install groq
```

### 4. Restart Backend Server

If your backend is running, restart it to load the new environment variable:

```bash
# Stop the current server (Ctrl+C)
# Then restart:
python backend/run.py
```

### 5. Test It

1. Open the frontend
2. Go to Command Center tab
3. You should see the AI status indicator (no warning)
4. Try chatting or selecting a notification to see AI analysis

### Verify It's Working

Check the backend logs - you should see:
```
AI Service initialized with Groq (free tier)
```

Or test the API directly:
```bash
curl http://localhost:8000/ai/status
```

Should return:
```json
{
  "enabled": true,
  "available": true,
  "provider": "groq"
}
```

## Using OpenAI Instead (Paid)

If you prefer OpenAI:

1. Set `OPENAI_API_KEY` instead:
   ```bash
   export OPENAI_API_KEY='your_openai_key'
   ```

2. The service will automatically use OpenAI if Groq is not configured.

## Troubleshooting

- **"AI not configured" warning**: Make sure the API key is set and the backend was restarted
- **Import errors**: Run `pip install groq` (or `pip install openai` for OpenAI)
- **Still not working**: Check backend logs for error messages

