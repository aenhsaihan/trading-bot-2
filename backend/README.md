# FastAPI Backend - Trading Bot Notifications

FastAPI backend providing REST API and WebSocket support for real-time notifications.

## Quick Start

```bash
# Install dependencies (if not already installed)
pip install fastapi uvicorn[standard] websockets pydantic

# Run the server
python backend/run.py

# Or use uvicorn directly
uvicorn backend.api.main:app --reload --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs (Swagger UI)
- **WebSocket**: ws://localhost:8000/ws/notifications

## API Endpoints

### REST API

- `GET /notifications` - Get all notifications (supports `limit` and `unread_only` query params)
- `GET /notifications/{id}` - Get specific notification
- `POST /notifications` - Create new notification
- `PATCH /notifications/{id}` - Update notification (mark as read, respond)
- `POST /notifications/{id}/respond` - Respond to notification
- `DELETE /notifications/{id}` - Delete notification
- `GET /notifications/stats/summary` - Get statistics

### WebSocket

- `ws://localhost:8000/ws/notifications` - Real-time notification stream

## Example Usage

### Create a notification (REST API)

```bash
curl -X POST "http://localhost:8000/notifications" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "combined_signal",
    "priority": "critical",
    "title": "Strong Buy Signal",
    "message": "BTC/USDT showing strong buy signal with 85% confidence",
    "source": "combined",
    "symbol": "BTC/USDT",
    "confidence_score": 85.0,
    "urgency_score": 90.0,
    "promise_score": 88.0
  }'
```

### Connect to WebSocket (Python)

```python
import asyncio
import websockets
import json

async def listen_notifications():
    uri = "ws://localhost:8000/ws/notifications"
    async with websockets.connect(uri) as websocket:
        # Send ping to keep connection alive
        await websocket.send("ping")
        
        # Listen for notifications
        async for message in websocket:
            data = json.loads(message)
            print(f"New notification: {data['title']}")

asyncio.run(listen_notifications())
```

### Connect to WebSocket (JavaScript)

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/notifications');

ws.onopen = () => {
  console.log('Connected to notification stream');
  ws.send('ping'); // Keep connection alive
};

ws.onmessage = (event) => {
  const notification = JSON.parse(event.data);
  console.log('New notification:', notification);
  // Show toast notification, update UI, etc.
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('Disconnected from notification stream');
};
```

## Architecture

```
backend/
├── api/
│   ├── main.py              # FastAPI app
│   ├── routes/
│   │   ├── notifications.py # REST API routes
│   │   └── websocket.py     # WebSocket handler
│   └── models/
│       └── notification.py  # Pydantic models
├── services/
│   └── notification_service.py  # Business logic (wraps NotificationManager)
└── run.py                   # Startup script
```

## Integration with Streamlit

The Streamlit dashboard can call the FastAPI backend:

```python
import requests

# Create notification
response = requests.post(
    "http://localhost:8000/notifications",
    json={
        "type": "combined_signal",
        "priority": "critical",
        "title": "Alert",
        "message": "Message here",
        "source": "system"
    }
)
```

## Next Steps

1. **React Frontend** - Build modern notification UI with WebSocket support
2. **Authentication** - Add auth for production
3. **Rate Limiting** - Add rate limiting for API endpoints
4. **Persistence** - Add database persistence for notifications
5. **Deployment** - Deploy to production (Docker, cloud, etc.)

