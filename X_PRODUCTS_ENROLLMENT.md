# Enroll App in Twitter API v2 - Step by Step

## Current Status
- ✅ App (31832043) is attached to project
- ✅ OAuth 2.0 is configured
- ✅ Account is connected
- ❌ **App is NOT enrolled in API v2** → Need to enable in Products section

## Step-by-Step: Enable Twitter API v2

### 1. Go to Products Section
1. In X Developer Portal, click on your **project** (not the app)
2. In the **left sidebar**, look for **"Products"** (might have a "NEW" badge)
3. Click on **"Products"**

### 2. Enable Twitter API v2
You should see options like:
- **"Twitter API v2"** or **"Essential"** tier
- **"Basic"** tier
- **"Pro"** tier (paid)

**For free tier:**
1. Click on **"Essential"** or **"Twitter API v2"**
2. Click **"Set up"** or **"Subscribe"**
3. Select **"Free"** tier if prompted
4. Confirm enrollment

### 3. Verify Enrollment
After enabling, you should see:
- ✅ **"Twitter API v2"** status: **"Active"** or **"Enrolled"**
- Your app listed under "Apps with API v2 access"

### 4. Regenerate OAuth Credentials (IMPORTANT!)
After enrollment, regenerate OAuth 2.0 credentials:

1. Go to **"Keys and tokens"** tab
2. Under **"OAuth 2.0 Client ID and Client Secret"**
3. Click **"Regenerate"** on **Client Secret**
4. **Copy the new Client Secret** (Client ID usually stays the same)

### 5. Update .env
```bash
# Update X_CLIENT_SECRET with the new value
```

### 6. Reconnect
```bash
rm .x_tokens.json
# Restart backend
# Then reconnect: http://localhost:8000/x/auth/authorize
```

### 7. Test
```bash
curl http://localhost:8000/x/test/following | python3 -m json.tool
```

Should see `"status_code": 200`! 🎉

## Why This Is Needed
OAuth credentials generated **before** API v2 enrollment are tied to the unenrolled state. Regenerating **after** enrollment creates credentials that work with API v2.

## If You Don't See "Products" Section
- Check if you're in the **project** (not the app)
- Some accounts might need to apply for API access first
- Free tier should be available for most accounts

