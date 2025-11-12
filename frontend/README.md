# Trading Bot Notification Frontend

Modern React frontend for real-time trading bot notifications.

## Features

- ✅ **Real-time WebSocket updates** - Instant notifications
- ✅ **Beautiful toast notifications** - Slide in from top-right
- ✅ **Voice alerts** - Web Speech API (StarCraft-style)
- ✅ **Notification center** - Full history and filtering
- ✅ **Modern UI** - Tailwind CSS + Framer Motion
- ✅ **Type-safe** - TypeScript throughout

## Quick Start

### Install Dependencies

```bash
cd frontend
npm install
```

### Start Development Server

```bash
npm run dev
```

The app will run on http://localhost:3000

### Build for Production

```bash
npm run build
npm run preview
```

## Configuration

Create a `.env` file (optional):

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws/notifications
```

## Architecture

```
frontend/
├── src/
│   ├── components/        # React components
│   │   ├── ToastNotification.tsx    # Toast component
│   │   ├── ToastContainer.tsx       # Toast manager
│   │   ├── NotificationCard.tsx     # Notification card
│   │   ├── NotificationCenter.tsx   # Main center UI
│   │   └── SystemStatus.tsx         # Status indicator
│   ├── hooks/
│   │   └── useNotifications.ts      # WebSocket hook
│   ├── services/
│   │   └── api.ts                    # API client
│   ├── types/
│   │   └── notification.ts          # TypeScript types
│   ├── utils/
│   │   └── voice.ts                 # Voice alerts
│   ├── App.tsx                      # Main app
│   └── main.tsx                     # Entry point
├── package.json
└── vite.config.ts
```

## Integration

This frontend connects to your FastAPI backend:
- **REST API**: `http://localhost:8000/notifications`
- **WebSocket**: `ws://localhost:8000/ws/notifications`

Make sure the FastAPI backend is running!

## Next Steps

1. **Start FastAPI backend**: `python backend/run.py`
2. **Start React frontend**: `npm run dev`
3. **Create notifications** via API or Streamlit
4. **See them appear** in real-time! 🎉

