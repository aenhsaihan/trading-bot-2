# Quick Start Guide - React Notification Frontend

## 🚀 Get Started in 3 Steps

### Step 1: Start FastAPI Backend

```bash
cd /Users/anar_enhsaihan/Documents/playground/composer/trading-bot-2
source venv/bin/activate
python backend/run.py
```

Backend runs on: **http://localhost:8000**

### Step 2: Start React Frontend

**In a new terminal:**

```bash
cd /Users/anar_enhsaihan/Documents/playground/composer/trading-bot-2/frontend
npm install  # First time only
npm run dev
```

Frontend runs on: **http://localhost:3000**

### Step 3: Test It!

**Create a notification via API:**

```bash
curl -X POST "http://localhost:8000/notifications/" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "combined_signal",
    "priority": "critical",
    "title": "🚀 Strong Buy Signal",
    "message": "BTC/USDT showing strong buy signal with 90% confidence!",
    "source": "system",
    "symbol": "BTC/USDT",
    "confidence_score": 90.0,
    "urgency_score": 95.0,
    "promise_score": 92.0,
    "actions": ["Approve", "Reject", "Custom"]
  }'
```

**What you'll see:**
1. ✅ Toast notification slides in from top-right
2. 🔊 Voice alert plays the message
3. 📋 Notification appears in the center
4. 🔄 Real-time updates via WebSocket

## 🎯 What You Get

- **Real-time notifications** - WebSocket updates instantly
- **Beautiful toasts** - Slide in animations, auto-dismiss
- **Voice alerts** - Web Speech API (StarCraft-style)
- **Notification center** - Full history, filtering, actions
- **Modern UI** - Dark theme, smooth animations
- **Type-safe** - TypeScript throughout

## 🔧 Troubleshooting

**Frontend won't start?**
```bash
cd frontend
npm install
npm run dev
```

**Backend connection failed?**
- Make sure FastAPI is running on port 8000
- Check `http://localhost:8000/health`

**No notifications showing?**
- Check browser console for errors
- Verify WebSocket connection (should show "Connected" in header)
- Try creating a notification via API

## 📁 Project Structure

```
trading-bot-2/
├── backend/          # FastAPI backend (KEEP - it's good!)
├── frontend/         # React frontend (NEW!)
├── src/              # Core trading logic (KEEP - it's good!)
└── ...
```

## 🎨 Features

- ✅ Real-time WebSocket updates
- ✅ Toast notifications with animations
- ✅ Voice alerts
- ✅ Notification filtering
- ✅ Mark as read / Respond actions
- ✅ System status indicator
- ✅ Connection status

## 🚀 Next Steps

1. **Customize styling** - Edit `tailwind.config.js`
2. **Add more features** - Extend components
3. **Deploy** - Build with `npm run build`
4. **Integrate** - Connect to Streamlit or use standalone

Enjoy your notification-first UI! 🎉

