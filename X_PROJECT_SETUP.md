# X Developer Project Setup - Fixing 403 Error

## Issue
Getting `403 Client Forbidden` error: "client-not-enrolled" when trying to use API v2 endpoints.

## Solution

### Step 1: Verify App is Attached to Project

1. Go to https://developer.twitter.com/en/portal/dashboard
2. Click on your project: **"tactical-trader"**
3. Go to **"Settings"** tab (not "Keys and tokens")
4. Under **"App"** section, make sure your app is listed and attached
5. If not attached, click **"Add App"** or **"Attach App"**

### Step 2: Check API Access Level

The error might also mean you need to upgrade your API access:

1. In your project, go to **"Products"** in the left sidebar
2. Check if you have **"Twitter API v2"** access enabled
3. If not, you may need to:
   - Apply for API access (free tier available)
   - Or upgrade to a paid tier

### Step 3: Verify OAuth 2.0 Credentials

1. Make sure you're using the **OAuth 2.0 Client ID and Client Secret** from the project
2. These are different from:
   - API Key/Secret (for API v1.1)
   - Bearer Token (for read-only access)
3. Your Client ID should start with something like: `TG5HaFdkMmxDR1hGaEkyTHByTFo6MTpjaQ`

### Step 4: Update .env File

Make sure your `.env` has the OAuth 2.0 credentials from the **project** (not from a standalone app):

```env
X_CLIENT_ID=TG5HaFdkMmxDR1hGaEkyTHByTFo6MTpjaQ
X_CLIENT_SECRET=your_client_secret_from_project
X_REDIRECT_URI=http://localhost:8000/x/auth/callback
```

### Step 5: Reconnect After Changes

If you regenerated credentials or changed project settings:

1. Delete `.x_tokens.json` (old tokens won't work)
2. Restart backend
3. Reconnect: `http://localhost:8000/x/auth/authorize`

## Common Issues

### "App not attached to project"
- Solution: Go to project Settings → Add/Attach your app

### "Insufficient API access level"
- Solution: Apply for Twitter API v2 access in Products section

### "Using wrong credentials"
- Solution: Make sure you're using OAuth 2.0 Client ID/Secret from the project, not from a standalone app

## Test After Fixing

```bash
# Test connection
curl http://localhost:8000/x/auth/status

# Test API access
curl http://localhost:8000/x/test/following
```

If it works, you should see `status_code: 200` instead of `403`.

