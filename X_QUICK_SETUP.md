# X Integration Quick Setup

## Step 1: Add Credentials to .env

Add these lines to your `.env` file (in project root):

```env
# X (Twitter) OAuth Credentials
X_CLIENT_ID=your_client_id_here
X_CLIENT_SECRET=your_client_secret_here
X_REDIRECT_URI=http://localhost:8000/api/x/callback
```

**Important:** Replace `your_client_id_here` and `your_client_secret_here` with your actual credentials from X Developer Portal.

## Step 2: Configure OAuth Callback in X Developer Portal

1. Go to https://developer.twitter.com/en/portal/dashboard
2. Click on your App
3. Go to "Settings" → "User authentication settings"
4. Add callback URL: `http://localhost:8000/api/x/callback`
5. Enable OAuth 2.0
6. Set app permissions:
   - ✅ Read tweets
   - ✅ Read users
   - ✅ Read follows
   - ✅ Offline access (for refresh tokens)
7. Save changes

## Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

This will install `twitter-api-v2` if not already installed.

## Step 4: Restart Backend

If your backend is running, restart it:

```bash
# Stop current server (Ctrl+C)
python backend/run.py
```

## Step 5: Test the Setup

### Test 1: Check if credentials are loaded

```bash
curl http://localhost:8000/api/x/auth/status
```

Should return:
```json
{
  "connected": false,
  "configured": true,
  "user_id": null
}
```

If `configured: false`, check that your `.env` file has the correct variable names.

### Test 2: Test OAuth flow

1. Open browser: `http://localhost:8000/api/x/auth/authorize`
2. You should be redirected to X authorization page
3. Authorize the app
4. You'll be redirected back to frontend (or see success message)

## Step 6: Start Monitoring (After OAuth)

Once connected, you can:

1. **Get followed accounts:**
   ```bash
   curl http://localhost:8000/api/x/monitoring/accounts
   ```

2. **Start monitoring:**
   ```bash
   curl -X POST http://localhost:8000/api/x/monitoring/start
   ```

3. **Check status:**
   ```bash
   curl http://localhost:8000/api/x/monitoring/status
   ```

## Troubleshooting

### "X OAuth not configured"
- Check `.env` file has `X_CLIENT_ID` and `X_CLIENT_SECRET`
- Make sure no extra spaces or quotes around values
- Restart backend after adding credentials

### "Invalid redirect URI"
- Make sure callback URL in X Developer Portal matches exactly: `http://localhost:8000/api/x/callback`
- No trailing slash, exact match required

### "OAuth error" after authorization
- Check backend logs for detailed error
- Verify OAuth 2.0 is enabled in X Developer Portal
- Make sure app permissions are set correctly

### "Rate limit exceeded"
- X API has rate limits
- Wait a few minutes and try again
- System respects rate limits automatically

## Next: Frontend Integration

Once backend is working, we'll build the frontend UI for:
- Connect/Disconnect X account button
- Display connection status
- Show followed accounts
- Start/Stop monitoring buttons

