# Enabling Twitter API v2 Access

## The Issue
You're getting `403 Client Forbidden - client-not-enrolled` because your app needs to be enrolled in Twitter API v2.

## Solution: Enable Twitter API v2

1. **Go to Products section:**
   - In the left sidebar, click **"Products"** (has a "NEW" tag)
   - This will show available API products

2. **Enable Twitter API v2:**
   - Look for **"Twitter API v2"** or **"Essential"** or **"Basic"** tier
   - Click **"Set up"** or **"Subscribe"**
   - Follow the prompts to enable it

3. **Free Tier Available:**
   - Twitter API v2 has a free tier (Essential/Basic)
   - You should be able to enable it without payment
   - Free tier includes:
     - 10,000 tweets/month read
     - User lookup, following lists, etc.

4. **After Enabling:**
   - Wait a few minutes for the changes to propagate
   - Test again: `curl http://localhost:8000/x/test/following`
   - Should see `status_code: 200` instead of `403`

## Alternative: Check Project Settings

If Products section doesn't show Twitter API v2:

1. Go back to your project: **"tactical-trader"**
2. Check if there's an **"API Access"** or **"Enrollment"** section
3. Make sure the app is enrolled in API v2

## Still Not Working?

If you still get 403 after enabling API v2:
- Wait 5-10 minutes (changes can take time to propagate)
- Try regenerating OAuth 2.0 credentials
- Make sure you're using OAuth 2.0 Client ID/Secret (not API Key/Secret)

