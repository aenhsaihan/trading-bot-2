# X API v2 Enrollment Checklist

## Current Issue
App (ID: 31832010) is getting `403 client-not-enrolled` error. The app needs to be explicitly enrolled in API v2.

## Step-by-Step Fix

### 1. Verify App is in Project

1. Go to https://developer.twitter.com/en/portal/dashboard
2. Click on project: **"tactical-trader"**
3. Go to **"Settings"** tab
4. Under **"App"** section, verify your app is listed
5. If not listed, click **"Add App"** and select your app

### 2. Check API v2 Enrollment Status

1. In your project, look for:
   - **"API Access"** section
   - **"Enrollment"** section  
   - **"Products"** → Check if API v2 shows as "Active" or "Enrolled"

2. If you see an **"Enroll"** or **"Activate"** button, click it

### 3. Regenerate OAuth Credentials (IMPORTANT)

After ensuring the app is enrolled:

1. Go to **"Keys and tokens"** tab
2. Under **"OAuth 2.0 Client ID and Client Secret"**
3. Click **"Regenerate"** on **Client Secret** (this creates new enrolled credentials)
4. Copy the new values

### 4. Update .env and Reconnect

1. Update `.env`:
   ```env
   X_CLIENT_ID=TG5HaFdkMmxDR1hGaEkyTHByTFo6MTpjaQ
   X_CLIENT_SECRET=new_secret_after_regeneration
   X_REDIRECT_URI=http://localhost:8000/x/auth/callback
   X_BEARER_TOKEN=AAAAAAAAAAAAAAAAAAAAAMq35QEAAAAA%2BwYvHJnl4pg0CilErvEE0Otq%2FY0%3D6ZsKuOw3fCNRNl0pd45X6cjJOdqZElL0cxS0FeSWR1qfZqgGsj
   ```

2. Delete old tokens:
   ```bash
   rm .x_tokens.json
   ```

3. Restart backend

4. Reconnect: `http://localhost:8000/x/auth/authorize`

### 5. Test

```bash
curl http://localhost:8000/x/test/following
```

Should see `"status_code": 200` instead of `403`.

## Why This Happens

OAuth credentials generated **before** the app is enrolled in API v2 won't work. You must regenerate them **after** enrollment.

## Alternative: Check Project Dashboard

Sometimes enrollment happens automatically when you:
1. Create a project
2. Add an app to the project
3. Enable a product (Free/Basic/Pro)

But the OAuth credentials need to be regenerated after these steps.

