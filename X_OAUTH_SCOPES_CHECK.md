# X OAuth 2.0 Scopes Verification

## Current Scopes We're Requesting

According to our code in `x_auth_service.py`, we're requesting:
```
tweet.read users.read follows.read offline.access
```

## Required Scopes for `/users/:id/following`

According to [X API v2 authentication mapping](https://docs.x.com/fundamentals/authentication/guides/v2-authentication-mapping):

The endpoint `GET /2/users/:id/following` requires:
- **OAuth 2.0 Authorization Code with PKCE** ✅ (we're using this)
- **Scopes:** `tweet.read`, `users.read`, `follows.read` ✅ (we have all of these)

## Verification

Our implementation is correct:
- ✅ Using OAuth 2.0 Authorization Code with PKCE
- ✅ Requesting correct scopes: `tweet.read users.read follows.read offline.access`
- ✅ Using correct endpoint: `/users/:id/following`
- ✅ Using OAuth 2.0 access token (not Bearer token) for user-specific endpoints

## The Real Issue

The 403 "client-not-enrolled" error is **NOT** about scopes or authentication method. It's about:

**The app (ID: 31832010) is not enrolled in Twitter API v2.**

Even with:
- ✅ Correct OAuth 2.0 flow
- ✅ Correct scopes
- ✅ Correct endpoint
- ✅ All credentials configured

The app needs to be **explicitly enrolled in API v2** in the X Developer Portal.

## Solution

1. Go to your project "tactical-trader" in X Developer Portal
2. Look for **"Enroll"** or **"Activate API v2"** button
3. Or check **"Products"** section → Make sure Twitter API v2 is **"Active"** or **"Enrolled"**
4. After enrollment, **regenerate OAuth 2.0 Client Secret** (old credentials won't work)
5. Update `.env` with new Client Secret
6. Reconnect your X account

## Why This Happens

OAuth credentials generated **before** the app is enrolled in API v2 are tied to the unenrolled app state. You must regenerate them **after** enrollment.

