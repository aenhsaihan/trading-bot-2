# How to Start the FastAPI Backend

## Prerequisites

Make sure you're using the virtual environment:

```bash
cd /Users/anar_enhsaihan/Documents/playground/composer/trading-bot-2
source venv/bin/activate
```

## Install Dependencies (if not already installed)

```bash
pip install fastapi uvicorn[standard] websockets pydantic
```

## Start the Backend

```bash
python backend/run.py
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

## Verify It's Running

Open in browser:
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

Or test with curl:
```bash
curl http://localhost:8000/health
```

Should return: `{"status":"healthy"}`

## Running Both Services

**Terminal 1** - FastAPI Backend:
```bash
cd /Users/anar_enhsaihan/Documents/playground/composer/trading-bot-2
source venv/bin/activate
python backend/run.py
```

**Terminal 2** - Streamlit Dashboard:
```bash
cd /Users/anar_enhsaihan/Documents/playground/composer/trading-bot-2
source venv/bin/activate
streamlit run src/monitoring/dashboard_app.py
```

## Test Creating a Notification

```bash
curl -X POST "http://localhost:8000/notifications" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "combined_signal",
    "priority": "critical",
    "title": "Test Notification",
    "message": "This is a test from the API",
    "source": "system",
    "symbol": "BTC/USDT",
    "confidence_score": 85.0
  }'
```

## What Happens

1. **Backend starts** → FastAPI server running on port 8000
2. **Streamlit starts** → Checks if backend is available
3. **If backend available** → Streamlit shows "✅ Connected to FastAPI backend"
4. **If backend not available** → Streamlit shows "ℹ️ Using direct NotificationManager" and works normally

## Troubleshooting

**Port already in use?**
```bash
# Find what's using port 8000
lsof -i :8000

# Kill it if needed
kill -9 <PID>
```

**Import errors?**
```bash
# Make sure you're in venv
source venv/bin/activate

# Install dependencies
pip install fastapi uvicorn[standard] websockets pydantic
```

**Backend won't start?**
- Make sure you're in the virtual environment: `source venv/bin/activate`
- Check Python version: `python --version` (should be 3.8+)
- Check if you're in the right directory
- Check for syntax errors: `python -m py_compile backend/api/main.py`
