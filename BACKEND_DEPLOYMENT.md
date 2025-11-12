# FastAPI Backend Deployment Guide

## Architecture Overview

```
┌─────────────────┐         HTTP/WebSocket        ┌──────────────────┐
│  Streamlit App  │ ────────────────────────────> │  FastAPI Backend │
│  (Port 8501)    │                               │  (Port 8000)     │
└─────────────────┘                               └──────────────────┘
```

**Key Points:**
- Streamlit and FastAPI are **separate services** running on different ports
- Streamlit calls FastAPI via HTTP requests (REST API)
- For real-time updates, Streamlit can poll the API (or use WebSocket client in custom component)
- Both services need to be deployed and accessible to each other

## Deployment Options

### Option 1: Same Server, Different Ports (Recommended for Start)

**Setup:**
- Streamlit: Port 8501 (default)
- FastAPI: Port 8000
- Both on same server/container

**Pros:**
- Simple deployment
- Low latency (localhost)
- Easy to manage

**Cons:**
- Both services must be running
- Need to manage two processes

**Implementation:**
```bash
# Start FastAPI backend
python backend/run.py  # Runs on port 8000

# Start Streamlit (in another terminal or as background process)
streamlit run src/monitoring/dashboard_app.py  # Runs on port 8501
```

### Option 2: Separate Services (Production)

**Setup:**
- Streamlit: Streamlit Cloud (or your hosting)
- FastAPI: Separate service (Railway, Render, Fly.io, AWS, etc.)

**Pros:**
- Scalable independently
- Better resource management
- Can use different hosting providers

**Cons:**
- More complex setup
- Need to configure CORS
- Network latency between services

### Option 3: Docker Compose (Best for Self-Hosted)

**Setup:**
- Both services in Docker containers
- Same network, different ports
- Easy to deploy together

## Streamlit Integration

### How Streamlit Calls FastAPI

Streamlit can call the FastAPI backend using `requests`:

```python
import requests
import streamlit as st

# Get API URL from environment or config
API_URL = st.secrets.get("API_URL", "http://localhost:8000")

# Create notification
def create_notification(title, message, priority="info"):
    response = requests.post(
        f"{API_URL}/notifications",
        json={
            "type": "system_status",
            "priority": priority,
            "title": title,
            "message": message,
            "source": "system"
        }
    )
    return response.json()

# Get notifications
def get_notifications():
    response = requests.get(f"{API_URL}/notifications")
    return response.json()
```

### Real-Time Updates in Streamlit

Since Streamlit is server-side Python, WebSockets are tricky. Options:

1. **Polling** (Simple):
```python
import time

if st.button("Refresh"):
    notifications = get_notifications()
    st.json(notifications)

# Auto-refresh every 5 seconds
if st.checkbox("Auto-refresh"):
    time.sleep(5)
    st.rerun()
```

2. **Custom Streamlit Component** (Advanced):
   - Create a React component that connects to WebSocket
   - Embed in Streamlit via `streamlit.components.v1`
   - Component handles WebSocket, Streamlit handles UI

3. **Hybrid Approach** (Recommended):
   - Keep Streamlit for main dashboard
   - Build separate React app for notifications
   - Both call same FastAPI backend

## Environment Configuration

### Streamlit Secrets (`.streamlit/secrets.toml`)

```toml
[api]
url = "http://localhost:8000"  # Local development
# url = "https://your-api.railway.app"  # Production
```

### FastAPI Environment Variables

```bash
# .env file
CORS_ORIGINS=http://localhost:8501,https://your-streamlit-app.streamlit.app
API_HOST=0.0.0.0
API_PORT=8000
```

## Deployment Steps

### For Streamlit Cloud

1. **Deploy FastAPI separately** (Railway, Render, Fly.io, etc.)
2. **Add API URL to Streamlit secrets**:
   ```toml
   [api]
   url = "https://your-api.railway.app"
   ```
3. **Update Streamlit code** to use `st.secrets["api"]["url"]`
4. **Configure CORS** in FastAPI to allow Streamlit Cloud domain

### For Self-Hosted (Docker)

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  streamlit:
    build: .
    ports:
      - "8501:8501"
    environment:
      - API_URL=http://api:8000
    depends_on:
      - api

  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    ports:
      - "8000:8000"
    environment:
      - CORS_ORIGINS=http://localhost:8501
```

## Current Implementation

The FastAPI backend is **ready to use** but needs to be:

1. **Started separately** from Streamlit
2. **Configured** with correct API URL in Streamlit
3. **Updated** in Streamlit code to call API instead of direct NotificationManager

## Next Steps

1. **Create Streamlit API client** - Helper functions to call FastAPI
2. **Update Streamlit dashboard** - Use API client instead of direct NotificationManager
3. **Add environment config** - API URL configuration
4. **Deploy FastAPI** - Choose hosting and deploy
5. **Update Streamlit secrets** - Add API URL

## Quick Start (Local Development)

```bash
# Terminal 1: Start FastAPI backend
cd /path/to/trading-bot-2
python backend/run.py

# Terminal 2: Start Streamlit
streamlit run src/monitoring/dashboard_app.py

# Both services running:
# - FastAPI: http://localhost:8000
# - Streamlit: http://localhost:8501
```

## Production Checklist

- [ ] Deploy FastAPI backend to hosting service
- [ ] Configure CORS for Streamlit domain
- [ ] Add API URL to Streamlit secrets
- [ ] Update Streamlit code to use API client
- [ ] Test end-to-end
- [ ] Set up monitoring/logging
- [ ] Configure SSL/HTTPS
- [ ] Set up authentication (if needed)

