# X Free Tier - Quick Start

## What This Does

✅ **Works with Free tier** - Uses Bearer token, no OAuth needed
✅ **Manual account list** - You specify which accounts to monitor
✅ **Real notifications** - Converts tweets to notifications with AI + voice
✅ **No upgrade required** - Works right now!

## Quick Setup (3 Steps)

### 1. Add Bearer Token to `.env`
```env
X_BEARER_TOKEN=AAAAAAAAAAAAAAAAAAAAAMq35QEAAAAA%2BwYvHJnl4pg0CilErvEE0Otq%2FY0%3D6ZsKuOw3fCNRNl0pd45X6cjJOdqZElL0cxS0FeSWR1qfZqgGsj
```

### 2. Add Accounts to Monitor
```env
X_MONITOR_ACCOUNTS=elonmusk,VitalikButerin,cz_binance
```

**Or add via API after starting:**
```bash
curl -X POST http://localhost:8000/x/simple/accounts/add \
  -H "Content-Type: application/json" \
  -d '{"username_or_id": "elonmusk"}'
```

### 3. Start Monitoring
```bash
curl -X POST http://localhost:8000/x/simple/start
```

## That's It! 🎉

Now:
- ✅ Monitoring polls every 5 minutes
- ✅ New tweets become notifications
- ✅ AI summarizes them (StarCraft-style)
- ✅ Voice alerts play (if enabled)
- ✅ Crypto symbols are detected

## Check Status

```bash
curl http://localhost:8000/x/simple/status | python3 -m json.tool
```

## Example: Monitor Crypto Accounts

```bash
# Add popular crypto accounts
curl -X POST http://localhost:8000/x/simple/accounts/add \
  -H "Content-Type: application/json" \
  -d '{"username_or_id": "elonmusk"}'

curl -X POST http://localhost:8000/x/simple/accounts/add \
  -H "Content-Type: application/json" \
  -d '{"username_or_id": "VitalikButerin"}'

curl -X POST http://localhost:8000/x/simple/accounts/add \
  -H "Content-Type: application/json" \
  -d '{"username_or_id": "cz_binance"}'

# Start monitoring
curl -X POST http://localhost:8000/x/simple/start

# Check status
curl http://localhost:8000/x/simple/status | python3 -m json.tool
```

## What You'll See

When a monitored account tweets:
1. **Backend**: Fetches tweet, converts to notification
2. **AI**: Summarizes it (StarCraft-style)
3. **Frontend**: Shows notification in UI
4. **Voice**: Speaks the summarized message (if enabled)

## Troubleshooting

**"Bearer token not configured"**
- Check `.env` has `X_BEARER_TOKEN`
- Restart backend

**"No accounts to monitor"**
- Add accounts via `.env` or API
- Check with: `curl http://localhost:8000/x/simple/accounts`

**"Could not resolve username"**
- Verify username is correct (no @)
- Try user ID instead

## Next Steps

Once you see it working:
- Add more accounts
- Customize poll interval (default: 5 min)
- Build frontend UI to manage accounts
- Upgrade to Basic tier later for automatic following

