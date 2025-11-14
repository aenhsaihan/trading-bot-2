# X (Twitter) Integration Setup Guide

## Prerequisites

1. **X Developer Account**
   - Go to https://developer.twitter.com/
   - Sign up for developer access (free tier available)
   - Create a new App

2. **Get API Credentials**
   - API Key (`X_CLIENT_ID`)
   - API Secret (`X_CLIENT_SECRET`)
   - Bearer Token (optional, for some endpoints)

3. **Configure OAuth**
   - Enable OAuth 2.0 in your X App settings
   - Set callback URL: `http://localhost:8000/api/x/callback` (for development)
   - Request permissions: `tweet.read`, `users.read`, `follows.read`, `offline.access`

## Environment Variables

Add to your `.env` file:

```env
# X (Twitter) OAuth Credentials
X_CLIENT_ID=your_client_id_here
X_CLIENT_SECRET=your_client_secret_here
X_REDIRECT_URI=http://localhost:8000/api/x/callback
```

## Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Restart backend server:**
   ```bash
   python backend/run.py
   ```

## Usage

### 1. Connect X Account

1. Open frontend: `http://localhost:5173`
2. Go to Settings
3. Click "Connect X Account"
4. Authorize the app on X
5. You'll be redirected back to settings

### 2. Start Monitoring

1. After connecting, click "Start Monitoring"
2. System will fetch accounts you follow
3. Polls every 5 minutes for new tweets
4. New tweets become notifications automatically

### 3. View Notifications

- X notifications appear in the notification feed
- They get AI-summarized messages (StarCraft-style)
- Voice alerts work automatically
- Source badge shows "X" or Twitter icon

## API Endpoints

### Authentication

- `GET /api/x/auth/status` - Check connection status
- `GET /api/x/auth/authorize` - Initiate OAuth flow
- `GET /api/x/auth/callback` - OAuth callback (handled automatically)
- `POST /api/x/auth/disconnect` - Disconnect X account

### Monitoring

- `GET /api/x/monitoring/status` - Get monitoring status
- `GET /api/x/monitoring/accounts` - Get followed accounts
- `POST /api/x/monitoring/refresh` - Refresh followed accounts list
- `POST /api/x/monitoring/start` - Start monitoring
- `POST /api/x/monitoring/stop` - Stop monitoring

## How It Works

1. **OAuth Flow:**
   - User clicks "Connect X Account"
   - Redirected to X authorization page
   - User authorizes app
   - Redirected back with authorization code
   - Backend exchanges code for access/refresh tokens
   - Tokens stored (in-memory for MVP)

2. **Monitoring:**
   - Fetches list of accounts user follows
   - Polls each account's timeline every 5 minutes
   - Detects new tweets (using `since_id`)
   - Converts tweets to notifications
   - Creates notifications via NotificationService
   - AI summarizes messages
   - Voice alerts delivered

3. **Notification Conversion:**
   - Extracts crypto symbols (BTC, ETH, etc.)
   - Determines priority (based on author, engagement)
   - Determines notification type (technical, news, risk, etc.)
   - Creates notification with metadata

## Troubleshooting

### "X OAuth not configured"
- Make sure `X_CLIENT_ID` and `X_CLIENT_SECRET` are set in `.env`
- Restart backend server after adding env vars

### "X account not connected"
- Go to Settings and connect your X account
- Make sure OAuth callback URL matches in X App settings

### "Rate limit exceeded"
- X API has rate limits (varies by endpoint)
- System respects rate limits automatically
- Wait a few minutes and try again

### "No followed accounts"
- Make sure you're following accounts on X
- Click "Refresh" to reload followed accounts list

### Monitoring not working
- Check connection status: `GET /api/x/auth/status`
- Check monitoring status: `GET /api/x/monitoring/status`
- Make sure monitoring is started: `POST /api/x/monitoring/start`

## Next Steps

After MVP is working:
- Add keyword filtering
- Add sentiment analysis
- Add priority scoring
- Add duplicate detection
- Switch to streaming API (real-time)

