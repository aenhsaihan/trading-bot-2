# X Free Tier Setup Guide

## Overview

This is a **simplified X integration** that works with the **Free tier** by:
- Using **Bearer token** (no OAuth required)
- **Manually configuring** accounts to monitor (no `/users/:id/following` endpoint needed)
- Polling tweets from specific accounts periodically

## How It Works

1. **Bearer Token**: Uses your `X_BEARER_TOKEN` from `.env` to authenticate
2. **Manual Account List**: You specify which X accounts to monitor (usernames or user IDs)
3. **Polling**: Checks for new tweets every 5 minutes (configurable)
4. **Notifications**: Converts tweets to notifications with AI summarization and voice alerts

## Setup

### 1. Get Your Bearer Token

You already have this from your X Developer Portal:
```
X_BEARER_TOKEN=AAAAAAAAAAAAAAAAAAAAAMq35QEAAAAA%2BwYvHJnl4pg0CilErvEE0Otq%2FY0%3D6ZsKuOw3fCNRNl0pd45X6cjJOdqZElL0cxS0FeSWR1qfZqgGsj
```

### 2. Configure Accounts to Monitor

Add to your `.env` file:
```env
X_BEARER_TOKEN=AAAAAAAAAAAAAAAAAAAAAMq35QEAAAAA%2BwYvHJnl4pg0CilErvEE0Otq%2FY0%3D6ZsKuOw3fCNRNl0pd45X6cjJOdqZElL0cxS0FeSWR1qfZqgGsj
X_MONITOR_ACCOUNTS=elonmusk,VitalikButerin,cz_binance
```

**Format**: Comma-separated list of usernames (without @) or user IDs

**Examples**:
- Usernames: `elonmusk,VitalikButerin,cz_binance`
- User IDs: `44196397,295218901,877807935493033984`
- Mixed: `elonmusk,44196397,VitalikButerin`

### 3. Restart Backend

```bash
python backend/run.py
```

## API Endpoints

### Get Status
```bash
curl http://localhost:8000/x/simple/status
```

### Get Monitored Accounts
```bash
curl http://localhost:8000/x/simple/accounts
```

### Add Account (via API)
```bash
curl -X POST http://localhost:8000/x/simple/accounts/add \
  -H "Content-Type: application/json" \
  -d '{"username_or_id": "elonmusk"}'
```

### Remove Account
```bash
curl -X DELETE http://localhost:8000/x/simple/accounts/elonmusk
```

### Start Monitoring
```bash
curl -X POST http://localhost:8000/x/simple/start
```

### Stop Monitoring
```bash
curl -X POST http://localhost:8000/x/simple/stop
```

## How It Works

1. **Account Resolution**: If you provide a username, it resolves to user ID using `/users/by/username/:username`
2. **Tweet Fetching**: Uses `/users/:id/tweets` endpoint with Bearer token
3. **Deduplication**: Tracks last seen tweet ID per account to avoid duplicates
4. **Notification Creation**: Converts tweets to notifications with:
   - AI summarization (StarCraft-style)
   - Voice alerts (if enabled)
   - Crypto symbol detection
   - Priority determination

## Free Tier Limitations

- ✅ **Works**: Reading tweets from specific users (if you know their username/ID)
- ✅ **Works**: Bearer token authentication
- ❌ **Doesn't work**: Fetching list of followed accounts (`/users/:id/following`)
- ❌ **Doesn't work**: OAuth 2.0 user-specific endpoints (without Basic tier)

## Testing

1. **Add a test account**:
   ```bash
   curl -X POST http://localhost:8000/x/simple/accounts/add \
     -H "Content-Type: application/json" \
     -d '{"username_or_id": "elonmusk"}'
   ```

2. **Start monitoring**:
   ```bash
   curl -X POST http://localhost:8000/x/simple/start
   ```

3. **Check status**:
   ```bash
   curl http://localhost:8000/x/simple/status | python3 -m json.tool
   ```

4. **Wait for new tweets** (monitoring polls every 5 minutes)

5. **Check notifications** in your frontend - you should see new notifications appear!

## Troubleshooting

### "Bearer token not configured"
- Make sure `X_BEARER_TOKEN` is set in `.env`
- Restart backend after adding it

### "No accounts to monitor"
- Set `X_MONITOR_ACCOUNTS` in `.env` or use API to add accounts
- Format: comma-separated usernames (without @)

### "Could not resolve username"
- Check if username is correct (no @ symbol)
- Some accounts might be private or suspended
- Try using user ID instead

### Rate Limits
- Free tier has rate limits (check X API docs)
- Default poll interval is 5 minutes (300 seconds)
- Adjust `poll_interval` in code if needed

## Next Steps

Once this works, you can:
1. Add more accounts to monitor
2. Customize notification priorities per account
3. Add frontend UI to manage monitored accounts
4. Upgrade to Basic tier later for automatic following list

