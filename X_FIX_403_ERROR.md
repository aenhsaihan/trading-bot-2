# Fixing 403 "client-not-enrolled" Error

## The Problem
Even with Free tier access, you're getting `403 Client Forbidden - client-not-enrolled`. This means the app isn't properly enrolled in API v2.

## Solution Steps

### Step 1: Verify App is Attached to Project

1. Go to your project: **"tactical-trader"**
2. Click **"Settings"** tab
3. Look for **"App"** section
4. Make sure your app is listed there
5. If not, click **"Add App"** or **"Attach App"**

### Step 2: Regenerate OAuth 2.0 Credentials

After attaching to project, you need NEW OAuth credentials:

1. Go to **"Keys and tokens"** tab
2. Under **"OAuth 2.0 Client ID and Client Secret"**
3. Click **"Regenerate"** on both Client ID and Client Secret
4. **Copy the new values**

### Step 3: Update .env File

Update your `.env` with the NEW credentials:

```env
X_CLIENT_ID=new_client_id_here
X_CLIENT_SECRET=new_client_secret_here
X_REDIRECT_URI=http://localhost:8000/x/auth/callback
```

### Step 4: Delete Old Tokens and Reconnect

1. Delete the old token file:
   ```bash
   rm .x_tokens.json
   ```

2. Restart backend:
   ```bash
   python backend/run.py
   ```

3. Reconnect your X account:
   - Open: `http://localhost:8000/x/auth/authorize`
   - Authorize with the new credentials

### Step 5: Test Again

```bash
curl http://localhost:8000/x/test/following
```

Should see `"status_code": 200` instead of `403`.

## Why This Happens

The OAuth credentials generated BEFORE the app was attached to the project won't work with API v2. You need to regenerate them AFTER the app is properly attached.

## Alternative: Check Project Enrollment

If regenerating doesn't work:

1. Go to your project
2. Look for **"API Access"** or **"Enrollment"** section
3. Make sure API v2 is enabled/enrolled
4. There might be a button to "Enroll" or "Activate" API v2

