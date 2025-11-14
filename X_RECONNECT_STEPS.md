# Reconnect X Account with New App

## ✅ What's Done
- ✅ New OAuth 2.0 credentials updated in `.env`
- ✅ Old tokens deleted (`.x_tokens.json`)

## Next Steps

### 1. Restart Backend
The backend needs to reload the new credentials from `.env`:

```bash
# Stop the current backend (Ctrl+C)
# Then restart:
python backend/run.py
```

### 2. Reconnect X Account
Open this URL in your browser:
```
http://localhost:8000/x/auth/authorize
```

You'll be redirected to X to authorize the new app. After authorization, you'll be redirected back to the callback URL.

### 3. Test Connection
After reconnecting, test if it works:

```bash
# Check connection status
curl http://localhost:8000/x/auth/status | python3 -m json.tool

# Test fetching followed accounts (should work now!)
curl http://localhost:8000/x/test/following | python3 -m json.tool
```

## Expected Results

✅ `auth/status` should show:
```json
{
  "connected": true,
  "configured": true,
  "user_id": "your_x_user_id"
}
```

✅ `test/following` should show:
```json
{
  "status_code": 200,
  "response": {
    "accounts": [...],
    "count": 5
  }
}
```

**No more 403 errors!** 🎉

