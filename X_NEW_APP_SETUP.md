# Setting Up OAuth 2.0 for New App

## Step 1: Set Up User Authentication

1. On the **Settings** tab, find **"User authentication settings"**
2. Click the **"Set up"** button
3. This will open the OAuth 2.0 configuration

## Step 2: Configure OAuth 2.0

When you click "Set up", you'll see a form. Fill it in:

1. **App permissions:**
   - ✅ Read tweets
   - ✅ Read users  
   - ✅ Read follows
   - ✅ Offline access (for refresh tokens)

2. **Callback URI / Redirect URL:**
   ```
   http://localhost:8000/x/auth/callback
   ```

3. **Website URL:**
   ```
   https://example.com
   ```
   (or your actual website URL)

4. **Type of App:**
   - Select "Web App" or "Automated App"

5. Click **"Save"** or **"Update"**

## Step 3: Get New OAuth 2.0 Credentials

After setting up OAuth 2.0:

1. Go to **"Keys and tokens"** tab
2. Scroll down to **"OAuth 2.0 Client ID and Client Secret"**
3. Copy the **Client ID** and **Client Secret**
4. These will be DIFFERENT from your old app's credentials

## Step 4: Update .env File

Replace the old OAuth credentials with the new ones:

```env
X_CLIENT_ID=new_client_id_from_new_app
X_CLIENT_SECRET=new_client_secret_from_new_app
X_REDIRECT_URI=http://localhost:8000/x/auth/callback
X_API_KEY=ms4snfwsZArZtND7ro4hFcMEe
X_API_SECRET=9TmhJRUvHcCdkL61c1IlIcBSi2Hut8EY3n0hmjbvn3pxyw4prf
X_BEARER_TOKEN=AAAAAAAAAAAAAAAAAAAAAMq35QEAAAAA%2BwYvHJnl4pg0CilErvEE0Otq%2FY0%3D6ZsKuOw3fCNRNl0pd45X6cjJOdqZElL0cxS0FeSWR1qfZqgGsj
```

## Step 5: Clean Up and Reconnect

1. Delete old tokens:
   ```bash
   rm .x_tokens.json
   ```

2. Restart backend:
   ```bash
   python backend/run.py
   ```

3. Reconnect X account:
   - Open: `http://localhost:8000/x/auth/authorize`
   - Authorize the new app

## Step 6: Test

```bash
curl http://localhost:8000/x/test/following
```

Should see `"status_code": 200` instead of `403`!

## Why This Will Work

The new app is:
- ✅ Attached to the project
- ✅ Will have OAuth 2.0 properly configured
- ✅ Will be enrolled in API v2 (since it's in a project with API v2 access)

The old app (31832010) wasn't properly enrolled, but the new one should work!

