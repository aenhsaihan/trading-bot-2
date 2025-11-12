# Frontend Migration Plan - Notification System

## Current State
- Streamlit dashboard for trading bot monitoring
- Python backend with trading logic, exchanges, strategies
- Notification system partially implemented (struggling with Streamlit limitations)

## Proposed Architecture

### Phase 1: Add FastAPI Backend (Week 1)
**Goal**: Create REST API + WebSocket server for notifications

**Structure**:
```
backend/
├── api/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── routes/
│   │   ├── notifications.py # Notification endpoints
│   │   ├── trading.py       # Trading endpoints
│   │   └── websocket.py     # WebSocket handler
│   └── models/
│       └── notification.py  # Pydantic models
├── services/
│   └── notification_service.py  # Business logic
└── requirements.txt
```

**Key Features**:
- REST API for notification CRUD
- WebSocket server for real-time push notifications
- Reuse existing `NotificationManager` from `src/notifications/`
- Keep Streamlit dashboard working (it can call API too)

### Phase 2: React Notification Frontend (Week 2)
**Goal**: Build modern notification UI

**Structure**:
```
frontend/
├── package.json
├── vite.config.js          # Vite for fast dev
├── src/
│   ├── App.tsx
│   ├── components/
│   │   ├── ToastNotification.tsx    # Toast component
│   │   ├── NotificationCenter.tsx   # Notification list
│   │   └── NotificationCard.tsx      # Individual card
│   ├── hooks/
│   │   └── useNotifications.ts      # WebSocket hook
│   ├── services/
│   │   └── api.ts                   # API client
│   └── styles/
│       └── toast.css                # Animations
└── public/
```

**Key Features**:
- Real-time WebSocket connection
- Beautiful toast notifications (slide in from top-right)
- Notification center with filtering
- Quick actions (Approve/Reject/Custom/Snooze)
- Voice alerts (Web Speech API)

### Phase 3: Integration (Week 3)
**Goal**: Connect everything together

- Streamlit dashboard calls FastAPI for notifications
- React app runs alongside Streamlit (different port)
- Or embed React app in Streamlit via iframe
- Shared authentication/session

## Technology Stack

### Backend
- **FastAPI** - Modern Python web framework
- **WebSockets** - Real-time notifications
- **Pydantic** - Data validation
- **Existing code** - Reuse `NotificationManager`, `NotificationType`, etc.

### Frontend
- **React + TypeScript** - Modern UI framework
- **Vite** - Fast build tool
- **Tailwind CSS** - Utility-first styling
- **Framer Motion** - Smooth animations
- **WebSocket API** - Real-time updates
- **Web Speech API** - Voice alerts

## Implementation Steps

### Step 1: FastAPI Backend (2-3 hours)
```python
# backend/api/main.py
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"])

@app.websocket("/ws/notifications")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    # Send notifications in real-time
```

### Step 2: React Toast Component (1-2 hours)
```tsx
// frontend/src/components/ToastNotification.tsx
export function ToastNotification({ notification, onDismiss }) {
  return (
    <motion.div
      initial={{ x: 400, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 400, opacity: 0 }}
      className="toast-notification"
    >
      <button onClick={onDismiss}>×</button>
      {/* Notification content */}
    </motion.div>
  );
}
```

### Step 3: WebSocket Hook (1 hour)
```tsx
// frontend/src/hooks/useNotifications.ts
export function useNotifications() {
  const [notifications, setNotifications] = useState([]);
  
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws/notifications');
    ws.onmessage = (event) => {
      const notification = JSON.parse(event.data);
      setNotifications(prev => [notification, ...prev]);
    };
    return () => ws.close();
  }, []);
  
  return notifications;
}
```

## Benefits

1. **Real Frontend Control** - No Streamlit limitations
2. **Real-time Updates** - WebSockets for instant notifications
3. **Beautiful UI** - Modern React components with animations
4. **Reusable Backend** - API can serve Streamlit, React, mobile app, etc.
5. **Incremental Migration** - Keep Streamlit working, add React gradually

## Migration Path

1. **Week 1**: Build FastAPI backend, keep Streamlit
2. **Week 2**: Build React notification UI
3. **Week 3**: Integrate, test, deploy
4. **Future**: Gradually migrate more Streamlit features to React if needed

## Quick Start Commands

```bash
# Backend
cd backend
pip install fastapi uvicorn websockets
uvicorn api.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev  # Runs on port 3000
```

## Decision

**Recommendation**: Start with Phase 1 (FastAPI backend). This gives you:
- Real-time WebSocket notifications
- REST API for notifications
- Keep Streamlit dashboard working
- Foundation for future React frontend

Then add React frontend when ready (or use it immediately for notifications).

Would you like me to:
1. **Start with FastAPI backend** (2-3 hours, immediate benefits)
2. **Build full React frontend** (more time, better UX)
3. **Both** (backend first, then frontend)

