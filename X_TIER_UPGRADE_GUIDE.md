# X API Tier Upgrade Guide

## The Problem
The **Free tier** doesn't support:
- ❌ Fetching followers/following lists (`/users/:id/following`)
- ❌ Fetching tweets
- ❌ Most read operations

According to [Stack Overflow](https://stackoverflow.com/questions/76486671/when-authenticating-requests-to-the-twitter-api-v2-endpoints), you need at least the **Basic tier** (paid) to access these endpoints.

## What Free Tier Allows
✅ Create/delete tweets
✅ Get user info (profile)

## What Requires Basic Tier
✅ Get tweets
✅ Get followers/following lists
✅ Most read operations

## How to Upgrade to Basic Tier

### Step 1: Go to Products Section
1. In X Developer Portal, go to your **project**
2. Click **"Products"** in the left sidebar
3. You should see tiers: **Free**, **Basic**, **Pro**

### Step 2: Subscribe to Basic Tier
1. Click on **"Basic"** tier
2. Review pricing (usually $100/month)
3. Click **"Subscribe"** or **"Upgrade"**
4. Complete payment/subscription process

### Step 3: Verify Access
After subscribing:
1. Your project should show **"Basic"** tier status
2. Your app should automatically have access to:
   - `/users/:id/following` endpoint
   - Tweet fetching endpoints
   - Other read operations

### Step 4: Test Again
```bash
curl http://localhost:8000/x/test/following | python3 -m json.tool
```

Should work now! 🎉

## Alternative: Check Current Tier
1. Go to your project dashboard
2. Look for **"API Access"** or **"Subscription"** section
3. Check what tier you're currently on
4. If it says "Free", you'll need to upgrade

## Cost Consideration
- **Basic tier**: ~$100/month
- **Pro tier**: ~$5,000/month

For MVP/testing, Basic tier should be sufficient.

## References
- [Stack Overflow Discussion](https://stackoverflow.com/questions/76486671/when-authenticating-requests-to-the-twitter-api-v2-endpoints)
- X API Documentation: https://developer.twitter.com/en/docs

