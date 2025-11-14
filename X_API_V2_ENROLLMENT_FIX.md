# Fix: App Not Enrolled in API v2

## Current Status
✅ App is attached to project (ID: 31832043)
✅ OAuth 2.0 is configured
✅ Account is connected (user_id: 1989203910213660680)
❌ **App is NOT enrolled in API v2** (403 "client-not-enrolled")

## The Problem
Even though your app is attached to a project, it needs to be **explicitly enrolled** in Twitter API v2 access.

## Solution: Enroll App in API v2

### Step 1: Go to Your Project Dashboard
1. In the X Developer Portal, go to your **project** (not the app)
2. Look for a section called:
   - **"Products"** or **"API Access"**
   - **"Enroll"** or **"Activate API v2"** button
   - **"Twitter API v2"** section

### Step 2: Enable API v2 Access
You should see options like:
- ✅ **Twitter API v2** (toggle or checkbox)
- Or a button: **"Enroll in API v2"** or **"Activate"**

### Step 3: Select Your App
If prompted, select your app: **tactical-trader** (ID: 31832043)

### Step 4: Confirm Enrollment
After enrolling, you should see:
- ✅ API v2 status: **Active** or **Enrolled**
- Your app listed under "Apps with API v2 access"

## Alternative: Check Project Settings

If you don't see an enrollment option:

1. Go to **Project Settings**
2. Look for **"API Access"** or **"Products"**
3. Check if **Twitter API v2** is listed and enabled
4. If not, there might be a **"Request Access"** or **"Upgrade"** option

## After Enrollment

1. **No need to regenerate credentials** (OAuth tokens are fine)
2. **Test again:**
   ```bash
   curl http://localhost:8000/x/test/following | python3 -m json.tool
   ```

## Expected Result After Enrollment

```json
{
  "success": true,
  "status_code": 200,
  "response": {
    "accounts": [
      {
        "id": "...",
        "username": "...",
        "name": "..."
      }
    ],
    "count": 5
  }
}
```

## If You Can't Find Enrollment Option

The project might need to be upgraded or you might need to:
1. Check your **Developer Account tier** (Free/Basic/Pro)
2. Some features require a paid tier
3. Contact X Developer Support if enrollment option is missing

Let me know what you see in the project dashboard!

