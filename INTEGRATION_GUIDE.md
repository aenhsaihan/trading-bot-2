# Streamlit + FastAPI Integration Guide

## Current Situation

**Streamlit doesn't automatically know about FastAPI.** They are separate services that need to be connected.

## How It Works

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Your Server/Cloud                     │
│                                                          │
│  ┌──────────────┐              ┌──────────────┐        │
│  │   Streamlit   │   HTTP       │   FastAPI    │        │
│  │   Port 8501  │ ───────────> │   Port 8000  │        │
│  │              │   Requests   │              │        │
│  └──────────────┘              └──────────────┘        │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Two Deployment Scenarios

#### Scenario 1: Streamlit Cloud (Current)

**Problem:** Streamlit Cloud only runs your Streamlit app. FastAPI needs separate hosting.

**Solution:**
1. Deploy FastAPI to separate service (Railway, Render, Fly.io, etc.)
2. Streamlit calls FastAPI via HTTP (public URL)
3. Configure CORS in FastAPI to allow Streamlit Cloud domain

**Example:**
- Streamlit: `https://your-app.streamlit.app` (Streamlit Cloud)
- FastAPI: `https://your-api.railway.app` (Railway)
- Streamlit calls FastAPI via `https://your-api.railway.app`

#### Scenario 2: Self-Hosted (Both on Same Server)

**Solution:**
1. Run both services on same server
2. Streamlit calls FastAPI via `http://localhost:8000` (same server)
3. Both accessible via different ports

**Example:**
- Streamlit: `http://your-server.com:8501`
- FastAPI: `http://your-server.com:8000`
- Streamlit calls FastAPI via `http://localhost:8000` (internal)

## Implementation Steps

### Step 1: Create API Client (✅ Done)

I've created `src/monitoring/api_client.py` - a helper class for Streamlit to call FastAPI.

### Step 2: Update Streamlit Code

**Option A: Use API Client (Recommended)**

```python
from src.monitoring.api_client import NotificationAPIClient

# Initialize client (reads URL from secrets or defaults to localhost)
api_client = NotificationAPIClient()

# Create notification
api_client.create_notification(
    notification_type="combined_signal",
    priority="critical",
    title="Alert",
    message="Message here",
    source="system"
)

# Get notifications
notifications = api_client.get_notifications()
```

**Option B: Keep Direct NotificationManager (Fallback)**

If FastAPI is not available, fall back to direct NotificationManager:

```python
from src.monitoring.api_client import NotificationAPIClient
from src.notifications.notification_manager import NotificationManager

# Try API first, fallback to direct manager
try:
    api_client = NotificationAPIClient()
    if api_client.health_check():
        # Use API
        notifications = api_client.get_notifications()
    else:
        raise ConnectionError("API not available")
except:
    # Fallback to direct manager
    notification_manager = NotificationManager()
    notifications = notification_manager.get_all()
```

### Step 3: Configure API URL

**For Local Development:**
```bash
# .streamlit/secrets.toml
[api]
url = "http://localhost:8000"
```

**For Production (Streamlit Cloud):**
```bash
# Add to Streamlit Cloud secrets (via UI)
api.url = "https://your-api.railway.app"
```

### Step 4: Start Both Services

**Local Development:**
```bash
# Terminal 1: Start FastAPI
python backend/run.py

# Terminal 2: Start Streamlit
streamlit run src/monitoring/dashboard_app.py
```

**Production:**
- Deploy FastAPI to hosting service (Railway, Render, etc.)
- Deploy Streamlit to Streamlit Cloud
- Configure API URL in Streamlit Cloud secrets

## Migration Path

### Phase 1: Hybrid (Current)
- Keep existing NotificationManager code
- Add API client as optional
- Test both approaches

### Phase 2: Full API (Future)
- Replace NotificationManager calls with API client
- Remove direct NotificationManager usage
- All notifications go through API

### Phase 3: React Frontend (Future)
- Build React app for notifications
- React connects to FastAPI via WebSocket
- Streamlit still uses API for dashboard

## Quick Test

```python
# In Streamlit app
from src.monitoring.api_client import NotificationAPIClient

api_client = NotificationAPIClient()

# Check if API is available
if api_client.health_check():
    st.success("✅ FastAPI backend is connected")
    notifications = api_client.get_notifications()
    st.json(notifications)
else:
    st.warning("⚠️ FastAPI backend not available, using direct NotificationManager")
    # Fallback to direct manager
```

## Summary

**Streamlit doesn't automatically know about FastAPI** - you need to:

1. ✅ **API Client created** - Helper class ready
2. ⏳ **Update Streamlit code** - Use API client instead of direct manager
3. ⏳ **Configure API URL** - Add to secrets/config
4. ⏳ **Deploy FastAPI** - Separate service or same server
5. ⏳ **Test connection** - Verify Streamlit can reach FastAPI

The API client handles all the HTTP communication - Streamlit just calls methods like `api_client.get_notifications()`.

